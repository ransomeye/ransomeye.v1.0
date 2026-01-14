#!/usr/bin/env python3
"""
RansomEye v1.0 Policy Engine - Database Module
AUTHORITATIVE: Database operations for read-only policy engine
Python 3.10+ only - aligns with Phase 7 requirements
"""

import os
import sys
import psycopg2
from typing import List, Dict, Any
from datetime import datetime
import json

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.db.safety import (create_readonly_connection, IsolationLevel, 
                                   execute_read_operation, validate_connection_health)
    from common.logging import setup_logging
    _common_db_safety_available = True
    _logger = setup_logging('policy-engine-db')
except ImportError:
    _common_db_safety_available = False
    _logger = None
    def create_readonly_connection(*args, **kwargs): raise RuntimeError("Database safety utilities not available")
    def execute_read_operation(*args, **kwargs): raise RuntimeError("Database safety utilities not available")
    def validate_connection_health(*args, **kwargs): return True
    class IsolationLevel: READ_COMMITTED = 2


def get_db_connection():
    """
    Get read-only PostgreSQL database connection.
    Read-only enforcement: Policy Engine must never write to DB.
    Abort Core if any write is attempted.
    Connection safety: Validate health before returning.
    
    GA-BLOCKING FIX: Removed fallback psycopg2.connect() path.
    Fail-fast if common/db/safety.py utilities are not available.
    """
    if not _common_db_safety_available:
        error_msg = "CRITICAL: Database safety utilities (common/db/safety.py) are not available. Core must terminate."
        if _logger:
            _logger.fatal(error_msg)
        else:
            print(f"FATAL: {error_msg}", file=sys.stderr)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.STARTUP_ERROR)
    
    # v1.0 GA: Use gagan/gagan (Phase A.2 reverted)
    db_user = os.getenv("RANSOMEYE_DB_USER", "gagan")
    
    conn = create_readonly_connection(
        host=os.getenv("RANSOMEYE_DB_HOST", "localhost"),
        port=int(os.getenv("RANSOMEYE_DB_PORT", "5432")),
        database=os.getenv("RANSOMEYE_DB_NAME", "ransomeye"),
        user=db_user,  # v1.0 GA: gagan
        password=os.getenv("RANSOMEYE_DB_PASSWORD", ""),
        isolation_level=IsolationLevel.READ_COMMITTED,
        logger=_logger
    )
    return conn


def get_unresolved_incidents(conn) -> List[Dict[str, Any]]:
    """
    Get unresolved incidents for policy evaluation.
    Read-only operation: Enforced at connection level.
    Connection safety: Validated before operation.
    Policy Engine must never write to DB.
    """
    def _do_read():
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT 
                    incident_id,
                    machine_id,
                    current_stage,
                    first_observed_at,
                    last_observed_at,
                    total_evidence_count,
                    confidence_score
                FROM incidents
                WHERE resolved = FALSE
                ORDER BY first_observed_at ASC
            """)
            
            columns = [desc[0] for desc in cur.description]
            incidents = []
            for row in cur.fetchall():
                incident = dict(zip(columns, row))
                for key in ['first_observed_at', 'last_observed_at']:
                    if isinstance(incident[key], datetime):
                        incident[key] = incident[key].isoformat()
                incidents.append(incident)
            
            return incidents
        finally:
            cur.close()
    
    # GA-BLOCKING FIX: Removed fallback read operation path.
    # Fail-fast if common/db/safety.py utilities are not available.
    if not _common_db_safety_available:
        error_msg = "CRITICAL: Database safety utilities (common/db/safety.py) are not available. Core must terminate."
        if _logger:
            _logger.fatal(error_msg)
        else:
            print(f"FATAL: {error_msg}", file=sys.stderr)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.STARTUP_ERROR)
    
    return execute_read_operation(conn, "get_unresolved_incidents", _do_read, _logger, enforce_readonly=True)


def check_incident_evaluated(incident_id: str) -> bool:
    """
    Check if incident has already been evaluated by policy engine.
    Contract compliance: Idempotency check (restarting engine does NOT duplicate policy decisions)
    Deterministic: Simple existence check, no time-window logic
    
    Note: For Phase 7 minimal, we check if a policy decision file exists for this incident.
    Since we cannot modify schema, we use file-based storage for policy decisions.
    
    Args:
        incident_id: Incident ID to check
        
    Returns:
        True if incident has already been evaluated, False otherwise
    """
    # Phase 7 minimal: Check if policy decision exists in file storage
    # For Phase 7 minimal, we use file-based storage (not in database)
    # This is acceptable for Phase 7 minimal since policy decisions are metadata
    policy_dir = os.getenv("RANSOMEYE_POLICY_DIR", "/tmp/ransomeye/policy")
    policy_file = os.path.join(policy_dir, f"policy_decision_{incident_id}.json")
    return os.path.exists(policy_file)
