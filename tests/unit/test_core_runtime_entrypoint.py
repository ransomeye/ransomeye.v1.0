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
from core.orchestrator import ComponentSpec, ComponentState, CoreOrchestrator


class _Logger:
    def startup(self, *_a, **_k): pass
    def shutdown(self, *_a, **_k): pass
    def info(self, *_a, **_k): pass
    def warning(self, *_a, **_k): pass
    def error(self, *_a, **_k): pass
    def fatal(self, *_a, **_k): pass
    def config_error(self, *_a, **_k): pass
    def db_error(self, *_a, **_k): pass


class _Shutdown:
    def is_shutdown_requested(self): return False


def _base_env():
    return {
        "RANSOMEYE_DB_PASSWORD": "valid-password-12345",
        "RANSOMEYE_DB_USER": "valid_user",
        "RANSOMEYE_COMMAND_SIGNING_KEY": "signing-key-1234567890-abcdef-XYZ-9876543210",
        "RANSOMEYE_EVENT_ENVELOPE_SCHEMA_PATH": str(_REPO_ROOT / "contracts" / "event-envelope.schema.json"),
        "RANSOMEYE_LOG_DIR": "/tmp",
    }


def _env_with(**overrides):
    env = _base_env()
    env.update(overrides)
    return env


def _assert_hit_marker(capsys, marker):
    err = capsys.readouterr().err
    assert f"HIT_BRANCH: {marker}" in err


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


def test_run_startup_sequence_config_loader_exception(monkeypatch, capsys):
    env = _env_with()
    def _raise():
        raise runtime.ConfigError("boom")
    monkeypatch.setattr(runtime.config_loader, "load", _raise)
    with pytest.raises(runtime.ConfigError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "config_loader_exception")


def test_run_startup_sequence_missing_env_db_password(monkeypatch, capsys):
    env = _env_with()
    env["RANSOMEYE_DB_PASSWORD"] = ""
    monkeypatch.setattr(runtime.config_loader, "load", lambda: {})
    monkeypatch.setattr(runtime, "_core_startup_validation", lambda: runtime._validate_environment())
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "missing_env_db_password")


def test_run_startup_sequence_missing_env_db_user(monkeypatch, capsys):
    env = _env_with()
    env["RANSOMEYE_DB_USER"] = ""
    monkeypatch.setattr(runtime, "_core_startup_validation", lambda: runtime._validate_environment())
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "missing_env_db_user")


def test_run_startup_sequence_missing_env_signing_key(monkeypatch, capsys):
    env = _env_with()
    env["RANSOMEYE_COMMAND_SIGNING_KEY"] = ""
    monkeypatch.setattr(runtime, "_core_startup_validation", lambda: runtime._validate_environment())
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "signing_key_missing")


def test_run_startup_sequence_db_user_too_short(monkeypatch, capsys):
    env = _env_with(RANSOMEYE_DB_USER="ab")
    monkeypatch.setattr(runtime, "_core_startup_validation", lambda: runtime._validate_environment())
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "db_user_too_short")


def test_run_startup_sequence_weak_db_user(monkeypatch, capsys):
    env = _env_with(RANSOMEYE_DB_USER="admin")
    monkeypatch.setattr(runtime, "_core_startup_validation", lambda: runtime._validate_environment())
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "weak_db_user")


def test_run_startup_sequence_db_password_too_short(monkeypatch, capsys):
    env = _env_with(RANSOMEYE_DB_PASSWORD="short")
    monkeypatch.setattr(runtime.config_loader, "load", lambda: {})
    monkeypatch.setattr(runtime, "_core_startup_validation", lambda: runtime._validate_environment())
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "db_password_too_short")


def test_run_startup_sequence_db_password_weak(monkeypatch, capsys):
    env = _env_with(RANSOMEYE_DB_PASSWORD="aaaaaaaa")
    monkeypatch.setattr(runtime.config_loader, "load", lambda: {})
    monkeypatch.setattr(runtime, "_core_startup_validation", lambda: runtime._validate_environment())
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "db_password_weak")


