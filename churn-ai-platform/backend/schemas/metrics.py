from pydantic import BaseModel

from schemas.observability import RequestSummary, SLOStatus


class MetricsResponse(BaseModel):
    service: str
    model_loaded: bool
    model_path: str
    inference_count: int
    uptime_seconds: float
    last_prediction_at: str
    request_summary: RequestSummary
    slo: SLOStatus
