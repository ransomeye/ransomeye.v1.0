#!/usr/bin/env python3
"""
RansomEye v1.0 Policy Engine (Phase 7 - Simulation-First)
AUTHORITATIVE: Minimal policy engine operating in simulation-first mode
Python 3.10+ only - aligns with Phase 7 requirements
"""

import os
import sys
import json
import uuid
import signal
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

if os.getenv("COVERAGE_PROCESS_START") and not os.getenv("PYTEST_CURRENT_TEST"):
    try:
        import coverage

        coverage.process_startup()
    except Exception:
        pass

# Add common utilities to path (Phase 10 requirement)
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.config import ConfigLoader, ConfigError, validate_port
    from common.logging import setup_logging
    from common.shutdown import ShutdownHandler, ExitCode, exit_config_error, exit_startup_error
    from common.resource.safety import (safe_create_directory, safe_write_file, 
                                        safe_read_file, check_file_descriptors)
    _common_available = True
    _common_resource_safety_available = True
except ImportError:
    _common_available = False
    _common_resource_safety_available = False
    def safe_create_directory(*args, **kwargs): raise RuntimeError("Resource safety utilities not available")
    def safe_write_file(*args, **kwargs): raise RuntimeError("Resource safety utilities not available")
    def safe_read_file(*args, **kwargs): raise RuntimeError("Resource safety utilities not available")
    def check_file_descriptors(*args, **kwargs): pass
    class ConfigLoader:
        def __init__(self, name): self.config = {}; self.required_vars = []
        def require(self, *args, **kwargs): return self
        def optional(self, *args, **kwargs): return self  
        def load(self): return {}
    class ConfigError(Exception): pass
    def validate_port(p): return int(p)
    def setup_logging(name):
        class Logger:
            def info(self, m, **k): print(m)
            def error(self, m, **k): print(m, file=sys.stderr)
            def warning(self, m, **k): print(m, file=sys.stderr)
            def fatal(self, m, **k): print(f"FATAL: {m}", file=sys.stderr)
            def startup(self, m, **k): print(f"STARTUP: {m}")
            def shutdown(self, m, **k): print(f"SHUTDOWN: {m}")
            def db_error(self, m, op, **k): print(f"DB_ERROR[{op}]: {m}", file=sys.stderr)
        return Logger()
    class ShutdownHandler:
        def __init__(self, *args, **kwargs): pass
        def is_shutdown_requested(self): return False
    class ExitCode:
        SUCCESS = 0
        CONFIG_ERROR = 1
        STARTUP_ERROR = 2
        FATAL_ERROR = 4
    def exit_config_error(m): 
        print(f"CONFIG_ERROR: {m}", file=sys.stderr)
        sys.exit(1)
    def exit_startup_error(m): 
        print(f"STARTUP_ERROR: {m}", file=sys.stderr)
        sys.exit(2)

# Contract compliance: No async, no background threads (Phase 7 requirements)
# Synchronous batch processing only

from db import get_db_connection, get_unresolved_incidents, check_incident_evaluated
from rules import evaluate_policy
from signer import create_signed_command

# Phase 10 requirement: Centralized configuration
# Configuration is loaded at runtime, not at import time
if _common_available:
    config_loader = ConfigLoader('policy-engine')
    config_loader.require('RANSOMEYE_DB_PASSWORD', description='Database password (security-sensitive)')
    config_loader.optional('RANSOMEYE_DB_HOST', default='localhost')
    config_loader.optional('RANSOMEYE_DB_PORT', default='5432', validator=validate_port)
    config_loader.optional('RANSOMEYE_DB_NAME', default='ransomeye')
    config_loader.require('RANSOMEYE_DB_USER', description='Database user (PHASE 1: per-service user required, no defaults)')
    config_loader.optional('RANSOMEYE_POLICY_DIR', default='/tmp/ransomeye/policy')
    config_loader.optional('RANSOMEYE_POLICY_ENFORCEMENT_ENABLED', default='false')
else:
    config_loader = None

