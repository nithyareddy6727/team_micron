from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from time import perf_counter

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.recommendation_schemas import (
    HealthResponse,
    RecommendRequest,
    RecommendResponse,
    RecommendationItem,
)
from app.services.model import CollaborativeFilteringModel


logger = logging.getLogger("recommendation-service")
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [request_id=%(request_id)s] %(message)s",
)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "n/a"
        return True


logger.addFilter(RequestIdFilter())

MODEL_DIR = Path(os.getenv("MODEL_ARTIFACT_DIR", "artifacts"))
MODEL_PATH = MODEL_DIR / "recommender.joblib"

app = FastAPI(title="Recommendation Service", version="1.0.0")
recommender = CollaborativeFilteringModel()


@app.on_event("startup")
def startup() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if not MODEL_PATH.exists():
        logger.warning(
            "model_not_found",
            extra={"request_id": "n/a"},
        )
        return

    try:
        recommender.load(str(MODEL_PATH))
        logger.info("model_loaded", extra={"request_id": "n/a"})
    except Exception:
        logger.exception("model_load_failed", extra={"request_id": "n/a"})


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request.state.request_id = request_id
    started = perf_counter()

    try:
        response = await call_next(request)
    except Exception as exc:
        logger.exception("request_failed", extra={"request_id": request_id})
        raise exc

    elapsed_ms = round((perf_counter() - started) * 1000, 3)
    response.headers["x-request-id"] = request_id
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} ({elapsed_ms}ms)",
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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "n/a")
    logger.exception("unhandled_exception", extra={"request_id": request_id})
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "request_id": request_id,
        },
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    loaded = recommender.artifacts is not None
    version = recommender.artifacts.model_version if loaded else None
    return HealthResponse(
        service="recommendation-service",
        status="healthy" if loaded else "degraded",
        model_loaded=loaded,
        model_version=version,
        timestamp=datetime.utcnow().isoformat(),
    )


@app.post("/recommend", response_model=RecommendResponse)
def recommend(payload: RecommendRequest) -> RecommendResponse:
    if recommender.artifacts is None:
        raise HTTPException(
            status_code=503,
            detail="Recommendation model is not loaded. Train and place recommender.joblib in artifacts/.",
        )

    try:
        interaction_history = [event.model_dump() for event in payload.interaction_history]
        recs = recommender.recommend(
            user_id=payload.user_id,
            interaction_history=interaction_history,
            top_n=payload.top_n,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    items = [RecommendationItem(item_id=int(r["item_id"]), score=float(r["score"])) for r in recs]
    return RecommendResponse(
        user_id=payload.user_id,
        recommendations=items,
        model_version=recommender.artifacts.model_version,
    )
