import os
import sys
import pathlib
import secrets

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from limits import parse_many
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from shared.schemas import SecurityRequest
from security_agent.auth import create_access_token, verify_access_token
from security_agent.validation import sanitize_text


app = FastAPI(title="NutriAgent - Security & Validation Agent")

# Separate per-IP counters for each decorated route. Local demo only: counters
# reset on restart and are not shared between server worker processes.
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def configured_rate_limit(name: str, default: str) -> str:
    value = os.getenv(name, default)
    try:
        rules = parse_many(value)
        if not rules or any(rule.amount <= 0 for rule in rules):
            return default
    except ValueError:
        # SlowAPI can skip malformed dynamic limits; keep the default protection.
        return default
    return value

INTAKE_AGENT_URL = os.getenv(
    "INTAKE_AGENT_URL",
    "http://localhost:8002"
)


def authenticate(token: str | None) -> str | None:
    if not token:
        return None

    return verify_access_token(token)


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/login")
@limiter.limit(lambda: configured_rate_limit("LOGIN_RATE_LIMIT", "5/minute"))
def login(request: Request, payload: LoginRequest):
    # Mock university-project login; no persistent user management.
    demo_user_id = os.getenv("DEMO_USER_ID")
    demo_password = os.getenv("DEMO_PASSWORD")
    if not demo_user_id or not demo_user_id.strip() or not demo_password:
        raise HTTPException(status_code=503, detail="Demo login is not configured")

    valid_user = secrets.compare_digest(payload.username.encode("utf-8"), demo_user_id.encode("utf-8"))
    valid_password = secrets.compare_digest(payload.password.encode("utf-8"), demo_password.encode("utf-8"))
    if not (valid_user and valid_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    token = create_access_token(demo_user_id)

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "agent": "security"
    }


@app.post("/process")
@limiter.limit(lambda: configured_rate_limit("PROCESS_RATE_LIMIT", "10/minute"))
async def process(request: Request, payload: SecurityRequest):
    subject = authenticate(payload.token)
    if subject is None:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )

    if subject != payload.user_id:
        raise HTTPException(status_code=403, detail="Token does not match user_id")

    clean_text = sanitize_text(payload.raw_text)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{INTAKE_AGENT_URL}/process",
            json={
                "user_id": payload.user_id,
                "raw_text": clean_text
            },
            timeout=30.0,
        )

    response.raise_for_status()

    return response.json()
