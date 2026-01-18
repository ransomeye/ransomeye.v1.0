#!/usr/bin/env python3
"""
RansomEye v1.0 Correlation Engine (Phase 10 - Hardened)
AUTHORITATIVE: Hardened correlation engine with proper startup, shutdown, and error handling
Python 3.10+ only - aligns with Phase 10 requirements
"""

import os
import sys
import uuid
import signal
import time
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

if os.getenv("COVERAGE_PROCESS_START") and not os.getenv("PYTEST_CURRENT_TEST"):
    try:
        import coverage

        coverage.process_startup()
    except Exception:
        pass

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.config import ConfigLoader, ConfigError, validate_port
    from common.logging import setup_logging, StructuredLogger
    from common.shutdown import ShutdownHandler, ExitCode, exit_config_error, exit_startup_error
except ImportError as e:
    # Security: Sanitize exception message before printing
    try:
        from common.security.redaction import sanitize_exception
        safe_error = sanitize_exception(e)
    except ImportError:
        safe_error = str(e)
    print(f"WARNING: Could not import common modules: {safe_error}", file=sys.stderr)
    # Minimal fallbacks
    class ConfigError(Exception): pass
    class ConfigLoader:
        def __init__(self, name): self.config = {}; self.required_vars = []
        def require(self, *args, **kwargs): return self
        def optional(self, *args, **kwargs): return self
        def load(self): return {}
    def validate_port(p): return int(p)
    class StructuredLogger:
        def __init__(self, *args, **kwargs): pass
        def info(self, *args, **kwargs): print(*args)
        def error(self, *args, **kwargs): print(*args, file=sys.stderr)
        def warning(self, *args, **kwargs): print(*args, file=sys.stderr)
        def startup(self, msg, **kwargs): print(f"STARTUP: {msg}")
        def shutdown(self, msg, **kwargs): print(f"SHUTDOWN: {msg}")
        def db_error(self, msg, op, **kwargs): print(f"DB_ERROR[{op}]: {msg}", file=sys.stderr)
    def setup_logging(name, **kwargs): return StructuredLogger()
    class ShutdownHandler:
        def __init__(self, *args, **kwargs): pass
        def is_shutdown_requested(self): return False
    class ExitCode: SUCCESS = 0; CONFIG_ERROR = 1; STARTUP_ERROR = 2; RUNTIME_ERROR = 3
    def exit_config_error(msg): print(f"CONFIG_ERROR: {msg}", file=sys.stderr); sys.exit(1)
    def exit_startup_error(msg): print(f"STARTUP_ERROR: {msg}", file=sys.stderr); sys.exit(2)

from db import get_db_connection, get_unprocessed_events, create_incident, check_event_processed
from rules import evaluate_event

# Phase 10 requirement: Centralized configuration loading
# Configuration is loaded at runtime, not at import time
config_loader = ConfigLoader('correlation-engine')
config_loader.require('RANSOMEYE_DB_PASSWORD', description='Database password (security-sensitive)')
config_loader.optional('RANSOMEYE_DB_HOST', default='localhost')
config_loader.optional('RANSOMEYE_DB_PORT', default='5432', validator=validate_port)
config_loader.optional('RANSOMEYE_DB_NAME', default='ransomeye')
config_loader.require('RANSOMEYE_DB_USER', description='Database user (PHASE 1: per-service user required, no defaults)')

# Runtime configuration (loaded in _load_config_and_initialize)
config: Optional[Dict[str, Any]] = None

# Phase 10 requirement: Structured logging
logger = setup_logging('correlation-engine')

def _load_config_and_initialize():
    """Load configuration and initialize runtime constants at startup (not import time)."""
    global config
    
    try:
        config = config_loader.load()
    except ConfigError as e:
        exit_config_error(str(e))
    
    # Security: Redact secrets from config before logging
    try:
        from common.security.redaction import get_redacted_config
        redacted_config = get_redacted_config(config)
        logger.startup("Correlation engine starting", config_keys=list(redacted_config.keys()))
    except ImportError:
        logger.startup("Correlation engine starting", config_keys=list(config.keys()))

