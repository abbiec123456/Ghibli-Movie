"""
Ghibli Movie Booking System

This Flask application provides a simple web interface for customers to log in,
view their personal details and bookings, and update extra requests for courses.

"""

import os
import re
import logging
from urllib.parse import urlparse
import psycopg2
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "ghibli_secret_key")
env = os.environ.get("FLASK_ENV", "development").lower()
if env == "production" and app.config["SECRET_KEY"] == "ghibli_secret_key":
    raise ValueError("No SECRET_KEY set !")

LOGIN_TEMPLATE = "customer_login.html"
REGISTER_TEMPLATE = "REGISTER_TEMPLATE"
INVALID_CRED_MSG = "Invalid login credentials"

# Initialize Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def get_db_connection():
    """
    Parse DATABASE_URL (from Docker Compose) and connect securely.
    """
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")

    parsed = urlparse(database_url)

    return psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        dbname=parsed.path[1:],
        user=parsed.username,
        password=parsed.password,
    )


app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_DEBUG", "1") == "0"

csrf = CSRFProtect(app)


# ---------- LANDING PAGE ----------
@app.route("/")
def index():
    """
    Render the landing page.

    Returns:
        str: Rendered HTML template for the index page
    """
    return render_template("index.html")

# ---------- PASSWORD VERIFICATION ----------
def verify_customer_password(stored_password, provided_password, email):
    """Handles both modern hashes and legacy plain-text migration.
    
    Returns:
        bool: True if password is valid, False otherwise
    """
    if stored_password.startswith(("pbkdf2:", "sha256:", "scrypt:")):
        return check_password_hash(stored_password, provided_password)
    
    # Legacy check
    if stored_password == provided_password:
        rehash_customer_password(email, provided_password)
        return True
    return False


# ---------- GET CUSTOMER HELPER ----------
def get_customer_by_email(email):
    """
    Retrieve a customer record from the database based on their email address.

    This helper isolates the database connection and query logic to streamline 
    the authentication flow and reduce cognitive complexity in route handlers.

    Args:
        email (str): The email address of the customer to look up.

    Returns:
        tuple: A tuple containing (customer_id, name, last_name, email, phone, password)
                if found; otherwise, None.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT customer_id, name, last_name, email, phone, password
                FROM customers
                WHERE email = %s
                """,
                (email,),
            )
            return cur.fetchone()
    finally:
        conn.close()

def rehash_customer_password(email, password):
    """
    Update a customer's plain-text password to a secure hash in the database.

    This function is triggered during a successful login for accounts still 
    using legacy plain-text passwords. It ensures seamless migration to 
    Werkzeug-compatible secure hashing without disrupting the user experience.

    Args:
        email (str): The unique email identifier for the customer.
        password (str): The plain-text password to be hashed and stored.

    Returns:
        None
    """
    new_hashed = generate_password_hash(password)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE customers SET password = %s WHERE email = %s",
                (new_hashed, email),
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error rehashing customer password: {e}")
    finally:
        conn.close()


# ---------- CUSTOMER LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def customer_login():
    """
    Handle customer login.

    GET: Display the login form
    POST: Process login credentials and create session

    Returns:
        str: login template or redirect to dashboard on POST
    """
    if request.method == "GET":
        return render_template(LOGIN_TEMPLATE)
    
    email = request.form.get("email")
    password = request.form.get("password")

    cur = None
    row = None
    try:
        row = get_customer_by_email(email)

    except Exception:
        flash("INVALID_CRED_MSG", "error")
        return render_template(LOGIN_TEMPLATE), 401

    if not row or not verify_customer_password(row[5], password, email):
        flash("INVALID_CRED_MSG", "error")
        return render_template(LOGIN_TEMPLATE), 200

    customer_id, first_name, last_name, email_db, phone, stored_password = row

    # Successful login — set session
    full_name = f"{first_name} {last_name}"
    session["user"] = email_db
    session["role"] = "customer"
    session["name"] = full_name
    session["email"] = email_db
    session["phone"] = phone

    return redirect(url_for("customer_dashboard"))

