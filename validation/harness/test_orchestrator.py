#!/usr/bin/env python3
"""
RansomEye v1.0 Validation Harness - Core Orchestrator Tests
AUTHORITATIVE: Phase 2 supervision validation
"""

import json
import os
import signal
import subprocess
import tempfile
import time
import threading
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, Any

from validation.harness.phase_c_executor import ValidationStatus


def _core_main() -> Path:
    project_root = Path(__file__).parent.parent.parent
    return project_root / "core" / "main.py"


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    _, port = sock.getsockname()
    sock.close()
    return port


def _wait_for_state(status_path: Path, state: str, timeout: int = 15) -> Dict[str, Any]:
    start = time.time()
    while time.time() - start < timeout:
        if status_path.exists():
            data = json.loads(status_path.read_text(encoding="utf-8"))
            if data.get("state") == state:
                return data
        time.sleep(0.5)
    return {}


def test_orch_001_startup_shutdown() -> Dict[str, Any]:
    """
    ORCH-001: Core starts components and shuts them down.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="ransomeye-orch-"))
    status_path = temp_dir / "core_status.json"
    env = os.environ.copy()
    env["RANSOMEYE_ORCHESTRATOR_STUB"] = "1"
    env["RANSOMEYE_CORE_STATUS_PATH"] = str(status_path)
    env["RANSOMEYE_STARTUP_TIMEOUT_SECONDS"] = "5"
    env["RANSOMEYE_SUPERVISOR_POLL_SECONDS"] = "1"
    env["RANSOMEYE_RUN_DIR"] = str(temp_dir)
    env["CI"] = "true"
    env["RANSOMEYE_ENV"] = "ci"

    proc = subprocess.Popen([os.environ.get("PYTHON", "python3"), str(_core_main())], env=env)
    data = _wait_for_state(status_path, "RUNNING", timeout=10)

    if not data:
        proc.terminate()
        return {"status": ValidationStatus.FAILED.value, "error": "Core did not reach RUNNING"}

    proc.send_signal(signal.SIGTERM)
    proc.wait(timeout=10)

    stopped = _wait_for_state(status_path, "STOPPED", timeout=5)
    components = stopped.get("components", {}) if stopped else {}
    all_stopped = all(c.get("state") == "STOPPED" and c.get("pid") is None for c in components.values())
    passed = bool(stopped) and all_stopped
    return {
        "status": ValidationStatus.PASSED.value if passed else ValidationStatus.FAILED.value,
        "start_order": data.get("start_order", []),
        "stopped_state": stopped.get("state") if stopped else None,
        "all_components_stopped": all_stopped
    }


def test_orch_002_failure_injection() -> Dict[str, Any]:
    """
    ORCH-002: Health failure triggers Core exit.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="ransomeye-orch-fail-"))
    status_path = temp_dir / "core_status.json"
    env = os.environ.copy()
    env["RANSOMEYE_ORCHESTRATOR_STUB"] = "1"
    env["RANSOMEYE_CORE_STATUS_PATH"] = str(status_path)
    env["RANSOMEYE_INJECT_FAIL_HEALTH"] = "ingest"
    env["RANSOMEYE_STARTUP_TIMEOUT_SECONDS"] = "5"
    env["RANSOMEYE_SUPERVISOR_POLL_SECONDS"] = "1"
    env["RANSOMEYE_RUN_DIR"] = str(temp_dir)
    env["CI"] = "true"
    env["RANSOMEYE_ENV"] = "ci"

    proc = subprocess.Popen([os.environ.get("PYTHON", "python3"), str(_core_main())], env=env)
    proc.wait(timeout=10)
    data = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
    failed = data.get("components", {}).get("ingest", {}).get("state") == "FAILED"
    passed = proc.returncode not in (0, None) and failed

    return {
        "status": ValidationStatus.PASSED.value if passed else ValidationStatus.FAILED.value,
        "exit_code": proc.returncode,
        "ingest_state": data.get("components", {}).get("ingest", {}).get("state")
    }


