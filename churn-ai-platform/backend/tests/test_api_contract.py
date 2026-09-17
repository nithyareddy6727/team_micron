from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes import routes
from utils.error_handlers import register_exception_handlers
from utils.api_key_middleware import APIKeyMiddleware
from utils.request_id_middleware import RequestIdMiddleware
from utils.security_middleware import PayloadLimitMiddleware, RateLimitMiddleware


class ContractPredictionService:
    model_loaded = True
    model_path = "model.pkl"
    inference_count = 7
    last_prediction_at = "2026-01-01T00:00:00Z"

    def predict(self, features, return_proba=True, explain=False):
        explanation = None
        top_features = []
        if explain:
            explanation = {
                "available": True,
                "method": "shap",
                "model_version": "v-contract",
                "feature_count": 3,
                "background_rows": 25,
                "top_features": [
                    {"feature": "tenure_in_months", "impact": 0.42},
                    {"feature": "monthly_charge", "impact": -0.21},
                ],
            }
            top_features = explanation["top_features"]

        return 1, 0.91, "High Risk 🔴", 0.82, top_features, 12.5, "v-contract", explanation

    def save_prediction(self, **kwargs):
        return 1

    def feature_importance(self, top_n=10):
        return {
            "available": True,
            "method": "shap",
            "model_version": "v-contract",
            "feature_count": 3,
            "background_rows": 25,
            "top_features": [
                {"feature": "tenure_in_months", "impact": 0.42},
                {"feature": "monthly_charge", "impact": 0.21},
            ][:top_n],
        }


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(PayloadLimitMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(APIKeyMiddleware)
    app.include_router(routes.router)
    register_exception_handlers(app)
    return app


def _assert_envelope(response_body: dict) -> None:
    assert set(response_body) == {"success", "data", "error"}
    assert response_body["success"] is True
    assert response_body["error"] is None


def test_contracts_for_core_endpoints(monkeypatch) -> None:
    monkeypatch.setenv("API_KEY", "secret")
    monkeypatch.setenv("ENFORCE_API_KEY", "true")
    monkeypatch.setenv("MAX_PAYLOAD_BYTES", "1048576")
    monkeypatch.setattr(routes, "prediction_service", ContractPredictionService())
    monkeypatch.setattr(routes, "track_prediction", lambda **kwargs: None)
    monkeypatch.setattr(routes.customer_service, "get_customers", lambda limit=100, offset=0: (1, [{"id": "cust_1", "customer_id": "cust_1", "name": "User One", "email": "u1@example.com", "age": 30, "gender": "Female", "tenure": 12, "monthly_charges": 49.5, "contract_type": "Month-to-month"}]))
    monkeypatch.setattr(routes, "fetch_history", lambda limit=100, offset=0: (1, [{"id": 1, "customer_id": "cust_1", "prediction": 1, "probability": 0.91, "confidence_score": 0.82, "latency_ms": 12.5, "risk_level": "High Risk 🔴", "model_version": "v-contract", "timestamp": "2026-01-01T00:00:00Z"}]))
    monkeypatch.setattr(routes, "fetch_predictions_per_hour", lambda hours=24: [{"hour": "2026-01-01T10:00:00Z", "prediction_count": 5}])
    monkeypatch.setattr(routes, "fetch_churn_distribution", lambda hours=24: [{"risk_level": "High Risk 🔴", "count": 1}])
    monkeypatch.setattr(routes, "is_database_connected", lambda: True)
    monkeypatch.setattr(routes.observability_service, "request_summary", lambda: {"window_seconds": 300, "request_count": 10, "error_count": 0, "error_rate": 0.0, "latency_p95_ms": 40.0, "latency_avg_ms": 20.0})
    monkeypatch.setattr(routes.observability_service, "slo_status", lambda dependencies_ok=True: {"targets": {"latency_p95_ms": 500.0, "error_rate_max": 0.01, "uptime_percent": 99.9}, "current": {"latency_p95_ms": 40.0, "error_rate": 0.0, "uptime_percent": 100.0}, "status": {"latency_ok": True, "error_rate_ok": True, "uptime_ok": True, "overall_ok": True}, "window_seconds": 300, "request_count": 10})

    client = TestClient(_build_app())
    headers = {"x-api-key": "secret"}

    customers = client.get("/customers", headers=headers)
    predict = client.post("/predict", headers=headers, json={"customer_id": "cust_1", "features": {"customer_id": "cust_1"}, "return_proba": True, "explain": True})
    batch = client.post("/predict/batch", headers=headers, json={"customer_ids": ["cust_1"]})
    metrics = client.get("/metrics/app", headers=headers)
    health = client.get("/health", headers=headers)

    for response in (customers, predict, batch, metrics, health):
        assert response.status_code == 200
        _assert_envelope(response.json())

    assert customers.json()["data"]["total"] == 1
    assert customers.json()["data"]["customers"][0]["id"] == "cust_1"
    assert predict.json()["data"]["model_version"] == "v-contract"
    assert predict.json()["data"]["explanation"]["available"] is True
    assert batch.json()["data"]["predictions"][0]["customer_id"] == "cust_1"
    assert metrics.json()["data"]["model_loaded"] is True
    assert health.json()["data"]["database_connected"] is True
