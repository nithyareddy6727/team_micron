from __future__ import annotations

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score


def recall_at_top_k(y_true: np.ndarray, y_score: np.ndarray, top_k_pct: float) -> float:
    if len(y_true) == 0:
        return 0.0
    k = max(1, int(len(y_true) * top_k_pct))
    ranked_idx = np.argsort(-y_score)
    top_idx = ranked_idx[:k]
    positives = np.sum(y_true == 1)
    if positives == 0:
        return 0.0
    return float(np.sum(y_true[top_idx] == 1) / positives)


def evaluate_binary_scores(y_true: np.ndarray, y_score: np.ndarray, top_k_pct: float) -> dict[str, float]:
    metrics = {
        "roc_auc": float(roc_auc_score(y_true, y_score)) if len(np.unique(y_true)) > 1 else 0.0,
        "pr_auc": float(average_precision_score(y_true, y_score)),
        "recall_top_k": float(recall_at_top_k(y_true, y_score, top_k_pct)),
    }
    return metrics