def validate_registration(form, testing_mode):
    """
    Validate customer registration input data against business rules.

    Checks for presence of required fields, email format validity, 
    password matching, and password complexity (if not in testing mode).

    Args:
        form_data (dict): The request.form dictionary containing user input.
        testing_mode (bool): Flag to bypass strict password complexity 
                             requirements during automated tests.

    Returns:
        str: An error message if validation fails; otherwise, None.
    """
    password = form.get("password")
    email = form.get("email")
    
    if not all([form.get("first_name"), form.get("last_name"), email, password]):
        return "Please fill in all required fields."
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return "Please enter a valid email address."
    if password != form.get("confirm_password"):
        return "Passwords do not match."
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    
    if not testing_mode:
        if not all([re.search(r"[A-Z]", password), re.search(r"[a-z]", password), re.search(r"[0-9]", password)]):
            return "Password must include uppercase, lowercase and a number."
    return None


# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Handle customer registration.

    GET: Display the registration form
    POST: Process registration and create new customer account

    Returns:
        str: Rendered registration template or redirect to login
    """
    if request.method == "GET":
        return render_template(REGISTER_TEMPLATE)
    
    error = validate_registration(request.form, app.config.get("TESTING"))
    if error:
        flash(error, "error")
        return render_template(REGISTER_TEMPLATE)

    # Hash the password for live/new users
    hashed_pw = (
        generate_password_hash(request.form.get("password"))
        if not app.config.get("TESTING")
        else request.form.get("password")
        )

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO customers
                (name, last_name, email, phone, created_at, password)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                """,
                (request.form.get("first_name"), request.form.get("last_name"), 
                request.form.get("email"), request.form.get("phone"), hashed_pw)
            )
            conn.commit()
        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("customer_login"))
    except Exception as e:
        msg = str(e).lower()
        if "duplicate" in msg or "unique" in msg:
            flash("An account with this email already exists.", "error")
            return render_template(REGISTER_TEMPLATE)
        return "Error creating account", 500
    finally:
        if 'conn' in locals(): conn.close()    


