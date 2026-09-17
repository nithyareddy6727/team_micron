from pydantic import BaseModel


class RequestSummary(BaseModel):
    window_seconds: int
    request_count: int
    error_count: int
    error_rate: float
    latency_p95_ms: float
    latency_avg_ms: float


class SLOTargets(BaseModel):
    latency_p95_ms: float
    error_rate_max: float
    uptime_percent: float


class SLOCurrent(BaseModel):
    latency_p95_ms: float
    error_rate: float
    uptime_percent: float


class SLOStatusFlags(BaseModel):
    latency_ok: bool
    error_rate_ok: bool
    uptime_ok: bool
    overall_ok: bool


class SLOStatus(BaseModel):
    targets: SLOTargets
    current: SLOCurrent
    status: SLOStatusFlags
    window_seconds: int
    request_count: int


class PredictionsPerHourItem(BaseModel):
    hour: str
    prediction_count: int


class ChurnDistributionItem(BaseModel):
    risk_level: str
    count: int


class FeatureImpactItem(BaseModel):
    feature: str
    impact: float


class MetricsDashboardResponse(BaseModel):
    window_hours: int
    total_customers: int
    total_predictions: int
    churn_rate: float
    high_risk_count: int
    high_risk_percentage: float
    predictions_today: int
    risk_distribution: dict[str, int]
    churn_vs_nonchurn: dict[str, int]
    trend: list[PredictionsPerHourItem]
    predictions_per_hour: list[PredictionsPerHourItem]
    prediction_trend: list[PredictionsPerHourItem]
    churn_distribution: list[ChurnDistributionItem]
    high_risk_customers: list[dict[str, object]] = []


class AnalyticsResponse(BaseModel):
    window_hours: int
    total_customers: int
    total_predictions: int
    risk_distribution: dict[str, int]
    churn_vs_nonchurn: dict[str, int]
    trend: list[PredictionsPerHourItem]
    predictions_per_hour: list[PredictionsPerHourItem]
    top_features: list[FeatureImpactItem] = []


class ModelHealthResponse(BaseModel):
    status: str
    drift_score: float
    drift_detected: bool
    alerts_count: int
    current_predictions: dict[str, object]
    baseline_predictions: dict[str, object]
    current_features: dict[str, object]
    baseline_features: dict[str, object]
    alerts: list[dict[str, object]]


class RetrainResponse(BaseModel):
    status: str
    returncode: int | None = None
    output: dict[str, object] | None = None
    stderr: str | None = None