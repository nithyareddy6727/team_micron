from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class RecommenderArtifacts:
    item_ids: list[int]
    item_similarity: np.ndarray
    popular_items: list[int]
    model_version: str


class CollaborativeFilteringModel:
    def __init__(self) -> None:
        self.artifacts: RecommenderArtifacts | None = None

    @staticmethod
    def create_user_item_matrix(interactions_df: pd.DataFrame) -> pd.DataFrame:
        required = {"user_id", "item_id", "interaction_value"}
        missing = required - set(interactions_df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        matrix = interactions_df.pivot_table(
            index="user_id",
            columns="item_id",
            values="interaction_value",
            aggfunc="sum",
            fill_value=0.0,
        )

        matrix.columns = [int(col) for col in matrix.columns]
        return matrix

    def fit(self, interactions_df: pd.DataFrame) -> RecommenderArtifacts:
        matrix = self.create_user_item_matrix(interactions_df)
        item_ids = list(matrix.columns)
        if not item_ids:
            raise ValueError("No items found in interaction matrix")

        item_matrix = matrix.to_numpy(dtype=float).T
        item_similarity = cosine_similarity(item_matrix)

        popularity = (
            interactions_df.groupby("item_id", as_index=False)["interaction_value"]
            .sum()
            .sort_values("interaction_value", ascending=False)
        )

        popular_items = [int(v) for v in popularity["item_id"].tolist()]
        model_version = f"cf-cosine-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        self.artifacts = RecommenderArtifacts(
            item_ids=item_ids,
            item_similarity=item_similarity,
            popular_items=popular_items,
            model_version=model_version,
        )
        return self.artifacts

    def save(self, model_path: str) -> None:
        if self.artifacts is None:
            raise ValueError("Model is not trained")
        joblib.dump(self.artifacts, model_path)

    def load(self, model_path: str) -> RecommenderArtifacts:
        artifacts = joblib.load(model_path)
        if not isinstance(artifacts, RecommenderArtifacts):
            raise ValueError("Invalid recommender artifact format")
        self.artifacts = artifacts
        return artifacts

    def recommend(
        self,
        user_id: int,
        interaction_history: Iterable[dict],
        top_n: int = 5,
    ) -> list[dict[str, float]]:
        if self.artifacts is None:
            raise ValueError("Model is not loaded")

        item_ids = self.artifacts.item_ids
        item_index = {item_id: idx for idx, item_id in enumerate(item_ids)}

        user_vector = np.zeros(len(item_ids), dtype=float)
        seen_items: set[int] = set()

        for event in interaction_history:
            item_id = int(event.get("item_id"))
            value = float(event.get("interaction_value", 1.0))
            if item_id in item_index:
                user_vector[item_index[item_id]] += value
                seen_items.add(item_id)

        if np.allclose(user_vector, 0.0):
            # Cold start: return most popular items.
            cold = [item for item in self.artifacts.popular_items if item not in seen_items][:top_n]
            return [{"item_id": int(item), "score": 0.0} for item in cold]

        raw_scores = user_vector @ self.artifacts.item_similarity

        for seen in seen_items:
            raw_scores[item_index[seen]] = -np.inf

        best_idx = np.argsort(raw_scores)[::-1]
        selected = []
        max_score = np.max(raw_scores[np.isfinite(raw_scores)]) if np.isfinite(raw_scores).any() else 1.0
        max_score = float(max_score) if max_score > 0 else 1.0

        for idx in best_idx:
            if len(selected) >= top_n:
                break
            score = raw_scores[idx]
            if not np.isfinite(score):
                continue
            selected.append(
                {
                    "item_id": int(item_ids[int(idx)]),
                    "score": float(round(float(score) / max_score, 6)),
                }
            )

        return selected
