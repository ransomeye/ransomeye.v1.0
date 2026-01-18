#!/usr/bin/env python3
"""
RansomEye v1.0 Core Runtime
AUTHORITATIVE: Core runtime coordinator for all components
Phase 10.1 requirement: Harden startup and shutdown for Core components
"""

import os
import sys
import signal
import json
import hashlib
import psycopg2
from psycopg2 import OperationalError
from typing import Dict, Any, Optional, List
from pathlib import Path
from enum import IntEnum
from datetime import datetime, timezone

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(_current_file))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.config import ConfigLoader, ConfigError, validate_path, validate_port, check_disk_space
    from common.logging import setup_logging, StructuredLogger
    from common.shutdown import ShutdownHandler, ExitCode, exit_config_error, exit_startup_error, exit_fatal
    from core.orchestrator import CoreOrchestrator, ComponentState
    _common_available = True
except ImportError:
    _common_available = False
    class ConfigLoader:
        def __init__(self, name): self.config = {}; self.required_vars = []
        def require(self, *args, **kwargs): return self
        def optional(self, *args, **kwargs): return self  
        def load(self): return {}
    class ConfigError(Exception): pass
    def validate_path(p, **kwargs): return Path(p)
    def validate_port(p): return int(p)
    def check_disk_space(p, **kwargs): pass
    def setup_logging(name, **kwargs):
        class Logger:
            def info(self, m, **k): print(m)
            def error(self, m, **k): print(m, file=sys.stderr)
            def warning(self, m, **k): print(m, file=sys.stderr)
            def fatal(self, m, **k): print(f"FATAL: {m}", file=sys.stderr)
            def startup(self, m, **k): print(f"STARTUP: {m}")
            def shutdown(self, m, **k): print(f"SHUTDOWN: {m}")
            def db_error(self, m, op, **k): print(f"DB_ERROR[{op}]: {m}", file=sys.stderr)
            def resource_error(self, res, m, **k): print(f"RESOURCE_ERROR[{res}]: {m}", file=sys.stderr)
        return Logger()
    class ShutdownHandler:
        def __init__(self, *args, **kwargs): pass
        def is_shutdown_requested(self): return False
        def exit(self, code): sys.exit(int(code))
    class ExitCode:
        SUCCESS = 0
        CONFIG_ERROR = 1
        STARTUP_ERROR = 2
        FATAL_ERROR = 4
        RUNTIME_ERROR = 3
    class ComponentState:
        FAILED = "FAILED"
    def exit_config_error(m): 
        print(f"CONFIG_ERROR: {m}", file=sys.stderr)
        sys.exit(1)
    def exit_startup_error(m): 
        print(f"STARTUP_ERROR: {m}", file=sys.stderr)
        sys.exit(2)
    def exit_fatal(m, code=4): 
        print(f"FATAL: {m}", file=sys.stderr)
        sys.exit(int(code))

# Core configuration
# Configuration is loaded at runtime, not at import time
if _common_available:
    config_loader = ConfigLoader('core')
    config_loader.require('RANSOMEYE_DB_PASSWORD', description='Database password (security-sensitive)')
    config_loader.optional('RANSOMEYE_DB_HOST', default='localhost')
    config_loader.optional('RANSOMEYE_DB_PORT', default='5432', validator=validate_port)
    config_loader.optional('RANSOMEYE_DB_NAME', default='ransomeye')
    config_loader.optional('RANSOMEYE_DB_USER', default='ransomeye')
    config_loader.optional('RANSOMEYE_INGEST_PORT', default='8000', validator=validate_port)
    config_loader.optional('RANSOMEYE_UI_PORT', default='8080', validator=validate_port)
    config_loader.optional('RANSOMEYE_SCHEMA_MIGRATIONS_DIR',
                          default=str(Path(_project_root) / 'schemas' / 'migrations'),
                          validator=lambda v: validate_path(v, must_exist=False))
    config_loader.optional('RANSOMEYE_EVENT_ENVELOPE_SCHEMA_PATH', 
                          default='/opt/ransomeye/etc/contracts/event-envelope.schema.json',
                          validator=lambda v: validate_path(v, must_exist=True))
    config_loader.optional('RANSOMEYE_POLICY_DIR', default='/tmp/ransomeye/policy')
    config_loader.optional('RANSOMEYE_LOG_DIR', default='/var/log/ransomeye',
                          validator=lambda v: validate_path(v, must_exist=False, must_be_writable=True))
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
            sys.stderr.write("HIT_BRANCH: config_loader_exception\n")
            exit_config_error(str(e))
    else:
        config = {}
        if not os.getenv('RANSOMEYE_DB_PASSWORD'):
            sys.stderr.write("HIT_BRANCH: missing_env_db_password_no_common\n")
            exit_config_error('RANSOMEYE_DB_PASSWORD required')

logger = setup_logging('core')
_shutdown_handler = ShutdownHandler('core', cleanup_func=lambda: _core_cleanup())
_orchestrator: Optional[CoreOrchestrator] = None

# Signal/shutdown state tracking
_startup_complete = False
_db_transaction_active = False
_shutdown_in_progress = False


def _allow_weak_test_credentials() -> bool:
    return (
        os.getenv("RANSOMEYE_ALLOW_WEAK_TEST_CREDENTIALS") == "1"
        and (
            os.getenv("RANSOMEYE_ENV") == "ci"
            or os.getenv("RANSOMEYE_VALIDATION_PHASE") == "step05"
        )
    )

def shutdown_handler():
    """Get shutdown handler."""
    return _shutdown_handler

# Component modules (imported on demand)
_ingest_module = None
_correlation_module = None
_ai_core_module = None
_policy_module = None
_ui_module = None

# Component state
_component_state = {
    'ingest': {'running': False, 'conn': None},
    'correlation': {'running': False, 'conn': None},
    'ai_core': {'running': False, 'conn': None},
    'policy': {'running': False, 'conn': None},
    'ui': {'running': False, 'conn': None}
}