# Runtime configuration (loaded in _load_config_and_initialize)
config: Optional[Dict[str, Any]] = None

def _load_config_and_initialize():
    """Load configuration at startup (not import time)."""
    global config
    
    if _common_available:
        try:
            config = config_loader.load()
        except ConfigError as e:
            exit_config_error(str(e))
    else:
        config = {}
        if not os.getenv('RANSOMEYE_DB_PASSWORD'):
            exit_config_error('RANSOMEYE_DB_PASSWORD required')

logger = setup_logging('policy-engine')
shutdown_handler = ShutdownHandler('policy-engine')
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
    return Path(os.getenv("RANSOMEYE_COMPONENT_STATUS_PATH", "/tmp/ransomeye/policy-engine.status.json"))

def _write_status(state: str, last_successful_cycle: Optional[str], failure_reason: Optional[str]):
    payload = {
        "state": state,
        "last_successful_cycle": last_successful_cycle,
        "failure_reason": failure_reason
    }
    path = _status_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

# PHASE 4: Initialize ed25519 signer at startup (read once, never reloaded, never logged)
try:
    from signer import get_signer
    # Initialize signer at startup (fail-fast on invalid keypair)
    _signer_initialized = False
    try:
        _ = get_signer()  # Validates and loads keypair
        _signer_initialized = True
        logger.info("PHASE 4: Command signing keypair initialized successfully (ed25519)")
    except SystemExit:
        # get_signer terminates Core on invalid keypair
        raise
except Exception as e:
    error_msg = f"SECURITY VIOLATION: Failed to initialize signing keypair: {e}"
    logger.fatal(error_msg)
    exit_startup_error(error_msg)
except ImportError:
    _signer_initialized = False
    logger.warning("Signer initialization skipped (signer module not available)")


def store_policy_decision(incident_id: str, policy_decision: Dict[str, Any]):
    """
    Store policy decision (for Phase 7 minimal, uses file-based storage).
    
    Disk safety: Detects disk full, permission denied, read-only filesystem.
    Terminates Core immediately on any failure (no retries).
    """
    try:
        policy_dir = Path(os.getenv("RANSOMEYE_POLICY_DIR", "/tmp/ransomeye/policy"))
        
        # Check file descriptors before operation
        if _common_resource_safety_available:
            check_file_descriptors(logger)
        
        # Safely create directory
        if _common_resource_safety_available:
            safe_create_directory(policy_dir, logger, min_bytes=1024)  # 1KB minimum
        else:
            os.makedirs(policy_dir, exist_ok=True)
        
        policy_file = policy_dir / f"policy_decision_{incident_id}.json"
        content = json.dumps(policy_decision, indent=2)
        
        # Safely write file
        if _common_resource_safety_available:
            safe_write_file(policy_file, content, logger, min_bytes=len(content.encode('utf-8')))
        else:
            with open(policy_file, 'w') as f:
                f.write(content)
    except MemoryError:
        error_msg = f"MEMORY ALLOCATION FAILURE: Failed to store policy decision for incident {incident_id}"
        logger.fatal(error_msg)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
    except Exception as e:
        error_msg = f"Failed to store policy decision for incident {incident_id}: {e}"
        logger.fatal(error_msg)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)


def store_signed_command(incident_id: str, signed_command: Dict[str, Any]):
    """
    Store signed command (for Phase 7 minimal, uses file-based storage).
    
    Disk safety: Detects disk full, permission denied, read-only filesystem.
    Terminates Core immediately on any failure (no retries).
    """
    try:
        policy_dir = Path(os.getenv("RANSOMEYE_POLICY_DIR", "/tmp/ransomeye/policy"))
        
        # Check file descriptors before operation
        if _common_resource_safety_available:
            check_file_descriptors(logger)
        
        # Safely create directory
        if _common_resource_safety_available:
            safe_create_directory(policy_dir, logger, min_bytes=1024)  # 1KB minimum
        else:
            os.makedirs(policy_dir, exist_ok=True)
        
        command_id = signed_command['payload']['command_id']
        command_file = policy_dir / f"signed_command_{command_id}.json"
        content = json.dumps(signed_command, indent=2)
        
        # Safely write file
        if _common_resource_safety_available:
            safe_write_file(command_file, content, logger, min_bytes=len(content.encode('utf-8')))
        else:
            with open(command_file, 'w') as f:
                f.write(content)
    except MemoryError:
        error_msg = f"MEMORY ALLOCATION FAILURE: Failed to store signed command for incident {incident_id}"
        logger.fatal(error_msg)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
    except Exception as e:
        error_msg = f"Failed to store signed command for incident {incident_id}: {e}"
        logger.fatal(error_msg)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)


