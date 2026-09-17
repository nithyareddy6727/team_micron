from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes import routes
from utils.error_handlers import register_exception_handlers


class StubPredictionService:
    model_loaded = True
    model_path = "model.pkl"
    inference_count = 1
    last_prediction_at = "2026-01-01T00:00:00Z"

    def predict(self, features, return_proba=True, explain=False):
        explanation = None
        top_features = []
        if explain:
            explanation = {
                "available": True,
                "method": "shap",
                "model_version": "v-test",
                "feature_count": 2,
                "background_rows": 10,
                "top_features": [
                    {"feature": "tenure_in_months", "impact": 0.34},
                    {"feature": "monthly_charge", "impact": -0.18},
                ],
            }
            top_features = explanation["top_features"]

        return 1, 0.81, "High Risk 🔴", 0.62, top_features, 123.4, "v-test", explanation

    def save_prediction(self, **kwargs):
        return 1

    def feature_importance(self, top_n=10):
        return {
            "available": True,
            "method": "shap",
            "model_version": "v-test",
            "feature_count": 2,
            "background_rows": 10,
            "top_features": [
                {"feature": "tenure_in_months", "impact": 0.34},
                {"feature": "monthly_charge", "impact": 0.18},
            ][:top_n],
        }


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(routes.router)
    register_exception_handlers(app)
    return app


def test_predict_endpoint_returns_contract(monkeypatch) -> None:
    monkeypatch.setattr(routes, "prediction_service", StubPredictionService())
    monkeypatch.setattr(routes, "track_prediction", lambda **kwargs: None)

    client = TestClient(_build_app())
    payload = {
        "customer_id": "cust_123",
        "features": {"customer_id": "cust_123"},
        "return_proba": True,
        "explain": False,
    }
    response = client.post("/predict", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    assert body["data"]["model_version"] == "v-test"
    assert body["data"]["latency_ms"] == 123.4
    assert body["data"]["explanation"] is None


def test_predict_endpoint_includes_explanation_when_requested(monkeypatch) -> None:
    monkeypatch.setattr(routes, "prediction_service", StubPredictionService())
    monkeypatch.setattr(routes, "track_prediction", lambda **kwargs: None)

    client = TestClient(_build_app())
    payload = {
        "customer_id": "cust_123",
        "features": {"customer_id": "cust_123"},
        "return_proba": True,
        "explain": True,
    }
    response = client.post("/predict", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["explanation"]["available"] is True
    assert body["data"]["top_features"][0]["feature"] == "tenure_in_months"


def test_predict_endpoint_accepts_flat_payload(monkeypatch) -> None:
    monkeypatch.setattr(routes, "prediction_service", StubPredictionService())
    monkeypatch.setattr(routes, "track_prediction", lambda **kwargs: None)

    client = TestClient(_build_app())
    payload = {
        "customer_id": "cust_123",
        "age": 37,
        "tenure": 12,
        "monthly_charges": 79.9,
        "contract": "month-to-month",
        "return_proba": True,
    }
    response = client.post("/predict", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["confidence"] == body["data"]["confidence_score"]
    assert body["data"]["latency"] == body["data"]["latency_ms"]


def test_metrics_dashboard_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(routes, "fetch_predictions_per_hour", lambda hours=24: [{"hour": "2026-01-01T10:00:00Z", "prediction_count": 5}])
    monkeypatch.setattr(routes, "fetch_churn_distribution", lambda hours=24: [{"risk_level": "High Risk 🔴", "count": 2}])

    client = TestClient(_build_app())
    response = client.get("/metrics/dashboard?hours=24")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["window_hours"] == 24
    assert body["data"]["predictions_per_hour"][0]["prediction_count"] == 5


def test_analytics_endpoint_includes_aggregated_top_features(monkeypatch) -> None:
    monkeypatch.setattr(routes, "fetch_total_customers_count", lambda: 3)
    monkeypatch.setattr(routes, "fetch_latest_prediction_summary", lambda: {
        "total_predictions": 5,
        "high_risk": 2,
        "medium_risk": 2,
        "low_risk": 1,
        "churn_count": 3,
        "non_churn_count": 2,
        "churn_rate": 0.6,
    })
    monkeypatch.setattr(routes, "fetch_latest_risk_distribution", lambda: {"low": 1, "medium": 2, "high": 2})
    monkeypatch.setattr(routes, "fetch_churn_vs_non_churn", lambda: {"churn": 3, "non_churn": 2})
    monkeypatch.setattr(routes, "fetch_predictions_per_hour", lambda hours=24: [{"hour": "2026-01-01T10:00:00Z", "prediction_count": 5}])
    monkeypatch.setattr(routes, "fetch_aggregated_top_feature_impacts", lambda top_n=10, hours=24: [{"feature": "monthly_charges", "impact": 0.42}])

    client = TestClient(_build_app())
    response = client.get("/analytics?hours=24")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["top_features"][0]["feature"] == "monthly_charges"
    assert body["data"]["top_features"][0]["impact"] == 0.42


def test_system_health_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(routes, "prediction_service", StubPredictionService())
    monkeypatch.setattr(routes, "is_database_connected", lambda: True)

    client = TestClient(_build_app())
    response = client.get("/system-health")

    assert response.status_code == 200
    body = response.json()
    assert body["model_loaded"] is True
    assert body["db_connected"] is True
    assert body["api_status"] == "OK"


def test_feature_importance_endpoint_returns_shap_summary(monkeypatch) -> None:
    monkeypatch.setattr(routes, "prediction_service", StubPredictionService())

    client = TestClient(_build_app())
    response = client.get("/explainability/feature-importance?top_n=2")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["available"] is True
    assert body["data"]["top_features"][0]["feature"] == "tenure_in_months"
