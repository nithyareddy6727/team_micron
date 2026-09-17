from __future__ import annotations

import logging

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from utils.request_context import get_request_id


def build_error_response(message: str, status_code: int = 500, request_id: str | None = None) -> JSONResponse:
    headers = {"X-Request-ID": request_id or get_request_id() or "-"}
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error": message},
        headers=headers,
    )


def register_exception_handlers(app) -> None:
    logger = logging.getLogger("churn_error")

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None) or get_request_id()
        logger.warning(
            "http_exception | status_code=%s | path=%s | request_id=%s | detail=%s",
            exc.status_code,
            request.url.path,
            request_id,
            exc.detail,
        )
        return build_error_response(str(exc.detail), status_code=exc.status_code, request_id=request_id)

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None) or get_request_id()
        logger.warning(
            "starlette_http_exception | status_code=%s | path=%s | request_id=%s | detail=%s",
            exc.status_code,
            request.url.path,
            request_id,
            exc.detail,
        )
        return build_error_response(str(exc.detail), status_code=exc.status_code, request_id=request_id)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None) or get_request_id()
        logger.warning(
            "validation_exception | path=%s | request_id=%s | errors=%s",
            request.url.path,
            request_id,
            exc.errors(),
        )
        return build_error_response("Invalid request payload", status_code=422, request_id=request_id)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None) or get_request_id()
        logger.exception(
            "unhandled_exception | path=%s | request_id=%s | message=%s",
            request.url.path,
            request_id,
            str(exc),
        )
        return build_error_response("Internal server error", status_code=500, request_id=request_id)