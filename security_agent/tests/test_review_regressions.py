import json
import os
import runpy
import secrets
import unittest
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import httpx
from fastapi.testclient import TestClient

from security_agent.logging_config import LOGGER_NAME
from security_agent.tests import test_auth as fixtures

main, auth = fixtures.main, fixtures.auth


class RequestRegressionTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, fixtures.TEST_ENV, clear=True))
        main.limiter.reset()
        self.addCleanup(main.limiter.reset)
        self.client = self.enterContext(TestClient(main.app, raise_server_exceptions=False))
        self.logs = self.enterContext(self.assertLogs(LOGGER_NAME, level="INFO"))
        self.trace_id = str(uuid4())
        self.token = auth.create_access_token("test-demo")
        self.factory = self.enterContext(patch("security_agent.main.httpx.AsyncClient"))
        self.downstream = self.factory.return_value.__aenter__.return_value
        self.downstream.post = AsyncMock(return_value=httpx.Response(
            200, json={"user_id": "test-demo", "meals": []},
            request=httpx.Request("POST", "http://intake.test:8002/process"),
        ))

    def process(self):
        return self.client.post("/process", headers={"X-Trace-ID": self.trace_id}, json={
            "user_id": "test-demo", "raw_text": "I want a meal plan", "token": self.token,
        })

    def assert_safe_error(self, response, status, message):
        self.assertEqual(response.status_code, status)
        self.assertEqual(response.json(), {"detail": message})
        self.assertEqual(response.headers["X-Trace-ID"], self.trace_id)
        entry = json.loads(self.logs.records[-1].getMessage())
        self.assertEqual(entry["status"], status)
        self.assertEqual(entry["trace_id"], self.trace_id)
        self.assertEqual(entry["path"], "/process")
        self.assertNotIn("private-downstream-sentinel", response.text)
        self.assertNotIn("private-downstream-sentinel", str(self.logs.output))

    def check_malformed_quota(self, **kwargs):
        with patch.dict(os.environ, {"LOGIN_RATE_LIMIT": "2/minute", "PROCESS_RATE_LIMIT": "2/minute"}):
            for path in ("/login", "/process"):
                with self.subTest(path=path):
                    main.limiter.reset()
                    responses = [self.client.post(path, **kwargs) for _ in range(4)]
                    self.assertEqual([r.status_code for r in responses], [422, 422, 429, 429])
                    for response in responses:
                        self.assertEqual(UUID(response.headers["X-Trace-ID"]).version, 4)
                    self.assertEqual(json.loads(self.logs.records[-1].getMessage())["path"], path)
        self.factory.assert_not_called()

    def test_malformed_json_consumes_quota(self):
        self.check_malformed_quota(content=b'{"password":', headers={"Content-Type": "application/json"})

    def test_empty_body_consumes_quota(self):
        self.check_malformed_quota(content=b'', headers={"Content-Type": "application/json"})

    def test_missing_required_fields_consumes_quota(self):
        self.check_malformed_quota(json={})

    def test_valid_and_malformed_requests_share_one_counter(self):
        with patch.dict(os.environ, {"LOGIN_RATE_LIMIT": "2/minute", "PROCESS_RATE_LIMIT": "2/minute"}):
            self.assertEqual(self.client.post("/login", json={}).status_code, 422)
            credentials = {"username": "test-demo", "password": "test-only-password"}
            self.assertEqual(self.client.post("/login", json=credentials).status_code, 200)
            self.assertEqual(self.client.post("/login", json=credentials).status_code, 429)
            self.assertEqual(self.client.post("/process", json={}).status_code, 422)
            self.assertEqual(self.process().status_code, 200)
            self.assertEqual(self.process().status_code, 429)
        self.assertEqual(self.downstream.post.await_count, 1)

    def test_connection_and_protocol_failures_return_502(self):
        for error in (httpx.ConnectError, httpx.RemoteProtocolError):
            with self.subTest(error=error.__name__):
                self.downstream.post.side_effect = error("private-downstream-sentinel")
                self.assert_safe_error(self.process(), 502, "Intake service unavailable")

    def test_timeout_failures_return_504(self):
        for error in (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout):
            with self.subTest(error=error.__name__):
                self.downstream.post.side_effect = error("private-downstream-sentinel")
                self.assert_safe_error(self.process(), 504, "Intake service timed out")

    def test_unsuccessful_downstream_statuses_return_502(self):
        for status in (302, 400, 401, 403, 404, 429, 500, 503):
            with self.subTest(status=status):
                self.downstream.post.return_value = httpx.Response(
                    status, text="private-downstream-sentinel",
                    request=httpx.Request("POST", "http://intake.test:8002/process"),
                )
                self.assert_safe_error(self.process(), 502, "Intake service unavailable")

    def test_invalid_downstream_json_returns_502(self):
        for content in (b'private-downstream-sentinel', b'', b'\xff', b'{"value": NaN}', b'"\\ud800"'):
            with self.subTest(content_length=len(content)):
                self.downstream.post.return_value = httpx.Response(
                    200, content=content,
                    request=httpx.Request("POST", "http://intake.test:8002/process"),
                )
                self.assert_safe_error(self.process(), 502, "Invalid response from Intake service")

    def test_invalid_unicode_credentials_return_sanitized_422(self):
        for field in ("username", "password"):
            with self.subTest(field=field):
                body = {"username": "test-demo", "password": "test-only-password"}
                body[field] = "private-unicode-sentinel\ud800"
                response = self.client.post("/login", json=body, headers={"X-Trace-ID": self.trace_id})
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.headers["X-Trace-ID"], self.trace_id)
                self.assertEqual(response.json(), {"detail": [
                    {"loc": ["body", field], "type": "value_error", "msg": "Invalid field value"}
                ]})
                self.assertNotIn("private-unicode-sentinel", response.text)
        self.assertNotIn("private-unicode-sentinel", str(self.logs.output))

    def test_unicode_credentials_that_encode_are_not_server_errors(self):
        response = self.client.post("/login", json={"username": "café", "password": "පාස්වර්ඩ්"})
        self.assertEqual(response.status_code, 401)

    def test_validation_responses_do_not_reflect_sensitive_values(self):
        sensitive = "private-validation-sentinel"
        requests = [
            ("/login", {"json": {"password": sensitive}}),
            ("/login", {"json": {"username": "test-demo", "password": {sensitive: sensitive}}}),
            ("/process", {"json": {"token": self.token, "raw_text": sensitive}}),
            ("/process", {"json": {"user_id": "test-demo", "token": [self.token], "raw_text": [sensitive]}}),
            ("/login", {"content": ('{"password":"' + sensitive + '",').encode(),
                        "headers": {"Content-Type": "application/json"}}),
        ]
        for path, kwargs in requests:
            with self.subTest(path=path, kind=list(kwargs)[0]):
                response = self.client.post(path, **kwargs)
                self.assertEqual(response.status_code, 422)
                self.assertEqual(UUID(response.headers["X-Trace-ID"]).version, 4)
                self.assertNotIn(sensitive, response.text)
                self.assertNotIn(self.token, response.text)
                for error in response.json()["detail"]:
                    self.assertEqual(set(error), {"loc", "type", "msg"})
        self.assertNotIn(sensitive, str(self.logs.output))
        self.assertNotIn(self.token, str(self.logs.output))
        self.factory.assert_not_called()


