from __future__ import annotations

from pathlib import Path
from typing import Any

import mlflow


def initialize_mlflow(mlruns_dir: Path, experiment_name: str = "churn-prediction") -> None:
    mlruns_dir.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(f"file:{mlruns_dir.resolve()}")
    mlflow.set_experiment(experiment_name)


def track_prediction(
    model_version: str,
    customer_id: str,
    prediction: int,
    probability: float,
    latency_ms: float,
    risk_level: str,
    confidence_score: float,
    features: dict[str, Any],
) -> None:
    try:
        with mlflow.start_run(run_name=f"predict-{customer_id}", nested=True):
            mlflow.log_param("model_version", model_version)
            mlflow.log_param("customer_id", customer_id)
            mlflow.log_param("risk_level", risk_level)

            mlflow.log_metric("prediction", float(prediction))
            mlflow.log_metric("probability", float(probability))
            mlflow.log_metric("latency_ms", float(latency_ms))
            mlflow.log_metric("confidence_score", float(confidence_score))

            mlflow.log_dict(features, "features.json")
            mlflow.log_dict(
                {
                    "model_version": model_version,
                    "customer_id": customer_id,
                    "prediction": int(prediction),
                    "probability": float(probability),
                    "latency_ms": float(latency_ms),
                    "risk_level": risk_level,
                    "confidence_score": float(confidence_score),
                },
                "prediction_summary.json",
            )
    except Exception:
        pass
