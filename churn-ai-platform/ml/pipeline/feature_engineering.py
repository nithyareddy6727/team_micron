from __future__ import annotations

import logging
import re
from pathlib import Path

import numpy as np
import pandas as pd


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

PROJECT_ROOT = Path(__file__).resolve().parent
DATASET_PATH = PROJECT_ROOT / "churn-ai-platform" / "data" / "processed" / "telco_churn_cleaned.csv"
OUTPUT_DIR = PROJECT_ROOT / "artifacts"
OUTPUT_PATH = OUTPUT_DIR / "churn_feature_engineered.csv"
SUMMARY_PATH = OUTPUT_DIR / "feature_engineering_summary.md"

YES_NO_MAP = {
    "yes": 1,
    "no": 0,
    "y": 1,
    "n": 0,
    "true": 1,
    "false": 0,
}

SERVICE_COLUMNS = [
    "phone_service",
    "multiple_lines",
    "internet_service",
    "online_security",
    "online_backup",
    "device_protection_plan",
    "premium_tech_support",
    "streaming_tv",
    "streaming_movies",
    "streaming_music",
    "unlimited_data",
]


def load_dataset(path: Path = DATASET_PATH) -> pd.DataFrame:
    logging.info("Loading dataset from %s", path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    return pd.read_csv(path)


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    cleaned.columns = [
        re.sub(r"[^a-zA-Z0-9]+", "_", str(col).strip().lower()).strip("_")
        for col in cleaned.columns
    ]
    return cleaned


def _is_yes_no_series(series: pd.Series) -> bool:
    values = series.dropna().astype(str).str.strip().str.lower().unique().tolist()
    return bool(values) and set(values).issubset(YES_NO_MAP.keys())


def impute_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    numeric_cols = cleaned.select_dtypes(include="number").columns.tolist()
    categorical_cols = cleaned.select_dtypes(exclude="number").columns.tolist()

    for col in numeric_cols:
        if cleaned[col].isna().any():
            cleaned[col] = cleaned[col].fillna(cleaned[col].median())

    for col in categorical_cols:
        if cleaned[col].isna().any():
            mode = cleaned[col].mode(dropna=True)
            if not mode.empty:
                cleaned[col] = cleaned[col].fillna(mode.iloc[0])

    return cleaned


def encode_yes_no_columns(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    for col in cleaned.columns:
        if cleaned[col].dtype == object and _is_yes_no_series(cleaned[col]):
            cleaned[col] = cleaned[col].astype(str).str.strip().str.lower().map(YES_NO_MAP).astype("Int64")
    return cleaned


def clean_churn_data(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize the raw churn dataset before feature engineering."""

    cleaned = normalize_column_names(df)
    cleaned = cleaned.drop_duplicates().reset_index(drop=True)
    cleaned = impute_missing_values(cleaned)
    cleaned = encode_yes_no_columns(cleaned)

    if "churn_label" in cleaned.columns and cleaned["churn_label"].dtype == object:
        normalized = cleaned["churn_label"].astype(str).str.strip().str.lower()
        cleaned["churn_label"] = normalized.map(YES_NO_MAP).astype("Int64")

    return cleaned


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = denominator.replace(0, np.nan)
    result = numerator / denominator
    return result.replace([np.inf, -np.inf], np.nan).fillna(0)


def add_feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    """Create churn-relevant features from the cleaned dataset."""

    engineered = df.copy()

    if "tenure_in_months" in engineered.columns:
        bins = [-1, 12, 24, 48, np.inf]
        labels = ["0_12_months", "13_24_months", "25_48_months", "49_plus_months"]
        engineered["tenure_group"] = pd.cut(
            engineered["tenure_in_months"], bins=bins, labels=labels
        )

    if {"total_revenue", "tenure_in_months"}.issubset(engineered.columns):
        engineered["revenue_per_month"] = _safe_divide(
            engineered["total_revenue"], engineered["tenure_in_months"]
        )

    if {"monthly_charge", "tenure_in_months"}.issubset(engineered.columns):
        engineered["avg_monthly_value"] = _safe_divide(
            engineered["monthly_charge"], engineered["tenure_in_months"]
        )

    active_service_cols = [col for col in SERVICE_COLUMNS if col in engineered.columns]
    if active_service_cols:
        engineered["service_count"] = engineered[active_service_cols].sum(axis=1)

    if {"satisfaction_score", "tenure_in_months"}.issubset(engineered.columns):
        engineered["satisfaction_tenure_interaction"] = (
            engineered["satisfaction_score"] * engineered["tenure_in_months"]
        )

    if {"satisfaction_score", "monthly_charge"}.issubset(engineered.columns):
        engineered["satisfaction_monthly_charge_interaction"] = (
            engineered["satisfaction_score"] * engineered["monthly_charge"]
        )

    if {"total_revenue", "tenure_in_months"}.issubset(engineered.columns):
        engineered["revenue_tenure_interaction"] = (
            engineered["total_revenue"] * engineered["tenure_in_months"]
        )

    return engineered


def build_summary(original_df: pd.DataFrame, engineered_df: pd.DataFrame) -> str:
    new_columns = [col for col in engineered_df.columns if col not in original_df.columns]
    lines = [
        "# Feature Engineering Summary",
        "",
        f"- Rows: {engineered_df.shape[0]}",
        f"- Original columns: {original_df.shape[1]}",
        f"- Engineered columns: {engineered_df.shape[1]}",
        "",
        "## Added Features",
    ]

    for col in new_columns:
        lines.append(f"- {col}")

    lines.extend(
        [
            "",
            "## Engineering Notes",
            "- tenure_group bins tenure_in_months into ordered customer lifecycle stages.",
            "- revenue_per_month and avg_monthly_value capture revenue efficiency over customer tenure.",
            "- service_count aggregates active service flags into a single usage signal.",
            "- interaction features combine satisfaction and revenue signals with tenure.",
        ]
    )
    return "\n".join(lines)


def engineer_features(path: Path = DATASET_PATH) -> pd.DataFrame:
    raw_df = load_dataset(path)
    cleaned_df = clean_churn_data(raw_df)
    engineered_df = add_feature_engineering(cleaned_df)
    return engineered_df


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    raw_df = load_dataset()
    cleaned_df = clean_churn_data(raw_df)
    engineered_df = add_feature_engineering(cleaned_df)

    engineered_df.to_csv(OUTPUT_PATH, index=False)
    SUMMARY_PATH.write_text(build_summary(cleaned_df, engineered_df), encoding="utf-8")

    print("=== UPDATED DATASET ===")
    print(engineered_df.head(10).to_string(index=False))
    print("\n=== FEATURE ENGINEERING SUMMARY ===")
    print(build_summary(cleaned_df, engineered_df))
    print("\n=== SAVED ARTIFACTS ===")
    print(f"- {OUTPUT_PATH}")
    print(f"- {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
