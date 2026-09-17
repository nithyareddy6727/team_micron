from __future__ import annotations

import os
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from models.db import insert_audit_log
from utils.env_config import get_bool_env, get_env


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class APIKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.api_key = get_env("API_KEY")
        self.enforce_api_key = get_bool_env("ENFORCE_API_KEY", default=False)
        self.protected_routes = {
            ("POST", "/predict"),
            ("POST", "/predict/batch"),
            ("GET", "/customers"),
            ("GET", "/history"),
        }

    def _audit(self, request: Request, event_type: str, payload: dict[str, Any]) -> None:
        try:
            insert_audit_log(
                event_type=event_type,
                entity_type="security",
                entity_id=request.url.path,
                payload=payload,
                actor=_client_ip(request),
            )
        except Exception:
            # Security controls must not fail closed due to audit write issues.
            pass

    async def dispatch(self, request: Request, call_next):
        if not self.enforce_api_key:
            return await call_next(request)

        route_key = (request.method.upper(), request.url.path)
        if route_key in self.protected_routes:
            if not self.api_key:
                self._audit(
                    request,
                    "api_key_missing_server_config",
                    {
                        "method": request.method,
                        "path": request.url.path,
                    },
                )
                return JSONResponse(status_code=500, content={"success": False, "error": "API key is not configured on server"})

            provided_key = request.headers.get("x-api-key")
            if not provided_key or provided_key != self.api_key:
                self._audit(
                    request,
                    "api_key_validation_failed",
                    {
                        "method": request.method,
                        "path": request.url.path,
                        "has_key": bool(provided_key),
                    },
                )
                return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized access"})

            self._audit(
                request,
                "api_key_validation_passed",
                {
                    "method": request.method,
                    "path": request.url.path,
                },
            )

        return await call_next(request)
