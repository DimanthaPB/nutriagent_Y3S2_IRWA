"""Request tracing with an explicit allowlist of safe log metadata."""

import json
import logging
from datetime import datetime, timezone
from time import perf_counter
from uuid import UUID, uuid4

from starlette.datastructures import Headers, MutableHeaders


LOGGER_NAME = "nutriagent.security.requests"


def configure_logging():
    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    # Replace URL-based access logs, which can include passwords in query strings.
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    return logger


def choose_trace_id(values: list[str]) -> str:
    # Accept only a single canonical UUID4, not arbitrary caller-supplied text.
    if len(values) == 1 and len(values[0]) == 36:
        value = values[0]
        try:
            parsed = UUID(value)
            if parsed.version == 4 and str(parsed) == value.lower():
                return value
        except ValueError:
            pass
    return str(uuid4())


class TraceLoggingMiddleware:
    def __init__(self, app):
        self.app = app
        self.logger = configure_logging()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        trace_id = choose_trace_id(Headers(scope=scope).getlist("x-trace-id"))
        scope.setdefault("state", {})["trace_id"] = trace_id
        started = perf_counter()
        status = 500

        async def send_with_trace(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                MutableHeaders(scope=message)["X-Trace-ID"] = trace_id
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "DENY"
                headers["Referrer-Policy"] = "no-referrer"
                # CSP is deferred until inline JS/CSS and Google Fonts have an
                # explicit compatible policy; avoid breaking the current UI.
            await send(message)

        try:
            await self.app(scope, receive, send_with_trace)
        finally:
            # Never read bodies, query strings, credentials, or exception text.
            # Use route templates so unknown paths cannot inject sensitive text.
            path = getattr(scope.get("route"), "path", "<unmatched>")
            method = scope.get("method", "OTHER")
            if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE", "CONNECT"}:
                method = "OTHER"
            self.logger.info(json.dumps({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "trace_id": trace_id,
                "agent": "security",
                "method": method,
                "path": path,
                "status": status,
                "duration_ms": round((perf_counter() - started) * 1000, 3),
            }))
