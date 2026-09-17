from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_fastapi_instrumentator import Instrumentator

from routes import routes
from utils.error_handlers import register_exception_handlers


class SmokePredictionService:
    model_loaded = True
    model_path = "model.pkl"
    inference_count = 1
    last_prediction_at = "2026-01-01T00:00:00Z"

    def predict(self, features, return_proba=True, explain=False):
        return 1, 0.76, "High", 0.64, [], 15.2, "v-smoke", None

    def save_prediction(self, **kwargs):
        return 1


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(routes.router)
    register_exception_handlers(app)
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    return app


def test_smoke_health_predict_metrics(monkeypatch) -> None:
    monkeypatch.setattr(routes, "prediction_service", SmokePredictionService())
    monkeypatch.setattr(routes, "track_prediction", lambda **kwargs: None)
    monkeypatch.setattr(routes, "is_database_connected", lambda: True)

    client = TestClient(_build_app())

    health_response = client.get("/health")
    assert health_response.status_code == 200
    assert health_response.json()["success"] is True
    assert health_response.json()["data"]["status"] in {"running", "degraded"}

    predict_payload = {
        "customer_id": "CUST-UNKNOWN",
        "features": {
            "customer_id": "CUST-UNKNOWN",
            "Tenure": 9,
            "MonthlyCharges": 88.1,
            "age": 35,
            "Contract": "Month-to-month",
            "InternetService": "Fiber optic",
        },
        "return_proba": True,
        "explain": False,
    }
    predict_response = client.post("/predict", json=predict_payload)
    assert predict_response.status_code == 200
    assert predict_response.json()["success"] is True
    assert predict_response.json()["data"]["prediction"] in {0, 1}

    metrics_response = client.get("/metrics")
    assert metrics_response.status_code == 200
    assert "http_requests_total" in metrics_response.text
