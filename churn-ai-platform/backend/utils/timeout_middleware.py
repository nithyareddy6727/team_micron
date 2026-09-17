from __future__ import annotations

import asyncio
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from utils.request_context import get_request_id


class TimeoutMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, timeout_seconds: float | None = None) -> None:
        super().__init__(app)
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else float(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))

    async def dispatch(self, request: Request, call_next):
        request_id = get_request_id()
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout_seconds)
        except TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"success": False, "error": "Request timed out"},
                headers={"X-Request-ID": request_id or getattr(request.state, "request_id", "-")},
            )