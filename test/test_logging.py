import asyncio
import io
import json
import logging
import unittest
import uuid
from contextlib import redirect_stdout

from loguru import logger

from app.core.logging_config import setup_logging
from app.core.middleware import LoggingAndCorrelationMiddleware


class LoggingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.output = io.StringIO()
        with redirect_stdout(self.output):
            setup_logging()

    def tearDown(self):
        logger.remove()

    def records(self):
        return [json.loads(line) for line in self.output.getvalue().splitlines()]

    async def test_sensitive_data_and_exception(self):
        logger.info(
            "password=hidden Bearer opaque eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.signature"
        )
        logger.info(
            "safe_event", nested=[{"password": "private", "refresh_token": "opaque"}]
        )
        try:
            raise ValueError("secret exception text")
        except ValueError:
            logger.exception("operation_failed")
            logging.getLogger("example").exception("password=hidden")
        result = self.output.getvalue()
        for secret in (
            "private",
            "opaque",
            "secret exception text",
            "password=hidden",
            "eyJhbGci",
        ):
            self.assertNotIn(secret, result)
        self.assertEqual(self.records()[2]["exception_type"], "ValueError")

    async def test_fastapi_errors_keep_correlation(self):
        from fastapi import FastAPI, HTTPException

        api = FastAPI()

        @api.get("/items/{item_id}")
        async def item(item_id: str):
            if item_id == "denied":
                raise HTTPException(status_code=401, detail="private")
            raise ValueError("private")

        for path, status in [("/items/denied", 401), ("/items/private", 500)]:
            messages = []

            async def send(message):
                messages.append(message)

            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}

            scope = {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": path,
                "root_path": "",
                "query_string": b"",
                "headers": [],
                "server": ("test", 80),
                "client": ("test", 1),
            }
            try:
                await LoggingAndCorrelationMiddleware(api)(scope, receive, send)
            except ValueError:
                pass
            self.assertEqual(messages[0]["status"], status)
            uuid.UUID(dict(messages[0]["headers"])[b"x-request-id"].decode())
        self.assertNotIn("private", self.output.getvalue())
        self.assertTrue(
            any(r["data"].get("event") == "auth.denied" for r in self.records())
        )
        self.assertTrue(
            any(r["data"].get("route") == "/items/{item_id}" for r in self.records())
        )

    async def test_concurrent_requests_and_error_header(self):
        async def endpoint(scope, receive, send):
            await asyncio.sleep(0)
            logger.info("inside")
            await send(
                {
                    "type": "http.response.start",
                    "status": 500 if scope["path"] == "/error" else 200,
                    "headers": [],
                }
            )
            await send({"type": "http.response.body", "body": b""})
            if scope["path"] == "/error":
                raise RuntimeError("password=private")

        async def request(identifier, path):
            messages = []

            async def send(message):
                messages.append(message)

            scope = {
                "type": "http",
                "method": "GET",
                "path": path,
                "headers": [(b"x-request-id", identifier)],
                "query_string": b"access_token=private",
            }
            try:
                await LoggingAndCorrelationMiddleware(endpoint)(scope, None, send)
            except RuntimeError:
                pass
            return dict(messages[0]["headers"])[b"x-request-id"].decode()

        expected = str(uuid.uuid4())
        ids = await asyncio.gather(
            request(expected.encode(), "/ok"), request(b"password=private", "/error")
        )
        self.assertEqual(ids[0], expected)
        uuid.UUID(ids[1])
        self.assertNotEqual(*ids)
        records = self.records()
        completed = [r for r in records if r["message"] == "request_completed"]
        self.assertEqual({r["correlation_id"] for r in completed}, set(ids))
        self.assertTrue(all(0 <= r["data"]["duration_ms"] < 1000 for r in completed))
        self.assertNotIn("private", self.output.getvalue())
        logger.info("outside")
        self.assertIsNone(self.records()[-1]["correlation_id"])


if __name__ == "__main__":
    unittest.main()
