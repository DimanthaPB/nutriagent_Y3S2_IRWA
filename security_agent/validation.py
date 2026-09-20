"""Advanced multi-layered prompt injection and unsafe input validation engine."""

import re
import unicodedata
from fastapi import HTTPException

# Count the original input, including padding, before trimming or regex matching.
MAX_RAW_TEXT_LENGTH = 5_000

# High-confidence prompt injection, jailbreak, and malicious pattern detectors
BLOCKED_PATTERNS = tuple(re.compile(pattern, re.IGNORECASE) for pattern in (
    # 1. Instruction Overrides & Constraint Bypasses
    r"\b(?:ignore|disregard|forget|override|bypass|disable|reset|discard|clear|drop)\s+"
    r"(?:all\s+)?(?:(?:previous|prior|initial|system|safety|safety-related)\s+)?"
    r"(?:instructions?|rules?|constraints?|filters?|guidelines?|directives?|prompts?)\b",

    # 2. Persona Hijacking & Autonomous Jailbreak Modes
    r"\b(?:jailbreak|dan\s+mode|developer\s+mode|uncensored\s+mode|god\s+mode|chaosgpt)\b",
    r"\b(?:act\s+as|pretend\s+(?:to\s+be|you\s+are)|you\s+are\s+now|roleplay\s+as)\s+"
    r"(?:an?\s+)?(?:unrestricted|unfiltered|jailbroken|evil|hacker|root|admin|dan)\b",
    r"\b(?:behave|act|pretend|assume)\s+(?:as\s+if\s+you|you)\s+have\s+no\s+"
    r"(?:rules|restrictions|filters|limits|guardrails)\b",
    r"\b(?:from\s+now\s+on\s+)?you\s+(?:can|must)\s+do\s+anything\s+now\b",

    # 3. Prompt & Secret Exfiltration
    r"\b(?:reveal|repeat|print|output|display|show|dump|leak)\s+"
    r"(?:all\s+)?(?:your\s+)?(?:system\s+prompt|initial\s+instructions?|base\s+prompt|secret\s+key|api_key|token|credentials?)\b",
    r"\bwhat\s+(?:are|were)\s+your\s+(?:exact\s+)?(?:system\s+)?(?:instructions?|prompts?)\b",
    r"\bsystem\s+prompt\b",

    # 4. Delimiter Impersonation & Special Tokens
    r"(?:\[\s*(?:system|admin|developer|instruction)\s*\]|<\|im_start\|>|<<sys>>|###\s*(?:human|assistant|system):)",

    # 5. Database, Administrative, Account & OS Destructive Commands
    r"<\s*/?\s*script\b",
    r"\b(?:drop\s+(?:table|database|schema|user|role|column)|delete\s+(?:from|user|account|all|database|records?)|alter\s+(?:table|user|database)|truncate\s+(?:table)?|insert\s+into|union\s+select)\b",
    r"\b(?:remove|erase|destroy|purge|wipe)\s+(?:all\s+)?(?:users?|accounts?|databases?|tables?|records?|logs?|profiles?)\b",
    r"\b(?:delete|drop|remove)\s+(?:the\s+)?(?:current\s+)?(?:user|account|profile|database)\b",
    r"^\s*(?:delete|drop|remove|destroy|kill|purge)\s+(?:users?|accounts?|databases?|profiles?)\s*$",
    r"\b(?:format\s+[a-z]:|rm\s+-rf|shutdown|reboot|kill\s+(?:-9|\d+|process|user))\b",
    r"\b(?:eval|exec|os\.system|subprocess|shutil|cmd\.exe|powershell)\s*\(?",
))

# Character normalization mapping for de-obfuscation
LEET_MAP = str.maketrans({
    "@": "a", "4": "a", "$": "s", "5": "s", "0": "o", "1": "i", "!": "i", "3": "e", "7": "t",
})


def _normalize_text(text: str) -> str:
    """Strip zero-width characters and de-obfuscate obvious homoglyphs/leetspeak."""
    # Normalize unicode
    cleaned = unicodedata.normalize("NFKD", text)
    # Strip zero-width spaces and control characters
    cleaned = re.sub(r"[\u200B-\u200D\uFEFF\u0000-\u0008\u000B\u000C\u000E-\u001F]", "", cleaned)
    # De-obfuscate simple leetspeak for pattern checking
    deobfuscated = cleaned.translate(LEET_MAP)
    # Collapse spaced-out letters (e.g. "i g n o r e" -> "ignore")
    collapsed = re.sub(r"(?<=\b[a-zA-Z])\s+(?=[a-zA-Z]\b)", "", cleaned)
    return f"{cleaned}\n{deobfuscated}\n{collapsed}"


def sanitize_text(text: str) -> str:
    """Validate text length, reject malicious prompt injections, and preserve user input."""
    if len(text) > MAX_RAW_TEXT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Input must not exceed {MAX_RAW_TEXT_LENGTH} characters.",
        )

    clean_text = text.strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Empty input is not allowed.")

    normalized_variants = _normalize_text(clean_text)

    # Check both clean text and normalized variants against threat vectors
    for pattern in BLOCKED_PATTERNS:
        if pattern.search(clean_text) or pattern.search(normalized_variants):
            raise HTTPException(
                status_code=400,
                detail="Input rejected: potentially unsafe content or prompt injection detected.",
            )

    # Preserve user's legitimate wording and internal whitespace for the Intake Agent
    return clean_text
