from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import text

from app.db import get_engine
from app.services.training_service import FEATURE_COLUMNS

WARNING_THRESHOLD = 0.2
RETRAIN_THRESHOLD = 0.3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute PSI drift and persist drift_metrics rows")
    parser.add_argument("--compare-days", type=int, default=14)
    return parser.parse_args()


def compute_psi(baseline: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    baseline = baseline.astype(float)
    current = current.astype(float)

    if baseline.size == 0 or current.size == 0:
        return 0.0

    quantiles = np.linspace(0, 1, bins + 1)
    cut_points = np.unique(np.quantile(baseline, quantiles))
    if cut_points.size < 3:
        return 0.0

    baseline_binned = pd.cut(baseline, bins=cut_points, include_lowest=True)
    current_binned = pd.cut(current, bins=cut_points, include_lowest=True)

    baseline_dist = baseline_binned.value_counts(normalize=True, sort=False).replace(0, 1e-6)
    current_dist = current_binned.value_counts(normalize=True, sort=False).replace(0, 1e-6)

    aligned = baseline_dist.index.union(current_dist.index)
    b = baseline_dist.reindex(aligned, fill_value=1e-6)
    c = current_dist.reindex(aligned, fill_value=1e-6)

    psi = np.sum((c - b) * np.log(c / b))
    return float(psi)


def load_active_model(engine):
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT model_version, feature_version, training_data_start, training_data_end
                FROM model_registry
                WHERE status = 'production'
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """
            )
        ).mappings().first()

    if row is None:
        raise RuntimeError("No production model found in model_registry")
    return row


def load_features(engine, feature_version: str, start_date: str, end_date: str) -> pd.DataFrame:
    sql = text(
        f"""
        SELECT {', '.join(FEATURE_COLUMNS)}
        FROM features_daily
        WHERE feature_version = :feature_version
          AND feature_date BETWEEN :start_date AND :end_date
        """
    )

    return pd.read_sql(
        sql,
        con=engine,
        params={
            "feature_version": feature_version,
            "start_date": start_date,
            "end_date": end_date,
        },
    )


def persist_drift_metrics(engine, records: list[dict]) -> None:
    if not records:
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO drift_metrics (
                  computed_at, feature_name, feature_version, model_version, psi_value,
                  threshold_warning, threshold_retrain, status,
                  baseline_start, baseline_end, compare_start, compare_end, metadata_json
                ) VALUES (
                  :computed_at, :feature_name, :feature_version, :model_version, :psi_value,
                  :threshold_warning, :threshold_retrain, :status,
                  :baseline_start, :baseline_end, :compare_start, :compare_end, :metadata_json
                )
                """
            ),
            records,
        )


def main() -> None:
    args = parse_args()
    engine = get_engine()

    model = load_active_model(engine)
    baseline_start = pd.to_datetime(model["training_data_start"]).date()
    baseline_end = pd.to_datetime(model["training_data_end"]).date()

    compare_end = datetime.utcnow().date()
    compare_start = compare_end - timedelta(days=max(1, args.compare_days))

    baseline_df = load_features(engine, model["feature_version"], str(baseline_start), str(baseline_end))
    compare_df = load_features(engine, model["feature_version"], str(compare_start), str(compare_end))

    if baseline_df.empty or compare_df.empty:
        raise RuntimeError("Insufficient feature rows for PSI drift detection")

    computed_at = datetime.utcnow()
    records: list[dict] = []
    max_psi = 0.0

    for feature in FEATURE_COLUMNS:
        psi = compute_psi(baseline_df[feature].to_numpy(), compare_df[feature].to_numpy())
        max_psi = max(max_psi, psi)

        if psi > RETRAIN_THRESHOLD:
            status = "retrain"
        elif psi > WARNING_THRESHOLD:
            status = "warning"
        else:
            status = "ok"

        records.append(
            {
                "computed_at": computed_at,
                "feature_name": feature,
                "feature_version": model["feature_version"],
                "model_version": model["model_version"],
                "psi_value": psi,
                "threshold_warning": WARNING_THRESHOLD,
                "threshold_retrain": RETRAIN_THRESHOLD,
                "status": status,
                "baseline_start": baseline_start,
                "baseline_end": baseline_end,
                "compare_start": compare_start,
                "compare_end": compare_end,
                "metadata_json": json.dumps({"compare_days": args.compare_days}),
            }
        )

    persist_drift_metrics(engine, records)

    overall_status = "retrain" if max_psi > RETRAIN_THRESHOLD else "warning" if max_psi > WARNING_THRESHOLD else "ok"

    print(
        json.dumps(
            {
                "status": overall_status,
                "max_psi": round(max_psi, 6),
                "model_version": model["model_version"],
                "feature_version": model["feature_version"],
                "thresholds": {
                    "warning": WARNING_THRESHOLD,
                    "retrain": RETRAIN_THRESHOLD,
                },
            }
        )
    )


if __name__ == "__main__":
    main()
