"""Production-grade customer churn training pipeline.

This script builds a dual-mode system:
- FAST_MODE = True: quick development run
- FAST_MODE = False: full training run with heavier tuning and explainability

Outputs:
- artifacts/churn_model.pkl
- artifacts/scaler.pkl
- artifacts/encoder.pkl
- artifacts/metrics.json
- artifacts/model_comparison.csv
- artifacts/plots/*
- data.md

Run:
    f:/project/churn-prediction/.venv/Scripts/python.exe data.py
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import randint, uniform
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import RandomizedSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

try:
    from xgboost import XGBClassifier

    HAS_XGBOOST = True
except Exception:
    HAS_XGBOOST = False

try:
    from lightgbm import LGBMClassifier

    HAS_LIGHTGBM = True
except Exception:
    HAS_LIGHTGBM = False

try:
    import shap

    HAS_SHAP = True
except Exception:
    HAS_SHAP = False

try:
    import tensorflow as tf
    from tensorflow.keras import Sequential
    from tensorflow.keras.layers import Dense, Dropout

    HAS_TENSORFLOW = True
except Exception:
    HAS_TENSORFLOW = False


RANDOM_STATE = 42
FAST_MODE = True
FULL_MODE = not FAST_MODE

TARGET_COLUMN = "churn_label"
TARGET_ALIASES = ["churn", "target", "label"]
ID_COLUMNS = {"customer_id"}
LEAKAGE_COLUMNS = {"customer_status", "churn_score", "churn_category"}

YES_NO_MAP = {
    "yes": 1,
    "no": 0,
    "y": 1,
    "n": 0,
    "true": 1,
    "false": 0,
    "1": 1,
    "0": 0,
}

SERVICE_COLUMNS = [
    "referred_a_friend",
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


@dataclass
class Artifacts:
    model_path: Path
    scaler_path: Path
    encoder_path: Path
    metrics_path: Path
    comparison_path: Path
    report_path: Path
    plots_dir: Path


@dataclass(frozen=True)
class ModeConfig:
    name: str
    xgb_n_iter: int
    xgb_cv: int
    rf_n_iter: int
    rf_cv: int
    lgbm_n_iter: int
    lgbm_cv: int
    enable_shap: bool
    enable_dl: bool
    xgb_estimators_low: int
    xgb_estimators_high: int
    rf_estimators_low: int
    rf_estimators_high: int


FAST_CONFIG = ModeConfig(
    name="FAST",
    xgb_n_iter=5,
    xgb_cv=3,
    rf_n_iter=5,
    rf_cv=3,
    lgbm_n_iter=5,
    lgbm_cv=3,
    enable_shap=False,
    enable_dl=False,
    xgb_estimators_low=50,
    xgb_estimators_high=120,
    rf_estimators_low=80,
    rf_estimators_high=200,
)

FULL_CONFIG = ModeConfig(
    name="FULL",
    xgb_n_iter=30,
    xgb_cv=5,
    rf_n_iter=20,
    rf_cv=5,
    lgbm_n_iter=20,
    lgbm_cv=5,
    enable_shap=True,
    enable_dl=True,
    xgb_estimators_low=150,
    xgb_estimators_high=500,
    rf_estimators_low=200,
    rf_estimators_high=700,
)


class ChurnPipeline:
    def __init__(self, data_path: Path, artifacts_dir: Path, fast_mode: bool = FAST_MODE):
        self.data_path = data_path
        self.artifacts_dir = artifacts_dir
        self.fast_mode = fast_mode
        self.mode_config = FAST_CONFIG if fast_mode else FULL_CONFIG

        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        (self.artifacts_dir / "plots").mkdir(parents=True, exist_ok=True)

        self.artifacts = Artifacts(
            model_path=self.artifacts_dir / "churn_model.pkl",
            scaler_path=self.artifacts_dir / "scaler.pkl",
            encoder_path=self.artifacts_dir / "encoder.pkl",
            metrics_path=self.artifacts_dir / "metrics.json",
            comparison_path=self.artifacts_dir / "model_comparison.csv",
            report_path=Path("data.md"),
            plots_dir=self.artifacts_dir / "plots",
        )

        self.logger = self._configure_logging()
        self.preprocessor: ColumnTransformer | None = None
        self.best_pipeline: Pipeline | None = None
        self.best_model_name = ""
        self.input_columns: list[str] = []
        self.feature_names_in_: list[str] = []
        self.target_distribution: dict[int, int] = {}

    @staticmethod
    def _configure_logging() -> logging.Logger:
        logger = logging.getLogger("churn_pipeline")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        logger.addHandler(console)
        return logger

    @staticmethod
    def _safe_divide(a: pd.Series, b: pd.Series) -> pd.Series:
        denominator = b.replace(0, np.nan)
        return (a / denominator).replace([np.inf, -np.inf], np.nan)

    @staticmethod
    def _normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = [re.sub(r"[^a-zA-Z0-9]+", "_", str(col).strip().lower()).strip("_") for col in df.columns]
        return df

    @staticmethod
    def _to_binary_series(series: pd.Series) -> pd.Series:
        normalized = series.astype(str).str.strip().str.lower()
        return normalized.map(YES_NO_MAP)

    @staticmethod
    def _coerce_target(series: pd.Series) -> pd.Series:
        normalized = series.astype(str).str.strip().str.lower()
        return normalized.map({"yes": 1, "no": 0, "true": 1, "false": 0, "1": 1, "0": 0})

    def _mode_label(self) -> str:
        return self.mode_config.name

    def load_data(self) -> pd.DataFrame:
        self.logger.info("STEP 1: Loading data from %s", self.data_path)
        df = pd.read_csv(self.data_path)
        self.logger.info("Dataset shape: %s", df.shape)
        self.logger.info("Initial columns: %s", list(df.columns))
        self.logger.info("Target distribution before cleaning: %s", df[TARGET_COLUMN].value_counts(dropna=False).to_dict())
        return df

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        self.logger.info("STEP 1: Cleaning data and normalizing values")
        df = self._normalize_column_names(df)

        if TARGET_COLUMN not in df.columns:
            target_found = next((col for col in TARGET_ALIASES if col in df.columns), None)
            if target_found is None:
                raise ValueError(f"Target column not found. Expected one of: {[TARGET_COLUMN, *TARGET_ALIASES]}")
            df = df.rename(columns={target_found: TARGET_COLUMN})

        before = len(df)
        df = df.drop_duplicates().reset_index(drop=True)
        self.logger.info("Removed duplicates: %d", before - len(df))

        for col in df.columns:
            if col == TARGET_COLUMN:
                continue
            if df[col].dtype == "object":
                binary_candidate = self._to_binary_series(df[col])
                if binary_candidate.notna().any() and binary_candidate.notna().sum() >= max(10, int(0.8 * len(df))):
                    df[col] = binary_candidate

        df[TARGET_COLUMN] = self._coerce_target(df[TARGET_COLUMN])
        if df[TARGET_COLUMN].isna().any():
            raise ValueError("Target column could not be normalized to binary labels")

        for col in df.select_dtypes(include=[np.number]).columns:
            if df[col].isna().any():
                df[col] = df[col].fillna(df[col].median())

        for col in df.select_dtypes(include=["object"]).columns:
            if df[col].isna().any():
                mode_val = df[col].mode(dropna=True)
                if not mode_val.empty:
                    df[col] = df[col].fillna(mode_val.iloc[0])

        self.logger.info("Missing values after cleaning: %d", int(df.isna().sum().sum()))
        return df

    def handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        self.logger.info("STEP 2: Outlier diagnostics and winsorization")
        df = df.copy()

        numeric_cols = [
            col
            for col in df.select_dtypes(include=[np.number]).columns
            if col != TARGET_COLUMN and df[col].nunique(dropna=False) > 2 and col not in ID_COLUMNS
        ]

        if numeric_cols:
            preview_cols = numeric_cols[:12]
            plot_df = df[preview_cols].melt(var_name="feature", value_name="value")
            plt.figure(figsize=(16, 7))
            sns.boxplot(data=plot_df, x="feature", y="value")
            plt.xticks(rotation=70)
            plt.tight_layout()
            plt.savefig(self.artifacts.plots_dir / "boxplots_before_winsorization.png", dpi=180)
            plt.close()

        iqr_rows: list[dict[str, Any]] = []
        for col in numeric_cols:
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            outlier_count = int(((df[col] < lower) | (df[col] > upper)).sum())
            iqr_rows.append(
                {
                    "feature": col,
                    "q1": float(q1),
                    "q3": float(q3),
                    "iqr": float(iqr),
                    "lower_bound": float(lower),
                    "upper_bound": float(upper),
                    "outliers_iqr": outlier_count,
                }
            )
            p01 = df[col].quantile(0.01)
            p99 = df[col].quantile(0.99)
            df[col] = df[col].clip(lower=p01, upper=p99)

        pd.DataFrame(iqr_rows).sort_values("outliers_iqr", ascending=False).to_csv(
            self.artifacts.plots_dir / "iqr_outlier_summary.csv", index=False
        )
        return df

    def feature_engineering(self, df: pd.DataFrame) -> pd.DataFrame:
        self.logger.info("STEP 3: Feature engineering")
        df = df.copy()

        tenure_col = "tenure_in_months"
        monthly_col = "monthly_charge"
        revenue_col = "total_revenue"
        satisfaction_col = "satisfaction_score"

        if tenure_col in df.columns:
            bins = [-1, 6, 12, 24, 48, np.inf]
            labels = ["0_6", "7_12", "13_24", "25_48", "49_plus"]
            df["tenure_group"] = pd.cut(df[tenure_col], bins=bins, labels=labels)

        if revenue_col in df.columns and tenure_col in df.columns:
            df["revenue_per_month"] = self._safe_divide(df[revenue_col], df[tenure_col])

        if monthly_col in df.columns and tenure_col in df.columns:
            df["avg_monthly_value"] = self._safe_divide(df[monthly_col], df[tenure_col])

        service_active = []
        for col in SERVICE_COLUMNS:
            if col not in df.columns:
                continue
            if df[col].dtype == "object":
                active = (
                    df[col]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    .isin({"yes", "1", "true", "dsl", "fiber optic", "cable"})
                    .astype(int)
                )
            else:
                active = (df[col].fillna(0).astype(float) > 0).astype(int)
            service_active.append(active)

        if service_active:
            service_df = pd.concat(service_active, axis=1)
            df["service_count"] = service_df.sum(axis=1)

        if satisfaction_col in df.columns and tenure_col in df.columns:
            df["satisfaction_tenure_interaction"] = df[satisfaction_col] * np.log1p(df[tenure_col].clip(lower=0))

        if monthly_col in df.columns and satisfaction_col in df.columns:
            df["monthly_charge_satisfaction_interaction"] = df[monthly_col] * df[satisfaction_col]

        if revenue_col in df.columns and monthly_col in df.columns:
            df["revenue_charge_ratio"] = self._safe_divide(df[revenue_col], df[monthly_col])

        return df

    def build_preprocessor(self, X: pd.DataFrame) -> ColumnTransformer:
        self.logger.info("STEP 4: Building preprocessing pipeline")
        numeric_features = X.select_dtypes(include=[np.number]).columns.tolist()
        categorical_features = X.select_dtypes(exclude=[np.number]).columns.tolist()

        numeric_transformer = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]
        )

        categorical_transformer = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=True)),
            ]
        )

        self.preprocessor = ColumnTransformer(
            transformers=[
                ("num", numeric_transformer, numeric_features),
                ("cat", categorical_transformer, categorical_features),
            ]
        )
        return self.preprocessor

    def _mode_params(self) -> dict[str, Any]:
        config = self.mode_config
        return {
            "xgb": {
                "n_iter": config.xgb_n_iter,
                "cv": config.xgb_cv,
                "estimators_low": config.xgb_estimators_low,
                "estimators_high": config.xgb_estimators_high,
            },
            "rf": {
                "n_iter": config.rf_n_iter,
                "cv": config.rf_cv,
                "estimators_low": config.rf_estimators_low,
                "estimators_high": config.rf_estimators_high,
            },
            "lgbm": {
                "n_iter": config.lgbm_n_iter,
                "cv": config.lgbm_cv,
                "estimators_low": config.xgb_estimators_low,
                "estimators_high": config.xgb_estimators_high,
            },
        }

    @staticmethod
    def _probabilities(model: Pipeline, X: pd.DataFrame) -> np.ndarray:
        if hasattr(model, "predict_proba"):
            return model.predict_proba(X)[:, 1]
        if hasattr(model, "decision_function"):
            decision = model.decision_function(X)
            return 1 / (1 + np.exp(-decision))
        return model.predict(X)

    def evaluate_model(self, model: Pipeline, X_test: pd.DataFrame, y_test: pd.Series) -> dict[str, Any]:
        y_pred = model.predict(X_test)
        y_prob = self._probabilities(model, X_test)

        return {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "roc_auc": float(roc_auc_score(y_test, y_prob)),
            "precision": float(precision_score(y_test, y_pred, zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, zero_division=0)),
            "f1": float(f1_score(y_test, y_pred, zero_division=0)),
            "classification_report": classification_report(y_test, y_pred, zero_division=0),
            "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        }

    def _fit_search(
        self,
        pipeline: Pipeline,
        param_distributions: dict[str, Any],
        n_iter: int,
        cv: int,
        X_train: pd.DataFrame,
        y_train: pd.Series,
    ) -> Pipeline:
        search = RandomizedSearchCV(
            pipeline,
            param_distributions=param_distributions,
            n_iter=n_iter,
            cv=cv,
            scoring="roc_auc",
            n_jobs=-1,
            random_state=RANDOM_STATE,
            verbose=0,
            refit=True,
        )
        search.fit(X_train, y_train)
        self.logger.info("Best params: %s", search.best_params_)
        return search.best_estimator_

    def train_models(self, X_train: pd.DataFrame, y_train: pd.Series, imbalance_ratio: float) -> dict[str, Pipeline]:
        self.logger.info("STEP 7-10: Training and tuning models in %s mode", self._mode_label())
        if self.preprocessor is None:
            raise RuntimeError("Preprocessor has not been built")

        params = self._mode_params()
        models: dict[str, Pipeline] = {}

        if HAS_XGBOOST:
            scale_pos_weight = max(1.0, float(imbalance_ratio))
            xgb = XGBClassifier(
                objective="binary:logistic",
                eval_metric="auc",
                random_state=RANDOM_STATE,
                n_jobs=-1,
                tree_method="hist",
                scale_pos_weight=scale_pos_weight,
            )
            xgb_pipe = Pipeline(steps=[("preprocessor", self.preprocessor), ("model", xgb)])
            xgb_params = {
                "model__n_estimators": randint(params["xgb"]["estimators_low"], params["xgb"]["estimators_high"] + 1),
                "model__max_depth": randint(3, 10),
                "model__learning_rate": uniform(0.01, 0.29),
                "model__subsample": uniform(0.65, 0.35),
                "model__colsample_bytree": uniform(0.65, 0.35),
                "model__min_child_weight": randint(1, 8),
                "model__gamma": uniform(0.0, 1.0),
            }
            models["xgboost"] = self._fit_search(
                xgb_pipe,
                xgb_params,
                params["xgb"]["n_iter"],
                params["xgb"]["cv"],
                X_train,
                y_train,
            )

        rf = RandomForestClassifier(
            random_state=RANDOM_STATE,
            n_jobs=-1,
            class_weight="balanced",
        )
        rf_pipe = Pipeline(steps=[("preprocessor", self.preprocessor), ("model", rf)])
        rf_params = {
            "model__n_estimators": randint(params["rf"]["estimators_low"], params["rf"]["estimators_high"] + 1),
            "model__max_depth": randint(4, 25),
            "model__min_samples_split": randint(2, 15),
            "model__min_samples_leaf": randint(1, 8),
            "model__max_features": ["sqrt", "log2", None],
        }
        models["random_forest"] = self._fit_search(
            rf_pipe,
            rf_params,
            params["rf"]["n_iter"],
            params["rf"]["cv"],
            X_train,
            y_train,
        )

        lr = LogisticRegression(max_iter=5000, class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1)
        lr_pipe = Pipeline(steps=[("preprocessor", self.preprocessor), ("model", lr)])
        lr_pipe.fit(X_train, y_train)
        models["logistic_regression"] = lr_pipe

        if HAS_LIGHTGBM:
            lgbm = LGBMClassifier(
                objective="binary",
                random_state=RANDOM_STATE,
                n_jobs=-1,
                class_weight="balanced",
            )
            lgbm_pipe = Pipeline(steps=[("preprocessor", self.preprocessor), ("model", lgbm)])
            lgbm_params = {
                "model__n_estimators": randint(params["lgbm"]["estimators_low"], params["lgbm"]["estimators_high"] + 1),
                "model__max_depth": randint(3, 12),
                "model__learning_rate": uniform(0.01, 0.25),
                "model__subsample": uniform(0.65, 0.35),
                "model__colsample_bytree": uniform(0.65, 0.35),
                "model__num_leaves": randint(15, 63),
            }
            models["lightgbm"] = self._fit_search(
                lgbm_pipe,
                lgbm_params,
                params["lgbm"]["n_iter"],
                params["lgbm"]["cv"],
                X_train,
                y_train,
            )

        return models

    def maybe_train_dl_baseline(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series,
    ) -> dict[str, Any] | None:
        if not self.mode_config.enable_dl:
            self.logger.info("STEP 16: Deep learning baseline disabled in FAST mode")
            return None
        if not HAS_TENSORFLOW or self.preprocessor is None:
            self.logger.info("STEP 16: TensorFlow unavailable; skipping deep learning baseline")
            return None

        self.logger.info("STEP 16: Training simple neural network baseline")
        dense_preprocessor = clone(self.preprocessor)
        X_train_t = dense_preprocessor.fit_transform(X_train)
        X_test_t = dense_preprocessor.transform(X_test)

        if hasattr(X_train_t, "toarray"):
            X_train_t = X_train_t.toarray()
            X_test_t = X_test_t.toarray()

        model = Sequential(
            [
                Dense(128, activation="relu", input_shape=(X_train_t.shape[1],)),
                Dropout(0.3),
                Dense(64, activation="relu"),
                Dropout(0.2),
                Dense(1, activation="sigmoid"),
            ]
        )
        model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy", tf.keras.metrics.AUC(name="auc")])
        model.fit(X_train_t, y_train.values, epochs=12, batch_size=64, validation_split=0.2, verbose=0)

        y_prob = model.predict(X_test_t, verbose=0).ravel()
        y_pred = (y_prob >= 0.5).astype(int)

        return {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "roc_auc": float(roc_auc_score(y_test, y_prob)),
            "precision": float(precision_score(y_test, y_pred, zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, zero_division=0)),
            "f1": float(f1_score(y_test, y_pred, zero_division=0)),
            "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        }

    def save_artifacts(self) -> None:
        if self.best_pipeline is None:
            raise RuntimeError("Best pipeline is not available")

        self.logger.info("STEP 13: Saving artifacts")
        joblib.dump(self.best_pipeline, self.artifacts.model_path)

        preprocessor = self.best_pipeline.named_steps["preprocessor"]
        num_transformer = preprocessor.named_transformers_["num"]
        cat_transformer = preprocessor.named_transformers_["cat"]
        scaler = num_transformer.named_steps["scaler"]
        encoder = cat_transformer.named_steps["encoder"]

        joblib.dump(scaler, self.artifacts.scaler_path)
        joblib.dump(encoder, self.artifacts.encoder_path)

    def save_feature_importance_plot(self) -> None:
        if self.best_pipeline is None:
            return
        model = self.best_pipeline.named_steps["model"]
        preprocessor = self.best_pipeline.named_steps["preprocessor"]
        if not hasattr(model, "feature_importances_"):
            return

        importances = model.feature_importances_
        feature_names = preprocessor.get_feature_names_out()
        fi = pd.DataFrame({"feature": feature_names, "importance": importances}).sort_values("importance", ascending=False)
        fi.to_csv(self.artifacts.plots_dir / "feature_importance_full.csv", index=False)

        plt.figure(figsize=(12, 8))
        sns.barplot(data=fi.head(25), x="importance", y="feature")
        plt.title("Top Feature Importances")
        plt.tight_layout()
        plt.savefig(self.artifacts.plots_dir / "feature_importance.png", dpi=180)
        plt.close()

    def save_shap_summary(self, X_sample: pd.DataFrame) -> None:
        if not self.mode_config.enable_shap:
            self.logger.info("STEP 16: SHAP disabled in FAST mode")
            return
        if not HAS_SHAP or self.best_pipeline is None:
            self.logger.info("STEP 16: SHAP unavailable; skipping explainability")
            return

        self.logger.info("STEP 16: Generating SHAP summary plot")
        model = self.best_pipeline.named_steps["model"]
        preprocessor = self.best_pipeline.named_steps["preprocessor"]

        X_t = preprocessor.transform(X_sample)
        if hasattr(X_t, "toarray"):
            X_t = X_t.toarray()

        X_t = X_t[:300]
        feature_names = preprocessor.get_feature_names_out()

        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_t)

        plt.figure(figsize=(12, 8))
        shap.summary_plot(shap_values, X_t, feature_names=feature_names, show=False, max_display=20)
        plt.tight_layout()
        plt.savefig(self.artifacts.plots_dir / "shap_summary.png", dpi=180)
        plt.close()

    def build_run_report(
        self,
        dataset_shape: tuple[int, int],
        numerical_features: list[str],
        categorical_features: list[str],
        comparison_df: pd.DataFrame,
        best_metrics: dict[str, Any],
        dl_metrics: dict[str, Any] | None,
        class_distribution: dict[int, int],
    ) -> None:
        self.logger.info("STEP 18: Writing markdown report to %s", self.artifacts.report_path)

        lines: list[str] = []
        lines.append("# data")
        lines.append("")
        lines.append("## Executed Command")
        lines.append("")
        lines.append("```powershell")
        lines.append("f:/project/churn-prediction/.venv/Scripts/python.exe data.py")
        lines.append("```")
        lines.append("")
        lines.append("## Execution Mode")
        lines.append("")
        lines.append(f"- FAST_MODE: {FAST_MODE}")
        lines.append(f"- Mode: {self._mode_label()}")
        lines.append("")
        lines.append("## Dataset Summary")
        lines.append("")
        lines.append(f"- Shape: {dataset_shape}")
        lines.append(f"- Numerical feature count: {len(numerical_features)}")
        lines.append(f"- Categorical feature count: {len(categorical_features)}")
        lines.append(f"- Target distribution: {class_distribution}")
        lines.append("")
        lines.append("## Model Comparison")
        lines.append("")
        lines.append(comparison_df.to_markdown(index=False))
        lines.append("")
        lines.append("## Best Model")
        lines.append("")
        lines.append(f"- Model: {self.best_model_name}")
        lines.append(f"- Accuracy: {best_metrics['accuracy']:.6f}")
        lines.append(f"- ROC-AUC: {best_metrics['roc_auc']:.6f}")
        lines.append(f"- Precision: {best_metrics['precision']:.6f}")
        lines.append(f"- Recall: {best_metrics['recall']:.6f}")
        lines.append(f"- F1-score: {best_metrics['f1']:.6f}")
        lines.append("")
        lines.append("### Confusion Matrix")
        lines.append("")
        lines.append("```text")
        lines.append(str(best_metrics["confusion_matrix"]))
        lines.append("```")
        lines.append("")
        lines.append("### Classification Report")
        lines.append("")
        lines.append("```text")
        lines.append(best_metrics["classification_report"])
        lines.append("```")

        if dl_metrics is not None:
            lines.append("")
            lines.append("## Deep Learning Baseline")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(dl_metrics, indent=2))
            lines.append("```")

        lines.append("")
        lines.append("## Saved Artifacts")
        lines.append("")
        lines.append(f"- {self.artifacts.model_path.as_posix()}")
        lines.append(f"- {self.artifacts.scaler_path.as_posix()}")
        lines.append(f"- {self.artifacts.encoder_path.as_posix()}")
        lines.append(f"- {self.artifacts.metrics_path.as_posix()}")
        lines.append(f"- {self.artifacts.comparison_path.as_posix()}")
        lines.append(f"- {self.artifacts.plots_dir.as_posix()}/feature_importance.png")
        lines.append(f"- {self.artifacts.plots_dir.as_posix()}/shap_summary.png")
        lines.append(f"- {self.artifacts.plots_dir.as_posix()}/boxplots_before_winsorization.png")

        self.artifacts.report_path.write_text("\n".join(lines), encoding="utf-8")

    def _prepare_inference_frame(self, input_dict: dict[str, Any], pipeline: Pipeline) -> pd.DataFrame:
        raw = pd.DataFrame([input_dict])
        raw = self._normalize_column_names(raw)
        raw = self.clean_data(raw)
        raw = self.handle_outliers(raw)
        raw = self.feature_engineering(raw)
        raw = raw.drop(columns=[TARGET_COLUMN], errors="ignore")
        raw = raw.drop(columns=[col for col in LEAKAGE_COLUMNS if col in raw.columns], errors="ignore")
        raw = raw.drop(columns=[col for col in ID_COLUMNS if col in raw.columns], errors="ignore")

        expected_cols = list(pipeline.named_steps["preprocessor"].feature_names_in_)
        raw = raw.reindex(columns=expected_cols)
        return raw

    def run(self) -> dict[str, Any]:
        self.logger.info("========================================")
        self.logger.info("Churn training pipeline starting")
        self.logger.info("Mode: %s", self._mode_label())
        self.logger.info("========================================")

        df = self.load_data()
        df = self.clean_data(df)
        df = self.handle_outliers(df)
        df = self.feature_engineering(df)

        if TARGET_COLUMN not in df.columns:
            raise ValueError(f"Target column '{TARGET_COLUMN}' not found after preprocessing")

        df = df[df[TARGET_COLUMN].isin([0, 1])].copy()

        drop_cols = [TARGET_COLUMN]
        drop_cols.extend([col for col in LEAKAGE_COLUMNS if col in df.columns])
        drop_cols.extend([col for col in ID_COLUMNS if col in df.columns])

        X = df.drop(columns=drop_cols, errors="ignore")
        y = df[TARGET_COLUMN].astype(int)
        self.input_columns = X.columns.tolist()
        self.target_distribution = {int(k): int(v) for k, v in y.value_counts().to_dict().items()}

        numerical_features = X.select_dtypes(include=[np.number]).columns.tolist()
        categorical_features = X.select_dtypes(exclude=[np.number]).columns.tolist()
        self.build_preprocessor(X)

        self.logger.info("STEP 5: Stratified train/test split")
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.2,
            random_state=RANDOM_STATE,
            stratify=y,
        )

        class_counts = y_train.value_counts()
        imbalance_ratio = float(class_counts.max() / max(class_counts.min(), 1))
        self.logger.info("STEP 6: Class imbalance ratio = %.4f", imbalance_ratio)

        self.logger.info("STEP 7-10: Model training and hyperparameter tuning")
        trained_models = self.train_models(X_train, y_train, imbalance_ratio)

        self.logger.info("STEP 11-12: Evaluating and selecting best model")
        evaluation_rows: list[dict[str, Any]] = []
        metrics_by_model: dict[str, dict[str, Any]] = {}

        for model_name, model in trained_models.items():
            metrics = self.evaluate_model(model, X_test, y_test)
            metrics_by_model[model_name] = metrics
            evaluation_rows.append(
                {
                    "model": model_name,
                    "accuracy": metrics["accuracy"],
                    "roc_auc": metrics["roc_auc"],
                    "precision": metrics["precision"],
                    "recall": metrics["recall"],
                    "f1": metrics["f1"],
                }
            )

        comparison_df = pd.DataFrame(evaluation_rows).sort_values(by=["roc_auc", "accuracy", "f1"], ascending=False).reset_index(drop=True)
        self.best_model_name = str(comparison_df.iloc[0]["model"])
        self.best_pipeline = trained_models[self.best_model_name]
        best_metrics = metrics_by_model[self.best_model_name]

        self.save_artifacts()

        output_payload = {
            "fast_mode": FAST_MODE,
            "mode": self._mode_label(),
            "best_model": self.best_model_name,
            "best_metrics": best_metrics,
            "model_comparison": comparison_df.to_dict(orient="records"),
            "dataset_shape": list(df.shape),
            "class_distribution": self.target_distribution,
            "input_columns": self.input_columns,
            "random_state": RANDOM_STATE,
        }

        self.artifacts.metrics_path.write_text(json.dumps(output_payload, indent=2), encoding="utf-8")
        comparison_df.to_csv(self.artifacts.comparison_path, index=False)

        self.save_feature_importance_plot()
        if self.mode_config.enable_shap:
            sample_size = min(len(X_test), 300)
            self.save_shap_summary(X_test.sample(sample_size, random_state=RANDOM_STATE))

        dl_metrics = self.maybe_train_dl_baseline(X_train, y_train, X_test, y_test)
        if dl_metrics is not None:
            output_payload["deep_learning_baseline"] = dl_metrics

        self.build_run_report(
            dataset_shape=df.shape,
            numerical_features=numerical_features,
            categorical_features=categorical_features,
            comparison_df=comparison_df,
            best_metrics=best_metrics,
            dl_metrics=dl_metrics,
            class_distribution=self.target_distribution,
        )

        self.logger.info("Training complete")
        self.logger.info("Best model: %s", self.best_model_name)
        self.logger.info("Accuracy: %.6f | ROC-AUC: %.6f", best_metrics["accuracy"], best_metrics["roc_auc"])

        return output_payload


def load_model_for_inference(model_path: str | Path = "artifacts/churn_model.pkl") -> Pipeline:
    return joblib.load(model_path)


def predict_user(input_dict: dict[str, Any], model_path: str | Path = "artifacts/churn_model.pkl") -> dict[str, Any]:
    model = load_model_for_inference(model_path)
    if not isinstance(model, Pipeline):
        raise TypeError("Loaded artifact is not a sklearn Pipeline")

    pipeline_wrapper = ChurnPipeline(Path("."), Path("artifacts"), fast_mode=FAST_MODE)
    prepared_input = pipeline_wrapper._prepare_inference_frame(input_dict, model)

    prediction = int(model.predict(prepared_input)[0])
    probability = float(model.predict_proba(prepared_input)[0, 1]) if hasattr(model, "predict_proba") else float(prediction)

    return {
        "prediction": prediction,
        "prediction_label": "Yes" if prediction == 1 else "No",
        "churn_probability": round(probability, 6),
        "model_path": str(model_path),
    }


def main() -> None:
    project_root = Path(__file__).resolve().parent
    data_path = project_root / "churn-ai-platform" / "data" / "processed" / "telco_churn_cleaned.csv"
    artifacts_path = project_root / "artifacts"

    if not data_path.exists():
        raise FileNotFoundError(f"Dataset not found at: {data_path}")

    np.random.seed(RANDOM_STATE)
    os.environ.setdefault("PYTHONHASHSEED", str(RANDOM_STATE))

    trainer = ChurnPipeline(data_path=data_path, artifacts_dir=artifacts_path, fast_mode=FAST_MODE)
    result = trainer.run()
    print(json.dumps({"best_model": result["best_model"], "best_metrics": result["best_metrics"]}, indent=2))


if __name__ == "__main__":
    main()
