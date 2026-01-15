#!/usr/bin/env python3
"""
RansomEye v1.0 Core Runtime
AUTHORITATIVE: Core runtime coordinator for all components
Phase 10.1 requirement: Harden startup and shutdown for Core components
"""

import os
import sys
import signal
import psycopg2
from typing import Dict, Any, Optional, List
from pathlib import Path
from enum import IntEnum

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(_current_file))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.config import ConfigLoader, ConfigError, validate_path, validate_port, check_disk_space
    from common.logging import setup_logging, StructuredLogger
    from common.shutdown import ShutdownHandler, ExitCode, exit_config_error, exit_startup_error, exit_fatal
    from core.orchestrator import CoreOrchestrator
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
    try:
        config = config_loader.load()
    except ConfigError as e:
        exit_config_error(str(e))
else:
    config = {}
    if not os.getenv('RANSOMEYE_DB_PASSWORD'):
        exit_config_error('RANSOMEYE_DB_PASSWORD required')

logger = setup_logging('core')
_shutdown_handler = ShutdownHandler('core', cleanup_func=lambda: _core_cleanup())
_orchestrator: Optional[CoreOrchestrator] = None

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
            missing.append(var)
    
    if missing:
        error_msg = f"Missing required environment variables: {', '.join(missing)}"
        logger.config_error(error_msg)
        exit_config_error(error_msg)
    
    # Validate secrets are not weak/default values
    try:
        from common.security.secrets import validate_secret_present, validate_signing_key
        
        # Validate DB password
        db_password = validate_secret_present('RANSOMEYE_DB_PASSWORD', min_length=8)
        
        # Validate DB user (minimum 3 chars, not weak)
        db_user = os.getenv('RANSOMEYE_DB_USER')
        if not db_user:
            exit_config_error("RANSOMEYE_DB_USER is required")
        if len(db_user) < 3:
            exit_config_error("RANSOMEYE_DB_USER is too short (minimum 3 characters)")
        weak_users = ['gagan', 'test', 'admin', 'root', 'default']
        if db_user.lower() in [u.lower() for u in weak_users]:
            exit_config_error(f"SECURITY VIOLATION: RANSOMEYE_DB_USER uses weak/default value '{db_user}' (not allowed)")
        
        # Validate signing key
        signing_key = validate_signing_key('RANSOMEYE_COMMAND_SIGNING_KEY', min_length=32, fail_on_default=True)
        
        logger.startup("Environment variables and secrets validated")
    except ImportError:
        # Fallback validation if common module not available
        db_password = os.getenv('RANSOMEYE_DB_PASSWORD')
        if not db_password:
            exit_config_error("RANSOMEYE_DB_PASSWORD is required")
        if len(db_password) < 8:
            exit_config_error("RANSOMEYE_DB_PASSWORD is too short (minimum 8 characters)")
        if db_password.lower() in ['gagan', 'password', 'test', 'changeme', 'default', 'secret']:
            exit_config_error(f"SECURITY VIOLATION: RANSOMEYE_DB_PASSWORD uses weak/default value (not allowed)")
        
        signing_key = os.getenv('RANSOMEYE_COMMAND_SIGNING_KEY')
        if not signing_key:
            exit_config_error("RANSOMEYE_COMMAND_SIGNING_KEY is required")
        if len(signing_key) < 32:
            exit_config_error("RANSOMEYE_COMMAND_SIGNING_KEY is too short (minimum 32 characters)")
        if 'test_signing_key' in signing_key.lower() or 'default' in signing_key.lower():
            exit_config_error("SECURITY VIOLATION: RANSOMEYE_COMMAND_SIGNING_KEY uses weak/default value (not allowed)")
        
        logger.startup("Environment variables validated (basic validation)")

