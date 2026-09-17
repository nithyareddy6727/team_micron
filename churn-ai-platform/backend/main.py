from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from routes.routes import prediction_service, router
from models.db import init_db
from utils.api_key_middleware import APIKeyMiddleware
from utils.error_handlers import register_exception_handlers
from utils.logging_config import setup_logging
from utils.mlflow_tracker import initialize_mlflow
from utils.env_config import get_bool_env, get_env
from utils.request_id_middleware import RequestIdMiddleware
from utils.request_logging_middleware import RequestLoggingMiddleware
from utils.security_middleware import PayloadLimitMiddleware, RateLimitMiddleware
from utils.timeout_middleware import TimeoutMiddleware

PLATFORM_ROOT = BACKEND_ROOT.parent
LOGS_DIR = PLATFORM_ROOT / "logs"
MLRUNS_DIR = PLATFORM_ROOT / "mlruns"

app = FastAPI(
    title="Churn Backend API",
    description="FastAPI backend for churn prediction platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(TimeoutMiddleware)
app.add_middleware(PayloadLimitMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(APIKeyMiddleware)
app.include_router(router)
register_exception_handlers(app)

# Prometheus instrumentation for request count, latency, and status/error distribution.
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.on_event("startup")
def startup_event() -> None:
    app_logger, _ = setup_logging(LOGS_DIR)
    app.state.app_logger = app_logger
    if get_bool_env("ENFORCE_API_KEY", default=False) and not get_env("API_KEY"):
        raise RuntimeError("ENFORCE_API_KEY is true but API_KEY is not set")
    initialize_mlflow(MLRUNS_DIR)
    try:
        init_db()
    except Exception as exc:
        app_logger.warning("Database initialization failed (%s); operating in fallback dataset mode", exc)
    if not prediction_service.model_loaded:
        raise RuntimeError("Model failed to load during startup")
    try:
        prediction_service.register_model_metadata()
    except Exception as exc:
        app_logger.warning("register_model_metadata skipped: %s", exc)
    app_logger.info(
        "model_ready | model_path=%s | model_version=%s",
        prediction_service.model_path,
        prediction_service.model_version,
    )
    app_logger.info("FastAPI startup complete | logs_dir=%s | mlruns_dir=%s", LOGS_DIR, MLRUNS_DIR)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Churn FastAPI backend is running"}
