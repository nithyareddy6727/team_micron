from __future__ import annotations

import statistics
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes import routes
from utils.error_handlers import register_exception_handlers
from utils.api_key_middleware import APIKeyMiddleware
from utils.request_id_middleware import RequestIdMiddleware
from utils.security_middleware import PayloadLimitMiddleware, RateLimitMiddleware


class PerfPredictionService:
    model_loaded = True
    model_path = "model.pkl"
    inference_count = 0
    last_prediction_at = "2026-01-01T00:00:00Z"

    def predict(self, features, return_proba=True, explain=False):
        start = time.perf_counter()
        time.sleep(0.003)
        latency_ms = (time.perf_counter() - start) * 1000.0
        self.inference_count += 1
        return 1, 0.87, "High Risk 🔴", 0.74, [], latency_ms, "v-perf", None

    def save_prediction(self, **kwargs):
        return 1


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(PayloadLimitMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(APIKeyMiddleware)
    app.include_router(routes.router)
    register_exception_handlers(app)
    return app


def test_prediction_latency_smoke(monkeypatch) -> None:
    monkeypatch.setenv("API_KEY", "secret")
    monkeypatch.setenv("ENFORCE_API_KEY", "true")
    monkeypatch.setattr(routes, "prediction_service", PerfPredictionService())
    monkeypatch.setattr(routes, "track_prediction", lambda **kwargs: None)

    client = TestClient(_build_app())
    headers = {"x-api-key": "secret"}
    samples: list[float] = []
    model_latencies: list[float] = []

    for _ in range(20):
        start = time.perf_counter()
        response = client.post(
            "/predict",
            headers=headers,
            json={"customer_id": "cust_1", "features": {"customer_id": "cust_1"}, "return_proba": True, "explain": False},
        )
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        body = response.json()
        samples.append(elapsed_ms)
        model_latencies.append(body["data"]["latency_ms"])
        assert response.status_code == 200
        assert body["success"] is True

    p95 = statistics.quantiles(samples, n=20)[-1]
    avg = statistics.mean(samples)
    model_avg = statistics.mean(model_latencies)

    report = {
        "requests": len(samples),
        "p95_ms": round(p95, 3),
        "avg_ms": round(avg, 3),
        "model_avg_ms": round(model_avg, 3),
    }
    print(report)

    assert p95 < 250.0
    assert model_avg < 100.0
