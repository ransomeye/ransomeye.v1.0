"""
FAMILY-5: Core Runtime Invariant Tests
Tests for runtime invariant checking logic.
"""
import os
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault(
    "RANSOMEYE_EVENT_ENVELOPE_SCHEMA_PATH",
    str(_REPO_ROOT / "contracts" / "event-envelope.schema.json"),
)
os.environ.setdefault("RANSOMEYE_LOG_DIR", "/tmp")
os.environ.setdefault("RANSOMEYE_DB_PASSWORD", "bootstrap-password-12345")
os.environ.setdefault("RANSOMEYE_DB_USER", "bootstrap_user")
os.environ.setdefault(
    "RANSOMEYE_COMMAND_SIGNING_KEY",
    "bootstrap-signing-key-1234567890-abcdef-XYZ-9876543210",
)

from core import runtime


class _FakeCursor:
    def __init__(self, fetchone_values=None, fetchall_values=None, execute_error=None):
        self._fetchone_values = list(fetchone_values or [])
        self._fetchall_values = list(fetchall_values or [])
        self._execute_error = execute_error

    def execute(self, *_a, **_k):
        if self._execute_error:
            raise self._execute_error

    def fetchone(self):
        if self._fetchone_values:
            return self._fetchone_values.pop(0)
        return None

    def fetchall(self):
        return list(self._fetchall_values)

    def close(self):
        return None


class _FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def close(self):
        return None


def _assert_hit_marker(capsys, marker):
    err = capsys.readouterr().err
    assert f"HIT_BRANCH: {marker}" in err


def test_invariant_missing_env_db_password(monkeypatch, capsys):
    """FAMILY-5: Test invariant check for missing DB_PASSWORD env var."""
    # Mock exit_fatal to raise RuntimeError instead of sys.exit
    def exit_as_runtime_error(msg, code=None):
        raise RuntimeError(msg)
    monkeypatch.setattr(runtime, "exit_fatal", exit_as_runtime_error)
    
    # Remove the env var
    original_value = os.environ.pop("RANSOMEYE_DB_PASSWORD", None)
    try:
        with pytest.raises(RuntimeError):
            runtime._invariant_check_missing_env('RANSOMEYE_DB_PASSWORD')
        _assert_hit_marker(capsys, "invariant_missing_env")
    finally:
        if original_value:
            os.environ["RANSOMEYE_DB_PASSWORD"] = original_value


def test_invariant_missing_env_db_user(monkeypatch, capsys):
    """FAMILY-5: Test invariant check for missing DB_USER env var."""
    # Mock exit_fatal to raise RuntimeError instead of sys.exit
    def exit_as_runtime_error(msg, code=None):
        raise RuntimeError(msg)
    monkeypatch.setattr(runtime, "exit_fatal", exit_as_runtime_error)
    
    # Remove the env var
    original_value = os.environ.pop("RANSOMEYE_DB_USER", None)
    try:
        with pytest.raises(RuntimeError):
            runtime._invariant_check_missing_env('RANSOMEYE_DB_USER')
        _assert_hit_marker(capsys, "invariant_missing_env")
    finally:
        if original_value:
            os.environ["RANSOMEYE_DB_USER"] = original_value


def test_invariant_missing_env_signing_key(monkeypatch, capsys):
    """FAMILY-5: Test invariant check for missing SIGNING_KEY env var."""
    # Mock exit_fatal to raise RuntimeError instead of sys.exit
    def exit_as_runtime_error(msg, code=None):
        raise RuntimeError(msg)
    monkeypatch.setattr(runtime, "exit_fatal", exit_as_runtime_error)
    
    # Remove the env var
    original_value = os.environ.pop("RANSOMEYE_COMMAND_SIGNING_KEY", None)
    try:
        with pytest.raises(RuntimeError):
            runtime._invariant_check_missing_env('RANSOMEYE_COMMAND_SIGNING_KEY')
        _assert_hit_marker(capsys, "invariant_missing_env")
    finally:
        if original_value:
            os.environ["RANSOMEYE_COMMAND_SIGNING_KEY"] = original_value


def test_invariant_db_connection_failure(monkeypatch, capsys):
    """FAMILY-5: Test invariant check for DB connection failure."""
    # Mock exit_fatal to raise RuntimeError instead of sys.exit
    def exit_as_runtime_error(msg, code=None):
        raise RuntimeError(msg)
    monkeypatch.setattr(runtime, "exit_fatal", exit_as_runtime_error)
    
    # Mock psycopg2.connect to fail
    def failing_connect(**_k):
        raise RuntimeError("Connection refused")
    monkeypatch.setattr(runtime.psycopg2, "connect", failing_connect)
    
    # Mock config.get to return test values
    class MockConfig:
        def get(self, key, default=None):
            defaults = {
                'RANSOMEYE_DB_HOST': 'localhost',
                'RANSOMEYE_DB_PORT': 5432,
                'RANSOMEYE_DB_NAME': 'ransomeye',
                'RANSOMEYE_DB_USER': 'test_user',
            }
            return defaults.get(key, default)
    monkeypatch.setattr(runtime, "config", MockConfig())
    
    # Mock config_loader.get_secret to return password
    if hasattr(runtime, 'config_loader'):
        monkeypatch.setattr(runtime.config_loader, "get_secret", lambda *_a, **_k: "test-password")
    
    with pytest.raises(RuntimeError):
        runtime._invariant_check_db_connection()
    _assert_hit_marker(capsys, "invariant_db_connection_failure")


