from __future__ import annotations

from fastapi import FastAPI

from app.churn_routes import router as churn_router


app = FastAPI(title="churn-scoring-api", version="1.0.0")
app.include_router(churn_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