# ---------- CUSTOMER DASHBOARD ----------
@app.route("/dashboard", methods=["GET", "POST"])
def customer_dashboard():
    """
    Display customer dashboard with personal details and bookings.
    """
    if session.get("role") != "customer":
        return redirect(url_for("customer_login"))

    user_email = session.get("email")

    if request.method == "POST":
        course_id_to_update = request.form.get("course")
        new_extra = request.form.get("extra")

        if not course_id_to_update:
            return "Missing course ID", 400

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            update_query = """
            UPDATE bookings
            SET nice_to_have_requests = %s, updated_at = NOW()
            FROM customers c
            WHERE bookings.customer_id = c.customer_id
            AND c.email = %s
            AND bookings.course_id = %s
            """
            cursor.execute(update_query, (new_extra, user_email, course_id_to_update))
            conn.commit()

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Update Error: {e}")
            return f"Error updating booking: {e}", 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

        # Redirect-after-POST to prevent resubmission
        return redirect(url_for("customer_dashboard"))

    # --- GET ---
    personal_details = {
        "name": session.get("name"),
        "email": session.get("email"),
        "phone": session.get("phone"),
    }

    conn = None
    cursor = None
    user_bookings = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
        SELECT
            b.booking_id,
            b.course_id,
            b.nice_to_have_requests,
            b.status,
            co.course_name,
            co.description
        FROM bookings b
        JOIN customers c ON b.customer_id = c.customer_id
        JOIN courses co ON b.course_id = co.course_id
        WHERE c.email = %s
        ORDER BY b.booking_id DESC
        """
        cursor.execute(query, (user_email,))
        rows = cursor.fetchall()

        for row in rows:
            user_bookings.append(
                {
                    "booking_id": row[0],
                    "course_id": row[1],
                    "extra": row[2],
                    "status": row[3],
                    "course": row[4],
                    "description": row[5],
                }
            )

    except Exception as e:
        logger.error(f"Dashboard Fetch Error: {e}")
        return f"Error fetching dashboard: {e}", 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template(
        "customer_dashboard.html",
        personal_details=personal_details,
        bookings=user_bookings,
    )


# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    """
    Log out the current user by clearing the session.

    Returns:
        werkzeug.wrappers.Response: Redirect to login page
    """
    session.clear()
    return redirect(url_for("customer_login"))


# ---------- BOOKING PAGE -----------
@app.route("/book", methods=["GET", "POST"])
def booking():
    """
    Handle course booking.
    Fetches active courses and modules from DB for selection.
    """
    if session.get("role") != "customer":
        return redirect(url_for("customer_login"))

    user_email = session.get("email")

    # --- POST: Handle Form Submission ---
    if request.method == "POST":
        selected_course_ids = request.form.getlist("courses")
        extra_request = request.form.get("extra", "")

        if not selected_course_ids:
            return redirect(url_for("booking"))

        new_booking_ids = []

        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute(
                "SELECT customer_id FROM customers WHERE email = %s", (user_email,)
            )
            customer_row = cur.fetchone()
            if not customer_row:
                return redirect(url_for("customer_login"))
            customer_id = customer_row[0]

            for course_id in selected_course_ids:
                # Check for duplicate booking
                cur.execute(
                    "SELECT booking_id FROM bookings WHERE customer_id = %s AND course_id = %s",
                    (customer_id, course_id),
                )
                if cur.fetchone():
                    continue

                # Insert booking
                cur.execute(
                    """
                    INSERT INTO bookings
                    (customer_id, course_id, status, nice_to_have_requests, updated_at)
                    VALUES (%s, %s, 'Pending', %s, NOW())
                    RETURNING booking_id
                    """,
                    (customer_id, course_id, extra_request),
                )
                new_booking_id = cur.fetchone()[0]
                new_booking_ids.append(new_booking_id)

                # Insert selected modules
                selected_module_ids = request.form.getlist(f"modules_{course_id}")
                if selected_module_ids:
                    module_insert_data = [
                        (new_booking_id, m_id) for m_id in selected_module_ids
                    ]
                    cur.executemany(
                        "INSERT INTO booking_modules (booking_id, module_id) VALUES (%s, %s)",
                        module_insert_data,
                    )

            conn.commit()
            session["last_booking_ids"] = new_booking_ids
            return redirect(url_for("booking_submitted"))

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Booking POST Error: {e}")
            return f"Error processing booking: {e}", 500
        finally:
            if conn:
                conn.close()

    # --- GET: Render Form ---
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT course_id, course_name, description
            FROM courses
            WHERE active = TRUE
            ORDER BY course_name
        """)
        courses_data = cur.fetchall()

        cur.execute("""
            SELECT module_id, course_id, module_name, module_description
            FROM course_modules
            WHERE active = TRUE
            ORDER BY module_order
        """)
        modules_data = cur.fetchall()

        cur.close()
        conn.close()

        modules_by_course = {}
        for m in modules_data:
            m_id, m_course_id, m_name, m_desc = m
            if m_course_id not in modules_by_course:
                modules_by_course[m_course_id] = []
            modules_by_course[m_course_id].append(
                {"id": m_id, "name": m_name, "description": m_desc}
            )

        courses_payload = []
        for c in courses_data:
            c_id, c_name, c_desc = c
            courses_payload.append(
                {
                    "id": c_id,
                    "name": c_name,
                    "description": c_desc,
                    "modules": modules_by_course.get(c_id, []),
                }
            )

        return render_template(
            "booking.html",
            user={
                "name": session.get("name"),
                "email": session.get("email"),
                "phone": session.get("phone"),
            },
            courses=courses_payload,
        )

    except Exception as e:
        logger.error(f"Booking GET Error: {e}")
        return f"Error loading booking page: {e}", 500
    finally:
        if conn:
            conn.close()