def test_invariant_schema_mismatch_missing_column(monkeypatch, capsys):
    """FAMILY-5: Test invariant check for schema mismatch - missing event_id column."""
    # Mock exit_fatal to raise RuntimeError instead of sys.exit
    def exit_as_runtime_error(msg, code=None):
        raise RuntimeError(msg)
    monkeypatch.setattr(runtime, "exit_fatal", exit_as_runtime_error)
    
    # Mock cursor to return None (column not found)
    cursor = _FakeCursor(fetchone_values=[None])
    conn = _FakeConn(cursor)
    
    # Mock psycopg2.connect to return fake connection
    monkeypatch.setattr(runtime.psycopg2, "connect", lambda **_k: conn)
    
    # Mock config.get to return test values
    class MockConfig:
        def get(self, key, default=None):
            defaults = {
                'RANSOMEYE_DB_HOST': 'localhost',
                'RANSOMEYE_DB_PORT': 5432,
                'RANSOMEYE_DB_NAME': 'ransomeye',
                'RANSOMEYE_DB_USER': 'test_user',
            }
            return defaults.get(key, default)
    monkeypatch.setattr(runtime, "config", MockConfig())
    
    # Mock config_loader.get_secret to return password
    if hasattr(runtime, 'config_loader'):
        monkeypatch.setattr(runtime.config_loader, "get_secret", lambda *_a, **_k: "test-password")
    
    with pytest.raises(RuntimeError):
        runtime._invariant_check_schema_mismatch()
    _assert_hit_marker(capsys, "invariant_schema_mismatch")


def test_invariant_schema_check_exception(monkeypatch, capsys):
    """FAMILY-5: Test invariant check for schema check exception."""
    # Mock exit_fatal to raise RuntimeError instead of sys.exit
    def exit_as_runtime_error(msg, code=None):
        raise RuntimeError(msg)
    monkeypatch.setattr(runtime, "exit_fatal", exit_as_runtime_error)
    
    # Mock psycopg2.connect to raise an exception
    def failing_connect(**_k):
        raise RuntimeError("Database query failed")
    monkeypatch.setattr(runtime.psycopg2, "connect", failing_connect)
    
    # Mock config.get to return test values
    class MockConfig:
        def get(self, key, default=None):
            defaults = {
                'RANSOMEYE_DB_HOST': 'localhost',
                'RANSOMEYE_DB_PORT': 5432,
                'RANSOMEYE_DB_NAME': 'ransomeye',
                'RANSOMEYE_DB_USER': 'test_user',
            }
            return defaults.get(key, default)
    monkeypatch.setattr(runtime, "config", MockConfig())
    
    # Mock config_loader.get_secret to return password
    if hasattr(runtime, 'config_loader'):
        monkeypatch.setattr(runtime.config_loader, "get_secret", lambda *_a, **_k: "test-password")
    
    with pytest.raises(RuntimeError):
        runtime._invariant_check_schema_mismatch()
    _assert_hit_marker(capsys, "invariant_schema_check_exception")


def test_invariant_unauthorized_write(monkeypatch, capsys):
    """FAMILY-5: Test invariant check for unauthorized write by UI component."""
    # Mock exit_fatal to raise RuntimeError instead of sys.exit
    def exit_as_runtime_error(msg, code=None):
        raise RuntimeError(msg)
    monkeypatch.setattr(runtime, "exit_fatal", exit_as_runtime_error)
    
    with pytest.raises(RuntimeError):
        runtime._invariant_check_unauthorized_write('ui', 'write')
    _assert_hit_marker(capsys, "invariant_unauthorized_write")


def test_invariant_duplicate_incident(monkeypatch, capsys):
    """FAMILY-5: Test invariant check for duplicate incident creation."""
    # Mock exit_fatal to raise RuntimeError instead of sys.exit
    def exit_as_runtime_error(msg, code=None):
        raise RuntimeError(msg)
    monkeypatch.setattr(runtime, "exit_fatal", exit_as_runtime_error)
    
    # Mock cursor to return count > 0 (duplicate found)
    cursor = _FakeCursor(fetchone_values=[(1,)])  # Count = 1
    conn = _FakeConn(cursor)
    
    with pytest.raises(RuntimeError):
        runtime._invariant_check_duplicate_incident(conn, "test-event-id-123")
    _assert_hit_marker(capsys, "invariant_duplicate_incident")