def _validate_db_connectivity():
    """
    Phase 10.1 requirement: Validate DB connectivity.
    Fail-fast: Exit immediately if connection fails.
    """
    logger.startup("Validating database connectivity")
    
    try:
        conn = psycopg2.connect(
            host=config.get('RANSOMEYE_DB_HOST', 'localhost'),
            port=config.get('RANSOMEYE_DB_PORT', 5432),
            database=config.get('RANSOMEYE_DB_NAME', 'ransomeye'),
            user=config.get('RANSOMEYE_DB_USER', 'ransomeye'),
            password=config['RANSOMEYE_DB_PASSWORD']
        )
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        logger.startup("Database connectivity validated")
    except Exception as e:
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
        conn = psycopg2.connect(
            host=config.get('RANSOMEYE_DB_HOST', 'localhost'),
            port=config.get('RANSOMEYE_DB_PORT', 5432),
            database=config.get('RANSOMEYE_DB_NAME', 'ransomeye'),
            user=config.get('RANSOMEYE_DB_USER', 'ransomeye'),
            password=config['RANSOMEYE_DB_PASSWORD']
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
            error_msg = f"Missing required tables: {', '.join(missing_tables)}"
            logger.fatal(f"Schema validation failed: {error_msg}")
            exit_startup_error(error_msg)
        
        logger.startup(f"Database schema validated ({len(required_tables)} tables present)")
    except Exception as e:
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
        error_msg = f"Schema migrations directory not found: {migrations_path}"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)
    
    try:
        from common.db.migration_runner import get_latest_migration_version
    except Exception as e:
        error_msg = f"Migration runner not available for schema version check: {e}"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)
    
    expected_version = get_latest_migration_version(migrations_path)
    if not expected_version:
        error_msg = "No migrations found; schema version cannot be determined"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)
    
    try:
        conn = psycopg2.connect(
            host=config.get('RANSOMEYE_DB_HOST', 'localhost'),
            port=config.get('RANSOMEYE_DB_PORT', 5432),
            database=config.get('RANSOMEYE_DB_NAME', 'ransomeye'),
            user=config.get('RANSOMEYE_DB_USER', 'ransomeye'),
            password=config['RANSOMEYE_DB_PASSWORD']
        )
        cur = conn.cursor()
        cur.execute("SELECT to_regclass('public.schema_migrations')")
        if cur.fetchone()[0] is None:
            cur.close()
            conn.close()
            error_msg = "Schema migrations table missing; database not initialized"
            logger.fatal(error_msg)
            exit_startup_error(error_msg)
        
        cur.execute("SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1")
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            error_msg = "No schema migrations applied; database not initialized"
            logger.fatal(error_msg)
            exit_startup_error(error_msg)
        
        current_version = row[0]
        if current_version != expected_version:
            error_msg = (
                f"Schema version mismatch: expected {expected_version}, "
                f"found {current_version}"
            )
            logger.fatal(error_msg)
            exit_startup_error(error_msg)
        
        logger.startup(f"Schema version validated (version {current_version})")
    except Exception as e:
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
                error_msg = f"Cannot create policy directory {policy_dir}: {e}"
                logger.resource_error("policy_dir", error_msg)
                exit_startup_error(error_msg)
        
        if not os.access(policy_dir, os.W_OK):
            error_msg = f"Policy directory not writable: {policy_dir}"
            logger.resource_error("policy_dir", error_msg)
            exit_startup_error(error_msg)
        
        # Check log directory write permissions
        log_dir = Path(config.get('RANSOMEYE_LOG_DIR', '/var/log/ransomeye'))
        if not log_dir.exists():
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                error_msg = f"Cannot create log directory {log_dir}: {e}"
                logger.resource_error("log_dir", error_msg)
                exit_startup_error(error_msg)
        
        if not os.access(log_dir, os.W_OK):
            error_msg = f"Log directory not writable: {log_dir}"
            logger.resource_error("log_dir", error_msg)
            exit_startup_error(error_msg)
        
        logger.startup("Write permissions validated")
    except Exception as e:
        error_msg = f"Write permissions validation failed: {e}"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)

