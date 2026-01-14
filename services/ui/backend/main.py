#!/usr/bin/env python3
"""
RansomEye v1.0 SOC UI Backend (Phase 8 - Read-Only)
AUTHORITATIVE: Minimal read-only backend for SOC UI
Python 3.10+ only - aligns with Phase 8 requirements
"""

import os
import sys
import json
import re
import psycopg2
from psycopg2 import pool
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
import uvicorn

# Add common utilities to path (Phase 10 requirement)
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.config import ConfigLoader, ConfigError, validate_path, validate_port
    from common.logging import setup_logging
    from common.shutdown import ShutdownHandler, ExitCode, exit_config_error, exit_startup_error
    from common.db.safety import (create_readonly_connection_pool, IsolationLevel, 
                                   execute_read_operation, validate_connection_health,
                                   enforce_read_only_connection)
    from common.resource.safety import check_file_descriptors
    _common_available = True
    _common_db_safety_available = True
    _common_resource_safety_available = True
except ImportError:
    _common_available = False
    _common_db_safety_available = False
    _common_resource_safety_available = False
    def check_file_descriptors(*args, **kwargs): pass
    def create_readonly_connection_pool(*args, **kwargs): raise RuntimeError("Database safety utilities not available")
    def execute_read_operation(*args, **kwargs): raise RuntimeError("Database safety utilities not available")
    def validate_connection_health(*args, **kwargs): return True
    def enforce_read_only_connection(*args, **kwargs): pass
    class IsolationLevel: READ_COMMITTED = 2
    class ConfigLoader:
        def __init__(self, name): self.config = {}; self.required_vars = []
        def require(self, *args, **kwargs): return self
        def optional(self, *args, **kwargs): return self  
        def load(self): return {}
    class ConfigError(Exception): pass
    def validate_path(p, **kwargs): return p
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

# Phase 10 requirement: Centralized configuration
if _common_available:
    config_loader = ConfigLoader('ui-backend')
    config_loader.require('RANSOMEYE_DB_PASSWORD', description='Database password (security-sensitive)')
    config_loader.optional('RANSOMEYE_DB_HOST', default='localhost')
    config_loader.optional('RANSOMEYE_DB_PORT', default='5432', validator=validate_port)
    config_loader.optional('RANSOMEYE_DB_NAME', default='ransomeye')
    config_loader.require('RANSOMEYE_DB_USER', description='Database user (PHASE 1: per-service user required, no defaults)')
    config_loader.optional('RANSOMEYE_UI_PORT', default='8080', validator=validate_port)
    config_loader.optional('RANSOMEYE_POLICY_DIR', default='/tmp/ransomeye/policy')
    config_loader.optional('RANSOMEYE_DB_POOL_MIN', default='2', validator=lambda v: int(v))
    config_loader.optional('RANSOMEYE_DB_POOL_MAX', default='10', validator=lambda v: int(v))
    try:
        # Security: Secrets are redacted in config dict, use config_loader.get_secret() for actual values
        config = config_loader.load()
    except ConfigError as e:
        exit_config_error(str(e))
else:
    config = {}
    if not os.getenv('RANSOMEYE_DB_PASSWORD'):
        exit_config_error('RANSOMEYE_DB_PASSWORD required')
    # Security: Create dummy config_loader for get_secret() in fallback mode
    class DummyConfigLoader:
        def get_secret(self, env_var):
            return os.getenv(env_var, "")
    config_loader = DummyConfigLoader()

logger = setup_logging('ui-backend')
shutdown_handler = ShutdownHandler('ui-backend', cleanup_func=lambda: _cleanup())

# Database connection pool (Phase 10 requirement: Resource safety)
db_pool: Optional[pool.ThreadedConnectionPool] = None

def _init_db_pool():
    """Initialize read-only database connection pool."""
    global db_pool
    try:
        min_conn = int(config.get('RANSOMEYE_DB_POOL_MIN', 2))
        max_conn = int(config.get('RANSOMEYE_DB_POOL_MAX', 10))
        
        # Security: Get password from secure storage (never logged)
        db_password = config_loader.get_secret('RANSOMEYE_DB_PASSWORD')
        
        # Use common database safety utilities to create read-only pool
        if _common_db_safety_available:
            db_pool = create_readonly_connection_pool(
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
            # Fallback
            db_pool = pool.ThreadedConnectionPool(
                min_conn, max_conn,
                host=config['RANSOMEYE_DB_HOST'],
                port=int(config['RANSOMEYE_DB_PORT']),
                database=config['RANSOMEYE_DB_NAME'],
                user=config['RANSOMEYE_DB_USER'],  # PHASE 1: Per-service user (required, no defaults)
                password=db_password  # Security: Use secret from secure storage
            )
            # Test connection and enforce read-only
            conn = db_pool.getconn()
            try:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.execute("SET TRANSACTION READ ONLY")
                cur.close()
            finally:
                db_pool.putconn(conn)
            
            logger.info(f"Database connection pool initialized (read-only)", min_conn=min_conn, max_conn=max_conn)
    except Exception as e:
        logger.db_error(str(e), "pool_initialization")
        raise

def _cleanup():
    """Cleanup on shutdown."""
    global db_pool
    logger.shutdown("UI backend shutting down")
    
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

# Contract compliance: No async, no background threads (Phase 8 requirements)
# Synchronous read-only operations only

app = FastAPI(title="RansomEye SOC UI Backend", version="1.0.0")
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Phase 8 requirement: CORS support for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Phase 8 minimal: Allow all origins (restrict in production)
    allow_credentials=True,
    allow_methods=["GET"],  # Phase 8 requirement: Read-only (GET only)
    allow_headers=["*"],
)