# Resource safety: Check file descriptors at startup
try:
    from common.resource.safety import check_file_descriptors
    _common_resource_safety_available = True
except ImportError:
    _common_resource_safety_available = False
    def check_file_descriptors(*args, **kwargs): pass

def _check_file_descriptors():
    """Check file descriptors after config is loaded."""
    if _common_resource_safety_available:
        check_file_descriptors(logger)

# Phase 10 requirement: Graceful shutdown handler (for batch jobs, tracks shutdown signal)
shutdown_handler = ShutdownHandler('correlation-engine')
_shutdown_requested = False

def _handle_signal(signum, frame):
    global _shutdown_requested
    _shutdown_requested = True
    if hasattr(shutdown_handler, "shutdown_requested") and hasattr(shutdown_handler.shutdown_requested, "set"):
        shutdown_handler.shutdown_requested.set()

def _should_shutdown() -> bool:
    if hasattr(shutdown_handler, "is_shutdown_requested"):
        try:
            return shutdown_handler.is_shutdown_requested()
        except Exception:
            return _shutdown_requested
    return _shutdown_requested

def _status_path():
    return Path(os.getenv("RANSOMEYE_COMPONENT_STATUS_PATH", "/tmp/ransomeye/correlation-engine.status.json"))

def _write_status(state: str, last_successful_cycle: Optional[str], failure_reason: Optional[str]):
    payload = {
        "state": state,
        "last_successful_cycle": last_successful_cycle,
        "failure_reason": failure_reason
    }
    path = _status_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

def process_event(conn, event: Dict[str, Any]) -> bool:
    """
    GA-BLOCKING: Process single event through correlation rules with state machine.
    
    Implements:
    - Deduplication (same machine → same incident)
    - Confidence accumulation
    - State transitions (SUSPICIOUS → PROBABLE → CONFIRMED)
    - Contradiction handling (confidence decay)
    
    Resource safety: Memory allocation failures terminate Core immediately.
    """
    event_id = event['event_id']
    
    try:
        # Phase 10 requirement: Idempotency check (restart-safe)
        if check_event_processed(conn, event_id):
            logger.info(f"Event already processed, skipping (idempotent)", event_id=event_id)
            return False
        
        machine_id = event['machine_id']

        # GA-BLOCKING: Deduplication - find existing incident
        from state_machine import get_deduplication_key, is_within_deduplication_window, detect_contradiction, DEDUPLICATION_TIME_WINDOW
        from datetime import datetime, timezone
        from dateutil import parser

        observed_at = event['observed_at']
        if isinstance(observed_at, str):
            observed_at = parser.isoparse(observed_at)

        # GA-BLOCKING: Rule evaluation with evidence counts
        evidence_count = 1
        component = event.get('component')
        if component in ('linux_agent', 'dpi'):
            from db import count_recent_events
            evidence_count = count_recent_events(conn, machine_id, component, observed_at, DEDUPLICATION_TIME_WINDOW)
        should_create, stage, confidence_score, evidence_type = evaluate_event(event, evidence_count)

        if not should_create:
            return False

        if not evidence_type:
            evidence_type = 'CORRELATION_PATTERN'
        confidence_score = float(confidence_score)

        dedup_key = get_deduplication_key(event)
        
        existing_incident_id = None
        if dedup_key:
            from db import find_existing_incident
            existing_incident_id = find_existing_incident(conn, machine_id, dedup_key, observed_at)
        
        if existing_incident_id:
            # PHASE 3: Add evidence to existing incident
            # Check for contradiction with existing evidence
            try:
                # PHASE 3: Get existing evidence for contradiction detection
                from db import get_incident_evidence
                existing_evidence_list = get_incident_evidence(conn, existing_incident_id)
                
                # PHASE 3: Detect contradiction (deterministic, specific types)
                is_contradiction, contradiction_type = detect_contradiction(event, existing_evidence_list)
                
                if is_contradiction:
                    # PHASE 3: Apply contradiction decay (blocks escalation, downgrades confidence)
                    from db import apply_contradiction_to_incident
                    apply_contradiction_to_incident(conn, existing_incident_id, contradiction_type)
                    logger.info(f"Applied contradiction decay to incident",
                              incident_id=existing_incident_id, event_id=event_id,
                              contradiction_type=contradiction_type)
                else:
                    # PHASE 3: Add evidence and accumulate confidence (deterministic)
                    from db import add_evidence_to_incident
                    add_evidence_to_incident(conn, existing_incident_id, event, event_id,
                                           evidence_type, confidence_score)
                    logger.info(f"Added evidence to existing incident",
                              incident_id=existing_incident_id, event_id=event_id,
                              confidence=confidence_score)
            except Exception as e:
                logger.db_error(str(e), "add_evidence_to_incident", 
                              incident_id=existing_incident_id, event_id=event_id)
                conn.rollback()
                raise
            
            return True
        else:
            # GA-BLOCKING: Create new incident (single signal → SUSPICIOUS only)
            incident_id = str(uuid.uuid4())
            
            # Phase 10 requirement: Atomic transaction with rollback on error
            try:
                create_incident(conn, incident_id, machine_id, event, stage, confidence_score, event_id, evidence_type)
                logger.info(f"Created incident", 
                          incident_id=incident_id, event_id=event_id, 
                          stage=stage, confidence=confidence_score)
                return True
            except MemoryError:
                error_msg = f"MEMORY ALLOCATION FAILURE: Failed to create incident {incident_id} for event {event_id}"
                logger.fatal(error_msg)
                conn.rollback()
                from common.shutdown import ExitCode, exit_fatal
                exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
            except Exception as e:
                logger.db_error(str(e), "create_incident", incident_id=incident_id, event_id=event_id)
                conn.rollback()
                raise
        
        return False
    except MemoryError:
        error_msg = f"MEMORY ALLOCATION FAILURE: Failed to process event {event_id}"
        logger.fatal(error_msg)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
    except Exception as e:
        # Security: Sanitize exception message before logging
        try:
            from common.security.redaction import sanitize_exception
            safe_error = sanitize_exception(e)
        except ImportError:
            safe_error = str(e)
        logger.error(f"Error processing event: {safe_error}", event_id=event_id)
        raise

