import importlib
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException


class _Request:
    def __init__(self, envelope):
        self._envelope = envelope

    async def json(self):
        return self._envelope


class _FakeCursor:
    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, _params=None):
        self._conn.state["executed"].append(query)

    def fetchone(self):
        if self._conn.fetch_queue:
            return self._conn.fetch_queue.pop(0)
        return None

    def close(self):
        return None


class _FakeConn:
    def __init__(self, fetch_queue=None):
        self.fetch_queue = list(fetch_queue or [])
        self.state = {"executed": []}
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return _FakeCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def _load_ingest(tmp_path, monkeypatch):
    project_root = Path(__file__).resolve().parents[2]
    env = {
        "RANSOMEYE_DB_PASSWORD": "test-password-12345",
        "RANSOMEYE_DB_USER": "test_user",
        "RANSOMEYE_EVENT_ENVELOPE_SCHEMA_PATH": str(
            project_root / "contracts" / "event-envelope.schema.json"
        ),
        "RANSOMEYE_LOG_DIR": str(tmp_path / "logs"),
        "CI": "true",
        "RANSOMEYE_ENV": "ci",
        "RANSOMEYE_ALLOW_UNAUTH_INGEST": "1",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    if "services.ingest.app.main" in sys.modules:
        return importlib.reload(sys.modules["services.ingest.app.main"])
    return importlib.import_module("services.ingest.app.main")


def _build_envelope(ingest, sequence=0, prev_hash=None):
    now = datetime.now(timezone.utc).isoformat()
    envelope = {
        "event_id": str(uuid.uuid4()),
        "machine_id": "machine-1",
        "component": "linux_agent",
        "component_instance_id": "component-1",
        "observed_at": now,
        "ingested_at": now,
        "sequence": sequence,
        "payload": {"event_type": "PROCESS_EXECUTION"},
        "identity": {
            "hostname": "host-1",
            "boot_id": "boot-1",
            "agent_version": "1.0.0",
        },
        "integrity": {
            "hash_sha256": "",
            "prev_hash_sha256": prev_hash,
        },
    }
    envelope["integrity"]["hash_sha256"] = ingest.compute_hash(envelope)
    return envelope


def _assert_audit_logged(conn):
    executed = "\n".join(conn.state["executed"]).lower()
    assert "insert into event_validation_log" in executed


def _assert_db_unchanged(conn):
    executed = "\n".join(conn.state["executed"]).lower()
    assert "insert into raw_events" not in executed
    assert "insert into machines" not in executed
    assert "insert into component_instances" not in executed


def _patch_db(ingest, monkeypatch, conn):
    monkeypatch.setattr(ingest, "get_db_connection", lambda: conn)
    monkeypatch.setattr(ingest, "put_db_connection", lambda _conn: None)
    monkeypatch.setattr(ingest, "_metrics_available", False)


def _patch_store_event_fallback(ingest, monkeypatch):
    monkeypatch.setattr(ingest, "_common_db_safety_available", False)
    monkeypatch.setattr(ingest, "begin_transaction", lambda *_: None)
    monkeypatch.setattr(ingest, "commit_transaction", lambda *_: None)
    monkeypatch.setattr(ingest, "rollback_transaction", lambda *_: None)


@pytest.mark.anyio
async def test_ingest_missing_sequence_field(tmp_path, monkeypatch, capsys):
    ingest = _load_ingest(tmp_path, monkeypatch)
    envelope = _build_envelope(ingest, sequence=1, prev_hash="a" * 64)
    envelope.pop("sequence", None)
    envelope["integrity"]["hash_sha256"] = ingest.compute_hash(envelope)
    conn = _FakeConn()
    _patch_db(ingest, monkeypatch, conn)

    with pytest.raises(HTTPException) as exc:
        await ingest.ingest_event(_Request(envelope))

    captured = capsys.readouterr()
    assert "HIT_BRANCH: sequence_missing" in captured.err
    assert exc.value.detail["error_code"] == "SCHEMA_VIOLATION"
    _assert_audit_logged(conn)
    _assert_db_unchanged(conn)


@pytest.mark.anyio
async def test_ingest_non_integer_sequence(tmp_path, monkeypatch, capsys):
    ingest = _load_ingest(tmp_path, monkeypatch)
    envelope = _build_envelope(ingest, sequence=0, prev_hash=None)
    envelope["sequence"] = "not-an-int"
    envelope["integrity"]["hash_sha256"] = ingest.compute_hash(envelope)
    conn = _FakeConn()
    _patch_db(ingest, monkeypatch, conn)

    with pytest.raises(HTTPException) as exc:
        await ingest.ingest_event(_Request(envelope))

    captured = capsys.readouterr()
    assert "HIT_BRANCH: sequence_non_integer" in captured.err
    assert exc.value.detail["error_code"] == "SCHEMA_VIOLATION"
    _assert_audit_logged(conn)
    _assert_db_unchanged(conn)


@pytest.mark.anyio
async def test_ingest_negative_sequence(tmp_path, monkeypatch, capsys):
    ingest = _load_ingest(tmp_path, monkeypatch)
    envelope = _build_envelope(ingest, sequence=-1, prev_hash=None)
    envelope["integrity"]["hash_sha256"] = ingest.compute_hash(envelope)
    conn = _FakeConn()
    _patch_db(ingest, monkeypatch, conn)

    with pytest.raises(HTTPException) as exc:
        await ingest.ingest_event(_Request(envelope))

    captured = capsys.readouterr()
    assert "HIT_BRANCH: sequence_negative" in captured.err
    assert exc.value.detail["error_code"] == "SCHEMA_VIOLATION"
    _assert_audit_logged(conn)
    _assert_db_unchanged(conn)


@pytest.mark.anyio
async def test_ingest_first_event_nonzero_sequence(tmp_path, monkeypatch, capsys):
    ingest = _load_ingest(tmp_path, monkeypatch)
    envelope = _build_envelope(ingest, sequence=5, prev_hash="b" * 64)
    conn = _FakeConn(fetch_queue=[None, (0,)])
    _patch_db(ingest, monkeypatch, conn)
    _patch_store_event_fallback(ingest, monkeypatch)
    monkeypatch.setattr(ingest, "check_duplicate", lambda *_: False)

    with pytest.raises(HTTPException) as exc:
        await ingest.ingest_event(_Request(envelope))

    captured = capsys.readouterr()
    assert "HIT_BRANCH: sequence_first_event_nonzero" in captured.err
    assert exc.value.detail["error_code"] == "INTEGRITY_VIOLATION"
    _assert_audit_logged(conn)
    _assert_db_unchanged(conn)


@pytest.mark.anyio
async def test_ingest_sequence_gap_jump_forward(tmp_path, monkeypatch, capsys):
    ingest = _load_ingest(tmp_path, monkeypatch)
    envelope = _build_envelope(ingest, sequence=2005, prev_hash="c" * 64)
    conn = _FakeConn(fetch_queue=[(0,)])
    _patch_db(ingest, monkeypatch, conn)
    _patch_store_event_fallback(ingest, monkeypatch)
    monkeypatch.setattr(ingest, "check_duplicate", lambda *_: False)
    monkeypatch.setattr(ingest, "verify_hash_chain_continuity", lambda *_: (True, None))

    with pytest.raises(HTTPException) as exc:
        await ingest.ingest_event(_Request(envelope))

    captured = capsys.readouterr()
    assert "HIT_BRANCH: sequence_gap" in captured.err
    assert exc.value.detail["error_code"] == "INTEGRITY_VIOLATION"
    _assert_audit_logged(conn)
    _assert_db_unchanged(conn)


@pytest.mark.anyio
async def test_ingest_prev_hash_present_no_prior_event(tmp_path, monkeypatch, capsys):
    ingest = _load_ingest(tmp_path, monkeypatch)
    envelope = _build_envelope(ingest, sequence=2, prev_hash="d" * 64)
    conn = _FakeConn(fetch_queue=[None, (2,)])
    _patch_db(ingest, monkeypatch, conn)
    _patch_store_event_fallback(ingest, monkeypatch)
    monkeypatch.setattr(ingest, "check_duplicate", lambda *_: False)

    with pytest.raises(HTTPException) as exc:
        await ingest.ingest_event(_Request(envelope))

    captured = capsys.readouterr()
    assert "HIT_BRANCH: prev_hash_no_prior_event" in captured.err
    assert exc.value.detail["error_code"] == "INTEGRITY_VIOLATION"
    _assert_audit_logged(conn)
    _assert_db_unchanged(conn)


@pytest.mark.anyio
async def test_ingest_prev_hash_incorrect_sequence_valid(tmp_path, monkeypatch, capsys):
    ingest = _load_ingest(tmp_path, monkeypatch)
    envelope = _build_envelope(ingest, sequence=2, prev_hash="e" * 64)
    conn = _FakeConn(fetch_queue=[("event-1", 1, "f" * 64)])
    _patch_db(ingest, monkeypatch, conn)
    _patch_store_event_fallback(ingest, monkeypatch)
    monkeypatch.setattr(ingest, "check_duplicate", lambda *_: False)

    with pytest.raises(HTTPException) as exc:
        await ingest.ingest_event(_Request(envelope))

    captured = capsys.readouterr()
    assert "HIT_BRANCH: prev_hash_incorrect" in captured.err
    assert exc.value.detail["error_code"] == "INTEGRITY_VIOLATION"
    _assert_audit_logged(conn)
    _assert_db_unchanged(conn)


@pytest.mark.anyio
async def test_ingest_duplicate_event_different_hash(tmp_path, monkeypatch, capsys):
    ingest = _load_ingest(tmp_path, monkeypatch)
    envelope = _build_envelope(ingest, sequence=1, prev_hash="a" * 64)
    conn = _FakeConn()
    _patch_db(ingest, monkeypatch, conn)
    monkeypatch.setattr(ingest, "check_duplicate", lambda *_: True)

    with pytest.raises(HTTPException) as exc:
        await ingest.ingest_event(_Request(envelope))

    captured = capsys.readouterr()
    assert "HIT_BRANCH: duplicate_event_id" in captured.err
    assert exc.value.detail["error_code"] == "DUPLICATE_EVENT_ID"
    _assert_audit_logged(conn)
    _assert_db_unchanged(conn)