def test_run_startup_sequence_signing_key_too_short(monkeypatch, capsys):
    env = _env_with(RANSOMEYE_COMMAND_SIGNING_KEY="short-signing-key")
    monkeypatch.setattr(runtime, "_core_startup_validation", lambda: runtime._validate_environment())
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "signing_key_too_short")


def test_run_startup_sequence_signing_key_weak(monkeypatch, capsys):
    env = _env_with(RANSOMEYE_COMMAND_SIGNING_KEY="default-signing-key-1234567890-abcdef-XYZ")
    monkeypatch.setattr(runtime, "_core_startup_validation", lambda: runtime._validate_environment())
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "signing_key_weak")


def test_run_startup_sequence_signing_key_weak_pattern_startup_validation(monkeypatch, capsys):
    env = _env_with(RANSOMEYE_COMMAND_SIGNING_KEY="weak-password-key-1234567890-abcdef-XYZ")
    import types
    monkeypatch.setitem(
        sys.modules,
        "core.diagnostics.db_bootstrap_validator",
        types.SimpleNamespace(validate_db_bootstrap=lambda **_k: None),
    )
    monkeypatch.setattr(runtime, "_validate_environment", lambda: None)
    monkeypatch.setattr(runtime, "_validate_db_connectivity", lambda: None)
    monkeypatch.setattr(runtime, "_validate_schema_version", lambda: None)
    monkeypatch.setattr(runtime, "_validate_schema_presence", lambda: None)
    monkeypatch.setattr(runtime, "_validate_write_permissions", lambda: None)
    monkeypatch.setattr(runtime, "_validate_filesystem_edges", lambda: None)
    monkeypatch.setattr(runtime, "_validate_readonly_enforcement", lambda: None)
    monkeypatch.setattr(runtime, "_invariant_check_missing_env", lambda *_a, **_k: None)
    monkeypatch.setattr(runtime, "_invariant_check_db_connection", lambda: None)
    monkeypatch.setattr(runtime, "_invariant_check_schema_mismatch", lambda: None)
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "signing_key_weak_pattern")


def test_run_startup_sequence_bootstrap_import_error(monkeypatch, capsys):
    env = _env_with()
    import builtins
    original_import = builtins.__import__
    def _import_guard(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "core.diagnostics.db_bootstrap_validator":
            raise ImportError("missing bootstrap validator")
        return original_import(name, globals, locals, fromlist, level)
    monkeypatch.setattr(builtins, "__import__", _import_guard)
    monkeypatch.setattr(runtime, "_validate_environment", lambda: None)
    monkeypatch.setattr(runtime, "_validate_db_connectivity", lambda: (_ for _ in ()).throw(RuntimeError("stop")))
    monkeypatch.setattr(runtime, "_validate_schema_version", lambda: None)
    monkeypatch.setattr(runtime, "_validate_schema_presence", lambda: None)
    monkeypatch.setattr(runtime, "_validate_write_permissions", lambda: None)
    monkeypatch.setattr(runtime, "_validate_filesystem_edges", lambda: None)
    monkeypatch.setattr(runtime, "_validate_readonly_enforcement", lambda: None)
    monkeypatch.setattr(runtime, "_invariant_check_missing_env", lambda *_a, **_k: None)
    monkeypatch.setattr(runtime, "_invariant_check_db_connection", lambda: None)
    monkeypatch.setattr(runtime, "_invariant_check_schema_mismatch", lambda: None)
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "bootstrap_import_error")


def test_run_startup_sequence_bootstrap_missing_db_user(monkeypatch, capsys):
    env = _env_with()
    monkeypatch.setattr(runtime.config_loader, "load", lambda: {"RANSOMEYE_DB_HOST": "localhost"})
    monkeypatch.setattr(runtime.config_loader, "get_secret", lambda *_a, **_k: "valid-password-12345")
    monkeypatch.setattr(runtime, "_validate_environment", lambda: None)
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "bootstrap_missing_db_user")


