from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
import math
import os
import time
from typing import Any

import pandas as pd
from mysql.connector.errors import IntegrityError

from config.sectors import get_risk_tier, get_sector_profile
from models.db import fetch_customer_core_features, insert_prediction, upsert_model_metadata
from models.model_loader import ModelLoader
from schemas.explainability import ExplainabilitySummary
from services.explainability_service import ExplainabilityService
from services.recommendation_service import recommendation_service
from services.dataset_service import dataset_service
from utils.paths import PLATFORM_ROOT


class PredictionService:
    EXPECTED_FEATURES = ["age", "tenure", "monthly_charges"]

    def __init__(self) -> None:
        self._logger = logging.getLogger("churn_app")
        self._artifacts = ModelLoader.load()
        self._inference_count = 0
        self._last_prediction_at: datetime | None = None
        self._explainer = None
        self._explainer_initialized = False
        self._shap_plot_dir = PLATFORM_ROOT / "logs" / "shap"
        self._save_shap_plots = os.getenv("SAVE_SHAP_PLOTS", "false").lower() == "true"
        self._default_explain = os.getenv("ENABLE_EXPLAINABILITY", "false").lower() == "true"
        self._feature_names = getattr(self._artifacts.model, "feature_names_in_", None)
        self._feature_name_set = set(self._feature_names.tolist()) if self._feature_names is not None else set()
        self._feature_store = self._load_feature_store()
        self._default_feature_row = self._build_default_feature_row()
        self._uses_pipeline = hasattr(self._artifacts.model, "named_steps")
        self._explainability_service = ExplainabilityService(self._artifacts)
        self._population_cache_ttl_seconds = max(30, int(os.getenv("POPULATION_SNAPSHOT_TTL_SECONDS", "300")))
        self._population_cache: dict[str, Any] | None = None

        self._positive_class_index: int | None = None
        classes = getattr(self._artifacts.model, "classes_", None)
        if classes is not None and 1 in classes:
            self._positive_class_index = list(classes).index(1)

        # VALIDATION: Prevent double preprocessing
        if self._uses_pipeline and self._artifacts.preprocessor is not None:
            self._logger.warning("DOUBLE_PREPROCESSING_RISK | Pipeline has internal preprocessing AND standalone preprocessor exists")
            self._logger.warning("RESOLUTION | Using pipeline internal preprocessing; standalone preprocessor artifact is IGNORED")
            # Don't use standalone preprocessor if pipeline is detected
            self._artifacts.preprocessor = None
        
        if self._uses_pipeline:
            self._logger.info("model_architecture | type=Pipeline | internal_preprocessing=true")
        elif self._artifacts.preprocessor is not None:
            self._logger.info("model_architecture | type=Standalone | external_preprocessor=true")
        else:
            self._logger.info("model_architecture | type=Standalone | external_preprocessor=false")

    def _load_feature_store(self) -> pd.DataFrame | None:
        try:
            return dataset_service.frame.copy()
        except Exception as exc:
            self._logger.warning("Failed to load dataset feature store: %s", exc)
            return None

    def _build_default_feature_row(self) -> dict[str, Any]:
        if self._feature_store is None or self._feature_names is None:
            return {}

        defaults: dict[str, Any] = {}
        for column in self._feature_names:
            if column not in self._feature_store.columns:
                continue

            series = self._feature_store[column]
            if pd.api.types.is_numeric_dtype(series):
                defaults[column] = float(series.median())
            else:
                mode = series.mode(dropna=True)
                defaults[column] = mode.iloc[0] if not mode.empty else "Unknown"

        return defaults

    def validate_required_features(self, features: dict[str, Any]) -> list[str]:
        missing: list[str] = []
        for column in self.EXPECTED_FEATURES:
            value = features.get(column)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                missing.append(column)
        return missing

    def _build_feature_frame(self, features: dict[str, Any], sector: str = "telecom") -> tuple[pd.DataFrame, str]:
        raw_features = dict(features)
        customer_id = str(raw_features.get("customer_id", "")).strip()
        
        # Resolve sector aliases (e.g. mrr -> monthly_charges, account_age_months -> tenure)
        profile = get_sector_profile(sector)
        for canon, aliases in profile.get("field_aliases", {}).items():
            if canon not in raw_features or raw_features[canon] in (None, ""):
                for alias in aliases:
                    if alias in raw_features and raw_features[alias] not in (None, ""):
                        raw_features[canon] = raw_features[alias]
                        break

        # Log input data
        self._logger.debug("build_feature_frame_input | customer_id=%s | sector=%s | input_keys=%s", customer_id, sector, list(raw_features.keys()))
        
        # Fetch customer features from database
        customer_features = dataset_service.get_customer_features(customer_id) if customer_id else None
        if customer_features is None and customer_id:
            try:
                customer_features = fetch_customer_core_features(customer_id)
            except Exception:
                customer_features = None
        if customer_id and customer_features is None:
            self._logger.info("customer_lookup_miss | customer_id=%s | mode=manual_fallback", customer_id)
        
        # STEP 1: Populate EXPECTED_FEATURES from DB or raw input
        # Ensure core features are present before building frame
        if customer_features is not None:
            # Map DB core features to model feature names while preserving requested aliases.
            raw_features.setdefault("age", customer_features["age"])
            raw_features.setdefault("tenure", customer_features["tenure"])
            raw_features.setdefault("monthly_charges", customer_features["monthly_charges"])
            raw_features.setdefault("tenure_in_months", customer_features["tenure"])
            raw_features.setdefault("monthly_charge", customer_features["monthly_charges"])

        # STEP 2: Validate EXPECTED_FEATURES are present EARLY
        missing_columns = [column for column in self.EXPECTED_FEATURES if column not in raw_features]
        imputed_columns: list[str] = []
        for column in list(missing_columns):
            default_value = self._default_feature_row.get(column)
            if default_value is not None:
                raw_features[column] = default_value
                imputed_columns.append(column)

        if imputed_columns:
            self._logger.info("manual_feature_imputation | columns=%s", imputed_columns)

        missing_columns = [column for column in self.EXPECTED_FEATURES if column not in raw_features]
        if missing_columns:
            if customer_id and customer_features is None:
                raise ValueError(
                    f"Customer '{customer_id}' not found and manual input is missing required features {missing_columns}"
                )
            raise ValueError(f"Feature mismatch: missing required features {missing_columns}")
        
        # STEP 3: Validate EXPECTED_FEATURES have no null values EARLY
        core_features_values = {feat: raw_features.get(feat) for feat in self.EXPECTED_FEATURES}
        if any(v is None for v in core_features_values.values()):
            raise ValueError(f"Missing feature values in {self.EXPECTED_FEATURES}: {core_features_values}")
        
        self._logger.debug("build_feature_frame_core_features | age=%s | tenure=%s | monthly_charges=%s",
                          core_features_values["age"], core_features_values["tenure"], core_features_values["monthly_charges"])
        
        # STEP 4: Select feature source
        if customer_id and self._feature_store is not None and customer_id in self._feature_store.index:
            row = self._feature_store.loc[customer_id].to_dict()
            source = "feature_store"
        elif customer_features is not None:
            row = dict(self._default_feature_row)
            source = "database"
        else:
            row = dict(self._default_feature_row)
            source = "defaults"
        
        # STEP 5: Merge raw features into row
        for key, value in raw_features.items():
            key_name = str(key)
            if not self._feature_name_set or key_name in self._feature_name_set:
                row[key_name] = value
        
        frame = pd.DataFrame([row])
        
        # STEP 6: Enforce feature column order - use model's feature_names_in_ if available
        if self._feature_names is not None:
            for column in self._feature_names:
                if column not in frame.columns:
                    frame[column] = self._default_feature_row.get(column, 0)
            # ENFORCE: Select only model's expected columns in the right order
            frame = frame[list(self._feature_names)]
            self._logger.debug("build_feature_frame_model_features | enforced_order=%s | shape=%s", list(self._feature_names), frame.shape)
        else:
            # No model feature spec - enforce EXPECTED_FEATURES ordering as minimum
            # Reorder frame to have EXPECTED_FEATURES first
            expected_cols = [col for col in self.EXPECTED_FEATURES if col in frame.columns]
            other_cols = [col for col in frame.columns if col not in self.EXPECTED_FEATURES]
            enforced_order = expected_cols + other_cols
            frame = frame[enforced_order]
            self._logger.debug("build_feature_frame_enforced_order | expected_first=%s | shape=%s", enforced_order[:len(self.EXPECTED_FEATURES)], frame.shape)
        
        # STEP 7: Final validation using canonical expected feature values.
        # Do not index frame by EXPECTED_FEATURES here because model feature_names_in_
        # can use aliases (for example tenure_in_months/monthly_charge).
        expected_values = [raw_features.get(column) for column in self.EXPECTED_FEATURES]
        if all(value is None for value in expected_values):
            raise ValueError("Invalid input: all EXPECTED_FEATURES are null")
        
        self._logger.debug("build_feature_frame_output | source=%s | shape=%s | columns=%s", source, frame.shape, list(frame.columns))
        
        return frame, source

    def _predict_probability(self, frame: pd.DataFrame, return_proba: bool) -> float:
        model = self._artifacts.model
        
        # Log input frame details
        self._logger.debug("predict_probability_input | shape=%s | dtypes=%s | sample=%s",
            frame.shape,
            {column: str(dtype) for column, dtype in frame.dtypes.items()},
            frame.iloc[0].to_dict() if len(frame) > 0 else {}
        )

        # CRITICAL: Choose preprocessing path based on model type
        if self._uses_pipeline:
            # Pipeline model: preprocessing handled internally
            self._logger.debug("predict_probability_mode | type=pipeline_internal | no_external_preprocessing")
            processed_frame = frame
            preprocessing_applied = "pipeline_internal"
        else:
            # Non-pipeline model: use standalone preprocessor if available
            if self._artifacts.preprocessor is not None:
                self._logger.debug("predict_probability_mode | type=standalone_preprocessor")
                processed_frame = self._artifacts.preprocessor.transform(frame)
                self._logger.debug("predict_probability_transformed | output_type=%s | output_shape=%s",
                    type(processed_frame).__name__,
                    getattr(processed_frame, "shape", "unknown")
                )
                preprocessing_applied = "standalone_preprocessor"
            else:
                # No preprocessing
                self._logger.debug("predict_probability_mode | type=raw_features | no_preprocessing")
                processed_frame = frame
                preprocessing_applied = "none"

        # Get predictions
        if return_proba and hasattr(model, "predict_proba"):
            self._logger.debug("predict_probability_method | using=predict_proba | preprocessing=%s", preprocessing_applied)
            proba = model.predict_proba(processed_frame)[0]
            self._logger.debug("predict_probability_proba | raw_probabilities=%s", proba)
            
            if self._positive_class_index is not None:
                result = float(proba[self._positive_class_index])
                self._logger.debug("predict_probability_result | class_index=%s | probability=%.6f", self._positive_class_index, result)
                return result
            
            result = float(max(proba))
            self._logger.debug("predict_probability_result | using=max_probability | probability=%.6f", result)
            return result

        # Fallback to predict() if predict_proba not available
        self._logger.debug("predict_probability_method | using=predict | preprocessing=%s", preprocessing_applied)
        raw_prediction = int(model.predict(processed_frame)[0])
        self._logger.debug("predict_probability_raw | prediction=%s", raw_prediction)
        result = 1.0 if raw_prediction == 1 else 0.0
        return result

    @property
    def model_loaded(self) -> bool:
        return self._artifacts.model is not None

    @property
    def model_path(self) -> str:
        return str(self._artifacts.model_path)

    @property
    def model_version(self) -> str:
        return self._artifacts.model_version

    @property
    def inference_count(self) -> int:
        return self._inference_count

    @property
    def last_prediction_at(self) -> str | None:
        if self._last_prediction_at is None:
            return None
        return self._last_prediction_at.isoformat()

    def _calibrate_probability(self, probability: float) -> float:
        # Temperature scaling and bias are configurable without retraining.
        temperature = float(os.getenv("PROB_CALIBRATION_TEMPERATURE", "1.0"))
        bias = float(os.getenv("PROB_CALIBRATION_BIAS", "0.0"))
        temperature = temperature if temperature > 0 else 1.0

        eps = 1e-6
        p = min(max(probability, eps), 1 - eps)
        logit = math.log(p / (1 - p))
        calibrated = 1.0 / (1.0 + math.exp(-((logit / temperature) + bias)))
        return float(min(max(calibrated, 0.0), 1.0))

    def _risk_level(self, calibrated_probability: float) -> str:
        return get_risk_tier(calibrated_probability)

    def _prepare_population_model_frame(self) -> tuple[pd.DataFrame, pd.Series]:
        frame = dataset_service.frame.copy()
        customer_ids = frame.index.astype(str)

        if self._feature_names is not None:
            columns = list(self._feature_names)
        else:
            columns = [column for column in self.EXPECTED_FEATURES if column in frame.columns]

        model_frame = frame.copy()
        for column in columns:
            if column not in model_frame.columns:
                model_frame[column] = self._default_feature_row.get(column, 0)

        return model_frame[columns], customer_ids

    def _predict_probabilities_batch(self, model_frame: pd.DataFrame) -> pd.Series:
        model = self._artifacts.model

        if self._uses_pipeline:
            processed = model_frame
        elif self._artifacts.preprocessor is not None:
            processed = self._artifacts.preprocessor.transform(model_frame)
        else:
            processed = model_frame

        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba(processed)
            if self._positive_class_index is not None:
                positive_idx = self._positive_class_index
            else:
                positive_idx = 1 if probabilities.shape[1] > 1 else 0
            return pd.Series(probabilities[:, positive_idx], index=model_frame.index, dtype="float64")

        predictions = model.predict(processed)
        return pd.Series(predictions, index=model_frame.index, dtype="float64")

    def _compute_population_snapshot(self) -> dict[str, Any]:
        model_frame, customer_ids = self._prepare_population_model_frame()
        raw_probabilities = self._predict_probabilities_batch(model_frame)
        calibrated_probabilities = raw_probabilities.apply(self._calibrate_probability)

        risk_distribution = {"low": 0, "medium": 0, "high": 0}
        risk_index: dict[str, dict[str, Any]] = {}
        predicted_churn = 0

        for customer_id, probability in calibrated_probabilities.items():
            risk_level = self._risk_level(float(probability))
            risk_key = risk_level.lower()
            risk_distribution[risk_key] += 1
            prediction = 1 if float(probability) >= 0.5 else 0
            predicted_churn += prediction

            cust_features = model_frame.loc[customer_id].to_dict() if customer_id in model_frame.index else {}
            driver = recommendation_service.identify_primary_driver([], cust_features, sector_id="telecom")
            _, recs = recommendation_service.generate_recommendations("telecom", float(probability), risk_level, [], cust_features)
            recommended_action = recs[0] if recs else "Review customer satisfaction."

            risk_index[str(customer_id)] = {
                "risk": risk_key,
                "risk_level": risk_level,
                "probability": float(probability),
                "prediction": prediction,
                "primary_driver": driver,
                "recommended_action": recommended_action,
            }

        total_customers = int(len(customer_ids))
        high_risk_count = int(risk_distribution["high"])

        churn_vs_nonchurn = {
            "churn": int(predicted_churn),
            "non_churn": int(total_customers - predicted_churn),
        }
        churn_label_series = dataset_service.frame.get("churn_label")
        if churn_label_series is not None:
            churn_label = churn_label_series.astype(str).str.lower().str.strip()
            churn_vs_nonchurn = {
                "churn": int((churn_label == "yes").sum()),
                "non_churn": int((churn_label != "yes").sum()),
            }

        snapshot = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_customers": total_customers,
            "total_predictions": total_customers,
            "risk_distribution": risk_distribution,
            "high_risk_count": high_risk_count,
            "high_risk_percentage": float((high_risk_count / total_customers) * 100) if total_customers else 0.0,
            "churn_vs_nonchurn": churn_vs_nonchurn,
            "risk_index": risk_index,
        }
        return snapshot

    def _population_snapshot(self, force_refresh: bool = False) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        if not force_refresh and self._population_cache is not None:
            expires_at = self._population_cache.get("expires_at")
            if isinstance(expires_at, datetime) and expires_at > now:
                return dict(self._population_cache["snapshot"])

        snapshot = self._compute_population_snapshot()
        self._population_cache = {
            "expires_at": now + timedelta(seconds=self._population_cache_ttl_seconds),
            "snapshot": snapshot,
        }
        return dict(snapshot)

    def population_summary(self, force_refresh: bool = False) -> dict[str, Any]:
        snapshot = self._population_snapshot(force_refresh=force_refresh)
        return {
            "generated_at": str(snapshot.get("generated_at") or ""),
            "total_customers": int(snapshot.get("total_customers") or 0),
            "total_predictions": int(snapshot.get("total_predictions") or 0),
            "risk_distribution": dict(snapshot.get("risk_distribution") or {"low": 0, "medium": 0, "high": 0}),
            "high_risk_count": int(snapshot.get("high_risk_count") or 0),
            "high_risk_percentage": float(snapshot.get("high_risk_percentage") or 0.0),
            "churn_vs_nonchurn": dict(snapshot.get("churn_vs_nonchurn") or {"churn": 0, "non_churn": 0}),
        }

    def population_risk_index(self, customer_ids: list[str] | None = None) -> dict[str, dict[str, Any]]:
        snapshot = self._population_snapshot(force_refresh=False)
        full_index = dict(snapshot.get("risk_index") or {})
        if customer_ids is None:
            return full_index
        requested = {str(customer_id).strip() for customer_id in customer_ids if str(customer_id).strip()}
        return {customer_id: value for customer_id, value in full_index.items() if customer_id in requested}

    def explain_prediction(self, features: dict[str, Any], top_n: int = 5) -> ExplainabilitySummary:
        return self._explainability_service.explain_prediction(features=features, top_n=top_n)

    def feature_importance(self, top_n: int = 10) -> ExplainabilitySummary:
        return self._explainability_service.global_feature_importance(top_n=top_n)

    def predict(
        self,
        features: dict[str, Any],
        return_proba: bool = True,
        explain: bool = False,
        sector: str = "telecom",
    ) -> tuple[int, float, str, float, list[dict[str, float | str]], float, str, ExplainabilitySummary | None, str, list[str]]:
        start_time = time.perf_counter()

        # Required production observability logs.
        self._logger.info("Prediction request received | sector=%s", sector)
        self._logger.info("Input features: %s", features)
        
        # STEP 1: Log input
        self._logger.info("predict_start | customer_id=%s | sector=%s | input_features=%s | return_proba=%s | explain=%s",
            features.get("customer_id", "NONE"), sector, list(features.keys()), return_proba, explain)
        
        # STEP 2: Build feature frame with alignment, fetch from DB, validate
        try:
            frame, feature_source = self._build_feature_frame(features, sector=sector)
        except ValueError as e:
            self._logger.error("Prediction failed", exc_info=True)
            self._logger.error("predict_error_feature_frame | error=%s", str(e))
            raise

        self._logger.debug("predict_features_prepared | source=%s | shape=%s | expected_features=%s",
            feature_source, frame.shape, self.EXPECTED_FEATURES)
        self._logger.info(
            "model_inputs | age=%s | tenure=%s | monthly_charges=%s",
            frame.iloc[0].get("age", None),
            frame.iloc[0].get("tenure", None),
            frame.iloc[0].get("monthly_charges", None),
        )

        # STEP 3: Get probability from model
        probability = self._predict_probability(frame, return_proba=return_proba)
        self._logger.debug("predict_probability_raw | value=%.6f", probability)

        # STEP 4: Calibrate probability
        calibrated_probability = self._calibrate_probability(probability)
        self._logger.debug("predict_probability_calibrated | raw=%.6f | calibrated=%.6f", probability, calibrated_probability)
        
        # STEP 5: Compute risk level and prediction
        risk_level = self._risk_level(calibrated_probability)
        prediction = 1 if calibrated_probability >= 0.5 else 0
        confidence_score = float(abs(calibrated_probability - 0.5) * 2.0)
        
        self._logger.debug("predict_risk_level | probability=%.6f | risk_level=%s | prediction=%s | confidence=%.6f",
            calibrated_probability, risk_level, prediction, confidence_score)

        # STEP 6: Generate explanations and retention recommendations
        explain_enabled = explain or self._default_explain
        explanation = self.explain_prediction(features, top_n=5) if explain_enabled else None
        top_features = [item.model_dump() for item in explanation.top_features] if explanation is not None and explanation.available else []

        primary_driver, recommendations = recommendation_service.generate_recommendations(
            sector_id=sector,
            probability=calibrated_probability,
            risk_level=risk_level,
            top_features=top_features,
            customer_features=features,
        )

        # STEP 7: Compute latency and finalize
        self._inference_count += 1
        self._last_prediction_at = datetime.now(timezone.utc)
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        
        self._logger.info("predict_complete | customer_id=%s | sector=%s | prediction=%s | probability=%.6f | risk=%s | driver=%s | latency_ms=%.2f",
            features.get("customer_id", "NONE"), sector, prediction, calibrated_probability, risk_level, primary_driver, latency_ms)
        self._logger.info("Prediction result: %s", prediction)
        
        return (
            prediction,
            calibrated_probability,
            risk_level,
            confidence_score,
            top_features,
            float(latency_ms),
            self.model_version,
            explanation,
            primary_driver,
            recommendations,
        )

    def register_model_metadata(self) -> None:
        upsert_model_metadata(
            model_name="churn_model",
            model_version=self.model_version,
            artifact_path=str(self._artifacts.model_path),
            artifact_sha256=self._artifacts.artifact_sha256,
            feature_version=os.getenv("FEATURE_VERSION", "v1"),
            notes=(
                f"preprocessor={self._artifacts.preprocessor_path}" if self._artifacts.preprocessor_path is not None else "preprocessor=none"
            ),
            is_active=True,
        )

    def save_prediction(
        self,
        customer_id: str,
        prediction: int,
        probability: float,
        risk_level: str,
        confidence_score: float = 0.0,
        latency_ms: float = 0.0,
        top_features: list[dict[str, float | str]] | None = None,
        input_features: dict[str, Any] | None = None,
        model_version: str | None = None,
    ) -> int:
        timestamp = datetime.now(timezone.utc).isoformat()
        try:
            return insert_prediction(
                customer_id=customer_id,
                prediction=prediction,
                probability=probability,
                risk_level=risk_level,
                timestamp=timestamp,
                confidence_score=confidence_score,
                latency_ms=latency_ms,
                top_features=top_features,
                input_features=input_features,
                model_version=model_version or self.model_version,
            )
        except IntegrityError as exc:
            message = str(exc)
            if "fk_predictions_customer" in message.lower() or "foreign key" in message.lower():
                raise ValueError(f"Customer '{customer_id}' not found") from exc
            return 1
        except Exception as exc:
            self._logger.warning("save_prediction skipped due to database unavailability: %s", exc)
            return 1
