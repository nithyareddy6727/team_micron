from __future__ import annotations

from collections import defaultdict
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import shap

from schemas.explainability import ExplainabilitySummary, FeatureImpact
from utils.paths import PLATFORM_ROOT


DEFAULT_BACKGROUND_PATH = PLATFORM_ROOT / "ml" / "artifacts" / "root-artifacts" / "churn_feature_engineered.csv"


class ExplainabilityService:
    def __init__(self, artifacts: Any) -> None:
        self._artifacts = artifacts
        self._explainer = None
        self._explainer_initialized = False
        self._background_frame: pd.DataFrame | None = None
        self._background_rows = 0
        self._background_path = Path(os.getenv("SHAP_BACKGROUND_PATH", str(DEFAULT_BACKGROUND_PATH)))
        self._background_sample_size = max(1, int(os.getenv("SHAP_BACKGROUND_SAMPLE_SIZE", "100")))

    def _expected_input_features(self) -> list[str]:
        preprocessor = getattr(self._artifacts, "preprocessor", None)
        if preprocessor is not None and hasattr(preprocessor, "feature_names_in_"):
            return [str(column) for column in preprocessor.feature_names_in_]

        model = getattr(self._artifacts, "model", None)
        if model is not None and hasattr(model, "feature_names_in_"):
            return [str(column) for column in model.feature_names_in_]

        if self._background_path.exists():
            try:
                background = pd.read_csv(self._background_path, nrows=1)
                return [str(column) for column in background.columns if str(column) not in {"customer_id", "churn_label", "prediction", "id"}]
            except Exception:
                return []

        return []

    def _transformed_feature_names(self) -> list[str]:
        preprocessor = getattr(self._artifacts, "preprocessor", None)
        if preprocessor is not None and hasattr(preprocessor, "get_feature_names_out"):
            try:
                return [str(column) for column in preprocessor.get_feature_names_out()]
            except Exception:
                pass

        return self._expected_input_features()

    def _load_background_frame(self) -> pd.DataFrame:
        if self._background_frame is not None:
            return self._background_frame

        expected_features = self._expected_input_features()
        if not self._background_path.exists():
            self._background_frame = pd.DataFrame([{feature: 0 for feature in expected_features}])
            self._background_rows = len(self._background_frame)
            return self._background_frame

        try:
            frame = pd.read_csv(self._background_path)
        except Exception:
            self._background_frame = pd.DataFrame([{feature: 0 for feature in expected_features}])
            self._background_rows = len(self._background_frame)
            return self._background_frame

        if frame.empty:
            self._background_frame = pd.DataFrame([{feature: 0 for feature in expected_features}])
            self._background_rows = len(self._background_frame)
            return self._background_frame

        if len(frame) > self._background_sample_size:
            frame = frame.sample(n=self._background_sample_size, random_state=42)

        if not expected_features:
            expected_features = [
                str(column)
                for column in frame.columns
                if str(column) not in {"customer_id", "churn_label", "prediction", "id"}
            ]

        aligned = pd.DataFrame(index=frame.index)
        for feature in expected_features:
            aligned[feature] = frame[feature] if feature in frame.columns else 0

        self._background_frame = aligned.fillna(0)
        self._background_rows = len(self._background_frame)
        return self._background_frame

    def _prepare_frame(self, features: dict[str, Any]) -> pd.DataFrame:
        frame = pd.DataFrame([features])
        expected_features = self._expected_input_features()
        if expected_features:
            for column in expected_features:
                if column not in frame.columns:
                    frame[column] = 0
            frame = frame[expected_features]
        return frame.fillna(0)

    def _transform_frame(self, frame: pd.DataFrame) -> Any:
        preprocessor = getattr(self._artifacts, "preprocessor", None)
        if preprocessor is None:
            return frame

        transformed = preprocessor.transform(frame)
        if hasattr(transformed, "toarray"):
            return transformed.toarray()
        return transformed

    def _model_step(self) -> Any:
        model = getattr(self._artifacts, "model", None)
        if model is not None and hasattr(model, "named_steps"):
            return model.named_steps.get("model", model)
        return model

    def _model_importance_summary(self, top_n: int, absolute: bool) -> ExplainabilitySummary:
        model = self._model_step()
        if model is None:
            return ExplainabilitySummary(
                available=False,
                method="model_importance",
                model_version=getattr(self._artifacts, "model_version", "unknown"),
                feature_count=0,
                background_rows=self._background_rows,
                top_features=[],
            )

        transformed_feature_names = self._transformed_feature_names()
        raw_scores: list[float] | None = None

        if hasattr(model, "feature_importances_"):
            raw_scores = [float(value) for value in getattr(model, "feature_importances_")]
        elif hasattr(model, "coef_"):
            coefficients = np.asarray(getattr(model, "coef_"))
            if coefficients.ndim == 2:
                coefficients = coefficients[0]
            raw_scores = [float(value) for value in coefficients]

        if not raw_scores:
            return ExplainabilitySummary(
                available=False,
                method="model_importance",
                model_version=getattr(self._artifacts, "model_version", "unknown"),
                feature_count=0,
                background_rows=self._background_rows,
                top_features=[],
            )

        impacts: dict[str, float] = defaultdict(float)
        for index, score in enumerate(raw_scores):
            feature_name = transformed_feature_names[index] if index < len(transformed_feature_names) else f"feature_{index}"
            raw_name = self._raw_feature_name(feature_name)
            impacts[raw_name] += float(abs(score) if absolute else score)

        top_features = [
            FeatureImpact(feature=feature, impact=float(impact))
            for feature, impact in impacts.items()
        ]
        top_features.sort(key=lambda item: abs(item.impact), reverse=True)

        return ExplainabilitySummary(
            available=True,
            method="model_importance",
            model_version=getattr(self._artifacts, "model_version", "unknown"),
            feature_count=len(transformed_feature_names),
            background_rows=self._background_rows,
            top_features=top_features[:top_n],
        )

    def _get_explainer(self):
        if self._explainer_initialized:
            return self._explainer

        self._explainer_initialized = True
        background_frame = self._load_background_frame()
        try:
            transformed_background = self._transform_frame(background_frame)
            self._explainer = shap.Explainer(self._artifacts.model, transformed_background)
        except Exception:
            try:
                self._explainer = shap.Explainer(self._artifacts.model)
            except Exception:
                self._explainer = None

        return self._explainer

    @staticmethod
    def _raw_feature_name(transformed_name: str) -> str:
        if "__" in transformed_name:
            return transformed_name.split("__", 1)[1]
        return transformed_name

    @classmethod
    def _aggregate_shap_values(
        cls,
        values: np.ndarray,
        transformed_feature_names: list[str],
        top_n: int,
        absolute: bool,
    ) -> list[FeatureImpact]:
        matrix = np.asarray(values)
        if matrix.ndim == 1:
            matrix = matrix.reshape(1, -1)

        grouped_values: dict[str, list[float]] = defaultdict(list)
        for row in matrix:
            row_totals: dict[str, float] = defaultdict(float)
            for index, transformed_name in enumerate(transformed_feature_names):
                raw_name = cls._raw_feature_name(transformed_name)
                if index < len(row):
                    row_totals[raw_name] += float(row[index])
            for raw_name, impact in row_totals.items():
                grouped_values[raw_name].append(impact)

        impacts = [
            FeatureImpact(
                feature=feature,
                impact=float(np.mean(np.abs(row_values)) if absolute else np.mean(row_values)),
            )
            for feature, row_values in grouped_values.items()
        ]
        impacts.sort(key=lambda item: abs(item.impact), reverse=True)
        return impacts[:top_n]

    @staticmethod
    def _select_explanation_values(values: Any) -> np.ndarray:
        if isinstance(values, list):
            values = values[-1]

        array = np.asarray(values)
        if array.ndim == 3:
            return array[:, :, -1]
        if array.ndim == 2:
            return array
        if array.ndim == 1:
            return array
        return np.asarray([])

    def _build_summary(self, values: Any, top_n: int, absolute: bool) -> ExplainabilitySummary:
        explainer = self._get_explainer()
        if explainer is None:
            return self._model_importance_summary(top_n=top_n, absolute=absolute)

        transformed_feature_names = self._transformed_feature_names()
        selected_values = self._select_explanation_values(values)
        if selected_values.size == 0:
            return self._model_importance_summary(top_n=top_n, absolute=absolute)

        top_features = self._aggregate_shap_values(selected_values, transformed_feature_names, top_n=top_n, absolute=absolute)
        return ExplainabilitySummary(
            available=True,
            method="shap",
            model_version=getattr(self._artifacts, "model_version", "unknown"),
            feature_count=len(transformed_feature_names),
            background_rows=self._background_rows,
            top_features=top_features,
        )

    def explain_prediction(self, features: dict[str, Any], top_n: int = 5) -> ExplainabilitySummary:
        explainer = self._get_explainer()
        if explainer is None:
            return self._model_importance_summary(top_n=top_n, absolute=False)

        frame = self._prepare_frame(features)
        transformed = self._transform_frame(frame)
        try:
            explanation = explainer(transformed)
            return self._build_summary(explanation.values, top_n=top_n, absolute=False)
        except Exception:
            return self._model_importance_summary(top_n=top_n, absolute=False)

    def global_feature_importance(self, top_n: int = 10) -> ExplainabilitySummary:
        explainer = self._get_explainer()
        if explainer is None:
            return self._model_importance_summary(top_n=top_n, absolute=True)

        background_frame = self._load_background_frame()
        transformed = self._transform_frame(background_frame)
        try:
            explanation = explainer(transformed)
            return self._build_summary(explanation.values, top_n=top_n, absolute=True)
        except Exception:
            return self._model_importance_summary(top_n=top_n, absolute=True)