def test_run_startup_sequence_bootstrap_missing_db_password(monkeypatch, capsys):
    env = _env_with()
    monkeypatch.setattr(runtime.config_loader, "load", lambda: {"RANSOMEYE_DB_USER": "valid_user"})
    monkeypatch.setattr(runtime.config_loader, "get_secret", lambda *_a, **_k: None)
    monkeypatch.setattr(runtime, "_validate_environment", lambda: None)
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "bootstrap_missing_db_password")


def test_run_startup_sequence_bootstrap_validator_exception(monkeypatch, capsys):
    env = _env_with()
    import types
    monkeypatch.setitem(
        sys.modules,
        "core.diagnostics.db_bootstrap_validator",
        types.SimpleNamespace(validate_db_bootstrap=lambda **_k: (_ for _ in ()).throw(RuntimeError("boom"))),
    )
    monkeypatch.setattr(runtime, "_validate_environment", lambda: None)
    monkeypatch.setattr(runtime, "_validate_db_connectivity", lambda: None)
    monkeypatch.setattr(runtime, "_validate_schema_version", lambda: None)
    monkeypatch.setattr(runtime, "_validate_schema_presence", lambda: None)
    monkeypatch.setattr(runtime, "_validate_write_permissions", lambda: None)
    monkeypatch.setattr(runtime, "_validate_readonly_enforcement", lambda: None)
    monkeypatch.setattr(runtime, "_invariant_check_missing_env", lambda *_a, **_k: None)
    monkeypatch.setattr(runtime, "_invariant_check_db_connection", lambda: None)
    monkeypatch.setattr(runtime, "_invariant_check_schema_mismatch", lambda: None)
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "bootstrap_validator_exception")


def test_run_startup_sequence_db_connectivity_failure(monkeypatch, capsys):
    env = _env_with()
    import types
    monkeypatch.setitem(
        sys.modules,
        "core.diagnostics.db_bootstrap_validator",
        types.SimpleNamespace(validate_db_bootstrap=lambda **_k: None),
    )
    monkeypatch.setattr(runtime, "_validate_environment", lambda: None)
    monkeypatch.setattr(runtime.psycopg2, "connect", lambda **_k: (_ for _ in ()).throw(RuntimeError("db down")))
    monkeypatch.setattr(runtime, "_validate_schema_version", lambda: None)
    monkeypatch.setattr(runtime, "_validate_schema_presence", lambda: None)
    monkeypatch.setattr(runtime, "_validate_write_permissions", lambda: None)
    monkeypatch.setattr(runtime, "_validate_readonly_enforcement", lambda: None)
    monkeypatch.setattr(runtime, "_invariant_check_missing_env", lambda *_a, **_k: None)
    monkeypatch.setattr(runtime, "_invariant_check_db_connection", lambda: None)
    monkeypatch.setattr(runtime, "_invariant_check_schema_mismatch", lambda: None)
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "db_connectivity_failure")


def test_run_startup_sequence_migrations_dir_missing(monkeypatch, capsys):
    env = _env_with(RANSOMEYE_SCHEMA_MIGRATIONS_DIR="/tmp/ransomeye-missing-migrations")
    monkeypatch.setattr(runtime, "_core_startup_validation", lambda: runtime._validate_schema_version())
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "migrations_dir_missing")


def test_run_startup_sequence_migration_runner_missing(monkeypatch, capsys):
    env = _env_with(RANSOMEYE_SCHEMA_MIGRATIONS_DIR=str(_REPO_ROOT / "schemas" / "migrations"))
    import builtins
    original_import = builtins.__import__
    def _import_guard(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "common.db.migration_runner":
            raise ImportError("missing migration runner")
        return original_import(name, globals, locals, fromlist, level)
    monkeypatch.setattr(builtins, "__import__", _import_guard)
    monkeypatch.setattr(runtime, "_core_startup_validation", lambda: runtime._validate_schema_version())
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "migration_runner_missing")


