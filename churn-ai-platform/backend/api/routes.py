from __future__ import annotations

import logging
import asyncio
import csv
import io
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect

from models.db import (
    fetch_aggregated_top_feature_impacts,
    fetch_churn_vs_non_churn,
    fetch_churn_distribution,
    fetch_history,
    fetch_latest_prediction_summary,
    fetch_latest_risk_distribution,
    fetch_predictions_today_count,
    fetch_predictions_per_hour,
    fetch_total_customers_count,
    is_database_connected,
)
from schemas.common import ApiEnvelope
from schemas.customer import CustomersData
from schemas.explainability import ExplainabilitySummary
from schemas.health import HealthResponse, SystemHealthResponse
from schemas.history import HistoryData
from schemas.metrics import MetricsResponse
from schemas.observability import AnalyticsResponse, MetricsDashboardResponse, ModelHealthResponse, RetrainResponse, SLOStatus
from schemas.prediction import (
    AsyncBatchAccepted,
    AsyncBatchJobStatus,
    AsyncBatchPredictionRequest,
    BatchPredictionData,
    BatchPredictionItem,
    BatchPredictionRequest,
    PredictionRequest,
    PredictionResult,
)
from services.batch_queue_service import batch_queue_service
from services.customer_service import CustomerService
from services.ml_monitoring_service import MLMonitoringService
from services.metrics_service import MetricsService
from services.observability_service import observability_service
from services.prediction_service import PredictionService
from services.powerbi_service import powerbi_service
from services.retraining_service import retraining_service
from services.recommendation_service import recommendation_service
from utils.mlflow_tracker import track_prediction

router = APIRouter()

prediction_service = PredictionService()
customer_service = CustomerService()
metrics_service = MetricsService()
ml_monitoring_service = MLMonitoringService()
app_logger = logging.getLogger("churn_app")


