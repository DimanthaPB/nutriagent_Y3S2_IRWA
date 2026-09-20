"""Run public SlowAPI decorators before FastAPI parses endpoint bodies."""

import os

from fastapi import Request, Response
from fastapi.routing import APIRoute
from limits import parse_many
from slowapi import Limiter
from slowapi.util import get_remote_address


limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")


def configured_rate_limit(name: str, default: str) -> str:
    value = os.getenv(name, default)
    try:
        rules = parse_many(value)
        if not rules or any(rule.amount <= 0 for rule in rules):
            return default
    except ValueError:
        return default
    return value


@limiter.limit(lambda: configured_rate_limit("LOGIN_RATE_LIMIT", "5/minute"))
async def check_login_limit(request: Request):
    return Response()


@limiter.limit(lambda: configured_rate_limit("PROCESS_RATE_LIMIT", "10/minute"))
async def check_process_limit(request: Request):
    return Response()


@limiter.limit(lambda: configured_rate_limit("REGISTER_RATE_LIMIT", "5/minute"))
async def check_register_limit(request: Request):
    return Response()


class RateLimitedRoute(APIRoute):
    def get_route_handler(self):
        original_handler = super().get_route_handler()
        check = {"/login": check_login_limit, "/process": check_process_limit,
                 "/register": check_register_limit}.get(self.path)

        async def handler(request: Request):
            if check is not None and request.method == "POST":
                await check(request)
            # Body parsing and validation occur here, after the one quota check.
            return await original_handler(request)

        return handler
