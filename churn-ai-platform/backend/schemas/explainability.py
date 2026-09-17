from __future__ import annotations

from pydantic import BaseModel, Field


class FeatureImpact(BaseModel):
    feature: str
    impact: float = Field(description="Signed SHAP impact for a prediction or mean absolute impact globally")


class ExplainabilitySummary(BaseModel):
    available: bool
    method: str
    model_version: str
    feature_count: int
    background_rows: int
    top_features: list[FeatureImpact]
