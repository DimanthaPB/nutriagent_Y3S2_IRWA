import os
import sys
import pathlib
import secrets

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.schemas import SecurityRequest
from security_agent.auth import create_access_token, verify_access_token
from security_agent.validation import sanitize_text


app = FastAPI(title="NutriAgent - Security & Validation Agent")

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
def login(request: LoginRequest):
    # Mock university-project login; no persistent user management.
    demo_user_id = os.getenv("DEMO_USER_ID")
    demo_password = os.getenv("DEMO_PASSWORD")
    if not demo_user_id or not demo_user_id.strip() or not demo_password:
        raise HTTPException(status_code=503, detail="Demo login is not configured")

    valid_user = secrets.compare_digest(request.username.encode("utf-8"), demo_user_id.encode("utf-8"))
    valid_password = secrets.compare_digest(request.password.encode("utf-8"), demo_password.encode("utf-8"))
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
async def process(request: SecurityRequest):
    subject = authenticate(request.token)
    if subject is None:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )

    if subject != request.user_id:
        raise HTTPException(status_code=403, detail="Token does not match user_id")

    clean_text = sanitize_text(request.raw_text)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{INTAKE_AGENT_URL}/process",
            json={
                "user_id": request.user_id,
                "raw_text": clean_text
            },
            timeout=30.0,
        )

    response.raise_for_status()

    return response.json()
