# ML System Audit and Production Guide

## 1. Problem Statement

- The goal is to predict customer churn using real ML inference, not rule-based logic.
- The system should help teams identify customers at risk, explain why they are risky, and store every prediction for dashboard and analytics use.
- The backend must be the source of truth for predictions, history, and aggregates.

## 2. Audit Result

- The system already contains a real trained model artifact.
- The model is loaded with joblib.
- The deployed artifact is a real sklearn Pipeline with:
- predict()
- predict_proba()
- a preprocessing stage
- a tree-based XGBoost classifier inside the pipeline
- The preprocessing pipeline contains:
- SimpleImputer for missing values
- StandardScaler for numeric features
- OneHotEncoder for categorical features
- Live inference checks showed different inputs produce different probabilities.
- Example validation result:
- one input produced probability 0.9942
- another input produced probability 0.0048
- This confirms the system is not using a static UI simulation.

## 3. Dataset Description

- Main dataset: telco churn dataset stored in the processed data folder.
- Canonical dataset size is enforced in the backend dataset service.
- Dataset fields support customer profile and usage information.
- Important fields used by the model include:
- age
- tenure_in_months or tenure
- monthly_charge or monthly_charges
- contract
- many categorical service and profile fields
- The backend dataset service normalizes names and derives missing convenience fields such as email and contract_type.

## 4. Feature Engineering

- Feature engineering is done before training and also supported in runtime feature preparation.
- The training pipeline removes leakage columns before preprocessing.
- Numeric features are imputed and scaled.
- Categorical features are imputed and one-hot encoded.
- The runtime prediction service maps customer_id to stored customer features when available.
- The model input contract centers on:
- age
- tenure
- monthly_charges
- customer_id
- This allows both direct manual input and lookup-based prediction.

## 5. Model Used

- The training pipeline supports multiple real models.
- Available model families include:
- XGBoost
- Random Forest
- Logistic Regression
- LightGBM when installed
- The deployed production artifact is a trained sklearn Pipeline wrapping preprocessing plus the model.
- The current inspected artifact is an XGBClassifier inside a Pipeline.
- The model supports class probabilities through predict_proba.
- The backend uses probability thresholds to map risk into:
- Low
- Medium
- High

## 6. Training Process

- The training pipeline follows these steps:
- Load the dataset.
- Split features and target.
- Encode the churn label to binary values.
- Build preprocessing with imputation, scaling, and encoding.
- Split data into train and test sets using 80/20.
- Train candidate models using randomized search.
- Select the best model using ROC-AUC.
- Save the best pipeline artifact with joblib.
- Optional SHAP summary plots can be generated for tree-based models.

- The evaluation script also compares saved model artifacts on a holdout test set.
- Metrics include:
- accuracy
- ROC-AUC
- precision
- recall
- F1-score

## 7. Evaluation Metrics

- The evaluation pipeline computes standard classification metrics.
- Metrics are saved as CSV and JSON artifacts.
- The report also stores confusion matrices.
- This is the correct production standard because churn is an imbalanced classification problem.
- The backend uses a probability threshold instead of only class labels.

## 8. Prediction API Design

- Endpoint: POST /predict
- Input fields:
- age
- tenure
- monthly_charges
- contract_type
- customer_id can also be supplied for feature lookup

- Pipeline:
- Receive request.
- Validate input.
- Build feature frame.
- Apply preprocessing from the saved pipeline.
- Call model.predict_proba().
- Derive prediction and risk level.
- Save the prediction to the database.
- Return the response to the frontend.

- The API response includes:
- prediction
- probability
- confidence_score
- latency_ms
- risk / risk_level
- top_features
- explanation when requested

## 9. Explainability System

- Explainability is supported in two ways:
- model-based feature importance for tree models
- optional SHAP-based explanation for deeper inspection
- If SHAP is unavailable, the backend falls back to model-based feature importance from `feature_importances_` or `coef_`.

- The backend can return top features and explanation context.
- This makes the system easier to explain in interviews and more useful for analysts.
- A simple human-friendly explanation can be built from the dominant risk factors such as low tenure and high monthly charges.

- The system now also exposes model-based feature importance through the API.
- The prediction history stores both the model output and the live request input payload for audit and drift analysis.
- MLflow tracks each prediction run with parameters, metrics, input features, and a prediction summary artifact.

- The prediction API now returns:
- prediction
- probability
- confidence_score
- latency_ms
- feature_importance
- explanation_text
- explanation

## 10. Prediction Storage and Data Pipeline

- Every successful prediction is stored in the database.
- Stored fields include:
- customer_id
- prediction
- probability
- confidence_score
- timestamp
- risk information and other metadata are also stored by the backend service layer.

- This stored history powers:
- /dashboard
- /analytics
- /history
- /customers customer modal history view
- /model-health

- The backend also exposes a retraining trigger endpoint:
- POST /retrain
- This reuses the existing ML service retraining script.

- Real-time prediction is available through WebSocket:
- WS /ws/predict
- It uses the same prediction, explanation, and persistence flow as the HTTP endpoint.

- This is important because analytics must come from real prediction events, not hardcoded counts.

## 11. Dashboard Logic

- Dashboard metrics are computed from stored predictions.
- No static chart values should be used.
- Metrics include:
- total customers
- predictions today
- high risk percentage
- risk distribution
- churn vs non-churn split
- prediction trend over time

- Risk buckets are computed from prediction probability:
- low: probability < 0.3
- medium: 0.3 to < 0.7
- high: >= 0.7

## 12. Analytics Logic

- Analytics is also computed from prediction history.
- It shows:
- churn vs non-churn
- risk distribution
- time trend

- The frontend chart components receive live values from the backend.
- The backend normalizes the data so the frontend can handle different response shapes safely.

- The /model-health endpoint runs drift checks against training/reference distributions and the latest live prediction window.
- The /retrain endpoint triggers the retraining pipeline and persists the new model artifact and registry entry.
- MLflow also logs the retraining run and stores the trained model artifact for versioned lineage.

## 13. Full Data Flow

- User enters input in the frontend.
- Frontend sends a request to the backend prediction API.
- Backend loads the saved ML pipeline.
- Backend preprocesses the data.
- Backend runs inference.
- Backend computes probability and explainability.
- Backend stores the prediction in the database.
- Dashboard and analytics read from the stored prediction history.
- History and customer views also use the stored records.

## 14. Validation Evidence

- A direct artifact audit confirmed:
- a real trained model file exists
- the model is loadable through joblib
- the artifact is a Pipeline
- predict() and predict_proba() are available
- the preprocessing artifact is a ColumnTransformer
- a live inference check produced very different probabilities for two different customer profiles

- This confirms the system is production ML, not a fake UI simulation.

## 15. Limitations

- The model quality depends on dataset quality and freshness.
- Explainability is strongest for tree-based models and can be less direct for some pipelines.
- If customer_id is missing or not found, runtime feature lookup may fail and manual inputs must be complete.
- Dashboard accuracy depends on the database having stored prediction history.

## 16. Future Improvements

- Add model drift monitoring and retraining triggers.
- Add calibration plots and probability calibration checks.
- Add richer SHAP summaries in the frontend.
- Add experiment tracking for every retraining run.
- Add automated integration tests for dashboard and analytics aggregates.
- Add batch scoring and scheduled retraining jobs.

## 17. Interview Summary

- This is a real ML-driven churn prediction system.
- It uses a trained persisted model with preprocessing.
- It stores predictions and builds analytics from historical inference data.
- It includes explainability and a secure FastAPI backend.
- The frontend is only a consumer of the live backend, not the source of truth.