def run_policy_engine():
    """
    Main policy engine loop.
    
    Phase 7 requirement: Consume existing incidents, evaluate explicit policy rules, produce policy decisions
    Phase 7 requirement: Policy engine operates in SIMULATION MODE BY DEFAULT
    Phase 7 requirement: No automatic enforcement, no agent execution, no incident modification
    Phase 7 requirement: System correctness does not depend on policy engine
    
    Contract compliance:
    - Read from incidents table (read-only, does not modify)
    - Write policy decisions and signed commands (metadata only, not facts)
    - Does NOT modify incidents, evidence, or any fact tables
    - Does NOT execute commands or contact agents
    """
    logger.startup("Policy engine starting")
    
    # Check file descriptors at startup
    if _common_resource_safety_available:
        check_file_descriptors(logger)
    
    # Phase 7 requirement: No async, no background threads, no background schedulers
    # Synchronous batch processing only
    
    # Phase 7 requirement: Simulation mode by default (no enforcement)
    simulation_mode = config.get('RANSOMEYE_POLICY_ENFORCEMENT_ENABLED', 'false').lower() == "true"
    if simulation_mode:
        logger.warning("Policy enforcement is enabled (simulation mode should be default)")
    else:
        logger.info("Policy engine running in SIMULATION MODE (no enforcement, no execution)")
    
    # Phase 10 requirement: Database connection with error handling
    try:
        conn = get_db_connection()
    except Exception as e:
        logger.db_error(str(e), "connection")
        exit_startup_error(f"Failed to connect to database: {e}")
    
    try:
        # Phase 7 requirement: Consume existing incidents (read-only)
        # Contract compliance: Read from incidents table (does not modify incidents)
        try:
            incidents = get_unresolved_incidents(conn)
        except Exception as e:
            logger.db_error(str(e), "get_unresolved_incidents")
            raise
        
        if not incidents:
            logger.info("No unresolved incidents found for policy evaluation")
            return
        
        logger.info(f"Processing {len(incidents)} unresolved incidents", incident_count=len(incidents))
        
        # Phase 7 requirement: Evaluate explicit policy rules
        # Deterministic: Policy evaluation is deterministic (no probabilistic logic)
        decisions_count = 0
        commands_count = 0
        
        for incident in incidents:
            incident_id = incident['incident_id']
            
            # Phase 7 requirement: Idempotency (restarting engine does NOT duplicate policy decisions)
            # Deterministic: Simple existence check, no time-window logic
            if check_incident_evaluated(incident_id):
                # Incident already evaluated, skip (idempotent)
                continue
            
            try:
                # Phase 7 requirement: Evaluate policy rules (deterministic)
                should_recommend, action, reason = evaluate_policy(incident)
                
                # Phase 7 requirement: Record policy decision (for audit trail)
                policy_decision = {
                    'incident_id': incident_id,
                    'machine_id': incident['machine_id'],
                    'evaluated_at': datetime.now().isoformat(),
                    'should_recommend_action': should_recommend,
                    'recommended_action': action,
                    'reason': reason,
                    'simulation_mode': True,  # Phase 7 requirement: Simulation mode by default
                    'enforcement_disabled': True  # Phase 7 requirement: No automatic enforcement
                }
                
                store_policy_decision(incident_id, policy_decision)
                decisions_count += 1
                
                # Phase 7 requirement: Generate signed command if action is recommended
                if should_recommend and action:
                    # Phase 7 requirement: Create signed command (NOT execute it)
                    # PHASE 4: Create signed command with policy authority binding
                    # Policy ID and version from policy decision
                    policy_id = f"policy-suspicious-incident-{incident_id[:8]}"  # PHASE 4: Policy identifier
                    policy_version = "1.0.0"  # PHASE 4: Policy version
                    issuing_authority = "policy-engine"  # PHASE 4: Issuing authority
                    
                    signed_command = create_signed_command(
                        command_type=action,
                        target_machine_id=incident['machine_id'],
                        incident_id=incident_id,
                        policy_id=policy_id,
                        policy_version=policy_version,
                        issuing_authority=issuing_authority
                    )
                    
                    # Phase 7 requirement: Store signed command (for audit trail)
                    # Phase 7 requirement: DO NOT send to agents (simulation-first)
                    store_signed_command(incident_id, signed_command)
                    commands_count += 1
                    
                    print(f"Policy decision for incident {incident_id}: {action} (SIMULATION - NOT EXECUTED)")
                else:
                    print(f"Policy decision for incident {incident_id}: NO_ACTION")
                    
            except Exception as e:
                # Phase 7 requirement: No retries
                # Security: Sanitize exception message before logging
                try:
                    from common.security.redaction import sanitize_exception
                    safe_error = sanitize_exception(e)
                except ImportError:
                    safe_error = str(e)
                logger.error(f"Failed to evaluate policy for incident {incident_id}: {safe_error}")
                continue
        
        print(f"Policy engine complete: {decisions_count} policy decision(s), {commands_count} signed command(s) (SIMULATION - NOT EXECUTED)")
        logger.info("Policy engine batch processing complete",
                   decisions_count=decisions_count, commands_count=commands_count)
        logger.info("NOTE: All commands are signed but NOT executed (simulation-first mode)")
        
    except Exception as e:
        # Security: Sanitize exception message before logging
        try:
            from common.security.redaction import sanitize_exception
            safe_error = sanitize_exception(e)
        except ImportError:
            safe_error = str(e)
        logger.fatal(f"Fatal error in policy engine: {safe_error}")
        raise
    finally:
        conn.close()
        logger.shutdown("Database connection closed")

