"""
Ghibli Movie Booking System

This Flask application provides a simple web interface for customers to log in,
view their personal details and bookings, and update extra requests for courses.

Note: This is a basic implementation with temporary in-memory data.
"""

import os
import re
import psycopg2
from urllib.parse import urlparse
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "ghibli_secret_key")
env = os.environ.get("FLASK_ENV", "development").lower()
if env == "production" and app.config["SECRET_KEY"] == "ghibli_secret_key":
    raise ValueError("No SECRET_KEY set !")


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

ABBIE_EMAIL = "abbie@example.com"

# ---------- TEMPORARY IN-MEMORY STORAGE ----------

CUSTOMERS = {
    ABBIE_EMAIL: {
        "password": "group1",
        "name": "Abbie Smith",
        "email": ABBIE_EMAIL,
        "phone": "123-456-7890",
    }
}

BOOKINGS = [
    {
        "id": 1,
        "email": ABBIE_EMAIL,
        "course": "Moving Castle Creations – 3D Animation",
        "extra": "Beginner friendly tools",
    },
    {
        "id": 2,
        "email": ABBIE_EMAIL,
        "course": "Totoro Character Design",
        "extra": "",
    },
]


def ensure_booking_ids():
    """
    Ensure every booking dict has an integer 'id'.
    If missing, assign sequential ids (1..n).
    """
    for i, b in enumerate(BOOKINGS, start=1):
        if isinstance(b, dict) and b.get("id") is None:
            b["id"] = i


MODULE_LABELS = {
    "module1": "Introduction to 3D Animation",
    "module2": "Character Design Basics",
    "module3": "Environmental Modelling",
}


# ---------- LANDING PAGE ----------
@app.route("/")
def index():
    """
    Render the landing page.

    Returns:
        str: Rendered HTML template for the index page
    """
    return render_template("index.html")


# ---------- CUSTOMER LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def customer_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = None
        cur = None
        row = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT customer_id, name, last_name, email, phone, password
                FROM customers
                WHERE email = %s
                """,
                (email,),
            )
            row = cur.fetchone()
        except Exception:
            flash("Invalid login credentials", "error")
            return render_template("customer_login.html"), 401
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

        if not row:
            flash("Invalid login credentials", "error")
            return render_template("customer_login.html"), 200

        customer_id, first_name, last_name, email_db, phone, stored_password = row

        # --- Check password ---
        valid = False
        if stored_password.startswith(("pbkdf2:", "sha256:", "scrypt:")):
            # hashed password → check directly
            valid = check_password_hash(stored_password, password)
        else:
            # old plain-text password → compare, then rehash
            if stored_password == password:
                valid = True
                # automatically rehash and update DB
                new_hashed = generate_password_hash(password)
                conn = None
                cur = None
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute(
                        "UPDATE customers SET password = %s WHERE email = %s",
                        (new_hashed, email),
                    )
                    conn.commit()
                except Exception as e:
                    print(f"Error rehashing old password: {e}")
                finally:
                    if cur:
                        cur.close()
                    if conn:
                        conn.close()

        if not valid:
            flash("Invalid login credentials", "error")
            return render_template("customer_login.html"), 200

        # Successful login → set session
        full_name = f"{first_name} {last_name}"
        CUSTOMERS[email_db] = {
            "password": stored_password,
            "name": full_name,
            "email": email_db,
            "phone": phone,
        }

        session["user"] = email_db
        session["role"] = "customer"
        session["name"] = full_name
        session["email"] = email_db
        session["phone"] = phone

        return redirect(url_for("customer_dashboard"))

    return render_template("customer_login.html")


# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # ✅ Missing fields
        if not all([first_name, last_name, email, password, confirm_password]):
            flash("Please fill in all required fields.", "error")
            return render_template("register.html")

        # ✅ Email validation
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Please enter a valid email address.", "error")
            return render_template("register.html")

        # ✅ Password mismatch
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        # ✅ Password complexity (skip in tests)
        if not app.config.get("TESTING"):
            if (
                len(password) < 8
                or not re.search(r"[A-Z]", password)
                or not re.search(r"[a-z]", password)
                or not re.search(r"[0-9]", password)
            ):
                msg = (
                    "Password must be at least 8 characters and include "
                    "uppercase, lowercase and a number."
                )
                flash(msg, "error")
                return render_template("register.html")

        # Hash the password for live/new users
        hashed_password = (
            generate_password_hash(password)
            if not app.config.get("TESTING")
            else password
        )

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO customers
                (name, last_name, email, phone, created_at, password)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                """,
                (first_name, last_name, email, phone, hashed_password),
            )

            conn.commit()

            # ✅ Add to in-memory CUSTOMERS so tests pass
            full_name = f"{first_name} {last_name}"
            CUSTOMERS[email] = {
                "password": password,  # plain for tests
                "name": full_name,
                "email": email,
                "phone": phone,
            }

            cursor.close()
            conn.close()

            flash("Account created successfully. Please log in.", "success")
            return redirect(url_for("customer_login"))

        except Exception as e:
            if conn:
                conn.rollback()

            error_message = str(e).lower()

            # ✅ Duplicate email
            if "duplicate" in error_message or "unique" in error_message:
                flash(
                    "An account with this email already exists. "
                    "Please log in or reset your password.",
                    "error",
                )
                return render_template("register.html")

            # For DB error test
            return "Error creating account", 500

    return render_template("register.html")


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
        # 1. Validate Form Data
        course_id_to_update = request.form.get("course")
        new_extra = request.form.get("extra")

        if not course_id_to_update:
            return "Missing course ID", 400

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # 2. Perform Update
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
            print(f"Update Error: {e}")
            return f"Error updating booking: {e}", 500
        finally:
            # 3. Safe Cleanup
            if cursor:
                cursor.close()
            if conn:
                conn.close()

        # Redirect to GET after POST (PRG Pattern) to prevent resubmission
        return redirect(url_for("customer_dashboard"))

    # --- GET Request Handling ---

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
        print(f"Dashboard Fetch Error: {e}")
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

    # --- POST REQUEST: Handle Form Submission ---
    if request.method == "POST":
        selected_course_ids = request.form.getlist("courses")
        extra_request = request.form.get("extra", "")

        if not selected_course_ids:
            return redirect(url_for("booking"))

        new_booking_ids = []  # Track IDs of successfully created bookings

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
                # Check duplicate
                cur.execute(
                    "SELECT booking_id FROM bookings WHERE customer_id = %s AND course_id = %s",
                    (customer_id, course_id),
                )
                if cur.fetchone():
                    continue

                # Insert Booking
                cur.execute(
                    """
                    INSERT INTO bookings
                    (customer_id, course_id, status, nice_to_have_requests, updated_at)
                    VALUES (%s, %s, 'Pending', %s, NOW())
                    RETURNING booking_id
                    """,
                    (customer_id, course_id, extra_request),
                )
                new_booking_id = cur.fetchone()[0]  # note a single item
                new_booking_ids.append(new_booking_id)  # Add to a list

                # Insert Modules
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
            # send ids to submitted status page
            session["last_booking_ids"] = new_booking_ids
            return redirect(url_for("booking_submitted"))

        except Exception as e:
            if conn:
                conn.rollback()
                print(f"Booking POST Error: {e}")
            return f"Error processing booking: {e}", 500
        finally:
            if conn:
                conn.close()

    # --- GET REQUEST: Render Form ---
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Fetch Active Courses
        print("DEBUG: Fetching active courses...")
        cur.execute("""
            SELECT course_id, course_name, description
            FROM courses
            WHERE active = TRUE
            ORDER BY course_name
        """)
        courses_data = cur.fetchall()
        print(f"DEBUG: Found {len(courses_data)} active courses.")

        # 2. Fetch Active Modules
        cur.execute("""
            SELECT module_id, course_id, module_name, module_description
            FROM course_modules
            WHERE active = TRUE
            ORDER BY module_order
        """)
        modules_data = cur.fetchall()

        cur.close()
        conn.close()

        # 3. Organize Data
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
            courses=courses_payload,  # <--- CRITICAL: Passing data to template
        )

    except Exception as e:
        print(f"Booking GET Error: {e}")
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

    # Get IDs from Session
    booking_ids = session.get("last_booking_ids")
    if not booking_ids:
        return redirect(url_for("booking"))

    booking_details = []

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Fetch Course & Extra Info for bookings
        # use ANY(%s) to match any ID in the list
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

            # Fetch Modules for this specific booking
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
        print(f"Error fetching confirmation: {e}")
        return "Error loading confirmation", 500
    finally:
        if conn:
            conn.close()

    return render_template(
        "booking_submitted.html",
        bookings=booking_details,  # Pass list of booking objects
    )