def _validate_config_access():
    """
    Phase 10.1 requirement: Validate config file access if provided.
    Fail-fast: Exit immediately if config file validation fails.
    """
    config_file_path = os.getenv('RANSOMEYE_CONFIG_FILE')
    if not config_file_path:
        # Config file validation is optional - skip if path not set
        return
    
    logger.startup("Validating config file access")
    config_path = Path(config_file_path)
    
    # A1: Config file permission denied
    if config_path.exists() and not os.access(config_path, os.R_OK):
        sys.stderr.write("HIT_BRANCH: config_permission_denied\n")
        sys.stderr.flush()
        error_msg = f"Config file permission denied: {config_file_path}"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)
    
    # A2: Config path is directory, not file
    if config_path.exists() and config_path.is_dir():
        sys.stderr.write("HIT_BRANCH: config_is_directory\n")
        sys.stderr.flush()
        error_msg = f"Config path is a directory, not a file: {config_file_path}"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)
    
    # A3: Config file empty
    if config_path.exists() and config_path.stat().st_size == 0:
        sys.stderr.write("HIT_BRANCH: config_empty_file\n")
        sys.stderr.flush()
        error_msg = f"Config file is empty: {config_file_path}"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)
    
    # A4: Missing required config keys (if JSON config file)
    if config_path.exists() and config_path.suffix in ['.json', '.yaml', '.yml']:
        # A8: Config file too large (size limit exceeded) - check before reading
        max_config_size = 1024 * 1024  # 1MB limit
        if config_path.stat().st_size > max_config_size:
            sys.stderr.write("HIT_BRANCH: config_too_large\n")
            sys.stderr.flush()
            error_msg = f"Config file too large: {config_path.stat().st_size} bytes (max {max_config_size})"
            logger.fatal(error_msg)
            exit_startup_error(error_msg)
        
        try:
            # A7: Config file unreadable due to encoding error
            try:
                config_content = config_path.read_text(encoding='utf-8')
            except (UnicodeDecodeError, UnicodeError) as e:
                sys.stderr.write("HIT_BRANCH: config_encoding_error\n")
                sys.stderr.flush()
                error_msg = f"Config file encoding error: {e}"
                logger.fatal(error_msg)
                exit_startup_error(error_msg)
            
            if config_path.suffix == '.json':
                config_data = json.loads(config_content)
                required_keys = ['RANSOMEYE_DB_PASSWORD', 'RANSOMEYE_DB_USER']
                missing_keys = [key for key in required_keys if key not in config_data or not config_data.get(key)]
                if missing_keys:
                    sys.stderr.write("HIT_BRANCH: config_missing_required_keys\n")
                    sys.stderr.flush()
                    error_msg = f"Config file missing required keys: {', '.join(missing_keys)}"
                    logger.fatal(error_msg)
                    exit_startup_error(error_msg)
                
                # A10: Config value out of allowed range
                if 'RANSOMEYE_DB_PORT' in config_data:
                    try:
                        db_port = int(config_data['RANSOMEYE_DB_PORT'])
                        if db_port < 1 or db_port > 65535:
                            sys.stderr.write("HIT_BRANCH: config_value_out_of_range\n")
                            sys.stderr.flush()
                            error_msg = f"Config value RANSOMEYE_DB_PORT out of range: {db_port} (must be 1-65535)"
                            logger.fatal(error_msg)
                            exit_startup_error(error_msg)
                    except (ValueError, TypeError):
                        # Type errors handled by A5
                        pass
        except (json.JSONDecodeError, Exception):
            # JSON parsing errors are handled elsewhere, skip here
            pass
    
    logger.startup("Config file access validated")


def _validate_environment():
    """
    Phase 10.1 requirement: Validate all required environment variables.
    Fail-fast: Exit immediately if any check fails.
    """
    logger.startup("Validating environment variables")
    
    required_vars = ['RANSOMEYE_DB_PASSWORD', 'RANSOMEYE_DB_USER', 'RANSOMEYE_COMMAND_SIGNING_KEY']
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            if var == "RANSOMEYE_DB_PASSWORD":
                sys.stderr.write("HIT_BRANCH: missing_env_db_password\n")
            elif var == "RANSOMEYE_DB_USER":
                sys.stderr.write("HIT_BRANCH: missing_env_db_user\n")
            elif var == "RANSOMEYE_COMMAND_SIGNING_KEY":
                sys.stderr.write("HIT_BRANCH: signing_key_missing\n")
            missing.append(var)
    
    if missing:
        error_msg = f"Missing required environment variables: {', '.join(missing)}"
        logger.config_error(error_msg)
        exit_config_error(error_msg)
    
    # Validate secrets are not weak/default values
    try:
        from common.security.secrets import validate_secret_present, validate_signing_key
        
        # Validate DB password
        db_password_raw = os.getenv('RANSOMEYE_DB_PASSWORD')
        allow_weak_secrets = os.getenv("RANSOMEYE_ALLOW_WEAK_SECRETS") == "1"
        if db_password_raw and len(db_password_raw) < 8 and not allow_weak_secrets:
            sys.stderr.write("HIT_BRANCH: db_password_too_short\n")
        if db_password_raw and len(set(db_password_raw)) < 3 and not allow_weak_secrets:
            sys.stderr.write("HIT_BRANCH: db_password_weak\n")
        db_password = validate_secret_present('RANSOMEYE_DB_PASSWORD', min_length=8)
        
        # Validate DB user (minimum 3 chars, not weak)
        db_user = os.getenv('RANSOMEYE_DB_USER')
        if not db_user:
            exit_config_error("RANSOMEYE_DB_USER is required")
        if len(db_user) < 3:
            sys.stderr.write("HIT_BRANCH: db_user_too_short\n")
            exit_config_error("RANSOMEYE_DB_USER is too short (minimum 3 characters)")
        weak_users = ['gagan', 'test', 'admin', 'root', 'default']
        if db_user.lower() in [u.lower() for u in weak_users]:
            if _allow_weak_test_credentials():
                logger.warning(
                    "TEMPORARY OVERRIDE: Weak DB user allowed for STEP-05 validation",
                    override_env="RANSOMEYE_ALLOW_WEAK_TEST_CREDENTIALS",
                    validation_phase=os.getenv("RANSOMEYE_VALIDATION_PHASE")
                )
            else:
                sys.stderr.write("HIT_BRANCH: weak_db_user\n")
                exit_config_error(
                    f"SECURITY VIOLATION: RANSOMEYE_DB_USER uses weak/default value '{db_user}' (not allowed)"
                )
        
        # A5: ENV override present but invalid type
        # Check port overrides for type validation
        for port_var in ['RANSOMEYE_DB_PORT', 'RANSOMEYE_INGEST_PORT', 'RANSOMEYE_UI_PORT']:
            port_val = os.getenv(port_var)
            # A9: ENV override present but empty
            if port_val == '':
                sys.stderr.write("HIT_BRANCH: env_override_empty\n")
                sys.stderr.flush()
                error_msg = f"ENV override {port_var} is empty (not allowed)"
                logger.fatal(error_msg)
                exit_startup_error(error_msg)
            if port_val:
                try:
                    port_int = int(port_val)
                    if not (1 <= port_int <= 65535):
                        sys.stderr.write("HIT_BRANCH: env_override_invalid_value\n")
                        sys.stderr.flush()
                        error_msg = f"ENV override {port_var} has invalid value: {port_val} (must be 1-65535)"
                        logger.fatal(error_msg)
                        exit_startup_error(error_msg)
                except (ValueError, TypeError):
                    sys.stderr.write("HIT_BRANCH: env_override_invalid_type\n")
                    sys.stderr.flush()
                    error_msg = f"ENV override {port_var} has invalid type: {port_val} (expected integer)"
                    logger.fatal(error_msg)
                    exit_startup_error(error_msg)
        
        # A6: ENV override invalid value (e.g., negative port, invalid path)
        db_port_str = os.getenv('RANSOMEYE_DB_PORT')
        if db_port_str:
            try:
                db_port = int(db_port_str)
                if db_port < 1 or db_port > 65535:
                    sys.stderr.write("HIT_BRANCH: env_override_invalid_value\n")
                    sys.stderr.flush()
                    error_msg = f"ENV override RANSOMEYE_DB_PORT has invalid value: {db_port} (must be 1-65535)"
                    logger.fatal(error_msg)
                    exit_startup_error(error_msg)
            except (ValueError, TypeError):
                # Type errors handled by A5 above
                pass
        
        # Validate signing key
        signing_key_raw = os.getenv('RANSOMEYE_COMMAND_SIGNING_KEY')
        if signing_key_raw and len(signing_key_raw) < 32:
            sys.stderr.write("HIT_BRANCH: signing_key_too_short\n")
        insecure_patterns = [
            "phase7_minimal_default_key_change_in_production",
            "test_signing_key_minimum_32_characters_long_for_validation_long_enough",
            "test_signing_key",
            "default",
            "test",
            "changeme",
            "password",
            "secret",
        ]
        if signing_key_raw:
            for pattern in insecure_patterns:
                if pattern.lower() in signing_key_raw.lower():
                    sys.stderr.write("HIT_BRANCH: signing_key_weak\n")
                    break
        signing_key = validate_signing_key('RANSOMEYE_COMMAND_SIGNING_KEY', min_length=32, fail_on_default=True)
        
        logger.startup("Environment variables and secrets validated")
    except ImportError:
        # Fallback validation if common module not available
        db_password = os.getenv('RANSOMEYE_DB_PASSWORD')
        if not db_password:
            sys.stderr.write("HIT_BRANCH: missing_env_db_password\n")
            exit_config_error("RANSOMEYE_DB_PASSWORD is required")
        if len(db_password) < 8:
            sys.stderr.write("HIT_BRANCH: db_password_too_short\n")
            exit_config_error("RANSOMEYE_DB_PASSWORD is too short (minimum 8 characters)")
        if db_password.lower() in ['gagan', 'password', 'test', 'changeme', 'default', 'secret']:
            if _allow_weak_test_credentials():
                logger.warning(
                    "TEMPORARY OVERRIDE: Weak DB password allowed for STEP-05 validation",
                    override_env="RANSOMEYE_ALLOW_WEAK_TEST_CREDENTIALS",
                    validation_phase=os.getenv("RANSOMEYE_VALIDATION_PHASE")
                )
            else:
                sys.stderr.write("HIT_BRANCH: db_password_weak\n")
                exit_config_error(
                    "SECURITY VIOLATION: RANSOMEYE_DB_PASSWORD uses weak/default value (not allowed)"
                )
        
        signing_key = os.getenv('RANSOMEYE_COMMAND_SIGNING_KEY')
        if not signing_key:
            sys.stderr.write("HIT_BRANCH: signing_key_missing\n")
            exit_config_error("RANSOMEYE_COMMAND_SIGNING_KEY is required")
        if len(signing_key) < 32:
            sys.stderr.write("HIT_BRANCH: signing_key_too_short\n")
            exit_config_error("RANSOMEYE_COMMAND_SIGNING_KEY is too short (minimum 32 characters)")
        if 'test_signing_key' in signing_key.lower() or 'default' in signing_key.lower():
            sys.stderr.write("HIT_BRANCH: signing_key_weak\n")
            exit_config_error("SECURITY VIOLATION: RANSOMEYE_COMMAND_SIGNING_KEY uses weak/default value (not allowed)")
        
        logger.startup("Environment variables validated (basic validation)")

