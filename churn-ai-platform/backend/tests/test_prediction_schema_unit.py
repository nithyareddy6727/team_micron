import pytest
from pydantic import ValidationError

from schemas.prediction import BatchPredictionRequest, PredictionRequest


def test_prediction_request_rejects_too_many_features() -> None:
    features = {f"f{i}": i for i in range(101)}
    with pytest.raises(ValidationError):
        PredictionRequest(
            customer_id="cust_1",
            features=features,
            return_proba=True,
            explain=False,
        )


def test_batch_prediction_request_rejects_oversized_batch() -> None:
    oversized = [f"cust_{i}" for i in range(201)]
    with pytest.raises(ValidationError):
        BatchPredictionRequest(customer_ids=oversized)
