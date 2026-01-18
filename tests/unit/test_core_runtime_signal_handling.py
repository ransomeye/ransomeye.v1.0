"""
FAMILY-6 GROUP F: Core Runtime Signal / Shutdown Handling Tests
Tests for signal handling and shutdown failure branches.
"""
import os
import sys
import signal
from pathlib import Path
from unittest.mock import patch, MagicMock

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


def test_sigterm_before_startup(monkeypatch, capsys):
    """GROUP F1: Test SIGTERM received before startup completes."""
    # Reset startup complete flag
    runtime._startup_complete = False
    runtime._shutdown_in_progress = False
    
    # Invoke SIGTERM handler directly (simulating signal)
    # Create a mock frame
    frame = MagicMock()
    
    # Call signal handler directly - it should exit
    with pytest.raises(SystemExit):
        runtime._signal_handler(signal.SIGTERM, frame)
    
    _assert_hit_marker(capsys, "sigterm_before_startup")
    
    # Reset state
    runtime._startup_complete = True
    runtime._shutdown_in_progress = False


def test_sigint_during_db(monkeypatch, capsys):
    """GROUP F2: Test SIGINT during DB transaction."""
    # Set DB transaction active flag
    runtime._db_transaction_active = True
    runtime._startup_complete = True
    runtime._shutdown_in_progress = False
    
    # Invoke SIGINT handler directly
    frame = MagicMock()
    
    # Call signal handler directly - it should exit
    with pytest.raises(SystemExit):
        runtime._signal_handler(signal.SIGINT, frame)
    
    _assert_hit_marker(capsys, "sigint_during_db")
    
    # Reset state
    runtime._db_transaction_active = False
    runtime._shutdown_in_progress = False


def test_double_signal_detected(monkeypatch, capsys):
    """GROUP F3: Test double signal delivery (re-entrant handler)."""
    # Set shutdown in progress flag
    runtime._shutdown_in_progress = True
    runtime._startup_complete = True
    
    # Invoke signal handler again (simulating re-entrant call)
    frame = MagicMock()
    
    # Call signal handler directly - it should exit idempotently
    with pytest.raises(SystemExit):
        runtime._signal_handler(signal.SIGTERM, frame)
    
    _assert_hit_marker(capsys, "double_signal_detected")
    
    # Reset state
    runtime._shutdown_in_progress = False


def test_shutdown_hook_exception(monkeypatch, capsys):
    """GROUP F4: Test exception thrown inside shutdown hook."""
    # Mock _core_cleanup to raise exception
    original_cleanup = runtime._core_cleanup
    
    def failing_cleanup():
        raise RuntimeError("Shutdown hook exception")
    
    runtime._core_cleanup = failing_cleanup
    runtime._startup_complete = True
    runtime._shutdown_in_progress = False
    
    try:
        # Invoke signal handler
        frame = MagicMock()
        
        # Call signal handler directly - it should exit with safe fallback
        with pytest.raises(SystemExit):
            runtime._signal_handler(signal.SIGTERM, frame)
        
        _assert_hit_marker(capsys, "shutdown_hook_exception")
    finally:
        # Restore cleanup function
        runtime._core_cleanup = original_cleanup
        runtime._shutdown_in_progress = False