def run_correlation_engine():
    """
    Main correlation engine loop (hardened).
    
    Resource safety: Memory allocation failures and file descriptor exhaustion terminate Core immediately.
    
    STEP-10.5 LIFECYCLE FIX: Never exits on "no work" - this is a daemon, not a batch job.
    Returns normally after processing (or when idle) but never exits the process.
    """
    logger.startup("Correlation engine starting processing")
    
    # Check file descriptors before processing
    if _common_resource_safety_available:
        check_file_descriptors(logger)
    
    try:
        # Phase 10 requirement: Database connection with error handling
        conn = get_db_connection()
        try:
            # Phase 10 requirement: Read unprocessed events with proper error handling
            try:
                events = get_unprocessed_events(conn)
            except MemoryError:
                error_msg = "MEMORY ALLOCATION FAILURE: Failed to read unprocessed events"
                logger.fatal(error_msg)
                from common.shutdown import ExitCode, exit_fatal
                exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
            except Exception as e:
                logger.db_error(str(e), "get_unprocessed_events")
                raise
            
            if not events:
                # STEP-10.5 FIX: Log idle state but DO NOT exit - this is a long-running daemon
                logger.info("No unprocessed events found - daemon remains alive")
                return
            
            logger.info(f"Processing {len(events)} unprocessed events", event_count=len(events))
            
            # Phase 10 requirement: Process events deterministically with error handling
            incidents_created = 0
            events_processed = 0
            events_failed = 0
            
            for event in events:
                # Phase 10 requirement: Check shutdown signal (for graceful termination)
                if shutdown_handler.is_shutdown_requested():
                    logger.warning("Shutdown requested, stopping processing")
                    break
                
                try:
                    if process_event(conn, event):
                        incidents_created += 1
                    events_processed += 1
                except MemoryError:
                    # Memory allocation failure - terminate Core immediately
                    error_msg = f"MEMORY ALLOCATION FAILURE: Failed to process event {event.get('event_id')}"
                    logger.fatal(error_msg)
                    from common.shutdown import ExitCode, exit_fatal
                    exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
                except Exception as e:
                    # Phase 10 requirement: No retries, log error and continue
                    # Security: Sanitize exception message before logging
                    try:
                        from common.security.redaction import sanitize_exception
                        safe_error = sanitize_exception(e)
                    except ImportError:
                        safe_error = str(e)
                    events_failed += 1
                    logger.error(f"Failed to process event: {safe_error}", 
                               event_id=event.get('event_id'))
                    # Continue with next event (fail-safe)
                    continue
            
            logger.info(f"Correlation engine complete", 
                       incidents_created=incidents_created,
                       events_processed=events_processed,
                       events_failed=events_failed)
            
        finally:
            # STEP-10.5 FIX: Close DB connection for this cycle (not a shutdown - daemon continues)
            conn.close()
            # Changed log level from "shutdown" to "info" - this is cycle cleanup, not process shutdown
            logger.info("Database connection closed for cycle (daemon continues)")
            
    except Exception as e:
        # Security: Sanitize exception message before logging
        try:
            from common.security.redaction import sanitize_exception
            safe_error = sanitize_exception(e)
        except ImportError:
            safe_error = str(e)
        logger.fatal(f"Fatal error in correlation engine: {safe_error}")
        exit_startup_error(safe_error)

