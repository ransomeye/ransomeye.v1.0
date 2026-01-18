"""
FAMILY-6 GROUP A: Core Runtime Config / Startup Failure Tests
Tests for config file access and validation failure branches.
"""
import os
import json
import stat
import sys
from pathlib import Path
from unittest.mock import patch

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
    err = capsys.readouterr().err
    assert f"HIT_BRANCH: {marker}" in err


def test_config_permission_denied(monkeypatch, capsys, tmp_path):
    """GROUP A1: Test config file permission denied."""
    # Create config file and remove read permission
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"test": "value"}), encoding="utf-8")
    config_file.chmod(0o000)  # No permissions
    
    monkeypatch.setenv("RANSOMEYE_CONFIG_FILE", str(config_file))
    
    try:
        # Call _validate_config_access() directly - it should exit
        with pytest.raises(SystemExit):
            runtime._validate_config_access()
        
        _assert_hit_marker(capsys, "config_permission_denied")
    finally:
        # Restore permissions for cleanup
        config_file.chmod(0o644)


def test_config_is_directory(monkeypatch, capsys, tmp_path):
    """GROUP A2: Test config path is directory."""
    # Create directory at config path
    config_dir = tmp_path / "config_dir"
    config_dir.mkdir()
    monkeypatch.setenv("RANSOMEYE_CONFIG_FILE", str(config_dir))
    
    # Call _validate_config_access() directly - it should exit
    with pytest.raises(SystemExit):
        runtime._validate_config_access()
    
    _assert_hit_marker(capsys, "config_is_directory")


def test_config_empty_file(monkeypatch, capsys, tmp_path):
    """GROUP A3: Test config file empty."""
    # Create empty config file
    config_file = tmp_path / "config.json"
    config_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("RANSOMEYE_CONFIG_FILE", str(config_file))
    
    # Call _validate_config_access() directly - it should exit
    with pytest.raises(SystemExit):
        runtime._validate_config_access()
    
    _assert_hit_marker(capsys, "config_empty_file")


def test_config_missing_required_keys(monkeypatch, capsys, tmp_path):
    """GROUP A4: Test missing required config keys."""
    # Create config file missing required keys
    config_file = tmp_path / "config.json"
    config_data = {
        "RANSOMEYE_DB_HOST": "localhost"
        # Missing RANSOMEYE_DB_PASSWORD and RANSOMEYE_DB_USER
    }
    config_file.write_text(json.dumps(config_data), encoding="utf-8")
    monkeypatch.setenv("RANSOMEYE_CONFIG_FILE", str(config_file))
    
    # Call _validate_config_access() directly - it should exit
    with pytest.raises(SystemExit):
        runtime._validate_config_access()
    
    _assert_hit_marker(capsys, "config_missing_required_keys")


def test_env_override_invalid_type(monkeypatch, capsys, tmp_path):
    """GROUP A5: Test ENV override present but invalid type."""
    # Set port env var to non-integer value
    monkeypatch.setenv("RANSOMEYE_DB_PORT", "not_an_integer")
    
    # Call _validate_environment() - it should exit
    with pytest.raises(SystemExit):
        runtime._validate_environment()
    
    _assert_hit_marker(capsys, "env_override_invalid_type")


def test_env_override_invalid_value(monkeypatch, capsys, tmp_path):
    """GROUP A6: Test ENV override invalid value."""
    # Set port env var to invalid port number (out of range)
    monkeypatch.setenv("RANSOMEYE_DB_PORT", "99999")  # Port > 65535
    
    # Call _validate_environment() - it should exit
    with pytest.raises(SystemExit):
        runtime._validate_environment()
    
    _assert_hit_marker(capsys, "env_override_invalid_value")


def test_config_encoding_error(monkeypatch, capsys, tmp_path):
    """GROUP A7: Test config file unreadable due to encoding error."""
    # Create config file with invalid UTF-8 encoding
    config_file = tmp_path / "config.json"
    # Write invalid UTF-8 bytes
    config_file.write_bytes(b'\xff\xfe\x00\x00')  # Invalid UTF-8 sequence
    monkeypatch.setenv("RANSOMEYE_CONFIG_FILE", str(config_file))
    
    # Call _validate_config_access() directly - it should exit
    with pytest.raises(SystemExit):
        runtime._validate_config_access()
    
    _assert_hit_marker(capsys, "config_encoding_error")


def test_config_too_large(monkeypatch, capsys, tmp_path):
    """GROUP A8: Test config file too large."""
    # Create config file exceeding size limit (1MB)
    config_file = tmp_path / "config.json"
    large_content = json.dumps({"key": "x" * (2 * 1024 * 1024)})  # 2MB
    config_file.write_text(large_content, encoding="utf-8")
    monkeypatch.setenv("RANSOMEYE_CONFIG_FILE", str(config_file))
    
    # Call _validate_config_access() directly - it should exit
    with pytest.raises(SystemExit):
        runtime._validate_config_access()
    
    _assert_hit_marker(capsys, "config_too_large")


def test_env_override_empty(monkeypatch, capsys, tmp_path):
    """GROUP A9: Test ENV override present but empty."""
    # Set port env var to empty string
    monkeypatch.setenv("RANSOMEYE_DB_PORT", "")
    
    # Call _validate_environment() - it should exit
    with pytest.raises(SystemExit):
        runtime._validate_environment()
    
    _assert_hit_marker(capsys, "env_override_empty")


def test_config_value_out_of_range(monkeypatch, capsys, tmp_path):
    """GROUP A10: Test config value out of allowed range."""
    # Create config file with port out of range
    config_file = tmp_path / "config.json"
    config_data = {
        "RANSOMEYE_DB_PASSWORD": "test123",
        "RANSOMEYE_DB_USER": "testuser",
        "RANSOMEYE_DB_PORT": 99999  # Out of range
    }
    config_file.write_text(json.dumps(config_data), encoding="utf-8")
    monkeypatch.setenv("RANSOMEYE_CONFIG_FILE", str(config_file))
    
    # Call _validate_config_access() directly - it should exit
    with pytest.raises(SystemExit):
        runtime._validate_config_access()
    
    _assert_hit_marker(capsys, "config_value_out_of_range")