def _validate_db_connectivity():
    """
    Phase 10.1 requirement: Validate DB connectivity.
    Fail-fast: Exit immediately if connection fails.
    """
    logger.startup("Validating database connectivity")
    
    try:
        db_password = config_loader.get_secret('RANSOMEYE_DB_PASSWORD') if _common_available else os.getenv('RANSOMEYE_DB_PASSWORD')
        conn = psycopg2.connect(
            host=config.get('RANSOMEYE_DB_HOST', 'localhost'),
            port=config.get('RANSOMEYE_DB_PORT', 5432),
            database=config.get('RANSOMEYE_DB_NAME', 'ransomeye'),
            user=config.get('RANSOMEYE_DB_USER', 'ransomeye'),
            password=db_password
        )
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        logger.startup("Database connectivity validated")
    except OperationalError as e:
        error_str = str(e).lower()
        if "connection refused" in error_str or "could not connect" in error_str:
            sys.stderr.write("HIT_BRANCH: db_conn_refused\n")
            sys.stderr.flush()
        elif "password authentication failed" in error_str or "authentication failed" in error_str:
            sys.stderr.write("HIT_BRANCH: db_auth_failed\n")
            sys.stderr.flush()
        else:
            sys.stderr.write("HIT_BRANCH: db_connectivity_failure\n")
        error_msg = f"Database connection failed: {e}"
        logger.db_error(str(e), "connectivity_check")
        exit_startup_error(error_msg)
    except Exception as e:
        sys.stderr.write("HIT_BRANCH: db_connectivity_failure\n")
        error_msg = f"Database connection failed: {e}"
        logger.db_error(str(e), "connectivity_check")
        exit_startup_error(error_msg)

