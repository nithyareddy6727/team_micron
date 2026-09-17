from __future__ import annotations

import os
import importlib
from dataclasses import dataclass
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import text

from app.config import settings
from app.db import get_engine


@dataclass
class LoadedModel:
    model_version: str
    model_type: str
    feature_version: str
    threshold_medium: float
    threshold_high: float
    model: object
    feature_columns: list[str]
    explainer: object


_loaded_model: LoadedModel | None = None


def _build_explainer(model: object, model_type: str):
    try:
        shap = importlib.import_module("shap")
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "SHAP is not installed. Install service dependencies from requirements.txt"
        ) from exc
    if model_type == "xgboost":
        return shap.TreeExplainer(model)
    return shap.Explainer(model)


def load_active_model(force_reload: bool = False) -> LoadedModel | None:
    global _loaded_model
    if _loaded_model is not None and not force_reload:
        return _loaded_model

    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT model_version, model_type, feature_version, threshold_medium, threshold_high, artifact_uri
                FROM model_registry
                WHERE status = 'production'
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """
            )
        ).mappings().first()

    if row is None:
        _loaded_model = None
        return None

    artifact_uri = row["artifact_uri"]
    artifact_path = artifact_uri
    if not os.path.isabs(artifact_path):
        artifact_path = os.path.join(settings.model_artifact_dir, artifact_uri)

    if not os.path.exists(artifact_path):
        _loaded_model = None
        return None

    payload = joblib.load(artifact_path)
    model = payload["model"]
    feature_columns = payload["feature_columns"]

    _loaded_model = LoadedModel(
        model_version=row["model_version"],
        model_type=row["model_type"],
        feature_version=row["feature_version"],
        threshold_medium=float(row["threshold_medium"]),
        threshold_high=float(row["threshold_high"]),
        model=model,
        feature_columns=feature_columns,
        explainer=_build_explainer(model, row["model_type"]),
    )
    return _loaded_model


def score_row(loaded: LoadedModel, row_df: pd.DataFrame) -> tuple[float, list[dict[str, object]]]:
    proba = loaded.model.predict_proba(row_df[loaded.feature_columns])[:, 1]
    score = float(proba[0])

    shap_values = loaded.explainer(row_df[loaded.feature_columns])
    shap_row = np.array(shap_values.values[0], dtype=float)

    sort_idx = np.argsort(np.abs(shap_row))[::-1][:5]
    top_drivers: list[dict[str, object]] = []
    for idx in sort_idx:
        val = float(shap_row[idx])
        top_drivers.append(
            {
                "feature": loaded.feature_columns[idx],
                "shap_value": round(val, 6),
                "direction": "increase" if val >= 0 else "decrease",
            }
        )

    return score, top_drivers


def band_for_score(score: float, threshold_medium: float, threshold_high: float) -> str:
    if score >= threshold_high:
        return "high"
    if score >= threshold_medium:
        return "medium"
    return "low"


def now_iso() -> str:
    return datetime.utcnow().isoformat()
