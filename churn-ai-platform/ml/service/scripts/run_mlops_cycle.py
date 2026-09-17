from __future__ import annotations

import argparse
import json
import subprocess
import sys


def run_cmd(cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run drift check and conditional retraining cycle")
    parser.add_argument("--compare-days", type=int, default=14)
    parser.add_argument("--model-type", choices=["xgboost", "logreg"], default="xgboost")
    parser.add_argument("--feature-version", default="v1")
    parser.add_argument("--horizon-days", type=int, default=30)
    parser.add_argument("--top-k-pct", type=float, default=0.1)
    parser.add_argument("--force-retrain", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    drift_cmd = [
        sys.executable,
        "scripts/monitor_drift.py",
        "--compare-days",
        str(args.compare_days),
    ]
    drift = run_cmd(drift_cmd)

    retrain_cmd = [
        sys.executable,
        "scripts/retraining_pipeline.py",
        "--model-type",
        args.model_type,
        "--feature-version",
        args.feature_version,
        "--horizon-days",
        str(args.horizon_days),
        "--top-k-pct",
        str(args.top_k_pct),
    ]
    if args.force_retrain:
        retrain_cmd.append("--force")

    retrain = run_cmd(retrain_cmd)

    output = {
        "drift": drift,
        "retrain": retrain,
    }
    print(json.dumps(output))

    if drift["returncode"] != 0 or retrain["returncode"] != 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
