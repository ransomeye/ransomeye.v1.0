#!/usr/bin/env python3
"""
RansomEye v1.0 SOC UI Backend (Phase 4 - Authenticated + RBAC)
AUTHORITATIVE: Production-grade UI backend with JWT auth and RBAC enforcement
Python 3.10+ only
"""

import os
import sys
import json
import re
import uuid
from functools import wraps
from datetime import datetime, timezone
import psycopg2
from psycopg2 import pool
from typing import List, Dict, Any, Optional, Tuple
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
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
    from common.security.secrets import validate_signing_key
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

# Phase 4 requirement: Centralized configuration (auth + RBAC)
if _common_available:
    config_loader = ConfigLoader('ui-backend')
    config_loader.require('RANSOMEYE_DB_PASSWORD', description='Database password (security-sensitive)')
    config_loader.optional('RANSOMEYE_DB_HOST', default='localhost')
    config_loader.optional('RANSOMEYE_DB_PORT', default='5432', validator=validate_port)
    config_loader.optional('RANSOMEYE_DB_NAME', default='ransomeye')
    config_loader.require('RANSOMEYE_DB_USER', description='Database user (PHASE 1: per-service user required, no defaults)')
    config_loader.optional('RANSOMEYE_UI_PORT', default='8080', validator=validate_port)
    config_loader.optional('RANSOMEYE_UI_BIND_ADDRESS', default='127.0.0.1')
    config_loader.optional('RANSOMEYE_POLICY_DIR', default='/tmp/ransomeye/policy')
    config_loader.optional('RANSOMEYE_UI_CORS_ALLOW_ORIGINS', default='http://127.0.0.1:5173,http://localhost:5173')
    config_loader.optional('RANSOMEYE_UI_CORS_ALLOW_METHODS', default='GET,POST')
    config_loader.optional('RANSOMEYE_UI_COOKIE_SECURE', default='true')
    config_loader.optional('RANSOMEYE_UI_COOKIE_SAMESITE', default='strict')
    config_loader.optional('RANSOMEYE_UI_ACCESS_TOKEN_TTL_SECONDS', default='900', validator=lambda v: int(v))
    config_loader.optional('RANSOMEYE_UI_REFRESH_TOKEN_TTL_SECONDS', default='604800', validator=lambda v: int(v))
    config_loader.require('RANSOMEYE_UI_JWT_SIGNING_KEY', description='JWT signing key (no defaults allowed)')
    config_loader.require('RANSOMEYE_AUDIT_LEDGER_PATH', description='Audit ledger path (auth decisions)')
    config_loader.require('RANSOMEYE_AUDIT_LEDGER_KEY_DIR', description='Audit ledger signing key directory')
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

# JWT config validation (fail-closed)
if _common_available:
    _jwt_signing_key = validate_signing_key('RANSOMEYE_UI_JWT_SIGNING_KEY', min_length=32, fail_on_default=True)
else:
    _jwt_signing_key = os.getenv('RANSOMEYE_UI_JWT_SIGNING_KEY')
    if not _jwt_signing_key:
        exit_config_error('RANSOMEYE_UI_JWT_SIGNING_KEY required')
    if len(_jwt_signing_key) < 32:
        exit_config_error('RANSOMEYE_UI_JWT_SIGNING_KEY too short (minimum 32 characters)')

_jwt_issuer = 'ransomeye-ui'
_jwt_audience = 'ransomeye-ui'

# Audit ledger configuration
_audit_ledger_path = config.get('RANSOMEYE_AUDIT_LEDGER_PATH', os.getenv('RANSOMEYE_AUDIT_LEDGER_PATH'))
_audit_ledger_key_dir = config.get('RANSOMEYE_AUDIT_LEDGER_KEY_DIR', os.getenv('RANSOMEYE_AUDIT_LEDGER_KEY_DIR'))

if not _audit_ledger_path or not _audit_ledger_key_dir:
    exit_config_error("RANSOMEYE_AUDIT_LEDGER_PATH and RANSOMEYE_AUDIT_LEDGER_KEY_DIR are required")

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

# Contract compliance: No async, no background threads (read-only UI)
# Synchronous read-only operations only

