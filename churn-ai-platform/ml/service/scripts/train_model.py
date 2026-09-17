from __future__ import annotations

import argparse

from app.services.training_service import create_run_id, get_training_run, run_training_job


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train churn model with time-based validation")
    parser.add_argument("--model-type", choices=["xgboost", "logreg"], default="xgboost")
    parser.add_argument("--feature-version", default="v1")
    parser.add_argument("--horizon-days", type=int, default=30)
    parser.add_argument("--top-k-pct", type=float, default=0.1)
    parser.add_argument("--set-as-production", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_id = create_run_id()

    run_training_job(
        run_id=run_id,
        model_type=args.model_type,
        feature_version=args.feature_version,
        horizon_days=args.horizon_days,
        top_k_pct=args.top_k_pct,
        set_as_production=args.set_as_production,
    )

    result = get_training_run(run_id)
    print({"run_id": run_id, "result": result})


if __name__ == "__main__":
    main()
