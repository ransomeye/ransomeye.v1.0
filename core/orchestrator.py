#!/usr/bin/env python3
"""
RansomEye v1.0 Core Orchestrator
AUTHORITATIVE: Component orchestration, supervision, and shutdown enforcement
"""

import json
import os
import signal
import sys
import time
import urllib.request
import urllib.error
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from subprocess import Popen
from typing import Dict, List, Optional

from core.status_schema import validate_status


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ComponentState(str, Enum):
    INIT = "INIT"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"


@dataclass
class ComponentSpec:
    name: str
    dependencies: List[str]
    critical: bool
    health_mode: str  # "http" or "status" or "process"
    health_url: Optional[str] = None
    start_command: List[str] = field(default_factory=list)
    stop_signal: int = signal.SIGTERM
    health_timeout_seconds: int = 3
    cycle_timeout_seconds: int = 300
    status_path: Optional[Path] = None


class ComponentAdapter:
    def __init__(self, spec: ComponentSpec, logger, env: Dict[str, str], stub_mode: bool = False):
        self.spec = spec
        self.logger = logger
        self.env = env
        self.stub_mode = stub_mode
        self.process: Optional[Popen] = None
        self.state = ComponentState.INIT
        self.last_error: Optional[str] = None
        self.last_health: Optional[bool] = None
        self.last_successful_cycle: Optional[str] = None
        self.failure_reason: Optional[str] = None
        self.started_at: Optional[str] = None
        self.next_run_at: Optional[float] = None

    def start(self) -> None:
        self.state = ComponentState.STARTING
        self.started_at = _now()
        if os.getenv("RANSOMEYE_INJECT_FAIL_START") == self.spec.name:
            raise RuntimeError(f"Injected startup failure for {self.spec.name}")
        command = self._resolve_command()
        self.process = Popen(
            command,
            env=self.env
        )
        self.logger.startup(f"Component started: {self.spec.name}", command=" ".join(command))
        self.next_run_at = None

    def stop(self, timeout_seconds: int = 10) -> None:
        if not self.process:
            self.state = ComponentState.STOPPED
            return
        self.state = ComponentState.STOPPING
        try:
            self.process.send_signal(self.spec.stop_signal)
            self.process.wait(timeout=timeout_seconds)
        except Exception:
            try:
                self.process.kill()
            except Exception:
                pass
        self.process = None
        self.state = ComponentState.STOPPED
        self.logger.shutdown(f"Component stopped: {self.spec.name}")

    def health(self) -> bool:
        if os.getenv("RANSOMEYE_INJECT_FAIL_HEALTH") == self.spec.name:
            return False
        if self.stub_mode and not (
            self.spec.name == "ui-backend" and os.getenv("RANSOMEYE_FORCE_UI_HTTP_HEALTH") == "1"
        ):
            return self._health_process()
        if self.spec.health_mode == "http":
            return self._health_http()
        if self.spec.health_mode == "status":
            return self._health_status()
        return self._health_process()

    def _health_status(self) -> bool:
        if not self.process:
            return False
        if self.process.poll() is not None:
            self.failure_reason = f"Process exited with {self.process.returncode}"
            return False
        if not self.spec.status_path or not self.spec.status_path.exists():
            self.failure_reason = "Status file missing"
            return False
        try:
            status = json.loads(self.spec.status_path.read_text(encoding="utf-8"))
        except Exception as exc:
            self.failure_reason = f"Status file invalid: {exc}"
            return False
        self.last_successful_cycle = status.get("last_successful_cycle")
        self.failure_reason = status.get("failure_reason")
        state = status.get("state")
        if state != "RUNNING":
            self.failure_reason = self.failure_reason or "Component not running"
            return False
        if not self.last_successful_cycle:
            if self.started_at:
                try:
                    started = datetime.fromisoformat(self.started_at)
                    age = (datetime.now(timezone.utc) - started).total_seconds()
                    if age <= self.spec.cycle_timeout_seconds:
                        return True
                except Exception:
                    pass
            return False
        try:
            last_time = datetime.fromisoformat(self.last_successful_cycle)
            age = (datetime.now(timezone.utc) - last_time).total_seconds()
            if age > self.spec.cycle_timeout_seconds * 2:
                self.failure_reason = f"Last cycle too old ({age}s)"
                return False
        except Exception:
            self.failure_reason = "Invalid last_successful_cycle timestamp"
            return False
        return True

    def _health_process(self) -> bool:
        if not self.process:
            return False
        return self.process.poll() is None

    def _health_http(self) -> bool:
        if not self.spec.health_url:
            return self._health_process()
        try:
            request = urllib.request.Request(self.spec.health_url)
            if self.spec.name == "ui-backend":
                ui_token = os.getenv("RANSOMEYE_UI_HEALTH_TOKEN")
                if ui_token:
                    request.add_header("Authorization", f"Bearer {ui_token}")
            with urllib.request.urlopen(request, timeout=self.spec.health_timeout_seconds) as response:
                if response.status != 200:
                    return False
                payload = json.loads(response.read().decode("utf-8"))
                self.last_successful_cycle = payload.get("last_successful_cycle")
                self.failure_reason = payload.get("failure_reason")
                return True
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                self.failure_reason = "AUTH_FAILURE"
                self.last_error = f"auth_failure:{exc.code}"
            else:
                self.last_error = str(exc)
            return False
        except Exception as exc:
            self.last_error = str(exc)
            return False

    def _resolve_command(self) -> List[str]:
        if self.stub_mode:
            if self.spec.kind == "batch":
                return ["python3", "-c", "import time; time.sleep(3600)"]
            return ["python3", "-c", "import time; time.sleep(3600)"]
        return self.spec.start_command


