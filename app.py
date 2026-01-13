from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "ghibli_secret_key"

# Temporary in-memory storage
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

# ---------- CUSTOMER LOGIN ----------
@app.route('/', methods=['GET', 'POST'])
def customer_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in CUSTOMERS and CUSTOMERS[username]['password'] == password:
            session['user'] = username
            session['name'] = CUSTOMERS[username]['name']
            session['email'] = CUSTOMERS[username]['email']
            session['phone'] = CUSTOMERS[username]['phone']
            session['role'] = 'customer'
            return redirect(url_for('customer_dashboard'))

        return "Invalid login credentials"

    return render_template('customer_login.html')


# ---------- CUSTOMER DASHBOARD ----------
@app.route('/dashboard', methods=['GET', 'POST'])
def customer_dashboard():
    if session.get('role') != 'customer':
        return redirect(url_for('customer_login'))

    user_email = session.get('email')

    # Update extra requests if form submitted
    if request.method == 'POST':
        course_to_update = request.form['course']
        new_extra = request.form['extra']
        # Find the booking and update it
        for booking in BOOKINGS:
            if booking['email'] == user_email and booking['course'] == course_to_update:
                booking['extra'] = new_extra
                break

    personal_details = {
        "name": session.get('name'),
        "email": session.get('email'),
        "phone": session.get('phone')
    }

    user_bookings = [b for b in BOOKINGS if b['email'] == user_email]

    return render_template(
        'customer_dashboard.html',
        personal_details=personal_details,
        bookings=user_bookings
    )


# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('customer_login'))


if __name__ == '__main__':
    app.run(debug=True)
