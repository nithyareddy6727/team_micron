from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

PROJECT_ROOT = Path(__file__).resolve().parent
DATASET_PATH = PROJECT_ROOT / "churn-ai-platform" / "data" / "processed" / "telco_churn_cleaned.csv"


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("-", "_", regex=False)
    )
    return df


def load_data(path: Path = DATASET_PATH) -> pd.DataFrame:
    logging.info("Loading dataset from %s", path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    return pd.read_csv(path)


def summarize_dataset(df: pd.DataFrame, target_col: str = "churn_label") -> None:
    df = normalize_columns(df)

    logging.info("Shape: %s", df.shape)
    print("\n=== DATASET SHAPE ===")
    print(df.shape)

    print("\n=== INFO ===")
    df.info()

    print("\n=== DESCRIBE (NUMERIC) ===")
    print(df.describe().T)

    print("\n=== TARGET COLUMN ===")
    if target_col in df.columns:
        print(target_col)
        print(df[target_col].value_counts(dropna=False))
        print((df[target_col].value_counts(normalize=True) * 100).round(2))
    else:
        raise KeyError(f"Target column '{target_col}' not found.")

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = df.select_dtypes(exclude="number").columns.tolist()

    print("\n=== NUMERICAL COLUMNS ===")
    print(numeric_cols)

    print("\n=== CATEGORICAL COLUMNS ===")
    print(categorical_cols)

    print("\n=== MISSING VALUES ===")
    missing = df.isna().sum().sort_values(ascending=False)
    print(missing[missing > 0] if (missing > 0).any() else "No missing values found")

    print("\n=== DUPLICATES ===")
    print(df.duplicated().sum())

    churn_binary = df[target_col].map({"Yes": 1, "No": 0})
    insight_numeric = df[numeric_cols].copy()
    insight_numeric["churn_binary"] = churn_binary
    correlations = insight_numeric.corr(numeric_only=True)["churn_binary"].drop("churn_binary")

    print("\n=== SUMMARY INSIGHTS ===")
    print(f"Rows: {len(df):,}")
    print(f"Columns: {df.shape[1]}")
    print(f"Churn rate: {df[target_col].eq('Yes').mean() * 100:.2f}%")
    print(f"Average tenure for churned customers: {df.loc[df[target_col] == 'Yes', 'tenure_in_months'].mean():.2f}")
    print(f"Average tenure for retained customers: {df.loc[df[target_col] == 'No', 'tenure_in_months'].mean():.2f}")
    print(f"Average monthly charge for churned customers: {df.loc[df[target_col] == 'Yes', 'monthly_charge'].mean():.2f}")
    print(f"Average monthly charge for retained customers: {df.loc[df[target_col] == 'No', 'monthly_charge'].mean():.2f}")
    print("Top absolute numeric correlations with churn:")
    print(correlations.abs().sort_values(ascending=False).head(10))


def main() -> None:
    df = load_data()
    summarize_dataset(df)


if __name__ == "__main__":
    main()