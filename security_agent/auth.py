import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from jose import JWTError, jwt


# Resolve independently of the working directory; existing environment wins.
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
if not SECRET_KEY or not SECRET_KEY.strip():
    raise RuntimeError("JWT_SECRET is not configured")

if ALGORITHM not in {"HS256", "HS384", "HS512"}:
    raise RuntimeError("JWT_ALGORITHM must be HS256, HS384, or HS512")

try:
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))
    if ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
        raise ValueError
except ValueError:
    raise RuntimeError("JWT_EXPIRE_MINUTES must be a positive integer") from None


def create_access_token(user_id: str) -> str:
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("Token subject must be a non-empty string")

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": user_id,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def verify_access_token(token: str) -> str | None:
    if not isinstance(token, str) or not token.strip():
        return None

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require_sub": True, "require_exp": True},
        )

        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            return None
        expiration = payload.get("exp")
        if isinstance(expiration, bool) or not isinstance(expiration, (int, float)):
            return None
        if not expiration > datetime.now(timezone.utc).timestamp():
            return None
        return subject

    except (JWTError, TypeError, ValueError, OverflowError):
        return None
