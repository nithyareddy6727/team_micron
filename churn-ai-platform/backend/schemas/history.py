from pydantic import BaseModel


class HistoryItem(BaseModel):
    id: int
    customer_id: str
    prediction: int
    probability: float
    confidence_score: float
    latency_ms: float
    risk: str
    risk_level: str
    model_version: str
    input_features: dict[str, object] | None = None
    timestamp: str


class HistoryData(BaseModel):
    total: int
    limit: int
    offset: int
    history: list[HistoryItem]
