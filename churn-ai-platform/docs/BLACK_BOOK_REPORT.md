# ChurnX AI - Customer Churn Prediction Platform

## 1. Abstract
ChurnX AI is a full-stack churn prediction platform that combines a React frontend, a FastAPI backend, a persisted sklearn ML pipeline, a MySQL-backed prediction store, and SHAP-based explainability. The system is designed to turn live prediction events into operational dashboards, analytics, and customer history views rather than relying on mock or synthetic UI data.

## 2. Introduction
Customer churn prediction helps businesses identify customers who are likely to leave, prioritize retention work, and monitor product or service health over time. This platform addresses that need by exposing a live inference workflow and storing each prediction event for downstream reporting.

## 3. System Architecture
The system follows a simple production flow:

Frontend -> FastAPI -> sklearn ML Pipeline -> Database -> UI

The frontend submits requests to the backend prediction endpoint. The backend loads the serialized model pipeline, prepares features, computes predictions, stores the prediction event in the database, and returns the result to the UI. Dashboard, analytics, and history views read from the same persisted prediction events, which keeps reporting consistent with live inference.

## 4. Technologies Used
- React
- Vite
- TanStack Query
- FastAPI
- Python 3.13
- sklearn
- pandas
- SHAP
- MLflow
- MySQL

## 5. Dataset
The platform uses a processed telco churn dataset stored in `data/processed/telco_churn_cleaned.csv`. The dataset contains customer profile fields, service usage fields, contract and billing signals, and churn labels used for model training and live feature alignment.

Core signal groups include:
- Demographics such as age and gender
- Tenure and contract information
- Billing and monthly charge behavior
- Service adoption and support usage
- Customer lifetime value and related retention signals

The target variable is churn, represented as a binary class for churn versus non-churn prediction.

## 6. Data Preprocessing
The production model includes a preprocessing pipeline that performs the following steps:
- Missing value imputation
- Scaling for numeric features
- One-hot encoding for categorical features
- Feature alignment to the model's expected input columns

The model artifact inspection confirmed that the production pipeline exposes `predict()` and `predict_proba()` and is not a UI-only simulation.

## 7. Machine Learning Model
The production artifact is a real sklearn Pipeline saved at `ml/artifacts/root-artifacts/churn_model_optimized.pkl`.

Verified properties:
- The artifact is a Pipeline
- `predict()` is available
- `predict_proba()` is available
- Feature names are embedded in the trained pipeline
- Probabilities vary across different customer rows

Validation results from the live artifact:
- Minimum probability on a real dataset slice: 0.0035179078
- Maximum probability on a real dataset slice: 0.9964838028
- Mean probability on that slice: 0.2881160080

This confirms the model is producing a non-trivial churn score distribution.

## 8. Model Deployment
The backend exposes the live scoring API through FastAPI.

Verified endpoints:
- GET /dashboard
- GET /customers
- POST /predict
- GET /analytics
- GET /history

Additional operational endpoints are also present:
- GET /model-health
- POST /retrain
- WebSocket /ws/predict

The prediction endpoint uses the live model, stores the event in the database, and returns the prediction result in a consistent API envelope.

## 9. Explainable AI (SHAP)
The prediction response includes explainability data when requested. SHAP-based feature importance is surfaced when available, and the backend also supports a fallback explanation path if SHAP is unavailable.

The UI presents:
- Probability
- Risk level
- Confidence
- Latency
- Top feature drivers

## 10. Dashboard and Analytics
The dashboard and analytics views are fully data-driven.

Dashboard responsibilities:
- Show total customers
- Show high-risk percentage
- Show predictions today
- Render churn distribution
- Render risk distribution
- Render prediction trend
- Show recent live predictions

Analytics responsibilities:
- Show aggregate counts
- Render risk distribution charts
- Render churn vs non-churn charts
- Render prediction trend charts

Both views read from persisted prediction events rather than hardcoded arrays or mock datasets.

## 11. Data Flow
The operational flow is:

User -> API -> ML model -> DB -> UI

Flow details:
1. A user enters customer data in the frontend.
2. The frontend calls `POST /predict`.
3. The backend loads the model pipeline and computes a churn prediction.
4. The prediction event is stored in the database.
5. Dashboard, analytics, and history query the same stored events.
6. The UI updates with live data on refresh or polling.

## 12. Results
Verified runtime behavior:
- The model produces different probabilities across different inputs
- The dataset slice showed a probability range from 0.0035 to 0.9965
- Backend contract tests passed
- Frontend build passed

Sample smoke test result:
- Two different synthetic inputs produced distinct probabilities
- Real dataset rows produced a broad churn score distribution

## 13. Limitations
- The platform depends on a valid model artifact path and available database connectivity.
- Some operational metrics, including model health and retraining status, depend on backend runtime support and backend-side data freshness.
- The model is only as strong as the training data distribution and feature coverage.
- If the database is empty, dashboard and analytics will naturally show zero or near-zero values until real predictions are recorded.

## 14. Future Enhancements
- Real-time streaming ingestion for prediction events
- Scheduled retraining and model registry automation
- Cloud deployment with managed database and model artifacts
- Alerting for drift and service-level regressions
- A/B testing for model candidates
- Expanded customer journey analytics

## 15. Conclusion
ChurnX AI is a verified end-to-end churn prediction platform built around a real sklearn model, a live FastAPI scoring service, and database-backed analytics. The frontend now consumes live backend data, the backend persists prediction events for reporting, and the ML pipeline has been validated to produce non-trivial churn probabilities across real inputs.

## Validation Checklist
- Frontend pages use live APIs: pass
- No mock or static production data in main views: pass
- Backend endpoints respond with consistent envelopes: pass
- Model artifact exists and is a sklearn Pipeline: pass
- `predict()` and `predict_proba()` are available: pass
- Predictions vary across inputs: pass
- Dashboard and analytics read from stored prediction events: pass
- Contract and integration tests: pass
- Frontend production build: pass