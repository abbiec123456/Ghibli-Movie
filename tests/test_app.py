"""
Unit Tests for Ghibli Movie Booking System

Comprehensive coverage including:
- Customer and admin authentication (plain-text and hashed passwords)
- All CRUD operations for bookings and customers
- Error paths and edge cases
- Session management and isolation
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from werkzeug.security import generate_password_hash
from app import app

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class GhibliBookingSystemTests(unittest.TestCase):
    """Main test suite for the Ghibli Movie Booking System"""

    def setUp(self):
        """Set up test client and global DB mock before each test"""
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()

        patcher = patch("app.get_db_connection")
        self.addCleanup(patcher.stop)
        self.mock_db = patcher.start()

        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.return_value = self.mock_conn
        self.mock_conn.cursor.return_value = self.mock_cursor

        # Default: a valid plain-text-password customer row
        self.mock_cursor.fetchone.return_value = (
            4, "Abbie", "Smith", "abbie@example.com", "123-456-7890", "group1"
        )

    def _login_as_customer(self, email="abbie@example.com", password="group1"):
        """Helper: log in as a customer."""
        return self.client.post(
            "/login", data={"email": email, "password": password}
        )

    def _set_admin_session(self):
        """Helper: directly inject an admin session."""
        with self.client.session_transaction() as sess:
            sess["role"] = "admin"
            sess["user"] = "admin@example.com"
            sess["name"] = "Admin"

    # =========================================================================
    # LANDING PAGE
    # =========================================================================

    def test_index_page_loads(self):
        """Landing page returns 200"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    # =========================================================================
    # CUSTOMER LOGIN
    # =========================================================================

    def test_login_page_loads(self):
        """Login page returns 200"""
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)

    @patch("app.get_db_connection")
    def test_login_plain_text_password(self, mock_db):
        """Login succeeds with a legacy plain-text password"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (
            4, "Abbie", "Smith", "abbie@example.com", "123-456-7890", "group1"
        )

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

    @patch("app.get_db_connection")
    def test_login_hashed_password(self, mock_db):
        """Login succeeds with a werkzeug-hashed password"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        hashed = generate_password_hash("mypassword")
        mock_cursor.fetchone.return_value = (
            5, "John", "Doe", "john@example.com", "555-1234", hashed
        )

        response = self.client.post(
            "/login",
            data={"email": "john@example.com", "password": "mypassword"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["user"], "john@example.com")
            self.assertEqual(sess["role"], "customer")

    @patch("app.get_db_connection")
    def test_login_invalid_email(self, mock_db):
        """Login fails when email is not found"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        response = self.client.post(
            "/login",
            data={"email": "nonexistent@example.com", "password": "wrongpass"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid login credentials", response.data)
        with self.client.session_transaction() as sess:
            self.assertNotIn("user", sess)

    @patch("app.get_db_connection")
    def test_login_invalid_password(self, mock_db):
        """Login fails when password is wrong"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (
            4, "Abbie", "Smith", "abbie@example.com", "123-456-7890", "correctpwd"
        )

        response = self.client.post(
            "/login",
            data={"email": "abbie@example.com", "password": "wrongpassword"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid login credentials", response.data)
        with self.client.session_transaction() as sess:
            self.assertNotIn("user", sess)
            self.assertNotIn("role", sess)

    @patch("app.get_db_connection")
    def test_login_db_exception(self, mock_db):
        """Login returns 401 when DB raises an exception"""
        mock_db.side_effect = Exception("DB Error")

        response = self.client.post(
            "/login", data={"email": "test@example.com", "password": "pass"}
        )

        self.assertEqual(response.status_code, 401)
        self.assertIn(b"Invalid login credentials", response.data)

    @patch("app.get_db_connection")
    def test_login_plain_text_rehash_db_error(self, mock_db):
        """Login still succeeds even when the rehash DB update fails"""
        # First call: main SELECT succeeds; second call: rehash connection fails
        mock_conn_main = MagicMock()
        mock_cursor_main = MagicMock()
        mock_cursor_main.fetchone.return_value = (
            4, "Abbie", "Smith", "abbie@example.com", "123-456-7890", "group1"
        )
        mock_conn_main.cursor.return_value = mock_cursor_main

        mock_db.side_effect = [mock_conn_main, Exception("Rehash DB fail")]

        response = self.client.post(
            "/login",
            data={"email": "abbie@example.com", "password": "group1"},
            follow_redirects=True,
        )

        # Login should still succeed — rehash failure is non-fatal
        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["role"], "customer")

    # =========================================================================
    # REGISTRATION
    # =========================================================================

    def test_register_page_loads(self):
        """Registration page returns 200"""
        response = self.client.get("/register")
        self.assertEqual(response.status_code, 200)

    @patch("app.get_db_connection")
    def test_register_success(self, mock_db):
        """Successful registration inserts to DB and redirects to login"""
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
                "phone": "555-1234",
                "password": "password123",
                "confirm_password": "password123",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    def test_register_missing_fields(self):
        """Registration fails with missing required fields"""
        response = self.client.post(
            "/register",
            data={
                "first_name": "John",
                "last_name": "Doe",
                "email": "",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
        )
        self.assertIn(b"required", response.data.lower())

    def test_register_invalid_email_format(self):
        """Registration fails when email format is invalid"""
        response = self.client.post(
            "/register",
            data={
                "first_name": "John",
                "last_name": "Doe",
                "email": "notanemail",
                "password": "password123",
                "confirm_password": "password123",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"valid email", response.data.lower())

    def test_register_password_mismatch(self):
        """Registration fails when passwords do not match"""
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
        self.mock_cursor.execute.assert_not_called()

    def test_register_password_too_short(self):
        """Registration fails when password is too short"""
        response = self.client.post(
            "/register",
            data={
                "first_name": "John",
                "last_name": "Doe",
                "email": "test@example.com",
                "password": "123",
                "confirm_password": "123",
            },
        )
        self.assertIn(b"password", response.data.lower())

    @patch("app.get_db_connection")
    def test_register_duplicate_email(self, mock_db):
        """Registration fails with a friendly message on duplicate email"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception(
            "duplicate key value violates unique constraint"
        )

        response = self.client.post(
            "/register",
            data={
                "first_name": "Dup",
                "last_name": "User",
                "email": "existing@example.com",
                "phone": "555-1234",
                "password": "password123",
                "confirm_password": "password123",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"already exists", response.data)

    @patch("app.get_db_connection")
    def test_register_db_error(self, mock_db):
        """Registration returns 500 on unexpected DB failure"""
        mock_db.side_effect = Exception("DB Fail")

        response = self.client.post(
            "/register",
            data={
                "first_name": "Fail",
                "last_name": "User",
                "email": "fail@example.com",
                "phone": "N/A",
                "password": "ValidPassword123!",
                "confirm_password": "ValidPassword123!",
            },
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Error creating account", response.data)

    # =========================================================================
    # CUSTOMER DASHBOARD
    # =========================================================================

    def test_dashboard_requires_authentication(self):
        """Dashboard redirects unauthenticated users to login"""
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/login"))

    def test_dashboard_loads_for_authenticated_user(self):
        """Dashboard returns 200 for logged-in customer"""
        self._login_as_customer()
        self.mock_cursor.fetchall.return_value = []
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)

    def test_dashboard_update_missing_course_id(self):
        """POST to dashboard without course ID returns 400"""
        self._login_as_customer()
        response = self.client.post("/dashboard", data={"extra": "No course id"})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Missing course ID", response.data)

    @patch("app.get_db_connection")
    def test_update_booking_extra_request(self, mock_db):
        """Dashboard POST updates extra request with correct SQL parameters"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = (
            1, "Abbie", "Smith", "abbie@example.com", "123-456-7890", "group1"
        )
        mock_cursor.fetchall.return_value = [
            (1, 5, "", "confirmed", "Moving Castle Creations", "Learn animation")
        ]

        self.client.post(
            "/login", data={"email": "abbie@example.com", "password": "group1"}
        )

        response = self.client.post(
            "/dashboard",
            data={"course": "5", "extra": "Updated extra request"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        update_call = None
        for c in mock_cursor.execute.call_args_list:
            if "UPDATE bookings" in c[0][0]:
                update_call = c
                break

        self.assertIsNotNone(update_call, "UPDATE query was not executed")
        _, params = update_call[0]
        self.assertEqual(params[0], "Updated extra request")
        self.assertEqual(params[1], "abbie@example.com")
        self.assertEqual(params[2], "5")

        mock_conn.commit.assert_called()

    @patch("app.get_db_connection")
    def test_dashboard_post_db_exception(self, mock_db):
        """Dashboard POST returns 500 when the UPDATE query fails"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (
            4, "Abbie", "Smith", "abbie@example.com", "123-456-7890", "group1"
        )

        # Login succeeds, then make the next DB call fail for the POST
        self.client.post(
            "/login", data={"email": "abbie@example.com", "password": "group1"}
        )
        mock_db.side_effect = Exception("DB Update Error")

        response = self.client.post(
            "/dashboard",
            data={"course": "5", "extra": "Will fail"},
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Error updating booking", response.data)

    @patch("app.get_db_connection")
    def test_dashboard_get_db_exception(self, mock_db):
        """Dashboard GET returns 500 when the SELECT query fails"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (
            4, "Abbie", "Smith", "abbie@example.com", "123-456-7890", "group1"
        )

        self.client.post(
            "/login", data={"email": "abbie@example.com", "password": "group1"}
        )
        mock_db.side_effect = Exception("DB Fetch Error")

        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Error fetching dashboard", response.data)

    # =========================================================================
    # LOGOUT
    # =========================================================================

    def test_logout_clears_session(self):
        """Logout clears all session data"""
        self._login_as_customer()
        response = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertNotIn("user", sess)
            self.assertNotIn("role", sess)

    # =========================================================================
    # BOOKING PAGE
    # =========================================================================

    def test_booking_requires_authentication(self):
        """Booking page redirects unauthenticated users"""
        response = self.client.get("/book")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/login"))

    def test_booking_page_loads_for_authenticated_user(self):
        """Booking page returns 200 for logged-in customer"""
        self._login_as_customer()
        self.mock_cursor.fetchall.side_effect = [
            [(1, "Course 1", "Desc 1")],
            [(10, 1, "Module A", "Desc A")],
        ]
        response = self.client.get("/book")
        self.assertEqual(response.status_code, 200)

    def test_booking_page_renders_course_content(self):
        """Booking page actually renders course data from DB"""
        self._login_as_customer()
        self.mock_cursor.fetchall.side_effect = [
            [(1, "Spirited Away Workshop", "A great course")],
            [(10, 1, "Module A", "Desc A")],
        ]
        response = self.client.get("/book")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Spirited Away Workshop", response.data)

    def test_booking_without_courses_redirects(self):
        """Booking POST with no courses selected redirects back to booking"""
        self._login_as_customer()
        response = self.client.post("/book", data={"courses": []})
        self.assertEqual(response.status_code, 302)

    def test_create_new_booking(self):
        """Booking POST creates a booking and sets session IDs"""
        self._login_as_customer()

        self.mock_cursor.fetchone.side_effect = [
            (4,),    # customer_id
            None,    # no duplicate
            (999,),  # new booking_id
        ]

        response = self.client.post(
            "/book",
            data={
                "courses": ["1"],
                "modules_1": ["10", "11"],
                "extra": "Special request",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["last_booking_ids"], [999])

    def test_create_booking_without_modules(self):
        """Booking POST without modules still succeeds"""
        self._login_as_customer()
        self.mock_cursor.fetchone.side_effect = [(4,), None, (888,)]

        response = self.client.post(
            "/book",
            data={"courses": ["2"], "extra": "No modules"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["last_booking_ids"], [888])

    def test_booking_post_customer_not_found(self):
        """Booking POST redirects to login when customer record is not in DB"""
        self._login_as_customer()

        # fetchone returns None — customer lookup finds nothing
        self.mock_cursor.fetchone.side_effect = [None]

        response = self.client.post(
            "/book",
            data={"courses": ["1"], "extra": "test"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)

    def test_booking_post_duplicate_skipped(self):
        """Booking POST silently skips a course the customer already booked"""
        self._login_as_customer()

        # customer_id found, then duplicate check returns an existing booking_id
        self.mock_cursor.fetchone.side_effect = [
            (4,),   # customer_id
            (55,),  # duplicate found — should continue (skip)
        ]

        response = self.client.post(
            "/book",
            data={"courses": ["1"], "extra": "Duplicate"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        # No new booking inserted, so last_booking_ids should be an empty list
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["last_booking_ids"], [])

    @patch("app.get_db_connection")
    def test_booking_post_db_exception(self, mock_db):
        """Booking POST returns 500 when DB raises during insert"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (
            4, "Abbie", "Smith", "abbie@example.com", "123-456-7890", "group1"
        )

        self.client.post(
            "/login", data={"email": "abbie@example.com", "password": "group1"}
        )
        mock_db.side_effect = Exception("DB Insert Error")

        response = self.client.post(
            "/book",
            data={"courses": ["1"], "extra": "Will fail"},
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Error processing booking", response.data)

    @patch("app.get_db_connection")
    def test_booking_get_db_exception(self, mock_db):
        """Booking GET returns 500 when DB raises during course fetch"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (
            4, "Abbie", "Smith", "abbie@example.com", "123-456-7890", "group1"
        )

        self.client.post(
            "/login", data={"email": "abbie@example.com", "password": "group1"}
        )
        mock_db.side_effect = Exception("DB Fetch Error")

        response = self.client.get("/book")
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Error loading booking page", response.data)

    # =========================================================================
    # BOOKING SUBMITTED
    # =========================================================================

    def test_booking_submitted_requires_authentication(self):
        """Booking submitted page redirects unauthenticated users"""
        response = self.client.get("/booking-submitted")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/login"))

    def test_booking_submitted_redirects_without_session_ids(self):
        """Booking submitted redirects to /book when no booking IDs in session"""
        self._login_as_customer()
        response = self.client.get("/booking-submitted")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/book"))

    def test_booking_submitted_shows_booking_details(self):
        """Booking submitted page renders course name and module names"""
        self._login_as_customer()
        with self.client.session_transaction() as sess:
            sess["last_booking_ids"] = [101]

        self.mock_cursor.fetchall.side_effect = [
            [(101, "Test Course Name", "Test Extra")],
            [("Module A",), ("Module B",)],
        ]

        response = self.client.get("/booking-submitted")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Course Name", response.data)
        self.assertIn(b"Module A", response.data)

    @patch("app.get_db_connection")
    def test_booking_submitted_db_exception(self, mock_db):
        """Booking submitted returns 500 when DB fails"""
        mock_db.side_effect = Exception("DB Error")

        with self.client.session_transaction() as sess:
            sess["user"] = "abbie@example.com"
            sess["role"] = "customer"
            sess["name"] = "Abbie Smith"
            sess["email"] = "abbie@example.com"
            sess["last_booking_ids"] = [101]

        response = self.client.get("/booking-submitted")
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Error loading confirmation", response.data)

    # =========================================================================
    # ADMIN LOGIN
    # =========================================================================

    def test_admin_login_page_loads(self):
        """Admin login page returns 200"""
        response = self.client.get("/admin/login")
        self.assertEqual(response.status_code, 200)

    @patch("app.get_db_connection")
    def test_admin_login_plain_text_success(self, mock_db):
        """Admin login succeeds with legacy plain-text password"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (
            1, "Admin User", "admin@example.com", "adminpass"
        )

        response = self.client.post(
            "/admin/login",
            data={"email": "admin@example.com", "password": "adminpass"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["role"], "admin")
            self.assertEqual(sess["user"], "admin@example.com")
            self.assertEqual(sess["name"], "Admin User")

    @patch("app.get_db_connection")
    def test_admin_login_hashed_password_success(self, mock_db):
        """Admin login succeeds with a werkzeug-hashed password"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        hashed = generate_password_hash("adminpass")
        mock_cursor.fetchone.return_value = (
            1, "Admin User", "admin@example.com", hashed
        )

        response = self.client.post(
            "/admin/login",
            data={"email": "admin@example.com", "password": "adminpass"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["role"], "admin")

    @patch("app.get_db_connection")
    def test_admin_login_wrong_password_rejected(self, mock_db):
        """Admin login is rejected when password is wrong"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        hashed = generate_password_hash("correctpass")
        mock_cursor.fetchone.return_value = (
            1, "Admin User", "admin@example.com", hashed
        )

        response = self.client.post(
            "/admin/login",
            data={"email": "admin@example.com", "password": "wrongpass"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertIn(b"Invalid admin credentials", response.data)
        with self.client.session_transaction() as sess:
            self.assertNotIn("role", sess)

    @patch("app.get_db_connection")
    def test_admin_login_user_not_found(self, mock_db):
        """Admin login returns 401 when no admin record is found"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        response = self.client.post(
            "/admin/login",
            data={"email": "nobody@example.com", "password": "anything"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertIn(b"Invalid admin credentials", response.data)

    @patch("app.get_db_connection")
    def test_admin_login_db_exception(self, mock_db):
        """Admin login returns 500 when DB raises during SELECT"""
        mock_db.side_effect = Exception("DB Error")

        response = self.client.post(
            "/admin/login",
            data={"email": "admin@example.com", "password": "adminpass"},
        )

        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Database error occurred", response.data)

    @patch("app.get_db_connection")
    def test_admin_login_plain_text_rehash_db_error(self, mock_db):
        """Admin login still succeeds even when the rehash DB update fails"""
        mock_conn_main = MagicMock()
        mock_cursor_main = MagicMock()
        mock_cursor_main.fetchone.return_value = (
            1, "Admin User", "admin@example.com", "adminpass"
        )
        mock_conn_main.cursor.return_value = mock_cursor_main

        # First call: main SELECT succeeds; second call: rehash UPDATE fails
        mock_db.side_effect = [mock_conn_main, Exception("Rehash DB fail")]

        response = self.client.post(
            "/admin/login",
            data={"email": "admin@example.com", "password": "adminpass"},
            follow_redirects=True,
        )

        # Login should still succeed — rehash failure is non-fatal
        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["role"], "admin")

    # =========================================================================
    # ADMIN DASHBOARD
    # =========================================================================

    def test_admin_dashboard_requires_auth(self):
        """Admin dashboard redirects non-admins"""
        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 302)

    def test_admin_dashboard_loads(self):
        """Admin dashboard returns 200 and renders counts"""
        self._set_admin_session()
        self.mock_cursor.fetchone.side_effect = [(10,), (5,), (20,)]
        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 200)

    @patch("app.get_db_connection")
    def test_admin_dashboard_db_exception(self, mock_db):
        """Admin dashboard returns 500 when DB raises"""
        self._set_admin_session()
        mock_db.side_effect = Exception("DB Error")

        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Admin Stats Error", response.data)

    # =========================================================================
    # ADMIN BOOKINGS
    # =========================================================================

    def test_manage_bookings_requires_admin(self):
        """Manage bookings page rejects non-admin role"""
        with self.client.session_transaction() as sess:
            sess["role"] = "customer"
        response = self.client.get("/admin/bookings")
        self.assertEqual(response.status_code, 302)

    def test_manage_bookings_loads(self):
        """Manage bookings page loads for admin"""
        self._set_admin_session()
        self.mock_cursor.fetchall.return_value = [
            (1, "customer@example.com", "Test Course", "Some extra")
        ]
        response = self.client.get("/admin/bookings")
        self.assertEqual(response.status_code, 200)

    @patch("app.get_db_connection")
    def test_manage_bookings_db_exception(self, mock_db):
        """Manage bookings returns 500 when DB raises"""
        self._set_admin_session()
        mock_db.side_effect = Exception("DB Error")

        response = self.client.get("/admin/bookings")
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Error loading bookings", response.data)

    def test_edit_booking_get_loads(self):
        """Edit booking form loads with current data"""
        self._set_admin_session()
        self.mock_cursor.fetchone.return_value = (1, "Extra req", 101, "Howl's Moving Castle")
        self.mock_cursor.fetchall.return_value = [
            (101, "Howl's Moving Castle"),
            (102, "Spirited Away"),
        ]
        response = self.client.get("/admin/bookings/1/edit")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Howl&#39;s Moving Castle", response.data)

    def test_edit_booking_get_not_found(self):
        """Edit booking GET returns 404 when booking ID does not exist"""
        self._set_admin_session()
        self.mock_cursor.fetchone.return_value = None

        response = self.client.get("/admin/bookings/9999/edit")
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Booking not found", response.data)

    def test_edit_booking_post_redirects(self):
        """Editing a booking redirects to bookings list"""
        self._set_admin_session()
        response = self.client.post(
            "/admin/bookings/1/edit",
            data={"course_id": "1", "extra": "Updated extra"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/admin/bookings"))

    @patch("app.get_db_connection")
    def test_edit_booking_db_exception(self, mock_db):
        """Edit booking handles DB exception with rollback and redirect"""
        self._set_admin_session()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("DB Error")

        response = self.client.post(
            "/admin/bookings/1/edit",
            data={"course_id": "1", "extra": "Will fail"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        mock_conn.rollback.assert_called()

    def test_delete_booking_calls_db_and_commits(self):
        """Deleting a booking executes both DELETE statements and commits"""
        self._set_admin_session()
        response = self.client.post(
            "/admin/bookings/1/delete", follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.mock_cursor.execute.called)
        self.mock_conn.commit.assert_called()

    def test_delete_booking_removes_modules_first(self):
        """Delete booking removes booking_modules before bookings (FK order)"""
        self._set_admin_session()
        self.client.post("/admin/bookings/5/delete")

        calls = [str(c) for c in self.mock_cursor.execute.call_args_list]
        module_call_index = next(
            (i for i, c in enumerate(calls) if "booking_modules" in c), None
        )
        booking_call_index = next(
            (i for i, c in enumerate(calls) if "DELETE FROM bookings" in c), None
        )
        self.assertIsNotNone(module_call_index)
        self.assertIsNotNone(booking_call_index)
        self.assertLess(module_call_index, booking_call_index)

    @patch("app.get_db_connection")
    def test_delete_booking_db_exception(self, mock_db):
        """Delete booking handles DB exception with rollback"""
        self._set_admin_session()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("DB Delete Error")

        response = self.client.post(
            "/admin/bookings/1/delete", follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        mock_conn.rollback.assert_called()

    # =========================================================================
    # ADMIN CUSTOMERS
    # =========================================================================

    def test_admin_customers_list_loads(self):
        """Admin customers list page returns 200"""
        self._set_admin_session()
        self.mock_cursor.fetchall.return_value = [
            (1, "John", "Doe", "john@example.com", "555-1234", "2024-01-01")
        ]
        response = self.client.get("/admin/customers")
        self.assertEqual(response.status_code, 200)

    @patch("app.get_db_connection")
    def test_admin_customers_db_exception(self, mock_db):
        """Admin customers list returns 500 when DB raises"""
        self._set_admin_session()
        mock_db.side_effect = Exception("DB Error")

        response = self.client.get("/admin/customers")
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Error loading customers", response.data)

    def test_edit_customer_get_loads(self):
        """Edit customer form loads with current customer data"""
        self._set_admin_session()
        self.mock_cursor.fetchone.return_value = (
            1, "John", "Doe", "john@example.com", "555-1234"
        )
        response = self.client.get("/admin/customers/1/edit")
        self.assertEqual(response.status_code, 200)

    def test_edit_customer_get_not_found(self):
        """Edit customer GET returns 404 when customer ID does not exist"""
        self._set_admin_session()
        self.mock_cursor.fetchone.return_value = None

        response = self.client.get("/admin/customers/9999/edit")
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Customer not found", response.data)

    def test_edit_customer_post_updates_and_redirects(self):
        """Editing a customer commits and redirects to customers list"""
        self._set_admin_session()
        response = self.client.post(
            "/admin/customers/1/edit",
            data={
                "name": "Jane",
                "last_name": "Smith",
                "email": "jane@example.com",
                "phone": "555-5678",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.mock_conn.commit.assert_called()

    def test_edit_customer_post_missing_required_fields(self):
        """Edit customer POST redirects back when required fields are empty"""
        self._set_admin_session()
        response = self.client.post(
            "/admin/customers/1/edit",
            data={
                "name": "",       # required — empty
                "last_name": "",  # required — empty
                "email": "",      # required — empty
                "phone": "555",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        # Validation failed before any DB write
        self.mock_conn.commit.assert_not_called()

    @patch("app.get_db_connection")
    def test_edit_customer_db_exception(self, mock_db):
        """Edit customer handles DB exception with rollback and redirect"""
        self._set_admin_session()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("DB Error")

        response = self.client.post(
            "/admin/customers/1/edit",
            data={
                "name": "Jane",
                "last_name": "Smith",
                "email": "jane@example.com",
                "phone": "555",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        mock_conn.rollback.assert_called()

    def test_delete_customer_calls_db_and_commits(self):
        """Deleting a customer executes all DELETE statements and commits"""
        self._set_admin_session()
        response = self.client.post(
            "/admin/customers/1/delete", follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.mock_cursor.execute.called)
        self.mock_conn.commit.assert_called()

    def test_delete_customer_removes_dependencies_first(self):
        """Delete customer removes booking_modules, then bookings, then customer"""
        self._set_admin_session()
        self.client.post("/admin/customers/3/delete")

        calls = [str(c) for c in self.mock_cursor.execute.call_args_list]
        modules_idx = next(
            (i for i, c in enumerate(calls) if "booking_modules" in c), None
        )
        bookings_idx = next(
            (i for i, c in enumerate(calls) if "DELETE FROM bookings" in c), None
        )
        customers_idx = next(
            (i for i, c in enumerate(calls) if "DELETE FROM customers" in c), None
        )
        self.assertIsNotNone(modules_idx)
        self.assertIsNotNone(bookings_idx)
        self.assertIsNotNone(customers_idx)
        self.assertLess(modules_idx, bookings_idx)
        self.assertLess(bookings_idx, customers_idx)

    @patch("app.get_db_connection")
    def test_delete_customer_db_exception(self, mock_db):
        """Delete customer handles DB exception with rollback"""
        self._set_admin_session()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("DB Delete Error")

        response = self.client.post(
            "/admin/customers/1/delete", follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        mock_conn.rollback.assert_called()

    # =========================================================================
    # DB DUMP
    # =========================================================================

    def test_db_dump_requires_admin(self):
        """DB dump redirects unauthenticated users to admin login"""
        response = self.client.get("/debug/db-dump")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login", response.location)

    def test_db_dump_loads_for_admin(self):
        """DB dump returns 200 for authenticated admin"""
        self._set_admin_session()
        self.mock_cursor.fetchall.side_effect = [
            [("customers",)],                      # table_name query
            [("customer_id",), ("name",)],          # column_name query
            [(1, "Abbie", "Smith")],                # SELECT * FROM customers
        ]
        response = self.client.get("/debug/db-dump")
        self.assertEqual(response.status_code, 200)

    def test_db_dump_skips_non_whitelisted_tables(self):
        """DB dump ignores tables not in the allowed whitelist"""
        self._set_admin_session()
        # Return only a table that is NOT in _ALLOWED_TABLES
        self.mock_cursor.fetchall.side_effect = [
            [("pg_secret_table",)],
        ]
        response = self.client.get("/debug/db-dump")
        self.assertEqual(response.status_code, 200)

    @patch("app.get_db_connection")
    def test_db_dump_db_exception(self, mock_db):
        """DB dump returns 500 when DB raises"""
        self._set_admin_session()
        mock_db.side_effect = Exception("DB Error")

        response = self.client.get("/debug/db-dump")
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Error dumping database", response.data)

    # =========================================================================
    # INTEGRATION TEST
    # =========================================================================

    @patch("app.get_db_connection")
    def test_full_user_journey(self, mock_db):
        """Full journey: register → login → view booking page → logout"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # 1. REGISTER
        response = self.client.post(
            "/register",
            data={
                "first_name": "Journey",
                "last_name": "Tester",
                "email": "journey@test.com",
                "phone": "555-9999",
                "password": "testpass",
                "confirm_password": "testpass",
            },
        )
        self.assertIn(response.status_code, [200, 302])

        # 2. LOGIN
        mock_cursor.fetchone.return_value = (
            99, "Journey", "Tester", "journey@test.com", "555-9999", "testpass"
        )
        response = self.client.post(
            "/login",
            data={"email": "journey@test.com", "password": "testpass"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["role"], "customer")
            self.assertEqual(sess["email"], "journey@test.com")

        # 3. VIEW DASHBOARD
        mock_cursor.fetchall.return_value = []
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)

        # 4. VIEW BOOKING PAGE
        mock_cursor.fetchall.side_effect = [
            [(1, "Test Course", "Course Description")],
            [(101, 1, "Test Module", "Module Desc")],
        ]
        response = self.client.get("/book")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Course", response.data)

        # 5. LOGOUT
        response = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertNotIn("user", sess)


# =============================================================================
# SESSION MANAGEMENT TESTS
# =============================================================================

class SessionManagementTests(unittest.TestCase):
    """Test session persistence and isolation between users"""

    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()

        patcher = patch("app.get_db_connection")
        self.addCleanup(patcher.stop)
        self.mock_db = patcher.start()
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.return_value = self.mock_conn
        self.mock_conn.cursor.return_value = self.mock_cursor
        self.mock_cursor.fetchone.return_value = (
            1, "Test", "User", "test@example.com", "000-000-0000", "testpass"
        )

    def test_session_persists_across_requests(self):
        """Authenticated session is valid across multiple page requests"""
        self.client.post(
            "/login", data={"email": "test@example.com", "password": "testpass"}
        )
        self.mock_cursor.fetchall.return_value = []

        r1 = self.client.get("/dashboard")
        r2 = self.client.get("/book")
        r3 = self.client.get("/dashboard")

        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r3.status_code, 200)

    def test_multiple_users_sessions_isolated(self):
        """Sequential logins produce isolated sessions per user"""

        def mock_fetchone_by_email(*args, **kwargs):
            last_call = self.mock_cursor.execute.call_args
            if last_call and len(last_call[0]) > 1:
                params = last_call[0][1]
                if isinstance(params, tuple) and params:
                    email = params[0]
                    if email == "test@example.com":
                        return (1, "Test", "User", "test@example.com", "000-0000", "testpass")
                    elif email == "user2@example.com":
                        return (2, "User", "Two", "user2@example.com", "111-1111", "pass2")
            return None

        self.mock_cursor.fetchone.side_effect = mock_fetchone_by_email

        self.client.post(
            "/login", data={"email": "test@example.com", "password": "testpass"}
        )
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["email"], "test@example.com")

        self.client.get("/logout")

        self.client.post(
            "/login", data={"email": "user2@example.com", "password": "pass2"}
        )
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["email"], "user2@example.com")
            self.assertNotEqual(sess.get("email"), "test@example.com")


if __name__ == "__main__":
    unittest.main(verbosity=2)