def run_correlation_daemon():
    cycle_seconds = int(os.getenv("RANSOMEYE_COMPONENT_CYCLE_SECONDS", "60"))
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    last_success = None
    failure_reason = None
    _write_status("RUNNING", last_success, failure_reason)
    
    # Send READY notification to systemd (required for Type=notify services)
    # Must be sent AFTER initialization and status file is written
    notify_available = False
    try:
        from systemd.daemon import notify
        notify("READY=1")
        logger.startup("Sent READY notification to systemd")
        notify_available = True
    except ImportError:
        # systemd.daemon not available (non-systemd environment) - continue
        logger.startup("systemd.daemon not available, skipping READY notification")
    except Exception as e:
        logger.warning(f"Failed to send READY notification: {e}")
        # Continue even if notification fails
    
    # Determine watchdog interval from systemd environment or use safe default
    watchdog_usec = os.environ.get('WATCHDOG_USEC', '')
    if watchdog_usec:
        try:
            watchdog_interval = max(1.0, (int(watchdog_usec) / 1_000_000) / 2)
        except (ValueError, TypeError):
            watchdog_interval = 10  # Default to 10 seconds if parsing fails
    else:
        watchdog_interval = 10  # Default to 10 seconds if not set
    
    # STEP-10.5 LIFECYCLE FIX: Start watchdog notification background task
    # Watchdog thread must run continuously while daemon is alive
    if notify_available:
        import threading
        watchdog_stop = threading.Event()
        
        def watchdog_loop():
            """
            Background thread to send periodic WATCHDOG notifications.
            STEP-10.5 FIX: Thread must not exit while daemon is running - runs until watchdog_stop is set.
            """
            try:
                from systemd.daemon import notify
                # Send initial WATCHDOG notification immediately after READY
                notify("WATCHDOG=1")
                last_watchdog = time.time()
                
                while not watchdog_stop.is_set():
                    try:
                        current_time = time.time()
                        elapsed = current_time - last_watchdog
                        if elapsed >= watchdog_interval:
                            notify("WATCHDOG=1")
                            last_watchdog = current_time
                        # Sleep for half the interval to ensure timely notifications
                        watchdog_stop.wait(min(1.0, watchdog_interval / 2))
                    except Exception as inner_e:
                        # STEP-10.5 FIX: Log inner loop exceptions but continue - thread must not exit
                        logger.error(f"Watchdog notification inner loop failed: {inner_e}")
                        # Continue loop - do not exit thread
                        time.sleep(min(1.0, watchdog_interval / 2))
            except Exception as e:
                logger.error(f"Watchdog notification thread failed: {e}")
                # Fail-fast: if watchdog notifications fail and WATCHDOG_USEC is set, exit
                if watchdog_usec:
                    logger.fatal(f"Watchdog notification thread failed but WATCHDOG_USEC is set, exiting")
                    os.kill(os.getpid(), signal.SIGTERM)
        
        watchdog_thread = threading.Thread(target=watchdog_loop, daemon=True, name="correlation-engine-watchdog")
        watchdog_thread.start()
        logger.startup(f"Watchdog notification thread started (interval: {watchdog_interval:.1f}s, thread: {watchdog_thread.name})")
    
    # STEP-10.5 LIFECYCLE FIX: Main daemon loop - NEVER exits on "no work"
    # Only exits on SIGTERM/SIGINT or fatal unrecoverable error (handled by exit_startup_error/exit_fatal)
    try:
        while not _should_shutdown():
            try:
                # STEP-10.5 FIX: run_correlation_engine() returns normally (never exits) when idle
                # Daemon loop continues and sleeps, then polls again
                run_correlation_engine()
                last_success = datetime.now(timezone.utc).isoformat()
                failure_reason = None
                _write_status("RUNNING", last_success, failure_reason)
            except Exception as e:
                # Fatal errors (exit_startup_error/exit_fatal) exit the process directly
                # Other exceptions are unrecoverable - exit daemon loop
                failure_reason = str(e)
                _write_status("FAILED", last_success, failure_reason)
                raise
            time.sleep(cycle_seconds)
    finally:
        # STEP-10.5 FIX: Stop watchdog thread gracefully on shutdown
        if notify_available and 'watchdog_stop' in locals():
            watchdog_stop.set()
            # Give watchdog thread a moment to exit gracefully
            if 'watchdog_thread' in locals() and watchdog_thread.is_alive():
                watchdog_thread.join(timeout=1.0)
    _write_status("STOPPED", last_success, failure_reason)


