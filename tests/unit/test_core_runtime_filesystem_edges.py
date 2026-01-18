"""
GROUP E: Filesystem & Permission Edge Cases
Test file for filesystem edge case validation in Core Runtime.
"""
import os
import sys
import tempfile
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


def _assert_hit_marker(capsys, marker):
    """Assert that a HIT_BRANCH marker was written to stderr."""
    captured = capsys.readouterr()
    assert f"HIT_BRANCH: {marker}" in captured.err, f"Expected marker {marker} not found in stderr: {captured.err}"


def _base_env():
    """Base environment variables for tests."""
    return {
        "RANSOMEYE_DB_PASSWORD": "valid-password-12345",
        "RANSOMEYE_DB_USER": "valid_user",
        "RANSOMEYE_COMMAND_SIGNING_KEY": "signing-key-1234567890-abcdef-XYZ-9876543210",
        "RANSOMEYE_EVENT_ENVELOPE_SCHEMA_PATH": str(_REPO_ROOT / "contracts" / "event-envelope.schema.json"),
        "RANSOMEYE_LOG_DIR": "/tmp",
        "RANSOMEYE_POLICY_DIR": "/tmp/ransomeye/policy",
    }


def test_e1_log_dir_not_writable(monkeypatch, capsys, tmp_path):
    """E1: Test log directory not writable branch."""
    env = _base_env()
    env["RANSOMEYE_POLICY_DIR"] = str(tmp_path / "policy")
    env["RANSOMEYE_LOG_DIR"] = str(tmp_path / "logs_readonly")
    
    # Mock exit_startup_error to raise RuntimeError instead of sys.exit
    def exit_as_runtime_error(msg):
        raise RuntimeError(msg)
    monkeypatch.setattr(runtime, "exit_startup_error", exit_as_runtime_error)
    
    # Replace config with a mock object
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


def test_e2_runtime_dir_missing(monkeypatch, capsys, tmp_path):
    """E2: Test runtime/work directory missing branch."""
    env = _base_env()
    env["RANSOMEYE_RUN_DIR"] = str(tmp_path / "nonexistent_run_dir")
    
    # Mock exit_startup_error to raise RuntimeError instead of sys.exit
    def exit_as_runtime_error(msg):
        raise RuntimeError(msg)
    monkeypatch.setattr(runtime, "exit_startup_error", exit_as_runtime_error)
    
    # Ensure the directory does not exist
    run_dir = Path(env["RANSOMEYE_RUN_DIR"])
    if run_dir.exists():
        run_dir.rmdir()
    
    # Mock os.getenv to return our test env
    original_getenv = os.getenv
    def mock_getenv(key, default=None):
        return env.get(key, original_getenv(key, default))
    monkeypatch.setattr(os, "getenv", mock_getenv)
    
    with pytest.raises(RuntimeError):
        runtime._validate_filesystem_edges()
    _assert_hit_marker(capsys, "runtime_dir_missing")


def test_e3_temp_dir_readonly(monkeypatch, capsys, tmp_path):
    """E3: Test temp directory read-only branch."""
    env = _base_env()
    readonly_temp_dir = tmp_path / "temp_readonly"
    readonly_temp_dir.mkdir(parents=True, exist_ok=True)
    readonly_temp_dir.chmod(0o444)  # Read-only
    
    env["RANSOMEYE_RUN_DIR"] = str(tmp_path / "run_dir")
    env["RANSOMEYE_TMP_DIR"] = str(readonly_temp_dir)
    
    # Create run_dir (required for E2 check)
    Path(env["RANSOMEYE_RUN_DIR"]).mkdir(parents=True, exist_ok=True)
    
    # Mock exit_startup_error to raise RuntimeError instead of sys.exit
    def exit_as_runtime_error(msg):
        raise RuntimeError(msg)
    monkeypatch.setattr(runtime, "exit_startup_error", exit_as_runtime_error)
    
    # Mock os.getenv to return our test env
    original_getenv = os.getenv
    def mock_getenv(key, default=None):
        return env.get(key, original_getenv(key, default))
    monkeypatch.setattr(os, "getenv", mock_getenv)
    
    # Mock os.access to return False for temp dir
    original_access = os.access
    def mock_access(path, mode):
        if str(path) == str(readonly_temp_dir) and mode == os.W_OK:
            return False
        return original_access(path, mode)
    monkeypatch.setattr(os, "access", mock_access)
    
    try:
        with pytest.raises(RuntimeError):
            runtime._validate_filesystem_edges()
        _assert_hit_marker(capsys, "temp_dir_readonly")
    finally:
        readonly_temp_dir.chmod(0o755)


def test_e4_symlink_traversal_blocked(monkeypatch, capsys, tmp_path):
    """E4: Test symlink traversal blocked branch."""
    env = _base_env()
    
    # Create a symlink pointing to /etc (outside allowed roots like /tmp, /var/tmp, /opt, /var/run, /run)
    etc_symlink = tmp_path / "etc_symlink"
    try:
        etc_symlink.symlink_to("/etc")
        env["RANSOMEYE_RUN_DIR"] = str(etc_symlink)
        
        # Mock exit_startup_error to raise RuntimeError instead of sys.exit
        def exit_as_runtime_error(msg):
            raise RuntimeError(msg)
        monkeypatch.setattr(runtime, "exit_startup_error", exit_as_runtime_error)
        
        # Mock os.getenv to return our test env
        original_getenv = os.getenv
        def mock_getenv(key, default=None):
            return env.get(key, original_getenv(key, default))
        monkeypatch.setattr(os, "getenv", mock_getenv)
        
        with pytest.raises(RuntimeError):
            runtime._validate_filesystem_edges()
        _assert_hit_marker(capsys, "symlink_traversal_blocked")
    except (OSError, PermissionError):
        # Skip if we can't create symlink to /etc
        pytest.skip("Cannot create symlink to /etc (permission denied)")
    finally:
        if etc_symlink.exists():
            etc_symlink.unlink()


def test_e5_filesystem_io_error(monkeypatch, capsys, tmp_path):
    """E5: Test filesystem I/O error branch."""
    env = _base_env()
    run_dir = tmp_path / "run_dir"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    env["RANSOMEYE_RUN_DIR"] = str(run_dir)
    
    # Mock exit_startup_error to raise RuntimeError instead of sys.exit
    def exit_as_runtime_error(msg):
        raise RuntimeError(msg)
    monkeypatch.setattr(runtime, "exit_startup_error", exit_as_runtime_error)
    
    # Mock os.getenv to return our test env
    original_getenv = os.getenv
    def mock_getenv(key, default=None):
        return env.get(key, original_getenv(key, default))
    monkeypatch.setattr(os, "getenv", mock_getenv)
    
    # Mock Path.write_text to raise OSError
    original_write_text = Path.write_text
    def mock_write_text(self, *args, **kwargs):
        if '.ransomeye_io_test' in str(self):
            raise OSError("Simulated filesystem I/O error")
        return original_write_text(self, *args, **kwargs)
    monkeypatch.setattr(Path, "write_text", mock_write_text)
    
    with pytest.raises(RuntimeError):
        runtime._validate_filesystem_edges()
    _assert_hit_marker(capsys, "filesystem_io_error")
