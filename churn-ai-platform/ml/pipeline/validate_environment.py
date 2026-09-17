from __future__ import annotations

import logging
from pathlib import Path


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


PROJECT_ROOT = Path(__file__).resolve().parent
DATASET_PATH = PROJECT_ROOT / "churn-ai-platform" / "data" / "processed" / "telco_churn_cleaned.csv"


def log_step(message: str) -> None:
    logging.info(message)


def verify_imports() -> None:
    log_step("STEP 1: Verifying package imports")
    import joblib  # noqa: F401
    import lightgbm  # noqa: F401
    import matplotlib  # noqa: F401
    import numpy  # noqa: F401
    import pandas  # noqa: F401
    import sklearn  # noqa: F401
    import seaborn  # noqa: F401
    import shap  # noqa: F401
    import tensorflow  # noqa: F401
    import xgboost  # noqa: F401


def verify_dataset() -> None:
    log_step("STEP 2: Verifying dataset path")
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")
    log_step(f"Dataset found: {DATASET_PATH}")


def print_versions() -> None:
    log_step("STEP 3: Printing environment summary")
    import joblib
    import lightgbm
    import matplotlib
    import numpy as np
    import pandas as pd
    import seaborn as sns
    import shap
    import sklearn
    import tensorflow as tf
    import xgboost

    logging.info("pandas=%s", pd.__version__)
    logging.info("numpy=%s", np.__version__)
    logging.info("scikit-learn=%s", sklearn.__version__)
    logging.info("xgboost=%s", xgboost.__version__)
    logging.info("lightgbm=%s", lightgbm.__version__)
    logging.info("seaborn=%s", sns.__version__)
    logging.info("matplotlib=%s", matplotlib.__version__)
    logging.info("joblib=%s", joblib.__version__)
    logging.info("shap=%s", shap.__version__)
    logging.info("tensorflow=%s", tf.__version__)


def main() -> None:
    log_step("STEP 0: Starting environment validation")
    verify_imports()
    verify_dataset()
    print_versions()
    log_step("Environment validation completed successfully")


if __name__ == "__main__":
    main()