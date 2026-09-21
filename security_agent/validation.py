"""Lightweight rejection of obvious unsafe input, not a complete injection defense."""

import re

from fastapi import HTTPException


# Count the original input, including padding, before trimming or regex matching.
MAX_RAW_TEXT_LENGTH = 5_000

BLOCKED_PATTERNS = tuple(re.compile(pattern, re.IGNORECASE) for pattern in (
    r"\b(?:ignore|disregard|forget|override)\s+"
    r"(?:all\s+)?(?:(?:previous|prior)\s+)?(?:instructions?|rules?)\b",
    r"\bsystem\s+prompt\b",
    r"<\s*/?\s*script\b",
    r"\bdrop\s+table\b",
))


def sanitize_text(text: str) -> str:
    if len(text) > MAX_RAW_TEXT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Input must not exceed {MAX_RAW_TEXT_LENGTH} characters.",
        )

    try:
        text.encode("utf-8")
    except UnicodeError:
        raise HTTPException(status_code=400, detail="Input must be valid UTF-8 text.") from None

    clean_text = text.strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Empty input is not allowed.")

    if any(pattern.search(clean_text) for pattern in BLOCKED_PATTERNS):
        raise HTTPException(
            status_code=400,
            detail="Input rejected: potentially unsafe content detected.",
        )

    # Preserve the user's wording and internal whitespace for the Intake Agent.
    return clean_text
