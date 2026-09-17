from __future__ import annotations

import logging
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

PROJECT_ROOT = Path(__file__).resolve().parent
DATASET_PATH = PROJECT_ROOT / "churn-ai-platform" / "data" / "processed" / "telco_churn_cleaned.csv"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
PLOTS_DIR = ARTIFACTS_DIR / "plots"
OUTLIER_DATASET_PATH = ARTIFACTS_DIR / "churn_outlier_cleaned.csv"
OUTLIER_COUNTS_PATH = ARTIFACTS_DIR / "outlier_summary.csv"
OUTLIER_SUMMARY_PATH = ARTIFACTS_DIR / "outlier_summary.md"

YES_NO_MAP = {
    "yes": 1,
    "no": 0,
    "y": 1,
    "n": 0,
    "true": 1,
    "false": 0,
}

EXCLUDE_FROM_WINSORIZATION = {"customer_id", "churn_label"}


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
            cleaned[col] = (
                cleaned[col].astype(str).str.strip().str.lower().map(YES_NO_MAP).astype("Int64")
            )
    return cleaned


def clean_churn_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean churn data for ML preprocessing."""

    cleaned = normalize_column_names(df)
    cleaned = cleaned.drop_duplicates().reset_index(drop=True)
    cleaned = impute_missing_values(cleaned)
    cleaned = encode_yes_no_columns(cleaned)

    if "churn_label" in cleaned.columns and cleaned["churn_label"].dtype == object:
        normalized = cleaned["churn_label"].astype(str).str.strip().str.lower()
        cleaned["churn_label"] = normalized.map(YES_NO_MAP).astype("Int64")

    return cleaned


def get_numeric_outlier_columns(df: pd.DataFrame) -> list[str]:
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    return [
        col
        for col in numeric_cols
        if col not in EXCLUDE_FROM_WINSORIZATION and df[col].nunique(dropna=True) > 10
    ]


def detect_iqr_outliers(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    records: list[dict[str, float | int | str]] = []

    for col in columns:
        series = df[col].dropna()
        if series.empty:
            continue

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        mask = (df[col] < lower) | (df[col] > upper)
        count = int(mask.sum())

        records.append(
            {
                "column": col,
                "q1": float(q1),
                "q3": float(q3),
                "iqr": float(iqr),
                "lower_bound": float(lower),
                "upper_bound": float(upper),
                "outlier_count": count,
                "outlier_pct": round((count / len(df)) * 100, 2),
            }
        )

    if not records:
        return pd.DataFrame(
            columns=[
                "column",
                "q1",
                "q3",
                "iqr",
                "lower_bound",
                "upper_bound",
                "outlier_count",
                "outlier_pct",
            ]
        )

    return pd.DataFrame(records).sort_values("outlier_count", ascending=False).reset_index(drop=True)


def winsorize_numeric_columns(
    df: pd.DataFrame,
    columns: list[str],
    lower_q: float = 0.01,
    upper_q: float = 0.99,
) -> pd.DataFrame:
    cleaned = df.copy()
    for col in columns:
        lower = cleaned[col].quantile(lower_q)
        upper = cleaned[col].quantile(upper_q)
        cleaned[col] = cleaned[col].clip(lower=lower, upper=upper)
    return cleaned


def save_boxplots(df: pd.DataFrame, columns: list[str], output_path: Path, title: str) -> None:
    if not columns:
        return

    sns.set_theme(style="whitegrid")
    num_cols = 3
    num_rows = int(np.ceil(len(columns) / num_cols))
    fig, axes = plt.subplots(num_rows, num_cols, figsize=(18, 5 * num_rows))
    axes = np.atleast_1d(axes).ravel()

    for idx, col in enumerate(columns):
        sns.boxplot(y=df[col], ax=axes[idx], color="#4C72B0", width=0.35)
        axes[idx].set_title(col)
        axes[idx].set_xlabel("")

    for idx in range(len(columns), len(axes)):
        axes[idx].axis("off")

    fig.suptitle(title, fontsize=16)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def build_outlier_summary(summary: pd.DataFrame, before_shape: tuple[int, int], after_shape: tuple[int, int]) -> str:
    lines = [
        "# Outlier Analysis Summary",
        "",
        f"- Rows before treatment: {before_shape[0]}",
        f"- Rows after treatment: {after_shape[0]}",
        f"- Columns: {before_shape[1]}",
        "",
        "## Top Outlier Columns (IQR)",
        "",
    ]

    if summary.empty:
        lines.append("No outliers detected.")
    else:
        for _, row in summary.head(10).iterrows():
            lines.append(
                f"- {row['column']}: {int(row['outlier_count'])} outliers ({row['outlier_pct']}%), bounds [{row['lower_bound']:.3f}, {row['upper_bound']:.3f}]"
            )

    lines.extend(
        [
            "",
            "## Saved Visualizations",
            f"- {PLOTS_DIR / 'boxplots_before.png'}",
            f"- {PLOTS_DIR / 'boxplots_after.png'}",
            f"- {PLOTS_DIR / 'outlier_counts.png'}",
        ]
    )
    return "\n".join(lines)


def process_dataset(path: Path = DATASET_PATH) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw_df = load_dataset(path)
    cleaned_df = clean_churn_data(raw_df)
    numeric_cols = get_numeric_outlier_columns(cleaned_df)
    outlier_summary = detect_iqr_outliers(cleaned_df, numeric_cols)
    treated_df = winsorize_numeric_columns(cleaned_df, numeric_cols, 0.01, 0.99)
    return cleaned_df, treated_df, outlier_summary


def main() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    cleaned_df, treated_df, outlier_summary = process_dataset()
    numeric_cols = get_numeric_outlier_columns(cleaned_df)

    save_boxplots(
        cleaned_df,
        numeric_cols,
        PLOTS_DIR / "boxplots_before.png",
        "Numeric Feature Boxplots Before Winsorization",
    )
    save_boxplots(
        treated_df,
        numeric_cols,
        PLOTS_DIR / "boxplots_after.png",
        "Numeric Feature Boxplots After Winsorization",
    )

    if not outlier_summary.empty:
        sns.set_theme(style="whitegrid")
        fig, ax = plt.subplots(figsize=(12, 8))
        chart_df = outlier_summary.sort_values("outlier_count", ascending=True)
        sns.barplot(data=chart_df, x="outlier_count", y="column", ax=ax, color="#DD8452")
        ax.set_title("Outlier Counts by Feature (IQR Method)")
        ax.set_xlabel("Outlier Count")
        ax.set_ylabel("Feature")
        fig.tight_layout()
        fig.savefig(PLOTS_DIR / "outlier_counts.png", dpi=160, bbox_inches="tight")
        plt.close(fig)

    treated_df.to_csv(OUTLIER_DATASET_PATH, index=False)
    outlier_summary.to_csv(OUTLIER_COUNTS_PATH, index=False)
    OUTLIER_SUMMARY_PATH.write_text(
        build_outlier_summary(outlier_summary, cleaned_df.shape, treated_df.shape),
        encoding="utf-8",
    )

    print("\n=== CLEANED DATAFRAME ===")
    print(treated_df.head(10).to_string(index=False))

    print("\n=== OUTLIER SUMMARY ===")
    if outlier_summary.empty:
        print("No outliers detected using the IQR method.")
    else:
        print(outlier_summary.head(10).to_string(index=False))

    print("\n=== SAVED ARTIFACTS ===")
    print(f"- {OUTLIER_DATASET_PATH}")
    print(f"- {OUTLIER_COUNTS_PATH}")
    print(f"- {OUTLIER_SUMMARY_PATH}")
    print(f"- {PLOTS_DIR / 'boxplots_before.png'}")
    print(f"- {PLOTS_DIR / 'boxplots_after.png'}")
    print(f"- {PLOTS_DIR / 'outlier_counts.png'}")


if __name__ == "__main__":
    main()
