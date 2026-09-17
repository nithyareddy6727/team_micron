from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(StrictBase):
    service: str
    status: str
    db_connected: bool
    active_model_version: str | None
    timestamp: str


class ActiveModelResponse(StrictBase):
    model_version: str
    model_type: str
    feature_version: str
    threshold_medium: float
    threshold_high: float
    validation_metric: str
    validation_score: float
    status: str
    updated_at: datetime | None = None


class ScoreRequest(StrictBase):
    customer_id: int
    feature_date: date | None = None
    horizon_days: int = Field(default=30, gt=0, le=365)


class ScoreWithFeaturesRequest(StrictBase):
    customer_id: int
    features: dict
    horizon_days: int = Field(default=30, gt=0, le=365)


class Driver(StrictBase):
    feature: str
    shap_value: float
    direction: Literal["increase", "decrease"]


class ScoreResponse(StrictBase):
    prediction_id: int
    customer_id: int
    score: float
    risk_band: Literal["low", "medium", "high"]
    model_version: str
    top_drivers: list[Driver]


class BatchScoreRequest(StrictBase):
    customer_ids: list[int] = Field(min_length=1, max_length=1000)
    feature_date: date | None = None
    horizon_days: int = Field(default=30, gt=0, le=365)


class BatchItemError(StrictBase):
    customer_id: int
    error: str


class BatchScoreResponse(StrictBase):
    results: list[ScoreResponse]
    errors: list[BatchItemError]


class ExplainResponse(StrictBase):
    prediction_id: int
    customer_id: int
    score: float
    risk_band: Literal["low", "medium", "high"]
    model_version: str
    feature_version: str
    feature_date: date
    top_drivers: list[Driver]
    prediction_ts: datetime


class TrainingStartRequest(StrictBase):
    model_type: Literal["xgboost", "logreg"] = "xgboost"
    feature_version: str = "v1"
    horizon_days: int = Field(default=30, gt=0, le=365)
    top_k_pct: float = Field(default=0.1, gt=0.0, le=1.0)
    set_as_production: bool = True


class TrainingStartResponse(StrictBase):
    run_id: str
    status: Literal["queued", "running", "failed", "completed"]


class TrainingRunStatus(StrictBase):
    run_id: str
    status: Literal["queued", "running", "failed", "completed"]
    message: str | None = None
    model_version: str | None = None


class RecommendationInteraction(StrictBase):
    item_id: int
    interaction_value: float = 1.0


class CandidateItem(StrictBase):
    item_id: int
    name: str = ""
    category: str = ""


class RecommendRequest(StrictBase):
    user_id: int
    interaction_history: list[RecommendationInteraction] = Field(default_factory=list)
    top_n: int = Field(default=5, ge=1, le=100)


class RecommendedItem(StrictBase):
    item_id: int
    score: float


class RecommendResponse(StrictBase):
    user_id: int
    recommendations: list[RecommendedItem]
    recommended_items: list[RecommendedItem] | None = None
    model_version: str
