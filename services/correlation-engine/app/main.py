#!/usr/bin/env python3
"""
RansomEye v1.0 Correlation Engine (Phase 10 - Hardened)
AUTHORITATIVE: Hardened correlation engine with proper startup, shutdown, and error handling
Python 3.10+ only - aligns with Phase 10 requirements
"""

import os
import sys
import uuid
from typing import Dict, Any

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
config_loader = ConfigLoader('correlation-engine')
config_loader.require('RANSOMEYE_DB_PASSWORD', description='Database password (security-sensitive)')
config_loader.optional('RANSOMEYE_DB_HOST', default='localhost')
config_loader.optional('RANSOMEYE_DB_PORT', default='5432', validator=validate_port)
config_loader.optional('RANSOMEYE_DB_NAME', default='ransomeye')
config_loader.optional('RANSOMEYE_DB_USER', default='ransomeye')

try:
    config = config_loader.load()
except ConfigError as e:
    exit_config_error(str(e))

# Phase 10 requirement: Structured logging
logger = setup_logging('correlation-engine')

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

if _common_resource_safety_available:
    check_file_descriptors(logger)

# Phase 10 requirement: Graceful shutdown handler (for batch jobs, tracks shutdown signal)
shutdown_handler = ShutdownHandler('correlation-engine')

def process_event(conn, event: Dict[str, Any]) -> bool:
    """
    Process single event through correlation rules.
    
    Resource safety: Memory allocation failures terminate Core immediately.
    """
    event_id = event['event_id']
    
    try:
        # Phase 10 requirement: Idempotency check (restart-safe)
        if check_event_processed(conn, event_id):
            logger.info(f"Event already processed, skipping (idempotent)", event_id=event_id)
            return False
        
        # Phase 10 requirement: Rule evaluation with error handling
        should_create, stage, confidence_score = evaluate_event(event)
        
        if should_create:
            incident_id = str(uuid.uuid4())
            machine_id = event['machine_id']
            
            # Phase 10 requirement: Atomic transaction with rollback on error
            try:
                create_incident(conn, incident_id, machine_id, event, stage, confidence_score, event_id)
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
                logger.info("No unprocessed events found")
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
            conn.close()
            logger.shutdown("Database connection closed")
            
    except Exception as e:
        # Security: Sanitize exception message before logging
        try:
            from common.security.redaction import sanitize_exception
            safe_error = sanitize_exception(e)
        except ImportError:
            safe_error = str(e)
        logger.fatal(f"Fatal error in correlation engine: {safe_error}")
        exit_startup_error(safe_error)

if __name__ == "__main__":
    try:
        run_correlation_engine()
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
