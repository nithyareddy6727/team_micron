from pathlib import Path
import json
import shutil

import joblib


ROOT = Path(__file__).resolve().parent
ARTIFACTS_DIR = ROOT / "artifacts"


def pick_existing(paths):
    for path in paths:
        if path.exists():
            return path
    return None


def main():
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    model_source = pick_existing(
        [
            ARTIFACTS_DIR / "churn_model_optimized.pkl",
            ARTIFACTS_DIR / "trained_models" / "xgboost_optimized.joblib",
            ARTIFACTS_DIR / "churn_model.pkl",
        ]
    )
    if model_source is None:
        raise FileNotFoundError("No trained model file found to export churn_model.pkl")

    preprocessing_source = pick_existing(
        [
            ARTIFACTS_DIR / "optimized_preprocessing_pipeline.joblib",
            ARTIFACTS_DIR / "preprocessing_pipeline.joblib",
        ]
    )
    if preprocessing_source is None:
        raise FileNotFoundError(
            "No preprocessing pipeline found to extract scaler and encoder"
        )

    metrics_source = pick_existing(
        [
            ARTIFACTS_DIR / "optimized_metrics.json",
            ARTIFACTS_DIR / "evaluation_metrics.json",
            ARTIFACTS_DIR / "fast_mode_metrics.json",
            ARTIFACTS_DIR / "metrics.json",
        ]
    )
    if metrics_source is None:
        raise FileNotFoundError("No metrics file found to export metrics.json")

    model_target = ARTIFACTS_DIR / "churn_model.pkl"
    if model_source.resolve() != model_target.resolve():
        shutil.copyfile(model_source, model_target)

    preprocessing = joblib.load(preprocessing_source)

    numeric_pipeline = preprocessing.named_transformers_.get("num")
    categorical_pipeline = preprocessing.named_transformers_.get("cat")

    if numeric_pipeline is None or categorical_pipeline is None:
        raise ValueError("Expected 'num' and 'cat' transformers in preprocessing pipeline")

    scaler = numeric_pipeline.named_steps.get("scaler")
    encoder = categorical_pipeline.named_steps.get("onehot")

    if scaler is None:
        raise ValueError("Scaler step not found in numeric pipeline")
    if encoder is None:
        raise ValueError("Encoder step not found in categorical pipeline")

    scaler_target = ARTIFACTS_DIR / "scaler.pkl"
    encoder_target = ARTIFACTS_DIR / "encoder.pkl"
    joblib.dump(scaler, scaler_target)
    joblib.dump(encoder, encoder_target)

    with metrics_source.open("r", encoding="utf-8") as f:
        metrics_data = json.load(f)

    metrics_target = ARTIFACTS_DIR / "metrics.json"
    with metrics_target.open("w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)

    print("Saved artifacts:")
    print(f"- {model_target}")
    print(f"- {scaler_target}")
    print(f"- {encoder_target}")
    print(f"- {metrics_target}")


if __name__ == "__main__":
    main()
