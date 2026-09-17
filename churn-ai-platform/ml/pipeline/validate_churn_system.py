from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from preprocessing_pipeline import normalize_column_names, remove_leakage_columns


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

PROJECT_ROOT = Path(__file__).resolve().parent
DATASET_PATH = PROJECT_ROOT / "churn-ai-platform" / "data" / "processed" / "telco_churn_cleaned.csv"
MODEL_PATH = PROJECT_ROOT / "artifacts" / "churn_model.pkl"
METRICS_PATH = PROJECT_ROOT / "artifacts" / "metrics.json"
COMPARISON_PATH = PROJECT_ROOT / "artifacts" / "model_comparison.csv"
TARGET_COLUMN = "churn_label"
LEAKAGE_COLUMNS = ["churn_score", "churn_category", "customer_status"]


SAMPLE_INPUT: dict[str, Any] = {
    "tenure_in_months": 12,
    "monthly_charge": 70,
    "total_revenue": 800,
}


REQUIRED_FILES = [MODEL_PATH, METRICS_PATH, COMPARISON_PATH]


def verify_required_files() -> None:
    """Ensure the requested artifact files are present."""

    for path in REQUIRED_FILES:
        if not path.exists():
            raise FileNotFoundError(f"Required artifact missing: {path}")
        logging.info("Verified artifact: %s", path)


def load_dataset(path: Path = DATASET_PATH) -> pd.DataFrame:
    """Load the raw churn dataset."""

    logging.info("Loading dataset from %s", path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    return pd.read_csv(path)


def build_default_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Build a single-row feature frame using dataset medians/modes for missing values."""

    cleaned = normalize_column_names(df)
    if TARGET_COLUMN not in cleaned.columns:
        raise KeyError(f"Target column '{TARGET_COLUMN}' not found.")

    features = cleaned.drop(columns=[TARGET_COLUMN], errors="ignore")
    features = remove_leakage_columns(features)

    defaults: dict[str, Any] = {}
    for col in features.columns:
        if pd.api.types.is_numeric_dtype(features[col]):
            defaults[col] = float(features[col].median())
        else:
            mode = features[col].mode(dropna=True)
            defaults[col] = mode.iloc[0] if not mode.empty else "Unknown"

    sample_row = pd.DataFrame([defaults])
    for key, value in SAMPLE_INPUT.items():
        if key in sample_row.columns:
            sample_row.loc[0, key] = value

    return sample_row[features.columns]


def predict_sample(model: Any, sample_features: pd.DataFrame) -> dict[str, Any]:
    """Predict churn probability and class for the provided sample."""

    probability = float(model.predict_proba(sample_features)[:, 1][0])
    prediction = int(probability >= 0.5)
    return {
        "prediction": prediction,
        "churn_probability": probability,
        "predicted_label": "churn" if prediction == 1 else "no_churn",
    }


def main() -> None:
    verify_required_files()
    model = joblib.load(MODEL_PATH)
    dataset = load_dataset()
    sample_features = build_default_feature_frame(dataset)
    output = predict_sample(model, sample_features)

    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))

    print("=== FILE VERIFICATION ===")
    for path in REQUIRED_FILES:
        print(f"FOUND: {path}")

    print("\n=== SAMPLE INPUT ===")
    print(json.dumps(SAMPLE_INPUT, indent=2))

    print("\n=== PREDICTION OUTPUT ===")
    print(json.dumps(output, indent=2))

    print("\n=== MODEL METRICS ===")
    print(json.dumps(metrics.get("best_model_metrics", {}), indent=2))

    print("\n=== COMPARISON FILE ===")
    print(COMPARISON_PATH)


if __name__ == "__main__":
    main()