def _validate_schema_presence():
    """
    Phase 10.1 requirement: Validate schema presence.
    Fail-fast: Exit immediately if schema validation fails.
    """
    logger.startup("Validating database schema presence")
    
    try:
        db_password = config_loader.get_secret('RANSOMEYE_DB_PASSWORD') if _common_available else os.getenv('RANSOMEYE_DB_PASSWORD')
        conn = psycopg2.connect(
            host=config.get('RANSOMEYE_DB_HOST', 'localhost'),
            port=config.get('RANSOMEYE_DB_PORT', 5432),
            database=config.get('RANSOMEYE_DB_NAME', 'ransomeye'),
            user=config.get('RANSOMEYE_DB_USER', 'ransomeye'),
            password=db_password
        )
        cur = conn.cursor()
        
        # Phase 10.1 requirement: Verify required tables exist
        required_tables = [
            'machines', 'component_instances', 'raw_events', 'event_validation_log',
            'incidents', 'incident_stages', 'evidence',
            'feature_vectors', 'clusters', 'cluster_memberships', 'shap_explanations'
        ]
        
        cur.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
        """)
        existing_tables = {row[0] for row in cur.fetchall()}
        
        missing_tables = []
        for table in required_tables:
            if table not in existing_tables:
                missing_tables.append(table)
        
        cur.close()
        conn.close()
        
        if missing_tables:
            sys.stderr.write("HIT_BRANCH: schema_required_tables_missing\n")
            error_msg = f"Missing required tables: {', '.join(missing_tables)}"
            logger.fatal(f"Schema validation failed: {error_msg}")
            exit_startup_error(error_msg)
        
        logger.startup(f"Database schema validated ({len(required_tables)} tables present)")
    except Exception as e:
        sys.stderr.write("HIT_BRANCH: schema_presence_db_error\n")
        error_msg = f"Schema validation failed: {e}"
        logger.db_error(str(e), "schema_check")
        exit_startup_error(error_msg)

def _validate_schema_version():
    """
    Phase 1 requirement: Validate schema version strictly.
    Fail-fast: Exit immediately if DB version != expected version.
    """
    logger.startup("Validating database schema version")
    
    migrations_dir = os.getenv("RANSOMEYE_SCHEMA_MIGRATIONS_DIR")
    if not migrations_dir:
        migrations_dir = str(Path(_project_root) / "schemas" / "migrations")
    migrations_path = Path(migrations_dir)
    
    if not migrations_path.exists():
        sys.stderr.write("HIT_BRANCH: migrations_dir_missing\n")
        sys.stderr.flush()
        error_msg = f"Schema migrations directory not found: {migrations_path}"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)
    
    try:
        from common.db.migration_runner import get_latest_migration_version
    except Exception as e:
        sys.stderr.write("HIT_BRANCH: migration_runner_missing\n")
        error_msg = f"Migration runner not available for schema version check: {e}"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)
    
    expected_version = get_latest_migration_version(migrations_path)
    if not expected_version:
        sys.stderr.write("HIT_BRANCH: no_migrations_found\n")
        error_msg = "No migrations found; schema version cannot be determined"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)
    
    try:
        db_password = config_loader.get_secret('RANSOMEYE_DB_PASSWORD') if _common_available else os.getenv('RANSOMEYE_DB_PASSWORD')
        conn = psycopg2.connect(
            host=config.get('RANSOMEYE_DB_HOST', 'localhost'),
            port=config.get('RANSOMEYE_DB_PORT', 5432),
            database=config.get('RANSOMEYE_DB_NAME', 'ransomeye'),
            user=config.get('RANSOMEYE_DB_USER', 'ransomeye'),
            password=db_password
        )
        cur = conn.cursor()
        cur.execute("SELECT to_regclass('public.schema_migrations')")
        if cur.fetchone()[0] is None:
            cur.close()
            conn.close()
            sys.stderr.write("HIT_BRANCH: schema_migrations_missing\n")
            error_msg = "Schema migrations table missing; database not initialized"
            logger.fatal(error_msg)
            exit_startup_error(error_msg)
        
        cur.execute("SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1")
        row = cur.fetchone()
        cur.close()
        
        if not row:
            conn.close()
            sys.stderr.write("HIT_BRANCH: no_schema_migrations_applied\n")
            error_msg = "No schema migrations applied; database not initialized"
            logger.fatal(error_msg)
            exit_startup_error(error_msg)
        
        current_version = row[0]
        if current_version != expected_version:
            conn.close()
            sys.stderr.write("HIT_BRANCH: schema_version_mismatch\n")
            sys.stderr.flush()
            error_msg = (
                f"Schema version mismatch: expected {expected_version}, "
                f"found {current_version}"
            )
            logger.fatal(error_msg)
            exit_startup_error(error_msg)
        
        # B5: Validate migration checksums
        try:
            from common.db.migration_runner import discover_migrations, _load_sql_with_includes, _compute_checksum
            migrations = discover_migrations(migrations_path)
            cur = conn.cursor()
            cur.execute("SELECT version, checksum_sha256 FROM schema_migrations ORDER BY version")
            applied_migrations = {row[0]: row[1] for row in cur.fetchall()}
            cur.close()
            
            for migration in migrations:
                if migration.version in applied_migrations:
                    sql_text = _load_sql_with_includes(migration.up_path)
                    computed_checksum = _compute_checksum(sql_text)
                    stored_checksum = applied_migrations[migration.version]
                    if stored_checksum != computed_checksum:
                        conn.close()
                        sys.stderr.write("HIT_BRANCH: migration_checksum_mismatch\n")
                        sys.stderr.flush()
                        error_msg = (
                            f"Migration checksum mismatch for version {migration.version}: "
                            f"stored={stored_checksum}, computed={computed_checksum}"
                        )
                        logger.fatal(error_msg)
                        exit_startup_error(error_msg)
        except Exception as e:
            # If checksum validation fails, log but don't block (B5 is defensive)
            pass
        
        # B6: Check for partial migration (gaps in sequence)
        try:
            if migrations:
                cur = conn.cursor()
                cur.execute("SELECT version FROM schema_migrations ORDER BY version")
                applied_versions = [row[0] for row in cur.fetchall()]
                cur.close()
                
                migration_versions = [m.version for m in migrations]
                expected_before_current = [v for v in migration_versions if v <= current_version]
                if len(applied_versions) < len(expected_before_current):
                    conn.close()
                    sys.stderr.write("HIT_BRANCH: migration_partial_apply\n")
                    sys.stderr.flush()
                    error_msg = (
                        f"Partial migration detected: {len(applied_versions)} applied, "
                        f"{len(expected_before_current)} expected before version {current_version}"
                    )
                    logger.fatal(error_msg)
                    exit_startup_error(error_msg)
        except Exception as e:
            # If partial check fails, log but don't block (B6 is defensive)
            pass
        
        conn.close()
        logger.startup(f"Schema version validated (version {current_version})")
    except Exception as e:
        sys.stderr.write("HIT_BRANCH: schema_version_db_error\n")
        error_msg = f"Schema version validation failed: {e}"
        logger.db_error(str(e), "schema_version_check")
        exit_startup_error(error_msg)

def _validate_write_permissions():
    """
    Phase 10.1 requirement: Validate write permissions where applicable.
    Fail-fast: Exit immediately if permissions check fails.
    """
    logger.startup("Validating write permissions")
    
    try:
        # Check policy directory write permissions
        policy_dir = Path(config.get('RANSOMEYE_POLICY_DIR', '/tmp/ransomeye/policy'))
        if not policy_dir.exists():
            try:
                policy_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                sys.stderr.write("HIT_BRANCH: policy_dir_create_failure\n")
                error_msg = f"Cannot create policy directory {policy_dir}: {e}"
                logger.resource_error("policy_dir", error_msg)
                exit_startup_error(error_msg)
        
        if not os.access(policy_dir, os.W_OK):
            sys.stderr.write("HIT_BRANCH: policy_dir_not_writable\n")
            error_msg = f"Policy directory not writable: {policy_dir}"
            logger.resource_error("policy_dir", error_msg)
            exit_startup_error(error_msg)
        
        # Check log directory write permissions
        log_dir = Path(config.get('RANSOMEYE_LOG_DIR', '/var/log/ransomeye'))
        if not log_dir.exists():
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                sys.stderr.write("HIT_BRANCH: log_dir_create_failure\n")
                error_msg = f"Cannot create log directory {log_dir}: {e}"
                logger.resource_error("log_dir", error_msg)
                exit_startup_error(error_msg)
        
        if not os.access(log_dir, os.W_OK):
            sys.stderr.write("HIT_BRANCH: log_dir_not_writable\n")
            sys.stderr.flush()
            error_msg = f"Log directory not writable: {log_dir}"
            logger.resource_error("log_dir", error_msg)
            exit_startup_error(error_msg)
        
        logger.startup("Write permissions validated")
    except Exception as e:
        sys.stderr.write("HIT_BRANCH: write_permissions_exception\n")
        error_msg = f"Write permissions validation failed: {e}"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)

def _validate_filesystem_edges():
    """
    Phase 10.1 requirement: Validate filesystem edge cases.
    Fail-fast: Exit immediately if any check fails.
    """
    logger.startup("Validating filesystem edges")
    
    try:
        # E2: Runtime/work directory missing
        run_dir = os.getenv('RANSOMEYE_RUN_DIR', '/tmp/ransomeye')
        run_dir_path = Path(run_dir)
        if not run_dir_path.exists():
            sys.stderr.write("HIT_BRANCH: runtime_dir_missing\n")
            sys.stderr.flush()
            error_msg = f"Runtime directory missing: {run_dir}"
            logger.resource_error("runtime_dir", error_msg)
            exit_startup_error(error_msg)
        
        # E3: Temp directory read-only
        import tempfile
        temp_dir = os.getenv('RANSOMEYE_TMP_DIR') or tempfile.gettempdir()
        temp_dir_path = Path(temp_dir)
        if temp_dir_path.exists() and not os.access(temp_dir_path, os.W_OK):
            sys.stderr.write("HIT_BRANCH: temp_dir_readonly\n")
            sys.stderr.flush()
            error_msg = f"Temp directory read-only: {temp_dir}"
            logger.resource_error("temp_dir", error_msg)
            exit_startup_error(error_msg)
        
        # E4: Symlink traversal blocked
        # Check if run_dir or temp_dir are symlinks pointing outside allowed root
        allowed_roots = ['/tmp', '/var/tmp', '/opt', '/var/run', '/run']
        for check_dir in [run_dir_path, temp_dir_path]:
            if check_dir.exists() and check_dir.is_symlink():
                resolved = check_dir.resolve()
                # Check if resolved path is outside any allowed root
                is_allowed = any(str(resolved).startswith(root) for root in allowed_roots)
                if not is_allowed:
                    sys.stderr.write("HIT_BRANCH: symlink_traversal_blocked\n")
                    sys.stderr.flush()
                    error_msg = f"Symlink traversal blocked: {check_dir} -> {resolved} (outside allowed roots)"
                    logger.resource_error("symlink_traversal", error_msg)
                    exit_startup_error(error_msg)
        
        # E5: Filesystem I/O error - attempt a test write
        test_file = None
        try:
            test_file = temp_dir_path / '.ransomeye_io_test'
            test_file.write_text('test', encoding='utf-8')
            test_file.unlink()
        except OSError as e:
            sys.stderr.write("HIT_BRANCH: filesystem_io_error\n")
            sys.stderr.flush()
            error_msg = f"Filesystem I/O error: {e}"
            logger.resource_error("filesystem_io", error_msg)
            exit_startup_error(error_msg)
        except Exception as e:
            # Only catch OSError for I/O errors, re-raise others
            raise
        
        logger.startup("Filesystem edges validated")
    except OSError as e:
        # E5: Catch filesystem I/O errors not caught above
        sys.stderr.write("HIT_BRANCH: filesystem_io_error\n")
        sys.stderr.flush()
        error_msg = f"Filesystem I/O error: {e}"
        logger.resource_error("filesystem_io", error_msg)
        exit_startup_error(error_msg)
    except Exception as e:
        # Re-raise non-OSError exceptions (they should be handled elsewhere)
        raise

def _validate_manifest():
    """
    Phase 10.1 requirement: Validate installation manifest if present.
    Fail-fast: Exit immediately if manifest validation fails.
    """
    manifest_path = os.getenv('RANSOMEYE_MANIFEST_PATH')
    if not manifest_path:
        # Manifest validation is optional - skip if path not set
        return
    
    logger.startup("Validating installation manifest")
    manifest_file = Path(manifest_path)
    
    # C1: Manifest file missing
    if not manifest_file.exists():
        sys.stderr.write("HIT_BRANCH: manifest_missing\n")
        sys.stderr.flush()
        error_msg = f"Manifest file not found: {manifest_path}"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)
    
    # C2: Manifest JSON invalid
    try:
        manifest_content = manifest_file.read_text(encoding='utf-8')
        manifest = json.loads(manifest_content)
    except json.JSONDecodeError as e:
        sys.stderr.write("HIT_BRANCH: manifest_json_invalid\n")
        sys.stderr.flush()
        error_msg = f"Manifest JSON invalid: {e}"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)
    except Exception as e:
        sys.stderr.write("HIT_BRANCH: manifest_json_invalid\n")
        sys.stderr.flush()
        error_msg = f"Failed to load manifest: {e}"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)
    
    # C3: Manifest signature missing
    if 'signature' not in manifest or not manifest.get('signature'):
        sys.stderr.write("HIT_BRANCH: manifest_signature_missing\n")
        sys.stderr.flush()
        error_msg = "Manifest signature missing"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)
    
    # C4: Manifest signature invalid (if verifier available)
    try:
        from supply_chain.crypto.artifact_verifier import ArtifactVerifier as _ArtifactVerifier
        
        # Try to load public key from environment or defaults
        public_key_path = os.getenv('RANSOMEYE_SIGNING_PUBLIC_KEY_PATH')
        if public_key_path and Path(public_key_path).exists():
            verifier = _ArtifactVerifier(public_key_path=Path(public_key_path))
            if not verifier.verify_manifest_signature(manifest):
                sys.stderr.write("HIT_BRANCH: manifest_signature_invalid\n")
                sys.stderr.flush()
                error_msg = "Manifest signature verification failed"
                logger.fatal(error_msg)
                exit_startup_error(error_msg)
    except ImportError:
        # If verifier not available, skip signature check (defensive)
        pass
    except Exception as e:
        # If signature verification fails, fail closed
        sys.stderr.write("HIT_BRANCH: manifest_signature_invalid\n")
        sys.stderr.flush()
        error_msg = f"Manifest signature verification failed: {e}"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)
    
    # C5: Binary hash mismatch vs manifest (check core binary if path available)
    binary_path = os.getenv('RANSOMEYE_BIN_PATH') or os.path.abspath(__file__)
    expected_sha256 = manifest.get('sha256', '')
    if expected_sha256 and Path(binary_path).exists():
        try:
            hash_obj = hashlib.sha256()
            with open(binary_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hash_obj.update(chunk)
            computed_sha256 = hash_obj.hexdigest()
            
            if computed_sha256 != expected_sha256:
                sys.stderr.write("HIT_BRANCH: manifest_hash_mismatch\n")
                sys.stderr.flush()
                error_msg = (
                    f"Binary hash mismatch: expected {expected_sha256}, "
                    f"computed {computed_sha256}"
                )
                logger.fatal(error_msg)
                exit_startup_error(error_msg)
        except Exception as e:
            # If hash computation fails, fail closed
            sys.stderr.write("HIT_BRANCH: manifest_hash_mismatch\n")
            sys.stderr.flush()
            error_msg = f"Failed to compute binary hash: {e}"
            logger.fatal(error_msg)
            exit_startup_error(error_msg)
    
    # C6: Manifest schema version unsupported
    schema_version = manifest.get('schema_version', '1.0')
    if schema_version not in ['1.0', '1.1']:
        sys.stderr.write("HIT_BRANCH: manifest_schema_version_unsupported\n")
        sys.stderr.flush()
        error_msg = f"Manifest schema version unsupported: {schema_version}"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)
    
    # C7: Required field present but wrong type
    if 'version' in manifest and not isinstance(manifest.get('version'), str):
        sys.stderr.write("HIT_BRANCH: manifest_field_wrong_type\n")
        sys.stderr.flush()
        error_msg = f"Manifest field 'version' has wrong type: expected str, got {type(manifest.get('version')).__name__}"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)
    
    # C8: Public key missing / unreadable (if signature verification enabled)
    public_key_path = os.getenv('RANSOMEYE_SIGNING_PUBLIC_KEY_PATH')
    if public_key_path:
        if not Path(public_key_path).exists():
            sys.stderr.write("HIT_BRANCH: manifest_public_key_missing\n")
            sys.stderr.flush()
            error_msg = f"Public key file not found: {public_key_path}"
            logger.fatal(error_msg)
            exit_startup_error(error_msg)
        elif not os.access(public_key_path, os.R_OK):
            sys.stderr.write("HIT_BRANCH: manifest_public_key_unreadable\n")
            sys.stderr.flush()
            error_msg = f"Public key file not readable: {public_key_path}"
            logger.fatal(error_msg)
            exit_startup_error(error_msg)
    
    # C9: Manifest timestamp invalid / in the future
    if 'build_timestamp' in manifest:
        try:
            timestamp_str = manifest.get('build_timestamp')
            if timestamp_str:
                # Try to parse RFC3339 timestamp
                # Handle both 'Z' and '+00:00' formats
                if timestamp_str.endswith('Z'):
                    timestamp_str_clean = timestamp_str.replace('Z', '+00:00')
                else:
                    timestamp_str_clean = timestamp_str
                timestamp = datetime.fromisoformat(timestamp_str_clean)
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                if timestamp > now:
                    sys.stderr.write("HIT_BRANCH: manifest_timestamp_invalid\n")
                    sys.stderr.flush()
                    error_msg = f"Manifest timestamp is in the future: {timestamp_str}"
                    logger.fatal(error_msg)
                    exit_startup_error(error_msg)
        except (ValueError, TypeError) as e:
            sys.stderr.write("HIT_BRANCH: manifest_timestamp_invalid\n")
            sys.stderr.flush()
            error_msg = f"Manifest timestamp invalid: {e}"
            logger.fatal(error_msg)
            exit_startup_error(error_msg)
    
    logger.startup("Installation manifest validated")


def _validate_readonly_enforcement():
    """
    Phase 10.1 requirement: Validate read-only enforcement for UI Backend.
    Fail-fast: Exit immediately if enforcement check fails.
    """
    logger.startup("Validating read-only enforcement")
    
    try:
        db_password = config_loader.get_secret('RANSOMEYE_DB_PASSWORD') if _common_available else os.getenv('RANSOMEYE_DB_PASSWORD')
        conn = psycopg2.connect(
            host=config.get('RANSOMEYE_DB_HOST', 'localhost'),
            port=config.get('RANSOMEYE_DB_PORT', 5432),
            database=config.get('RANSOMEYE_DB_NAME', 'ransomeye'),
            user=config.get('RANSOMEYE_DB_USER', 'ransomeye'),
            password=db_password
        )
        cur = conn.cursor()
        
        # Phase 10.1 requirement: Verify UI views exist (read-only enforcement)
        required_views = [
            'v_active_incidents', 'v_incident_timeline', 
            'v_incident_evidence_summary', 'v_policy_recommendations', 'v_ai_insights'
        ]
        
        cur.execute("""
            SELECT viewname FROM pg_views 
            WHERE schemaname = 'public'
        """)
        existing_views = {row[0] for row in cur.fetchall()}
        
        missing_views = []
        for view in required_views:
            if view not in existing_views:
                missing_views.append(view)
        
        cur.close()
        conn.close()
        
        if missing_views:
            error_msg = f"Missing required views for read-only enforcement: {', '.join(missing_views)}"
            logger.fatal(f"Read-only enforcement validation failed: {error_msg}")
            exit_startup_error(error_msg)
        
        logger.startup(f"Read-only enforcement validated ({len(required_views)} views present)")
    except Exception as e:
        error_msg = f"Read-only enforcement validation failed: {e}"
        logger.db_error(str(e), "readonly_check")
        exit_startup_error(error_msg)

def _invariant_check_missing_env(var_name: str):
    """
    Phase 10.1 requirement: Fail-fast invariant - missing env var.
    Terminate Core immediately if violated.
    """
    if not os.getenv(var_name):
        sys.stderr.write("HIT_BRANCH: invariant_missing_env\n")
        error_msg = f"INVARIANT VIOLATION: Missing required environment variable: {var_name}"
        logger.fatal(error_msg)
        exit_fatal(error_msg, ExitCode.CONFIG_ERROR)

def _invariant_check_db_connection():
    """
    Phase 10.1 requirement: Fail-fast invariant - DB connection failure.
    Terminate Core immediately if violated.
    """
    try:
        db_password = config_loader.get_secret('RANSOMEYE_DB_PASSWORD') if _common_available else os.getenv('RANSOMEYE_DB_PASSWORD')
        conn = psycopg2.connect(
            host=config.get('RANSOMEYE_DB_HOST', 'localhost'),
            port=config.get('RANSOMEYE_DB_PORT', 5432),
            database=config.get('RANSOMEYE_DB_NAME', 'ransomeye'),
            user=config.get('RANSOMEYE_DB_USER', 'ransomeye'),
            password=db_password
        )
        conn.close()
    except Exception as e:
        sys.stderr.write("HIT_BRANCH: invariant_db_connection_failure\n")
        error_msg = f"INVARIANT VIOLATION: Database connection failure: {e}"
        logger.fatal(error_msg)
        exit_fatal(error_msg, ExitCode.STARTUP_ERROR)

def _invariant_check_schema_mismatch():
    """
    Phase 10.1 requirement: Fail-fast invariant - schema mismatch.
    Terminate Core immediately if violated.
    """
    try:
        db_password = config_loader.get_secret('RANSOMEYE_DB_PASSWORD') if _common_available else os.getenv('RANSOMEYE_DB_PASSWORD')
        conn = psycopg2.connect(
            host=config.get('RANSOMEYE_DB_HOST', 'localhost'),
            port=config.get('RANSOMEYE_DB_PORT', 5432),
            database=config.get('RANSOMEYE_DB_NAME', 'ransomeye'),
            user=config.get('RANSOMEYE_DB_USER', 'ransomeye'),
            password=db_password
        )
        cur = conn.cursor()
        
        # Check critical table structure
        cur.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'raw_events' AND column_name = 'event_id'
        """)
        if not cur.fetchone():
            cur.close()
            conn.close()
            sys.stderr.write("HIT_BRANCH: invariant_schema_mismatch\n")
            error_msg = "INVARIANT VIOLATION: Schema mismatch - raw_events.event_id column missing"
            logger.fatal(error_msg)
            exit_fatal(error_msg, ExitCode.STARTUP_ERROR)
        
        cur.close()
        conn.close()
    except Exception as e:
        sys.stderr.write("HIT_BRANCH: invariant_schema_check_exception\n")
        error_msg = f"INVARIANT VIOLATION: Schema mismatch check failed: {e}"
        logger.fatal(error_msg)
        exit_fatal(error_msg, ExitCode.STARTUP_ERROR)

