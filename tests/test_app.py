"""
Unit Tests for Ghibli Movie Booking System

This test suite provides comprehensive coverage for the Flask application,
testing all routes, authentication, booking functionality, and edge cases.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add the parent directory to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


try:
    from app import app, CUSTOMERS, BOOKINGS
except ImportError:
    # Try alternative import paths
    try:
        from main import app, CUSTOMERS, BOOKINGS
    except ImportError:
        # If running from tests directory
        sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
        from app import app, CUSTOMERS, BOOKINGS


class GhibliBookingSystemTests(unittest.TestCase):
    """Test suite for the Ghibli Movie Booking System"""

    def setUp(self):
        """Set up test client and reset data before each test"""
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()

        # Reset test data
        CUSTOMERS.clear()
        CUSTOMERS.update(
            {
                "abbie@example.com": {
                    "password": "group1",
                    "name": "Abbie Smith",
                    "email": "abbie@example.com",
                    "phone": "123-456-7890",
                }
            }
        )

        BOOKINGS.clear()
        BOOKINGS.extend(
            [
                {
                    "email": "abbie@example.com",
                    "course": "Moving Castle Creations – 3D Animation",
                    "extra": "Beginner friendly tools",
                },
                {
                    "email": "abbie@example.com",
                    "course": "Totoro Character Design",
                    "extra": "",
                },
            ]
        )

    def tearDown(self):
        """Clean up after each test"""
        CUSTOMERS.clear()
        BOOKINGS.clear()

    # ---------- LANDING PAGE TESTS ----------

    def test_index_page_loads(self):
        """Test that the landing page loads successfully"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    # ---------- CUSTOMER LOGIN TESTS ----------

    def test_login_page_loads(self):
        """Test that the login page loads successfully"""
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)

    def test_successful_login(self):
        """Test successful customer login"""
        response = self.client.post(
            "/login",
            data={"email": "abbie@example.com", "password": "group1"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        with self.client.session_transaction() as sess:
            self.assertEqual(sess["user"], "abbie@example.com")
            self.assertEqual(sess["role"], "customer")
            self.assertEqual(sess["name"], "Abbie Smith")
            self.assertEqual(sess["email"], "abbie@example.com")
            self.assertEqual(sess["phone"], "123-456-7890")

    def test_login_with_invalid_email(self):
        """Test login with non-existent email"""
        response = self.client.post(
            "/login", data={"email": "nonexistent@example.com", "password": "wrongpass"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid login credentials", response.data)

    def test_login_with_invalid_password(self):
        """Test login with correct email but wrong password"""
        response = self.client.post(
            "/login", data={"email": "abbie@example.com", "password": "wrongpassword"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid login credentials", response.data)

    # ---------- REGISTRATION TESTS ----------

    def test_register_page_loads(self):
        """Test that the registration page loads successfully"""
        response = self.client.get("/register")
        self.assertEqual(response.status_code, 200)

    @patch('app.get_db_connection')
    def test_successful_registration(self, mock_db):
        """Test successful new user registration"""
        # Mock the database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        response = self.client.post(
            "/register",
            data={
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "phone": "N/A",
                "password": "password123",
                "confirm_password": "password123",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        # Verify database insert was called
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        self.assertIn("john@example.com", CUSTOMERS)
        self.assertEqual(CUSTOMERS["john@example.com"]["name"], "John Doe")
        self.assertEqual(CUSTOMERS["john@example.com"]["password"], "password123")
        self.assertEqual(CUSTOMERS["john@example.com"]["phone"], "N/A")

    def test_registration_password_mismatch(self):
        """Test registration with mismatched passwords"""
        response = self.client.post(
            "/register",
            data={
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane@example.com",
                "phone": "N/A",
                "password": "password123",
                "confirm_password": "password456",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Passwords do not match", response.data)
        self.assertNotIn("jane@example.com", CUSTOMERS)

    # ---------- CUSTOMER DASHBOARD TESTS ----------

    def test_dashboard_requires_authentication(self):
        """Test that dashboard redirects unauthenticated users"""
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/login"))

    def test_dashboard_loads_for_authenticated_user(self):
        """Test that dashboard loads for authenticated users"""
        # Login first
        self.client.post(
            "/login", data={"email": "abbie@example.com", "password": "group1"}
        )

        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)

    def test_dashboard_shows_user_bookings(self):
        """Test that dashboard displays user's bookings"""
        # Login first
        self.client.post(
            "/login", data={"email": "abbie@example.com", "password": "group1"}
        )

        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
    @patch('app.get_db_connection')
    def test_update_booking_extra_request(self, mock_db):
        """Test updating extra request for a booking"""
        # Mock the database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock the SELECT query result (for displaying dashboard)
        mock_cursor.fetchall.return_value = [
            (1, 5, "Beginner friendly tools", "confirmed", "Moving Castle Creations – 3D Animation", "Learn 3D animation")
        ]

        # Login first
        self.client.post(
            "/login", data={"email": "abbie@example.com", "password": "group1"}
        )

        response = self.client.post(
            "/dashboard",
            data={
                "course": "5",
                "extra": "Updated extra request",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        # update should execute to query and parameters for assert
        update_call = mock_cursor.execute.call_args_list[0]
        query, params = update_call[0]

        # Check that the booking was updated
        self.assertIn("UPDATE bookings", query)
        self.assertEqual(params[0], "Updated extra request") # extra field data
        self.assertEqual(params[1], "abbie@example.com") # email
        self.assertEqual(params[2], "5")

        mock_conn.commit.assert_called()

    # ---------- LOGOUT TESTS ----------

    def test_logout_clears_session(self):
        """Test that logout clears the session"""
        # Login first
        self.client.post(
            "/login", data={"email": "abbie@example.com", "password": "group1"}
        )

        # Then logout
        response = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        with self.client.session_transaction() as sess:
            self.assertNotIn("user", sess)
            self.assertNotIn("role", sess)

    # ---------- BOOKING PAGE TESTS ----------

    def test_booking_page_requires_authentication(self):
        """Test that booking page redirects unauthenticated users"""
        response = self.client.get("/book")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/login"))

    def test_booking_page_loads_for_authenticated_user(self):
        """Test that booking page loads for authenticated users"""
        # Login first
        self.client.post(
            "/login", data={"email": "abbie@example.com", "password": "group1"}
        )

        response = self.client.get("/book")
        self.assertEqual(response.status_code, 200)

    def test_create_new_booking(self):
        """Test creating a new booking"""
        # Login first
        self.client.post(
            "/login", data={"email": "abbie@example.com", "password": "group1"}
        )

        initial_booking_count = len(BOOKINGS)

        response = self.client.post(
            "/book",
            data={"modules": ["Module 1", "Module 2"], "extra": "Special request here"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(BOOKINGS), initial_booking_count + 1)

        # Check the new booking
        new_booking = BOOKINGS[-1]
        self.assertEqual(new_booking["email"], "abbie@example.com")
        self.assertEqual(
            new_booking["course"], "Moving Castle Creations - 3D Animation"
        )
        self.assertEqual(new_booking["modules"], ["Module 1", "Module 2"])
        self.assertEqual(new_booking["extra"], "Special request here")

    def test_create_booking_without_modules(self):
        """Test creating a booking without selecting modules"""
        # Login first
        self.client.post(
            "/login", data={"email": "abbie@example.com", "password": "group1"}
        )

        response = self.client.post(
            "/book", data={"extra": "Just extra request"}, follow_redirects=True
        )

        self.assertEqual(response.status_code, 200)

        # Check the new booking
        new_booking = BOOKINGS[-1]
        self.assertEqual(new_booking["modules"], [])

    # ---------- BOOKING SUBMITTED TESTS ----------

    def test_booking_submitted_requires_authentication(self):
        """Test that booking submitted page redirects unauthenticated users"""
        response = self.client.get("/booking-submitted")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/login"))

    def test_booking_submitted_redirects_without_booking(self):
        """Test redirect when accessing submitted page without a booking"""
        # Login first
        self.client.post(
            "/login", data={"email": "abbie@example.com", "password": "group1"}
        )

        response = self.client.get("/booking-submitted")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/book"))

    def test_booking_submitted_shows_booking(self):
        """Test that booking submitted page shows the booking details"""
        # Login and create a booking
        self.client.post(
            "/login", data={"email": "abbie@example.com", "password": "group1"}
        )

        self.client.post(
            "/book", data={"modules": ["Module 1"], "extra": "Test request"}
        )

        response = self.client.get("/booking-submitted")
        self.assertEqual(response.status_code, 200)

    # ---------- ADMIN TESTS ----------

    def test_admin_dashboard_loads(self):
        """Test that admin dashboard loads"""
        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 200)

    def test_edit_booking_page_loads(self):
        """Test that edit booking page loads"""
        response = self.client.get("/admin/bookings/1/edit")
        self.assertEqual(response.status_code, 200)

    def test_edit_booking_post_redirects(self):
        """Test that posting to edit booking redirects to admin dashboard"""
        response = self.client.post("/admin/bookings/1/edit")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/admin"))

    # ---------- INTEGRATION TESTS ----------
    @patch('app.get_db_connection')
    def test_full_user_journey(self, mock_db):
        """Test complete user journey: register, login, book, view dashboard"""
        # Mock the database
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        # 1. Register
        self.client.post(
            "/register",
            data={
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com",
                "phone": "N/A",
                "password": "testpass",
                "confirm_password": "testpass",
            },
        )

        # 2. Login
        self.client.post(
            "/login", data={"email": "test@example.com", "password": "testpass"}
        )

        # 3. Create booking
        self.client.post(
            "/book",
            data={"modules": ["Intro to Animation"], "extra": "First time booking"},
        )

        # 4. View dashboard
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)

        # 5. Logout
        self.client.get("/logout")

        # 6. Verify can't access dashboard after logout
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 302)


class SessionManagementTests(unittest.TestCase):
    """Test suite for session management"""

    def setUp(self):
        """Set up test client"""
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        # Reset test data
        CUSTOMERS.clear()
        CUSTOMERS.update(
            {
                "test@example.com": {
                    "password": "testpass",
                    "name": "Test User",
                    "email": "test@example.com",
                    "phone": "000-000-0000",
                }
            }
        )

    def test_session_persists_across_requests(self):
        """Test that session data persists across multiple requests"""
        # Login
        self.client.post(
            "/login", data={"email": "test@example.com", "password": "testpass"}
        )

        # Make multiple requests
        response1 = self.client.get("/dashboard")
        response2 = self.client.get("/book")
        response3 = self.client.get("/dashboard")

        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response3.status_code, 200)

    def test_multiple_users_sessions_isolated(self):
        """Test that different users have isolated sessions"""
        # Add another user
        CUSTOMERS["user2@example.com"] = {
            "password": "pass2",
            "name": "User Two",
            "email": "user2@example.com",
            "phone": "111-111-1111",
        }

        # Create two clients
        client1 = self.app.test_client()
        client2 = self.app.test_client()

        # Login with different users
        client1.post(
            "/login", data={"email": "test@example.com", "password": "testpass"}
        )

        client2.post("/login", data={"email": "user2@example.com", "password": "pass2"})

        # Verify sessions are separate
        with client1.session_transaction() as sess:
            self.assertEqual(sess["email"], "test@example.com")

        with client2.session_transaction() as sess:
            self.assertEqual(sess["email"], "user2@example.com")


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
