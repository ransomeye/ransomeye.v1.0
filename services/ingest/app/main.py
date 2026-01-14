#!/usr/bin/env python3
"""
RansomEye v1.0 Ingest Service (Phase 10 - Hardened)
AUTHORITATIVE: Hardened ingest service with proper startup, shutdown, and error handling
Python 3.10+ only - aligns with Phase 10 requirements
"""

import sys
import os
import json
import hashlib
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID

import jsonschema
import psycopg2
from psycopg2 import pool
from dateutil import parser
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
import uvicorn

# Add common utilities to path
# Calculate project root (rebuild/) by going up from services/ingest/app/
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.config import ConfigLoader, ConfigError, validate_path, validate_port, check_disk_space
    from common.logging import setup_logging, StructuredLogger
    from common.shutdown import ShutdownHandler, ExitCode, exit_config_error, exit_startup_error, exit_fatal
    from common.integrity.verification import (
        verify_hash_chain_continuity, verify_sequence_monotonicity, 
        verify_idempotency, detect_corruption
    )
    from common.db.safety import (create_write_connection_pool, IsolationLevel, 
                                   execute_write_operation, begin_transaction, 
                                   commit_transaction, rollback_transaction,
                                   validate_connection_health)
    from common.resource.safety import (safe_create_directory, safe_read_file,
                                        safe_write_file, check_file_descriptors)
    from common.security.telemetry_verifier import TelemetryVerifier, TelemetryVerificationError
    from common.security.middleware import ServiceAuthMiddleware
    _common_integrity_available = True
    _common_db_safety_available = True
    _common_resource_safety_available = True
    _telemetry_verification_available = True
    _service_auth_available = True
except ImportError as e:
    _common_integrity_available = False
    _common_db_safety_available = False
    _common_resource_safety_available = False
    _telemetry_verification_available = False
    _service_auth_available = False
    def safe_create_directory(*args, **kwargs): raise RuntimeError("Resource safety utilities not available")
    def safe_read_file(*args, **kwargs): raise RuntimeError("Resource safety utilities not available")
    def safe_write_file(*args, **kwargs): raise RuntimeError("Resource safety utilities not available")
    def check_file_descriptors(*args, **kwargs): pass
    def verify_hash_chain_continuity(*args, **kwargs): return (True, None)
    def verify_sequence_monotonicity(*args, **kwargs): return (True, None)
    def verify_idempotency(*args, **kwargs): return True
    def detect_corruption(*args, **kwargs): return (False, None)
    class TelemetryVerifier:
        def __init__(self, *args, **kwargs): pass
        def verify_envelope(self, *args, **kwargs): return (False, "Telemetry verification not available")
        def verify_component_identity(self, *args, **kwargs): return (False, "Component identity verification not available")
    class ServiceAuthMiddleware:
        def __init__(self, *args, **kwargs): pass
    # Fallback: if common modules not available, use basic error handling
    print(f"WARNING: Could not import common modules: {e}", file=sys.stderr)
    # Define minimal fallbacks
    class ConfigError(Exception): pass
    class ConfigLoader:
        def __init__(self, name): self.config = {}; self.required_vars = []
        def require(self, *args, **kwargs): return self
        def optional(self, *args, **kwargs): return self
        def load(self): return {}
    def validate_path(p, **kwargs): return Path(p)
    def validate_port(p): return int(p)
    def check_disk_space(p, **kwargs): pass
    def setup_logging(name, **kwargs):
        import logging
        logger = logging.getLogger(name)
        logger.addHandler(logging.StreamHandler(sys.stderr))
        return type('Logger', (), {'info': logger.info, 'error': logger.error, 'warning': logger.warning, 'fatal': logger.critical, 'startup': lambda self, msg, **kw: logger.info(f"STARTUP: {msg}"), 'shutdown': lambda self, msg, **kw: logger.info(f"SHUTDOWN: {msg}"), 'db_error': lambda self, msg, op, **kw: logger.error(f"DB_ERROR[{op}]: {msg}"), 'resource_error': lambda self, res, msg, **kw: logger.error(f"RESOURCE_ERROR[{res}]: {msg}")})()
    class ShutdownHandler:
        def __init__(self, *args, **kwargs): self.shutdown_requested = type('Event', (), {'is_set': lambda: False})()
        def is_shutdown_requested(self): return False
        def exit(self, code): sys.exit(int(code))
    class ExitCode: SUCCESS = 0; CONFIG_ERROR = 1; STARTUP_ERROR = 2; RUNTIME_ERROR = 3; FATAL_ERROR = 4; SHUTDOWN_ERROR = 5
    def exit_config_error(msg): print(f"CONFIG_ERROR: {msg}", file=sys.stderr); sys.exit(1)
    def exit_startup_error(msg): print(f"STARTUP_ERROR: {msg}", file=sys.stderr); sys.exit(2)
    def exit_fatal(msg, code=4): print(f"FATAL: {msg}", file=sys.stderr); sys.exit(int(code))