app = FastAPI(title="RansomEye SOC UI Backend", version="1.0.0")
app.add_middleware(GZipMiddleware, minimum_size=1000)

def _parse_cors_origins(raw: str) -> List[str]:
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if not origins:
        exit_config_error("RANSOMEYE_UI_CORS_ALLOW_ORIGINS must be a non-empty allowlist")
    if any(origin == "*" for origin in origins):
        exit_config_error("CORS wildcard origins are not allowed; use explicit allowlist")
    return origins

cors_origins = _parse_cors_origins(config.get('RANSOMEYE_UI_CORS_ALLOW_ORIGINS', ''))
cors_methods = [m.strip().upper() for m in config.get('RANSOMEYE_UI_CORS_ALLOW_METHODS', 'GET,POST').split(",") if m.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=cors_methods,
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# RBAC + Auth initialization (fail-closed)
try:
    from rbac.middleware.fastapi_auth import RBACAuth
    from rbac.api.rbac_api import RBACAPI
    _audit_ledger_path_mod = os.path.join(_project_root, 'audit-ledger')
    if os.path.exists(_audit_ledger_path_mod) and _audit_ledger_path_mod not in sys.path:
        sys.path.insert(0, _audit_ledger_path_mod)
    from api import AuditLedger
    from auth import (
        create_access_token,
        create_refresh_token,
        decode_token,
        hash_token,
        utc_now
    )
except ImportError as exc:
    logger.fatal(f"RBAC/Auth imports failed: {exc}")
    exit_startup_error("RBAC/Auth dependencies missing")

rbac_api = None
rbac_auth = None
audit_ledger = None

def _init_rbac_backend() -> None:
    global rbac_api, rbac_auth, audit_ledger
    if os.getenv("RANSOMEYE_RBAC_FORCE_UNAVAILABLE") == "1":
        raise RuntimeError("RBAC backend forced unavailable")

    db_params = {
        "host": config.get('RANSOMEYE_DB_HOST', 'localhost'),
        "port": int(config.get('RANSOMEYE_DB_PORT', 5432)),
        "database": config.get('RANSOMEYE_DB_NAME', 'ransomeye'),
        "user": config.get('RANSOMEYE_DB_USER'),
        "password": config_loader.get_secret('RANSOMEYE_DB_PASSWORD')
    }

    audit_ledger = AuditLedger(
        ledger_path=validate_path(_audit_ledger_path, must_exist=False),
        key_dir=validate_path(_audit_ledger_key_dir, must_exist=True)
    )

    rbac_api = RBACAPI(
        db_conn_params=db_params,
        ledger_path=validate_path(_audit_ledger_path, must_exist=False),
        ledger_key_dir=validate_path(_audit_ledger_key_dir, must_exist=True)
    )

    rbac_auth = RBACAuth(
        rbac_api=rbac_api,
        jwt_signing_key=_jwt_signing_key.decode("utf-8") if isinstance(_jwt_signing_key, (bytes, bytearray)) else _jwt_signing_key,
        jwt_issuer=_jwt_issuer,
        jwt_audience=_jwt_audience,
        logger=logger,
        auth_audit_logger=_audit_auth_decision
    )

    _validate_rbac_tables()
    _validate_role_permissions()

def _validate_rbac_tables() -> None:
    try:
        conn = psycopg2.connect(
            host=config.get('RANSOMEYE_DB_HOST', 'localhost'),
            port=config.get('RANSOMEYE_DB_PORT', 5432),
            database=config.get('RANSOMEYE_DB_NAME', 'ransomeye'),
            user=config.get('RANSOMEYE_DB_USER'),
            password=config_loader.get_secret('RANSOMEYE_DB_PASSWORD')
        )
        cur = conn.cursor()
        required_tables = [
            "rbac_users",
            "rbac_user_roles",
            "rbac_role_permissions",
            "rbac_permission_audit",
            "rbac_refresh_tokens"
        ]
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        existing = {row[0] for row in cur.fetchall()}
        missing = [t for t in required_tables if t not in existing]
        cur.close()
        conn.close()
        if missing:
            raise RuntimeError(f"Missing RBAC tables: {', '.join(missing)}")
    except Exception as exc:
        raise RuntimeError(f"RBAC schema validation failed: {exc}") from exc

def _validate_role_permissions() -> None:
    try:
        conn = psycopg2.connect(
            host=config.get('RANSOMEYE_DB_HOST', 'localhost'),
            port=config.get('RANSOMEYE_DB_PORT', 5432),
            database=config.get('RANSOMEYE_DB_NAME', 'ransomeye'),
            user=config.get('RANSOMEYE_DB_USER'),
            password=config_loader.get_secret('RANSOMEYE_DB_PASSWORD')
        )
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM rbac_role_permissions")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        if count <= 0:
            raise RuntimeError("RBAC role-permission mappings not initialized")
    except Exception as exc:
        raise RuntimeError(f"RBAC role permission validation failed: {exc}") from exc

def _audit_auth_decision(entry: Dict[str, Any]) -> None:
    if not audit_ledger:
        return
    audit_ledger.append(
        component="ui-backend",
        component_instance_id="ui-auth",
        action_type="ui_auth_decision",
        subject={"type": "auth", "id": entry.get("user_id", "unknown")},
        actor={"type": "request", "identifier": entry.get("path", "unknown")},
        payload=entry
    )

def require_ui_permission(permission: str, resource_type: str = "ui"):
    """
    Decorator to enforce UI permission via RBAC.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            if not rbac_auth:
                raise HTTPException(status_code=503, detail={"error_code": "RBAC_UNAVAILABLE"})
            current_user = getattr(request.state, "user", None)
            if not current_user or not current_user.get("user_id"):
                raise HTTPException(status_code=401, detail={"error_code": "AUTH_REQUIRED"})
            user_id = current_user["user_id"]
            try:
                allowed = rbac_auth.permission_checker.check_permission(
                    user_id=user_id,
                    permission=permission,
                    resource_type=resource_type,
                    resource_id=None
                )
                if not allowed:
                    raise HTTPException(status_code=403, detail={"error_code": "PERMISSION_DENIED"})
            except HTTPException:
                raise
            except Exception as exc:
                logger.error(f"RBAC check failed: {exc}")
                raise HTTPException(status_code=503, detail={"error_code": "RBAC_UNAVAILABLE"})
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class LoginRequest(BaseModel):
    username: str
    password: str


def _cookie_secure() -> bool:
    return str(config.get("RANSOMEYE_UI_COOKIE_SECURE", "true")).lower() == "true"


def _cookie_samesite() -> str:
    samesite = str(config.get("RANSOMEYE_UI_COOKIE_SAMESITE", "strict")).lower()
    return samesite if samesite in ("strict", "lax", "none") else "strict"


def _set_refresh_cookie(response: Response, token: str, max_age: int) -> None:
    response.set_cookie(
        key="ransomeye_refresh",
        value=token,
        httponly=True,
        secure=_cookie_secure(),
        samesite=_cookie_samesite(),
        path="/auth",
        max_age=max_age
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.set_cookie(
        key="ransomeye_refresh",
        value="",
        httponly=True,
        secure=_cookie_secure(),
        samesite=_cookie_samesite(),
        path="/auth",
        max_age=0
    )


@app.middleware("http")
async def _auth_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)
    if request.url.path in ("/auth/login", "/auth/refresh"):
        return await call_next(request)
    if not rbac_auth:
        return JSONResponse(status_code=503, content={"error_code": "RBAC_UNAVAILABLE"})

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return JSONResponse(status_code=401, content={"error_code": "AUTH_REQUIRED"})
    token = auth_header.split(" ", 1)[1].strip()
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    try:
        current_user = await rbac_auth.get_current_user(request, credentials)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    request.state.user = current_user
    return await call_next(request)

# PHASE 5: Helper function to check if action requires warning
def requires_operator_warning(evidence_quality: Optional[Dict[str, Any]], 
                               ai_insights: Optional[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """
    PHASE 5: Determine if operator action requires warning.
    
    Args:
        evidence_quality: Evidence quality indicators dictionary
        ai_insights: AI insights dictionary
        
    Returns:
        Tuple of (requires_warning: bool, warning_reasons: List[str])
    """
    requires_warning = False
    warning_reasons = []
    
    if not evidence_quality:
        return False, []
    
    # Check for contradictions
    if evidence_quality.get('has_contradiction', False):
        requires_warning = True
        warning_reasons.append('Contradictions detected in evidence')
    
    # Check for incomplete evidence
    completeness = evidence_quality.get('evidence_completeness', 'UNKNOWN')
    if completeness in ['INCOMPLETE', 'NO_EVIDENCE']:
        requires_warning = True
        warning_reasons.append(f'Evidence is {completeness.lower().replace("_", " ")}')
    
    # Check for missing AI provenance
    if ai_insights and not evidence_quality.get('has_ai_provenance', False):
        requires_warning = True
        warning_reasons.append('AI output is advisory only (missing provenance)')
    
    return requires_warning, warning_reasons

@app.on_event("startup")
async def startup_event():
    """FastAPI startup event."""
    try:
        # Resource safety: Check file descriptors at startup
        if _common_resource_safety_available:
            check_file_descriptors(logger)

        _init_rbac_backend()
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


@app.post("/auth/login")
async def login(request: Request, payload: LoginRequest):
    """
    Authenticate user and issue access + refresh tokens.
    """
    if not rbac_api:
        raise HTTPException(status_code=503, detail={"error_code": "RBAC_UNAVAILABLE"})

    try:
        user = rbac_api.authenticate_user(payload.username, payload.password)
    except Exception as exc:
        _audit_auth_decision({
            "decision": "DENY",
            "reason": "rbac_auth_error",
            "username": payload.username,
            "path": "/auth/login",
            "timestamp": utc_now().isoformat()
        })
        raise HTTPException(status_code=503, detail={"error_code": "RBAC_UNAVAILABLE"}) from exc

    if not user:
        _audit_auth_decision({
            "decision": "DENY",
            "reason": "invalid_credentials",
            "username": payload.username,
            "path": "/auth/login",
            "timestamp": utc_now().isoformat()
        })
        raise HTTPException(status_code=401, detail={"error_code": "AUTH_FAILED"})
    if not user.get("role"):
        _audit_auth_decision({
            "decision": "DENY",
            "reason": "missing_role_assignment",
            "user_id": user.get("user_id"),
            "path": "/auth/login",
            "timestamp": utc_now().isoformat()
        })
        raise HTTPException(status_code=403, detail={"error_code": "ROLE_REQUIRED"})

    access_ttl = int(config.get("RANSOMEYE_UI_ACCESS_TOKEN_TTL_SECONDS", 900))
    refresh_ttl = int(config.get("RANSOMEYE_UI_REFRESH_TOKEN_TTL_SECONDS", 604800))
    token_id = str(uuid.uuid4())

    access_token, access_exp = create_access_token(
        user=user,
        signing_key=_jwt_signing_key.decode("utf-8") if isinstance(_jwt_signing_key, (bytes, bytearray)) else _jwt_signing_key,
        issuer=_jwt_issuer,
        audience=_jwt_audience,
        ttl_seconds=access_ttl
    )
    refresh_token, refresh_exp = create_refresh_token(
        user_id=user["user_id"],
        token_id=token_id,
        signing_key=_jwt_signing_key.decode("utf-8") if isinstance(_jwt_signing_key, (bytes, bytearray)) else _jwt_signing_key,
        issuer=_jwt_issuer,
        audience=_jwt_audience,
        ttl_seconds=refresh_ttl
    )

    rbac_api.store_refresh_token(
        token_id=token_id,
        user_id=user["user_id"],
        token_hash=hash_token(refresh_token),
        expires_at=refresh_exp,
        user_agent=request.headers.get("User-Agent"),
        ip_address=request.client.host if request.client else None
    )

    response = JSONResponse({
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": access_ttl,
        "user": {
            "user_id": user["user_id"],
            "username": user["username"],
            "role": user.get("role")
        }
    })
    _set_refresh_cookie(response, refresh_token, refresh_ttl)

    _audit_auth_decision({
        "decision": "ALLOW",
        "reason": "login_success",
        "user_id": user["user_id"],
        "path": "/auth/login",
        "timestamp": utc_now().isoformat()
    })
    return response


@app.post("/auth/refresh")
async def refresh(request: Request):
    """
    Refresh access token using HttpOnly refresh cookie (rotation enforced).
    """
    if not rbac_api:
        raise HTTPException(status_code=503, detail={"error_code": "RBAC_UNAVAILABLE"})

    refresh_cookie = request.cookies.get("ransomeye_refresh")
    if not refresh_cookie:
        _audit_auth_decision({
            "decision": "DENY",
            "reason": "missing_refresh_cookie",
            "path": "/auth/refresh",
            "timestamp": utc_now().isoformat()
        })
        raise HTTPException(status_code=401, detail={"error_code": "AUTH_REQUIRED"})

    try:
        payload = decode_token(
            refresh_cookie,
            signing_key=_jwt_signing_key.decode("utf-8") if isinstance(_jwt_signing_key, (bytes, bytearray)) else _jwt_signing_key,
            issuer=_jwt_issuer,
            audience=_jwt_audience
        )
    except Exception:
        _audit_auth_decision({
            "decision": "DENY",
            "reason": "invalid_refresh_token",
            "path": "/auth/refresh",
            "timestamp": utc_now().isoformat()
        })
        raise HTTPException(status_code=401, detail={"error_code": "INVALID_TOKEN"})

    if payload.get("token_type") != "refresh":
        _audit_auth_decision({
            "decision": "DENY",
            "reason": "invalid_token_type",
            "path": "/auth/refresh",
            "timestamp": utc_now().isoformat()
        })
        raise HTTPException(status_code=401, detail={"error_code": "INVALID_TOKEN_TYPE"})

    token_id = payload.get("jti")
    user_id = payload.get("sub")
    if not token_id or not user_id:
        _audit_auth_decision({
            "decision": "DENY",
            "reason": "missing_refresh_claims",
            "path": "/auth/refresh",
            "timestamp": utc_now().isoformat()
        })
        raise HTTPException(status_code=401, detail={"error_code": "INVALID_TOKEN"})

    token_record = rbac_api.validate_refresh_token(token_id, hash_token(refresh_cookie))
    if not token_record:
        _audit_auth_decision({
            "decision": "DENY",
            "reason": "refresh_token_revoked",
            "user_id": user_id,
            "path": "/auth/refresh",
            "timestamp": utc_now().isoformat()
        })
        raise HTTPException(status_code=401, detail={"error_code": "INVALID_TOKEN"})

    # Rotate refresh token
    rbac_api.revoke_refresh_token(token_id, reason="rotated")
    new_token_id = str(uuid.uuid4())
    refresh_ttl = int(config.get("RANSOMEYE_UI_REFRESH_TOKEN_TTL_SECONDS", 604800))
    access_ttl = int(config.get("RANSOMEYE_UI_ACCESS_TOKEN_TTL_SECONDS", 900))

    new_refresh, refresh_exp = create_refresh_token(
        user_id=user_id,
        token_id=new_token_id,
        signing_key=_jwt_signing_key.decode("utf-8") if isinstance(_jwt_signing_key, (bytes, bytearray)) else _jwt_signing_key,
        issuer=_jwt_issuer,
        audience=_jwt_audience,
        ttl_seconds=refresh_ttl
    )
    rbac_api.store_refresh_token(
        token_id=new_token_id,
        user_id=user_id,
        token_hash=hash_token(new_refresh),
        expires_at=refresh_exp,
        user_agent=request.headers.get("User-Agent"),
        ip_address=request.client.host if request.client else None
    )

    user = rbac_api.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail={"error_code": "AUTH_FAILED"})
    user_role = rbac_api.get_user_role(user_id)
    if not user_role:
        raise HTTPException(status_code=403, detail={"error_code": "ROLE_REQUIRED"})

    access_token, _ = create_access_token(
        user={**user, "role": user_role},
        signing_key=_jwt_signing_key.decode("utf-8") if isinstance(_jwt_signing_key, (bytes, bytearray)) else _jwt_signing_key,
        issuer=_jwt_issuer,
        audience=_jwt_audience,
        ttl_seconds=access_ttl
    )

    response = JSONResponse({
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": access_ttl
    })
    _set_refresh_cookie(response, new_refresh, refresh_ttl)
    _audit_auth_decision({
        "decision": "ALLOW",
        "reason": "refresh_success",
        "user_id": user_id,
        "path": "/auth/refresh",
        "timestamp": utc_now().isoformat()
    })
    return response


@app.post("/auth/logout")
@require_ui_permission("incident:view_all", resource_type="incident")
async def logout(request: Request):
    """
    Logout current session (refresh token revoked).
    """
    if not rbac_api:
        raise HTTPException(status_code=503, detail={"error_code": "RBAC_UNAVAILABLE"})

    current_user = getattr(request.state, "user", {})
    user_id = current_user.get("user_id")

    refresh_cookie = request.cookies.get("ransomeye_refresh")
    if refresh_cookie:
        try:
            payload = decode_token(
                refresh_cookie,
                signing_key=_jwt_signing_key.decode("utf-8") if isinstance(_jwt_signing_key, (bytes, bytearray)) else _jwt_signing_key,
                issuer=_jwt_issuer,
                audience=_jwt_audience
            )
            token_id = payload.get("jti")
            if token_id:
                rbac_api.revoke_refresh_token(token_id, reason="logout")
        except Exception:
            if user_id:
                rbac_api.revoke_refresh_tokens_for_user(user_id, reason="logout")
    elif user_id:
        rbac_api.revoke_refresh_tokens_for_user(user_id, reason="logout")

    response = JSONResponse({"status": "logged_out"})
    _clear_refresh_cookie(response)
    if user_id:
        _audit_auth_decision({
            "decision": "ALLOW",
            "reason": "logout_success",
            "user_id": user_id,
            "path": "/auth/logout",
            "timestamp": utc_now().isoformat()
        })
    return response


@app.get("/auth/me")
@require_ui_permission("incident:view_all", resource_type="incident")
async def auth_me(request: Request):
    current_user = getattr(request.state, "user", {})
    return {"user": current_user}


@app.get("/auth/permissions")
@require_ui_permission("incident:view_all", resource_type="incident")
async def auth_permissions(request: Request):
    current_user = getattr(request.state, "user", {})
    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail={"error_code": "AUTH_REQUIRED"})
    if not rbac_auth:
        raise HTTPException(status_code=503, detail={"error_code": "RBAC_UNAVAILABLE"})
    return rbac_auth.get_user_permissions(user_id)


@app.get("/")
@require_ui_permission("system:view_logs", resource_type="system")
async def root():
    """Root endpoint (health check)."""
    return {"status": "ok", "service": "RansomEye SOC UI Backend", "read_only": True}


@app.get("/api/incidents")
@require_ui_permission("incident:view_all", resource_type="incident")
async def get_active_incidents(request: Request):
    """
    Get active incidents.
    Read-only requirement: queries v_active_incidents view only
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
        # Read-only requirement: Query view only, not base table
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
            
            enriched_incident = incident.copy()
            enriched_incident['certainty_state'] = certainty_state
            enriched_incident['is_probabilistic'] = (certainty_state != 'CONFIRMED')
            enriched_incident['has_contradiction'] = eq.get('has_contradiction', False)
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
@require_ui_permission("incident:view", resource_type="incident")
async def get_incident_detail(request: Request, incident_id: str):
    """
    Get incident detail (including timeline, evidence, AI insights).
    Read-only requirement: queries views only
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
        # Read-only requirement: Query view only, not base table
        conn = get_db_connection()
        incident_detail = query_view(conn, "v_incident_detail", "incident_id", incident_id)
        
        if not incident_detail:
            raise HTTPException(status_code=404, detail="Incident not found")
        
        incident = incident_detail[0]
        
        # Read-only requirement: Get timeline from view
        timeline = query_view(conn, "v_incident_timeline", "incident_id", incident_id)
        
        # Read-only requirement: Get evidence summary from view
        evidence_summary = query_view(conn, "v_incident_evidence_summary", "incident_id", incident_id)
        
        # Read-only requirement: Get AI insights from view
        ai_insights = query_view(conn, "v_ai_insights", "incident_id", incident_id)
        
        # PHASE 5: Get evidence quality indicators
        evidence_quality = query_view(conn, "v_incident_evidence_quality", "incident_id", incident_id)
        
        # PHASE 5: Get AI provenance information
        ai_provenance = query_view(conn, "v_incident_ai_provenance", "incident_id", incident_id)
        
        # PHASE 5: Get contradiction information
        contradictions = query_view(conn, "v_incident_contradictions", "incident_id", incident_id)
        
        # Read-only requirement: Get policy recommendations (file-based when DB empty)
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
        
        # PHASE 5: Determine if operator action requires warning
        eq_data = evidence_quality[0] if evidence_quality else None
        ai_data = ai_insights[0] if ai_insights else None
        requires_warning, warning_reasons = requires_operator_warning(eq_data, ai_data)
        
        # PHASE 5: Add warning information to policy recommendations
        enriched_policy_recommendations = []
        for rec in policy_recommendations:
            enriched_rec = rec.copy()
            enriched_rec['requires_warning'] = requires_warning
            enriched_rec['warning_reasons'] = warning_reasons
            enriched_policy_recommendations.append(enriched_rec)
        
        return {
            "incident": incident_data,
            "timeline": timeline,
            "evidence_summary": evidence_summary[0] if evidence_summary else None,
            "ai_insights": ai_data,
            "evidence_quality": eq_data,  # PHASE 5: Evidence quality indicators
            "ai_provenance": ai_provenance,  # PHASE 5: AI provenance information
            "contradictions": contradictions[0] if contradictions else None,  # PHASE 5: Contradiction information
            "policy_recommendations": enriched_policy_recommendations  # PHASE 5: Policy recommendations with warnings
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
@require_ui_permission("incident:view", resource_type="incident")
async def get_incident_timeline(request: Request, incident_id: str):
    """
    Get incident timeline (stage transitions).
    Read-only requirement: queries v_incident_timeline view only
    Security: Validates incident_id format before processing.
    PHASE 5: RBAC enforcement - requires ui:read permission (if RBAC available)
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
        # Read-only requirement: Query view only, not base table
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

_last_successful_cycle = None
_failure_reason = None

@app.get("/health")
@require_ui_permission("system:view_logs", resource_type="system")
async def health_check(request: Request):
    """Health check endpoint."""
    global _last_successful_cycle, _failure_reason
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            _last_successful_cycle = datetime.now(timezone.utc).isoformat()
            _failure_reason = None
            return {
                "status": "healthy",
                "component": "ui-backend",
                "last_successful_cycle": _last_successful_cycle,
                "failure_reason": _failure_reason
            }
        finally:
            put_db_connection(conn)
    except Exception as e:
        # Security: Sanitize exception message before logging
        try:
            from common.security.redaction import sanitize_exception
            safe_error = sanitize_exception(e)
        except ImportError:
            safe_error = str(e)
        _failure_reason = safe_error
        logger.error(f"Health check failed: {safe_error}")
        # Security: Never expose full error details in response (avoid secret leakage)
        raise HTTPException(status_code=503, detail={
            "status": "unhealthy",
            "last_successful_cycle": _last_successful_cycle,
            "failure_reason": _failure_reason
        })

def _assert_supervised():
    if os.getenv("RANSOMEYE_SUPERVISED") != "1":
        error_msg = "UI Backend must be started by Core orchestrator"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)
    core_pid = os.getenv("RANSOMEYE_CORE_PID")
    core_token = os.getenv("RANSOMEYE_CORE_TOKEN")
    if not core_pid or not core_token:
        error_msg = "UI Backend missing Core supervision metadata"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)
    try:
        uuid.UUID(core_token)
    except Exception:
        error_msg = "UI Backend invalid Core token"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)
    if os.getppid() != int(core_pid):
        error_msg = "UI Backend parent PID mismatch"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)

if __name__ == "__main__":
    try:
        _assert_supervised()
        port = int(config.get('RANSOMEYE_UI_PORT', 8080))
        bind_address = config.get('RANSOMEYE_UI_BIND_ADDRESS', '127.0.0.1')
        logger.startup(f"Starting UI backend on {bind_address}:{port}")
        uvicorn.run(app, host=bind_address, port=port, log_config=None)
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
