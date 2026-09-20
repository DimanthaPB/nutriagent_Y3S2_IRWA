"""Local account storage. Passwords are hashed; health data is never stored here."""

import hashlib
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).with_name("nutriagent.db")
ITERATIONS = 100_000


@contextmanager
def connection():
    # Optional override supports isolated tests; the application default is local.
    path = os.getenv("SECURITY_DATABASE_PATH", str(DB_PATH))
    conn = sqlite3.connect(path, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS login_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                status TEXT NOT NULL,
                ip_address TEXT,
                trace_id TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        with conn:
            yield conn
    finally:
        conn.close()


def validate_registration(username: str, password: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9]{3,30}", username):
        raise ValueError("Username must contain 3–30 ASCII letters or digits")
    if not 6 <= len(password) <= 1024:
        raise ValueError("Password must contain 6–1024 characters")
    try:
        password.encode("utf-8")
    except UnicodeError:
        raise ValueError("Password must be valid UTF-8") from None


def verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    try:
        salt, expected = bytes.fromhex(salt_hex), bytes.fromhex(hash_hex)
        if len(salt) != 16 or len(expected) != 32:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
        return secrets.compare_digest(actual, expected)
    except (ValueError, UnicodeError, TypeError):
        return False


def register_user(username: str, password: str) -> bool:
    validate_registration(username, password)
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    try:
        with connection() as conn:
            conn.execute("INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
                         (username, digest.hex(), salt.hex()))
        return True
    except sqlite3.IntegrityError:
        return False


def user_exists(username: str) -> bool:
    with connection() as conn:
        return conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone() is not None


def authenticate_user(username: str, password: str) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    # Also perform the expensive hash for unknown users.
    valid = verify_password(password, row["salt"] if row else "00" * 16,
                            row["password_hash"] if row else "00" * 32)
    if row and valid:
        return {"id": row["id"], "username": row["username"], "created_at": row["created_at"]}
    return None


def log_login_attempt(username: str, status: str, ip: str, trace_id: str):
    if status not in {"SUCCESS", "FAILED"}:
        raise ValueError("Invalid audit status")
    with connection() as conn:
        conn.execute("INSERT INTO login_logs (username, status, ip_address, trace_id) VALUES (?, ?, ?, ?)",
                     (username[:128], status, ip, trace_id))


def get_recent_logs(limit: int = 20, *, username: str | None = None) -> list[dict]:
    limit = max(1, min(limit, 100))
    with connection() as conn:
        if username is None:
            rows = conn.execute("SELECT * FROM login_logs ORDER BY timestamp DESC, id DESC LIMIT ?", (limit,))
        else:
            rows = conn.execute("SELECT * FROM login_logs WHERE username = ? ORDER BY timestamp DESC, id DESC LIMIT ?",
                                (username, limit))
        return [dict(row) for row in rows]
