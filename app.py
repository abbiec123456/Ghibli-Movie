"""
Ghibli Movie Booking System

This Flask application provides a simple web interface for customers to log in,
view their personal details and bookings, and update extra requests for courses.

Note: This is a basic implementation with temporary in-memory data
"""

import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_wtf.csrf import CSRFProtect

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
    """
    Handle customer login.

    GET: Display the login form
    POST: Process login credentials and create session

    Returns:
        str: Rendered login template or redirect to dashboard
    """
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # Check if user exists and password matches
        if email in CUSTOMERS and CUSTOMERS[email]["password"] == password:
            session["user"] = email
            session["role"] = "customer"
            session["name"] = CUSTOMERS[email]["name"]
            session["email"] = CUSTOMERS[email]["email"]
            session["phone"] = CUSTOMERS[email]["phone"]

            return redirect(url_for("customer_dashboard"))

        return "Invalid login credentials"

    return render_template("customer_login.html")


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
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # Check passwords match
        if password != confirm_password:
            return "Passwords do not match"

        # Save new user
        CUSTOMERS[email] = {
            "password": password,
            "name": name,
            "email": email,
            "phone": "N/A",
        }

        return redirect(url_for("customer_login"))

    return render_template("register.html")


# ---------- CUSTOMER DASHBOARD ----------
@app.route("/dashboard", methods=["GET", "POST"])
def customer_dashboard():
    """
    Display customer dashboard with personal details and bookings.

    Allows customers to view their information and update booking extras.
    Requires authentication.

    Returns:
        str: Rendered dashboard template or redirect to login
    """
    if session.get("role") != "customer":
        return redirect(url_for("customer_login"))

    user_email = session.get("email")

    if request.method == "POST":
        course_to_update = request.form["course"]
        new_extra = request.form["extra"]

        for booking_item in BOOKINGS:
            if (
                booking_item["email"] == user_email
                and booking_item["course"] == course_to_update
            ):
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


# ---------- BOOKING PAGE ----------
@app.route("/book", methods=["GET", "POST"])
def booking():
    """
    Handle course booking.

    GET: Display the booking form
    POST: Process booking submission and store booking data

    Returns:
        str: Rendered booking template or redirect to confirmation
    """
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
            b["email"] == session["email"] and
            b["course"] == "Moving Castle Creations - 3D Animation"
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

    booking_data = session.get("last_booking")

    if not booking_data:
        return redirect(url_for("booking"))

    return render_template("booking_submitted.html", booking_data=booking_data,
                           module_labels=MODULE_LABELS)


# ---------- ADMIN ----------


@app.route("/admin")
def admin_dashboard():
    """
    Display admin dashboard.

    Returns:
        str: Rendered admin dashboard template
    """
    return render_template("admin_dashboard.html")


@app.route("/admin/bookings/<int:booking_id>/edit", methods=["GET", "POST"])
def edit_booking(booking_id):
    """
    Handle editing of bookings in admin panel.

    GET: Display the edit booking form
    POST: Process booking updates

    Args:
        booking_id (int): The ID of the booking to edit

    Returns:
        str: Rendered edit template or redirect to admin dashboard
    """
    if request.method == "POST":
        return redirect(url_for("admin_dashboard"))

    return render_template("edit_booking.html", booking_id=booking_id)

if __name__ == "__main__":
    app.run(debug=True)
    
    