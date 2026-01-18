from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORR_PATH = PROJECT_ROOT / "services" / "correlation-engine" / "app"
if str(CORR_PATH) not in sys.path:
    sys.path.insert(0, str(CORR_PATH))

import rules
import state_machine


def test_evaluate_event_no_incident():
    event = {"component": "core", "payload": {}}
    should_create, stage, confidence, evidence_type = rules.evaluate_event(event, evidence_count=1)
    assert should_create is False
    assert stage is None
    assert confidence == 0.0
    assert evidence_type is None


def test_evaluate_event_suspicious_linux_agent():
    event = {"component": "linux_agent", "payload": {"event_type": "PROCESS_EXECUTION"}}
    should_create, stage, confidence, evidence_type = rules.evaluate_event(event, evidence_count=10)
    assert should_create is True
    assert stage == "SUSPICIOUS"
    assert confidence > 0.0
    assert evidence_type == "PROCESS_ACTIVITY"


def test_cross_domain_escalation_thresholds():
    assert state_machine.determine_stage(10.0) == "SUSPICIOUS"
    assert state_machine.determine_stage(state_machine.CONFIDENCE_THRESHOLD_PROBABLE) == "PROBABLE"
    assert state_machine.determine_stage(state_machine.CONFIDENCE_THRESHOLD_CONFIRMED) == "CONFIRMED"


def test_deduplication_window():
    now = datetime.now(timezone.utc)
    later = now + timedelta(seconds=state_machine.DEDUPLICATION_TIME_WINDOW - 1)
    assert state_machine.is_within_deduplication_window(later, now) is True
    far = now + timedelta(seconds=state_machine.DEDUPLICATION_TIME_WINDOW + 5)
    assert state_machine.is_within_deduplication_window(far, now) is False


def test_detect_contradiction_host_vs_network():
    event = {"component": "dpi", "payload": {"threat_level": "BENIGN"}}
    evidence = [{"component": "linux_agent", "payload": {"threat_level": "SUSPICIOUS"}}]
    is_contradiction, contradiction_type = state_machine.detect_contradiction(event, evidence)
    assert is_contradiction is True
    assert contradiction_type == "HOST_VS_NETWORK"
