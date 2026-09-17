from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware

from services.observability_service import observability_service


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        started = time.perf_counter()
        app_logger = getattr(request.app.state, "app_logger", None)
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - started) * 1000.0
            observability_service.record_request(duration_ms=duration_ms, status_code=500)
            if app_logger is not None:
                app_logger.exception(
                    "request_error | method=%s | path=%s | status=500 | duration_ms=%.3f",
                    request.method,
                    request.url.path,
                    duration_ms,
                )
            raise

        duration_ms = (time.perf_counter() - started) * 1000.0
        observability_service.record_request(duration_ms=duration_ms, status_code=response.status_code)

        if app_logger is not None:
            app_logger.info(
                "request | method=%s | path=%s | status=%s | duration_ms=%.3f",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )

        return response