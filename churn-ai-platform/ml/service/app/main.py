from __future__ import annotations

import logging
import uuid
from datetime import datetime
from time import perf_counter

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.db import check_db, get_engine
from app.schemas import (
        RecommendRequest,
        RecommendResponse,
    ActiveModelResponse,
    BatchItemError,
    BatchScoreRequest,
    BatchScoreResponse,
    ExplainResponse,
    HealthResponse,
    ScoreRequest,
    ScoreResponse,
    ScoreWithFeaturesRequest,
    TrainingRunStatus,
    TrainingStartRequest,
    TrainingStartResponse,
)
from app.services.model_store import load_active_model
from app.services.recommendation_service import load_model_at_startup, recommend_items
from app.services.scoring_service import explain_prediction, score_customer
from app.services.scoring_service import score_customer_with_features
from app.services.training_service import create_run_id, get_training_run, run_training_job


logger = logging.getLogger("ml-service")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [request_id=%(request_id)s] %(message)s",
)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "n/a"
        return True


logger.addFilter(RequestIdFilter())

app = FastAPI(title=settings.app_name, version=settings.app_version)

metrics_state = {
    "request_count": 0,
    "error_count": 0,
    "latency_sum_ms": 0.0,
    "path_stats": {},
}


@app.on_event("startup")
def on_startup() -> None:
    load_model_at_startup()


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request.state.request_id = request_id
    started = perf_counter()

    try:
        response = await call_next(request)
    except Exception as exc:
        metrics_state["error_count"] += 1
        logger.exception("request_failed", extra={"request_id": request_id})
        raise exc

    elapsed_ms = (perf_counter() - started) * 1000
    metrics_state["request_count"] += 1
    metrics_state["latency_sum_ms"] += elapsed_ms
    path_key = request.url.path
    if path_key not in metrics_state["path_stats"]:
        metrics_state["path_stats"][path_key] = {"count": 0, "latency_sum_ms": 0.0}
    metrics_state["path_stats"][path_key]["count"] += 1
    metrics_state["path_stats"][path_key]["latency_sum_ms"] += elapsed_ms

    response.headers["x-request-id"] = request_id
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code}",
        extra={"request_id": request_id},
    )
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", "n/a")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "request_id": request_id,
        },
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    db_ok = False
    try:
        db_ok = check_db()
    except Exception:
        db_ok = False

    active = load_active_model()
    status = "healthy" if db_ok and active is not None else "degraded"
    return HealthResponse(
        service="ml-service",
        status=status,
        db_connected=db_ok,
        active_model_version=active.model_version if active else None,
        timestamp=datetime.utcnow().isoformat(),
    )


@app.get("/models/active", response_model=ActiveModelResponse)
def get_active_model() -> ActiveModelResponse:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT model_version, model_type, feature_version, threshold_medium, threshold_high,
                       validation_metric, validation_score, status, updated_at
                FROM model_registry
                WHERE status = 'production'
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """
            )
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="No production model found")

    return ActiveModelResponse(**row)


@app.post("/score", response_model=ScoreResponse)
def score(payload: ScoreRequest) -> ScoreResponse:
    return score_customer(
        customer_id=payload.customer_id,
        feature_date=payload.feature_date,
        horizon_days=payload.horizon_days,
    )


@app.post("/score/features", response_model=ScoreResponse)
def score_with_features(payload: ScoreWithFeaturesRequest) -> ScoreResponse:
    return score_customer_with_features(
        customer_id=payload.customer_id,
        features=payload.features,
        horizon_days=payload.horizon_days,
    )


@app.post("/score/batch", response_model=BatchScoreResponse)
def score_batch(payload: BatchScoreRequest) -> BatchScoreResponse:
    results: list[ScoreResponse] = []
    errors: list[BatchItemError] = []

    for customer_id in payload.customer_ids:
        try:
            result = score_customer(
                customer_id=customer_id,
                feature_date=payload.feature_date,
                horizon_days=payload.horizon_days,
            )
            results.append(result)
        except Exception as exc:
            errors.append(BatchItemError(customer_id=customer_id, error=str(exc)))

    return BatchScoreResponse(results=results, errors=errors)


@app.post("/recommend", response_model=RecommendResponse)
def recommend(payload: RecommendRequest) -> RecommendResponse:
    return recommend_items(payload)


@app.get("/predictions/{prediction_id}/explain", response_model=ExplainResponse)
def explain(prediction_id: int) -> ExplainResponse:
    data = explain_prediction(prediction_id)
    return ExplainResponse(**data)


@app.post("/training/start", response_model=TrainingStartResponse)
def start_training(payload: TrainingStartRequest, background_tasks: BackgroundTasks) -> TrainingStartResponse:
    run_id = create_run_id()
    background_tasks.add_task(
        run_training_job,
        run_id,
        payload.model_type,
        payload.feature_version,
        payload.horizon_days,
        payload.top_k_pct,
        payload.set_as_production,
    )
    return TrainingStartResponse(run_id=run_id, status="queued")


@app.get("/training/{run_id}", response_model=TrainingRunStatus)
def training_status(run_id: str) -> TrainingRunStatus:
    status = get_training_run(run_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"run_id={run_id} not found")
    return TrainingRunStatus(run_id=run_id, **status)


@app.get("/monitoring/metrics")
def monitoring_metrics() -> dict:
    count = metrics_state["request_count"]
    avg_latency = metrics_state["latency_sum_ms"] / count if count else 0.0
    by_path = {}
    for path, stat in metrics_state["path_stats"].items():
        p_count = stat["count"]
        by_path[path] = {
            "count": p_count,
            "avg_latency_ms": round(stat["latency_sum_ms"] / p_count, 3) if p_count else 0.0,
        }

    return {
        "request_count": count,
        "error_count": metrics_state["error_count"],
        "avg_latency_ms": round(avg_latency, 3),
        "path_stats": by_path,
    }
