from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from preprocessing_pipeline import normalize_column_names, remove_leakage_columns


PROJECT_ROOT = Path(__file__).resolve().parent
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
DATASET_PATH = PROJECT_ROOT / "churn-ai-platform" / "data" / "processed" / "telco_churn_cleaned.csv"
TARGET_COLUMN = "churn_label"


class ChurnPredictionSystem:
    """Load churn artifacts and run single-record predictions from a user dictionary."""

    def __init__(self) -> None:
        self.model = self._load_model()
        self.preprocessor = self._load_preprocessor()
        self.model_estimator = self._extract_estimator(self.model)
        self.feature_defaults, self.feature_order = self._build_feature_defaults(DATASET_PATH)

    @staticmethod
    def _pick_existing(paths: list[Path]) -> Path:
        for path in paths:
            if path.exists():
                return path
        raise FileNotFoundError(f"None of the expected files were found: {paths}")

    def _load_model(self):
        model_path = self._pick_existing(
            [
                ARTIFACTS_DIR / "churn_model.pkl",
                ARTIFACTS_DIR / "churn_model_optimized.pkl",
            ]
        )
        return joblib.load(model_path)

    def _load_preprocessor(self):
        preprocessor_path = self._pick_existing(
            [
                ARTIFACTS_DIR / "optimized_preprocessing_pipeline.joblib",
                ARTIFACTS_DIR / "preprocessing_pipeline.joblib",
            ]
        )
        return joblib.load(preprocessor_path)

    @staticmethod
    def _extract_estimator(model: Any) -> Any:
        if hasattr(model, "named_steps") and "model" in model.named_steps:
            return model.named_steps["model"]
        return model

    @staticmethod
    def _build_feature_defaults(dataset_path: Path) -> tuple[dict[str, Any], list[str]]:
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found: {dataset_path}")

        df = pd.read_csv(dataset_path)
        cleaned = normalize_column_names(df)
        features = cleaned.drop(columns=[TARGET_COLUMN], errors="ignore")
        features = remove_leakage_columns(features)

        defaults: dict[str, Any] = {}
        for col in features.columns:
            if pd.api.types.is_numeric_dtype(features[col]):
                defaults[col] = float(features[col].median())
            else:
                mode = features[col].mode(dropna=True)
                defaults[col] = mode.iloc[0] if not mode.empty else "Unknown"

        return defaults, list(features.columns)

    def _build_model_input_frame(self, user_input: dict[str, Any]) -> pd.DataFrame:
        if not isinstance(user_input, dict):
            raise TypeError("user_input must be a dictionary")

        normalized_input = {
            str(key).strip().lower(): value for key, value in user_input.items()
        }

        row = dict(self.feature_defaults)
        for key, value in normalized_input.items():
            if key in row:
                row[key] = value

        model_input = pd.DataFrame([row], columns=self.feature_order)
        return model_input

    def predict(self, user_input: dict[str, Any]) -> dict[str, Any]:
        model_input = self._build_model_input_frame(user_input)

        transformed = self.preprocessor.transform(model_input)
        probabilities = self.model_estimator.predict_proba(transformed)
        probability = float(probabilities[:, 1][0])

        prediction = int(probability >= 0.5)

        return {
            "prediction": prediction,
            "probability": round(probability, 4),
        }


EXAMPLE_INPUT = {
    "tenure_in_months": 12,
    "monthly_charge": 70,
    "total_revenue": 800,
}


def main() -> None:
    predictor = ChurnPredictionSystem()
    result = predictor.predict(EXAMPLE_INPUT)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
