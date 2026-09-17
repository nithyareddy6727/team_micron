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
    parser = argparse.ArgumentParser(description="Compute feature PSI and persist drift metrics")
    parser.add_argument("--compare-days", type=int, default=14)
    return parser.parse_args()


def psi_for_feature(baseline: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    baseline = baseline.astype(float)
    current = current.astype(float)

    if baseline.size == 0 or current.size == 0:
        return 0.0

    quantiles = np.linspace(0, 1, bins + 1)
    cut_points = np.unique(np.quantile(baseline, quantiles))
    if cut_points.size < 3:
        return 0.0

    baseline_bins = pd.cut(baseline, bins=cut_points, include_lowest=True)
    current_bins = pd.cut(current, bins=cut_points, include_lowest=True)

    base_dist = baseline_bins.value_counts(normalize=True, sort=False).replace(0, 1e-6)
    curr_dist = current_bins.value_counts(normalize=True, sort=False).replace(0, 1e-6)

    aligned = base_dist.index.union(curr_dist.index)
    base = base_dist.reindex(aligned, fill_value=1e-6)
    curr = curr_dist.reindex(aligned, fill_value=1e-6)

    psi = np.sum((curr - base) * np.log(curr / base))
    return float(psi)


def load_active_model_metadata(engine):
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
        raise RuntimeError("No production model in model_registry")
    return row


def load_feature_window(engine, feature_version: str, start_date: str, end_date: str) -> pd.DataFrame:
    sql = text(
        f"""
        SELECT {', '.join(FEATURE_COLUMNS)}
        FROM features_daily
        WHERE feature_version = :feature_version
          AND feature_date BETWEEN :start_date AND :end_date
        """
    )
    return pd.read_sql(sql, con=engine, params={"feature_version": feature_version, "start_date": start_date, "end_date": end_date})


def persist_drift(engine, records: list[dict]) -> None:
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

    model = load_active_model_metadata(engine)
    baseline_start = pd.to_datetime(model["training_data_start"]).date()
    baseline_end = pd.to_datetime(model["training_data_end"]).date()

    compare_end = datetime.utcnow().date()
    compare_start = compare_end - timedelta(days=max(1, args.compare_days))

    baseline_df = load_feature_window(engine, model["feature_version"], str(baseline_start), str(baseline_end))
    current_df = load_feature_window(engine, model["feature_version"], str(compare_start), str(compare_end))

    if baseline_df.empty or current_df.empty:
        raise RuntimeError("Insufficient feature rows for drift calculation")

    computed_at = datetime.utcnow()
    records = []
    max_psi = 0.0

    for feature in FEATURE_COLUMNS:
      psi_value = psi_for_feature(baseline_df[feature].to_numpy(), current_df[feature].to_numpy())
      max_psi = max(max_psi, psi_value)

      if psi_value > RETRAIN_THRESHOLD:
          status = "retrain"
      elif psi_value > WARNING_THRESHOLD:
          status = "warning"
      else:
          status = "ok"

      records.append(
          {
              "computed_at": computed_at,
              "feature_name": feature,
              "feature_version": model["feature_version"],
              "model_version": model["model_version"],
              "psi_value": psi_value,
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

    persist_drift(engine, records)

    trigger = "retrain" if max_psi > RETRAIN_THRESHOLD else "warning" if max_psi > WARNING_THRESHOLD else "ok"
    print(
        json.dumps(
            {
                "model_version": model["model_version"],
                "feature_version": model["feature_version"],
                "max_psi": round(max_psi, 6),
                "status": trigger,
                "compare_window": {"start": str(compare_start), "end": str(compare_end)},
            }
        )
    )


if __name__ == "__main__":
    main()
