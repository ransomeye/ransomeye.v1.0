from pathlib import Path
import sys
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AI_PATH = PROJECT_ROOT / "services" / "ai-core" / "app"
if str(AI_PATH) not in sys.path:
    sys.path.insert(0, str(AI_PATH))

import feature_extraction
import shap_explainer


def test_extract_incident_features_numeric_confidence():
    incident = {
        "confidence_score": 42.5,
        "current_stage": "PROBABLE",
        "total_evidence_count": 3,
    }
    features = feature_extraction.extract_incident_features(incident)
    assert features[0] == 42.5


def test_extract_incident_features_non_numeric_reject():
    incident = {
        "confidence_score": "not-a-number",
        "current_stage": "SUSPICIOUS",
        "total_evidence_count": 1,
    }
    with pytest.raises(ValueError):
        feature_extraction.extract_incident_features(incident)


def test_shap_explainer_malformed_vector_rejects():
    incident = {
        "confidence_score": 10.0,
        "current_stage": "SUSPICIOUS",
        "total_evidence_count": 1,
    }
    with pytest.raises(TypeError):
        shap_explainer.explain_incident_confidence(incident, ["bad"])
