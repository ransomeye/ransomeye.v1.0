#!/usr/bin/env python3
"""
RansomEye v1.0 Common Shutdown Handler
AUTHORITATIVE: Graceful shutdown handling for all services
Phase 10 requirement: Graceful shutdown handlers, clear exit codes, no silent crashes
"""

import sys
import signal
import atexit
import threading
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional, List
from enum import IntEnum


class ExitCode(IntEnum):
    """Standard exit codes for RansomEye services."""
    SUCCESS = 0
    CONFIG_ERROR = 1
    STARTUP_ERROR = 2
    RUNTIME_ERROR = 3
    FATAL_ERROR = 4
    SHUTDOWN_ERROR = 5


class ShutdownHandler:
    """
    Graceful shutdown handler for services.
    
    Phase 10 requirement: Handle SIGTERM, SIGINT gracefully with cleanup.
    """
    
    def __init__(self, component_name: str, cleanup_func: Optional[Callable[[], None]] = None):
        """
        Initialize shutdown handler.
        
        Args:
            component_name: Component name (for logging)
            cleanup_func: Cleanup function to call on shutdown
        """
        self.component_name = component_name
        self.cleanup_func = cleanup_func
        self.shutdown_requested = threading.Event()
        self.exit_code = ExitCode.SUCCESS
        self._cleanup_registered = False
        self._signals_registered = False
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register signal handlers and atexit handlers."""
        if self._cleanup_registered:
            return
        
        # Register atexit handler
        atexit.register(self._atexit_cleanup)
        self._cleanup_registered = True
        
        # Register signal handlers
        if not self._signals_registered:
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
            self._signals_registered = True
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals (SIGTERM, SIGINT)."""
        signal_name = signal.Signals(signum).name
        print(f"Received {signal_name}, initiating graceful shutdown...", file=sys.stderr)
        self.shutdown_requested.set()
        self._cleanup()
        
        # Exit with success code (graceful shutdown)
        sys.exit(ExitCode.SUCCESS)
    
    def _atexit_cleanup(self):
        """Cleanup on normal exit."""
        if not self.shutdown_requested.is_set():
            self._cleanup()
    
    def _cleanup(self):
        """Execute cleanup function if registered."""
        if self.cleanup_func:
            try:
                self.cleanup_func()
            except Exception as e:
                print(f"Error during cleanup: {e}", file=sys.stderr)
                self.exit_code = ExitCode.SHUTDOWN_ERROR
    
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self.shutdown_requested.is_set()
    
    def set_exit_code(self, code: ExitCode):
        """Set exit code (for fatal errors)."""
        self.exit_code = code
    
    def exit(self, code: Optional[ExitCode] = None):
        """Exit with specified code (or current exit code)."""
        if code is not None:
            self.exit_code = code
        
        self._cleanup()
        sys.exit(int(self.exit_code))


def exit_fatal(message: str, exit_code: ExitCode = ExitCode.FATAL_ERROR):
    """
    Exit immediately with fatal error.
    
    Phase 10 requirement: Clear exit codes for fatal errors.
    
    Args:
        message: Fatal error message
        exit_code: Exit code (default: FATAL_ERROR)
    """
    print(f"FATAL: {message}", file=sys.stderr)
    sys.exit(int(exit_code))


def _write_core_fatal_marker(reason_code: str, message: str) -> Optional[Path]:
    run_dir = os.getenv("RANSOMEYE_RUN_DIR", "/tmp/ransomeye")
    core_token = os.getenv("RANSOMEYE_CORE_TOKEN")
    component = os.getenv("RANSOMEYE_COMPONENT_NAME") or os.path.basename(sys.argv[0])
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason_code": reason_code,
        "message": message,
        "component": component,
        "core_token": core_token
    }
    try:
        path = Path(run_dir) / "core_fatal.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path
    except Exception:
        return None


def _signal_core_fatal(reason_code: str, message: str) -> None:
    core_pid = os.getenv("RANSOMEYE_CORE_PID")
    if not core_pid:
        return
    _write_core_fatal_marker(reason_code, message)
    try:
        os.kill(int(core_pid), signal.SIGUSR1)
    except Exception:
        pass


def exit_readonly_violation(message: str, exit_code: ExitCode = ExitCode.RUNTIME_ERROR):
    """
    Exit immediately on read-only violation and escalate to Core.
    """
    _signal_core_fatal("READ_ONLY_VIOLATION", message)
    exit_fatal(message, exit_code)


def exit_config_error(message: str):
    """Exit with configuration error."""
    exit_fatal(f"Configuration error: {message}", ExitCode.CONFIG_ERROR)


def exit_startup_error(message: str):
    """Exit with startup error."""
    exit_fatal(f"Startup error: {message}", ExitCode.STARTUP_ERROR)


def exit_runtime_error(message: str):
    """Exit with runtime error."""
    exit_fatal(f"Runtime error: {message}", ExitCode.RUNTIME_ERROR)
