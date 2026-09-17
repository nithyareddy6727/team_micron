from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes import routes
from utils.error_handlers import register_exception_handlers


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(routes.router)
    register_exception_handlers(app)
    return app


def _risk_bucket(probability: float) -> str:
    if probability >= 0.7:
        return "High"
    if probability >= 0.3:
        return "Medium"
    return "Low"


def test_e2e_predict_to_dashboard_and_analytics_consistency(monkeypatch) -> None:
    stored_events: list[dict[str, object]] = []

    class E2EPredictionService:
        model_loaded = True
        model_path = "ml/artifacts/root-artifacts/churn_model_optimized.pkl"
        inference_count = 0
        last_prediction_at = ""

        def predict(self, features, return_proba=True, explain=False):
            monthly = float(features.get("monthly_charges", 0.0))
            tenure = float(features.get("tenure", 0.0))
            probability = max(0.01, min(0.99, 0.2 + (monthly / 200.0) - (tenure / 240.0)))
            prediction = 1 if probability >= 0.5 else 0
            risk_level = _risk_bucket(probability)
            top_features = [
                {"feature": "monthly_charges", "impact": round(probability, 4)},
                {"feature": "tenure", "impact": round(1.0 - probability, 4)},
            ]
            return prediction, probability, risk_level, 0.9, top_features, 10.0, "v-e2e", None

        def save_prediction(self, **kwargs):
            stored_events.append(dict(kwargs))
            self.inference_count += 1
            self.last_prediction_at = "2026-01-01T00:00:00Z"
            return len(stored_events)

    def summary() -> dict[str, int | float]:
        high = medium = low = churn = non_churn = 0
        for event in stored_events:
            probability = float(event["probability"])
            prediction = int(event["prediction"])
            bucket = _risk_bucket(probability)
            if bucket == "High":
                high += 1
            elif bucket == "Medium":
                medium += 1
            else:
                low += 1
            if prediction == 1:
                churn += 1
            else:
                non_churn += 1

        total = len(stored_events)
        churn_rate = float(churn / total) if total else 0.0
        return {
            "total_predictions": total,
            "high_risk": high,
            "medium_risk": medium,
            "low_risk": low,
            "churn_count": churn,
            "non_churn_count": non_churn,
            "churn_rate": churn_rate,
        }

    def top_features(top_n=10, hours=24):
        aggregate: dict[str, list[float]] = {}
        for event in stored_events:
            for item in event.get("top_features") or []:
                feature = str(item.get("feature") or "")
                impact = float(item.get("impact") or 0.0)
                if not feature:
                    continue
                aggregate.setdefault(feature, []).append(abs(impact))

        ranked = [
            {"feature": name, "impact": float(sum(values) / len(values))}
            for name, values in aggregate.items()
        ]
        ranked.sort(key=lambda row: row["impact"], reverse=True)
        return ranked[:top_n]

    monkeypatch.setattr(routes, "prediction_service", E2EPredictionService())
    monkeypatch.setattr(routes, "track_prediction", lambda **kwargs: None)
    monkeypatch.setattr(routes, "is_database_connected", lambda: True)
    monkeypatch.setattr(routes, "fetch_total_customers_count", lambda: len({event["customer_id"] for event in stored_events}))
    monkeypatch.setattr(routes, "fetch_latest_prediction_summary", summary)
    monkeypatch.setattr(routes, "fetch_latest_risk_distribution", lambda: {"low": summary()["low_risk"], "medium": summary()["medium_risk"], "high": summary()["high_risk"]})
    monkeypatch.setattr(routes, "fetch_churn_vs_non_churn", lambda: {"churn": summary()["churn_count"], "non_churn": summary()["non_churn_count"]})
    monkeypatch.setattr(routes, "fetch_predictions_today_count", lambda: len(stored_events))
    monkeypatch.setattr(routes, "fetch_predictions_per_hour", lambda hours=24: [{"hour": "2026-01-01T10:00:00Z", "prediction_count": len(stored_events)}])
    monkeypatch.setattr(routes, "fetch_aggregated_top_feature_impacts", top_features)

    client = TestClient(_build_app())

    payload_a = {
        "customer_id": "cust_a",
        "features": {"customer_id": "cust_a", "monthly_charges": 95, "tenure": 4},
        "return_proba": True,
        "explain": True,
    }
    payload_b = {
        "customer_id": "cust_b",
        "features": {"customer_id": "cust_b", "monthly_charges": 30, "tenure": 40},
        "return_proba": True,
        "explain": True,
    }

    predict_a = client.post("/predict", json=payload_a)
    predict_b = client.post("/predict", json=payload_b)

    assert predict_a.status_code == 200
    assert predict_b.status_code == 200
    assert len(stored_events) == 2  # DB write simulation through persistence hook

    dashboard = client.get("/dashboard")
    analytics = client.get("/analytics")

    assert dashboard.status_code == 200
    assert analytics.status_code == 200

    dashboard_data = dashboard.json()["data"]
    analytics_data = analytics.json()["data"]

    assert dashboard_data["total_predictions"] == 2
    assert analytics_data["total_predictions"] == 2
    assert dashboard_data["risk_distribution"] == analytics_data["risk_distribution"]
    assert dashboard_data["churn_vs_nonchurn"] == analytics_data["churn_vs_nonchurn"]
    assert analytics_data["top_features"]
    feature_impacts = {row["feature"]: float(row["impact"]) for row in analytics_data["top_features"]}
    assert "monthly_charges" in feature_impacts
    assert "tenure" in feature_impacts
    assert feature_impacts["monthly_charges"] > 0.0
    assert feature_impacts["tenure"] > 0.0