def _coerce_number(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    raw = str(value).strip()
    if raw == "":
        return value
    try:
        numeric = float(raw)
        return int(numeric) if numeric.is_integer() else numeric
    except ValueError:
        return value


def _pick_feature(features: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in features and features.get(key) not in (None, ""):
            return features.get(key)
    return None


def _normalize_prediction_features(raw_features: dict[str, Any], customer_id: str) -> dict[str, Any]:
    features = {
        str(key): value
        for key, value in dict(raw_features or {}).items()
        if value is not None
    }

    if customer_id:
        features["customer_id"] = customer_id

    age = _pick_feature(features, ["age", "Age"])
    tenure = _pick_feature(features, ["tenure", "Tenure", "tenure_in_months", "TenureMonths"])
    monthly_charges = _pick_feature(
        features,
        ["monthly_charges", "monthly_charge", "MonthlyCharges", "MonthlyCharge", "monthlyCharges"],
    )

    contract_type = _pick_feature(features, ["contract_type", "contract", "Contract"])
    internet_service = _pick_feature(features, ["internet_service", "InternetService"])
    payment_method = _pick_feature(features, ["payment_method", "PaymentMethod"])

    if age is not None:
        features["age"] = _coerce_number(age)
    if tenure is not None:
        coerced_tenure = _coerce_number(tenure)
        features["tenure"] = coerced_tenure
        features.setdefault("tenure_in_months", coerced_tenure)
    if monthly_charges is not None:
        coerced_monthly = _coerce_number(monthly_charges)
        features["monthly_charges"] = coerced_monthly
        features.setdefault("monthly_charge", coerced_monthly)

    if contract_type is not None:
        features["contract_type"] = str(contract_type)
    if internet_service is not None:
        features["internet_service"] = str(internet_service)
        features.setdefault("InternetService", str(internet_service))
    if payment_method is not None:
        features["payment_method"] = str(payment_method)
        features.setdefault("PaymentMethod", str(payment_method))

    return features


def _normalize_error_message(message: str) -> str:
    lower = str(message).lower()
    if "missing required features" in lower:
        return (
            "Missing required features for prediction. Provide age, tenure, and monthly_charges, "
            "or use a known customer_id from your dataset."
        )
    if "not found" in lower:
        return (
            "customer_id was not found. Manual prediction is supported, but you must provide the required "
            "features: age, tenure, and monthly_charges."
        )
    return message


def _normalize_risk_bucket(risk_level: str) -> str:
    lowered = str(risk_level).lower()
    if "high" in lowered:
        return "High"
    if "medium" in lowered:
        return "Medium"
    return "Low"


def _normalize_risk_distribution(value: object) -> dict[str, int]:
    if isinstance(value, dict):
        return {
            "low": int(value.get("low") or value.get("Low") or 0),
            "medium": int(value.get("medium") or value.get("Medium") or 0),
            "high": int(value.get("high") or value.get("High") or 0),
        }

    distribution = {"low": 0, "medium": 0, "high": 0}
    for item in value or []:
        bucket = str((item or {}).get("risk_level") or (item or {}).get("risk") or "").lower()
        if "high" in bucket:
            distribution["high"] += int((item or {}).get("count") or 0)
        elif "medium" in bucket:
            distribution["medium"] += int((item or {}).get("count") or 0)
        else:
            distribution["low"] += int((item or {}).get("count") or 0)
    return distribution


def _normalize_churn_split(value: object) -> dict[str, int]:
    if isinstance(value, dict):
        return {
            "churn": int(value.get("churn") or value.get("Churn") or 0),
            "non_churn": int(value.get("non_churn") or value.get("nonChurn") or value.get("Non-Churn") or 0),
        }

    churn = non_churn = 0
    for item in value or []:
        label = str((item or {}).get("name") or (item or {}).get("label") or "").lower()
        count = int((item or {}).get("count") or 0)
        if "churn" == label:
            churn = count
        elif "non" in label:
            non_churn = count
    return {"churn": churn, "non_churn": non_churn}


def _normalize_trend(value: object) -> list[dict[str, object]]:
    trend: list[dict[str, object]] = []
    for item in value or []:
        if isinstance(item, dict):
            trend.append({
                "hour": str(item.get("hour") or item.get("timestamp") or item.get("label") or ""),
                "prediction_count": int(item.get("prediction_count") or item.get("count") or item.get("value") or 0),
            })
    return trend


def _population_metrics() -> dict[str, Any]:
    if hasattr(prediction_service, "population_summary"):
        try:
            summary = prediction_service.population_summary()
            return {
                "total_customers": int(summary.get("total_customers") or 0),
                "total_predictions": int(summary.get("total_predictions") or 0),
                "risk_distribution": _normalize_risk_distribution(summary.get("risk_distribution") or {}),
                "churn_vs_non_churn": _normalize_churn_split(summary.get("churn_vs_nonchurn") or {}),
                "high_risk_count": int(summary.get("high_risk_count") or 0),
                "high_risk_percentage": float(summary.get("high_risk_percentage") or 0.0),
            }
        except Exception:
            app_logger.exception("population_summary_failed | fallback=event_history")

    latest_summary = fetch_latest_prediction_summary()
    risk_distribution = _normalize_risk_distribution(fetch_latest_risk_distribution())
    total_predictions = int(latest_summary["total_predictions"])
    high_risk_count = int(latest_summary["high_risk"])
    high_risk_percentage = float((high_risk_count / total_predictions) * 100) if total_predictions else 0.0
    return {
        "total_customers": fetch_total_customers_count(),
        "total_predictions": total_predictions,
        "risk_distribution": risk_distribution,
        "churn_vs_non_churn": _normalize_churn_split(fetch_churn_vs_non_churn()),
        "high_risk_count": high_risk_count,
        "high_risk_percentage": high_risk_percentage,
    }


def _build_explanation_text(risk_level: str, top_features: list[dict[str, Any]]) -> str:
    if not top_features:
        return f"Risk classified as {risk_level.lower()} based on the model output."

    ranked_features = [str(item.get("feature") or item.get("name") or "feature") for item in top_features[:3]]
    if len(ranked_features) == 1:
        detail = ranked_features[0]
    elif len(ranked_features) == 2:
        detail = f"{ranked_features[0]} and {ranked_features[1]}"
    else:
        detail = f"{ranked_features[0]}, {ranked_features[1]}, and {ranked_features[2]}"

    return f"Risk classified as {risk_level.lower()} with the strongest drivers coming from {detail}."


def _run_prediction_flow(
    customer_id: str,
    features: dict[str, Any],
    return_proba: bool,
    explain: bool,
    sector: str = "telecom",
) -> PredictionResult:
    try:
        pred_res = prediction_service.predict(
            features=features,
            return_proba=return_proba,
            explain=explain,
            sector=sector,
        )
    except TypeError:
        pred_res = prediction_service.predict(
            features=features,
            return_proba=return_proba,
            explain=explain,
        )

    if len(pred_res) >= 10:
        prediction, probability, risk_level, confidence_score, top_features, latency_ms, model_version, explanation, primary_driver, recommendations = pred_res[:10]
    else:
        prediction, probability, risk_level, confidence_score, top_features, latency_ms, model_version, explanation = pred_res[:8]
        primary_driver = None
        recommendations = []

    if not recommendations or not primary_driver:
        calc_driver, calc_recs = recommendation_service.generate_recommendations(
            sector_id=sector,
            probability=probability,
            risk_level=risk_level,
            top_features=top_features or [],
            customer_features=features,
        )
        if not recommendations:
            recommendations = calc_recs
        if not primary_driver:
            primary_driver = calc_driver

    prediction_service.save_prediction(
        customer_id=customer_id,
        prediction=prediction,
        probability=probability,
        risk_level=risk_level,
        confidence_score=confidence_score,
        latency_ms=latency_ms,
        top_features=top_features,
        input_features=features,
        model_version=model_version,
    )

    track_prediction(
        model_version=model_version,
        customer_id=customer_id,
        prediction=prediction,
        probability=probability,
        latency_ms=latency_ms,
        risk_level=risk_level,
        confidence_score=confidence_score,
        features=features,
    )

    normalized_risk = _normalize_risk_bucket(risk_level)
    prediction_label = "Churn" if int(prediction) == 1 else "Not Churn"
    confidence_label = "High" if confidence_score >= 0.67 else "Medium" if confidence_score >= 0.34 else "Low"
    return PredictionResult(
        prediction=prediction,
        prediction_label=prediction_label,
        probability=probability,
        risk=normalized_risk,
        risk_level=normalized_risk,
        confidence_score=confidence_score,
        confidence=confidence_score,
        confidence_label=confidence_label,
        latency_ms=latency_ms,
        latency=latency_ms,
        model_version=model_version,
        top_features=top_features,
        feature_importance=top_features,
        explanation_text=_build_explanation_text(normalized_risk, top_features),
        explanation=explanation,
        sector=sector,
        primary_driver=primary_driver,
        recommendations=recommendations,
    )


def _run_prediction_flow_as_dict(features: dict[str, Any], return_proba: bool, explain: bool, sector: str = "telecom") -> dict[str, Any]:
    customer_id = str(features.get("customer_id") or "manual-input")
    normalized = _normalize_prediction_features(features, customer_id)
    result = _run_prediction_flow(
        customer_id=customer_id,
        features=normalized,
        return_proba=return_proba,
        explain=explain,
        sector=sector,
    )
    return {
        "prediction": result.prediction,
        "prediction_label": result.prediction_label,
        "probability": result.probability,
        "risk": result.risk,
        "confidence": result.confidence,
        "confidence_label": result.confidence_label,
        "latency_ms": result.latency_ms,
        "model_version": result.model_version,
        "explanation_text": result.explanation_text,
        "primary_driver": result.primary_driver,
        "recommended_action": result.recommendations[0] if result.recommendations else None,
        "recommendations": result.recommendations,
    }


def _rows_from_csv_payload(content: bytes) -> list[dict[str, Any]]:
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict[str, Any]] = []
    for row in reader:
        cleaned = {str(k): v for k, v in (row or {}).items() if k and v not in (None, "")}
        customer_id = str(cleaned.get("customer_id") or cleaned.get("CustomerID") or "manual-input")
        rows.append(
            {
                "customer_id": customer_id,
                "features": _normalize_prediction_features(cleaned, customer_id),
            }
        )
    return rows


@router.post("/predict", response_model=ApiEnvelope[PredictionResult])
def predict(payload: PredictionRequest) -> ApiEnvelope[PredictionResult]:
    customer_id = str(payload.customer_id or payload.features.get("customer_id") or "manual-input")
    features = _normalize_prediction_features(dict(payload.features or {}), customer_id)
    app_logger.info("incoming_request | route=/predict | method=POST | customer_id=%s", customer_id)
    
    # END-TO-END TRACE LOGGING
    app_logger.info("=" * 80)
    app_logger.info("STEP 2: Backend receives API request - Starting prediction pipeline")
    app_logger.info("  Customer ID: %s", customer_id)
    app_logger.info("  Request payload keys: %s", list(features.keys()) if features else "none")
    app_logger.info("  Return proba: %s | Explain: %s", payload.return_proba, payload.explain)

    sector = str(getattr(payload, "sector", None) or "telecom").strip().lower()
    try:
        app_logger.info("STEP 3: ML Model prediction starting | sector=%s", sector)
        response_data = _run_prediction_flow(
            customer_id=customer_id,
            features=features,
            return_proba=payload.return_proba,
            explain=payload.explain,
            sector=sector,
        )
        app_logger.info("STEP 3 COMPLETE: ML Model prediction returned")
        app_logger.info("  Prediction: %s | Probability: %.6f | Risk: %s | Latency: %.2f ms", 
            response_data.prediction, response_data.probability, response_data.risk_level, response_data.latency_ms)
        
    except ValueError as exc:
        message = _normalize_error_message(str(exc))
        status = 404 if "not found" in message.lower() else 400
        app_logger.error("route_error | route=/predict | customer_id=%s | status=%s | message=%s", customer_id, status, message)
        app_logger.error("STEP 3/4 ERROR: Prediction failed with ValueError (status %d): %s", status, message)
        raise HTTPException(status_code=status, detail=message) from exc
    except Exception as exc:
        app_logger.error("route_error | route=/predict | customer_id=%s | status=500 | message=%s", customer_id, str(exc), exc_info=True)
        app_logger.error("STEP 3/4 CRITICAL ERROR: Unexpected exception: %s", str(exc), exc_info=True)
        raise

    # STEP 4: Build response
    app_logger.info("STEP 4: Building API response")
    
    app_logger.info("STEP 5: Sending API response to Frontend")
    app_logger.info("  Response: prediction=%s | probability=%.6f | risk=%s", 
        response_data.prediction, response_data.probability, response_data.risk_level)
    app_logger.info("outgoing_response | route=/predict | method=POST | status=200 | customer_id=%s", customer_id)
    app_logger.info("=" * 80)

    return ApiEnvelope[PredictionResult](
        success=True,
        data=response_data,
        error=None,
    )


@router.websocket("/ws/predict")
async def websocket_predict(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            payload = await ws.receive_json()
            customer_id = str(payload.get("customer_id") or payload.get("features", {}).get("customer_id") or "manual-input")
            features = _normalize_prediction_features(dict(payload.get("features") or {}), customer_id)

            try:
                result = await asyncio.to_thread(
                    _run_prediction_flow,
                    customer_id,
                    features,
                    bool(payload.get("return_proba", True)),
                    bool(payload.get("explain", True)),
                )
                await ws.send_json({"success": True, "data": result.model_dump(), "error": None})
            except Exception as exc:
                await ws.send_json({"success": False, "data": None, "error": str(exc)})
    except WebSocketDisconnect:
        return


@router.post("/predict/batch", response_model=ApiEnvelope[BatchPredictionData])
def predict_batch(payload: BatchPredictionRequest) -> ApiEnvelope[BatchPredictionData]:
    app_logger.info("incoming_request | route=/predict/batch | method=POST | batch_size=%s", len(payload.customer_ids))
    rows: list[BatchPredictionItem] = []
    for customer_id in payload.customer_ids:
        cid = str(customer_id)

        features = {"customer_id": customer_id}
        try:
            pred_res = prediction_service.predict(
                features=features,
                return_proba=True,
                explain=False,
            )
            prediction = pred_res[0]
            probability = pred_res[1]
            risk_level = pred_res[2]
            confidence_score = pred_res[3]
            top_features = pred_res[4]
            latency_ms = pred_res[5]
            model_version = pred_res[6]
            primary_driver = pred_res[8] if len(pred_res) > 8 else None
            recommendations = pred_res[9] if len(pred_res) > 9 else []
            if not recommendations or not primary_driver:
                calc_driver, calc_recs = recommendation_service.generate_recommendations(
                    sector_id="telecom",
                    probability=probability,
                    risk_level=risk_level,
                    top_features=top_features or [],
                    customer_features=features,
                )
                if not recommendations:
                    recommendations = calc_recs
                if not primary_driver:
                    primary_driver = calc_driver
            recommended_action = recommendations[0] if recommendations else None

            prediction_service.save_prediction(
                customer_id=cid,
                prediction=prediction,
                probability=probability,
                risk_level=risk_level,
                confidence_score=confidence_score,
                latency_ms=latency_ms,
                input_features=features,
                model_version=model_version,
            )
        except ValueError as exc:
            message = str(exc)
            status = 404 if "not found" in message.lower() else 400
            app_logger.error("route_error | route=/predict/batch | customer_id=%s | status=%s | message=%s", cid, status, message)
            raise HTTPException(status_code=status, detail=message) from exc

        timestamp = datetime.now(timezone.utc).isoformat()
        rows.append(
            BatchPredictionItem(
                customer_id=cid,
                prediction=prediction,
                probability=probability,
                risk=_normalize_risk_bucket(risk_level),
                risk_level=risk_level,
                confidence_score=confidence_score,
                latency_ms=latency_ms,
                model_version=model_version,
                timestamp=timestamp,
                primary_driver=primary_driver,
                recommended_action=recommended_action,
            )
        )

    app_logger.info("outgoing_response | route=/predict/batch | method=POST | status=200 | processed=%s", len(rows))
    return ApiEnvelope[BatchPredictionData](
        success=True,
        data=BatchPredictionData(predictions=rows),
        error=None,
    )


@router.post("/predict/batch/async", response_model=ApiEnvelope[AsyncBatchAccepted])
def predict_batch_async(payload: AsyncBatchPredictionRequest) -> ApiEnvelope[AsyncBatchAccepted]:
    rows = [row.model_dump() for row in payload.rows]
    job = batch_queue_service.submit(
        rows=rows,
        run_prediction=_run_prediction_flow_as_dict,
        return_proba=payload.return_proba,
        explain=payload.explain,
    )
    return ApiEnvelope[AsyncBatchAccepted](
        success=True,
        data=AsyncBatchAccepted(
            job_id=str(job["job_id"]),
            total_rows=int(job["total_rows"]),
            status=str(job["status"]),
            submitted_at=str(job["submitted_at"]),
        ),
        error=None,
    )


@router.post("/predict/batch/upload", response_model=ApiEnvelope[AsyncBatchAccepted])
async def predict_batch_upload(
    file: UploadFile = File(...),
    return_proba: bool = Query(default=True),
    explain: bool = Query(default=False),
    sector: str = Query(default="telecom"),
) -> ApiEnvelope[AsyncBatchAccepted]:
    if not str(file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV upload is supported")

    content = await file.read()
    rows = _rows_from_csv_payload(content)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV contains no rows for prediction")

    run_fn = lambda feats, rp, exp: _run_prediction_flow_as_dict(feats, rp, exp, sector=sector)
    job = batch_queue_service.submit(
        rows=rows,
        run_prediction=run_fn,
        return_proba=return_proba,
        explain=explain,
    )
    return ApiEnvelope[AsyncBatchAccepted](
        success=True,
        data=AsyncBatchAccepted(
            job_id=str(job["job_id"]),
            total_rows=int(job["total_rows"]),
            status=str(job["status"]),
            submitted_at=str(job["submitted_at"]),
        ),
        error=None,
    )


@router.get("/predict/batch/jobs/{job_id}", response_model=ApiEnvelope[AsyncBatchJobStatus])
def predict_batch_job_status(job_id: str) -> ApiEnvelope[AsyncBatchJobStatus]:
    job = batch_queue_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Batch job '{job_id}' not found")

    return ApiEnvelope[AsyncBatchJobStatus](
        success=True,
        data=AsyncBatchJobStatus(**job),
        error=None,
    )


@router.get("/explainability/feature-importance", response_model=ApiEnvelope[ExplainabilitySummary])
def feature_importance(
    top_n: int = Query(default=10, ge=1, le=25),
) -> ApiEnvelope[ExplainabilitySummary]:
    summary = prediction_service.feature_importance(top_n=top_n)
    return ApiEnvelope[ExplainabilitySummary](success=True, data=summary, error=None)


@router.get("/customers", response_model=ApiEnvelope[CustomersData])
def get_customers(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    sector: str = Query(default="telecom"),
) -> ApiEnvelope[CustomersData]:
    app_logger.info("incoming_request | route=/customers | method=GET | limit=%s | offset=%s | search=%s | risk_level=%s | sector=%s", limit, offset, search, risk_level, sector)
    try:
        total, customers = customer_service.get_customers(limit=limit, offset=offset, search=search)
    except TypeError:
        total, customers = customer_service.get_customers(limit=limit, offset=offset)

    customer_ids = [str((row or {}).get("customer_id") or "").strip() for row in customers]
    risk_index: dict[str, dict[str, Any]] = {}
    if hasattr(prediction_service, "population_risk_index"):
        try:
            risk_index = prediction_service.population_risk_index(customer_ids)
        except Exception:
            app_logger.exception("population_risk_index_failed | fallback=default_low")

    enriched_customers = []
    for customer in customers:
        customer_id = str((customer or {}).get("customer_id") or "").strip()
        risk_payload = risk_index.get(customer_id) or {}
        norm_risk = _normalize_risk_bucket(str(risk_payload.get("risk_level") or customer.get("risk_level") or "Low"))
        
        # Check risk_level filter if requested
        if risk_level and risk_level.lower() != "all" and norm_risk.lower() != risk_level.strip().lower():
            continue

        enriched_customers.append(
            {
                **customer,
                "risk": norm_risk.lower(),
                "risk_level": norm_risk,
                "prediction_probability": float(risk_payload.get("probability") or 0.0),
                "primary_driver": risk_payload.get("primary_driver") or "Tenure & Engagement Balance",
                "recommended_action": risk_payload.get("recommended_action") or "Proactively review account health.",
            }
        )

    app_logger.info("outgoing_response | route=/customers | method=GET | status=200 | returned=%s | total=%s", len(enriched_customers), total)
    return ApiEnvelope[CustomersData](
        success=True,
        data=CustomersData(
            total=len(enriched_customers) if risk_level and risk_level.lower() != "all" else total,
            limit=limit,
            offset=offset,
            customers=enriched_customers,
        ),
        error=None,
    )


@router.get("/history", response_model=ApiEnvelope[HistoryData])
def history(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> ApiEnvelope[HistoryData]:
    app_logger.info("incoming_request | route=/history | method=GET | limit=%s | offset=%s", limit, offset)
    try:
        total, rows = fetch_history(limit=limit, offset=offset)
    except Exception:
        total, rows = 0, []
    normalized_rows = [
        {**row, "risk": _normalize_risk_bucket(str(row.get("risk_level", "")))}
        for row in rows
    ]
    app_logger.info("outgoing_response | route=/history | method=GET | status=200 | returned=%s | total=%s", len(normalized_rows), total)
    return ApiEnvelope[HistoryData](
        success=True,
        data=HistoryData(total=total, limit=limit, offset=offset, history=normalized_rows),
        error=None,
    )


@router.get("/system-health")
def system_health() -> dict[str, Any]:
    return {
        "api_status": "ONLINE",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
    }


@router.get("/model-health")
def model_health() -> dict[str, Any]:
    return {
        "success": True,
        "data": {
            "model_loaded": prediction_service.model_loaded,
            "model_version": getattr(prediction_service, "model_version", "v1.0"),
            "drift_score": 0.012,
            "status": "active",
        },
        "error": None,
    }


@router.get("/health", response_model=ApiEnvelope[HealthResponse])
def health() -> ApiEnvelope[HealthResponse]:
    app_logger.info("incoming_request | route=/health | method=GET")
    db_connected = is_database_connected()
    model_loaded = prediction_service.model_loaded
    status = "running" if db_connected and model_loaded else "degraded"

    app_logger.info("outgoing_response | route=/health | method=GET | status=200 | service_status=%s", status)
    return ApiEnvelope[HealthResponse](
        success=True,
        data=HealthResponse(
            status=status,
            model_loaded=model_loaded,
            database_connected=db_connected,
            uptime_seconds=metrics_service.uptime_seconds(),
            checks={
                "db_connection": db_connected,
                "model_loaded": model_loaded,
            },
        ),
        error=None,
    )


@router.get("/metrics/app", response_model=ApiEnvelope[MetricsResponse])
def metrics() -> ApiEnvelope[MetricsResponse]:
    app_logger.info("incoming_request | route=/metrics/app | method=GET")
    db_connected = is_database_connected()
    model_loaded = prediction_service.model_loaded
    dependencies_ok = db_connected and model_loaded

    request_summary = observability_service.request_summary()
    slo_state = observability_service.slo_status(dependencies_ok=dependencies_ok)

    app_logger.info("outgoing_response | route=/metrics/app | method=GET | status=200")
    return ApiEnvelope[MetricsResponse](
        success=True,
        data=MetricsResponse(
            service="fastapi-backend",
            model_loaded=model_loaded,
            model_path=prediction_service.model_path,
            inference_count=prediction_service.inference_count,
            uptime_seconds=metrics_service.uptime_seconds(),
            last_prediction_at=prediction_service.last_prediction_at or "",
            request_summary=request_summary,
            slo=SLOStatus(**slo_state),
        ),
        error=None,
    )


@router.get("/metrics/slo", response_model=ApiEnvelope[SLOStatus])
def metrics_slo() -> ApiEnvelope[SLOStatus]:
    app_logger.info("incoming_request | route=/metrics/slo | method=GET")
    db_connected = is_database_connected()
    model_loaded = prediction_service.model_loaded
    dependencies_ok = db_connected and model_loaded
    slo_state = observability_service.slo_status(dependencies_ok=dependencies_ok)

    app_logger.info("outgoing_response | route=/metrics/slo | method=GET | status=200")
    return ApiEnvelope[SLOStatus](
        success=True,
        data=SLOStatus(**slo_state),
        error=None,
    )


@router.get("/metrics/dashboard", response_model=ApiEnvelope[MetricsDashboardResponse])
def metrics_dashboard(
    hours: int = Query(default=24, ge=1, le=168),
) -> ApiEnvelope[MetricsDashboardResponse]:
    app_logger.info("incoming_request | route=/metrics/dashboard | method=GET | hours=%s", hours)
    population = _population_metrics()
    total_customers = int(population["total_customers"])
    total_predictions = int(population["total_predictions"])
    risk_distribution = dict(population["risk_distribution"])
    churn_vs_non_churn = dict(population["churn_vs_non_churn"])
    high_risk_count = int(population["high_risk_count"])
    high_risk_percentage = float(population["high_risk_percentage"])
    try:
        predictions_today = fetch_predictions_today_count()
    except Exception:
        predictions_today = 0

    try:
        predictions_per_hour = _normalize_trend(fetch_predictions_per_hour(hours=hours))
    except Exception:
        predictions_per_hour = []
    churn_distribution = [
        {"risk_level": "Low", "count": risk_distribution["low"]},
        {"risk_level": "Medium", "count": risk_distribution["medium"]},
        {"risk_level": "High", "count": risk_distribution["high"]},
    ]
    # Build prioritized high-risk customer records for immediate dashboard action
    high_risk_list: list[dict[str, Any]] = []
    if hasattr(prediction_service, "population_risk_index"):
        try:
            full_risk = prediction_service.population_risk_index()
            for cid, info in full_risk.items():
                if info.get("risk") == "high" or info.get("risk_level") == "High":
                    high_risk_list.append({
                        "customer_id": cid,
                        "probability": info.get("probability", 0.0),
                        "risk_level": "High",
                        "primary_driver": info.get("primary_driver", "Elevated Cost / Early Tenure"),
                        "recommended_action": info.get("recommended_action", "Offer retention discount & schedule CSM follow-up"),
                    })
            high_risk_list.sort(key=lambda x: x["probability"], reverse=True)
            high_risk_list = high_risk_list[:10]  # Top 10 immediate attention customers
        except Exception:
            app_logger.exception("failed_to_extract_dashboard_high_risk_customers")

    response = ApiEnvelope[MetricsDashboardResponse](
        success=True,
        data=MetricsDashboardResponse(
            window_hours=hours,
            total_customers=total_customers,
            total_predictions=total_predictions,
            churn_rate=float((churn_vs_non_churn.get("churn", 0) / total_customers) if total_customers else 0.0),
            high_risk_count=high_risk_count,
            high_risk_percentage=high_risk_percentage,
            predictions_today=predictions_today,
            risk_distribution=risk_distribution,
            churn_vs_nonchurn=churn_vs_non_churn,
            trend=predictions_per_hour,
            predictions_per_hour=predictions_per_hour,
            prediction_trend=predictions_per_hour,
            churn_distribution=churn_distribution,
            high_risk_customers=high_risk_list,
        ),
        error=None,
    )
    app_logger.info(
        "outgoing_response | route=/metrics/dashboard | method=GET | status=200 | hours=%s | total_customers=%s | total_predictions=%s | churn_rate=%.4f",
        hours,
        total_customers,
        total_predictions,
        float((churn_vs_non_churn.get("churn", 0) / total_customers) if total_customers else 0.0),
    )
    return response


@router.get("/dashboard", response_model=ApiEnvelope[MetricsDashboardResponse])
def dashboard_alias(
    hours: int = Query(default=24, ge=1, le=168),
) -> ApiEnvelope[MetricsDashboardResponse]:
    return metrics_dashboard(hours=hours)


@router.get("/analytics", response_model=ApiEnvelope[AnalyticsResponse])
def analytics_alias(
    hours: int = Query(default=24, ge=1, le=168),
) -> ApiEnvelope[AnalyticsResponse]:
    population = _population_metrics()
    total_customers = int(population["total_customers"])
    risk_distribution = dict(population["risk_distribution"])
    churn_vs_non_churn = dict(population["churn_vs_non_churn"])
    trend = _normalize_trend(fetch_predictions_per_hour(hours=hours))
    top_features = fetch_aggregated_top_feature_impacts(top_n=10, hours=hours)
    return ApiEnvelope[AnalyticsResponse](
        success=True,
        data=AnalyticsResponse(
            window_hours=hours,
            total_customers=total_customers,
            total_predictions=int(population["total_predictions"]),
            risk_distribution=risk_distribution,
            churn_vs_nonchurn=churn_vs_non_churn,
            trend=trend,
            predictions_per_hour=trend,
            top_features=top_features,
        ),
        error=None,
    )


@router.get("/system-health", response_model=SystemHealthResponse)
def system_health() -> SystemHealthResponse:
    model_loaded = prediction_service.model_loaded
    db_connected = is_database_connected()
    api_status = "OK" if model_loaded and db_connected else "DEGRADED"
    return SystemHealthResponse(
        model_loaded=model_loaded,
        db_connected=db_connected,
        api_status=api_status,
    )


@router.get("/model-health", response_model=ApiEnvelope[ModelHealthResponse])
def model_health() -> ApiEnvelope[ModelHealthResponse]:
    summary = ml_monitoring_service.run_monitoring()
    drift_score = float(summary.get("drift_score") or 0.0)
    status = "DRIFT DETECTED" if summary.get("status") == "alert" else "OK"
    return ApiEnvelope[ModelHealthResponse](
        success=True,
        data=ModelHealthResponse(
            status=status,
            drift_score=drift_score,
            drift_detected=bool(summary.get("drift_detected")),
            alerts_count=int(summary.get("alerts_count") or 0),
            current_predictions=dict(summary.get("current_predictions") or {}),
            baseline_predictions=dict(summary.get("baseline_predictions") or {}),
            current_features=dict(summary.get("current_features") or {}),
            baseline_features=dict(summary.get("baseline_features") or {}),
            alerts=list(summary.get("alerts") or []),
        ),
        error=None,
    )


@router.post("/retrain", response_model=ApiEnvelope[RetrainResponse])
def retrain_model(
    model_type: str = Query(default="xgboost", pattern="^(xgboost|logreg)$"),
    feature_version: str = Query(default="v1"),
    horizon_days: int = Query(default=30, ge=1, le=365),
    top_k_pct: float = Query(default=0.1, gt=0.0, le=1.0),
    force: bool = Query(default=True),
) -> ApiEnvelope[RetrainResponse]:
    result = retraining_service.retrain(
        force=force,
        model_type=model_type,
        feature_version=feature_version,
        horizon_days=horizon_days,
        top_k_pct=top_k_pct,
    )
    return ApiEnvelope[RetrainResponse](success=True, data=RetrainResponse(**result), error=None)


@router.get("/powerbi/embed-config", response_model=ApiEnvelope[dict[str, Any]])
def powerbi_embed_config(
    refresh: bool = Query(default=False),
) -> ApiEnvelope[dict[str, Any]]:
    app_logger.info("incoming_request | route=/powerbi/embed-config | method=GET | refresh=%s", refresh)
    try:
        config = powerbi_service.embed_config(force_refresh=refresh)
    except Exception as exc:
        app_logger.error("route_error | route=/powerbi/embed-config | status=503 | message=%s", str(exc))
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    app_logger.info("outgoing_response | route=/powerbi/embed-config | method=GET | status=200")
    return ApiEnvelope[dict[str, Any]](success=True, data=config, error=None)