def test_run_startup_sequence_no_migrations_found(monkeypatch, capsys):
    env = _env_with(RANSOMEYE_SCHEMA_MIGRATIONS_DIR=str(_REPO_ROOT / "schemas" / "migrations"))
    import types
    monkeypatch.setitem(
        sys.modules,
        "common.db.migration_runner",
        types.SimpleNamespace(get_latest_migration_version=lambda *_a, **_k: None),
    )
    monkeypatch.setattr(runtime, "_core_startup_validation", lambda: runtime._validate_schema_version())
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "no_migrations_found")


def test_run_startup_sequence_schema_migrations_missing(monkeypatch, capsys):
    env = _env_with(RANSOMEYE_SCHEMA_MIGRATIONS_DIR=str(_REPO_ROOT / "schemas" / "migrations"))
    import types
    monkeypatch.setitem(
        sys.modules,
        "common.db.migration_runner",
        types.SimpleNamespace(get_latest_migration_version=lambda *_a, **_k: "001"),
    )
    monkeypatch.setattr(runtime.config_loader, "get_secret", lambda *_a, **_k: "valid-password-12345")
    cursor = _FakeCursor(fetchone_values=[(None,)])
    monkeypatch.setattr(runtime.psycopg2, "connect", lambda **_k: _FakeConn(cursor))
    monkeypatch.setattr(runtime, "_core_startup_validation", lambda: runtime._validate_schema_version())
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "schema_migrations_missing")


def test_run_startup_sequence_no_schema_migrations_applied(monkeypatch, capsys):
    env = _env_with(RANSOMEYE_SCHEMA_MIGRATIONS_DIR=str(_REPO_ROOT / "schemas" / "migrations"))
    import types
    monkeypatch.setitem(
        sys.modules,
        "common.db.migration_runner",
        types.SimpleNamespace(get_latest_migration_version=lambda *_a, **_k: "001"),
    )
    monkeypatch.setattr(runtime.config_loader, "get_secret", lambda *_a, **_k: "valid-password-12345")
    cursor = _FakeCursor(fetchone_values=[("schema_migrations",), None])
    monkeypatch.setattr(runtime.psycopg2, "connect", lambda **_k: _FakeConn(cursor))
    monkeypatch.setattr(runtime, "_core_startup_validation", lambda: runtime._validate_schema_version())
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "no_schema_migrations_applied")


def test_run_startup_sequence_schema_version_mismatch(monkeypatch, capsys):
    env = _env_with(RANSOMEYE_SCHEMA_MIGRATIONS_DIR=str(_REPO_ROOT / "schemas" / "migrations"))
    import types
    monkeypatch.setitem(
        sys.modules,
        "common.db.migration_runner",
        types.SimpleNamespace(get_latest_migration_version=lambda *_a, **_k: "001"),
    )
    monkeypatch.setattr(runtime.config_loader, "get_secret", lambda *_a, **_k: "valid-password-12345")
    cursor = _FakeCursor(fetchone_values=[("schema_migrations",), ("002",)])
    monkeypatch.setattr(runtime.psycopg2, "connect", lambda **_k: _FakeConn(cursor))
    monkeypatch.setattr(runtime, "_core_startup_validation", lambda: runtime._validate_schema_version())
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "schema_version_mismatch")


def test_run_startup_sequence_schema_version_db_error(monkeypatch, capsys):
    env = _env_with(RANSOMEYE_SCHEMA_MIGRATIONS_DIR=str(_REPO_ROOT / "schemas" / "migrations"))
    import types
    monkeypatch.setitem(
        sys.modules,
        "common.db.migration_runner",
        types.SimpleNamespace(get_latest_migration_version=lambda *_a, **_k: "001"),
    )
    monkeypatch.setattr(runtime.psycopg2, "connect", lambda **_k: (_ for _ in ()).throw(RuntimeError("db down")))
    monkeypatch.setattr(runtime, "_core_startup_validation", lambda: runtime._validate_schema_version())
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "schema_version_db_error")