def _temporary_env(env: Optional[Dict[str, str]]):
    if not env:
        class _Noop:
            def __enter__(self): return None
            def __exit__(self, exc_type, exc, tb): return False
        return _Noop()
    class _Env:
        def __init__(self, updates):
            self.updates = updates
            self.original = None
        def __enter__(self):
            self.original = os.environ.copy()
            os.environ.update(self.updates)
        def __exit__(self, exc_type, exc, tb):
            os.environ.clear()
            os.environ.update(self.original or {})
            return False
    return _Env(env)


def run_correlation_cycle(env: Optional[Dict[str, str]] = None) -> bool:
    """
    Run a single Correlation Engine cycle (no loop). Raises on failure.
    """
    with _temporary_env(env):
        try:
            run_correlation_engine()
        except SystemExit as exc:
            raise RuntimeError("Correlation Engine cycle failed") from exc
    return True

def _assert_supervised():
    orch = os.getenv("RANSOMEYE_ORCHESTRATOR")
    if orch != "systemd":
        error_msg = "Correlation Engine must be started by Core orchestrator (systemd)"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)

if __name__ == "__main__":
    try:
        _assert_supervised()
        _load_config_and_initialize()
        _check_file_descriptors()
        run_correlation_daemon()
        logger.shutdown("Correlation engine completed successfully")
        sys.exit(ExitCode.SUCCESS)
    except KeyboardInterrupt:
        logger.shutdown("Received interrupt, shutting down")
        sys.exit(ExitCode.SUCCESS)
    except ConfigError as e:
        logger.config_error(str(e))
        sys.exit(ExitCode.CONFIG_ERROR)
    except Exception as e:
        # Security: Sanitize exception message before logging
        try:
            from common.security.redaction import sanitize_exception
            safe_error = sanitize_exception(e)
        except ImportError:
            safe_error = str(e)
        logger.fatal(f"Fatal error: {safe_error}")
        sys.exit(ExitCode.FATAL_ERROR)
