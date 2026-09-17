from typing import Generic, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class ApiEnvelope(BaseModel, Generic[T]):
    success: bool
    data: T
    error: str | None