# Phase 10 requirement: Centralized configuration loading
config_loader = ConfigLoader('ingest')
config_loader.require('RANSOMEYE_DB_PASSWORD', description='Database password (security-sensitive)')
config_loader.optional('RANSOMEYE_DB_HOST', default='localhost')
config_loader.optional('RANSOMEYE_DB_PORT', default='5432', validator=validate_port)
config_loader.optional('RANSOMEYE_DB_NAME', default='ransomeye')
config_loader.require('RANSOMEYE_DB_USER', description='Database user (PHASE 1: per-service user required, no defaults)')
config_loader.optional('RANSOMEYE_INGEST_PORT', default='8000', validator=validate_port)
config_loader.optional('RANSOMEYE_EVENT_ENVELOPE_SCHEMA_PATH', 
                      default='/opt/ransomeye/etc/contracts/event-envelope.schema.json',
                      validator=lambda v: validate_path(v, must_exist=True))
config_loader.optional('RANSOMEYE_LOG_DIR', default='/var/log/ransomeye',
                      validator=lambda v: validate_path(v, must_exist=False, must_be_writable=True))
config_loader.optional('RANSOMEYE_DB_POOL_MIN', default='2', validator=lambda v: int(v))
config_loader.optional('RANSOMEYE_DB_POOL_MAX', default='20', validator=lambda v: int(v))

# Load configuration (fail-fast on errors)
# Security: Secrets are redacted in config dict, use config_loader.get_secret() for actual values
try:
    config = config_loader.load()
except ConfigError as e:
    exit_config_error(str(e))

# Phase 10 requirement: Structured logging
logger = setup_logging('ingest')

# Security: Redact secrets from config before logging
try:
    from common.security.redaction import get_redacted_config
    redacted_config = get_redacted_config(config)
    logger.startup("Ingest service starting", config_keys=list(redacted_config.keys()))
except ImportError:
    logger.startup("Ingest service starting", config_keys=list(config.keys()))

# Phase 10 requirement: Graceful shutdown handler
shutdown_handler = ShutdownHandler('ingest', cleanup_func=lambda: _cleanup())

# Database connection pool (Phase 10 requirement: Resource safety)
db_pool: Optional[pool.ThreadedConnectionPool] = None

def _init_db_pool():
    """Initialize database connection pool with explicit isolation level."""
    global db_pool
    try:
        min_conn = int(config.get('RANSOMEYE_DB_POOL_MIN', 2))
        max_conn = int(config.get('RANSOMEYE_DB_POOL_MAX', 20))
        
        # Security: Get password from secure storage (never logged)
        db_password = config_loader.get_secret('RANSOMEYE_DB_PASSWORD')
        
        # Use common database safety utilities to create pool with isolation level
        if _common_db_safety_available:
            db_pool = create_write_connection_pool(
                min_conn, max_conn,
                host=config['RANSOMEYE_DB_HOST'],
                port=int(config['RANSOMEYE_DB_PORT']),
                database=config['RANSOMEYE_DB_NAME'],
                user=config['RANSOMEYE_DB_USER'],  # PHASE 1: Per-service user (required, no defaults)
                password=db_password,  # Security: Use secret from secure storage
                isolation_level=IsolationLevel.READ_COMMITTED,
                logger=logger
            )
        else:
            # Fallback if common utilities not available
            db_pool = pool.ThreadedConnectionPool(
                min_conn, max_conn,
                host=config['RANSOMEYE_DB_HOST'],
                port=int(config['RANSOMEYE_DB_PORT']),
                database=config['RANSOMEYE_DB_NAME'],
                user=config['RANSOMEYE_DB_USER'],  # PHASE 1: Per-service user (required, no defaults)
                password=db_password  # Security: Use secret from secure storage
            )
            # Test connection
            conn = db_pool.getconn()
            try:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.close()
            finally:
                db_pool.putconn(conn)
            
            logger.info(f"Database connection pool initialized", min_conn=min_conn, max_conn=max_conn)
    except Exception as e:
        logger.db_error(str(e), "pool_initialization")
        raise

