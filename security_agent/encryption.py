"""Fernet helpers for future stored sensitive fields, not inter-agent payloads.

Read FERNET_KEY lazily from the process environment. This module does not read
.env, persist data, or log keys, plaintext, ciphertext, or exception details.
"""

import base64
import binascii
import os
import re

from cryptography.fernet import Fernet, InvalidToken


class EncryptionConfigurationError(RuntimeError):
    """The encryption key is missing or malformed."""


class SensitiveDataDecryptionError(ValueError):
    """The ciphertext cannot be authenticated or decoded as UTF-8."""


def _get_fernet() -> Fernet:
    key = os.getenv("FERNET_KEY")
    if not key or not key.strip():
        raise EncryptionConfigurationError("FERNET_KEY is not configured")
    try:
        # Reject whitespace, non-URL-safe characters, and noncanonical encodings.
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}=", key):
            raise ValueError
        encoded = key.encode("ascii")
        decoded = base64.urlsafe_b64decode(encoded)
        if base64.urlsafe_b64encode(decoded) != encoded:
            raise ValueError
        return Fernet(encoded)
    except ValueError:
        raise EncryptionConfigurationError(
            "FERNET_KEY must be a URL-safe base64-encoded 32-byte key"
        ) from None


def encrypt_sensitive_data(value: str) -> str:
    """Encrypt a UTF-8 string, including an empty string, into Fernet text."""
    if not isinstance(value, str):
        raise TypeError("Sensitive data must be a string")
    cipher = _get_fernet()
    try:
        plaintext = value.encode("utf-8")
    except UnicodeError:
        raise ValueError("Sensitive data must be valid UTF-8 text") from None
    return cipher.encrypt(plaintext).decode("ascii")


def decrypt_sensitive_data(value: str) -> str:
    """Authenticate ciphertext and restore its original UTF-8 string."""
    if not isinstance(value, str):
        raise TypeError("Encrypted data must be a string")
    cipher = _get_fernet()
    try:
        token = value.encode("ascii")
        # Fernet's base64 decoder is permissive; reject appended junk explicitly.
        decoded = base64.b64decode(token, altchars=b"-_", validate=True)
        if base64.urlsafe_b64encode(decoded) != token:
            raise ValueError
        return cipher.decrypt(token).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeError, binascii.Error):
        raise SensitiveDataDecryptionError("Encrypted data is invalid or cannot be decrypted") from None
