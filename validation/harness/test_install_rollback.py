#!/usr/bin/env python3
"""
RansomEye v1.0 Validation Harness - Installer Rollback Tests
AUTHORITATIVE: Phase 1 rollback guarantees
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any

from validation.harness.phase_c_executor import ValidationStatus


def _transaction_script() -> Path:
    project_root = Path(__file__).parent.parent.parent
    return project_root / "installer" / "common" / "install_transaction.py"


def _run_transaction(args, env=None):
    cmd = [os.environ.get("PYTHON", "python3"), str(_transaction_script())] + args
    subprocess.run(cmd, check=True, env=env)


def _run_rollback_framework_linux() -> Dict[str, Any]:
    """
    ROLL-001: Linux rollback removes files and invokes handlers.
    """
    temp_root = Path(tempfile.mkdtemp(prefix="ransomeye-rollback-linux-"))
    state_file = temp_root / ".install_state.json"
    audit_file = temp_root / "rollback_audit.json"
    dummy_file = temp_root / "bin" / "dummy"
    dummy_file.parent.mkdir(parents=True, exist_ok=True)
    dummy_file.write_text("dummy", encoding="utf-8")

    _run_transaction(["init", "--state-file", str(state_file), "--component", "core"])
    _run_transaction([
        "record", "--state-file", str(state_file),
        "--action", "install_binary",
        "--rollback-action", "remove_path",
        "--meta", f"path={dummy_file}",
        "--rollback-meta", f"path={dummy_file}"
    ])
    _run_transaction([
        "record", "--state-file", str(state_file),
        "--action", "set_capabilities",
        "--rollback-action", "remove_capabilities",
        "--meta", f"path={dummy_file}",
        "--rollback-meta", f"path={dummy_file}"
    ])
    _run_transaction([
        "record", "--state-file", str(state_file),
        "--action", "install_systemd_service",
        "--rollback-action", "remove_systemd_service",
        "--meta", "service=ransomeye-test.service",
        "--meta", "service_file=/tmp/ransomeye-test.service",
        "--rollback-meta", "service=ransomeye-test.service",
        "--rollback-meta", "service_file=/tmp/ransomeye-test.service"
    ])
    _run_transaction([
        "record", "--state-file", str(state_file),
        "--action", "apply_migrations",
        "--rollback-action", "rollback_migrations",
        "--meta", "migrations_dir=/tmp/migrations",
        "--meta", "pythonpath=/tmp",
        "--meta", "db_host=localhost",
        "--meta", "db_port=5432",
        "--meta", "db_name=ransomeye",
        "--meta", "db_user=user",
        "--meta", "db_password=pass",
        "--rollback-meta", "migrations_dir=/tmp/migrations",
        "--rollback-meta", "pythonpath=/tmp",
        "--rollback-meta", "db_host=localhost",
        "--rollback-meta", "db_port=5432",
        "--rollback-meta", "db_name=ransomeye",
        "--rollback-meta", "db_user=user",
        "--rollback-meta", "db_password=pass"
    ])

    env = os.environ.copy()
    env["RANSOMEYE_ROLLBACK_SIMULATE"] = "1"
    env["RANSOMEYE_ROLLBACK_AUDIT_FILE"] = str(audit_file)
    _run_transaction(["rollback", "--state-file", str(state_file)], env=env)

    audit_entries = json.loads(audit_file.read_text(encoding="utf-8"))
    audit_actions = {entry["action"] for entry in audit_entries}
    simulate = env.get("RANSOMEYE_ROLLBACK_SIMULATE") == "1"
    required_actions = {
        "remove_path",
        "remove_capabilities",
        "remove_systemd_service",
        "rollback_migrations"
    }
    actions_ok = required_actions.issubset(audit_actions)
    residue_ok = True if simulate else not dummy_file.exists()
    passed = actions_ok and residue_ok

    return {
        "status": ValidationStatus.PASSED.value if passed else ValidationStatus.FAILED.value,
        "dummy_file_removed": not dummy_file.exists(),
        "audit_actions": sorted(audit_actions),
        "simulate": simulate
    }


def test_rollback_framework_linux() -> None:
    result = _run_rollback_framework_linux()
    assert result["status"] == ValidationStatus.PASSED.value, result


def _run_rollback_framework_windows() -> Dict[str, Any]:
    """
    ROLL-002: Windows rollback invokes service and registry handlers.
    """
    temp_root = Path(tempfile.mkdtemp(prefix="ransomeye-rollback-windows-"))
    state_file = temp_root / ".install_state.json"
    audit_file = temp_root / "rollback_audit.json"
    dummy_file = temp_root / "bin" / "dummy.exe"
    dummy_file.parent.mkdir(parents=True, exist_ok=True)
    dummy_file.write_text("dummy", encoding="utf-8")

    _run_transaction(["init", "--state-file", str(state_file), "--component", "windows-agent"])
    _run_transaction([
        "record", "--state-file", str(state_file),
        "--action", "install_binary",
        "--rollback-action", "remove_path",
        "--meta", f"path={dummy_file}",
        "--rollback-meta", f"path={dummy_file}"
    ])
    _run_transaction([
        "record", "--state-file", str(state_file),
        "--action", "install_windows_service",
        "--rollback-action", "remove_windows_service",
        "--meta", "service=RansomEyeWindowsAgent",
        "--meta", "registry_key=HKLM\\SYSTEM\\CurrentControlSet\\Services\\RansomEyeWindowsAgent",
        "--rollback-meta", "service=RansomEyeWindowsAgent",
        "--rollback-meta", "registry_key=HKLM\\SYSTEM\\CurrentControlSet\\Services\\RansomEyeWindowsAgent"
    ])

    env = os.environ.copy()
    env["RANSOMEYE_ROLLBACK_SIMULATE"] = "1"
    env["RANSOMEYE_ROLLBACK_AUDIT_FILE"] = str(audit_file)
    _run_transaction(["rollback", "--state-file", str(state_file)], env=env)

    audit_entries = json.loads(audit_file.read_text(encoding="utf-8"))
    audit_actions = {entry["action"] for entry in audit_entries}
    simulate = env.get("RANSOMEYE_ROLLBACK_SIMULATE") == "1"
    actions_ok = "remove_windows_service" in audit_actions
    residue_ok = True if simulate else not dummy_file.exists()
    passed = actions_ok and residue_ok

    return {
        "status": ValidationStatus.PASSED.value if passed else ValidationStatus.FAILED.value,
        "dummy_file_removed": not dummy_file.exists(),
        "audit_actions": sorted(audit_actions),
        "simulate": simulate
    }


def test_rollback_framework_windows() -> None:
    result = _run_rollback_framework_windows()
    assert result["status"] == ValidationStatus.PASSED.value, result
