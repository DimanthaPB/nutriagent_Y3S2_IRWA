import os
import sys
import pathlib
import secrets

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, field_validator
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from shared.schemas import SecurityRequest
from security_agent.auth import create_access_token, verify_access_token
from security_agent.validation import sanitize_text
from security_agent.logging_config import TraceLoggingMiddleware
from security_agent.rate_limiting import RateLimitedRoute, limiter


app = FastAPI(title="NutriAgent - Security & Validation Agent")
app.router.route_class = RateLimitedRoute
app.add_middleware(TraceLoggingMiddleware)

# Separate per-IP counters for each protected route. Local demo only: counters
# reset on restart and are not shared between server worker processes.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(RequestValidationError)
async def safe_validation_error(request: Request, exc: RequestValidationError):
    messages = {
        "missing": "Field required",
        "string_type": "Input should be a valid string",
        "json_invalid": "Invalid JSON",
        "model_attributes_type": "Input must be a JSON object",
        "value_error": "Invalid field value",
    }
    safe_locations = {"body", "query", "path", "header", "username", "password", "user_id", "raw_text", "token"}
    errors = []
    for error in exc.errors():
        kind = error["type"] if error["type"] in messages else "validation_error"
        location = [part if isinstance(part, int) or part in safe_locations else "field"
                    for part in error.get("loc", ())]
        errors.append({"loc": location, "type": kind, "msg": messages.get(kind, "Invalid request")})
    return JSONResponse(status_code=422, content={"detail": errors})

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

    @field_validator("username", "password")
    @classmethod
    def valid_utf8(cls, value: str) -> str:
        try:
            value.encode("utf-8")
        except UnicodeError:
            raise ValueError("Credentials must be valid UTF-8 text") from None
        return value


@app.post("/login")
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

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{INTAKE_AGENT_URL}/process",
                json={
                    "user_id": payload.user_id,
                    "raw_text": clean_text
                },
                timeout=30.0,
                headers={"X-Trace-ID": request.state.trace_id},
            )
        response.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Intake service timed out") from None
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Intake service unavailable") from None

    try:
        result = response.json()
        # Ensure downstream JSON is also serializable as a safe HTTP JSON response.
        JSONResponse(content=result)
    except (ValueError, UnicodeError, TypeError):
        raise HTTPException(status_code=502, detail="Invalid response from Intake service") from None
    return result
