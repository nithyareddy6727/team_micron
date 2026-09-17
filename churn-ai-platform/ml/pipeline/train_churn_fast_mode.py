from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from scipy.stats import loguniform, randint, uniform
from sklearn.base import BaseEstimator
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import RandomizedSearchCV, train_test_split
from sklearn.pipeline import Pipeline

from preprocessing_pipeline import (
    DATASET_PATH,
    build_preprocessing_pipeline,
    identify_column_types,
    split_features_target,
)

try:
    from xgboost import XGBClassifier
except Exception as exc:  # pragma: no cover - import guard
    raise ImportError("xgboost is required for the training script") from exc


FAST_MODE = True
ENABLE_SHAP = False
ENABLE_DEEP_LEARNING = False
RANDOM_STATE = 42
TEST_SIZE = 0.2
FAST_N_ITER = 5
FAST_CV = 3
TARGET_COLUMN = "churn_label"
OUTPUT_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_DIR = OUTPUT_DIR / "trained_models"
LOG_DIR = OUTPUT_DIR / "logs"
METRICS_PATH = OUTPUT_DIR / "fast_mode_metrics.json"
COMPARISON_PATH = OUTPUT_DIR / "fast_mode_model_comparison.csv"
PREPROCESSOR_PATH = OUTPUT_DIR / "preprocessing_pipeline.joblib"


@dataclass(frozen=True)
class ModelSpec:
    name: str
    estimator: BaseEstimator
    param_distributions: dict[str, Any]



def setup_logging() -> logging.Logger:
    """Configure console and file logging for the training run."""

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / "fast_mode_training.log"

    logger = logging.getLogger("churn_fast_train")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    return logger


LOGGER = setup_logging()



def load_and_prepare_data(path: Path = DATASET_PATH) -> tuple[pd.DataFrame, pd.Series]:
    """Load churn data, remove leakage columns, and return X/y."""

    LOGGER.info("STEP 1: Loading dataset from %s", path)
    features, target = split_features_target(pd.read_csv(path), target_col=TARGET_COLUMN)
    LOGGER.info("Loaded feature matrix shape: %s", features.shape)
    LOGGER.info("Loaded target distribution: %s", target.value_counts(dropna=False).to_dict())
    return features, target



def encode_target(y: pd.Series) -> pd.Series:
    """Convert churn label to binary 0/1."""

    normalized = y.astype(str).str.strip().str.lower()
    mapped = normalized.map({"no": 0, "yes": 1, "0": 0, "1": 1})
    if mapped.isna().any():
        unknown = sorted(normalized[mapped.isna()].unique().tolist())
        raise ValueError(f"Unexpected target values: {unknown}")
    return mapped.astype(int)



def build_model_specs(scale_pos_weight: float) -> list[ModelSpec]:
    """Create the fast-mode model search spaces."""

    xgb = XGBClassifier(
        objective="binary:logistic",
        eval_metric="auc",
        tree_method="hist",
        random_state=RANDOM_STATE,
        n_jobs=-1,
        scale_pos_weight=scale_pos_weight,
        verbosity=0,
    )
    xgb_params = {
        "model__n_estimators": randint(50, 121),
        "model__max_depth": randint(3, 7),
        "model__learning_rate": loguniform(0.01, 0.2),
        "model__subsample": uniform(0.7, 0.3),
        "model__colsample_bytree": uniform(0.7, 0.3),
        "model__min_child_weight": randint(1, 6),
        "model__reg_lambda": loguniform(1.0, 10.0),
    }

    rf = RandomForestClassifier(
        random_state=RANDOM_STATE,
        n_jobs=-1,
        class_weight="balanced",
    )
    rf_params = {
        "model__n_estimators": randint(100, 201),
        "model__max_depth": [None, 8, 12, 16, 20],
        "model__min_samples_split": randint(2, 11),
        "model__min_samples_leaf": randint(1, 6),
        "model__max_features": ["sqrt", "log2"],
    }

    lr = LogisticRegression(
        random_state=RANDOM_STATE,
        class_weight="balanced",
        max_iter=2000,
        solver="liblinear",
    )
    lr_params = {
        "model__C": loguniform(1e-3, 1e2),
        "model__penalty": ["l1", "l2"],
        "model__solver": ["liblinear"],
    }

    return [
        ModelSpec("xgboost", xgb, xgb_params),
        ModelSpec("random_forest", rf, rf_params),
        ModelSpec("logistic_regression", lr, lr_params),
    ]



def fit_model(
    name: str,
    model: BaseEstimator,
    param_distributions: dict[str, Any],
    X_train: pd.DataFrame,
    y_train: pd.Series,
    preprocessor: Pipeline,
) -> RandomizedSearchCV:
    """Fit a model pipeline using fast randomized search."""

    LOGGER.info("STEP 3: Training %s", name)
    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )

    search = RandomizedSearchCV(
        estimator=pipeline,
        param_distributions=param_distributions,
        n_iter=FAST_N_ITER,
        cv=FAST_CV,
        scoring="roc_auc",
        n_jobs=-1,
        random_state=RANDOM_STATE,
        verbose=0,
        refit=True,
    )
    search.fit(X_train, y_train)
    LOGGER.info("Completed %s | best_cv_roc_auc=%.4f | best_params=%s", name, search.best_score_, search.best_params_)
    return search