def test_orch_003_kill_ingest() -> Dict[str, Any]:
    """
    ORCH-003: Killing ingest triggers Core failure and stops dependents.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="ransomeye-orch-kill-"))
    status_path = temp_dir / "core_status.json"
    env = os.environ.copy()
    env["RANSOMEYE_ORCHESTRATOR_STUB"] = "1"
    env["RANSOMEYE_CORE_STATUS_PATH"] = str(status_path)
    env["RANSOMEYE_STARTUP_TIMEOUT_SECONDS"] = "5"
    env["RANSOMEYE_SUPERVISOR_POLL_SECONDS"] = "1"
    env["RANSOMEYE_RUN_DIR"] = str(temp_dir)
    env["CI"] = "true"
    env["RANSOMEYE_ENV"] = "ci"

    proc = subprocess.Popen([os.environ.get("PYTHON", "python3"), str(_core_main())], env=env)
    data = _wait_for_state(status_path, "RUNNING", timeout=10)
    if not data:
        proc.terminate()
        return {"status": ValidationStatus.FAILED.value, "error": "Core did not reach RUNNING"}

    ingest_pid = data.get("components", {}).get("ingest", {}).get("pid")
    if ingest_pid:
        os.kill(int(ingest_pid), signal.SIGKILL)

    proc.wait(timeout=10)
    final = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
    core_failed = final.get("state") == "FAILED"
    ui_state = final.get("components", {}).get("ui-backend", {}).get("state")
    passed = proc.returncode not in (0, None) and core_failed and ui_state in ("STOPPED", "FAILED")
    return {
        "status": ValidationStatus.PASSED.value if passed else ValidationStatus.FAILED.value,
        "core_state": final.get("state"),
        "ui_state": ui_state
    }


def test_orch_004_ui_degraded() -> Dict[str, Any]:
    """
    ORCH-004: UI health failure triggers SECURITY_DEGRADED without Core failure.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="ransomeye-orch-ui-"))
    status_path = temp_dir / "core_status.json"
    env = os.environ.copy()
    env["RANSOMEYE_ORCHESTRATOR_STUB"] = "1"
    env["RANSOMEYE_INJECT_FAIL_HEALTH"] = "ui-backend"
    env["RANSOMEYE_CORE_STATUS_PATH"] = str(status_path)
    env["RANSOMEYE_STARTUP_TIMEOUT_SECONDS"] = "5"
    env["RANSOMEYE_SUPERVISOR_POLL_SECONDS"] = "1"
    env["RANSOMEYE_RUN_DIR"] = str(temp_dir)
    env["CI"] = "true"
    env["RANSOMEYE_ENV"] = "ci"

    proc = subprocess.Popen([os.environ.get("PYTHON", "python3"), str(_core_main())], env=env)
    time.sleep(5)
    data = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
    global_state = data.get("global_state")
    ui_state = data.get("components", {}).get("ui-backend", {}).get("state")
    ingest_state = data.get("components", {}).get("ingest", {}).get("state")
    proc.send_signal(signal.SIGTERM)
    proc.wait(timeout=10)

    passed = global_state == "SECURITY_DEGRADED" and ui_state in ("STOPPED", "FAILED") and ingest_state == "RUNNING"
    return {
        "status": ValidationStatus.PASSED.value if passed else ValidationStatus.FAILED.value,
        "global_state": global_state,
        "ui_state": ui_state,
        "ingest_state": ingest_state
    }