def _cleanup():
    """Cleanup on shutdown."""
    global db_pool
    logger.shutdown("Ingest service shutting down")
    
    if db_pool:
        try:
            db_pool.closeall()
            logger.info("Database connection pool closed")
        except Exception as e:
            # Security: Sanitize exception message before logging
            try:
                from common.security.redaction import sanitize_exception
                safe_error = sanitize_exception(e)
            except ImportError:
                safe_error = str(e)
            logger.error(f"Error closing database pool: {safe_error}")

def get_db_connection():
    """Get database connection from pool with health validation."""
    global db_pool
    if not db_pool:
        raise RuntimeError("Database pool not initialized")
    
    try:
        conn = db_pool.getconn()
        if conn:
            # Validate connection health before returning
            if _common_db_safety_available:
                if not validate_connection_health(conn):
                    db_pool.putconn(conn)
                    raise RuntimeError("Connection health validation failed")
            return conn
    except Exception as e:
        logger.db_error(str(e), "get_connection")
        raise
    
    # Pool exhausted
    logger.resource_error("database_connections", "Connection pool exhausted")
    
    # GA-BLOCKING: Track pool exhaustion for operational telemetry
    if _metrics_available:
        metrics = get_metrics()
        if metrics:
            metrics.record_pool_exhaustion()
    
    raise RuntimeError("Database connection pool exhausted")

def put_db_connection(conn):
    """Return database connection to pool."""
    global db_pool
    if db_pool:
        db_pool.putconn(conn)

# Check file descriptors at startup
if _common_resource_safety_available:
    check_file_descriptors(logger)

# Load event envelope schema with disk safety
SCHEMA_PATH = Path(config['RANSOMEYE_EVENT_ENVELOPE_SCHEMA_PATH'])
if not SCHEMA_PATH.exists():
    exit_startup_error(f"Event envelope schema not found: {SCHEMA_PATH}")

try:
    if _common_resource_safety_available:
        schema_content = safe_read_file(SCHEMA_PATH, logger)
        EVENT_ENVELOPE_SCHEMA = json.loads(schema_content)
    else:
        with open(SCHEMA_PATH, 'r') as f:
            EVENT_ENVELOPE_SCHEMA = json.load(f)
    logger.info(f"Event envelope schema loaded", schema_path=str(SCHEMA_PATH))
except MemoryError:
    error_msg = f"MEMORY ALLOCATION FAILURE: Failed to load event envelope schema from {SCHEMA_PATH}"
    logger.fatal(error_msg)
    exit_startup_error(error_msg)
except Exception as e:
    # Security: Sanitize exception message before logging
    try:
        from common.security.redaction import sanitize_exception
        safe_error = sanitize_exception(e)
    except ImportError:
        safe_error = str(e)
    error_msg = f"Failed to load event envelope schema from {SCHEMA_PATH}: {safe_error}"
    logger.fatal(error_msg)
    exit_startup_error(error_msg)

# Disk safety: Check disk space and create log directory with explicit failure detection
LOG_DIR = Path(config.get('RANSOMEYE_LOG_DIR', '/var/log/ransomeye'))
try:
    if _common_resource_safety_available:
        safe_create_directory(LOG_DIR, logger, min_bytes=100 * 1024 * 1024)  # 100MB minimum
    else:
        if not LOG_DIR.exists():
            LOG_DIR.mkdir(parents=True, exist_ok=True)
        check_disk_space(LOG_DIR, min_bytes=100 * 1024 * 1024)  # 100MB minimum
except Exception as e:
    # Security: Sanitize exception message before logging
    try:
        from common.security.redaction import sanitize_exception
        safe_error = sanitize_exception(e)
    except ImportError:
        safe_error = str(e)
    error_msg = f"DISK SAFETY FAILURE: Log directory setup failed for {LOG_DIR}: {safe_error}"
    logger.fatal(error_msg)
    exit_startup_error(error_msg)

