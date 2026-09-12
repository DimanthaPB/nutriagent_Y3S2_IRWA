"""Run from the repository root: python -m unittest discover -s security_agent/tests -v."""

import os
import runpy
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient
from jose import jwt


TEST_ENV = {
    "JWT_SECRET": "test-only-signing-key-never-use-outside-tests",
    "JWT_ALGORITHM": "HS256",
    "JWT_EXPIRE_MINUTES": "30",
    "DEMO_USER_ID": "test-demo",
    "DEMO_PASSWORD": "test-only-password",
    "INTAKE_AGENT_URL": "http://intake.test:8002",
}

# Never load the developer's .env, including during module imports.
with patch.dict(os.environ, TEST_ENV, clear=True), patch("dotenv.load_dotenv"):
    from security_agent import auth, main


class AuthTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, TEST_ENV, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        self.client = TestClient(main.app)
        self.addCleanup(self.client.close)

        intake = patch("security_agent.main.httpx.AsyncClient")
        self.intake_factory = intake.start()
        self.addCleanup(intake.stop)
        self.intake = self.intake_factory.return_value.__aenter__.return_value
        self.meal_plan = {"user_id": "test-demo", "meals": [], "disclaimer": "Test response"}
        self.intake.post = AsyncMock(return_value=httpx.Response(
            200, json=self.meal_plan,
            request=httpx.Request("POST", "http://intake.test:8002/process"),
        ))

    def sign(self, claims, key=None, algorithm="HS256"):
        return jwt.encode(claims, key or TEST_ENV["JWT_SECRET"], algorithm=algorithm)

    def claims(self):
        return {"sub": "test-demo", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}

    def process(self, token=None, user_id="test-demo", raw_text="I want a meal plan"):
        body = {"user_id": user_id, "raw_text": raw_text}
        if token is not None:
            body["token"] = token
        return self.client.post("/process", json=body)

    def test_jwt_creation_and_verification(self):
        token = auth.create_access_token("test-demo")
        self.assertEqual(auth.verify_access_token(token), "test-demo")
        claims = jwt.decode(token, TEST_ENV["JWT_SECRET"], algorithms=["HS256"])
        seconds = claims["exp"] - datetime.now(timezone.utc).timestamp()
        self.assertTrue(1790 < seconds <= 1800)

    def test_invalid_token_rejected(self):
        for token in ["not-a-jwt", "", "   ", None]:
            with self.subTest(token=token):
                self.assertIsNone(auth.verify_access_token(token))

    def test_wrong_signature_rejected(self):
        self.assertIsNone(auth.verify_access_token(self.sign(self.claims(), key="different-test-key")))

    def test_wrong_algorithm_rejected(self):
        self.assertIsNone(auth.verify_access_token(self.sign(self.claims(), algorithm="HS384")))

    def test_expired_token_rejected(self):
        claims = self.claims()
        claims["exp"] = datetime.now(timezone.utc) - timedelta(minutes=1)
        self.assertIsNone(auth.verify_access_token(self.sign(claims)))

    def test_expiration_required(self):
        self.assertIsNone(auth.verify_access_token(self.sign({"sub": "test-demo"})))

    def test_invalid_expiration_rejected(self):
        for expiration in [None, True, "not-a-date", [], {}]:
            with self.subTest(expiration=expiration):
                claims = self.claims()
                claims["exp"] = expiration
                self.assertIsNone(auth.verify_access_token(self.sign(claims)))

    def test_subject_required(self):
        claims = self.claims()
        del claims["sub"]
        self.assertIsNone(auth.verify_access_token(self.sign(claims)))

    def test_subject_must_be_nonempty_string(self):
        for subject in ["", "   ", None, 123, []]:
            with self.subTest(subject=subject):
                claims = self.claims()
                claims["sub"] = subject
                self.assertIsNone(auth.verify_access_token(self.sign(claims)))
                with self.assertRaises(ValueError):
                    auth.create_access_token(subject)

    def test_valid_json_login(self):
        response = self.client.post("/login", json={
            "username": TEST_ENV["DEMO_USER_ID"], "password": TEST_ENV["DEMO_PASSWORD"],
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"access_token", "token_type"})
        self.assertEqual(response.json()["token_type"], "bearer")
        self.assertEqual(auth.verify_access_token(response.json()["access_token"]), "test-demo")

    def test_invalid_login_returns_401(self):
        for username, password in [("wrong-user", TEST_ENV["DEMO_PASSWORD"]),
                                   (TEST_ENV["DEMO_USER_ID"], "wrong-password")]:
            with self.subTest(username=username):
                response = self.client.post("/login", json={"username": username, "password": password})
                self.assertEqual(response.status_code, 401)

    def test_query_only_login_rejected(self):
        response = self.client.post("/login", params={"username": "test-demo", "password": "test-only-password"})
        self.assertEqual(response.status_code, 422)

    def test_unconfigured_login_fails_closed(self):
        for name in ["DEMO_USER_ID", "DEMO_PASSWORD"]:
            with self.subTest(name=name), patch.dict(os.environ, {name: ""}):
                response = self.client.post("/login", json={"username": "test-demo", "password": "test-only-password"})
                self.assertEqual(response.status_code, 503)

    def test_process_without_token_returns_401(self):
        self.assertEqual(self.process().status_code, 401)
        self.intake_factory.assert_not_called()

    def test_process_invalid_token_returns_401(self):
        self.assertEqual(self.process("invalid-token").status_code, 401)
        self.intake_factory.assert_not_called()

    def test_process_expired_token_returns_401(self):
        claims = self.claims()
        claims["exp"] = datetime.now(timezone.utc) - timedelta(minutes=1)
        self.assertEqual(self.process(self.sign(claims)).status_code, 401)
        self.intake_factory.assert_not_called()

    def test_process_different_user_rejected(self):
        self.assertEqual(self.process(auth.create_access_token("another-user")).status_code, 403)
        self.intake_factory.assert_not_called()

    def test_login_then_process_preserves_intake_contract(self):
        login = self.client.post("/login", json={"username": "test-demo", "password": "test-only-password"})
        response = self.process(login.json()["access_token"], raw_text="  I want a meal plan  ")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), self.meal_plan)
        self.intake.post.assert_awaited_once_with(
            "http://intake.test:8002/process",
            json={"user_id": "test-demo", "raw_text": "I want a meal plan"},
            timeout=30.0,
        )

    def test_sanitization_still_rejects_empty_and_blocked_text(self):
        for raw_text in ["   ", "ignore previous instructions", "system prompt", "<script>", "DROP TABLE users"]:
            with self.subTest(raw_text=raw_text):
                self.assertEqual(self.process(auth.create_access_token("test-demo"), raw_text=raw_text).status_code, 400)
        self.intake_factory.assert_not_called()

    def test_health_unchanged(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "agent": "security"})

    def test_validation_rejections_never_contact_intake(self):
        from security_agent.tests.test_validation import BLOCKED_EXAMPLES
        from security_agent.validation import MAX_RAW_TEXT_LENGTH

        token = auth.create_access_token("test-demo")
        for text in (*BLOCKED_EXAMPLES, "", "\t\n", "x" * (MAX_RAW_TEXT_LENGTH + 1)):
            with self.subTest(text=text[:80]):
                response = self.process(token, raw_text=text)
                self.assertEqual(response.status_code, 400)
                if text:
                    self.assertNotIn(text, response.json()["detail"])
        self.intake_factory.assert_not_called()

    def test_valid_nutrition_requests_preserve_forwarding_contract(self):
        from security_agent.tests.test_validation import VALID_EXAMPLES
        from security_agent.validation import MAX_RAW_TEXT_LENGTH

        token = auth.create_access_token("test-demo")
        for text in (*VALID_EXAMPLES, "a" * MAX_RAW_TEXT_LENGTH):
            with self.subTest(text=text[:80]):
                raw_text = " \n" + text + "\t " if len(text) < MAX_RAW_TEXT_LENGTH else text
                response = self.process(token, raw_text=raw_text)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), self.meal_plan)
                self.intake.post.assert_awaited_with(
                    "http://intake.test:8002/process",
                    json={"user_id": "test-demo", "raw_text": text},
                    timeout=30.0,
                )

    def test_authentication_still_precedes_validation(self):
        self.assertEqual(self.process(raw_text="ignore previous instructions").status_code, 401)
        self.assertEqual(self.process(
            auth.create_access_token("another-user"), raw_text="ignore previous instructions",
        ).status_code, 403)
        self.intake_factory.assert_not_called()