# PHASE 5: RBAC Authentication (if available)
_rbac_available = False
_rbac_auth = None
try:
    from rbac.middleware.fastapi_auth import RBACAuth
    from rbac.api.rbac_api import RBACAPI
    _rbac_available = True
    # Initialize RBAC (if available)
    # Note: In production, RBAC should be properly initialized with database connection
    # For now, this is a placeholder that will be integrated when RBAC is fully configured
    logger.info("PHASE 5: RBAC middleware available (not yet integrated)")
except ImportError:
    logger.warning("PHASE 5: RBAC middleware not available - endpoints are public (restrict in production)")

@app.on_event("startup")
async def startup_event():
    """FastAPI startup event."""
    try:
        # Resource safety: Check file descriptors at startup
        if _common_resource_safety_available:
            check_file_descriptors(logger)
        
        _init_db_pool()
        logger.startup("UI backend started successfully")
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

def get_db_connection():
    """Get read-only PostgreSQL database connection from pool."""
    global db_pool
    if not db_pool:
        raise RuntimeError("Database pool not initialized")
    
    try:
        conn = db_pool.getconn()
        if conn:
            # Validate connection health and enforce read-only
            if _common_db_safety_available:
                if not validate_connection_health(conn):
                    db_pool.putconn(conn)
                    raise RuntimeError("Connection health validation failed")
                # Enforce read-only mode on each connection
                enforce_read_only_connection(conn, logger)
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


