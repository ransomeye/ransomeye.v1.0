"""
FAMILY-6: Core Runtime Fatal Signal / Marker Handling Tests
Tests for fatal signal marker file handling logic.
"""
import os
import json
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


def _assert_hit_marker(capsys, marker):
    err = capsys.readouterr().err
    assert f"HIT_BRANCH: {marker}" in err


def test_fatal_marker_missing(monkeypatch, capsys, tmp_path):
    """FAMILY-6: Test fatal marker handling - marker file missing."""
    # Set run directory to tmp_path
    monkeypatch.setenv("RANSOMEYE_RUN_DIR", str(tmp_path))
    
    # Ensure marker file doesn't exist
    marker_file = tmp_path / "core_fatal.json"
    if marker_file.exists():
        marker_file.unlink()
    
    # Call _load_core_fatal_event() directly
    result = runtime._load_core_fatal_event()
    
    # Assert correct return value
    assert result["reason_code"] == "READ_ONLY_VIOLATION"
    assert "Read-only violation reported by supervised component" in result["message"]
    assert result["component"] == "unknown"
    
    # Assert HIT_BRANCH marker fired
    _assert_hit_marker(capsys, "fatal_marker_missing")


def test_fatal_marker_json_invalid(monkeypatch, capsys, tmp_path):
    """FAMILY-6: Test fatal marker handling - invalid JSON in marker file."""
    # Set run directory to tmp_path
    monkeypatch.setenv("RANSOMEYE_RUN_DIR", str(tmp_path))
    
    # Create marker file with invalid JSON
    marker_file = tmp_path / "core_fatal.json"
    marker_file.write_text("invalid json content{", encoding="utf-8")
    
    # Call _load_core_fatal_event() directly
    result = runtime._load_core_fatal_event()
    
    # Assert correct return value
    assert result["reason_code"] == "READ_ONLY_VIOLATION"
    assert "invalid marker" in result["message"]
    assert result["component"] == "unknown"
    
    # Assert HIT_BRANCH marker fired
    _assert_hit_marker(capsys, "fatal_marker_json_invalid")




def test_fatal_marker_token_mismatch(monkeypatch, capsys, tmp_path):
    """FAMILY-6: Test fatal marker handling - token mismatch."""
    # Set run directory to tmp_path
    monkeypatch.setenv("RANSOMEYE_RUN_DIR", str(tmp_path))
    
    # Set a core token
    monkeypatch.setenv("RANSOMEYE_CORE_TOKEN", "expected-token-12345")
    
    # Create marker file with different token
    marker_file = tmp_path / "core_fatal.json"
    marker_data = {
        "core_token": "wrong-token-67890",
        "reason_code": "READ_ONLY_VIOLATION",
        "message": "Test violation",
        "component": "test_component"
    }
    marker_file.write_text(json.dumps(marker_data), encoding="utf-8")
    
    # Call _load_core_fatal_event() directly
    result = runtime._load_core_fatal_event()
    
    # Assert correct return value
    assert result["reason_code"] == "READ_ONLY_VIOLATION"
    assert "token mismatch" in result["message"]
    assert result["component"] == "test_component"
    
    # Assert HIT_BRANCH marker fired
    _assert_hit_marker(capsys, "fatal_marker_token_mismatch")
