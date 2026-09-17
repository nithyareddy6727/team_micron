from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, conlist, field_validator, model_validator

from schemas.explainability import ExplainabilitySummary, FeatureImpact


CustomerId = Annotated[str, StringConstraints(min_length=1, max_length=64, strip_whitespace=True, pattern=r"^[A-Za-z0-9_\-]+$")]
FeatureKey = Annotated[str, StringConstraints(min_length=1, max_length=64, strip_whitespace=True)]
FeatureStringValue = Annotated[str, StringConstraints(max_length=256)]


class PredictionRequest(BaseModel):
    customer_id: CustomerId | None = Field(default=None, description="Unique customer identifier")
    features: dict[FeatureKey, FeatureStringValue | int | float | bool] = Field(default_factory=dict, description="Customer features used for inference")
    age: int | None = Field(default=None, ge=0, le=120)
    tenure: int | None = Field(default=None, ge=0, le=72)
    monthly_charges: float | None = Field(default=None, ge=0, le=200)
    contract: str | None = Field(default=None, max_length=64)
    contract_type: str | None = Field(default=None, max_length=64)
    sector: str = Field(default="telecom", description="Business sector: saas, telecom, consumer")
    return_proba: bool = Field(default=True, description="Return probability if model supports it")
    explain: bool = Field(default=False, description="Enable SHAP explainability for this request")

    @model_validator(mode="after")
    def validate_customer_or_features(self) -> "PredictionRequest":
        # Backward-compatible input normalization:
        # accept both nested `features` and flat fields in one payload.
        if self.age is not None:
            self.features.setdefault("age", self.age)
        if self.tenure is not None:
            self.features.setdefault("tenure", self.tenure)
        if self.monthly_charges is not None:
            self.features.setdefault("monthly_charges", self.monthly_charges)

        normalized_contract = self.contract_type or self.contract
        if normalized_contract:
            self.features.setdefault("contract_type", normalized_contract)

        has_customer_id = bool(self.customer_id)
        has_features = bool(self.features)
        if not has_customer_id and not has_features:
            raise ValueError("Either customer_id or features must be provided")

        if self.customer_id and "customer_id" not in self.features:
            self.features["customer_id"] = self.customer_id

        return self

    @field_validator("features")
    @classmethod
    def validate_feature_count(cls, value: dict[FeatureKey, FeatureStringValue | int | float | bool]) -> dict[FeatureKey, FeatureStringValue | int | float | bool]:
        if len(value) > 100:
            raise ValueError("features exceeds maximum size of 100")
        return value


class BatchPredictionRequest(BaseModel):
    customer_ids: conlist(CustomerId, min_length=1, max_length=200) = Field(..., description="List of customer IDs")


class BatchPredictionRow(BaseModel):
    customer_id: CustomerId | None = Field(default=None)
    features: dict[FeatureKey, FeatureStringValue | int | float | bool] = Field(default_factory=dict)

    @model_validator(mode="after")
    def ensure_features(self) -> "BatchPredictionRow":
        if self.customer_id and "customer_id" not in self.features:
            self.features["customer_id"] = self.customer_id
        if not self.features:
            raise ValueError("Each batch row must include features or customer_id")
        return self


class AsyncBatchPredictionRequest(BaseModel):
    rows: conlist(BatchPredictionRow, min_length=1, max_length=2000) = Field(
        ..., description="Batch rows for asynchronous prediction"
    )
    return_proba: bool = True
    explain: bool = False
    sector: str = "telecom"


class AsyncBatchAccepted(BaseModel):
    job_id: str
    total_rows: int
    status: Literal["queued", "processing", "completed", "failed"]
    submitted_at: str


class BatchJobPredictionItem(BaseModel):
    row_index: int
    customer_id: str
    prediction: int
    probability: float
    risk: Literal["High", "Medium", "Low"]
    confidence: float
    latency_ms: float
    model_version: str
    explanation_text: str | None = None
    primary_driver: str | None = None
    recommended_action: str | None = None


class BatchJobErrorItem(BaseModel):
    row_index: int
    customer_id: str | None = None
    message: str


class AsyncBatchJobStatus(BaseModel):
    job_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    submitted_at: str
    started_at: str | None = None
    completed_at: str | None = None
    total_rows: int
    processed_rows: int
    successful_rows: int
    failed_rows: int
    results: list[BatchJobPredictionItem] = Field(default_factory=list)
    errors: list[BatchJobErrorItem] = Field(default_factory=list)


class PredictionResult(BaseModel):
    prediction: int
    prediction_label: Literal["Churn", "Not Churn"]
    probability: float
    risk: Literal["High", "Medium", "Low"]
    risk_level: Literal["High", "Medium", "Low"]
    confidence_score: float
    confidence: float
    confidence_label: Literal["High", "Medium", "Low"]
    latency_ms: float
    latency: float
    model_version: str
    top_features: list[FeatureImpact]
    feature_importance: list[FeatureImpact] = Field(default_factory=list)
    explanation_text: str | None = None
    explanation: ExplainabilitySummary | None = None
    sector: str = "telecom"
    primary_driver: str | None = None
    recommendations: list[str] = Field(default_factory=list)


class BatchPredictionItem(BaseModel):
    customer_id: str
    prediction: int
    probability: float
    risk: Literal["High", "Medium", "Low"]
    risk_level: str
    confidence_score: float
    latency_ms: float
    model_version: str
    timestamp: str
    primary_driver: str | None = None
    recommended_action: str | None = None


class BatchPredictionData(BaseModel):
    predictions: list[BatchPredictionItem]
