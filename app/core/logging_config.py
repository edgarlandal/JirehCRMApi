"""Structured logs: only controlled metadata, never request payloads."""

import json
import logging
import re
import sys
from datetime import timezone

from loguru import logger

SENSITIVE_KEYS = {
    "password",
    "token",
    "authorization",
    "secret",
    "api_key",
    "apikey",
    "cookie",
    "jwt",
}
JWT_PATTERN = re.compile(r"\beyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")


def redact_sensitive_data(value):
    if isinstance(value, dict):
        return {
            str(k): "[REDACTED]"
            if any(part in str(k).lower().replace("-", "_") for part in SENSITIVE_KEYS)
            else redact_sensitive_data(v)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_sensitive_data(v) for v in value]
    if isinstance(value, str):
        value = JWT_PATTERN.sub("[REDACTED]", value)
        value = re.sub(r"(?i)\bBearer\s+[^\s,;]+", "Bearer [REDACTED]", value)
        return re.sub(
            r"(?i)\b([\w-]*(?:password|token|secret|api[_-]?key|authorization)[\w-]*)\s*[:=]\s*(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)",
            r"\1=[REDACTED]",
            value,
        )
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return "[OMITTED]"


def json_formatter(record):
    extra = {k: v for k, v in record["extra"].items() if k != "serialized"}
    entry = {
        "timestamp": record["time"].astimezone(timezone.utc).isoformat(),
        "level": record["level"].name,
        "message": redact_sensitive_data(record["message"]),
        "correlation_id": extra.pop("correlation_id", None),
        "module": record["name"],
        "data": redact_sensitive_data(extra),
    }
    if record["exception"]:
        entry["exception_type"] = record["exception"].type.__name__
    record["extra"]["serialized"] = json.dumps(entry, ensure_ascii=True)
    record["exception"] = None
    return "{extra[serialized]}\n"


class InterceptHandler(logging.Handler):
    def emit(self, record):
        # External messages can embed SQL parameters, URLs and credentials.
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        logger.bind(source=record.name).opt(exception=record.exc_info).log(
            level, "external_log"
        )


def setup_logging():
    logger.remove()
    logger.add(
        sys.stdout, level="INFO", format=json_formatter, backtrace=False, diagnose=False
    )
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=True)
    for name in ("uvicorn", "uvicorn.error", "fastapi", "sqlalchemy.engine"):
        external = logging.getLogger(name)
        external.handlers = [InterceptHandler()]
        external.propagate = False
    access = logging.getLogger("uvicorn.access")
    access.handlers = [logging.NullHandler()]
    access.propagate = False
