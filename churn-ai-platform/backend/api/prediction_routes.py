"""Prediction route compatibility module.

The primary route registrations remain in api.routes to preserve existing
integration behavior and monkeypatch-based tests.
This module provides a clean import surface for prediction endpoints.
"""

from api.routes import (
    feature_importance,
    predict,
    predict_batch,
    predict_batch_async,
    predict_batch_job_status,
    predict_batch_upload,
    websocket_predict,
)

__all__ = [
    "predict",
    "websocket_predict",
    "predict_batch",
    "predict_batch_async",
    "predict_batch_upload",
    "predict_batch_job_status",
    "feature_importance",
]