def test_run_startup_sequence_schema_required_tables_missing(monkeypatch, capsys):
    env = _env_with()
    monkeypatch.setattr(runtime.config_loader, "get_secret", lambda *_a, **_k: "valid-password-12345")
    cursor = _FakeCursor(fetchall_values=[("machines",), ("raw_events",)])
    monkeypatch.setattr(runtime.psycopg2, "connect", lambda **_k: _FakeConn(cursor))
    monkeypatch.setattr(runtime, "_core_startup_validation", lambda: runtime._validate_schema_presence())
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "schema_required_tables_missing")


def test_run_startup_sequence_schema_presence_db_error(monkeypatch, capsys):
    env = _env_with()
    monkeypatch.setattr(runtime.psycopg2, "connect", lambda **_k: (_ for _ in ()).throw(RuntimeError("db down")))
    monkeypatch.setattr(runtime, "_core_startup_validation", lambda: runtime._validate_schema_presence())
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)
    _assert_hit_marker(capsys, "schema_presence_db_error")

def test_run_startup_sequence_missing_env(monkeypatch):
    env = {
        "RANSOMEYE_DB_USER": "test_user",
        "RANSOMEYE_COMMAND_SIGNING_KEY": "x" * 40,
        "RANSOMEYE_EVENT_ENVELOPE_SCHEMA_PATH": "contracts/event-envelope.schema.json",
        "RANSOMEYE_LOG_DIR": "/tmp",
    }
    with pytest.raises(RuntimeError):
        runtime.run_startup_sequence(env=env)


def test_run_startup_sequence_db_unavailable(monkeypatch):
    env = {
        "RANSOMEYE_DB_PASSWORD": "test-password-12345",
        "RANSOMEYE_DB_USER": "test_user",
        "RANSOMEYE_COMMAND_SIGNING_KEY": "signing-key-1234567890-abcdef-XYZ-9876543210",
        "RANSOMEYE_EVENT_ENVELOPE_SCHEMA_PATH": "contracts/event-envelope.schema.json",
        "RANSOMEYE_LOG_DIR": "/tmp",
    }
    monkeypatch.setattr(runtime, "_validate_db_connectivity", lambda: (_ for _ in ()).throw(RuntimeError("db down")))
    monkeypatch.setattr(runtime, "_core_startup_validation", lambda: runtime._validate_db_connectivity())
    with pytest.raises(RuntimeError, match="db down"):
        runtime.run_startup_sequence(env=env)


def test_run_startup_sequence_schema_mismatch(monkeypatch):
    env = {
        "RANSOMEYE_DB_PASSWORD": "test-password-12345",
        "RANSOMEYE_DB_USER": "test_user",
        "RANSOMEYE_COMMAND_SIGNING_KEY": "signing-key-1234567890-abcdef-XYZ-9876543210",
        "RANSOMEYE_EVENT_ENVELOPE_SCHEMA_PATH": "contracts/event-envelope.schema.json",
        "RANSOMEYE_LOG_DIR": "/tmp",
    }
    monkeypatch.setattr(runtime, "_validate_schema_version", lambda: (_ for _ in ()).throw(RuntimeError("schema mismatch")))
    monkeypatch.setattr(runtime, "_core_startup_validation", lambda: runtime._validate_schema_version())
    with pytest.raises(RuntimeError, match="schema mismatch"):
        runtime.run_startup_sequence(env=env)


