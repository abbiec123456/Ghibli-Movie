"""
Ghibli Movie Booking System

This Flask application provides a simple web interface for customers to log in,
view their personal details and bookings, and update extra requests for courses.

Note: This is a basic implementation with temporary in-memory data.
"""

import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_wtf.csrf import CSRFProtect


# =========================================================
# Dummy DB connection (required for unit test patching)
# =========================================================
def get_db_connection():
    """
    Dummy DB connection for unit tests.
    Required because tests patch app.get_db_connection.
    """
    from unittest.mock import MagicMock

    class DummyConn:
        def cursor(self):
            return MagicMock()

        def commit(self):
            pass

        def close(self):
            pass

    return DummyConn()


# =========================================================
# App setup
# =========================================================
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "ghibli_secret_key")

if app.config["SECRET_KEY"] == "ghibli_secret_key" and not app.debug:
    raise ValueError("No SECRET_KEY set !")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_DEBUG", "1") == "0"

csrf = CSRFProtect(app)


# =========================================================
# In-memory data
# =========================================================
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


# =========================================================
# Routes
# =========================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def customer_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        if email in CUSTOMERS and CUSTOMERS[email]["password"] == password:
            session["user"] = email
            session["role"] = "customer"
            session["name"] = CUSTOMERS[email]["name"]
            session["email"] = CUSTOMERS[email]["email"]
            session["phone"] = CUSTOMERS[email]["phone"]
            return redirect(url_for("customer_dashboard"))

        return "Invalid login credentials"

    return render_template("customer_login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Accept either 'name' or first/last name
        name = request.form.get("name")
        if not name:
            first = request.form.get("first_name", "")
            last = request.form.get("last_name", "")
            name = f"{first} {last}".strip()

        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            return "Passwords do not match"

        CUSTOMERS[email] = {
            "password": password,
            "name": name,
            "email": email,
            "phone": request.form.get("phone", "N/A"),
        }

        return redirect(url_for("customer_login"))

    return render_template("register.html")


@app.route("/dashboard", methods=["GET", "POST"])
def customer_dashboard():
    if session.get("role") != "customer":
        return redirect(url_for("customer_login"))

    user_email = session.get("email")

    if request.method == "POST":
        course_to_update = request.form["course"]
        new_extra = request.form["extra"]

        for booking_item in BOOKINGS:
            if booking_item["email"] == user_email and booking_item["course"] == course_to_update:
                booking_item["extra"] = new_extra
                break

    personal_details = {
        "name": session.get("name"),
        "email": session.get("email"),
        "phone": session.get("phone"),
    }

    user_bookings = [b for b in BOOKINGS if b["email"] == user_email]

    return render_template(
        "customer_dashboard.html",
        personal_details=personal_details,
        bookings=user_bookings,
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("customer_login"))


@app.route("/book", methods=["GET", "POST"])
def booking():
    if session.get("role") != "customer":
        return redirect(url_for("customer_login"))

    if request.method == "POST":
        selected_modules = request.form.getlist("modules")
        extra = request.form.get("extra", "")

        booking_data = {
            "email": session.get("email"),
            "course": "Moving Castle Creations - 3D Animation",
            "modules": selected_modules,
            "extra": extra,
        }

        already_booked = any(
            b["email"] == session["email"]
            and b["course"] == "Moving Castle Creations - 3D Animation"
            for b in BOOKINGS
        )

        if already_booked:
            return redirect(url_for("customer_dashboard"))

        BOOKINGS.append(booking_data)
        session["last_booking"] = booking_data
        return redirect(url_for("booking_submitted"))

    return render_template(
        "booking.html",
        user={
            "name": session.get("name"),
            "email": session.get("email"),
            "phone": session.get("phone"),
        },
    )


@app.route("/booking-submitted")
def booking_submitted():
    if session.get("role") != "customer":
        return redirect(url_for("customer_login"))

    booking_data = session.get("last_booking")
    if not booking_data:
        return redirect(url_for("booking"))

    return render_template(
        "booking_submitted.html",
        booking_data=booking_data,
        module_labels=MODULE_LABELS,
    )


@app.route("/admin")
def admin_dashboard():
    return render_template("admin_dashboard.html")


@app.route("/admin/bookings/<int:booking_id>/edit", methods=["GET", "POST"])
def edit_booking(booking_id):
    if request.method == "POST":
        return redirect(url_for("admin_dashboard"))

    return render_template("edit_booking.html", booking_id=booking_id)


if __name__ == "__main__":
    app.run(debug=True)
