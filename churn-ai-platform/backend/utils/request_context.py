from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any


request_id_context: ContextVar[str | None] = ContextVar("request_id_context", default=None)


def set_request_id(request_id: str) -> Token[str | None]:
    return request_id_context.set(request_id)


def get_request_id() -> str | None:
    return request_id_context.get()


def clear_request_id(token: Token[str | None] | None = None) -> None:
    if token is None:
        request_id_context.set(None)
        return

    request_id_context.reset(token)


class RequestIdFilter:
    def filter(self, record: Any) -> bool:
        record.request_id = get_request_id() or "-"
        return True