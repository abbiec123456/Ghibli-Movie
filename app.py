import os
import psycopg2
from urllib.parse import urlparse
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "ghibli_secret_key")

if app.config["SECRET_KEY"] == "ghibli_secret_key" and not app.debug:
    raise ValueError("No SECRET_KEY set !")

csrf = CSRFProtect(app)

# ---------- TEMPORARY IN-MEMORY STORAGE ----------
ABBIE_EMAIL = "abbie@example.com"

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
        "email": ABBIE_EMAIL,
        "course": "Moving Castle Creations – 3D Animation",
        "extra": "Beginner friendly tools",
    },
    {"email": ABBIE_EMAIL, "course": "Totoro Character Design", "extra": ""},
]

MODULE_LABELS = {
    "module1": "Introduction to 3D Animation",
    "module2": "Character Design Basics",
    "module3": "Environmental Modelling",
}


# ---------- DATABASE CONNECTION ----------
def get_db_connection():
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


# ---------- APP CONFIG ----------
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_DEBUG", "1") == "0"


# ---------- ROUTES ----------

@app.route("/")
def index():
    return render_template("index.html")


# ---------- CUSTOMER LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def customer_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

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
            cur.close()
            conn.close()
        except Exception:
            flash("Invalid login credentials", "error")
            return render_template("customer_login.html")

        if not row:
            flash("Invalid login credentials", "error")
            return render_template("customer_login.html")

        customer_id, first_name, last_name, email_db, phone, s_password = row

        if s_password != password:
            flash("Invalid login credentials", "error")
            return render_template("customer_login.html")

        name = f"{first_name} {last_name}"
        CUSTOMERS[email_db] = {
            "password": s_password,
            "name": name,
            "email": email_db,
            "phone": phone,
        }

        session["user"] = email_db
        session["role"] = "customer"
        session["name"] = name
        session["email"] = email_db
        session["phone"] = phone

        return redirect(url_for("customer_dashboard"))

    return render_template("customer_login.html")


# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        name = f"{first_name} {last_name}"
        email = request.form["email"]
        phone = request.form["phone"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # Password match validation
        if password != confirm_password:
            flash("Passwords do not match", "error")
            return render_template("register.html")

        # Save in memory
        CUSTOMERS[email] = {
            "password": password,
            "name": name,
            "email": email,
            "phone": phone or "N/A",
        }

        # Insert into DB
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO customers (name, last_name, email, phone, created_at, password)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                """,
                (first_name, last_name, email, phone, password),
            )
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            flash(f"Error creating account: {e}", "error")
            return render_template("register.html")

        # SUCCESS
        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for("customer_login"))

    return render_template("register.html")


# ---------- DASHBOARD ----------
@app.route("/dashboard", methods=["GET", "POST"])
def customer_dashboard():
    if session.get("role") != "customer":
        return redirect(url_for("customer_login"))

    user_email = session.get("email")

    if request.method == "POST":
        course_id_to_update = request.form.get("course")
        new_extra = request.form.get("extra")
        if not course_id_to_update:
            flash("Missing course ID", "error")
            return redirect(url_for("customer_dashboard"))

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE bookings
                SET nice_to_have_requests = %s, updated_at = NOW()
                FROM customers c
                WHERE bookings.customer_id = c.customer_id
                AND c.email = %s
                AND bookings.course_id = %s
                """,
                (new_extra, user_email, course_id_to_update),
            )
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            flash(f"Error updating booking: {e}", "error")
            return redirect(url_for("customer_dashboard"))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

        return redirect(url_for("customer_dashboard"))

    personal_details = {
        "name": session.get("name"),
        "email": session.get("email"),
        "phone": session.get("phone"),
    }

    user_bookings = []
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
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
            """,
            (user_email,),
        )
        rows = cursor.fetchall()
        for row in rows:
            user_bookings.append({
                "booking_id": row[0],
                "course_id": row[1],
                "extra": row[2],
                "status": row[3],
                "course": row[4],
                "description": row[5],
            })
    except Exception as e:
        flash(f"Error fetching dashboard: {e}", "error")
        return render_template("customer_dashboard.html", personal_details=personal_details, bookings=[])
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
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("customer_login"))


if __name__ == "__main__":
    app.run(debug=True)
