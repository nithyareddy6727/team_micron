from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.churn_scoring_service import ChurnScoringService


router = APIRouter()
service = ChurnScoringService()


@router.post("/score")
def score(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict) or not payload:
        raise HTTPException(status_code=400, detail="Input JSON object is required")

    try:
        return service.score(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Scoring failed: {exc}") from exc


@router.post("/score/batch")
def score_batch(payload: dict[str, Any]) -> dict[str, Any]:
    users = payload.get("users")
    if not isinstance(users, list) or not users:
        raise HTTPException(status_code=400, detail="Payload must include non-empty users array")

    if any(not isinstance(user, dict) for user in users):
        raise HTTPException(status_code=400, detail="Each batch user item must be an object")

    try:
        return service.score_batch(users)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Batch scoring failed: {exc}") from exc