# Event validation status enum
VALIDATION_STATUS_VALID = "VALID"
VALIDATION_STATUS_DUPLICATE_REJECTED = "DUPLICATE_REJECTED"
VALIDATION_STATUS_SCHEMA_VALIDATION_FAILED = "SCHEMA_VALIDATION_FAILED"
VALIDATION_STATUS_TIMESTAMP_VALIDATION_FAILED = "TIMESTAMP_VALIDATION_FAILED"
VALIDATION_STATUS_INTEGRITY_CHAIN_BROKEN = "INTEGRITY_CHAIN_BROKEN"

# GA-BLOCKING: Import metrics collection for operational telemetry
try:
    from services.ingest.app.metrics import get_metrics
    _metrics_available = True
except ImportError:
    _metrics_available = False
    def get_metrics():
        return None

app = FastAPI(title="RansomEye Ingest Service", version="1.0.0")
app.add_middleware(GZipMiddleware, minimum_size=1000)

# PHASE 1: Service-to-service authentication middleware
if _service_auth_available:
    try:
        key_dir = os.getenv('RANSOMEYE_SERVICE_KEY_DIR')
        app.add_middleware(ServiceAuthMiddleware, service_name="ingest", key_dir=key_dir)
        logger.startup("Service authentication middleware enabled")
    except Exception as e:
        logger.fatal(f"Failed to initialize service authentication: {e}")
        exit_startup_error(f"Service authentication initialization failed: {e}")

# PHASE 1: Telemetry signature verifier
telemetry_verifier = None
if _telemetry_verification_available:
    try:
        key_dir = os.getenv('RANSOMEYE_COMPONENT_KEY_DIR')
        if key_dir:
            from pathlib import Path
            telemetry_verifier = TelemetryVerifier(public_key_dir=Path(key_dir))
        else:
            telemetry_verifier = TelemetryVerifier()
        logger.startup("Telemetry signature verification enabled")
    except Exception as e:
        logger.fatal(f"Failed to initialize telemetry verifier: {e}")
        exit_startup_error(f"Telemetry verification initialization failed: {e}")

# GA-BLOCKING: Register diagnostics router for /health/metrics endpoint
try:
    from services.ingest.app.routes.diagnostics import router as diagnostics_router
    app.include_router(diagnostics_router)
except ImportError:
    # Diagnostics router not available - continue without it
    pass

@app.on_event("startup")
async def startup_event():
    """FastAPI startup event."""
    try:
        _init_db_pool()
        logger.startup("Ingest service started successfully")
    except Exception as e:
        # Security: Sanitize exception message before logging
        try:
            from common.security.redaction import sanitize_exception
            safe_error = sanitize_exception(e)
        except ImportError:
            safe_error = str(e)
        logger.fatal(f"Startup failed: {safe_error}")
        shutdown_handler.exit(ExitCode.STARTUP_ERROR)

@app.on_event("shutdown")
async def shutdown_event():
    """FastAPI shutdown event."""
    _cleanup()

def compute_hash(envelope: dict) -> str:
    """Compute SHA256 hash of event envelope."""
    envelope_copy = envelope.copy()
    if "integrity" in envelope_copy:
        integrity_copy = envelope_copy["integrity"].copy()
        integrity_copy["hash_sha256"] = ""
        envelope_copy["integrity"] = integrity_copy
    
    json_str = json.dumps(envelope_copy, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    hash_obj = hashlib.sha256(json_str.encode("utf-8"))
    return hash_obj.hexdigest()

def validate_schema(envelope: dict) -> tuple[bool, Optional[str], Optional[dict]]:
    """Validate event envelope against schema."""
    try:
        jsonschema.validate(instance=envelope, schema=EVENT_ENVELOPE_SCHEMA)
        return True, None, None
    except jsonschema.ValidationError as e:
        return False, "SCHEMA_VIOLATION", {
            "field_path": ".".join(str(p) for p in e.path),
            "error_message": e.message,
            "expected": e.schema if "expected" in e.schema else None,
        }
    except Exception as e:
        return False, "SCHEMA_VALIDATION_FAILED", {"error": str(e)}

def validate_timestamps(envelope: dict) -> tuple[bool, Optional[str], Optional[dict]]:
    """Validate timestamps."""
    try:
        observed_at_str = envelope.get("observed_at")
        ingested_at_str = envelope.get("ingested_at")
        
        observed_at = parser.isoparse(observed_at_str)
        ingested_at = parser.isoparse(ingested_at_str)
        
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)
        else:
            observed_at = observed_at.astimezone(timezone.utc)
        
        if ingested_at.tzinfo is None:
            ingested_at = ingested_at.replace(tzinfo=timezone.utc)
        else:
            ingested_at = ingested_at.astimezone(timezone.utc)
        
        time_diff = (ingested_at - observed_at).total_seconds()
        if time_diff < -5:
            return False, "TIMESTAMP_FUTURE_BEYOND_TOLERANCE", {
                "observed_at": observed_at_str,
                "ingested_at": ingested_at_str,
                "time_diff_seconds": time_diff,
                "max_tolerance": -5
            }
        
        if time_diff > 30 * 24 * 3600:
            return False, "TIMESTAMP_TOO_OLD", {
                "observed_at": observed_at_str,
                "ingested_at": ingested_at_str,
                "time_diff_days": time_diff / (24 * 3600),
                "max_days": 30
            }
        
        late_arrival = time_diff > 3600
        arrival_latency_seconds = int(time_diff) if late_arrival else None
        
        return True, None, {
            "late_arrival": late_arrival,
            "arrival_latency_seconds": arrival_latency_seconds
        }
    except Exception as e:
        return False, "TIMESTAMP_PARSE_ERROR", {"error": str(e)}

