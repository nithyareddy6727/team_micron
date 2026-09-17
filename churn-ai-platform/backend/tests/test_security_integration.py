from fastapi import FastAPI
from fastapi.testclient import TestClient

from utils.api_key_middleware import APIKeyMiddleware
from utils.error_handlers import register_exception_handlers
from utils.request_id_middleware import RequestIdMiddleware
from utils.security_middleware import PayloadLimitMiddleware, RateLimitMiddleware
from schemas.prediction import PredictionRequest


def _build_security_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(PayloadLimitMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(APIKeyMiddleware)
    register_exception_handlers(app)

    @app.post("/predict")
    def predict(payload: PredictionRequest):
        return {"success": True, "data": payload.model_dump(), "error": None}

    return app


def test_api_key_middleware_blocks_missing_key(monkeypatch) -> None:
    monkeypatch.setenv("API_KEY", "secret")
    monkeypatch.setenv("ENFORCE_API_KEY", "true")

    app = FastAPI()
    app.add_middleware(APIKeyMiddleware)

    @app.get("/customers")
    def customers():
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/customers")

    assert response.status_code == 401
    assert response.json()["success"] is False


def test_api_key_middleware_allows_valid_key(monkeypatch) -> None:
    monkeypatch.setenv("API_KEY", "secret")
    monkeypatch.setenv("ENFORCE_API_KEY", "true")

    app = FastAPI()
    app.add_middleware(APIKeyMiddleware)

    @app.post("/predict")
    def predict():
        return {"ok": True}

    client = TestClient(app)
    response = client.post("/predict", headers={"x-api-key": "secret"})

    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_api_key_middleware_rejects_wrong_key(monkeypatch) -> None:
    monkeypatch.setenv("API_KEY", "secret")
    monkeypatch.setenv("ENFORCE_API_KEY", "true")

    app = FastAPI()
    app.add_middleware(APIKeyMiddleware)

    @app.post("/predict")
    def predict():
        return {"ok": True}

    client = TestClient(app)
    response = client.post("/predict", headers={"x-api-key": "wrong"})

    assert response.status_code == 401
    assert response.json() == {"success": False, "error": "Unauthorized access"}


def test_payload_limit_blocks_large_input(monkeypatch) -> None:
    monkeypatch.setenv("API_KEY", "secret")
    monkeypatch.setenv("ENFORCE_API_KEY", "true")
    monkeypatch.setenv("MAX_PAYLOAD_BYTES", "256")

    client = TestClient(_build_security_app())
    response = client.post(
        "/predict",
        headers={"x-api-key": "secret"},
        json={"customer_id": "cust_1", "features": {"blob": "x" * 1024}, "return_proba": True, "explain": False},
    )

    assert response.status_code == 413
    assert response.json() == {"success": False, "error": "Payload too large"}


def test_invalid_schema_returns_contract_error(monkeypatch) -> None:
    monkeypatch.setenv("API_KEY", "secret")
    monkeypatch.setenv("ENFORCE_API_KEY", "true")
    monkeypatch.setenv("MAX_PAYLOAD_BYTES", "1048576")

    client = TestClient(_build_security_app())
    response = client.post(
        "/predict",
        headers={"x-api-key": "secret"},
        json={"customer_id": "cust_1", "tenure": 99, "monthly_charges": 250},
    )

    assert response.status_code == 422
    assert response.json()["success"] is False


def test_rate_limit_blocks_repeated_requests(monkeypatch) -> None:
    monkeypatch.setenv("API_KEY", "secret")
    monkeypatch.setenv("ENFORCE_API_KEY", "true")
    monkeypatch.setenv("RATE_LIMIT_MAX_REQUESTS", "1")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")

    client = TestClient(_build_security_app())
    headers = {"x-api-key": "secret"}

    first = client.post(
        "/predict",
        headers=headers,
        json={"customer_id": "cust_1", "features": {"customer_id": "cust_1"}, "return_proba": True, "explain": False},
    )
    second = client.post(
        "/predict",
        headers=headers,
        json={"customer_id": "cust_1", "features": {"customer_id": "cust_1"}, "return_proba": True, "explain": False},
    )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json() == {"success": False, "error": "Rate limit exceeded"}