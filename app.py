"""
Ghibli Movie Booking System

This Flask application provides a simple web interface for customers to log in,
view their personal details and bookings, and update extra requests for courses.

Note: This is a basic implementation with temporary in-memory data.
"""

from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "ghibli_secret_key"

# ---------- TEMPORARY IN-MEMORY STORAGE ----------
CUSTOMERS = {
    "abbie@example.com": {
        "password": "group1",
        "name": "Abbie Smith",
        "email": "abbie@example.com",
        "phone": "123-456-7890"
    }
}

BOOKINGS = [
    {
        "email": "abbie@example.com",
        "course": "Moving Castle Creations – 3D Animation",
        "extra": "Beginner friendly tools"
    },
    {
        "email": "abbie@example.com",
        "course": "Totoro Character Design",
        "extra": ""
    }
]


# ---------- LANDING PAGE ----------
@app.route("/")
def index():
    return render_template("index.html")


# ---------- CUSTOMER LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def customer_login():
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
            "phone": "N/A"
        }

        return redirect(url_for("customer_login"))

    return render_template("register.html")


# ---------- CUSTOMER DASHBOARD ----------
@app.route("/dashboard", methods=["GET", "POST"])
def customer_dashboard():
    if session.get("role") != "customer":
        return redirect(url_for("customer_login"))

    user_email = session.get("email")

    if request.method == "POST":
        course_to_update = request.form["course"]
        new_extra = request.form["extra"]

        for booking in BOOKINGS:
            if booking["email"] == user_email and booking["course"] == course_to_update:
                booking["extra"] = new_extra
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
    session.clear()
    return redirect(url_for("customer_login"))


# ---------- BOOKING PAGE ----------
@app.route("/book", methods=["GET", "POST"])
def booking():
    if session.get("role") != "customer":
        return redirect(url_for("customer_login"))

    if request.method == "POST":
        selected_modules = request.form.getlist("modules")
        extra = request.form.get("extra", "")

        BOOKINGS.append({
            "email": session.get("email"),
            "course": "Moving Castle Creations - 3D Animation",
            "modules": selected_modules,
            "extra": extra
        })

        return redirect(url_for("customer_dashboard"))

    return render_template(
        "booking.html",
        user={
            "name": session.get("name"),
            "email": session.get("email"),
            "phone": session.get("phone")
        }
    )


# ---------- ADMIN ----------

@app.route("/admin")
def admin_dashboard():
    return render_template("admin_dashboard.html")


@app.route("/admin/bookings/<int:booking_id>/edit", methods=["GET", "POST"])
def edit_booking(booking_id):
    if request.method == "POST":
        return redirect(url_for("admin_dashboard"))
    return render_template("edit_booking.html")


if __name__ == "__main__":
    app.run(debug=True)
