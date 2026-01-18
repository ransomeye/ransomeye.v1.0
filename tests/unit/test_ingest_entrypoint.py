import importlib
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


def _load_ingest(tmp_path, monkeypatch):
    project_root = Path(__file__).resolve().parents[2]
    env = {
        "RANSOMEYE_DB_PASSWORD": "test-password-12345",
        "RANSOMEYE_DB_USER": "test_user",
        "RANSOMEYE_EVENT_ENVELOPE_SCHEMA_PATH": str(
            project_root / "contracts" / "event-envelope.schema.json"
        ),
        "RANSOMEYE_LOG_DIR": str(tmp_path / "logs"),
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return importlib.import_module("services.ingest.app.main")


def _build_envelope(ingest):
    now = datetime.now(timezone.utc).isoformat()
    envelope = {
        "event_id": str(uuid.uuid4()),
        "machine_id": "machine-1",
        "component": "linux_agent",
        "component_instance_id": "component-1",
        "observed_at": now,
        "ingested_at": now,
        "sequence": 1,
        "payload": {"event_type": "PROCESS_EXECUTION"},
        "identity": {
            "hostname": "host-1",
            "boot_id": "boot-1",
            "agent_version": "1.0.0",
        },
        "integrity": {
            "hash_sha256": "",
            "prev_hash_sha256": None,
        },
    }
    envelope["integrity"]["hash_sha256"] = ingest.compute_hash(envelope)
    return envelope


def test_run_ingest_once_valid_envelope(tmp_path, monkeypatch):
    ingest = _load_ingest(tmp_path, monkeypatch)
    envelope = _build_envelope(ingest)
    called = {"stored": False}

    def _store(conn, env, status, late_arrival, latency):
        called["stored"] = True

    assert ingest.run_ingest_once(
        envelope,
        allow_unverified=True,
        store_fn=_store,
        duplicate_check=lambda *_: False,
        db_conn=object(),
    )
    assert called["stored"] is True


def test_run_ingest_once_invalid_signature(tmp_path, monkeypatch):
    ingest = _load_ingest(tmp_path, monkeypatch)
    envelope = _build_envelope(ingest)

    class _Verifier:
        def verify_envelope(self, _env):
            return False, "bad_signature"

    with pytest.raises(ValueError, match="SIGNATURE_VERIFICATION_FAILED"):
        ingest.run_ingest_once(
            envelope,
            verifier=_Verifier(),
            allow_unverified=False,
            store_fn=lambda *_: True,
            duplicate_check=lambda *_: False,
            db_conn=object(),
        )


def test_run_ingest_once_component_identity_failure(tmp_path, monkeypatch):
    ingest = _load_ingest(tmp_path, monkeypatch)
    envelope = _build_envelope(ingest)

    class _Verifier:
        def verify_envelope(self, _env):
            return True, None

        def verify_component_identity(self, _env):
            return False, "unknown_key"

    with pytest.raises(ValueError, match="COMPONENT_IDENTITY_VERIFICATION_FAILED"):
        ingest.run_ingest_once(
            envelope,
            verifier=_Verifier(),
            allow_unverified=False,
            store_fn=lambda *_: True,
            duplicate_check=lambda *_: False,
            db_conn=object(),
        )


def test_run_ingest_once_schema_violation(tmp_path, monkeypatch):
    ingest = _load_ingest(tmp_path, monkeypatch)
    envelope = _build_envelope(ingest)
    envelope.pop("machine_id", None)

    with pytest.raises(ValueError, match="SCHEMA_VALIDATION_FAILED"):
        ingest.run_ingest_once(
            envelope,
            allow_unverified=True,
            store_fn=lambda *_: True,
            duplicate_check=lambda *_: False,
            db_conn=object(),
        )


def test_run_ingest_once_timestamp_parse_error(tmp_path, monkeypatch):
    ingest = _load_ingest(tmp_path, monkeypatch)
    envelope = _build_envelope(ingest)
    envelope["observed_at"] = "not-a-timestamp"
    envelope["integrity"]["hash_sha256"] = ingest.compute_hash(envelope)

    with pytest.raises(ValueError, match="TIMESTAMP_VALIDATION_FAILED"):
        ingest.run_ingest_once(
            envelope,
            allow_unverified=True,
            store_fn=lambda *_: True,
            duplicate_check=lambda *_: False,
            db_conn=object(),
        )


def test_run_ingest_once_timestamp_future_beyond_tolerance(tmp_path, monkeypatch, capsys):
    ingest = _load_ingest(tmp_path, monkeypatch)
    envelope = _build_envelope(ingest)
    base = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    envelope["observed_at"] = (base + timedelta(seconds=10)).isoformat()
    envelope["ingested_at"] = base.isoformat()
    envelope["integrity"]["hash_sha256"] = ingest.compute_hash(envelope)
    called = {"stored": False}

    with pytest.raises(ValueError, match="TIMESTAMP_VALIDATION_FAILED"):
        ingest.run_ingest_once(
            envelope,
            allow_unverified=True,
            store_fn=lambda *_: called.update(stored=True),
            duplicate_check=lambda *_: False,
            db_conn=object(),
        )
    captured = capsys.readouterr()
    assert "HIT_BRANCH: timestamp_future" in captured.err
    assert called["stored"] is False


def test_run_ingest_once_timestamp_too_old(tmp_path, monkeypatch, capsys):
    ingest = _load_ingest(tmp_path, monkeypatch)
    envelope = _build_envelope(ingest)
    base = datetime(2025, 1, 31, 0, 0, 0, tzinfo=timezone.utc)
    envelope["observed_at"] = (base - timedelta(days=31)).isoformat()
    envelope["ingested_at"] = base.isoformat()
    envelope["integrity"]["hash_sha256"] = ingest.compute_hash(envelope)
    called = {"stored": False}

    with pytest.raises(ValueError, match="TIMESTAMP_VALIDATION_FAILED"):
        ingest.run_ingest_once(
            envelope,
            allow_unverified=True,
            store_fn=lambda *_: called.update(stored=True),
            duplicate_check=lambda *_: False,
            db_conn=object(),
        )
    captured = capsys.readouterr()
    assert "HIT_BRANCH: timestamp_too_old" in captured.err
    assert called["stored"] is False


def test_run_ingest_once_duplicate_event(tmp_path, monkeypatch):
    ingest = _load_ingest(tmp_path, monkeypatch)
    envelope = _build_envelope(ingest)

    with pytest.raises(ValueError, match="DUPLICATE_EVENT"):
        ingest.run_ingest_once(
            envelope,
            allow_unverified=True,
            store_fn=lambda *_: True,
            duplicate_check=lambda *_: True,
            db_conn=object(),
        )


def test_run_ingest_once_hash_mismatch(tmp_path, monkeypatch):
    ingest = _load_ingest(tmp_path, monkeypatch)
    envelope = _build_envelope(ingest)
    envelope["integrity"]["hash_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="HASH_MISMATCH"):
        ingest.run_ingest_once(
            envelope,
            allow_unverified=True,
            store_fn=lambda *_: True,
            duplicate_check=lambda *_: False,
            db_conn=object(),
        )


def test_run_ingest_once_idempotency_violation(tmp_path, monkeypatch, capsys):
    ingest = _load_ingest(tmp_path, monkeypatch)
    envelope = _build_envelope(ingest)

    class _Cursor:
        def __init__(self):
            self.executes = 0
        def execute(self, *_a, **_k):
            self.executes += 1
        def close(self):
            return None

    class _Conn:
        def __init__(self):
            self.cursor_obj = _Cursor()
        def cursor(self):
            return self.cursor_obj

    conn = _Conn()
    monkeypatch.setattr(ingest, "_common_integrity_available", True)
    monkeypatch.setattr(ingest, "verify_hash_chain_continuity", lambda *_: (True, None))
    monkeypatch.setattr(ingest, "verify_sequence_monotonicity", lambda *_: (True, None))
    monkeypatch.setattr(ingest, "verify_idempotency", lambda *_: False)
    monkeypatch.setattr(ingest, "_common_db_safety_available", False)
    monkeypatch.setattr(ingest, "begin_transaction", lambda *_: None)
    monkeypatch.setattr(ingest, "commit_transaction", lambda *_: None)
    monkeypatch.setattr(ingest, "rollback_transaction", lambda *_: None)

    with pytest.raises(ValueError, match="duplicate"):
        ingest.run_ingest_once(
            envelope,
            allow_unverified=True,
            store_fn=ingest.store_event,
            duplicate_check=lambda *_: False,
            db_conn=conn,
        )
    captured = capsys.readouterr()
    assert "HIT_BRANCH: idempotency_violation" in captured.err
    assert conn.cursor_obj.executes == 0


def test_run_ingest_once_prev_hash_mismatch(tmp_path, monkeypatch):
    ingest = _load_ingest(tmp_path, monkeypatch)
    envelope = _build_envelope(ingest)

    class _Cursor:
        def close(self):
            return None

    class _Conn:
        def cursor(self):
            return _Cursor()

    monkeypatch.setattr(ingest, "_common_integrity_available", True)
    monkeypatch.setattr(ingest, "verify_hash_chain_continuity", lambda *_: (False, "prev_hash"))
    monkeypatch.setattr(ingest, "verify_sequence_monotonicity", lambda *_: (True, None))
    monkeypatch.setattr(ingest, "verify_idempotency", lambda *_: True)
    monkeypatch.setattr(ingest, "_common_db_safety_available", False)
    monkeypatch.setattr(ingest, "begin_transaction", lambda *_: None)
    monkeypatch.setattr(ingest, "commit_transaction", lambda *_: None)
    monkeypatch.setattr(ingest, "rollback_transaction", lambda *_: None)

    with pytest.raises(ValueError, match="Hash chain continuity violation"):
        ingest.run_ingest_once(
            envelope,
            allow_unverified=True,
            store_fn=ingest.store_event,
            duplicate_check=lambda *_: False,
            db_conn=_Conn(),
        )


def test_run_ingest_once_sequence_violation(tmp_path, monkeypatch):
    ingest = _load_ingest(tmp_path, monkeypatch)
    envelope = _build_envelope(ingest)

    class _Cursor:
        def close(self):
            return None

    class _Conn:
        def cursor(self):
            return _Cursor()

    monkeypatch.setattr(ingest, "_common_integrity_available", True)
    monkeypatch.setattr(ingest, "verify_sequence_monotonicity", lambda *_: (False, "replay"))
    monkeypatch.setattr(ingest, "verify_hash_chain_continuity", lambda *_: (True, None))
    monkeypatch.setattr(ingest, "verify_idempotency", lambda *_: True)
    monkeypatch.setattr(ingest, "_common_db_safety_available", False)
    monkeypatch.setattr(ingest, "begin_transaction", lambda *_: None)
    monkeypatch.setattr(ingest, "commit_transaction", lambda *_: None)
    monkeypatch.setattr(ingest, "rollback_transaction", lambda *_: None)

    with pytest.raises(ValueError, match="Sequence monotonicity violation"):
        ingest.run_ingest_once(
            envelope,
            allow_unverified=True,
            store_fn=ingest.store_event,
            duplicate_check=lambda *_: False,
            db_conn=_Conn(),
        )


def test_run_ingest_once_db_write_failure(tmp_path, monkeypatch):
    ingest = _load_ingest(tmp_path, monkeypatch)
    envelope = _build_envelope(ingest)

    class _Cursor:
        def execute(self, *_args, **_kwargs):
            raise RuntimeError("db write failed")

        def close(self):
            return None

    class _Conn:
        def cursor(self):
            return _Cursor()

    monkeypatch.setattr(ingest, "_common_integrity_available", True)
    monkeypatch.setattr(ingest, "verify_sequence_monotonicity", lambda *_: (True, None))
    monkeypatch.setattr(ingest, "verify_hash_chain_continuity", lambda *_: (True, None))
    monkeypatch.setattr(ingest, "verify_idempotency", lambda *_: True)
    monkeypatch.setattr(ingest, "_common_db_safety_available", False)
    monkeypatch.setattr(ingest, "begin_transaction", lambda *_: None)
    monkeypatch.setattr(ingest, "commit_transaction", lambda *_: None)
    monkeypatch.setattr(ingest, "rollback_transaction", lambda *_: None)

    with pytest.raises(RuntimeError, match="db write failed"):
        ingest.run_ingest_once(
            envelope,
            allow_unverified=True,
            store_fn=ingest.store_event,
            duplicate_check=lambda *_: False,
            db_conn=_Conn(),
        )