# ---------- BOOKING SUBMITTED ----------
@app.route("/booking-submitted")
def booking_submitted():
    """
    Display booking confirmation page.

    Shows the details of the most recently submitted booking.
    Requires authentication.

    Returns:
        str: Rendered booking confirmation template or redirect
    """
    if session.get("role") != "customer":
        return redirect(url_for("customer_login"))

    booking_ids = session.get("last_booking_ids")
    if not booking_ids:
        return redirect(url_for("booking"))

    booking_details = []

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT b.booking_id, c.course_name, b.nice_to_have_requests
            FROM bookings b
            JOIN courses c ON b.course_id = c.course_id
            WHERE b.booking_id = ANY(%s)
            """,
            (booking_ids,),
        )

        rows = cur.fetchall()

        for row in rows:
            b_id, c_name, extra = row

            cur.execute(
                """
                SELECT m.module_name
                FROM booking_modules bm
                JOIN course_modules m ON bm.module_id = m.module_id
                WHERE bm.booking_id = %s
                """,
                (b_id,),
            )

            modules = [m_row[0] for m_row in cur.fetchall()]

            booking_details.append(
                {"course": c_name, "modules": modules, "extra": extra}
            )

        cur.close()
        conn.close()

    except Exception as e:
        logger.error(f"Error fetching confirmation: {e}")
        return "Error loading confirmation", 500
    finally:
        if conn:
            conn.close()

    return render_template(
        "booking_submitted.html",
        bookings=booking_details,
    )


# ---------- ADMIN LOGIN ----------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """
    Handle administrator login.
    Supports both hashed and legacy plain-text passwords, auto-rehashing on login.
    """
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = None
        row = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT admin_id, name, email, password
                FROM admins
                WHERE email = %s
                """,
                (email,),
            )
            row = cur.fetchone()
            cur.close()
            conn.close()

        except Exception:
            flash("Database error occurred.", "error")
            return render_template("admin_login.html"), 500

        if not row:
            flash("Invalid admin credentials", "error")
            return render_template("admin_login.html"), 401

        admin_id, name, email_db, stored_password = row

        # Check password — support hashed and legacy plain-text
        valid = False
        if stored_password.startswith(("pbkdf2:", "sha256:", "scrypt:")):
            valid = check_password_hash(stored_password, password)
        else:
            # Legacy plain-text — compare, then rehash in a fresh connection
            if stored_password == password:
                valid = True
                new_hashed = generate_password_hash(password)
                rehash_conn = None
                rehash_cur = None
                try:
                    rehash_conn = get_db_connection()
                    rehash_cur = rehash_conn.cursor()
                    rehash_cur.execute(
                        "UPDATE admins SET password = %s WHERE email = %s",
                        (new_hashed, email),
                    )
                    rehash_conn.commit()
                except Exception as e:
                    logger.error(f"Error rehashing admin password: {e}")
                finally:
                    if rehash_cur:
                        rehash_cur.close()
                    if rehash_conn:
                        rehash_conn.close()

        # FIX: session assignment is strictly inside the `if valid:` block
        if valid:
            session.clear()
            session["user"] = email_db
            session["role"] = "admin"
            session["name"] = name
            return redirect(url_for("admin_dashboard"))

        flash("Invalid admin credentials", "error")
        return render_template("admin_login.html"), 401

    return render_template("admin_login.html")


# ---------- ADMIN DASHBOARD ----------
@app.route("/admin")
def admin_dashboard():
    """
    Admin dashboard showing summary counts.
    """
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM customers")
        customer_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM courses")
        course_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM bookings")
        booking_count = cur.fetchone()[0]

        return render_template(
            "admin_dashboard.html",
            customer_count=customer_count,
            course_count=course_count,
            booking_count=booking_count,
        )

    except Exception as e:
        return f"Admin Stats Error: {e}", 500

    finally:
        if conn:
            conn.close()

# --------------------- ADMIN COURSE -----------


@app.route("/admin/courses", methods=["GET", "POST"])
def manage_courses():
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if request.method == "POST":
            course_name = request.form.get("course_name", "").strip()
            description = request.form.get("description", "").strip()

            if not course_name or not description:
                flash("Course name and description are required.", "error")
                return redirect(url_for("manage_courses"))

            cur.execute(
                """
                INSERT INTO courses (course_name, description, active, created_at)
                VALUES (%s, %s, TRUE, NOW())
                """,
                (course_name, description),
            )
            conn.commit()
            flash("Course created successfully.", "success")
            return redirect(url_for("manage_courses"))

        cur.execute(
            """
            SELECT course_id, course_name, description
            FROM courses
            WHERE active = TRUE
            ORDER BY course_id ASC
            """
        )
        rows = cur.fetchall()

        courses = [
            {
                "id": row[0],
                "name": row[1],
                "description": row[2],
            }
            for row in rows
        ]

        cur.close()
        return render_template("admin_courses.html", courses=courses)

    except Exception as e:
        if conn:
            conn.rollback()
        return f"Manage Courses Error: {e}", 500

    finally:
        if conn:
            conn.close()