def run_policy_engine_daemon():
    cycle_seconds = int(os.getenv("RANSOMEYE_COMPONENT_CYCLE_SECONDS", "60"))
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    last_success = None
    failure_reason = None
    _write_status("RUNNING", last_success, failure_reason)
    while not _should_shutdown():
        try:
            run_policy_engine()
            last_success = datetime.now(timezone.utc).isoformat()
            failure_reason = None
            _write_status("RUNNING", last_success, failure_reason)
        except Exception as e:
            failure_reason = str(e)
            _write_status("FAILED", last_success, failure_reason)
            raise
        time.sleep(cycle_seconds)
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


def run_policy_cycle(env: Optional[Dict[str, str]] = None) -> bool:
    """
    Run a single Policy Engine cycle (no loop). Raises on failure.
    """
    with _temporary_env(env):
        try:
            run_policy_engine()
        except SystemExit as exc:
            raise RuntimeError("Policy Engine cycle failed") from exc
    return True


def _assert_supervised():
    # D.6.3: Accept both "core" (Core-managed) and "systemd" (systemd-managed) orchestrators
    orch = os.getenv("RANSOMEYE_ORCHESTRATOR")
    if orch not in ("core", "systemd"):
        error_msg = f"Policy Engine must be started by Core orchestrator (core) or systemd (systemd), got: {orch}"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)


if __name__ == "__main__":
    # Phase 7 requirement: No async, no background threads, no background schedulers
    # Synchronous batch execution only
    # Phase 7 requirement: Simulation mode by default (no enforcement)
    try:
        _assert_supervised()
        _load_config_and_initialize()
        run_policy_engine_daemon()
        logger.shutdown("Policy engine completed successfully")
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
