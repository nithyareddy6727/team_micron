from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from models.db import insert_audit_log


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _safe_audit(request: Request, event_type: str, payload: dict[str, Any]) -> None:
    try:
        insert_audit_log(
            event_type=event_type,
            entity_type="security",
            entity_id=request.url.path,
            payload=payload,
            actor=_client_ip(request),
        )
    except Exception:
        pass


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.max_requests = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "120"))
        self.window_seconds = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _key(self, request: Request) -> str:
        return f"{_client_ip(request)}::{request.method.upper()}::{request.url.path}"

    def _is_allowed(self, key: str) -> bool:
        now = time.time()
        window_start = now - self.window_seconds

        with self._lock:
            q = self._events[key]
            while q and q[0] < window_start:
                q.popleft()

            if len(q) >= self.max_requests:
                return False

            q.append(now)
            return True

    async def dispatch(self, request: Request, call_next):
        if request.url.path in {"/health", "/metrics", "/"}:
            return await call_next(request)

        key = self._key(request)
        if not self._is_allowed(key):
            _safe_audit(
                request,
                "rate_limit_exceeded",
                {
                    "method": request.method,
                    "path": request.url.path,
                    "window_seconds": self.window_seconds,
                    "max_requests": self.max_requests,
                },
            )
            return JSONResponse(status_code=429, content={"success": False, "error": "Rate limit exceeded"})

        return await call_next(request)


class PayloadLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.max_payload_bytes = int(os.getenv("MAX_PAYLOAD_BYTES", str(1024 * 1024)))

    async def dispatch(self, request: Request, call_next):
        if request.method.upper() not in {"POST", "PUT", "PATCH"}:
            return await call_next(request)

        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_payload_bytes:
                    _safe_audit(
                        request,
                        "payload_too_large_header",
                        {
                            "method": request.method,
                            "path": request.url.path,
                            "content_length": int(content_length),
                            "max_payload_bytes": self.max_payload_bytes,
                        },
                    )
                    return JSONResponse(status_code=413, content={"success": False, "error": "Payload too large"})
            except ValueError:
                pass

        body = await request.body()
        if len(body) > self.max_payload_bytes:
            _safe_audit(
                request,
                "payload_too_large_body",
                {
                    "method": request.method,
                    "path": request.url.path,
                    "payload_bytes": len(body),
                    "max_payload_bytes": self.max_payload_bytes,
                },
            )
            return JSONResponse(status_code=413, content={"success": False, "error": "Payload too large"})

        return await call_next(request)