class SecretConfigurationRegressionTests(unittest.TestCase):
    def load_config(self, secret, algorithm="HS256"):
        environment = {**fixtures.TEST_ENV, "JWT_ALGORITHM": algorithm}
        if secret is None:
            environment.pop("JWT_SECRET")
        else:
            environment["JWT_SECRET"] = secret
        with patch.dict(os.environ, environment, clear=True), patch("dotenv.load_dotenv"):
            return runpy.run_path(auth.__file__)

    def test_missing_or_empty_secret_fails(self):
        for secret in (None, "", "   "):
            with self.assertRaisesRegex(RuntimeError, "JWT_SECRET is not configured"):
                self.load_config(secret)

    def test_placeholder_secret_fails_without_disclosure(self):
        for secret in ("replace-with-a-random-secret", "REPLACE-WITH-A-RANDOM-SECRET", "your-256-bit-secret", "changeme"):
            with self.assertRaisesRegex(RuntimeError, "placeholder") as caught:
                self.load_config(secret)
            self.assertNotIn(secret, str(caught.exception))

    def test_too_short_secret_fails(self):
        secret = secrets.token_hex(15)
        with self.assertRaisesRegex(RuntimeError, "at least 32 bytes") as caught:
            self.load_config(secret)
        self.assertNotIn(secret, str(caught.exception))

    def test_valid_secret_at_minimum_length_succeeds(self):
        namespace = self.load_config(secrets.token_hex(16))
        token = namespace["create_access_token"]("test-user")
        self.assertEqual(namespace["verify_access_token"](token), "test-user")

    def test_key_length_counts_utf8_bytes(self):
        namespace = self.load_config("é" * 16)
        token = namespace["create_access_token"]("test-user")
        self.assertEqual(namespace["verify_access_token"](token), "test-user")

    def test_other_hmac_algorithms_enforce_matching_key_sizes(self):
        for algorithm, minimum in (("HS384", 48), ("HS512", 64)):
            with self.subTest(algorithm=algorithm):
                with self.assertRaisesRegex(RuntimeError, f"at least {minimum} bytes"):
                    self.load_config(secrets.token_hex(16), algorithm)
                namespace = self.load_config(secrets.token_hex(minimum // 2), algorithm)
                token = namespace["create_access_token"]("test-user")
                self.assertEqual(namespace["verify_access_token"](token), "test-user")


if __name__ == "__main__":
    unittest.main()