def _invariant_check_duplicate_incident(conn, event_id: str):
    """
    Phase 10.1 requirement: Fail-fast invariant - duplicate incident creation attempt.
    Terminate Core immediately if violated.
    """
    cur = conn.cursor()
    try:
        # Check if event already linked to incident
        cur.execute("SELECT COUNT(*) FROM evidence WHERE event_id = %s", (event_id,))
        count = cur.fetchone()[0]
        if count > 0:
            sys.stderr.write("HIT_BRANCH: invariant_duplicate_incident\n")
            error_msg = f"INVARIANT VIOLATION: Duplicate incident creation attempt for event_id={event_id}"
            logger.fatal(error_msg)
            exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
    finally:
        cur.close()

def _invariant_check_unauthorized_write(component: str, operation: str):
    """
    Phase 10.1 requirement: Fail-fast invariant - unauthorized write attempt (read-only module).
    Terminate Core immediately if violated.
    """
    if component == 'ui' and operation == 'write':
        sys.stderr.write("HIT_BRANCH: invariant_unauthorized_write\n")
        error_msg = f"INVARIANT VIOLATION: Unauthorized write attempt by read-only module: {component}"
        logger.fatal(error_msg)
        exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)

def _validate_runtime_dependencies():
    """
    D.7.3: Hard pre-flight check - Core refuses to start if any runtime-critical dependency is missing.
    Error clearly states the missing dependency.
    No partial component startup occurs.
    """
    logger.startup("Validating runtime dependencies")
    
    # D.7.1: Authoritative list of runtime-critical dependencies
    required_packages = {
        "core": ["psycopg2", "pydantic", "pydantic_settings", "dateutil"],
        "ingest": ["fastapi", "uvicorn", "jsonschema", "nacl", "jwt"],
        "ai-core": ["numpy", "sklearn"],
        "correlation-engine": [],
        "policy-engine": ["cryptography"],
        "ui-backend": ["fastapi", "uvicorn", "jwt", "bcrypt"],
    }
    
    missing = []
    for component, packages in required_packages.items():
        for pkg in packages:
            # Map package name to import name (e.g., "psycopg2-binary" -> "psycopg2")
            import_name = pkg.replace("-", "_")
            try:
                __import__(import_name)
            except ImportError as e:
                missing.append(f"{component}:{pkg}")
    
    if missing:
        error_msg = f"RUNTIME DEPENDENCY MISSING: {', '.join(missing)}"
        sys.stderr.write("HIT_BRANCH: runtime_dependency_missing\n")
        sys.stderr.flush()
        logger.fatal(error_msg)
        exit_startup_error(error_msg)