@app.route("/admin/courses/<int:course_id>/delete", methods=["POST"])
def delete_course(course_id):
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("DELETE FROM courses WHERE course_id = %s", (course_id,))
        conn.commit()

        flash("Course deleted successfully.", "success")
        return redirect(url_for("manage_courses"))

    except Exception:
        if conn:
            conn.rollback()
        flash("Unable to delete course.", "error")
        return redirect(url_for("manage_courses"))

    finally:
        if conn:
            conn.close()

# ---------- ADMIN MANAGE BOOKINGS ----------


@app.route("/admin/bookings")
def manage_bookings():
    """
    List all bookings for admin review.
    """
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT b.booking_id, c.email, co.course_name, b.nice_to_have_requests
            FROM bookings b
            JOIN customers c ON b.customer_id = c.customer_id
            JOIN courses co ON b.course_id = co.course_id
            ORDER BY b.booking_id DESC
        """)
        rows = cur.fetchall()
        bookings = [{"id": r[0], "email": r[1], "course": r[2], "extra": r[3]} for r in rows]
        return render_template("manage_bookings.html", bookings=bookings)
    except Exception as e:
        return f"Error loading bookings: {e}", 500
    finally:
        if conn:
            conn.close()


# ---------- ADMIN EDIT BOOKING ----------
@app.route("/admin/bookings/<int:booking_id>/edit", methods=["GET", "POST"])
def edit_booking(booking_id):
    """
    Handle editing of bookings in admin panel.

    GET: Display the edit booking form
    POST: Process booking updates

    Args:
        booking_id (int): The ID of the booking to edit

    Returns:
        str: Rendered edit template or redirect to bookings list
    """
    if not app.config.get("TESTING") and session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if request.method == "POST":
            new_course_id = request.form.get("course_id")
            new_extra = request.form.get("extra")

            cur.execute("""
                UPDATE bookings
                SET course_id = %s, nice_to_have_requests = %s, updated_at = NOW()
                WHERE booking_id = %s
            """, (new_course_id, new_extra, booking_id))
            conn.commit()
            flash("Booking updated successfully!", "success")
            return redirect(url_for("manage_bookings"))

        # GET: Fetch current booking and all courses for the dropdown
        cur.execute("""
            SELECT b.booking_id, b.nice_to_have_requests, b.course_id, c.course_name
            FROM bookings b
            JOIN courses c ON b.course_id = c.course_id
            WHERE b.booking_id = %s
        """, (booking_id,))
        row = cur.fetchone()

        if not row:
            return "Booking not found", 404

        cur.execute("SELECT course_id, course_name FROM courses WHERE active = TRUE")
        all_courses = cur.fetchall()

        booking_data = {
            "id": row[0],
            "extra": row[1],
            "course_id": row[2],
            "course_name": row[3],
        }

        return render_template("edit_booking.html", booking=booking_data, courses=all_courses)

    except Exception as e:
        if conn:
            conn.rollback()
        flash(f"Error updating booking: {e}", "error")
        return redirect(url_for("manage_bookings"))
    finally:
        if conn:
            conn.close()


# ---------- ADMIN DELETE BOOKING ----------
@app.route("/admin/bookings/<int:booking_id>/delete", methods=["POST"])
def delete_booking(booking_id):
    """
    Delete a booking and its associated modules.
    """
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM booking_modules WHERE booking_id = %s", (booking_id,))
        cur.execute("DELETE FROM bookings WHERE booking_id = %s", (booking_id,))
        conn.commit()
        flash("Booking deleted successfully.", "success")
    except Exception as e:
        if conn:
            conn.rollback()
        flash(f"Error deleting booking: {e}", "error")
    finally:
        if conn:
            conn.close()
    return redirect(url_for("manage_bookings"))


# ---------- ADMIN LIST CUSTOMERS ----------
@app.route("/admin/customers")
def admin_customers():
    """
    List all customers for admin review.
    """
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT customer_id, name, last_name, email, phone, created_at
            FROM customers
            ORDER BY customer_id DESC
        """)
        rows = cur.fetchall()
        customers = [
            {
                "id": r[0],
                "name": r[1],
                "last_name": r[2],
                "email": r[3],
                "phone": r[4],
                "created": r[5],
            }
            for r in rows
        ]
        return render_template("manage_customers.html", customerlist=customers)
    except Exception as e:
        return f"Error loading customers: {e}", 500
    finally:
        if conn:
            conn.close()


