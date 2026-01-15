import json
import os
from pathlib import Path

from installer.common.install_transaction import init_state, record_step, rollback


def test_installer_rollback_on_failure(tmp_path):
    state_file = tmp_path / "installer_state.json"
    audit_file = tmp_path / "rollback_audit.json"

    os.environ["RANSOMEYE_ROLLBACK_SIMULATE"] = "1"
    os.environ["RANSOMEYE_ROLLBACK_AUDIT_FILE"] = str(audit_file)

    init_state(state_file, component="dpi-probe")
    record_step(
        state_file,
        action="create_path",
        meta={"path": str(tmp_path / "payload")},
        rollback_action="remove_path",
        rollback_meta={"path": str(tmp_path / "payload")},
    )

    exit_code = rollback(state_file)
    assert exit_code == 0

    audit_entries = json.loads(audit_file.read_text(encoding="utf-8"))
    assert len(audit_entries) == 1
    assert audit_entries[0]["action"] == "remove_path"
