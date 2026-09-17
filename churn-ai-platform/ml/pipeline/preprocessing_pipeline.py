from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Tuple

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

PROJECT_ROOT = Path(__file__).resolve().parent
DATASET_PATH = PROJECT_ROOT / "churn-ai-platform" / "data" / "processed" / "telco_churn_cleaned.csv"
TARGET_COLUMN = "churn_label"
LEAKAGE_COLUMNS = ["churn_score", "churn_category", "customer_status"]


def load_dataset(path: Path = DATASET_PATH) -> pd.DataFrame:
    """Load the churn dataset from disk."""

    logging.info("Loading dataset from %s", path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    return pd.read_csv(path)


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize columns to lowercase snake_case."""

    cleaned = df.copy()
    cleaned.columns = [
        re.sub(r"[^a-zA-Z0-9]+", "_", str(col).strip().lower()).strip("_")
        for col in cleaned.columns
    ]
    return cleaned


def remove_leakage_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Drop leakage-prone columns before preprocessing."""

    return df.drop(columns=[col for col in LEAKAGE_COLUMNS if col in df.columns], errors="ignore")


def split_features_target(df: pd.DataFrame, target_col: str = TARGET_COLUMN) -> Tuple[pd.DataFrame, pd.Series]:
    """Split features and target, excluding leakage columns from features."""

    normalized = normalize_column_names(df)
    if target_col not in normalized.columns:
        raise KeyError(f"Target column '{target_col}' not found.")

    target = normalized[target_col]
    features = normalized.drop(columns=[target_col], errors="ignore")
    features = remove_leakage_columns(features)
    return features, target


def identify_column_types(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Identify numerical and categorical columns from features."""

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = df.select_dtypes(exclude="number").columns.tolist()
    return numeric_cols, categorical_cols


def build_preprocessing_pipeline(numeric_cols: list[str], categorical_cols: list[str]) -> ColumnTransformer:
    """Create the preprocessing pipeline requested for churn modeling."""

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessing_pipeline = ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, numeric_cols),
            ("cat", categorical_pipeline, categorical_cols),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )

    return preprocessing_pipeline


def prepare_preprocessing_pipeline(path: Path = DATASET_PATH) -> tuple[ColumnTransformer, pd.DataFrame, pd.Series]:
    """Load data, remove leakage, identify column types, and build the preprocessing object."""

    df = load_dataset(path)
    features, target = split_features_target(df)
    numeric_cols, categorical_cols = identify_column_types(features)
    pipeline = build_preprocessing_pipeline(numeric_cols, categorical_cols)
    return pipeline, features, target


def main() -> None:
    pipeline, features, target = prepare_preprocessing_pipeline()
    numeric_cols, categorical_cols = identify_column_types(features)

    print("=== FEATURE SUMMARY ===")
    print(f"Numeric columns ({len(numeric_cols)}): {numeric_cols}")
    print(f"Categorical columns ({len(categorical_cols)}): {categorical_cols}")
    print(f"Target column: {TARGET_COLUMN}")
    print(f"Leakage columns removed: {LEAKAGE_COLUMNS}")

    print("\n=== PREPROCESSING PIPELINE OBJECT ===")
    print(pipeline)

    print("\n=== SAMPLE TARGET DISTRIBUTION ===")
    print(target.value_counts(dropna=False))


if __name__ == "__main__":
    main()
