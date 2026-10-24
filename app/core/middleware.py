import time
import uuid

from fastapi import FastAPI
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, is_production: bool = False):
        super().__init__(app)
        self.is_production = is_production

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        if self.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; reload"
            )

        return response


class LoggingAndCorrelationMiddleware:
    """ASGI wrapper outside ServerErrorMiddleware, including 500 responses."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        try:
            correlation_id = str(
                uuid.UUID(headers.get(b"x-request-id", b"").decode("ascii"))
            )
        except (ValueError, UnicodeError):
            correlation_id = str(uuid.uuid4())
        scope.setdefault("state", {})["correlation_id"] = correlation_id
        start = time.perf_counter()
        status_code = 500

        async def send_with_id(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                message["headers"] = [
                    (k, v)
                    for k, v in message.get("headers", [])
                    if k.lower() != b"x-request-id"
                ]
                message["headers"].append(
                    (b"x-request-id", correlation_id.encode("ascii"))
                )
            await send(message)

        with logger.contextualize(correlation_id=correlation_id):
            logger.info(
                "request_started", event="request.started", method=scope["method"]
            )
            try:
                await self.app(scope, receive, send_with_id)
            except Exception as exc:
                logger.error(
                    "request_failed",
                    event="request.failed",
                    exception_type=type(exc).__name__,
                )
                raise
            finally:
                route = getattr(scope.get("route"), "path", "unmatched")
                log = (
                    logger.error
                    if status_code >= 500
                    else logger.warning
                    if status_code >= 400
                    else logger.info
                )
                log(
                    "request_completed",
                    event="request.completed",
                    method=scope["method"],
                    route=route,
                    status_code=status_code,
                    duration_ms=round((time.perf_counter() - start) * 1000, 2),
                )
                if status_code in (401, 403) or (
                    route.startswith("/api/v1/auth/") and status_code >= 400
                ):
                    logger.warning(
                        "authentication_denied",
                        event="auth.denied",
                        route=route,
                        status_code=status_code,
                    )
