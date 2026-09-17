from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StrictBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InteractionEvent(StrictBase):
    item_id: int
    interaction_value: float = Field(default=1.0)
    interacted_at: datetime | None = None


class RecommendRequest(StrictBase):
    user_id: int
    interaction_history: list[InteractionEvent] = Field(default_factory=list)
    top_n: int = Field(default=5, ge=1, le=100)


class RecommendationItem(StrictBase):
    item_id: int
    score: float


class RecommendResponse(StrictBase):
    user_id: int
    recommendations: list[RecommendationItem]
    model_version: str


class HealthResponse(StrictBase):
    service: str
    status: str
    model_loaded: bool
    model_version: str | None
    timestamp: str
