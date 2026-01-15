import json
import os
from pathlib import Path

from installer.common.install_transaction import init_state, record_step, rollback


def test_install_transaction_records_and_rolls_back(tmp_path):
    state_file = tmp_path / "state.json"
    audit_file = tmp_path / "audit.json"
    os.environ["RANSOMEYE_ROLLBACK_SIMULATE"] = "1"
    os.environ["RANSOMEYE_ROLLBACK_AUDIT_FILE"] = str(audit_file)

    init_state(state_file, component="core")
    record_step(
        state_file,
        action="create_path",
        meta={"path": "/tmp/example"},
        rollback_action="remove_path",
        rollback_meta={"path": "/tmp/example"},
    )
    exit_code = rollback(state_file)
    assert exit_code == 0

    entries = json.loads(audit_file.read_text(encoding="utf-8"))
    assert entries[0]["action"] == "remove_path"