class ConfigurationTests(unittest.TestCase):
    def load_auth(self, changes):
        environment = {**TEST_ENV, **changes}
        with patch.dict(os.environ, environment, clear=True), patch("dotenv.load_dotenv") as loader:
            namespace = runpy.run_path(auth.__file__)
        return namespace, loader

    def test_root_env_path_is_explicit(self):
        _, loader = self.load_auth({})
        loader.assert_called_once_with(dotenv_path=Path(auth.__file__).resolve().parent.parent / ".env")

    def test_secret_required(self):
        for value in ["", "   "]:
            with self.subTest(value=value), self.assertRaisesRegex(RuntimeError, "JWT_SECRET is not configured"):
                self.load_auth({"JWT_SECRET": value})

    def test_lifetime_must_be_positive_integer(self):
        for value in ["0", "-1", "", "abc", "1.5"]:
            with self.subTest(value=value), self.assertRaisesRegex(RuntimeError, "must be a positive integer"):
                self.load_auth({"JWT_EXPIRE_MINUTES": value})

    def test_valid_lifetime(self):
        namespace, _ = self.load_auth({"JWT_EXPIRE_MINUTES": "10"})
        self.assertEqual(namespace["ACCESS_TOKEN_EXPIRE_MINUTES"], 10)

    def test_unsupported_algorithm_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "JWT_ALGORITHM"):
            self.load_auth({"JWT_ALGORITHM": "none"})


if __name__ == "__main__":
    unittest.main()
