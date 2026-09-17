from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from preprocessing_pipeline import DATASET_PATH, split_features_target


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("churn_eval")

PROJECT_ROOT = Path(__file__).resolve().parent
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
TRAINED_MODELS_DIR = ARTIFACTS_DIR / "trained_models"
METRICS_CSV_PATH = ARTIFACTS_DIR / "evaluation_metrics.csv"
METRICS_JSON_PATH = ARTIFACTS_DIR / "evaluation_metrics.json"
REPORT_PATH = ARTIFACTS_DIR / "evaluation_report.md"
BEST_SUMMARY_PATH = ARTIFACTS_DIR / "best_model_summary.md"

RANDOM_STATE = 42
TEST_SIZE = 0.2
TARGET_COLUMN = "churn_label"


def encode_target(y: pd.Series) -> pd.Series:
    normalized = y.astype(str).str.strip().str.lower()
    mapped = normalized.map({"no": 0, "yes": 1, "0": 0, "1": 1})
    if mapped.isna().any():
        unknown = sorted(normalized[mapped.isna()].unique().tolist())
        raise ValueError(f"Unexpected target values: {unknown}")
    return mapped.astype(int)


def load_data() -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    LOGGER.info("Loading dataset from %s", DATASET_PATH)
    raw = pd.read_csv(DATASET_PATH)
    X, y_raw = split_features_target(raw, target_col=TARGET_COLUMN)
    y = encode_target(y_raw)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )
    LOGGER.info("Data split complete | X_train=%s | X_test=%s", X_train.shape, X_test.shape)
    return X_train, y_train, X_test, y_test


def discover_models() -> dict[str, Path]:
    candidates = {
        "xgboost": TRAINED_MODELS_DIR / "xgboost_optimized.joblib",
        "random_forest": TRAINED_MODELS_DIR / "random_forest_optimized.joblib",
        "logistic_regression": TRAINED_MODELS_DIR / "logistic_regression_optimized.joblib",
        "lightgbm": TRAINED_MODELS_DIR / "lightgbm_optimized.joblib",
    }

    available = {name: path for name, path in candidates.items() if path.exists()}
    if not available:
        raise FileNotFoundError(f"No optimized model artifacts found under: {TRAINED_MODELS_DIR}")
    return available


def evaluate_model(model: Any, X_test: pd.DataFrame, y_test: pd.Series) -> dict[str, Any]:
    probs = model.predict_proba(X_test)[:, 1]
    preds = (probs >= 0.5).astype(int)

    return {
        "accuracy": float(accuracy_score(y_test, preds)),
        "roc_auc": float(roc_auc_score(y_test, probs)),
        "precision": float(precision_score(y_test, preds, zero_division=0)),
        "recall": float(recall_score(y_test, preds, zero_division=0)),
        "f1": float(f1_score(y_test, preds, zero_division=0)),
        "confusion_matrix": confusion_matrix(y_test, preds).tolist(),
    }


def build_report(results_df: pd.DataFrame, best_row: pd.Series) -> str:
    lines = [
        "# Churn Model Evaluation Report",
        "",
        f"- Evaluation dataset: {DATASET_PATH}",
        f"- Test size: {TEST_SIZE}",
        f"- Random state: {RANDOM_STATE}",
        "",
        "## Model Comparison (sorted by ROC-AUC)",
        "",
    ]

    table_header = "| Model | Accuracy | ROC-AUC | Precision | Recall | F1 | Confusion Matrix |"
    table_sep = "|---|---:|---:|---:|---:|---:|---|"
    lines.append(table_header)
    lines.append(table_sep)

    for _, row in results_df.iterrows():
        lines.append(
            f"| {row['model']} | {row['accuracy']:.4f} | {row['roc_auc']:.4f} | {row['precision']:.4f} | {row['recall']:.4f} | {row['f1']:.4f} | {row['confusion_matrix']} |"
        )

    lines.extend(
        [
            "",
            "## Best Model",
            f"- Selected model: {best_row['model']}",
            f"- ROC-AUC: {best_row['roc_auc']:.4f}",
            f"- Accuracy: {best_row['accuracy']:.4f}",
            f"- Precision: {best_row['precision']:.4f}",
            f"- Recall: {best_row['recall']:.4f}",
            f"- F1-score: {best_row['f1']:.4f}",
            f"- Confusion matrix: {best_row['confusion_matrix']}",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    X_train, y_train, X_test, y_test = load_data()
    models = discover_models()

    results: list[dict[str, Any]] = []
    for model_name, model_path in models.items():
        LOGGER.info("Evaluating model: %s", model_name)
        model = joblib.load(model_path)
        metrics = evaluate_model(model, X_test, y_test)
        results.append({"model": model_name, **metrics, "model_path": str(model_path)})

    results_df = pd.DataFrame(results).sort_values(by="roc_auc", ascending=False).reset_index(drop=True)
    best_row = results_df.iloc[0]

    METRICS_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(METRICS_CSV_PATH, index=False)

    metrics_payload = {
        "target": TARGET_COLUMN,
        "test_size": TEST_SIZE,
        "random_state": RANDOM_STATE,
        "best_model": best_row["model"],
        "best_metrics": {
            "accuracy": float(best_row["accuracy"]),
            "roc_auc": float(best_row["roc_auc"]),
            "precision": float(best_row["precision"]),
            "recall": float(best_row["recall"]),
            "f1": float(best_row["f1"]),
            "confusion_matrix": best_row["confusion_matrix"],
        },
        "model_results": results,
    }
    METRICS_JSON_PATH.write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")

    report_text = build_report(results_df, best_row)
    REPORT_PATH.write_text(report_text, encoding="utf-8")

    best_summary = "\n".join(
        [
            "# Best Model Summary",
            "",
            f"- Model: {best_row['model']}",
            f"- ROC-AUC: {best_row['roc_auc']:.4f}",
            f"- Accuracy: {best_row['accuracy']:.4f}",
            f"- Precision: {best_row['precision']:.4f}",
            f"- Recall: {best_row['recall']:.4f}",
            f"- F1-score: {best_row['f1']:.4f}",
            f"- Confusion matrix: {best_row['confusion_matrix']}",
            f"- Model artifact: {best_row['model_path']}",
        ]
    )
    BEST_SUMMARY_PATH.write_text(best_summary, encoding="utf-8")

    print("=== MODEL EVALUATION COMPLETE ===")
    print(results_df[["model", "accuracy", "roc_auc", "precision", "recall", "f1", "confusion_matrix"]].to_string(index=False))
    print("\n=== BEST MODEL ===")
    print(best_summary)
    print("\n=== ARTIFACTS ===")
    print(METRICS_CSV_PATH)
    print(METRICS_JSON_PATH)
    print(REPORT_PATH)
    print(BEST_SUMMARY_PATH)


if __name__ == "__main__":
    main()