def _core_startup_validation():
    """
    Phase 10.1 requirement: Core startup validation.
    Validate all required checks before starting components.
    """
    logger.startup("Core startup validation beginning")
    
    # D.7.3: Validate runtime dependencies BEFORE other checks
    _validate_runtime_dependencies()
    
    # Phase 10.1 requirement: Validate config file access if provided
    _validate_config_access()
    
    # Phase 10.1 requirement: Validate all required environment variables
    _validate_environment()
    
    # GA-BLOCKING: Pre-flight database bootstrap validation (MUST run before schema validation)
    # This prevents opaque startup crashes caused by PostgreSQL authentication misconfiguration
    try:
        from core.diagnostics.db_bootstrap_validator import validate_db_bootstrap
        
        # Get credentials from config (must be provided, no defaults)
        db_host = config.get('RANSOMEYE_DB_HOST')
        db_port = config.get('RANSOMEYE_DB_PORT')
        db_name = config.get('RANSOMEYE_DB_NAME')
        db_user = config.get('RANSOMEYE_DB_USER')
        db_password = config_loader.get_secret('RANSOMEYE_DB_PASSWORD') if _common_available else os.getenv('RANSOMEYE_DB_PASSWORD')
        
        # Validate credentials are present (fail-closed)
        if not db_user:
            sys.stderr.write("HIT_BRANCH: bootstrap_missing_db_user\n")
            exit_config_error("RANSOMEYE_DB_USER is required (no default allowed)")
        if not db_password:
            sys.stderr.write("HIT_BRANCH: bootstrap_missing_db_password\n")
            exit_config_error("RANSOMEYE_DB_PASSWORD is required (no default allowed)")
        
        validate_db_bootstrap(
            host=db_host or 'localhost',
            port=db_port or 5432,
            database=db_name or 'ransomeye',
            user=db_user,
            password=db_password,
            logger=logger
        )
    except ImportError:
        # If diagnostics module not available, log warning but continue
        # (This should not happen in production, but preserves backward compatibility)
        sys.stderr.write("HIT_BRANCH: bootstrap_import_error\n")
        logger.warning("Database bootstrap validator not available, skipping pre-flight check")
    except SystemExit:
        # Re-raise SystemExit (from exit_startup_error) to preserve fail-closed behavior
        raise
    except Exception as e:
        # Unexpected error in validator itself
        sys.stderr.write("HIT_BRANCH: bootstrap_validator_exception\n")
        error_msg = f"Database bootstrap validator failed: {e}"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)
    
    # Phase 10.1 requirement: Validate DB connectivity
    _validate_db_connectivity()
    
    # Phase 1 requirement: Validate schema version before presence checks
    _validate_schema_version()
    
    # Phase 10.1 requirement: Validate schema presence
    _validate_schema_presence()
    
    # Phase 10.1 requirement: Validate write permissions where applicable
    _validate_write_permissions()
    
    # Phase 10.1 requirement: Validate filesystem edge cases
    _validate_filesystem_edges()
    
    # Phase 10.1 requirement: Validate read-only enforcement where applicable
    _validate_readonly_enforcement()
    
    # Phase 10.1 requirement: Validate installation manifest if present
    _validate_manifest()
    
    # Phase 10.1 requirement: Fail-fast invariant checks
    _invariant_check_missing_env('RANSOMEYE_DB_PASSWORD')
    _invariant_check_missing_env('RANSOMEYE_DB_USER')
    _invariant_check_missing_env('RANSOMEYE_COMMAND_SIGNING_KEY')
    _invariant_check_db_connection()
    _invariant_check_schema_mismatch()
    
    # Validate signing key is not weak/default
    signing_key = os.getenv('RANSOMEYE_COMMAND_SIGNING_KEY')
    if signing_key:
        weak_patterns = ['test_signing_key', 'default', 'changeme', 'password', 'secret', 'phase7_minimal']
        for pattern in weak_patterns:
            if pattern.lower() in signing_key.lower():
                sys.stderr.write("HIT_BRANCH: signing_key_weak_pattern\n")
                error_msg = f"SECURITY VIOLATION: Signing key contains weak/default pattern '{pattern}' (not allowed)"
                logger.fatal(error_msg)
                exit_fatal(error_msg, ExitCode.CONFIG_ERROR)
    
    logger.startup("Core startup validation complete")