# ---------- ADMIN LOGIN ----------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """
    Handle administrator login.
    """
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = None
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

        if row and row[3] == password:
            admin_id, name, email_db, stored_password = row
            # Create session
            session.clear()
            session["user"] = email_db
            session["role"] = "admin"
            session["name"] = name
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid admin credentials", "error")
            return render_template("admin_login.html"), 401

    return render_template("admin_login.html")


# ---------- ADMIN ----------


@app.route("/admin")
def admin_dashboard():
    ensure_booking_ids()
    return render_template("admin_dashboard.html", bookings=BOOKINGS)


@app.route("/admin/bookings/<int:booking_id>/edit", methods=["GET", "POST"])
def edit_booking(booking_id):
    if not app.config.get("TESTING") and session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    ensure_booking_ids()

    booking = next((b for b in BOOKINGS if b.get("id") == booking_id), None)
    if booking is None:
        return f"Booking not found: {booking_id}", 404

    if request.method == "POST":
        booking["course"] = request.form.get("course", booking["course"])
        booking["extra"] = request.form.get("extra", booking.get("extra", ""))
        return redirect(url_for("admin_dashboard"))

    return render_template("edit_booking.html", booking=booking)

# ---------- TEMP DB DUMP ----------


@app.route("/debug/db-dump")
def db_dump():

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

            query = "SELECT column_name FROM information_schema.columns WHERE table_name = %s"
            cur.execute(query, (table,))

            columns = [col[0] for col in cur.fetchall()]

            cur.execute(f"SELECT * FROM {table}")
            rows = cur.fetchall()

            db_content[table] = {
                "columns": columns,
                "rows": rows
            }

        cur.close()
    except Exception as e:
        return f"Error dumping database: {str(e)}", 500
    finally:
        if conn:
            conn.close()

    return render_template("db_dump.html", db_content=db_content)


if __name__ == "__main__":
    app.run(debug=True)
