from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from models.db import (
    fetch_feature_distribution,
    fetch_prediction_distribution,
    insert_monitoring_alert,
)


class MLMonitoringService:
    def __init__(self) -> None:
        self._logger = logging.getLogger("churn_app")
        self._config_path = Path(
            os.getenv(
                "TRAINING_DISTRIBUTION_PATH",
                str(Path(__file__).resolve().parents[1] / "config" / "training_distribution.json"),
            )
        )

    def _safe_ratio_diff(self, current: float, baseline: float) -> float:
        denom = max(abs(baseline), 1e-6)
        return abs(current - baseline) / denom

    def _load_training_distribution(self) -> dict[str, Any] | None:
        if not self._config_path.exists():
            self._logger.warning("training_distribution_missing | path=%s", self._config_path)
            return None

        try:
            payload = json.loads(self._config_path.read_text(encoding="utf-8"))
            self._logger.info("training_distribution_loaded | path=%s", self._config_path)
            return payload
        except Exception:
            self._logger.error("training_distribution_load_failed", exc_info=True)
            return None

    def _detect_prediction_anomaly(self, current: dict[str, Any]) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []

        min_mean = float(os.getenv("PREDICTION_MEAN_MIN", "0.05"))
        max_mean = float(os.getenv("PREDICTION_MEAN_MAX", "0.95"))
        max_variance = float(os.getenv("PREDICTION_VARIANCE_MAX", "0.30"))

        if current["probability_mean"] < min_mean or current["probability_mean"] > max_mean:
            alerts.append(
                {
                    "type": "prediction_anomaly_mean",
                    "severity": "warning",
                    "message": (
                        f"Prediction mean out of band: {current['probability_mean']:.4f} "
                        f"(expected range {min_mean:.2f}-{max_mean:.2f})"
                    ),
                }
            )

        if current["probability_variance"] > max_variance:
            alerts.append(
                {
                    "type": "prediction_anomaly_variance",
                    "severity": "warning",
                    "message": (
                        f"Prediction variance high: {current['probability_variance']:.4f} "
                        f"(max allowed {max_variance:.2f})"
                    ),
                }
            )

        return alerts

    def _detect_drift(
        self,
        current_predictions: dict[str, Any],
        current_features: dict[str, Any],
        baseline_predictions: dict[str, Any],
        baseline_features: dict[str, Any],
    ) -> tuple[bool, list[dict[str, Any]]]:
        drift_alerts: list[dict[str, Any]] = []
        drift_threshold = float(os.getenv("DRIFT_REL_DIFF_THRESHOLD", "0.20"))

        checks = [
            ("prediction.probability_mean", current_predictions["probability_mean"], baseline_predictions["probability_mean"]),
            ("prediction.probability_variance", current_predictions["probability_variance"], baseline_predictions["probability_variance"]),
            ("feature.age_mean", current_features["age_mean"], baseline_features["age_mean"]),
            ("feature.tenure_mean", current_features["tenure_mean"], baseline_features["tenure_mean"]),
            (
                "feature.monthly_charges_mean",
                current_features["monthly_charges_mean"],
                baseline_features["monthly_charges_mean"],
            ),
        ]

        for metric, current_value, baseline_value in checks:
            rel_diff = self._safe_ratio_diff(float(current_value), float(baseline_value))
            if rel_diff >= drift_threshold:
                drift_alerts.append(
                    {
                        "type": "data_drift_detected",
                        "severity": "error",
                        "message": (
                            f"Drift detected for {metric}: current={float(current_value):.4f}, "
                            f"baseline={float(baseline_value):.4f}, rel_diff={rel_diff:.4f}"
                        ),
                        "metric": metric,
                        "current": float(current_value),
                        "baseline": float(baseline_value),
                        "relative_diff": rel_diff,
                    }
                )

        return len(drift_alerts) > 0, drift_alerts

    def run_monitoring(self) -> dict[str, Any]:
        current_hours = int(os.getenv("MONITORING_CURRENT_WINDOW_HOURS", "24"))
        baseline_hours = int(os.getenv("MONITORING_BASELINE_WINDOW_HOURS", "168"))
        min_samples = int(os.getenv("MONITORING_MIN_SAMPLE_COUNT", "50"))

        current_predictions = fetch_prediction_distribution(hours=current_hours, offset_hours=0)
        current_features = fetch_feature_distribution(hours=current_hours, offset_hours=0)

        if current_predictions["sample_count"] < min_samples:
            message = (
                f"Insufficient samples for monitoring: {current_predictions['sample_count']} "
                f"< {min_samples}"
            )
            self._logger.warning("ml_monitoring_skipped | reason=insufficient_samples | %s", message)
            return {
                "status": "skipped",
                "reason": message,
                "current_predictions": current_predictions,
                "current_features": current_features,
                "alerts": [],
            }

        training_distribution = self._load_training_distribution()

        if training_distribution is not None:
            baseline_predictions = dict(training_distribution.get("prediction_distribution", {}))
            baseline_features = dict(training_distribution.get("feature_distribution", {}))
        else:
            baseline_predictions = fetch_prediction_distribution(hours=baseline_hours, offset_hours=current_hours)
            baseline_features = fetch_feature_distribution(hours=baseline_hours, offset_hours=current_hours)

        anomaly_alerts = self._detect_prediction_anomaly(current_predictions)
        drift_detected, drift_alerts = self._detect_drift(
            current_predictions=current_predictions,
            current_features=current_features,
            baseline_predictions=baseline_predictions,
            baseline_features=baseline_features,
        )

        all_alerts = anomaly_alerts + drift_alerts
        drift_score = 0.0
        for alert in drift_alerts:
            drift_score = max(drift_score, float(alert.get("relative_diff") or 0.0))

        for alert in all_alerts:
            alert_id = insert_monitoring_alert(
                alert_type=alert["type"],
                severity=alert["severity"],
                message=alert["message"],
                context={
                    "current_window_hours": current_hours,
                    "baseline_window_hours": baseline_hours,
                    "current_predictions": current_predictions,
                    "baseline_predictions": baseline_predictions,
                    "current_features": current_features,
                    "baseline_features": baseline_features,
                    "details": alert,
                },
            )
            self._logger.error("ml_monitoring_alert | id=%s | type=%s | message=%s", alert_id, alert["type"], alert["message"])

        summary = {
            "status": "ok" if not all_alerts else "alert",
            "drift_detected": drift_detected,
            "drift_score": drift_score,
            "alerts_count": len(all_alerts),
            "current_predictions": current_predictions,
            "baseline_predictions": baseline_predictions,
            "current_features": current_features,
            "baseline_features": baseline_features,
            "alerts": all_alerts,
        }

        self._logger.info(
            "ml_monitoring_summary | status=%s | drift_detected=%s | alerts=%s",
            summary["status"],
            summary["drift_detected"],
            summary["alerts_count"],
        )
        return summary