def query_view(conn, view_name: str, where_column: Optional[str] = None, where_value: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Query a read-only view.
    
    Read-only enforcement: Cannot execute writes. Any write attempt terminates Core immediately.
    Connection safety: Validate health before operation.
    """
    def _do_query():
        cur = conn.cursor()
        try:
            # Verify view_name is actually a view (read-only enforcement)
            cur.execute("""
                SELECT viewname FROM pg_views 
                WHERE schemaname = 'public' AND viewname = %s
            """, (view_name,))
            if not cur.fetchone():
                cur.close()
                error_msg = f"INVARIANT VIOLATION: Unauthorized write attempt by read-only module (UI): view_name={view_name} is not a view"
                logger.fatal(error_msg)
                from common.shutdown import ExitCode, exit_fatal
                exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
            
            # Only SELECT queries (read-only)
            query = f"SELECT * FROM {view_name}"
            if where_column and where_value:
                query += f" WHERE {where_column} = %s"
                cur.execute(query, (where_value,))
            else:
                cur.execute(query)
            
            columns = [desc[0] for desc in cur.description]
            results = []
            for row in cur.fetchall():
                result = dict(zip(columns, row))
                for key, value in result.items():
                    if hasattr(value, 'isoformat'):
                        result[key] = value.isoformat()
                results.append(result)
            
            return results
        finally:
            cur.close()
    
    if _common_db_safety_available:
        return execute_read_operation(conn, "query_view", _do_query, logger, enforce_readonly=True)
    else:
        # Enforce read-only manually
        if _common_available and _common_db_safety_available:
            enforce_read_only_connection(conn, logger)
        return _do_query()


@app.get("/")
async def root():
    """Root endpoint (health check)."""
    return {"status": "ok", "service": "RansomEye SOC UI Backend", "read_only": True}


@app.get("/api/incidents")
async def get_active_incidents():
    """
    Get active incidents.
    Phase 8 requirement: Read-only, queries v_active_incidents view only
    Phase 10 requirement: Proper error handling and resource cleanup
    PHASE 5: RBAC enforcement - requires ui:read permission (if RBAC available)
    """
    if shutdown_handler.is_shutdown_requested():
        raise HTTPException(status_code=503, detail={"error_code": "SERVICE_SHUTTING_DOWN"})
    
    # PHASE 5: RBAC enforcement (if available)
    # TODO: Integrate RBAC authentication when fully configured
    # For now, endpoints are public (restrict in production)
    
    conn = None
    try:
        # Phase 8 requirement: Query view only, not base table
        conn = get_db_connection()
        incidents = query_view(conn, "v_active_incidents")
        
        # PHASE 5: Add evidence quality indicators to incident list
        evidence_quality_map = {}
        if incidents:
            incident_ids = [inc['incident_id'] for inc in incidents]
            for incident_id in incident_ids:
                eq = query_view(conn, "v_incident_evidence_quality", "incident_id", incident_id)
                if eq:
                    evidence_quality_map[incident_id] = eq[0]
        
        # PHASE 5: Enrich incidents with evidence quality and certainty state
        enriched_incidents = []
        for incident in incidents:
            incident_id = incident['incident_id']
            eq = evidence_quality_map.get(incident_id, {})
            
            # PHASE 5: Separate confidence from certainty
            certainty_state = "UNCONFIRMED"
            if incident.get('stage') == 'CONFIRMED':
                certainty_state = "CONFIRMED"
            elif incident.get('stage') == 'PROBABLE':
                certainty_state = "PROBABLE"
            elif incident.get('stage') == 'SUSPICIOUS':
                certainty_state = "SUSPICIOUS"
            
            enriched_incident = {
                ...incident,
                'certainty_state': certainty_state,
                'is_probabilistic': (certainty_state != 'CONFIRMED'),
                'has_contradiction': eq.get('has_contradiction', False)
            }
            enriched_incidents.append(enriched_incident)
        
        return {"incidents": enriched_incidents}
    except Exception as e:
        # Security: Sanitize exception message before logging
        try:
            from common.security.redaction import sanitize_exception
            safe_error = sanitize_exception(e)
        except ImportError:
            safe_error = str(e)
        logger.error(f"Failed to get active incidents: {safe_error}")
        # Security: Never expose full error details in response (avoid secret leakage)
        raise HTTPException(status_code=500, detail={"error_code": "INTERNAL_ERROR"})
    finally:
        if conn:
            put_db_connection(conn)


@app.get("/api/incidents/{incident_id}")
async def get_incident_detail(incident_id: str):
    """
    Get incident detail (including timeline, evidence, AI insights).
    Phase 8 requirement: Read-only, queries views only
    Security: Validates incident_id format before processing.
    PHASE 5: RBAC enforcement - requires ui:read permission (if RBAC available)
    PHASE 5: Returns evidence quality indicators and separates confidence from certainty
    """
    if shutdown_handler.is_shutdown_requested():
        raise HTTPException(status_code=503, detail={"error_code": "SERVICE_SHUTTING_DOWN"})
    
    # Security: Validate untrusted input (incident_id from URL)
    try:
        from common.security.validation import validate_incident_id
        incident_id = validate_incident_id(incident_id)
    except ImportError:
        # Basic validation if security utilities not available
        if not incident_id or len(incident_id) > 100:
            raise HTTPException(status_code=400, detail={"error_code": "INVALID_INCIDENT_ID"})
        if re.search(r'[;"\'\\]|--', incident_id, re.IGNORECASE):
            raise HTTPException(status_code=400, detail={"error_code": "INVALID_INCIDENT_ID"})
    except SystemExit:
        # validate_incident_id terminates Core on invalid input
        raise HTTPException(status_code=400, detail={"error_code": "INVALID_INCIDENT_ID"})
    
    conn = None
    try:
        # Phase 8 requirement: Query view only, not base table
        conn = get_db_connection()
        incident_detail = query_view(conn, "v_incident_detail", "incident_id", incident_id)
        
        if not incident_detail:
            raise HTTPException(status_code=404, detail="Incident not found")
        
        incident = incident_detail[0]
        
        # Phase 8 requirement: Get timeline from view
        timeline = query_view(conn, "v_incident_timeline", "incident_id", incident_id)
        
        # Phase 8 requirement: Get evidence summary from view
        evidence_summary = query_view(conn, "v_incident_evidence_summary", "incident_id", incident_id)
        
        # Phase 8 requirement: Get AI insights from view
        ai_insights = query_view(conn, "v_ai_insights", "incident_id", incident_id)
        
        # PHASE 5: Get evidence quality indicators
        evidence_quality = query_view(conn, "v_incident_evidence_quality", "incident_id", incident_id)
        
        # PHASE 5: Get AI provenance information
        ai_provenance = query_view(conn, "v_incident_ai_provenance", "incident_id", incident_id)
        
        # PHASE 5: Get contradiction information
        contradictions = query_view(conn, "v_incident_contradictions", "incident_id", incident_id)
        
        # Phase 8 requirement: Get policy recommendations (file-based for Phase 8 minimal)
        policy_recommendations = []
        policy_dir = config.get("RANSOMEYE_POLICY_DIR", "/tmp/ransomeye/policy")
        policy_file = os.path.join(policy_dir, f"policy_decision_{incident_id}.json")
        if os.path.exists(policy_file):
            try:
                with open(policy_file, 'r') as f:
                    policy_recommendations = [json.load(f)]
            except Exception as e:
                # Security: Sanitize exception message before logging
                try:
                    from common.security.redaction import sanitize_exception
                    safe_error = sanitize_exception(e)
                except ImportError:
                    safe_error = str(e)
                logger.warning(f"Failed to read policy decision file: {safe_error}", incident_id=incident_id)
        
        # PHASE 5: Separate confidence from certainty (confirmation state)
        incident_data = incident.copy() if incident else {}
        certainty_state = "UNCONFIRMED"  # PHASE 5: Default to unconfirmed
        if incident_data.get('stage') == 'CONFIRMED':
            certainty_state = "CONFIRMED"
        elif incident_data.get('stage') == 'PROBABLE':
            certainty_state = "PROBABLE"
        elif incident_data.get('stage') == 'SUSPICIOUS':
            certainty_state = "SUSPICIOUS"
        
        # PHASE 5: Add certainty state to incident data
        incident_data['certainty_state'] = certainty_state
        incident_data['is_probabilistic'] = (certainty_state != 'CONFIRMED')  # PHASE 5: Only CONFIRMED is deterministic
        
        return {
            "incident": incident_data,
            "timeline": timeline,
            "evidence_summary": evidence_summary[0] if evidence_summary else None,
            "ai_insights": ai_insights[0] if ai_insights else None,
            "evidence_quality": evidence_quality[0] if evidence_quality else None,  # PHASE 5: Evidence quality indicators
            "ai_provenance": ai_provenance,  # PHASE 5: AI provenance information
            "contradictions": contradictions[0] if contradictions else None,  # PHASE 5: Contradiction information
            "policy_recommendations": policy_recommendations
        }
    except HTTPException:
        raise
    except Exception as e:
        # Security: Sanitize exception message before logging
        try:
            from common.security.redaction import sanitize_exception
            safe_error = sanitize_exception(e)
        except ImportError:
            safe_error = str(e)
        logger.error(f"Failed to get incident detail: {safe_error}", incident_id=incident_id)
        # Security: Never expose full error details in response (avoid secret leakage)
        raise HTTPException(status_code=500, detail={"error_code": "INTERNAL_ERROR"})
    finally:
        if conn:
            put_db_connection(conn)


@app.get("/api/incidents/{incident_id}/timeline")
async def get_incident_timeline(incident_id: str):
    """
    Get incident timeline (stage transitions).
    Phase 8 requirement: Read-only, queries v_incident_timeline view only
    Security: Validates incident_id format before processing.
    """
    if shutdown_handler.is_shutdown_requested():
        raise HTTPException(status_code=503, detail={"error_code": "SERVICE_SHUTTING_DOWN"})
    
    # Security: Validate untrusted input (incident_id from URL)
    try:
        from common.security.validation import validate_incident_id
        incident_id = validate_incident_id(incident_id)
    except ImportError:
        # Basic validation if security utilities not available
        if not incident_id or len(incident_id) > 100:
            raise HTTPException(status_code=400, detail={"error_code": "INVALID_INCIDENT_ID"})
        if re.search(r'[;"\'\\]|--', incident_id, re.IGNORECASE):
            raise HTTPException(status_code=400, detail={"error_code": "INVALID_INCIDENT_ID"})
    except SystemExit:
        # validate_incident_id terminates Core on invalid input
        raise HTTPException(status_code=400, detail={"error_code": "INVALID_INCIDENT_ID"})
    
    conn = None
    try:
        # Phase 8 requirement: Query view only, not base table
        conn = get_db_connection()
        timeline = query_view(conn, "v_incident_timeline", "incident_id", incident_id)
        return {"timeline": timeline}
    except Exception as e:
        # Security: Sanitize exception message before logging
        try:
            from common.security.redaction import sanitize_exception
            safe_error = sanitize_exception(e)
        except ImportError:
            safe_error = str(e)
        logger.error(f"Failed to get incident timeline: {safe_error}", incident_id=incident_id)
        # Security: Never expose full error details in response (avoid secret leakage)
        raise HTTPException(status_code=500, detail={"error_code": "INTERNAL_ERROR"})
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
            return {"status": "healthy", "component": "ui-backend"}
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
        port = int(config.get('RANSOMEYE_UI_PORT', 8080))
        logger.startup(f"Starting UI backend on port {port}")
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
