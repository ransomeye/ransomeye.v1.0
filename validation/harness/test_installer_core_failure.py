#!/usr/bin/env python3
"""
RansomEye v1.0 Validation Harness - Installer/Core Failure Integration
AUTHORITATIVE: Phase 2 rollback trigger validation
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Any

from validation.harness.phase_c_executor import ValidationStatus


def test_installer_rollback_on_core_fail() -> Dict[str, Any]:
    """
    ORCH-007: Installer rollback triggered on Core FAILED status.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="ransomeye-installer-core-fail-"))
    status_path = temp_dir / "core_status.json"
    state_file = temp_dir / ".install_state.json"
    audit_file = temp_dir / "rollback_audit.json"

    status = {
        "schema_version": "1.0",
        "state": "FAILED",
        "timestamp": "2026-01-01T00:00:00Z",
        "global_state": "FAILED",
        "failure_reason_code": "HEALTH_FAILED",
        "failure_reason": "Injected failure",
        "security_events": [],
        "components": {
            "ingest": {
                "state": "FAILED",
                "pid": 123,
                "last_health": False,
                "last_error": "Injected",
                "started_at": "2026-01-01T00:00:00Z",
                "last_successful_cycle": None,
                "failure_reason": "Injected"
            }
        },
        "start_order": ["ingest"],
        "core_pid": 1,
        "core_token": "00000000-0000-4000-8000-000000000000"
    }
    status_path.write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")

    from installer.common.install_transaction import init_state, record_step, rollback
    init_state(state_file, "core")
    record_step(
        state_file,
        "create_file",
        {"path": str(temp_dir / "dummy")},
        "remove_path",
        {"path": str(temp_dir / "dummy")}
    )
    (temp_dir / "dummy").write_text("x", encoding="utf-8")

    os.environ["RANSOMEYE_ROLLBACK_SIMULATE"] = "1"
    os.environ["RANSOMEYE_ROLLBACK_AUDIT_FILE"] = str(audit_file)
    rollback_exit = rollback(state_file)

    audit_entries = json.loads(audit_file.read_text(encoding="utf-8"))
    audit_actions = {entry["action"] for entry in audit_entries}
    passed = rollback_exit == 0 and "remove_path" in audit_actions

    return {
        "status": ValidationStatus.PASSED.value if passed else ValidationStatus.FAILED.value,
        "rollback_exit": rollback_exit,
        "audit_actions": sorted(audit_actions)
    }