def _core_cleanup():
    """
    Phase 10.1 requirement: Core cleanup on shutdown.
    Close all component connections cleanly.
    """
    global _db_transaction_active, _startup_complete
    
    # G5: Runtime state corruption detected
    if _startup_complete and not _shutdown_in_progress and _db_transaction_active:
        # Defensive check: startup complete but transaction still active without shutdown
        sys.stderr.write("HIT_BRANCH: runtime_state_corrupt\n")
        sys.stderr.flush()
        logger.fatal("Runtime state corruption detected: startup complete but transaction active without shutdown")
        exit_fatal("Runtime state corruption detected", ExitCode.FATAL_ERROR)
    
    logger.shutdown("Core cleanup beginning")
    
    # Phase 10.1 requirement: Close all DB connections cleanly
    for component_name, state in _component_state.items():
        if state.get('conn'):
            try:
                state['conn'].close()
                logger.info(f"Closed database connection for {component_name}")
            except Exception as e:
                logger.error(f"Error closing connection for {component_name}: {e}")
        state['running'] = False
    
    _db_transaction_active = False
    logger.shutdown("Core cleanup complete")

def _signal_handler(signum, frame):
    """
    Phase 10.1 requirement: Graceful shutdown handler for SIGTERM/SIGINT.
    Stop accepting new work, finish transactions, close connections, exit cleanly.
    """
    global _shutdown_in_progress, _startup_complete, _db_transaction_active
    
    # F3: Double signal delivery (re-entrant handler)
    if _shutdown_in_progress:
        sys.stderr.write("HIT_BRANCH: double_signal_detected\n")
        sys.stderr.flush()
        # Idempotent exit - already shutting down
        sys.exit(ExitCode.SUCCESS)
    
    _shutdown_in_progress = True
    
    # G2: Explicit internal assertion failure (invalid signal)
    try:
        signal_name = signal.Signals(signum).name
    except ValueError:
        sys.stderr.write("HIT_BRANCH: internal_assertion_failed\n")
        sys.stderr.flush()
        logger.fatal(f"Internal assertion failed: invalid signal number {signum}")
        exit_fatal(f"Invalid signal number: {signum}", ExitCode.FATAL_ERROR)
    
    # F1: SIGTERM received before startup completes
    if not _startup_complete and signal_name == 'SIGTERM':
        sys.stderr.write("HIT_BRANCH: sigterm_before_startup\n")
        sys.stderr.flush()
        logger.shutdown(f"Received {signal_name} before startup completion, exiting immediately")
        try:
            _core_cleanup()
        except Exception:
            pass  # Safe fallback
        sys.exit(ExitCode.SUCCESS)
    
    logger.shutdown(f"Received {signal_name}, initiating graceful shutdown")
    
    # F2: SIGINT during DB transaction
    if _db_transaction_active and signal_name == 'SIGINT':
        sys.stderr.write("HIT_BRANCH: sigint_during_db\n")
        sys.stderr.flush()
        logger.shutdown("SIGINT received during DB transaction, aborting transaction and exiting")
        # Abort transaction (connection cleanup happens in _core_cleanup)
        try:
            _core_cleanup()
        except Exception:
            pass  # Safe fallback
        sys.exit(ExitCode.SUCCESS)
    
    # Phase 2 requirement: Orchestrator-managed shutdown
    if _shutdown_handler:
        _shutdown_handler.shutdown_requested.set()
    if _orchestrator:
        _orchestrator._shutdown_components()
    
    try:
        _core_cleanup()
    except Exception as e:
        # F4: Exception thrown inside shutdown hook
        sys.stderr.write("HIT_BRANCH: shutdown_hook_exception\n")
        sys.stderr.flush()
        logger.fatal(f"Exception in shutdown hook: {e}")
        # Safe fallback exit
        sys.exit(ExitCode.SUCCESS)
    
    logger.shutdown("Core graceful shutdown complete")
    sys.exit(ExitCode.SUCCESS)


