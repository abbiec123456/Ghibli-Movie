"""
Ghibli Movie Booking System

This Flask application provides a simple web interface for customers to log in,
view their personal details and bookings, and update extra requests for courses.
It uses in-memory storage for demonstration purposes.

Features:
- Customer login with shared password authentication
- Dashboard to view personal details and bookings
- Ability to update extra requests for bookings
- Session-based authentication

Note: This is a basic implementation with temporary in-memory data.
In a production environment, use a proper database and secure password handling.
"""

from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "ghibli_secret_key"

# ---------- TEMPORARY IN-MEMORY STORAGE ----------

CUSTOMERS = {
    "abbie": {
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

SHARED_PASSWORD = "group1"


# ---------- CUSTOMER LOGIN ----------

@app.route("/", methods=["GET", "POST"])
def customer_login():
    """
    Handle customer login page.

    GET: Render the login form.
    POST: Validate password and create session.
    """
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if password == SHARED_PASSWORD:
            session["user"] = username
            session["role"] = "customer"

            # Load predefined user or create demo user
            if username in CUSTOMERS:
                session["name"] = CUSTOMERS[username]["name"]
                session["email"] = CUSTOMERS[username]["email"]
                session["phone"] = CUSTOMERS[username]["phone"]
            else:
                session["name"] = username.title()
                session["email"] = f"{username}@example.com"
                session["phone"] = "N/A"

            return redirect(url_for("customer_dashboard"))

        return "Invalid login credentials"

    return render_template("customer_login.html")


# ---------- CUSTOMER DASHBOARD ----------

@app.route("/dashboard", methods=["GET", "POST"])
def customer_dashboard():
    """
    Display customer dashboard.

    Shows personal details and subscribed courses.
    Allows updating extra requests only.
    """
    if session.get("role") != "customer":
        return redirect(url_for("customer_login"))

    user_email = session.get("email")

    # Update extra requests
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
    """Clear user session and log out."""
    session.clear()
    return redirect(url_for("customer_login"))

@app.route('/book')
def booking():
    return render_template("booking.html")

if __name__ == "__main__":
    app.run(debug=True)
