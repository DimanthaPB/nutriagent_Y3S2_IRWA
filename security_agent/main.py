"""
Security & Validation Agent
----------------------------
Front door of the system. Every client request hits this agent first.

Current responsibilities (implemented as a starting stub - see TODOs):
  1. Authenticate the caller (currently stubbed - always passes)
  2. Sanitize input text (basic pattern-based rejection is implemented)
  3. Forward the clean request to the Intake Agent
  4. Return the final response back up to the client

NOT yet implemented (see "Next steps" in the README for this agent):
  - Real JWT verification
  - Encryption of stored health data
  - Rate limiting
  - Structured audit logging with trace IDs
"""

import os
import re
import sys
import pathlib

# Make the sibling "shared" package importable regardless of where this
# script is launched from.
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

import httpx
from fastapi import FastAPI, HTTPException

from shared.schemas import SecurityRequest

app = FastAPI(title="NutriAgent - Security & Validation Agent")

INTAKE_AGENT_URL = os.getenv("INTAKE_AGENT_URL", "http://localhost:8002")

# Very basic prompt-injection / malicious-input patterns to reject outright.
# TODO: expand this list, and consider a proper sanitization library instead
# of hand-rolled regexes once you have more test cases.
BLOCKED_PATTERNS = [
    r"ignore (all|previous|prior) instructions",
    r"system prompt",
    r"<script.*?>",
    r"drop\s+table",
]


def sanitize_text(text: str) -> str:
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Empty input is not allowed.")
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            raise HTTPException(
                status_code=400,
                detail="Input rejected: potentially unsafe content detected.",
            )
    return text.strip()


def authenticate(token: str | None) -> bool:
    # TODO: replace with real JWT verification using python-jose or pyjwt.
    # For now this always allows the request through so the pipeline can be
    # tested end-to-end before auth is wired up.
    return True


@app.get("/health")
def health():
    return {"status": "ok", "agent": "security"}


@app.post("/process")
async def process(request: SecurityRequest):
    if not authenticate(request.token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    clean_text = sanitize_text(request.raw_text)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{INTAKE_AGENT_URL}/process",
            json={"user_id": request.user_id, "raw_text": clean_text},
            timeout=30.0,
        )
    response.raise_for_status()
    return response.json()
