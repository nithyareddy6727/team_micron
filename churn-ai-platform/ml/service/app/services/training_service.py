from __future__ import annotations

import os
import uuid
from datetime import datetime

import mlflow
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sqlalchemy import text

from app.config import settings
from app.db import get_engine
from app.services.metrics import evaluate_binary_scores

try:
    from xgboost import XGBClassifier
except Exception:  # pragma: no cover
    XGBClassifier = None


FEATURE_COLUMNS = [
    "recency_days",
    "sessions_7d",
    "sessions_30d",
    "usage_drop_30d_pct",
    "tickets_30d",
    "payment_failures_30d",
    "tenure_days",
]

_training_runs: dict[str, dict[str, str | None]] = {}


def get_training_run(run_id: str) -> dict[str, str | None] | None:
    return _training_runs.get(run_id)


def _choose_model(model_type: str):
    if model_type == "xgboost" and XGBClassifier is not None:
        return XGBClassifier(
            n_estimators=250,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="binary:logistic",
            eval_metric="aucpr",
            random_state=42,
        )

    return LogisticRegression(max_iter=400, class_weight="balanced")


def _load_training_frame(feature_version: str, horizon_days: int) -> pd.DataFrame:
    # Point-in-time join: features at t are matched with outcomes observed at t + horizon.
    engine = get_engine()
    sql = text(
        """
        SELECT
          fd.feature_date,
          fd.customer_id,
          fd.recency_days,
          fd.sessions_7d,
          fd.sessions_30d,
          fd.usage_drop_30d_pct,
          fd.tickets_30d,
          fd.payment_failures_30d,
          fd.tenure_days,
          o.churned_flag AS label
        FROM features_daily fd
        JOIN outcomes o
          ON o.customer_id = fd.customer_id
         AND o.evaluation_date = DATE_ADD(fd.feature_date, INTERVAL :horizon DAY)
        WHERE fd.feature_version = :feature_version
          AND o.observation_window_days = :horizon
        ORDER BY fd.feature_date ASC
        """
    )
    frame = pd.read_sql(sql, con=engine, params={"feature_version": feature_version, "horizon": horizon_days})
    if frame.empty:
        raise ValueError("No training rows found. Ensure outcomes are loaded with matching observation_window_days.")

    frame["feature_date"] = pd.to_datetime(frame["feature_date"]).dt.normalize()
    frame["label"] = frame["label"].astype(int)
    frame[FEATURE_COLUMNS] = frame[FEATURE_COLUMNS].fillna(0)
    return frame


def run_training_job(
    run_id: str,
    model_type: str,
    feature_version: str,
    horizon_days: int,
    top_k_pct: float,
    set_as_production: bool,
) -> None:
    _training_runs[run_id] = {"status": "running", "message": None, "model_version": None}

    try:
        tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(os.getenv("MLFLOW_EXPERIMENT_NAME", "churn_prediction"))

        frame = _load_training_frame(feature_version, horizon_days)
        split_idx = max(1, int(len(frame) * 0.8))

        train_df = frame.iloc[:split_idx]
        valid_df = frame.iloc[split_idx:]
        if valid_df.empty:
            raise ValueError("Validation fold is empty; add more dated rows.")

        X_train = train_df[FEATURE_COLUMNS]
        y_train = train_df["label"].to_numpy(dtype=int)
        X_valid = valid_df[FEATURE_COLUMNS]
        y_valid = valid_df["label"].to_numpy(dtype=int)

        model = _choose_model(model_type)
        with mlflow.start_run(run_name=run_id):
            mlflow.log_param("run_id", run_id)
            mlflow.log_param("model_type", model_type)
            mlflow.log_param("feature_version", feature_version)
            mlflow.log_param("horizon_days", horizon_days)
            mlflow.log_param("top_k_pct", top_k_pct)

            model.fit(X_train, y_train)
            valid_scores = model.predict_proba(X_valid)[:, 1]

            metrics = evaluate_binary_scores(y_valid, valid_scores, top_k_pct)
            for key, value in metrics.items():
                if isinstance(value, (int, float, np.floating, np.integer)):
                    mlflow.log_metric(key, float(value))
            model_version = f"{model_type}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            mlflow.sklearn.log_model(model, artifact_path="model")
            mlflow.log_dict({"feature_columns": FEATURE_COLUMNS, "feature_version": feature_version}, "training_metadata.json")

        os.makedirs(settings.model_artifact_dir, exist_ok=True)
        artifact_name = f"{model_version}.joblib"
        artifact_path = os.path.join(settings.model_artifact_dir, artifact_name)
        joblib.dump(
            {
                "model": model,
                "feature_columns": FEATURE_COLUMNS,
                "metrics": metrics,
                "trained_at": datetime.utcnow().isoformat(),
                "feature_version": feature_version,
                "model_type": model_type,
            },
            artifact_path,
        )

        threshold_high = float(np.quantile(valid_scores, 0.8))
        threshold_medium = float(np.quantile(valid_scores, 0.5))

        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO model_registry (
                      model_version, model_type, training_data_start, training_data_end,
                      validation_metric, validation_score, threshold_high, threshold_medium,
                      feature_version, artifact_uri, status
                    ) VALUES (
                      :model_version, :model_type, :training_data_start, :training_data_end,
                      :validation_metric, :validation_score, :threshold_high, :threshold_medium,
                      :feature_version, :artifact_uri, :status
                    )
                    ON DUPLICATE KEY UPDATE
                      validation_metric = VALUES(validation_metric),
                      validation_score = VALUES(validation_score),
                      threshold_high = VALUES(threshold_high),
                      threshold_medium = VALUES(threshold_medium),
                      artifact_uri = VALUES(artifact_uri),
                      status = VALUES(status),
                      updated_at = CURRENT_TIMESTAMP
                    """
                ),
                {
                    "model_version": model_version,
                    "model_type": model_type,
                    "training_data_start": train_df["feature_date"].min().date(),
                    "training_data_end": valid_df["feature_date"].max().date(),
                    "validation_metric": "pr_auc",
                    "validation_score": metrics["pr_auc"],
                    "threshold_high": threshold_high,
                    "threshold_medium": threshold_medium,
                    "feature_version": feature_version,
                    "artifact_uri": artifact_name,
                    "status": "production" if set_as_production else "staging",
                },
            )

            if set_as_production:
                conn.execute(
                    text(
                        """
                        UPDATE model_registry
                        SET status = 'archived', updated_at = CURRENT_TIMESTAMP
                        WHERE status = 'production' AND model_version <> :model_version
                        """
                    ),
                    {"model_version": model_version},
                )
                conn.execute(
                    text(
                        """
                        UPDATE model_registry
                        SET status = 'production', updated_at = CURRENT_TIMESTAMP
                        WHERE model_version = :model_version
                        """
                    ),
                    {"model_version": model_version},
                )

        _training_runs[run_id] = {
            "status": "completed",
            "message": (
                f"Training completed. ROC-AUC={metrics['roc_auc']:.4f}, "
                f"PR-AUC={metrics['pr_auc']:.4f}, Recall@TopK={metrics['recall_top_k']:.4f}"
            ),
            "model_version": model_version,
        }

    except Exception as exc:
        _training_runs[run_id] = {
            "status": "failed",
            "message": str(exc),
            "model_version": None,
        }


def create_run_id() -> str:
    return str(uuid.uuid4())