class CoreOrchestrator:
    def __init__(self, logger, shutdown_handler):
        self.logger = logger
        self.shutdown_handler = shutdown_handler
        self.stub_mode = os.getenv("RANSOMEYE_ORCHESTRATOR_STUB", "0") == "1"
        if self.stub_mode:
            if os.getenv("CI") != "true" or os.getenv("RANSOMEYE_ENV") != "ci":
                raise RuntimeError("Orchestrator stub mode is only allowed in CI with RANSOMEYE_ENV=ci")
        self.poll_interval = int(os.getenv("RANSOMEYE_SUPERVISOR_POLL_SECONDS", "2"))
        self.startup_timeout = int(os.getenv("RANSOMEYE_STARTUP_TIMEOUT_SECONDS", "30"))
        self.shutdown_timeout = int(os.getenv("RANSOMEYE_SHUTDOWN_TIMEOUT_SECONDS", "10"))
        self.status_path = Path(os.getenv("RANSOMEYE_CORE_STATUS_PATH", ""))
        if not self.status_path:
            run_dir = os.getenv("RANSOMEYE_RUN_DIR", "/tmp/ransomeye")
            self.status_path = Path(run_dir) / "core_status.json"
        self.start_order: List[str] = []
        self.adapters: Dict[str, ComponentAdapter] = {}
        self.state = ComponentState.INIT
        self.global_state = "INIT"
        self.failure_reason_code: Optional[str] = None
        self.failure_reason: Optional[str] = None
        self.security_events: List[Dict[str, str]] = []
        self.core_pid = os.getpid()
        self.core_token = os.getenv("RANSOMEYE_CORE_TOKEN", str(uuid.uuid4()))
        os.environ["RANSOMEYE_CORE_TOKEN"] = self.core_token
        self.specs = self._build_specs()
        self.adapters = self._build_adapters()

    def run(self) -> int:
        try:
            self.state = ComponentState.STARTING
            self.global_state = "STARTING"
            self._write_status()
            order = self._topological_sort()
            self.logger.startup("Core orchestrator starting components", order=order)
            self._start_components(order)
            if not self._all_critical_running():
                raise RuntimeError("Critical components not running")
            self.state = ComponentState.RUNNING
            self.global_state = "RUNNING"
            self._write_status()

            while not self.shutdown_handler.is_shutdown_requested():
                self._supervise()
                time.sleep(self.poll_interval)

            self._shutdown_components()
            return 0
        except Exception as exc:
            self.state = ComponentState.FAILED
            self.global_state = "FAILED"
            self.failure_reason = str(exc)
            self.failure_reason_code = self.failure_reason_code or "CORE_FAILURE"
            self._write_status()
            raise

    def _build_specs(self) -> List[ComponentSpec]:
        ingest_port = int(os.getenv("RANSOMEYE_INGEST_PORT", "8000"))
        ui_port = int(os.getenv("RANSOMEYE_UI_PORT", "8080"))
        batch_interval = int(os.getenv("RANSOMEYE_BATCH_INTERVAL_SECONDS", "300"))
        project_root = Path(__file__).resolve().parent.parent
        python = "python3"

        run_dir = Path(os.getenv("RANSOMEYE_RUN_DIR", "/tmp/ransomeye"))
        return [
            ComponentSpec(
                name="ingest",
                dependencies=[],
                critical=True,
                health_mode="http",
                health_url=f"http://127.0.0.1:{ingest_port}/health",
                start_command=[python, str(project_root / "services" / "ingest" / "app" / "main.py")],
                status_path=run_dir / "ingest.status.json"
            ),
            ComponentSpec(
                name="dpi-probe",
                dependencies=["ingest"],
                critical=True,
                health_mode="process",
                start_command=[python, str(project_root / "dpi" / "probe" / "main.py")],
                status_path=run_dir / "dpi-probe.status.json"
            ),
            ComponentSpec(
                name="correlation-engine",
                dependencies=["ingest"],
                critical=True,
                health_mode="status",
                cycle_timeout_seconds=batch_interval,
                start_command=[python, str(project_root / "services" / "correlation-engine" / "app" / "main.py")],
                status_path=run_dir / "correlation-engine.status.json"
            ),
            ComponentSpec(
                name="ai-core",
                dependencies=["correlation-engine"],
                critical=True,
                health_mode="status",
                cycle_timeout_seconds=batch_interval,
                start_command=[python, str(project_root / "services" / "ai-core" / "app" / "main.py")],
                status_path=run_dir / "ai-core.status.json"
            ),
            ComponentSpec(
                name="policy-engine",
                dependencies=["correlation-engine"],
                critical=True,
                health_mode="status",
                cycle_timeout_seconds=batch_interval,
                start_command=[python, str(project_root / "services" / "policy-engine" / "app" / "main.py")],
                status_path=run_dir / "policy-engine.status.json"
            ),
            ComponentSpec(
                name="ui-backend",
                dependencies=["ingest", "correlation-engine", "ai-core"],
                critical=False,
                health_mode="http",
                health_url=f"http://127.0.0.1:{ui_port}/health",
                start_command=[python, str(project_root / "services" / "ui" / "backend" / "main.py")],
                status_path=run_dir / "ui-backend.status.json"
            )
        ]

    def _build_adapters(self) -> Dict[str, ComponentAdapter]:
        env = os.environ.copy()
        env["RANSOMEYE_SUPERVISED"] = "1"
        env["RANSOMEYE_CORE_PID"] = str(self.core_pid)
        env["RANSOMEYE_CORE_TOKEN"] = self.core_token
        env["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent)
        install_root = env.get("RANSOMEYE_INSTALL_ROOT", "/opt/ransomeye")
        env.setdefault("RANSOMEYE_COMPONENT_KEY_DIR", str(Path(install_root) / "config" / "component-keys"))
        env.setdefault("RANSOMEYE_SERVICE_KEY_DIR", str(Path(install_root) / "config" / "keys"))
        adapters = {}
        for spec in self.specs:
            env_with_status = env.copy()
            if spec.status_path:
                env_with_status["RANSOMEYE_COMPONENT_STATUS_PATH"] = str(spec.status_path)
                env_with_status["RANSOMEYE_COMPONENT_CYCLE_SECONDS"] = str(spec.cycle_timeout_seconds)
            adapters[spec.name] = ComponentAdapter(spec, self.logger, env_with_status, stub_mode=self.stub_mode)
        return adapters

    def _topological_sort(self) -> List[str]:
        graph: Dict[str, List[str]] = {spec.name: list(spec.dependencies) for spec in self.specs}
        visited = set()
        temp = set()
        order: List[str] = []

        def visit(node: str):
            if node in temp:
                raise RuntimeError(f"Dependency cycle detected at {node}")
            if node in visited:
                return
            temp.add(node)
            for dep in graph[node]:
                visit(dep)
            temp.remove(node)
            visited.add(node)
            order.append(node)

        for name in graph:
            visit(name)
        return order

    def _start_components(self, order: List[str]) -> None:
        start_deadline = time.time() + self.startup_timeout
        for name in order:
            adapter = self.adapters[name]
            adapter.start()
            self.start_order.append(name)
            self._write_status()
            while time.time() < start_deadline:
                if adapter.health():
                    adapter.state = ComponentState.RUNNING
                    self._write_status()
                    break
                time.sleep(1)
            if adapter.state != ComponentState.RUNNING:
                adapter.state = ComponentState.FAILED
                self.failure_reason_code = "STARTUP_FAILED"
                self._write_status()
                raise RuntimeError(f"Component failed to start: {name}")

    def _supervise(self) -> None:
        for name, adapter in self.adapters.items():
            dependency_action = self._dependency_action(adapter.spec)
            if dependency_action == "core_fail":
                self.failure_reason_code = "DEPENDENCY_FAILURE"
                raise RuntimeError(f"Dependency failure for {name}")
            if dependency_action == "stop_dependent":
                adapter.stop(self.shutdown_timeout)
                if name == "ui-backend":
                    self._emit_security_degraded("UI_BACKEND_UNHEALTHY")
                continue

            healthy = adapter.health()
            adapter.last_health = healthy
            if healthy:
                if adapter.state in (ComponentState.STARTING, ComponentState.DEGRADED):
                    adapter.state = ComponentState.RUNNING
            else:
                adapter.state = ComponentState.FAILED
                if name == "ui-backend":
                    if adapter.failure_reason == "AUTH_FAILURE":
                        self._emit_security_degraded("UI_AUTH_FAILURE")
                    else:
                        self._emit_security_degraded("UI_BACKEND_UNHEALTHY")
                    adapter.stop(self.shutdown_timeout)
                    continue
                self.failure_reason_code = "HEALTH_FAILED"
                self._write_status()
                if adapter.spec.critical:
                    raise RuntimeError(f"Critical component unhealthy: {name}")
        if not self._all_critical_running():
            self.state = ComponentState.FAILED
            self.global_state = "FAILED"
            self.failure_reason_code = self.failure_reason_code or "CRITICAL_COMPONENT_DOWN"
        elif self.security_events:
            self.state = ComponentState.DEGRADED
            self.global_state = "SECURITY_DEGRADED"
        else:
            self.state = ComponentState.RUNNING
            self.global_state = "RUNNING"
        self._write_status()

    def _dependency_action(self, spec: ComponentSpec) -> str:
        for dep in spec.dependencies:
            dep_spec = next(s for s in self.specs if s.name == dep)
            dep_state = self.adapters[dep].state
            if dep_state in (ComponentState.FAILED, ComponentState.STOPPED):
                if dep_spec.critical and spec.critical:
                    return "core_fail"
                if dep_spec.critical and not spec.critical:
                    return "stop_dependent"
                if not dep_spec.critical:
                    return "none"
        return "none"

    def _shutdown_components(self) -> None:
        self.state = ComponentState.STOPPING
        self.global_state = "STOPPING"
        self._write_status()
        order = list(reversed(self._topological_sort()))
        for name in order:
            adapter = self.adapters[name]
            adapter.stop(self.shutdown_timeout)
        self.state = ComponentState.STOPPED
        self.global_state = "STOPPED"
        self._write_status()

    def _write_status(self) -> None:
        self.status_path.parent.mkdir(parents=True, exist_ok=True)
        status = {
            "schema_version": "1.0",
            "state": self.state.value,
            "timestamp": _now(),
            "global_state": self.global_state,
            "failure_reason_code": self.failure_reason_code,
            "failure_reason": self.failure_reason,
            "security_events": list(self.security_events),
            "components": {
                name: {
                    "state": adapter.state.value,
                    "pid": adapter.process.pid if adapter.process else None,
                    "last_health": adapter.last_health,
                    "last_error": adapter.last_error,
                    "started_at": adapter.started_at,
                    "last_successful_cycle": adapter.last_successful_cycle,
                    "failure_reason": adapter.failure_reason
                }
                for name, adapter in self.adapters.items()
            },
            "start_order": list(self.start_order)
            ,
            "core_pid": self.core_pid,
            "core_token": self.core_token
        }
        valid, error = validate_status(status)
        if not valid:
            raise RuntimeError(f"Status schema validation failed: {error}")
        self.status_path.write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")

    def _emit_security_degraded(self, reason: str) -> None:
        event = {"timestamp": _now(), "event": "SECURITY_DEGRADED", "reason": reason}
        self.security_events.append(event)
        self.failure_reason_code = "SECURITY_DEGRADED"
        self.failure_reason = reason

    def _all_critical_running(self) -> bool:
        return all(
            adapter.state == ComponentState.RUNNING
            for adapter in self.adapters.values()
            if adapter.spec.critical
        )