def evaluate_model(model: Pipeline, X_test: pd.DataFrame, y_test: pd.Series) -> dict[str, Any]:
    """Evaluate a fitted model on the holdout test set."""

    probabilities = model.predict_proba(X_test)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)

    return {
        "accuracy": accuracy_score(y_test, predictions),
        "roc_auc": roc_auc_score(y_test, probabilities),
        "precision": precision_score(y_test, predictions, zero_division=0),
        "recall": recall_score(y_test, predictions, zero_division=0),
        "f1": f1_score(y_test, predictions, zero_division=0),
        "confusion_matrix": confusion_matrix(y_test, predictions).tolist(),
    }



def save_model_artifact(model: Pipeline, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)



def main() -> None:
    start_time = time.time()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    LOGGER.info("FAST_MODE=%s", FAST_MODE)
    LOGGER.info("SHAP enabled=%s | Deep Learning enabled=%s", ENABLE_SHAP, ENABLE_DEEP_LEARNING)
    LOGGER.info("Training mode configured for rapid debugging")

    X, y_raw = load_and_prepare_data(DATASET_PATH)
    y = encode_target(y_raw)

    LOGGER.info("STEP 2: Performing stratified train/test split")
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )
    LOGGER.info("Split complete | X_train=%s | X_test=%s", X_train.shape, X_test.shape)

    numeric_cols, categorical_cols = identify_column_types(X_train)
    LOGGER.info("Numeric columns: %d | Categorical columns: %d", len(numeric_cols), len(categorical_cols))

    preprocessor = build_preprocessing_pipeline(numeric_cols, categorical_cols)
    LOGGER.info("STEP 4: Fitting preprocessing pipeline on training data")
    preprocessor.fit(X_train)
    joblib.dump(preprocessor, PREPROCESSOR_PATH)

    pos = int(y_train.sum())
    neg = int((y_train == 0).sum())
    scale_pos_weight = neg / max(pos, 1)
    LOGGER.info("Class imbalance ratio | negatives=%d | positives=%d | scale_pos_weight=%.4f", neg, pos, scale_pos_weight)

    model_specs = build_model_specs(scale_pos_weight)
    results: list[dict[str, Any]] = []
    fitted_models: dict[str, Pipeline] = {}

    for spec in model_specs:
        search = fit_model(spec.name, spec.estimator, spec.param_distributions, X_train, y_train, preprocessor)
        best_model = search.best_estimator_
        fitted_models[spec.name] = best_model

        test_metrics = evaluate_model(best_model, X_test, y_test)
        results.append(
            {
                "model": spec.name,
                "cv_best_roc_auc": float(search.best_score_),
                **{k: float(v) if isinstance(v, (np.floating, np.integer)) else v for k, v in test_metrics.items() if k != "confusion_matrix"},
                "confusion_matrix": test_metrics["confusion_matrix"],
                "best_params": search.best_params_,
            }
        )

        model_path = MODEL_DIR / f"{spec.name}_fast_mode.joblib"
        save_model_artifact(best_model, model_path)
        LOGGER.info("Saved trained model: %s", model_path)

    comparison_df = pd.DataFrame(results).sort_values(by="roc_auc", ascending=False).reset_index(drop=True)
    comparison_df.to_csv(COMPARISON_PATH, index=False)

    best_row = comparison_df.iloc[0].to_dict()
    best_model_name = str(best_row["model"])
    best_model = fitted_models[best_model_name]

    metrics_payload = {
        "fast_mode": FAST_MODE,
        "n_iter": FAST_N_ITER,
        "cv": FAST_CV,
        "test_size": TEST_SIZE,
        "random_state": RANDOM_STATE,
        "best_model": best_model_name,
        "best_model_metrics": {
            "accuracy": float(best_row["accuracy"]),
            "roc_auc": float(best_row["roc_auc"]),
            "precision": float(best_row["precision"]),
            "recall": float(best_row["recall"]),
            "f1": float(best_row["f1"]),
            "confusion_matrix": best_row["confusion_matrix"],
        },
        "model_comparison": results,
        "runtime_seconds": round(time.time() - start_time, 2),
        "shap_enabled": ENABLE_SHAP,
        "deep_learning_enabled": ENABLE_DEEP_LEARNING,
    }

    with METRICS_PATH.open("w", encoding="utf-8") as handle:
        json.dump(metrics_payload, handle, indent=2)

    LOGGER.info("STEP 5: Training complete")
    LOGGER.info("Best model: %s", best_model_name)
    LOGGER.info("Metrics saved to %s", METRICS_PATH)
    LOGGER.info("Model comparison saved to %s", COMPARISON_PATH)
    LOGGER.info("Preprocessor saved to %s", PREPROCESSOR_PATH)
    LOGGER.info("Total runtime: %.2f seconds", metrics_payload["runtime_seconds"])

    print("=== MODEL COMPARISON ===")
    print(comparison_df[["model", "cv_best_roc_auc", "accuracy", "roc_auc", "precision", "recall", "f1"]].to_string(index=False))
    print("\n=== BEST MODEL ===")
    print(best_model_name)
    print("\n=== METRICS FILE ===")
    print(METRICS_PATH)
    print("\n=== SAVED MODELS ===")
    for name in fitted_models:
        print(MODEL_DIR / f"{name}_fast_mode.joblib")
    print("\n=== PREPROCESSOR ===")
    print(PREPROCESSOR_PATH)
    print("\n=== LOG FILE ===")
    print(LOG_DIR / "fast_mode_training.log")


if __name__ == "__main__":
    main()
