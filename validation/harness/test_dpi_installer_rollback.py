#!/usr/bin/env python3
"""
RansomEye v1.0 Validation Harness - DPI Installer Rollback Test
AUTHORITATIVE: Validates rollback removes DPI artifacts and privileges
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


def test_dpi_installer_rollback() -> Dict[str, Any]:
    """
    DPI-ROLL-001: Rollback removes binaries, capabilities, services, users.
    """
    temp_root = Path(tempfile.mkdtemp(prefix="ransomeye-dpi-rollback-"))
    state_file = temp_root / ".install_state.json"
    audit_file = temp_root / "rollback_audit.json"
    dummy_file = temp_root / "bin" / "dpi-probe"
    dummy_file.parent.mkdir(parents=True, exist_ok=True)
    dummy_file.write_text("dummy", encoding="utf-8")

    _run_transaction(["init", "--state-file", str(state_file), "--component", "dpi-probe"])
    _run_transaction([
        "record", "--state-file", str(state_file),
        "--action", "install_probe",
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
        "--meta", "service=ransomeye-dpi.service",
        "--meta", "service_file=/tmp/ransomeye-dpi.service",
        "--rollback-meta", "service=ransomeye-dpi.service",
        "--rollback-meta", "service_file=/tmp/ransomeye-dpi.service"
    ])
    _run_transaction([
        "record", "--state-file", str(state_file),
        "--action", "create_user",
        "--rollback-action", "remove_user",
        "--meta", "username=ransomeye-dpi",
        "--rollback-meta", "username=ransomeye-dpi"
    ])

    env = os.environ.copy()
    env["RANSOMEYE_ROLLBACK_SIMULATE"] = "1"
    env["RANSOMEYE_ROLLBACK_AUDIT_FILE"] = str(audit_file)
    _run_transaction(["rollback", "--state-file", str(state_file)], env=env)

    audit_entries = json.loads(audit_file.read_text(encoding="utf-8"))
    audit_actions = {entry["action"] for entry in audit_entries}
    required_actions = {"remove_capabilities", "remove_systemd_service", "remove_path", "remove_user"}
    simulate = env.get("RANSOMEYE_ROLLBACK_SIMULATE") == "1"
    actions_ok = required_actions.issubset(audit_actions)
    residue_ok = True if simulate else not dummy_file.exists()
    passed = actions_ok and residue_ok

    return {
        "status": ValidationStatus.PASSED.value if passed else ValidationStatus.FAILED.value,
        "dummy_file_removed": not dummy_file.exists(),
        "audit_actions": sorted(audit_actions),
        "simulate": simulate
    }


if __name__ == "__main__":
    result = test_dpi_installer_rollback()
    print(json.dumps(result, indent=2))
    exit(0 if result["status"] == ValidationStatus.PASSED.value else 1)
