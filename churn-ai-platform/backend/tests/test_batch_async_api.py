from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes import routes
from utils.error_handlers import register_exception_handlers


class StubPredictionService:
    model_loaded = True
    model_path = "model.pkl"
    inference_count = 0
    last_prediction_at = None

    def predict(self, features, return_proba=True, explain=False):
        return 1, 0.77, "High", 0.54, [], 12.2, "v-async", None

    def save_prediction(self, **kwargs):
        return 1


class StubBatchQueueService:
    def submit(self, rows, run_prediction, return_proba, explain):
        return {
            "job_id": "job-123",
            "status": "queued",
            "submitted_at": "2026-01-01T00:00:00Z",
            "total_rows": len(rows),
        }

    def get_job(self, job_id):
        if job_id != "job-123":
            return None
        return {
            "job_id": "job-123",
            "status": "completed",
            "submitted_at": "2026-01-01T00:00:00Z",
            "started_at": "2026-01-01T00:00:01Z",
            "completed_at": "2026-01-01T00:00:02Z",
            "total_rows": 2,
            "processed_rows": 2,
            "successful_rows": 2,
            "failed_rows": 0,
            "results": [
                {
                    "row_index": 0,
                    "customer_id": "CUST-1001",
                    "prediction": 1,
                    "probability": 0.77,
                    "risk": "High",
                    "confidence": 0.54,
                    "latency_ms": 12.2,
                    "model_version": "v-async",
                    "explanation_text": None,
                }
            ],
            "errors": [],
        }


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(routes.router)
    register_exception_handlers(app)
    return app


def test_async_batch_submit_and_status(monkeypatch) -> None:
    monkeypatch.setattr(routes, "prediction_service", StubPredictionService())
    monkeypatch.setattr(routes, "track_prediction", lambda **kwargs: None)
    monkeypatch.setattr(routes, "batch_queue_service", StubBatchQueueService())

    client = TestClient(_build_app())

    response = client.post(
        "/predict/batch/async",
        json={
            "rows": [
                {"customer_id": "CUST-1001", "features": {"customer_id": "CUST-1001"}},
                {
                    "customer_id": "manual-input",
                    "features": {"age": 35, "tenure": 6, "monthly_charges": 81.2},
                },
            ],
            "return_proba": True,
            "explain": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["job_id"] == "job-123"

    status_response = client.get("/predict/batch/jobs/job-123")
    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["success"] is True
    assert status_body["data"]["status"] == "completed"
    assert status_body["data"]["processed_rows"] == 2


def test_csv_upload_batch_submit(monkeypatch) -> None:
    monkeypatch.setattr(routes, "prediction_service", StubPredictionService())
    monkeypatch.setattr(routes, "track_prediction", lambda **kwargs: None)
    monkeypatch.setattr(routes, "batch_queue_service", StubBatchQueueService())

    client = TestClient(_build_app())

    csv_payload = "customer_id,age,tenure,MonthlyCharges,Contract\nNEW-1,34,8,79.5,Month-to-month\n"
    response = client.post(
        "/predict/batch/upload?return_proba=true&explain=false",
        files={"file": ("batch.csv", csv_payload.encode("utf-8"), "text/csv")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["job_id"] == "job-123"
