import os
import sys
import pathlib
import secrets
import sqlite3

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, field_validator
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.concurrency import run_in_threadpool

from shared.schemas import SecurityRequest
from security_agent.auth import create_access_token, verify_access_token
from security_agent.validation import sanitize_text
from security_agent.logging_config import TraceLoggingMiddleware
from security_agent.rate_limiting import RateLimitedRoute, limiter
from security_agent import database


app = FastAPI(title="NutriAgent - Security & Validation Agent")
app.router.route_class = RateLimitedRoute
app.add_middleware(TraceLoggingMiddleware)

# Separate per-IP counters for each protected route. Local demo only: counters
# reset on restart and are not shared between server worker processes.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(sqlite3.Error)
async def database_error(request: Request, exc: sqlite3.Error):
    return JSONResponse(status_code=503, content={"detail": "Account service unavailable"})


@app.exception_handler(RequestValidationError)
async def safe_validation_error(request: Request, exc: RequestValidationError):
    if request.url.path == "/login":
        # Malformed bodies have no trustworthy username; never inspect their values.
        await run_in_threadpool(database.log_login_attempt, "<invalid-request>", "FAILED",
                                   request.client.host if request.client else "unknown", request.state.trace_id)
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
        if len(value) > 1024:
            raise ValueError("Credential is too long")
        try:
            value.encode("utf-8")
        except UnicodeError:
            raise ValueError("Credentials must be valid UTF-8 text") from None
        return value


@app.post("/login")
def login(request: Request, payload: LoginRequest):
    user = database.authenticate_user(payload.username, payload.password)
    demo_user_id = os.getenv("DEMO_USER_ID")
    demo_password = os.getenv("DEMO_PASSWORD")
    valid = user is not None
    unconfigured = False
    if not valid and not database.user_exists(payload.username):
        if not demo_user_id or not demo_user_id.strip() or not demo_password:
            unconfigured = True
        else:
            valid_user = secrets.compare_digest(payload.username.encode("utf-8"), demo_user_id.encode("utf-8"))
            valid_password = secrets.compare_digest(payload.password.encode("utf-8"), demo_password.encode("utf-8"))
            valid = valid_user and valid_password
    database.log_login_attempt(payload.username, "SUCCESS" if valid else "FAILED",
                               request.client.host if request.client else "unknown", request.state.trace_id)
    if unconfigured:
        raise HTTPException(status_code=503, detail="Demo login is not configured")
    if not valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    token = create_access_token(payload.username)

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@app.post("/register", status_code=201)
def register(request: Request, payload: LoginRequest):
    try:
        database.validate_registration(payload.username, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    if payload.username == os.getenv("DEMO_USER_ID") or not database.register_user(payload.username, payload.password):
        raise HTTPException(status_code=409, detail="Username already registered")
    return {"message": "User registered successfully", "username": payload.username}


@app.get("/api/audit-logs")
def audit_logs(request: Request):
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    subject = authenticate(token) if scheme.lower() == "bearer" else None
    if subject is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return JSONResponse(database.get_recent_logs(limit=25, username=subject), headers={"Cache-Control": "no-store"})


@app.get("/", response_class=FileResponse)
def web_ui():
    return FileResponse(pathlib.Path(__file__).with_name("static") / "index.html")


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
