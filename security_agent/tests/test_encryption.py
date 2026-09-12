import base64
import io
import os
import runpy
import traceback
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from cryptography.fernet import Fernet

from security_agent import encryption


class EncryptionTests(unittest.TestCase):
    def setUp(self):
        self.key = Fernet.generate_key().decode("ascii")
        self.enterContext(patch.dict(os.environ, {"FERNET_KEY": self.key}, clear=True))

    def test_ciphertext_differs_from_plaintext(self):
        plaintext = "Private health profile"
        ciphertext = encryption.encrypt_sensitive_data(plaintext)
        self.assertIsInstance(ciphertext, str)
        self.assertNotEqual(ciphertext, plaintext)
        self.assertNotIn(plaintext, ciphertext)

    def test_round_trip(self):
        value = "allergies: peanuts; conditions: diabetes"
        self.assertEqual(encryption.decrypt_sensitive_data(encryption.encrypt_sensitive_data(value)), value)

    def test_unicode_round_trip(self):
        value = "ආහාර / உணவு / café / 健康 / 🥗\nprofile\tdata"
        self.assertEqual(encryption.decrypt_sensitive_data(encryption.encrypt_sensitive_data(value)), value)

    def test_empty_string_round_trip(self):
        self.assertEqual(encryption.decrypt_sensitive_data(encryption.encrypt_sensitive_data("")), "")

    def test_repeated_plaintext_uses_fresh_ciphertexts(self):
        value = "Same sensitive field"
        first = encryption.encrypt_sensitive_data(value)
        second = encryption.encrypt_sensitive_data(value)
        self.assertNotEqual(first, second)
        self.assertEqual(encryption.decrypt_sensitive_data(first), value)
        self.assertEqual(encryption.decrypt_sensitive_data(second), value)

    def test_missing_and_blank_key_fail_clearly(self):
        for environment in ({}, {"FERNET_KEY": ""}, {"FERNET_KEY": "  "}):
            with patch.dict(os.environ, environment, clear=True):
                for function in (encryption.encrypt_sensitive_data, encryption.decrypt_sensitive_data):
                    with self.assertRaisesRegex(encryption.EncryptionConfigurationError, "not configured"):
                        function("private-value")

    def test_invalid_keys_are_rejected_without_disclosure(self):
        values = ("replace-with-a-generated-fernet-key", "bad-secret-key", "秘密", self.key + " ",
                  base64.urlsafe_b64encode(b"too-short").decode("ascii"), "!" * 43 + "=")
        for key in values:
            with self.subTest(case=len(key)), patch.dict(os.environ, {"FERNET_KEY": key}):
                for function in (encryption.encrypt_sensitive_data, encryption.decrypt_sensitive_data):
                    try:
                        function("private-value")
                    except encryption.EncryptionConfigurationError:
                        message = traceback.format_exc()
                        self.assertNotIn(key, message)
                        self.assertNotIn("private-value", str(message.splitlines()[-1]))
                    else:
                        self.fail("Invalid key was accepted")

    def test_import_does_not_require_a_key(self):
        with patch.dict(os.environ, {}, clear=True):
            namespace = runpy.run_path(encryption.__file__)
        self.assertTrue(callable(namespace["encrypt_sensitive_data"]))

    def test_tampered_ciphertext_is_rejected(self):
        token = encryption.encrypt_sensitive_data("private-value")
        data = bytearray(base64.urlsafe_b64decode(token))
        data[-1] ^= 1
        tampered = base64.urlsafe_b64encode(data).decode("ascii")
        with self.assertRaises(encryption.SensitiveDataDecryptionError):
            encryption.decrypt_sensitive_data(tampered)

    def test_invalid_ciphertexts_are_rejected(self):
        valid = encryption.encrypt_sensitive_data("private-value")
        for value in ("", "not-a-token", "秘密", valid + "!", valid[:-5], " " + valid):
            with self.subTest(case=len(value)), self.assertRaises(encryption.SensitiveDataDecryptionError):
                encryption.decrypt_sensitive_data(value)

    def test_wrong_key_is_rejected(self):
        token = encryption.encrypt_sensitive_data("private-value")
        with patch.dict(os.environ, {"FERNET_KEY": Fernet.generate_key().decode("ascii")}):
            with self.assertRaises(encryption.SensitiveDataDecryptionError):
                encryption.decrypt_sensitive_data(token)

    def test_valid_ciphertext_containing_non_utf8_is_rejected(self):
        token = Fernet(self.key.encode("ascii")).encrypt(b"\xff\xfe").decode("ascii")
        with self.assertRaises(encryption.SensitiveDataDecryptionError):
            encryption.decrypt_sensitive_data(token)

    def test_nonstring_values_are_rejected(self):
        for value in (None, b"data", 42, {}, []):
            for function in (encryption.encrypt_sensitive_data, encryption.decrypt_sensitive_data):
                with self.assertRaises(TypeError):
                    function(value)

    def test_utility_does_not_log_or_print_sensitive_data(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with self.assertNoLogs(level="DEBUG"), redirect_stdout(stdout), redirect_stderr(stderr):
            token = encryption.encrypt_sensitive_data("private-health-sentinel")
            encryption.decrypt_sensitive_data(token)
            with self.assertRaises(encryption.SensitiveDataDecryptionError) as caught:
                encryption.decrypt_sensitive_data("private-ciphertext-sentinel")
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        for sensitive in (self.key, token, "private-ciphertext-sentinel", "private-health-sentinel"):
            self.assertNotIn(sensitive, str(caught.exception))


if __name__ == "__main__":
    unittest.main()
