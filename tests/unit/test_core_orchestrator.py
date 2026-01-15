import json
import os
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.orchestrator import CoreOrchestrator, ComponentSpec, ComponentState, ComponentAdapter
from core.status_schema import validate_status


class _Logger:
    def startup(self, *args, **kwargs):
        return None

    def shutdown(self, *args, **kwargs):
        return None

    def info(self, *args, **kwargs):
        return None


class _ShutdownHandler:
    def is_shutdown_requested(self) -> bool:
        return True


@dataclass
class _FakeAdapter:
    state: ComponentState
    process: object = None
    last_health: bool = None
    last_error: str = None
    started_at: str = None
    last_successful_cycle: str = None
    failure_reason: str = None


def _make_orchestrator(tmp_path: Path) -> CoreOrchestrator:
    os.environ["RANSOMEYE_CORE_STATUS_PATH"] = str(tmp_path / "core_status.json")
    return CoreOrchestrator(_Logger(), _ShutdownHandler())


def test_topological_sort_detects_cycle(tmp_path):
    orchestrator = _make_orchestrator(tmp_path)
    orchestrator.specs = [
        ComponentSpec(name="a", dependencies=["b"], critical=True, health_mode="process"),
        ComponentSpec(name="b", dependencies=["a"], critical=True, health_mode="process"),
    ]
    with pytest.raises(RuntimeError):
        orchestrator._topological_sort()


def test_dependency_action_stops_noncritical(tmp_path):
    orchestrator = _make_orchestrator(tmp_path)
    orchestrator.specs = [
        ComponentSpec(name="core", dependencies=[], critical=True, health_mode="process"),
        ComponentSpec(name="ui", dependencies=["core"], critical=False, health_mode="http"),
    ]
    orchestrator.adapters = {
        "core": _FakeAdapter(state=ComponentState.FAILED),
        "ui": _FakeAdapter(state=ComponentState.RUNNING),
    }
    assert orchestrator._dependency_action(orchestrator.specs[1]) == "stop_dependent"


def test_dependency_action_fails_core(tmp_path):
    orchestrator = _make_orchestrator(tmp_path)
    orchestrator.specs = [
        ComponentSpec(name="ingest", dependencies=[], critical=True, health_mode="http"),
        ComponentSpec(name="dpi", dependencies=["ingest"], critical=True, health_mode="process"),
    ]
    orchestrator.adapters = {
        "ingest": _FakeAdapter(state=ComponentState.FAILED),
        "dpi": _FakeAdapter(state=ComponentState.RUNNING),
    }
    assert orchestrator._dependency_action(orchestrator.specs[1]) == "core_fail"


def test_write_status_emits_valid_schema(tmp_path):
    orchestrator = _make_orchestrator(tmp_path)
    orchestrator.adapters = {
        "ingest": _FakeAdapter(
            state=ComponentState.RUNNING,
            process=SimpleNamespace(pid=1234),
            last_health=True,
        ),
        "dpi-probe": _FakeAdapter(
            state=ComponentState.RUNNING,
            process=SimpleNamespace(pid=5678),
            last_health=True,
        ),
    }
    orchestrator.start_order = ["ingest", "dpi-probe"]
    orchestrator.state = ComponentState.RUNNING
    orchestrator.global_state = "RUNNING"
    orchestrator._write_status()

    payload = json.loads(Path(orchestrator.status_path).read_text(encoding="utf-8"))
    valid, error = validate_status(payload)
    assert valid is True
    assert error == ""


def test_component_health_status_checks(tmp_path):
    status_path = tmp_path / "component.status.json"
    spec = ComponentSpec(
        name="correlation-engine",
        dependencies=[],
        critical=True,
        health_mode="status",
        status_path=status_path,
        cycle_timeout_seconds=2,
    )
    adapter = ComponentAdapter(spec, _Logger(), env={}, stub_mode=False)
    adapter.process = SimpleNamespace(poll=lambda: None, returncode=None)
    adapter.started_at = "2024-01-01T00:00:00+00:00"
    status_path.write_text(
        json.dumps(
            {
                "state": "RUNNING",
                "last_successful_cycle": "2024-01-01T00:00:01+00:00",
                "failure_reason": None,
            }
        ),
        encoding="utf-8",
    )
    assert adapter._health_status() is True