def test_orchestrator_component_crash_terminates(monkeypatch):
    monkeypatch.setenv("RANSOMEYE_CORE_STATUS_PATH", "/tmp/core_status.json")
    orch = CoreOrchestrator(_Logger(), _Shutdown())
    spec = ComponentSpec(
        name="ingest",
        dependencies=[],
        critical=True,
        health_mode="process",
        start_command=["/bin/true"],
    )
    adapter = orch.adapters.get("ingest") or None
    if adapter is None:
        from core.orchestrator import ComponentAdapter
        adapter = ComponentAdapter(spec, _Logger(), {}, stub_mode=True)
    adapter.health = lambda: False
    adapter.state = ComponentState.RUNNING
    orch.adapters = {"ingest": adapter}
    orch.specs = [spec]
    with pytest.raises(RuntimeError, match="Critical component unhealthy"):
        orch._supervise()


def test_policy_dir_create_failure(monkeypatch, capsys, tmp_path):
    """FAMILY-4: Test policy directory creation failure branch."""
    env = _env_with(
        RANSOMEYE_POLICY_DIR=str(tmp_path / "policy_missing" / "nested"),
        RANSOMEYE_LOG_DIR=str(tmp_path / "logs"),
    )
    # Mock exit_startup_error to raise RuntimeError instead of sys.exit
    def exit_as_runtime_error(msg):
        raise RuntimeError(msg)
    monkeypatch.setattr(runtime, "exit_startup_error", exit_as_runtime_error)
    # Replace config with a mock object that has a get method
    class MockConfig:
        def get(self, key, default=None):
            return env.get(key, default) if key in env else default
    monkeypatch.setattr(runtime, "config", MockConfig())
    # Mock mkdir to fail for policy dir
    original_mkdir = Path.mkdir
    def failing_mkdir(self, *args, **kwargs):
        if "policy" in str(self):
            raise PermissionError("Permission denied")
        return original_mkdir(self, *args, **kwargs)
    monkeypatch.setattr(Path, "mkdir", failing_mkdir)
    # Ensure policy dir doesn't exist
    policy_dir = Path(env["RANSOMEYE_POLICY_DIR"])
    if policy_dir.exists():
        import shutil
        shutil.rmtree(policy_dir, ignore_errors=True)
    with pytest.raises(RuntimeError):
        runtime._validate_write_permissions()
    _assert_hit_marker(capsys, "policy_dir_create_failure")


def test_policy_dir_not_writable(monkeypatch, capsys, tmp_path):
    """FAMILY-4: Test policy directory not writable branch."""
    env = _env_with(
        RANSOMEYE_POLICY_DIR=str(tmp_path / "policy_readonly"),
        RANSOMEYE_LOG_DIR=str(tmp_path / "logs"),
    )
    # Mock exit_startup_error to raise RuntimeError instead of sys.exit
    def exit_as_runtime_error(msg):
        raise RuntimeError(msg)
    monkeypatch.setattr(runtime, "exit_startup_error", exit_as_runtime_error)
    # Replace config with a mock object that has a get method
    class MockConfig:
        def get(self, key, default=None):
            return env.get(key, default) if key in env else default
    monkeypatch.setattr(runtime, "config", MockConfig())
    # Create policy dir but make it read-only
    policy_dir = Path(env["RANSOMEYE_POLICY_DIR"])
    policy_dir.mkdir(parents=True, exist_ok=True)
    policy_dir.chmod(0o555)  # Read-only
    # Mock os.access to return False for policy dir
    original_access = os.access
    def mock_access(path, mode):
        if str(path) == str(policy_dir) and mode == os.W_OK:
            return False
        return original_access(path, mode)
    monkeypatch.setattr(os, "access", mock_access)
    try:
        with pytest.raises(RuntimeError):
            runtime._validate_write_permissions()
        _assert_hit_marker(capsys, "policy_dir_not_writable")
    finally:
        policy_dir.chmod(0o755)