def test_orch_005_stub_mode_guard() -> Dict[str, Any]:
    """
    ORCH-005: Stub mode rejected outside CI.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="ransomeye-orch-guard-"))
    status_path = temp_dir / "core_status.json"
    env = os.environ.copy()
    env["RANSOMEYE_ORCHESTRATOR_STUB"] = "1"
    env["RANSOMEYE_CORE_STATUS_PATH"] = str(status_path)
    env.pop("CI", None)
    env.pop("RANSOMEYE_ENV", None)

    proc = subprocess.Popen([os.environ.get("PYTHON", "python3"), str(_core_main())], env=env)
    proc.wait(timeout=5)
    passed = proc.returncode not in (0, None)
    return {
        "status": ValidationStatus.PASSED.value if passed else ValidationStatus.FAILED.value,
        "exit_code": proc.returncode
    }


def test_orch_006_status_schema_validation() -> Dict[str, Any]:
    """
    ORCH-006: Status schema rejects malformed data.
    """
    from core.status_schema import validate_status
    valid, _ = validate_status({"state": "RUNNING"})
    passed = valid is False
    return {
        "status": ValidationStatus.PASSED.value if passed else ValidationStatus.FAILED.value,
        "invalid_rejected": passed
    }


def test_orch_007_dpi_failure() -> Dict[str, Any]:
    """
    ORCH-007: DPI startup failure triggers Core failure.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="ransomeye-orch-dpi-fail-"))
    status_path = temp_dir / "core_status.json"
    env = os.environ.copy()
    env["RANSOMEYE_ORCHESTRATOR_STUB"] = "1"
    env["RANSOMEYE_CORE_STATUS_PATH"] = str(status_path)
    env["RANSOMEYE_INJECT_FAIL_START"] = "dpi-probe"
    env["RANSOMEYE_STARTUP_TIMEOUT_SECONDS"] = "5"
    env["RANSOMEYE_SUPERVISOR_POLL_SECONDS"] = "1"
    env["RANSOMEYE_RUN_DIR"] = str(temp_dir)
    env["CI"] = "true"
    env["RANSOMEYE_ENV"] = "ci"

    proc = subprocess.Popen([os.environ.get("PYTHON", "python3"), str(_core_main())], env=env)
    proc.wait(timeout=10)
    data = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
    dpi_state = data.get("components", {}).get("dpi-probe", {}).get("state")
    passed = proc.returncode not in (0, None) and dpi_state == "FAILED"

    return {
        "status": ValidationStatus.PASSED.value if passed else ValidationStatus.FAILED.value,
        "exit_code": proc.returncode,
        "dpi_state": dpi_state
    }


def _start_auth_failure_server(port: int) -> HTTPServer:
    class AuthFailureHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/health":
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b"unauthorized")
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            return

    server = HTTPServer(("127.0.0.1", port), AuthFailureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def test_orch_008_ui_auth_failure_degraded() -> Dict[str, Any]:
    """
    ORCH-008: UI auth failure triggers SECURITY_DEGRADED.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="ransomeye-orch-ui-auth-"))
    status_path = temp_dir / "core_status.json"
    port = _free_port()
    server = _start_auth_failure_server(port)

    env = os.environ.copy()
    env["RANSOMEYE_ORCHESTRATOR_STUB"] = "1"
    env["RANSOMEYE_FORCE_UI_HTTP_HEALTH"] = "1"
    env["RANSOMEYE_UI_PORT"] = str(port)
    env["RANSOMEYE_CORE_STATUS_PATH"] = str(status_path)
    env["RANSOMEYE_STARTUP_TIMEOUT_SECONDS"] = "5"
    env["RANSOMEYE_SUPERVISOR_POLL_SECONDS"] = "1"
    env["RANSOMEYE_RUN_DIR"] = str(temp_dir)
    env["CI"] = "true"
    env["RANSOMEYE_ENV"] = "ci"

    proc = subprocess.Popen([os.environ.get("PYTHON", "python3"), str(_core_main())], env=env)
    time.sleep(5)
    data = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
    global_state = data.get("global_state")
    ui_state = data.get("components", {}).get("ui-backend", {}).get("state")
    security_events = data.get("security_events", [])
    proc.send_signal(signal.SIGTERM)
    proc.wait(timeout=10)
    server.shutdown()

    auth_failure = any(event.get("reason") == "UI_AUTH_FAILURE" for event in security_events)
    passed = global_state == "SECURITY_DEGRADED" and auth_failure and ui_state in ("STOPPED", "FAILED")
    return {
        "status": ValidationStatus.PASSED.value if passed else ValidationStatus.FAILED.value,
        "global_state": global_state,
        "ui_state": ui_state,
        "auth_failure_event": auth_failure
    }
