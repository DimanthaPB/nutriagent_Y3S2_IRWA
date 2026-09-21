"""Focused regressions; fixtures use disposable SQLite and never load .env."""
import hashlib
import os
import threading
import unittest
from unittest.mock import patch

import httpx
from security_agent import database
from security_agent.tests import test_database as accounts
from security_agent.tests import test_auth as fixtures


class HardeningTests(unittest.TestCase):
    setUp = accounts.AccountTests.setUp
    register = accounts.AccountTests.register
    login = accounts.AccountTests.login

    def legacy_account(self, password="short"):
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000).hex()
        with database.connection() as conn:
            conn.execute("INSERT INTO users (username,password_hash,salt) VALUES (?,?,?)",
                         ("LegacyUser", digest, salt.hex()))
        return salt.hex(), digest

    def test_legacy_hash_verification(self):
        salt, digest = self.legacy_account()
        self.assertTrue(database.verify_password("short", salt, digest))
        self.assertFalse(database.verify_password("incorrect", salt, digest))

    def test_legacy_login_upgrades_without_password_policy_change(self):
        salt, digest = self.legacy_account()
        response = self.login({"username": "LegacyUser", "password": "short"})
        self.assertEqual(response.status_code, 200)
        with database.connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE username=?", ("LegacyUser",)).fetchone()
        self.assertTrue(row["password_hash"].startswith("pbkdf2_sha256$v1$600000$"))
        self.assertNotEqual(row["salt"], salt)
        self.assertTrue(database.verify_password("short", row["salt"], row["password_hash"]))
        self.assertEqual(self.login({"username": "LegacyUser", "password": "short"}).status_code, 200)

    def test_wrong_legacy_password_does_not_upgrade(self):
        _, digest = self.legacy_account()
        self.assertIsNone(database.authenticate_user("LegacyUser", "incorrect"))
        with database.connection() as conn:
            row = conn.execute("SELECT password_hash FROM users WHERE username=?", ("LegacyUser",)).fetchone()
        self.assertEqual(row[0], digest)

    def test_new_hash_verification_and_bad_metadata(self):
        self.register()
        with database.connection() as conn:
            row = conn.execute("SELECT * FROM users").fetchone()
        self.assertTrue(row["password_hash"].startswith("pbkdf2_sha256$v1$600000$"))
        self.assertTrue(database.verify_password(self.credentials["password"], row["salt"], row["password_hash"]))
        self.assertFalse(database.verify_password("wrong", row["salt"], row["password_hash"]))
        for malformed in ("pbkdf2_sha256$v2$600000$00", "pbkdf2_sha256$v1$9999999999$00", "bad$metadata"):
            self.assertFalse(database.verify_password("password", row["salt"], malformed))

    def test_new_password_boundaries_and_spaces_preserved(self):
        for value in ("", "1234567", " " * 8, "\t\n" * 5, "x" * 1025):
            with self.subTest(length=len(value)):
                with self.assertRaises(ValueError):
                    database.register_user("Boundary", value)
        for username, value in (("Minimum", "12345678"), ("Maximum", "x"*1024), ("Spaces", "  secret  ")):
            self.assertTrue(database.register_user(username, value))
            self.assertIsNotNone(database.authenticate_user(username, value))
        self.assertIsNone(database.authenticate_user("Spaces", "secret"))

    def test_invalid_unicode_never_reaches_intake(self):
        with patch("security_agent.main.httpx.AsyncClient") as downstream:
            for value in ("\ud800", "Nutrition \udfff"):
                response = self.client.post("/process", json={
                    "user_id": "test-demo", "token": fixtures.auth.create_access_token("test-demo"), "raw_text": value,
                })
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json(), {"detail": "Input must be valid UTF-8 text."})
                self.assertIn("X-Trace-ID", response.headers)
            downstream.assert_not_called()

    def test_valid_unicode_keeps_plaintext_contract(self):
        text = "野菜とタンパク質 🥗"
        with patch("security_agent.main.httpx.AsyncClient") as factory:
            post = factory.return_value.__aenter__.return_value.post
            post.return_value = httpx.Response(200, json={"ok": True}, request=httpx.Request("POST", "http://intake.test"))
            response = self.client.post("/process", json={"user_id": "test-demo",
                "token": fixtures.auth.create_access_token("test-demo"), "raw_text": "  " + text + "  "})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(post.call_args.kwargs["json"], {"user_id": "test-demo", "raw_text": text})
            self.assertEqual(post.call_args.kwargs["headers"], {"X-Trace-ID": response.headers["X-Trace-ID"]})

    def test_security_headers_on_success_and_handled_errors(self):
        with patch.dict(os.environ, {"REGISTER_RATE_LIMIT": "1/minute"}):
            responses = [self.client.get("/"), self.client.get("/health"),
                         self.client.get("/api/audit-logs"), self.client.post("/register", json={}),
                         self.register()]
        self.assertEqual([r.status_code for r in responses], [200, 200, 401, 422, 429])
        for response in responses:
            for name, value in {"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer"}.items():
                self.assertEqual(response.headers[name], value)

    def test_two_registered_users_cannot_select_each_others_audits(self):
        for username in ("UserAlpha", "UserBeta"):
            database.register_user(username, "test-password")
            self.login({"username": username, "password": "test-password"})
        for username, other in (("UserAlpha", "UserBeta"), ("UserBeta", "UserAlpha")):
            response = self.client.get("/api/audit-logs", params={"username": other, "user_id": other},
                headers={"Authorization": "Bearer " + fixtures.auth.create_access_token(username)})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json())
            self.assertEqual({row["username"] for row in response.json()}, {username})

    def test_malformed_login_audit_uses_worker_thread(self):
        from starlette.concurrency import run_in_threadpool
        observed = {}
        async def dispatch(func, *args):
            observed["handler"] = threading.get_ident()
            return await run_in_threadpool(func, *args)
        def audit(*args):
            observed["worker"] = threading.get_ident()
        with patch("security_agent.main.run_in_threadpool", side_effect=dispatch), \
             patch.object(database, "log_login_attempt", side_effect=audit):
            response = self.client.post("/login", json={})
        self.assertEqual(response.status_code, 422)
        self.assertIn("X-Trace-ID", response.headers)
        self.assertNotEqual(observed["handler"], observed["worker"])
