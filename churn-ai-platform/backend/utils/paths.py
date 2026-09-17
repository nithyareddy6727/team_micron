from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PLATFORM_ROOT = BACKEND_ROOT.parent

DEFAULT_MODEL_PATH = PLATFORM_ROOT / "ml" / "artifacts" / "root-artifacts" / "churn_model_optimized.pkl"
FALLBACK_MODEL_PATH = PLATFORM_ROOT / "ml" / "artifacts" / "root-artifacts" / "churn_model.pkl"
DEFAULT_PREPROCESSOR_PATH = PLATFORM_ROOT / "ml" / "artifacts" / "root-artifacts" / "optimized_preprocessing_pipeline.joblib"
FALLBACK_PREPROCESSOR_PATH = PLATFORM_ROOT / "ml" / "artifacts" / "root-artifacts" / "preprocessing_pipeline.joblib"
DEFAULT_CUSTOMERS_PATH = PLATFORM_ROOT / "data" / "processed" / "telco_churn_cleaned.csv"