def test_log_dir_create_failure(monkeypatch, capsys, tmp_path):
    """FAMILY-4: Test log directory creation failure branch."""
    env = _env_with(
        RANSOMEYE_POLICY_DIR=str(tmp_path / "policy"),
        RANSOMEYE_LOG_DIR=str(tmp_path / "logs_missing" / "nested"),
    )
    # Mock exit_startup_error to raise RuntimeError instead of sys.exit
    def exit_as_runtime_error(msg):
        raise RuntimeError(msg)
    monkeypatch.setattr(runtime, "exit_startup_error", exit_as_runtime_error)
    # Replace config with a mock object that has a get method
    class MockConfig:
        def get(self, key, default=None):
            return env.get(key, default) if key in env else default
    monkeypatch.setattr(runtime, "config", MockConfig())
    # Create policy dir first (it should pass)
    policy_dir = Path(env["RANSOMEYE_POLICY_DIR"])
    policy_dir.mkdir(parents=True, exist_ok=True)
    # Mock mkdir to fail only for log dir
    original_mkdir = Path.mkdir
    def failing_mkdir(self, *args, **kwargs):
        if "logs" in str(self):
            raise OSError("Read-only file system")
        return original_mkdir(self, *args, **kwargs)
    monkeypatch.setattr(Path, "mkdir", failing_mkdir)
    # Ensure log dir doesn't exist
    log_dir = Path(env["RANSOMEYE_LOG_DIR"])
    if log_dir.exists():
        import shutil
        shutil.rmtree(log_dir, ignore_errors=True)
    with pytest.raises(RuntimeError):
        runtime._validate_write_permissions()
    _assert_hit_marker(capsys, "log_dir_create_failure")


def test_log_dir_not_writable(monkeypatch, capsys, tmp_path):
    """FAMILY-4: Test log directory not writable branch."""
    env = _env_with(
        RANSOMEYE_POLICY_DIR=str(tmp_path / "policy"),
        RANSOMEYE_LOG_DIR=str(tmp_path / "logs_readonly"),
    )
    # Mock exit_startup_error to raise RuntimeError instead of sys.exit
    def exit_as_runtime_error(msg):
        raise RuntimeError(msg)
    monkeypatch.setattr(runtime, "exit_startup_error", exit_as_runtime_error)
    # Replace config with a mock object that has a get method
    class MockConfig:
        def get(self, key, default=None):
            return env.get(key, default) if key in env else default
    monkeypatch.setattr(runtime, "config", MockConfig())
    # Create both dirs
    policy_dir = Path(env["RANSOMEYE_POLICY_DIR"])
    policy_dir.mkdir(parents=True, exist_ok=True)
    log_dir = Path(env["RANSOMEYE_LOG_DIR"])
    log_dir.mkdir(parents=True, exist_ok=True)
    log_dir.chmod(0o555)  # Read-only
    # Mock os.access to return False for log dir only
    original_access = os.access
    def mock_access(path, mode):
        if str(path) == str(log_dir) and mode == os.W_OK:
            return False
        return original_access(path, mode)
    monkeypatch.setattr(os, "access", mock_access)
    try:
        with pytest.raises(RuntimeError):
            runtime._validate_write_permissions()
        _assert_hit_marker(capsys, "log_dir_not_writable")
    finally:
        log_dir.chmod(0o755)


def test_write_permissions_exception(monkeypatch, capsys, tmp_path):
    """FAMILY-4: Test write permissions validation exception branch."""
    env = _env_with(
        RANSOMEYE_POLICY_DIR=str(tmp_path / "policy"),
        RANSOMEYE_LOG_DIR=str(tmp_path / "logs"),
    )
    # Mock exit_startup_error to raise RuntimeError instead of sys.exit
    def exit_as_runtime_error(msg):
        raise RuntimeError(msg)
    monkeypatch.setattr(runtime, "exit_startup_error", exit_as_runtime_error)
    # Replace config with a mock object that raises on get for POLICY_DIR
    class MockConfig:
        def get(self, key, default=None):
            if key == "RANSOMEYE_POLICY_DIR":
                raise RuntimeError("Unexpected filesystem error")
            return env.get(key, default) if key in env else default
    monkeypatch.setattr(runtime, "config", MockConfig())
    with pytest.raises(RuntimeError):
        runtime._validate_write_permissions()
    _assert_hit_marker(capsys, "write_permissions_exception")
