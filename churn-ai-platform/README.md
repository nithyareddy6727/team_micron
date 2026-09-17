# Churn AI Platform

Production-ready local churn prediction system with FastAPI backend, React frontend, ML artifacts, and SQLite persistence.

## Project Structure

- backend/: FastAPI API, prediction logic, logging, security middleware
- frontend/: React dashboard (Vite + Tailwind + Recharts)
- ml/: model artifacts, training pipeline, mlruns
- data/: datasets
- database/: database file and migrations/schema
- docs/: architecture and implementation documents
- infra/: CI/K8s references
- scripts/: utility scripts
- config/environments/: environment templates for local, staging, and production

## Release Model

- Use the root `VERSION` file and git tags as the release identity.
- Deploy staging first, then promote the same version to production after validation.
- Roll back with `scripts/rollback.ps1` and Kubernetes rollout history.

## Setup

1. Create and activate Python environment (Windows PowerShell)

```powershell
f:/project/churn-prediction/.venv/Scripts/Activate.ps1
```

2. Install Python dependencies

```powershell
pip install -r churn-ai-platform/requirements.txt
```

3. Install frontend dependencies

```powershell
cd churn-ai-platform/frontend
npm install
```

4. Configure API key (optional but recommended)

```powershell
$env:API_KEY = "mysecurekey123"
```

## Run (One Command)

From repository root:

```powershell
f:/project/churn-prediction/.venv/Scripts/python.exe run_system.py
```

The system starts:
- Backend: http://localhost:8000
- Frontend: http://localhost:3000

## API Usage

### Health

```bash
GET /health
```

Response:

```json
{
  "status": "running",
  "model_loaded": true,
  "database_connected": true
}
```

### Predict (Protected)

```bash
POST /predict
Header: x-api-key: mysecurekey123
```

Example body:

```json
{
  "features": {
    "customer_id": "CUST-1001",
    "tenure": 12,
    "MonthlyCharges": 79.5,
    "TotalCharges": 954.0
  },
  "return_proba": true
}
```

Example response:

```json
{
  "prediction": 1,
  "probability": 0.7421,
  "risk_level": "High Risk 🔴",
  "confidence_score": 0.4842
}
```

### Customers (Protected)

```bash
GET /customers?limit=50&offset=0
Header: x-api-key: mysecurekey123
```

## Logging and Monitoring

- Prediction and app logs: churn-ai-platform/logs/app.log
- Error logs: churn-ai-platform/logs/error.log
- MLflow runs: churn-ai-platform/mlruns/

## Power BI Production Embedding

For production analytics embedding, configure Power BI secrets on backend only and use the token broker endpoint:

- `GET /powerbi/embed-config`

Required backend environment variables:

- `POWERBI_TENANT_ID`
- `POWERBI_CLIENT_ID`
- `POWERBI_CLIENT_SECRET`
- `POWERBI_WORKSPACE_ID`
- `POWERBI_REPORT_ID`
- `POWERBI_EMBED_URL`

Security best practice:

- Never expose service principal credentials or long-lived tokens in frontend code.
- Generate short-lived embed tokens per session via backend.

## Notes

- No Docker and no Redis required.
- Designed for Windows + VS Code local workflows.