def validate_hash_integrity(envelope: dict) -> tuple[bool, Optional[str]]:
    """Verify hash integrity."""
    provided_hash = envelope.get("integrity", {}).get("hash_sha256", "")
    computed_hash = compute_hash(envelope)
    
    if provided_hash != computed_hash:
        return False, "INTEGRITY_VIOLATION"
    
    return True, None

def check_duplicate(conn, event_id: str) -> bool:
    """Check if event_id already exists."""
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM raw_events WHERE event_id = %s", (event_id,))
        return cur.fetchone() is not None

def store_event(conn, envelope: dict, validation_status: str, late_arrival: bool, arrival_latency_seconds: Optional[int]):
    """
    Store event in database with integrity verification.
    
    Transaction discipline: Explicit begin, commit on success, rollback on failure.
    Deadlock/integrity violation detection: Log and terminate (no retries).
    Connection safety: Validate health before operation.
    """
    def _do_store_event():
        """Inner function for write operation."""
        cur = conn.cursor()
        try:
            event_id = envelope["event_id"]
            machine_id = envelope["machine_id"]
            component = envelope["component"]
            component_instance_id = envelope["component_instance_id"]
            observed_at = parser.isoparse(envelope["observed_at"])
            ingested_at = parser.isoparse(envelope["ingested_at"])
            sequence = envelope["sequence"]
            payload = json.dumps(envelope["payload"])
            hostname = envelope["identity"]["hostname"]
            boot_id = envelope["identity"]["boot_id"]
            agent_version = envelope["identity"]["agent_version"]
            hash_sha256 = envelope["integrity"]["hash_sha256"]
            prev_hash_sha256 = envelope["integrity"].get("prev_hash_sha256")
            
            # Verify hash-chain continuity
            if _common_integrity_available:
                is_valid, error_msg = verify_hash_chain_continuity(conn, component_instance_id, prev_hash_sha256, sequence)
                if not is_valid:
                    logger.error(f"Hash chain continuity violation: {error_msg}", event_id=event_id, sequence=sequence, component_instance_id=component_instance_id)
                    raise ValueError(f"Hash chain continuity violation: {error_msg}")
            
            # Verify sequence monotonicity
            if _common_integrity_available:
                is_valid, error_msg = verify_sequence_monotonicity(conn, component_instance_id, sequence)
                if not is_valid:
                    logger.error(f"Sequence monotonicity violation: {error_msg}", 
                               event_id=event_id, component_instance_id=component_instance_id, sequence=sequence)
                    raise ValueError(f"Sequence monotonicity violation: {error_msg}")
            
            # Verify idempotency (already checked in check_duplicate, but double-check)
            if _common_integrity_available:
                if not verify_idempotency(conn, event_id):
                    logger.warning(f"Idempotency violation: Event {event_id} already exists", event_id=event_id)
                    raise ValueError(f"Event {event_id} already exists (duplicate)")
            
            cur.execute("""
                INSERT INTO machines (machine_id, first_seen_at, last_seen_at, total_event_count)
                VALUES (%s, %s, %s, 1)
                ON CONFLICT (machine_id) DO UPDATE
                SET last_seen_at = EXCLUDED.last_seen_at,
                    total_event_count = machines.total_event_count + 1
            """, (machine_id, ingested_at, ingested_at))
            
            cur.execute("""
                INSERT INTO component_instances (
                    component_instance_id, machine_id, component, first_seen_at, last_seen_at,
                    last_sequence, total_event_count, last_hash_sha256
                )
                VALUES (%s, %s, %s, %s, %s, %s, 1, %s)
                ON CONFLICT (component_instance_id) DO UPDATE
                SET last_seen_at = EXCLUDED.last_seen_at,
                    last_sequence = EXCLUDED.last_sequence,
                    total_event_count = component_instances.total_event_count + 1,
                    last_hash_sha256 = EXCLUDED.last_hash_sha256
            """, (
                component_instance_id, machine_id, component, ingested_at, ingested_at,
                sequence, hash_sha256
            ))
            
            cur.execute("""
                INSERT INTO raw_events (
                    event_id, machine_id, component_instance_id, component,
                    observed_at, ingested_at, sequence, payload,
                    hostname, boot_id, agent_version,
                    hash_sha256, prev_hash_sha256,
                    validation_status, late_arrival, arrival_latency_seconds
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                event_id, machine_id, component_instance_id, component,
                observed_at, ingested_at, sequence, payload,
                hostname, boot_id, agent_version,
                hash_sha256, prev_hash_sha256,
                validation_status, late_arrival, arrival_latency_seconds
            ))
            
            cur.execute("""
                INSERT INTO event_validation_log (event_id, validation_status, validation_timestamp)
                VALUES (%s, %s, NOW())
            """, (event_id, validation_status))
            
            return True
        finally:
            cur.close()
    
    # GA-BLOCKING: Track DB write latency for operational telemetry
    write_start_time = time.time()
    
    # Use common database safety utilities for explicit transaction management
    try:
        if _common_db_safety_available:
            result = execute_write_operation(conn, "store_event", _do_store_event, logger)
        else:
            # Fallback: Explicit transaction management
            begin_transaction(conn, logger)
            try:
                result = _do_store_event()
                commit_transaction(conn, logger, "store_event")
            except Exception as e:
                rollback_transaction(conn, logger, "store_event")
                logger.db_error(str(e), "store_event", event_id=envelope.get("event_id"))
                raise
        
        # Record DB write latency (non-blocking, lightweight)
        if _metrics_available:
            write_latency_ms = (time.time() - write_start_time) * 1000.0
            metrics = get_metrics()
            if metrics:
                metrics.record_db_write(write_latency_ms)
        
        return result
    except Exception:
        # Record latency even on failure (for monitoring)
        if _metrics_available:
            write_latency_ms = (time.time() - write_start_time) * 1000.0
            metrics = get_metrics()
            if metrics:
                metrics.record_db_write(write_latency_ms)
        raise

@app.post("/events")
async def ingest_event(request: Request):
    """
    Ingest event endpoint.
    
    PHASE 1 REQUIREMENTS:
    - Service-to-service authentication (via middleware)
    - Telemetry signature verification (reject unsigned/spoofed telemetry)
    - Component identity binding verification
    """
    if shutdown_handler.is_shutdown_requested():
        raise HTTPException(status_code=503, detail={"error_code": "SERVICE_SHUTTING_DOWN"})
    
    try:
        envelope = await request.json()
    except Exception as e:
        # Security: Sanitize exception message before logging
        try:
            from common.security.redaction import sanitize_exception
            safe_error = sanitize_exception(e)
        except ImportError:
            safe_error = str(e)
        logger.error(f"Invalid JSON in request: {safe_error}")
        # Security: Never expose full error details in response (avoid secret leakage)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_JSON"}
        )
    
    # PHASE 1: Telemetry signature verification (CRITICAL - reject unsigned/spoofed telemetry)
    if telemetry_verifier:
        is_valid, error_msg = telemetry_verifier.verify_envelope(envelope)
        if not is_valid:
            conn = None
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO event_validation_log (
                            event_id, validation_status, validation_timestamp,
                            error_code, error_message
                        )
                        VALUES (%s, %s, NOW(), %s, %s)
                    """, (
                        envelope.get("event_id"),
                        "SIGNATURE_VERIFICATION_FAILED",
                        "SIGNATURE_VERIFICATION_FAILED",
                        error_msg
                    ))
                conn.commit()
                logger.warning(f"Telemetry signature verification failed: {error_msg}", event_id=envelope.get("event_id"))
            except Exception as e:
                if conn:
                    conn.rollback()
                logger.db_error(str(e), "log_signature_failure")
            finally:
                if conn:
                    put_db_connection(conn)
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error_code": "SIGNATURE_VERIFICATION_FAILED", "message": error_msg}
            )
        
        # PHASE 1: Component identity binding verification
        is_valid, error_msg = telemetry_verifier.verify_component_identity(envelope)
        if not is_valid:
            conn = None
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute("""
                    # PHASE 2: Use deterministic timestamp from envelope (observed_at)
                    observed_at = parser.isoparse(envelope.get("observed_at", envelope.get("ingested_at")))
                    cur.execute("""
                        INSERT INTO event_validation_log (
                            event_id, validation_status, validation_timestamp,
                            error_code, error_message
                        )
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        envelope.get("event_id"),
                        "COMPONENT_IDENTITY_VERIFICATION_FAILED",
                        observed_at,  # PHASE 2: Deterministic timestamp from envelope
                        "COMPONENT_IDENTITY_VERIFICATION_FAILED",
                        error_msg
                    ))
                conn.commit()
                logger.warning(f"Component identity verification failed: {error_msg}", event_id=envelope.get("event_id"))
            except Exception as e:
                if conn:
                    conn.rollback()
                logger.db_error(str(e), "log_identity_failure")
            finally:
                if conn:
                    put_db_connection(conn)
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error_code": "COMPONENT_IDENTITY_VERIFICATION_FAILED", "message": error_msg}
            )
    else:
        # PHASE 1: Fail-closed if telemetry verification is not available
        logger.fatal("Telemetry signature verification not available - rejecting all telemetry")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_code": "TELEMETRY_VERIFICATION_UNAVAILABLE", "message": "Telemetry verification service unavailable"}
        )
    
    is_valid, error_code, validation_details = validate_schema(envelope)
    if not is_valid:
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    # PHASE 2: Use deterministic timestamp from envelope (observed_at)
                    observed_at = parser.isoparse(envelope.get("observed_at", envelope.get("ingested_at")))
                    cur.execute("""
                        INSERT INTO event_validation_log (
                            event_id, validation_status, validation_timestamp,
                            error_code, error_message, validation_details
                        )
                        VALUES (NULL, %s, %s, %s, %s, %s::jsonb)
                    """, (
                        VALIDATION_STATUS_SCHEMA_VALIDATION_FAILED,
                        observed_at,  # PHASE 2: Deterministic timestamp from envelope
                        error_code,
                        validation_details.get("error_message") if validation_details else None,
                        json.dumps(validation_details) if validation_details else None
                    ))
            conn.commit()
            logger.warning(f"Schema validation failed: {error_code}", event_id=envelope.get("event_id"))
        except Exception as e:
            if conn:
                conn.rollback()
            logger.db_error(str(e), "log_validation_failure")
        finally:
            if conn:
                put_db_connection(conn)
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": error_code, "validation_details": validation_details}
        )
    
    is_valid, error_code = validate_hash_integrity(envelope)
    if not is_valid:
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    # PHASE 2: Use deterministic timestamp from envelope (observed_at)
                    observed_at = parser.isoparse(envelope.get("observed_at", envelope.get("ingested_at")))
                    cur.execute("""
                        INSERT INTO event_validation_log (
                            event_id, validation_status, validation_timestamp,
                            error_code, error_message
                        )
                        VALUES (NULL, %s, %s, %s, %s)
                    """, (VALIDATION_STATUS_INTEGRITY_CHAIN_BROKEN, observed_at, error_code, "Hash mismatch"))
            conn.commit()
            logger.warning(f"Hash integrity validation failed: {error_code}", event_id=envelope.get("event_id"))
        except Exception as e:
            if conn:
                conn.rollback()
            logger.db_error(str(e), "log_hash_failure")
        finally:
            if conn:
                put_db_connection(conn)
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": error_code}
        )
    
    # PHASE 2: Deterministic timestamp model - preserve ingested_at from envelope
    # Do NOT overwrite ingested_at with current time (non-deterministic)
    # ingested_at from envelope is the authoritative timestamp
    original_ingested_at = envelope["ingested_at"]
    # Keep ingested_at as-is from envelope (deterministic)
    
    is_valid, error_code, timestamp_details = validate_timestamps(envelope)
    if not is_valid:
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO event_validation_log (
                        event_id, validation_status, validation_timestamp,
                        error_code, error_message, validation_details
                    )
                    VALUES (NULL, %s, NOW(), %s, %s, %s::jsonb)
                """, (
                    VALIDATION_STATUS_TIMESTAMP_VALIDATION_FAILED,
                    error_code,
                    timestamp_details.get("error") if timestamp_details else None,
                    json.dumps(timestamp_details) if timestamp_details else None
                ))
            conn.commit()
            logger.warning(f"Timestamp validation failed: {error_code}", event_id=envelope.get("event_id"))
        except Exception as e:
            if conn:
                conn.rollback()
            logger.db_error(str(e), "log_timestamp_failure")
        finally:
            if conn:
                put_db_connection(conn)
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": error_code, "validation_details": timestamp_details}
        )
    
    late_arrival = timestamp_details.get("late_arrival", False)
    arrival_latency_seconds = timestamp_details.get("arrival_latency_seconds")
    
    conn = None
    try:
        conn = get_db_connection()
        event_id = envelope["event_id"]
        
        if check_duplicate(conn, event_id):
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO event_validation_log (
                        event_id, validation_status, validation_timestamp,
                        error_code, error_message
                    )
                    VALUES (%s, %s, %s, %s, %s)
                """, (event_id, VALIDATION_STATUS_DUPLICATE_REJECTED, "DUPLICATE_EVENT_ID", "Event ID already exists"))
            conn.commit()
            logger.info(f"Duplicate event rejected", event_id=event_id)
            
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_code": "DUPLICATE_EVENT_ID"}
            )
        
        # GA-BLOCKING: Record event ingestion for operational telemetry
        if _metrics_available:
            metrics = get_metrics()
            if metrics:
                metrics.record_event_ingested()
        
        # Phase 10 requirement: Store event with integrity verification
        try:
            store_event(conn, envelope, VALIDATION_STATUS_VALID, late_arrival, arrival_latency_seconds)
        except ValueError as e:
            # Phase 10 requirement: Integrity violation (hash-chain, sequence monotonicity, idempotency)
            error_msg = str(e)
            logger.error(f"Integrity violation during event storage: {error_msg}", event_id=event_id)
            
            # Log integrity violation to event_validation_log
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO event_validation_log (
                        event_id, validation_status, validation_timestamp,
                        error_code, error_message
                    )
                    VALUES (%s, %s, %s, %s, %s)
                """, (event_id, VALIDATION_STATUS_INTEGRITY_CHAIN_BROKEN, "INTEGRITY_VIOLATION", error_msg))
            conn.commit()
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error_code": "INTEGRITY_VIOLATION", "error_message": error_msg}
            )
        
        logger.info(f"Event ingested successfully", event_id=event_id, component=envelope.get("component"))
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"event_id": event_id, "status": "accepted"}
        )
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        # Security: Sanitize exception message before logging
        try:
            from common.security.redaction import sanitize_exception
            safe_error = sanitize_exception(e)
        except ImportError:
            safe_error = str(e)
        logger.error(f"Failed to ingest event: {safe_error}", event_id=envelope.get("event_id"))
        # Security: Never expose full error details in response (avoid secret leakage)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "INTERNAL_ERROR"}
        )
    finally:
        if conn:
            put_db_connection(conn)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            return {"status": "healthy", "component": "ingest"}
        finally:
            put_db_connection(conn)
    except Exception as e:
        # Security: Sanitize exception message before logging
        try:
            from common.security.redaction import sanitize_exception
            safe_error = sanitize_exception(e)
        except ImportError:
            safe_error = str(e)
        logger.error(f"Health check failed: {safe_error}")
        # Security: Never expose full error details in response (avoid secret leakage)
        raise HTTPException(status_code=503, detail={"status": "unhealthy"})

if __name__ == "__main__":
    try:
        port = int(config.get('RANSOMEYE_INGEST_PORT', 8000))
        logger.startup(f"Starting ingest service on port {port}")
        uvicorn.run(app, host="0.0.0.0", port=port, log_config=None)
    except KeyboardInterrupt:
        logger.shutdown("Received interrupt, shutting down")
        shutdown_handler.exit(ExitCode.SUCCESS)
    except Exception as e:
        # Security: Sanitize exception message before logging
        try:
            from common.security.redaction import sanitize_exception
            safe_error = sanitize_exception(e)
        except ImportError:
            safe_error = str(e)
        logger.fatal(f"Fatal error: {safe_error}")
        shutdown_handler.exit(ExitCode.FATAL_ERROR)
