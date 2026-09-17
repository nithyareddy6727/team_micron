"""Batch prediction schema aliases.

This module keeps batch-specific contracts in a dedicated namespace while
preserving backward compatibility with imports from schemas.prediction.
"""

from schemas.prediction import (
    AsyncBatchAccepted,
    AsyncBatchJobStatus,
    AsyncBatchPredictionRequest,
    BatchJobErrorItem,
    BatchJobPredictionItem,
    BatchPredictionData,
    BatchPredictionItem,
    BatchPredictionRequest,
    BatchPredictionRow,
)

__all__ = [
    "BatchPredictionRequest",
    "BatchPredictionData",
    "BatchPredictionItem",
    "BatchPredictionRow",
    "AsyncBatchPredictionRequest",
    "AsyncBatchAccepted",
    "AsyncBatchJobStatus",
    "BatchJobPredictionItem",
    "BatchJobErrorItem",
]
