from __future__ import annotations

import logging
import os
from pathlib import Path

from app.schemas import RecommendRequest, RecommendResponse, RecommendedItem
from app.services.model import CollaborativeFilteringModel

logger = logging.getLogger("ml-service")

MODEL_DIR = Path(os.getenv("MODEL_ARTIFACT_DIR", "artifacts"))
MODEL_PATH = MODEL_DIR / "recommender.joblib"

recommender_model = CollaborativeFilteringModel()


def load_model_at_startup() -> bool:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if not MODEL_PATH.exists():
        logger.warning("Recommender model not found at startup", extra={"request_id": "n/a"})
        return False

    try:
        recommender_model.load(str(MODEL_PATH))
        logger.info("Recommender model loaded", extra={"request_id": "n/a"})
        return True
    except Exception:
        logger.exception("Failed to load recommender model", extra={"request_id": "n/a"})
        return False

def recommend_items(payload: RecommendRequest) -> RecommendResponse:
    if recommender_model.artifacts is None:
        # Cold-start fallback if model is not trained/loaded yet.
        fallback = [
            RecommendedItem(item_id=event.item_id, score=0.0)
            for event in payload.interaction_history[: payload.top_n]
        ]
        return RecommendResponse(
            user_id=payload.user_id,
            recommendations=fallback,
            recommended_items=fallback,
            model_version="cold-start-v1",
        )

    recs = recommender_model.recommend(
        user_id=payload.user_id,
        interaction_history=[item.model_dump() for item in payload.interaction_history],
        top_n=payload.top_n,
    )

    items = [
        RecommendedItem(item_id=int(item["item_id"]), score=float(item["score"]))
        for item in recs
    ]

    return RecommendResponse(
        user_id=payload.user_id,
        recommendations=items,
        recommended_items=items,
        model_version=recommender_model.artifacts.model_version,
    )
