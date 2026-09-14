"""Persistent account/API tests use a disposable database, never local accounts."""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from security_agent.tests import test_auth as fixtures
from security_agent import database


class AccountTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory(dir=Path(__file__).parent))
        self.path = str(Path(directory) / "accounts.db")
        self.enterContext(patch.dict(os.environ, {
            **fixtures.TEST_ENV, "SECURITY_DATABASE_PATH": self.path,
            "REGISTER_RATE_LIMIT": "1000/minute",
        }, clear=True))
        fixtures.main.limiter.reset()
        self.addCleanup(fixtures.main.limiter.reset)
        self.client = self.enterContext(TestClient(fixtures.main.app))
        self.credentials = {"username": "Alice123", "password": "test-account-password"}

    def register(self):
        return self.client.post("/register", json=self.credentials)

    def login(self, credentials=None):
        return self.client.post("/login", json=credentials or self.credentials)

    def test_registration_and_persistent_login(self):
        self.assertEqual(self.register().status_code, 201)
        with TestClient(fixtures.main.app) as another_client:
            response = another_client.post("/login", json=self.credentials)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(fixtures.auth.verify_access_token(response.json()["access_token"]), "Alice123")

    def test_passwords_are_salted_hashes(self):
        self.register()
        database.register_user("Bob123", self.credentials["password"])
        with database.connection() as conn:
            users = conn.execute("SELECT * FROM users").fetchall()
        self.assertNotEqual(users[0]["salt"], users[1]["salt"])
        self.assertNotEqual(users[0]["password_hash"], users[1]["password_hash"])
        for row in users:
            self.assertEqual(len(bytes.fromhex(row["salt"])), 16)
            self.assertNotEqual(row["password_hash"], self.credentials["password"])
            self.assertTrue(database.verify_password(self.credentials["password"], row["salt"], row["password_hash"]))
            self.assertFalse(database.verify_password("wrong-password", row["salt"], row["password_hash"]))

    def test_duplicate_registration_returns_409(self):
        self.register()
        self.assertEqual(self.register().json(), {"detail": "Username already registered"})
        self.assertEqual(self.register().status_code, 409)

    def test_registration_validation(self):
        for username, password in [("ab", "long-enough"), ("x"*31, "long-enough"),
                                   ("user name", "long-enough"), ("user;DROP TABLE users", "long-enough"),
                                   ("Alice", "short")]:
            with self.subTest(username=username):
                self.assertEqual(self.client.post("/register", json={"username": username, "password": password}).status_code, 400)

    def test_unicode_password_round_trip(self):
        database.register_user("Unicode", "食事パスワード🔒")
        self.assertIsNotNone(database.authenticate_user("Unicode", "食事パスワード🔒"))

    def test_bad_hash_rejected(self):
        for salt, digest in [("bad", "bad"), ("00", "00"), ("xx"*16, "00"*32)]:
            self.assertFalse(database.verify_password("password", salt, digest))

    def test_failed_login_and_unknown_account(self):
        self.register()
        for username in ("Alice123", "Unknown"):
            self.assertEqual(self.login({"username": username, "password": "wrong-password"}).status_code, 401)

    def test_database_login_without_demo_configuration(self):
        self.register()
        with patch.dict(os.environ, {"DEMO_USER_ID": "", "DEMO_PASSWORD": ""}):
            self.assertEqual(self.login().status_code, 200)

    def test_demo_username_cannot_be_registered(self):
        with patch.dict(os.environ, {"DEMO_USER_ID": "DemoUser"}):
            self.assertEqual(self.client.post("/register", json={"username": "DemoUser", "password": "password"}).status_code, 409)

    def test_existing_database_account_does_not_fall_back_to_demo(self):
        self.register()
        with patch.dict(os.environ, {"DEMO_USER_ID": "Alice123", "DEMO_PASSWORD": "different-password"}):
            self.assertEqual(self.login({"username": "Alice123", "password": "different-password"}).status_code, 401)

    def test_audit_metadata_and_access_isolation(self):
        self.register()
        success = self.login()
        failed = self.login({"username": "Alice123", "password": "wrong-password"})
        self.login({"username": "OtherUser", "password": "wrong-password"})
        self.assertEqual(self.client.get("/api/audit-logs").status_code, 401)
        response = self.client.get("/api/audit-logs", headers={"Authorization": "Bearer " + success.json()["access_token"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        rows = response.json()
        self.assertEqual([r["status"] for r in rows], ["FAILED", "SUCCESS"])
        self.assertEqual(rows[0]["trace_id"], failed.headers["X-Trace-ID"])
        self.assertEqual(rows[1]["trace_id"], success.headers["X-Trace-ID"])
        self.assertEqual(rows[0]["ip_address"], "testclient")
        for sensitive in (self.credentials["password"], "wrong-password", success.json()["access_token"], "password_hash", "salt"):
            self.assertNotIn(sensitive, response.text)

    def test_registration_malformed_requests_share_quota(self):
        with patch.dict(os.environ, {"REGISTER_RATE_LIMIT": "2/minute"}):
            self.assertEqual(self.client.post("/register", json={}).status_code, 422)
            self.assertEqual(self.register().status_code, 201)
            response = self.register()
            self.assertEqual(response.status_code, 429)
            self.assertIn("X-Trace-ID", response.headers)
            self.assertEqual(self.client.get("/health").status_code, 200)

    def test_database_error_sanitized(self):
        with patch.object(database, "authenticate_user", side_effect=sqlite3.OperationalError("private-db-detail")):
            response = self.login()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Account service unavailable"})
        self.assertIn("X-Trace-ID", response.headers)

    def test_static_page_served(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["Content-Type"])
        for marker in ("Create account", "Your recent login activity", "Test the security boundary", "/api/audit-logs"):
            self.assertIn(marker, response.text)

    def test_malformed_login_is_audited_without_submitted_content(self):
        response = self.client.post("/login", json={"password": "private-submitted-password"})
        self.assertEqual(response.status_code, 422)
        rows = database.get_recent_logs()
        self.assertEqual(rows[0]["username"], "<invalid-request>")
        self.assertEqual(rows[0]["status"], "FAILED")
        self.assertNotIn("private-submitted-password", str(rows))

    def test_oversized_credentials_are_safely_rejected(self):
        for path in ("/register", "/login"):
            response = self.client.post(path, json={"username": "Alice123", "password": "x"*1025})
            self.assertEqual(response.status_code, 422)
            self.assertNotIn("x"*1025, response.text)


if __name__ == "__main__":
    unittest.main()
