# Churn Prediction System Documentation

## 1. Project Overview

- This project predicts whether a customer is likely to churn.
- It has three main parts:
- Frontend web app for users and analysts.
- Backend API for business logic and data access.
- ML model service for churn prediction.
- The system stores prediction history and uses that history for dashboard and analytics.
- For ML audit details, see [docs/ML_SYSTEM_AUDIT.md](docs/ML_SYSTEM_AUDIT.md).
- Prediction responses now include feature importance and a readable explanation string in addition to probability, confidence, and latency.
- The backend also exposes model-health and retrain endpoints for drift monitoring and continuous improvement.
- The backend also exposes a real-time WebSocket prediction endpoint at /ws/predict.
- Goal:
- Help teams identify high-risk customers early.
- Support retention actions with explainable ML outputs.

## 2. Architecture

- Architecture style:
- Modular full-stack application with clear separation of concerns.
- Main layers:
- Presentation layer: React frontend.
- API layer: FastAPI backend.
- Intelligence layer: trained churn model and explainability logic.
- Data layer: customer dataset + prediction history in database.

- Runtime components:
- Frontend runs on port 3000.
- Backend runs on port 8000.
- Frontend calls backend through HTTP APIs.
- Backend calls model artifacts and database.

- Cross-cutting features:
- API key middleware for protected routes.
- Request logging and request ID middleware.
- Rate limiting and payload size controls.
- Prometheus metrics endpoint for observability.

## 3. Frontend Explanation

- Tech stack:
- React with Vite.
- React Router for page navigation.
- TanStack Query for server state and caching.
- Axios for API calls.
- Recharts for analytics charts.

- Main pages:
- Dashboard: KPI cards, trend, risk split, recent predictions.
- Customers: searchable customer list, risk filtering, modal with history.
- Predictions: run single prediction and show result with confidence/risk.
- History: browse prediction events.
- Analytics: risk distribution, churn split, prediction trend.

- Frontend API behavior:
- Uses a strict response envelope:
- success must be true.
- error must be null.
- data contains actual payload.
- Shows loading, error, and retry states on key pages.

- Frontend design goals:
- Fast navigation with lazy-loaded routes.
- Clear state feedback while data loads.
- Interview-friendly structure with module folders.

## 4. Backend Explanation

- Tech stack:
- FastAPI with Pydantic schemas.
- Uvicorn ASGI server.
- Middleware for security, logging, and reliability.

- Main backend responsibilities:
- Serve prediction endpoints.
- Serve customer and history APIs.
- Build dashboard and analytics from stored prediction history.
- Expose health and observability metrics.

- Startup sequence:
- Initialize logging.
- Validate API key settings when enforcement is enabled.
- Initialize MLflow tracking.
- Initialize database and model metadata.

- Security model:
- API key middleware protects these routes when enabled:
- POST /predict
- POST /predict/batch
- GET /customers
- GET /history

## 5. ML Model Explanation

- Model loading:
- Backend loads model artifacts at startup through ModelLoader.
- Model path can be set by environment variable.
- If not set, default and fallback artifact paths are used.

- Feature contract:
- Core required features are:
- age
- tenure
- monthly_charges
- customer_id is used to fetch customer features from dataset/DB.

- Prediction output:
- prediction: 0 or 1.
- probability: churn probability.
- risk_level: Low, Medium, or High.
- confidence_score and latency_ms.
- optional explanation and top features.

- Risk thresholds:
- Low: probability < 0.30
- Medium: 0.30 to < 0.70
- High: >= 0.70

- Explainability:
- Supports feature importance and per-prediction explanation.
- Can include top drivers in response when explain flag is enabled.

## 6. Data Flow

- Prediction flow:
- User opens frontend Predictions page.
- Frontend sends POST /predict with customer_id and features.
- Backend validates payload and security middleware.
- Backend builds feature frame:
- Pulls customer features from dataset/DB when customer_id exists.
- Merges manual features when provided.
- Model runs inference and calculates probability/risk.
- Backend saves prediction event to database.
- Backend returns normalized API response.
- Frontend renders probability, risk, confidence, and explanation.

