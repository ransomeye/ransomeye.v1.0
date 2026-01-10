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
except ImportError as e:
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
config_loader.optional('RANSOMEYE_DB_USER', default='ransomeye')
config_loader.optional('RANSOMEYE_INGEST_PORT', default='8000', validator=validate_port)
config_loader.optional('RANSOMEYE_EVENT_ENVELOPE_SCHEMA_PATH', 
                      default='/opt/ransomeye/etc/contracts/event-envelope.schema.json',
                      validator=lambda v: validate_path(v, must_exist=True))
config_loader.optional('RANSOMEYE_LOG_DIR', default='/var/log/ransomeye',
                      validator=lambda v: validate_path(v, must_exist=False, must_be_writable=True))
config_loader.optional('RANSOMEYE_DB_POOL_MIN', default='2', validator=lambda v: int(v))
config_loader.optional('RANSOMEYE_DB_POOL_MAX', default='20', validator=lambda v: int(v))

# Load configuration (fail-fast on errors)
try:
    config = config_loader.load()
except ConfigError as e:
    exit_config_error(str(e))

# Phase 10 requirement: Structured logging
logger = setup_logging('ingest')
logger.startup("Ingest service starting", config_keys=list(config.keys()))

# Phase 10 requirement: Graceful shutdown handler
shutdown_handler = ShutdownHandler('ingest', cleanup_func=lambda: _cleanup())

# Database connection pool (Phase 10 requirement: Resource safety)
db_pool: Optional[pool.ThreadedConnectionPool] = None

def _init_db_pool():
    """Initialize database connection pool."""
    global db_pool
    try:
        min_conn = config.get('RANSOMEYE_DB_POOL_MIN', 2)
        max_conn = config.get('RANSOMEYE_DB_POOL_MAX', 20)
        
        db_pool = pool.ThreadedConnectionPool(
            min_conn, max_conn,
            host=config['RANSOMEYE_DB_HOST'],
            port=config['RANSOMEYE_DB_PORT'],
            database=config['RANSOMEYE_DB_NAME'],
            user=config['RANSOMEYE_DB_USER'],
            password=config['RANSOMEYE_DB_PASSWORD']
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
            logger.error(f"Error closing database pool: {e}")

def get_db_connection():
    """Get database connection from pool."""
    global db_pool
    if not db_pool:
        raise RuntimeError("Database pool not initialized")
    
    try:
        conn = db_pool.getconn()
        if conn:
            return conn
    except Exception as e:
        logger.db_error(str(e), "get_connection")
        raise
    
    # Pool exhausted
    logger.resource_error("database_connections", "Connection pool exhausted")
    raise RuntimeError("Database connection pool exhausted")

def put_db_connection(conn):
    """Return database connection to pool."""
    global db_pool
    if db_pool:
        db_pool.putconn(conn)

# Load event envelope schema
SCHEMA_PATH = Path(config['RANSOMEYE_EVENT_ENVELOPE_SCHEMA_PATH'])
if not SCHEMA_PATH.exists():
    exit_startup_error(f"Event envelope schema not found: {SCHEMA_PATH}")

try:
    with open(SCHEMA_PATH, 'r') as f:
        EVENT_ENVELOPE_SCHEMA = json.load(f)
    logger.info(f"Event envelope schema loaded", schema_path=str(SCHEMA_PATH))
except Exception as e:
    exit_startup_error(f"Failed to load event envelope schema: {e}")

# Phase 10 requirement: Check disk space for log directory
LOG_DIR = Path(config.get('RANSOMEYE_LOG_DIR', '/var/log/ransomeye'))
try:
    if not LOG_DIR.exists():
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    check_disk_space(LOG_DIR, min_bytes=100 * 1024 * 1024)  # 100MB minimum
except Exception as e:
    logger.warning(f"Disk space check failed: {e}")

# Event validation status enum
VALIDATION_STATUS_VALID = "VALID"
VALIDATION_STATUS_DUPLICATE_REJECTED = "DUPLICATE_REJECTED"
VALIDATION_STATUS_SCHEMA_VALIDATION_FAILED = "SCHEMA_VALIDATION_FAILED"
VALIDATION_STATUS_TIMESTAMP_VALIDATION_FAILED = "TIMESTAMP_VALIDATION_FAILED"
VALIDATION_STATUS_INTEGRITY_CHAIN_BROKEN = "INTEGRITY_CHAIN_BROKEN"

app = FastAPI(title="RansomEye Ingest Service", version="1.0.0")
app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.on_event("startup")
async def startup_event():
    """FastAPI startup event."""
    try:
        _init_db_pool()
        logger.startup("Ingest service started successfully")
    except Exception as e:
        logger.fatal(f"Startup failed: {e}")
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
    """Store event in database."""
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
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.db_error(str(e), "store_event", event_id=envelope.get("event_id"))
        raise
    finally:
        cur.close()

@app.post("/events")
async def ingest_event(request: Request):
    """Ingest event endpoint."""
    if shutdown_handler.is_shutdown_requested():
        raise HTTPException(status_code=503, detail={"error_code": "SERVICE_SHUTTING_DOWN"})
    
    try:
        envelope = await request.json()
    except Exception as e:
        logger.error(f"Invalid JSON in request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_JSON", "error_message": str(e)}
        )
    
    is_valid, error_code, validation_details = validate_schema(envelope)
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
                    VALIDATION_STATUS_SCHEMA_VALIDATION_FAILED,
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
                    INSERT INTO event_validation_log (
                        event_id, validation_status, validation_timestamp,
                        error_code, error_message
                    )
                    VALUES (NULL, %s, NOW(), %s, %s)
                """, (VALIDATION_STATUS_INTEGRITY_CHAIN_BROKEN, error_code, "Hash mismatch"))
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
    
    original_ingested_at = envelope["ingested_at"]
    ingested_at_updated = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    envelope["ingested_at"] = ingested_at_updated
    
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
                    VALUES (%s, %s, NOW(), %s, %s)
                """, (event_id, VALIDATION_STATUS_DUPLICATE_REJECTED, "DUPLICATE_EVENT_ID", "Event ID already exists"))
            conn.commit()
            logger.info(f"Duplicate event rejected", event_id=event_id)
            
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_code": "DUPLICATE_EVENT_ID"}
            )
        
        store_event(conn, envelope, VALIDATION_STATUS_VALID, late_arrival, arrival_latency_seconds)
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
        logger.error(f"Failed to ingest event: {e}", event_id=envelope.get("event_id"))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "INTERNAL_ERROR", "error_message": str(e)}
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
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail={"status": "unhealthy", "error": str(e)})

if __name__ == "__main__":
    try:
        port = int(config.get('RANSOMEYE_INGEST_PORT', 8000))
        logger.startup(f"Starting ingest service on port {port}")
        uvicorn.run(app, host="0.0.0.0", port=port, log_config=None)
    except KeyboardInterrupt:
        logger.shutdown("Received interrupt, shutting down")
        shutdown_handler.exit(ExitCode.SUCCESS)
    except Exception as e:
        logger.fatal(f"Fatal error: {e}")
        shutdown_handler.exit(ExitCode.FATAL_ERROR)
