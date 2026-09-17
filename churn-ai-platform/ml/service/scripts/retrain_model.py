from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime

from sqlalchemy import text

from app.db import get_engine
from app.services.training_service import get_training_run, run_training_job

RETRAIN_THRESHOLD = 0.3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run retraining based on latest drift PSI")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--model-type", choices=["xgboost", "logreg"], default="xgboost")
    parser.add_argument("--feature-version", default="v1")
    parser.add_argument("--horizon-days", type=int, default=30)
    parser.add_argument("--top-k-pct", type=float, default=0.1)
    return parser.parse_args()


def get_latest_max_psi(engine) -> float:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT COALESCE(MAX(psi_value), 0) AS max_psi
                FROM drift_metrics
                WHERE computed_at >= DATE_SUB(NOW(), INTERVAL 2 DAY)
                """
            )
        ).mappings().first()

    return float(row["max_psi"] if row else 0.0)


def insert_retrain_run(engine, run_id: str, trigger_reason: str, trigger_value: float) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO retraining_runs (run_id, triggered_by, trigger_reason, trigger_value, status)
                VALUES (:run_id, 'drift', :trigger_reason, :trigger_value, 'running')
                """
            ),
            {
                "run_id": run_id,
                "trigger_reason": trigger_reason,
                "trigger_value": trigger_value,
            },
        )


def finalize_retrain_run(engine, run_id: str, status: str, model_version: str | None, details: dict) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE retraining_runs
                SET status = :status,
                    model_version = :model_version,
                    details_json = :details_json,
                    completed_at = NOW()
                WHERE run_id = :run_id
                """
            ),
            {
                "run_id": run_id,
                "status": status,
                "model_version": model_version,
                "details_json": json.dumps(details),
            },
        )


def main() -> None:
    args = parse_args()
    engine = get_engine()

    max_psi = get_latest_max_psi(engine)
    should_retrain = args.force or (max_psi > RETRAIN_THRESHOLD)

    if not should_retrain:
        print(json.dumps({"status": "skipped", "reason": "psi_below_threshold", "max_psi": max_psi}))
        return

    run_id = str(uuid.uuid4())
    insert_retrain_run(engine, run_id, "psi_threshold", max_psi)

    try:
        run_training_job(
            run_id=run_id,
            model_type=args.model_type,
            feature_version=args.feature_version,
            horizon_days=args.horizon_days,
            top_k_pct=args.top_k_pct,
            set_as_production=True,
        )

        result = get_training_run(run_id) or {}

        if result.get("status") == "completed":
            finalize_retrain_run(
                engine,
                run_id,
                "completed",
                result.get("model_version"),
                {
                    "finished_at": datetime.utcnow().isoformat(),
                    "max_psi": max_psi,
                    "message": result.get("message", "Retraining completed"),
                },
            )
        else:
            finalize_retrain_run(
                engine,
                run_id,
                "failed",
                None,
                {
                    "finished_at": datetime.utcnow().isoformat(),
                    "max_psi": max_psi,
                    "message": result.get("message", "Retraining failed"),
                },
            )

        print(json.dumps({"run_id": run_id, "max_psi": max_psi, "result": result}))

    except Exception as exc:
        finalize_retrain_run(
            engine,
            run_id,
            "failed",
            None,
            {
                "finished_at": datetime.utcnow().isoformat(),
                "max_psi": max_psi,
                "message": str(exc),
            },
        )
        raise


if __name__ == "__main__":
    main()