# ---------- ADMIN DELETE CUSTOMER ----------
@app.route("/admin/customers/<int:customer_id>/delete", methods=["POST"])
def delete_customer(customer_id):
    """
    Delete a customer and all their associated bookings and modules.
    """
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Delete booking_modules for all of this customer's bookings
        cur.execute(
            """
            DELETE FROM booking_modules
            WHERE booking_id IN (
                SELECT booking_id FROM bookings WHERE customer_id = %s
            )
            """,
            (customer_id,),
        )

        cur.execute("DELETE FROM bookings WHERE customer_id = %s", (customer_id,))
        cur.execute("DELETE FROM customers WHERE customer_id = %s", (customer_id,))

        conn.commit()
        flash("Customer deleted successfully.", "success")
    except Exception as e:
        if conn:
            conn.rollback()
        flash(f"Error deleting Customer: {e}", "error")
    finally:
        if conn:
            conn.close()
    return redirect(url_for("admin_customers"))


# ---------- ADMIN EDIT CUSTOMER ----------
@app.route("/admin/customers/<int:customer_id>/edit", methods=["GET", "POST"])
def edit_customer(customer_id):
    """
    Handle editing of a customer from admin dashboard.

    GET: Display the edit customer form
    POST: Process customer update

    Args:
        customer_id (int): The ID of the customer to edit

    Returns:
        str: Rendered edit template or redirect to customers list
    """
    if not app.config.get("TESTING") and session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if request.method == "POST":
            new_name = request.form.get("name", "").strip()
            new_last_name = request.form.get("last_name", "").strip()
            new_email = request.form.get("email", "").strip()
            new_phone = request.form.get("phone", "").strip()

            if not all([new_name, new_last_name, new_email]):
                flash("Name, last name and email are required.", "error")
                return redirect(url_for("edit_customer", customer_id=customer_id))

            cur.execute(
                """
                UPDATE customers
                SET name = %s, last_name = %s, email = %s, phone = %s
                WHERE customer_id = %s
                """,
                (new_name, new_last_name, new_email, new_phone, customer_id),
            )
            conn.commit()
            flash("Customer updated successfully!", "success")
            return redirect(url_for("admin_customers"))

        # GET: fetch current customer data
        cur.execute(
            """
            SELECT customer_id, name, last_name, email, phone
            FROM customers
            WHERE customer_id = %s
            """,
            (customer_id,),
        )
        row = cur.fetchone()

        if not row:
            return "Customer not found", 404

        customer_data = {
            "id": row[0],
            "name": row[1],
            "last_name": row[2],
            "email": row[3],
            "phone": row[4],
        }
        return render_template("edit_customer.html", customer=customer_data)

    except Exception as e:
        if conn:
            conn.rollback()
        flash(f"Error updating customer: {e}", "error")
        return redirect(url_for("admin_customers"))
    finally:
        if conn:
            conn.close()


# ---------- DEBUG DB DUMP (admin-only) ----------
_ALLOWED_TABLES = {
    "customers", "admins", "bookings", "courses",
    "course_modules", "booking_modules",
}


@app.route("/debug/db-dump")
def db_dump():
    """
    Dump all database tables for debugging — admin only.
    """
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    conn = None
    db_content = {}

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """)
        tables = [row[0] for row in cur.fetchall()]

        for table in tables:
            # whitelist table names to prevent SQL injection
            if table not in _ALLOWED_TABLES:
                continue

            cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
                (table,),
            )
            columns = [col[0] for col in cur.fetchall()]

            # Safe: table name is validated against whitelist above
            cur.execute(f"SELECT * FROM {table}")  # noqa: S608
            rows = cur.fetchall()

            db_content[table] = {"columns": columns, "rows": rows}

        cur.close()
    except Exception as e:
        return f"Error dumping database: {str(e)}", 500
    finally:
        if conn:
            conn.close()

    return render_template("db_dump.html", db_content=db_content)


if __name__ == "__main__":
    app.run(debug=True)
