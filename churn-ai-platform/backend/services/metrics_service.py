from __future__ import annotations

import time
import logging

from models.db import fetch_customers_without_recent_predictions


class MetricsService:
    def __init__(self) -> None:
        self._started_at = time.time()
        self._logger = logging.getLogger("churn_app")

    def uptime_seconds(self) -> float:
        return round(time.time() - self._started_at, 3)

    def backfill_predictions_for_dashboard(self, prediction_service, window_hours: int = 24) -> dict[str, int]:
        customer_ids = fetch_customers_without_recent_predictions(window_hours=window_hours)
        attempted = 0
        succeeded = 0
        failed = 0

        if not customer_ids:
            self._logger.info("dashboard_backfill | status=skipped | reason=no_customers_missing_recent_predictions")
            return {"attempted": 0, "succeeded": 0, "failed": 0}

        self._logger.info("dashboard_backfill | pending_customers=%s | window_hours=%s", len(customer_ids), window_hours)
        for customer_id in customer_ids:
            attempted += 1
            try:
                pred_result = prediction_service.predict(
                    features={"customer_id": str(customer_id)},
                    return_proba=True,
                    explain=False,
                )
                prediction = pred_result[0]
                probability = pred_result[1]
                risk_level = pred_result[2]
                confidence_score = pred_result[3]
                top_features = pred_result[4]
                latency_ms = pred_result[5]
                model_version = pred_result[6]
                prediction_service.save_prediction(
                    customer_id=str(customer_id),
                    prediction=prediction,
                    probability=probability,
                    risk_level=risk_level,
                    confidence_score=confidence_score,
                    latency_ms=latency_ms,
                    top_features=top_features,
                    model_version=model_version,
                )
                succeeded += 1
            except Exception:
                failed += 1
                self._logger.error("dashboard_backfill_prediction_failed | customer_id=%s", customer_id, exc_info=True)

        self._logger.info(
            "dashboard_backfill_complete | attempted=%s | succeeded=%s | failed=%s",
            attempted,
            succeeded,
            failed,
        )
        return {"attempted": attempted, "succeeded": succeeded, "failed": failed}
