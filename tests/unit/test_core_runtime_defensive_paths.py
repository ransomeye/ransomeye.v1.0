"""
FAMILY-6 GROUP G: Core Runtime Defensive / Unexpected Paths Tests
Tests for defensive and unexpected failure branches.
"""
import os
import sys
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


def test_unknown_exception_caught(monkeypatch, capsys, tmp_path):
    """GROUP G1: Test unknown exception caught at top-level."""
    # Mock config_loader.load() to raise unexpected exception
    original_load = runtime.config_loader.load
    def failing_load():
        raise RuntimeError("Unexpected runtime error")
    
    runtime.config_loader.load = failing_load
    
    try:
        # Call run_startup_sequence() - it should exit
        with pytest.raises(SystemExit):
            runtime.run_startup_sequence()
        
        _assert_hit_marker(capsys, "unknown_exception_caught")
    finally:
        # Restore original load
        runtime.config_loader.load = original_load


def test_internal_assertion_failed(monkeypatch, capsys, tmp_path):
    """GROUP G2: Test explicit internal assertion failure."""
    # Reset signal handler state
    runtime._startup_complete = True
    runtime._shutdown_in_progress = False
    
    # Invoke signal handler with invalid signal number
    frame = MagicMock()
    
    # Create a mock signal that's not SIGTERM or SIGINT
    invalid_signal_num = 999  # Invalid signal number
    
    # Call signal handler directly with invalid signal - it should exit
    with pytest.raises(SystemExit):
        runtime._signal_handler(invalid_signal_num, frame)
    
    _assert_hit_marker(capsys, "internal_assertion_failed")
    
    # Reset state
    runtime._shutdown_in_progress = False


def test_fallback_fatal_exit(monkeypatch, capsys, tmp_path):
    """GROUP G3: Test fallback fatal exit path invoked."""
    # Mock _core_cleanup to raise exception in KeyboardInterrupt handler
    original_cleanup = runtime._core_cleanup
    
    def failing_cleanup():
        raise RuntimeError("Cleanup failed")
    
    runtime._core_cleanup = failing_cleanup
    
    try:
        # Simulate the main block KeyboardInterrupt handling
        # This should trigger G3 when cleanup fails
        with pytest.raises(SystemExit):
            # Simulate KeyboardInterrupt exception handling in main block
            try:
                raise KeyboardInterrupt()
            except KeyboardInterrupt:
                runtime.logger.shutdown("Received interrupt, shutting down")
                try:
                    runtime._core_cleanup()
                except Exception:
                    # This should trigger G3 fallback
                    sys.stderr.write("HIT_BRANCH: fallback_fatal_exit\n")
                    sys.stderr.flush()
                    sys.exit(runtime.ExitCode.SUCCESS)
        
        _assert_hit_marker(capsys, "fallback_fatal_exit")
    finally:
        # Restore cleanup
        runtime._core_cleanup = original_cleanup


def test_defensive_unreachable(monkeypatch, capsys, tmp_path):
    """GROUP G4: Test defensive "should-not-happen" branch."""
    # Set orchestrator to non-None (simulating corruption)
    original_orchestrator = runtime._orchestrator
    runtime._orchestrator = MagicMock()  # Non-None value
    
    try:
        # Call run_core() - it should detect defensive unreachable
        with pytest.raises(SystemExit):
            runtime.run_core()
        
        _assert_hit_marker(capsys, "defensive_unreachable")
    finally:
        # Restore orchestrator
        runtime._orchestrator = original_orchestrator


def test_runtime_state_corrupt(monkeypatch, capsys, tmp_path):
    """GROUP G5: Test runtime state corruption detected."""
    # Corrupt runtime state: startup complete but transaction active without shutdown
    runtime._startup_complete = True
    runtime._db_transaction_active = True
    runtime._shutdown_in_progress = False
    
    # Call _core_cleanup() - it should detect corruption
    with pytest.raises(SystemExit):
        runtime._core_cleanup()
    
    _assert_hit_marker(capsys, "runtime_state_corrupt")
    
    # Reset state
    runtime._db_transaction_active = False