def _validate_readonly_enforcement():
    """
    Phase 10.1 requirement: Validate read-only enforcement for UI Backend.
    Fail-fast: Exit immediately if enforcement check fails.
    """
    logger.startup("Validating read-only enforcement")
    
    try:
        conn = psycopg2.connect(
            host=config.get('RANSOMEYE_DB_HOST', 'localhost'),
            port=config.get('RANSOMEYE_DB_PORT', 5432),
            database=config.get('RANSOMEYE_DB_NAME', 'ransomeye'),
            user=config.get('RANSOMEYE_DB_USER', 'ransomeye'),
            password=config['RANSOMEYE_DB_PASSWORD']
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
        error_msg = f"INVARIANT VIOLATION: Missing required environment variable: {var_name}"
        logger.fatal(error_msg)
        exit_fatal(error_msg, ExitCode.CONFIG_ERROR)

def _invariant_check_db_connection():
    """
    Phase 10.1 requirement: Fail-fast invariant - DB connection failure.
    Terminate Core immediately if violated.
    """
    try:
        conn = psycopg2.connect(
            host=config.get('RANSOMEYE_DB_HOST', 'localhost'),
            port=config.get('RANSOMEYE_DB_PORT', 5432),
            database=config.get('RANSOMEYE_DB_NAME', 'ransomeye'),
            user=config.get('RANSOMEYE_DB_USER', 'ransomeye'),
            password=config['RANSOMEYE_DB_PASSWORD']
        )
        conn.close()
    except Exception as e:
        error_msg = f"INVARIANT VIOLATION: Database connection failure: {e}"
        logger.fatal(error_msg)
        exit_fatal(error_msg, ExitCode.STARTUP_ERROR)

def _invariant_check_schema_mismatch():
    """
    Phase 10.1 requirement: Fail-fast invariant - schema mismatch.
    Terminate Core immediately if violated.
    """
    try:
        conn = psycopg2.connect(
            host=config.get('RANSOMEYE_DB_HOST', 'localhost'),
            port=config.get('RANSOMEYE_DB_PORT', 5432),
            database=config.get('RANSOMEYE_DB_NAME', 'ransomeye'),
            user=config.get('RANSOMEYE_DB_USER', 'ransomeye'),
            password=config['RANSOMEYE_DB_PASSWORD']
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
            error_msg = "INVARIANT VIOLATION: Schema mismatch - raw_events.event_id column missing"
            logger.fatal(error_msg)
            exit_fatal(error_msg, ExitCode.STARTUP_ERROR)
        
        cur.close()
        conn.close()
    except Exception as e:
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
        error_msg = f"INVARIANT VIOLATION: Unauthorized write attempt by read-only module: {component}"
        logger.fatal(error_msg)
        exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)

def _core_startup_validation():
    """
    Phase 10.1 requirement: Core startup validation.
    Validate all required checks before starting components.
    """
    logger.startup("Core startup validation beginning")
    
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
        db_password = config.get('RANSOMEYE_DB_PASSWORD')
        
        # Validate credentials are present (fail-closed)
        if not db_user:
            exit_config_error("RANSOMEYE_DB_USER is required (no default allowed)")
        if not db_password:
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
        logger.warning("Database bootstrap validator not available, skipping pre-flight check")
    except SystemExit:
        # Re-raise SystemExit (from exit_startup_error) to preserve fail-closed behavior
        raise
    except Exception as e:
        # Unexpected error in validator itself
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
    
    # Phase 10.1 requirement: Validate read-only enforcement where applicable
    _validate_readonly_enforcement()
    
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
                error_msg = f"SECURITY VIOLATION: Signing key contains weak/default pattern '{pattern}' (not allowed)"
                logger.fatal(error_msg)
                exit_fatal(error_msg, ExitCode.CONFIG_ERROR)
    
    logger.startup("Core startup validation complete")

def _core_cleanup():
    """
    Phase 10.1 requirement: Core cleanup on shutdown.
    Close all component connections cleanly.
    """
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
    
    logger.shutdown("Core cleanup complete")

def _signal_handler(signum, frame):
    """
    Phase 10.1 requirement: Graceful shutdown handler for SIGTERM/SIGINT.
    Stop accepting new work, finish transactions, close connections, exit cleanly.
    """
    signal_name = signal.Signals(signum).name
    logger.shutdown(f"Received {signal_name}, initiating graceful shutdown")
    
    # Phase 2 requirement: Orchestrator-managed shutdown
    if _shutdown_handler:
        _shutdown_handler.shutdown_requested.set()
    if _orchestrator:
        _orchestrator._shutdown_components()
    _core_cleanup()
    logger.shutdown("Core graceful shutdown complete")
    sys.exit(ExitCode.SUCCESS)

def _initialize_core():
    """
    Phase 10.1 requirement: Initialize Core runtime.
    Register signal handlers and perform startup validation.
    """
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
    
    # Phase 10.1 requirement: Core startup validation
    _core_startup_validation()
    
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
    _initialize_core()
    logger.startup("Core runtime starting (orchestrator mode)")
    _orchestrator = CoreOrchestrator(logger, _shutdown_handler)
    exit_code = _orchestrator.run()
    logger.shutdown("Core runtime stopping")
    _core_cleanup()
    return exit_code

if __name__ == "__main__":
    try:
        exit_code = run_core()
        logger.shutdown("Core runtime completed successfully")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.shutdown("Received interrupt, shutting down")
        _core_cleanup()
        sys.exit(ExitCode.SUCCESS)
    except ConfigError as e:
        logger.config_error(str(e))
        sys.exit(ExitCode.CONFIG_ERROR)
    except Exception as e:
        logger.fatal(f"Fatal error in Core runtime: {e}")
        _core_cleanup()
        sys.exit(ExitCode.FATAL_ERROR)
