from __future__ import annotations

import json
from datetime import date

import pandas as pd
from fastapi import HTTPException
from sqlalchemy import text

from app.db import get_engine
from app.schemas import Driver, ScoreResponse
from app.services.model_store import band_for_score, load_active_model, score_row


FEATURE_COLUMNS = [
    "recency_days",
    "sessions_7d",
    "sessions_30d",
    "usage_drop_30d_pct",
    "tickets_30d",
    "payment_failures_30d",
    "tenure_days",
]


def _fetch_feature_row(customer_id: int, requested_feature_date: date | None, feature_version: str) -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                  customer_id,
                  feature_date,
                  recency_days,
                  sessions_7d,
                  sessions_30d,
                  usage_drop_30d_pct,
                  tickets_30d,
                  payment_failures_30d,
                  tenure_days
                FROM features_daily
                WHERE customer_id = :customer_id
                  AND feature_version = :feature_version
                  AND (:feature_date IS NULL OR feature_date <= :feature_date)
                ORDER BY feature_date DESC
                LIMIT 1
                """
            ),
            {
                "customer_id": customer_id,
                "feature_version": feature_version,
                "feature_date": requested_feature_date,
            },
        ).mappings().first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No features found for customer_id={customer_id} "
                f"and feature_version={feature_version}"
            ),
        )

    return dict(row)


def _store_prediction(
    customer_id: int,
    score: float,
    risk_band: str,
    model_version: str,
    feature_version: str,
    feature_date: date,
    horizon_days: int,
    top_drivers: list[dict[str, object]],
) -> int:
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                INSERT INTO predictions (
                  customer_id, prediction_ts, horizon_days, score, risk_band,
                  model_version, feature_version, feature_date, explainability_json
                ) VALUES (
                  :customer_id, NOW(), :horizon_days, :score, :risk_band,
                  :model_version, :feature_version, :feature_date, :explainability_json
                )
                """
            ),
            {
                "customer_id": customer_id,
                "horizon_days": horizon_days,
                "score": score,
                "risk_band": risk_band,
                "model_version": model_version,
                "feature_version": feature_version,
                "feature_date": feature_date,
                "explainability_json": json.dumps(top_drivers),
            },
        )
        prediction_id = int(result.lastrowid)
    return prediction_id


def score_customer(customer_id: int, feature_date: date | None, horizon_days: int) -> ScoreResponse:
    loaded = load_active_model()
    if loaded is None:
        raise HTTPException(status_code=503, detail="No active production model is available")

    feat_row = _fetch_feature_row(customer_id, feature_date, loaded.feature_version)
    row_df = pd.DataFrame([feat_row])
    row_df[FEATURE_COLUMNS] = row_df[FEATURE_COLUMNS].fillna(0)

    score, drivers = score_row(loaded, row_df)
    risk_band = band_for_score(score, loaded.threshold_medium, loaded.threshold_high)

    prediction_id = _store_prediction(
        customer_id=customer_id,
        score=score,
        risk_band=risk_band,
        model_version=loaded.model_version,
        feature_version=loaded.feature_version,
        feature_date=feat_row["feature_date"],
        horizon_days=horizon_days,
        top_drivers=drivers,
    )

    return ScoreResponse(
        prediction_id=prediction_id,
        customer_id=customer_id,
        score=round(score, 6),
        risk_band=risk_band,
        model_version=loaded.model_version,
        top_drivers=[Driver(**d) for d in drivers],
    )


def score_customer_with_features(customer_id: int, features: dict, horizon_days: int) -> ScoreResponse:
    loaded = load_active_model()
    if loaded is None:
        raise HTTPException(status_code=503, detail="No active production model is available")

    row_payload = {col: features.get(col, 0) for col in FEATURE_COLUMNS}
    row_df = pd.DataFrame([row_payload])
    row_df[FEATURE_COLUMNS] = row_df[FEATURE_COLUMNS].fillna(0)

    score, drivers = score_row(loaded, row_df)
    risk_band = band_for_score(score, loaded.threshold_medium, loaded.threshold_high)

    feature_date = features.get("feature_date") or date.today().isoformat()
    prediction_id = _store_prediction(
        customer_id=customer_id,
        score=score,
        risk_band=risk_band,
        model_version=loaded.model_version,
        feature_version=loaded.feature_version,
        feature_date=feature_date,
        horizon_days=horizon_days,
        top_drivers=drivers,
    )

    return ScoreResponse(
        prediction_id=prediction_id,
        customer_id=customer_id,
        score=round(score, 6),
        risk_band=risk_band,
        model_version=loaded.model_version,
        top_drivers=[Driver(**d) for d in drivers],
    )


def explain_prediction(prediction_id: int):
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT prediction_id, customer_id, score, risk_band, model_version,
                       feature_version, feature_date, prediction_ts, explainability_json
                FROM predictions
                WHERE prediction_id = :prediction_id
                """
            ),
            {"prediction_id": prediction_id},
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail=f"prediction_id={prediction_id} not found")

    drivers = []
    if row["explainability_json"]:
        parsed = json.loads(row["explainability_json"])
        drivers = [Driver(**d) for d in parsed]

    return {
        "prediction_id": int(row["prediction_id"]),
        "customer_id": int(row["customer_id"]),
        "score": float(row["score"]),
        "risk_band": row["risk_band"],
        "model_version": row["model_version"],
        "feature_version": row["feature_version"],
        "feature_date": row["feature_date"],
        "prediction_ts": row["prediction_ts"],
        "top_drivers": drivers,
    }