- Analytics flow:
- Frontend calls GET /dashboard or GET /analytics.
- Backend computes aggregates from prediction history:
- Total predictions.
- Risk distribution.
- Churn vs non-churn split.
- Trend by hour.
- Frontend renders charts from live backend data.

- Customer flow:
- Frontend calls GET /customers.
- Frontend can call GET /history for recent events.
- Customer modal shows per-customer latest prediction context.

## 7. API Endpoints

- Base URL:
- Backend: http://localhost:8000

- Core endpoints:
- GET /
- Service root message.

- POST /predict
- Run churn prediction for one customer.
- Supports return_proba and explain flags.
- Protected by API key when enforcement is enabled.

- POST /predict/batch
- Run prediction for multiple customer IDs.
- Protected by API key when enforcement is enabled.

- GET /customers
- Returns paginated customer list with search.
- Query params: limit, offset, search.
- Protected by API key when enforcement is enabled.

- GET /history
- Returns paginated prediction history.
- Query params: limit, offset.
- Protected by API key when enforcement is enabled.

- GET /dashboard
- Alias to dashboard metrics view.
- Query param: hours.

- GET /analytics
- Returns analytics payload for charts.
- Query param: hours.

- GET /metrics/dashboard
- Dashboard metrics payload including trend and risk split.

- GET /metrics/app
- Service metrics, inference count, SLO summary.

- GET /metrics/slo
- SLO status payload.

- GET /metrics
- Prometheus metrics endpoint.

- GET /health
- Service health with model and database status.

- GET /explainability/feature-importance
- Global feature importance summary.
- Query param: top_n.

## 8. Folder Structure

- Root:
- run_system.py
- churn-ai-platform/

- churn-ai-platform key folders:
- backend/
- main.py: FastAPI app bootstrap.
- api/: route definitions.
- services/: business logic (prediction, customer, observability).
- models/: DB and model loading modules.
- schemas/: response and request schemas.
- utils/: middleware, logging, security helpers.

- frontend/
- src/App.jsx: route map.
- src/modules/: feature pages (dashboard, customers, prediction, analytics, history).
- src/core/api.js: API client and envelope handling.
- src/components/: shared UI and charts.

- ml/
- models and artifacts.
- training and pipeline scripts.
- inference/evaluation assets.

- data/
- raw, processed, and feature datasets.

- database/
- schema, migrations, seeds, views.

- docs/
- project documentation files.

- scripts/
- release, rollback, and utility scripts.

## 9. How To Run Project

- Prerequisites:
- Python virtual environment created.
- Node.js and npm installed.
- Python dependencies installed.
- Frontend dependencies installed.

- Recommended quick start:
- Activate virtual environment.
- Run command from repository root:
- f:/project/churn-prediction/.venv/Scripts/python.exe run_system.py

- What this starts:
- Backend: http://localhost:8000
- Frontend: http://localhost:3000

- Manual start option:
- Backend:
- Go to churn-ai-platform/backend
- Run uvicorn main:app --host 0.0.0.0 --port 8000
- Frontend:
- Go to churn-ai-platform/frontend
- Run npm run start

- Optional API key setup:
- Set API_KEY environment variable.
- Set ENFORCE_API_KEY=true to enforce protected route auth.

- Basic validation steps:
- Open frontend dashboard page.
- Open health endpoint in browser: http://localhost:8000/health
- Run one prediction from Predictions page.
- Confirm Dashboard and Analytics update from live prediction history.

## Interview Summary (Short Version)

- Problem:
- Reduce customer churn risk with a production-ready prediction system.

- Solution:
- React frontend for operations + FastAPI backend for APIs + ML model for inference.

- Business value:
- Teams can identify high-risk customers and take retention actions sooner.

- Engineering value:
- Clean modular architecture, secure API controls, observable runtime, and reproducible ML artifact loading.