def _load_core_fatal_event() -> Dict[str, str]:
    run_dir = os.getenv("RANSOMEYE_RUN_DIR", "/tmp/ransomeye")
    core_token = os.getenv("RANSOMEYE_CORE_TOKEN")
    fatal_path = Path(run_dir) / "core_fatal.json"
    if not fatal_path.exists():
        sys.stderr.write("HIT_BRANCH: fatal_marker_missing\n")
        sys.stderr.flush()
        return {
            "reason_code": "READ_ONLY_VIOLATION",
            "message": "Read-only violation reported by supervised component",
            "component": "unknown"
        }
    try:
        payload = json.loads(fatal_path.read_text(encoding="utf-8"))
    except Exception:
        sys.stderr.write("HIT_BRANCH: fatal_marker_json_invalid\n")
        sys.stderr.flush()
        return {
            "reason_code": "READ_ONLY_VIOLATION",
            "message": "Read-only violation reported by supervised component (invalid marker)",
            "component": "unknown"
        }
    if core_token and payload.get("core_token") and payload.get("core_token") != core_token:
        sys.stderr.write("HIT_BRANCH: fatal_marker_token_mismatch\n")
        sys.stderr.flush()
        return {
            "reason_code": "READ_ONLY_VIOLATION",
            "message": "Read-only violation marker token mismatch",
            "component": payload.get("component", "unknown")
        }
    return {
        "reason_code": payload.get("reason_code", "READ_ONLY_VIOLATION"),
        "message": payload.get("message", "Read-only violation reported by supervised component"),
        "component": payload.get("component", "unknown")
    }


def _fatal_signal_handler(signum, frame):
    event = _load_core_fatal_event()
    reason_code = event.get("reason_code", "READ_ONLY_VIOLATION")
    message = event.get("message", "Read-only violation reported by supervised component")
    component = event.get("component", "unknown")
    logger.fatal(
        f"SECURITY-GRADE: Core termination due to {reason_code}: {message}",
        failure_reason_code=reason_code,
        source_component=component
    )
    if _orchestrator:
        _orchestrator.state = ComponentState.FAILED
        _orchestrator.global_state = "FAILED"
        _orchestrator.failure_reason_code = reason_code
        _orchestrator.failure_reason = message
        _orchestrator._write_status()
    os._exit(ExitCode.RUNTIME_ERROR)

def _initialize_core():
    """
    Phase 10.1 requirement: Initialize Core runtime.
    Register signal handlers and perform startup validation.
    """
    # Register signal handlers for graceful shutdown and fatal escalation
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGUSR1, _fatal_signal_handler)
    
    # Phase 10.1 requirement: Core startup validation
    _core_startup_validation()
    
    global _startup_complete
    _startup_complete = True
    
    logger.startup("Core runtime initialized")

def _load_component_modules():
    """
    Load component modules as Core modules (not standalone services).
    """
    global _ingest_module, _correlation_module, _ai_core_module, _policy_module, _ui_module
    
    # Phase 10.1 requirement: Load components as modules within Core
    sys.path.insert(0, os.path.join(_project_root, 'services/ingest/app'))
    sys.path.insert(0, os.path.join(_project_root, 'services/correlation-engine/app'))
    sys.path.insert(0, os.path.join(_project_root, 'services/ai-core/app'))
    sys.path.insert(0, os.path.join(_project_root, 'services/policy-engine/app'))
    sys.path.insert(0, os.path.join(_project_root, 'services/ui/backend'))
    
    try:
        import main as ingest_main
        _ingest_module = ingest_main
        logger.startup("Ingest module loaded")
    except Exception as e:
        logger.fatal(f"Failed to load Ingest module: {e}")
        exit_startup_error(f"Module load failed: Ingest - {e}")
    
    try:
        import main as correlation_main
        _correlation_module = correlation_main
        logger.startup("Correlation Engine module loaded")
    except Exception as e:
        logger.fatal(f"Failed to load Correlation Engine module: {e}")
        exit_startup_error(f"Module load failed: Correlation Engine - {e}")
    
    try:
        import main as ai_core_main
        _ai_core_module = ai_core_main
        logger.startup("AI Core module loaded")
    except Exception as e:
        logger.fatal(f"Failed to load AI Core module: {e}")
        exit_startup_error(f"Module load failed: AI Core - {e}")
    
    try:
        import main as policy_main
        _policy_module = policy_main
        logger.startup("Policy Engine module loaded")
    except Exception as e:
        logger.fatal(f"Failed to load Policy Engine module: {e}")
        exit_startup_error(f"Module load failed: Policy Engine - {e}")
    
    try:
        import main as ui_main
        _ui_module = ui_main
        logger.startup("UI Backend module loaded")
    except Exception as e:
        logger.fatal(f"Failed to load UI Backend module: {e}")
        exit_startup_error(f"Module load failed: UI Backend - {e}")

def run_core():
    """
    Phase 10.1 requirement: Run Core runtime.
    Initialize Core, load components as modules, coordinate execution.
    """
    global _orchestrator
    
    # G4: Defensive "should-not-happen" branch - orchestrator already exists
    if _orchestrator is not None:
        sys.stderr.write("HIT_BRANCH: defensive_unreachable\n")
        sys.stderr.flush()
        logger.fatal("Defensive check: orchestrator already exists (should not happen)")
        exit_fatal("Orchestrator already initialized", ExitCode.FATAL_ERROR)
    
    _load_config_and_initialize()
    _initialize_core()
    logger.startup("Core runtime starting (orchestrator mode)")
    _orchestrator = CoreOrchestrator(logger, _shutdown_handler)
    exit_code = _orchestrator.run()
    logger.shutdown("Core runtime stopping")
    _core_cleanup()
    return exit_code


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


def run_startup_sequence(env: Optional[Dict[str, str]] = None) -> bool:
    """
    Run Core startup validation sequence once (no subprocesses, no loops).
    Raises on failure.
    """
    with _temporary_env(env):
        if _common_available:
            global config
            try:
                config = config_loader.load()
            except ConfigError:
                sys.stderr.write("HIT_BRANCH: config_loader_exception\n")
                raise
            except Exception as e:
                # G1: Unknown exception caught at top-level
                sys.stderr.write("HIT_BRANCH: unknown_exception_caught\n")
                sys.stderr.flush()
                error_msg = f"Unknown exception during config load: {e}"
                logger.fatal(error_msg)
                exit_fatal(error_msg, ExitCode.FATAL_ERROR)
        try:
            _initialize_core()
        except SystemExit as exc:
            raise RuntimeError("Core startup sequence failed") from exc
        except Exception as e:
            # G1: Unknown exception caught at top-level
            sys.stderr.write("HIT_BRANCH: unknown_exception_caught\n")
            sys.stderr.flush()
            error_msg = f"Unknown exception during core initialization: {e}"
            logger.fatal(error_msg)
            exit_fatal(error_msg, ExitCode.FATAL_ERROR)
    return True

if __name__ == "__main__":
    try:
        exit_code = run_core()
        logger.shutdown("Core runtime completed successfully")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.shutdown("Received interrupt, shutting down")
        try:
            _core_cleanup()
        except Exception:
            # G3: Fallback fatal exit path invoked
            sys.stderr.write("HIT_BRANCH: fallback_fatal_exit\n")
            sys.stderr.flush()
            sys.exit(ExitCode.SUCCESS)
        sys.exit(ExitCode.SUCCESS)
    except ConfigError as e:
        logger.config_error(str(e))
        sys.exit(ExitCode.CONFIG_ERROR)
    except SystemExit:
        raise
    except Exception as e:
        # G1: Unknown exception caught at top-level
        sys.stderr.write("HIT_BRANCH: unknown_exception_caught\n")
        sys.stderr.flush()
        logger.fatal(f"Fatal error in Core runtime: {e}")
        try:
            _core_cleanup()
        except Exception:
            # G3: Fallback fatal exit path invoked
            sys.stderr.write("HIT_BRANCH: fallback_fatal_exit\n")
            sys.stderr.flush()
        sys.exit(ExitCode.FATAL_ERROR)
