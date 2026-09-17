from __future__ import annotations

import numpy as np

from services.explainability_service import ExplainabilityService


class DummyPreprocessor:
    feature_names_in_ = np.array(["tenure_in_months", "monthly_charge", "contract_type"])

    def transform(self, frame):
        return frame[["tenure_in_months", "monthly_charge", "contract_type"]].to_numpy(dtype=float)

    def get_feature_names_out(self):
        return np.array(["num__tenure_in_months", "num__monthly_charge", "cat__contract_type"])


class DummyModel:
    feature_names_in_ = np.array(["tenure_in_months", "monthly_charge", "contract_type"])


class DummyArtifacts:
    model = DummyModel()
    preprocessor = DummyPreprocessor()
    model_version = "v-test"


class StubExplanation:
    def __init__(self, values) -> None:
        self.values = values


class StubExplainer:
    def __call__(self, data):
        rows = getattr(data, "shape", (1,))[0]
        if rows > 1:
            return StubExplanation(np.array([[0.40, -0.15, 0.05], [0.20, -0.25, 0.10]]))
        return StubExplanation(np.array([[0.30, -0.20, 0.10]]))


def test_explainability_service_returns_local_and_global_shap(monkeypatch) -> None:
    monkeypatch.setattr("services.explainability_service.shap.Explainer", lambda *args, **kwargs: StubExplainer())

    service = ExplainabilityService(DummyArtifacts())

    local_summary = service.explain_prediction(
        {"tenure_in_months": 12, "monthly_charge": 79.5, "contract_type": 1},
        top_n=2,
    )
    global_summary = service.global_feature_importance(top_n=2)

    assert local_summary.available is True
    assert local_summary.top_features[0].feature == "tenure_in_months"
    assert len(local_summary.top_features) == 2

    assert global_summary.available is True
    assert global_summary.top_features[0].feature == "tenure_in_months"
    assert global_summary.background_rows >= 1
