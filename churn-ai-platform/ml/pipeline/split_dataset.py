from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from preprocessing_pipeline import normalize_column_names, remove_leakage_columns


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

PROJECT_ROOT = Path(__file__).resolve().parent
DATASET_PATH = PROJECT_ROOT / "churn-ai-platform" / "data" / "processed" / "telco_churn_cleaned.csv"
TARGET_COLUMN = "churn_label"
TEST_SIZE = 0.2
RANDOM_STATE = 42


def load_dataset(path: Path = DATASET_PATH) -> pd.DataFrame:
    """Load the churn dataset from disk."""

    logging.info("Loading dataset from %s", path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    return pd.read_csv(path)


def split_churn_dataset(
    df: pd.DataFrame,
    target_col: str = TARGET_COLUMN,
    test_size: float = TEST_SIZE,
    random_state: int = RANDOM_STATE,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Split churn data into train/test sets with stratification."""

    cleaned = normalize_column_names(df)
    if target_col not in cleaned.columns:
        raise KeyError(f"Target column '{target_col}' not found.")

    y = cleaned[target_col]
    X = cleaned.drop(columns=[target_col], errors="ignore")
    X = remove_leakage_columns(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )

    return X_train, X_test, y_train, y_test


def main() -> None:
    df = load_dataset()
    X_train, X_test, y_train, y_test = split_churn_dataset(df)

    print("=== SPLIT COMPLETE ===")
    print(f"X_train shape: {X_train.shape}")
    print(f"X_test shape: {X_test.shape}")
    print(f"y_train shape: {y_train.shape}")
    print(f"y_test shape: {y_test.shape}")

    print("\n=== TRAIN TARGET DISTRIBUTION ===")
    print(y_train.value_counts(dropna=False))

    print("\n=== TEST TARGET DISTRIBUTION ===")
    print(y_test.value_counts(dropna=False))

    print("\n=== FEATURE SAMPLE ===")
    print(X_train.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
