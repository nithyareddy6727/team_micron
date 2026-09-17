from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from predict_churn_system import ChurnPredictionSystem


PROJECT_ROOT = Path(__file__).resolve().parent


def read_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    return json.loads(raw)


def score_single(predictor: ChurnPredictionSystem, payload: dict[str, Any]) -> dict[str, Any]:
    return predictor.predict(payload)


def score_bulk(predictor: ChurnPredictionSystem, payload: dict[str, Any]) -> dict[str, Any]:
    customers = payload.get("customers", [])
    predictions: list[dict[str, Any]] = []

    rows: list[dict[str, Any]] = []
    customer_ids: list[str] = []
    for customer in customers:
        row = dict(predictor.feature_defaults)
        row["tenure_in_months"] = customer.get("tenure_in_months", row.get("tenure_in_months"))
        row["monthly_charge"] = customer.get("monthly_charge", row.get("monthly_charge"))
        row["total_revenue"] = customer.get("total_revenue", row.get("total_revenue"))
        rows.append(row)
        customer_ids.append(str(customer.get("customer_id")))

    if rows:
        frame = pd.DataFrame(rows, columns=predictor.feature_order)
        transformed = predictor.preprocessor.transform(frame)
        probabilities = predictor.model_estimator.predict_proba(transformed)[:, 1]
        predicted = (probabilities >= 0.5).astype(int)

        for idx, probability in enumerate(probabilities):
            predictions.append(
                {
                    "customer_id": customer_ids[idx],
                    "prediction": int(predicted[idx]),
                    "probability": round(float(probability), 4),
                }
            )

    return {
        "count": len(predictions),
        "predictions": predictions,
    }


def main() -> None:
    if len(sys.argv) < 2:
        raise ValueError("Mode is required: single|bulk")

    mode = sys.argv[1].strip().lower()
    payload = read_payload()
    predictor = ChurnPredictionSystem()

    if mode == "single":
        output = score_single(predictor, payload)
    elif mode == "bulk":
        output = score_bulk(predictor, payload)
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    print(json.dumps(output))


if __name__ == "__main__":
    main()
