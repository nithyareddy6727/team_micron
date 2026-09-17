from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import pandas as pd


TARGET_COLUMN = "churn_label"
LEAKAGE_COLUMNS = ["churn_score", "churn_category", "customer_status"]


class ChurnScoringService:
    """Loads churn artifacts and provides single-row prediction utilities."""

    def __init__(self) -> None:
        self.project_root = Path(__file__).resolve().parents[4]
        self.artifacts_dir = self.project_root / "artifacts"
        self.dataset_path = (
            self.project_root
            / "churn-ai-platform"
            / "data"
            / "processed"
            / "telco_churn_cleaned.csv"
        )

        self.model = self._load_model()
        self.preprocessor = self._load_preprocessor()
        self.model_estimator = self._extract_estimator(self.model)
        self.feature_defaults, self.feature_order = self._build_feature_defaults()

    @staticmethod
    def _normalize_column_name(value: str) -> str:
        return (
            str(value)
            .strip()
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
        )

    def _pick_existing(self, candidates: list[Path]) -> Path:
        for path in candidates:
            if path.exists():
                return path
        raise FileNotFoundError(f"Required artifact not found. Checked: {candidates}")

    def _load_model(self):
        model_path = self._pick_existing(
            [
                self.artifacts_dir / "churn_model.pkl",
                self.artifacts_dir / "churn_model_optimized.pkl",
            ]
        )
        return joblib.load(model_path)

    def _load_preprocessor(self):
        preprocessor_path = self._pick_existing(
            [
                self.artifacts_dir / "optimized_preprocessing_pipeline.joblib",
                self.artifacts_dir / "preprocessing_pipeline.joblib",
            ]
        )
        return joblib.load(preprocessor_path)

    @staticmethod
    def _extract_estimator(model: Any) -> Any:
        if hasattr(model, "named_steps") and "model" in model.named_steps:
            return model.named_steps["model"]
        return model

    def _build_feature_defaults(self) -> tuple[dict[str, Any], list[str]]:
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found: {self.dataset_path}")

        df = pd.read_csv(self.dataset_path)
        df.columns = [self._normalize_column_name(c) for c in df.columns]

        features = df.drop(columns=[TARGET_COLUMN], errors="ignore")
        features = features.drop(columns=[c for c in LEAKAGE_COLUMNS if c in features.columns], errors="ignore")

        defaults: dict[str, Any] = {}
        for col in features.columns:
            if pd.api.types.is_numeric_dtype(features[col]):
                defaults[col] = float(features[col].median())
            else:
                mode = features[col].mode(dropna=True)
                defaults[col] = mode.iloc[0] if not mode.empty else "Unknown"

        return defaults, list(features.columns)

    def _build_input_frame(self, user_input: dict[str, Any]) -> pd.DataFrame:
        normalized = {self._normalize_column_name(k): v for k, v in user_input.items()}

        row = dict(self.feature_defaults)
        for key, value in normalized.items():
            if key in row:
                row[key] = value

        return pd.DataFrame([row], columns=self.feature_order)

    def score(self, user_input: dict[str, Any]) -> dict[str, Any]:
        features_df = self._build_input_frame(user_input)
        transformed = self.preprocessor.transform(features_df)
        probability = float(self.model_estimator.predict_proba(transformed)[:, 1][0])
        prediction = int(probability >= 0.5)

        return {
            "prediction": prediction,
            "probability": round(probability, 4),
        }

    def score_batch(self, users: list[dict[str, Any]]) -> dict[str, Any]:
        if not users:
            return {"predictions": []}

        rows: list[dict[str, Any]] = []
        customer_ids: list[str] = []

        for index, user in enumerate(users):
            normalized = {
                self._normalize_column_name(str(k)): v for k, v in dict(user).items()
            }

            row = dict(self.feature_defaults)
            for key, value in normalized.items():
                if key in row:
                    row[key] = value

            rows.append(row)
            customer_ids.append(str(user.get("customer_id") or f"row-{index}"))

        features_df = pd.DataFrame(rows, columns=self.feature_order)
        transformed = self.preprocessor.transform(features_df)
        probabilities = self.model_estimator.predict_proba(transformed)[:, 1]
        predictions = (probabilities >= 0.5).astype(int)

        output = []
        for idx, probability in enumerate(probabilities):
            output.append(
                {
                    "customer_id": customer_ids[idx],
                    "prediction": int(predictions[idx]),
                    "probability": round(float(probability), 4),
                }
            )

        return {"predictions": output}
