#!/usr/bin/env python3
"""
RansomEye v1.0 Correlation Engine - Database Module
AUTHORITATIVE: Database operations for deterministic correlation engine
Python 3.10+ only - aligns with Phase 5 requirements
"""

import os
import sys
import psycopg2
from typing import Optional, List, Dict, Any
from datetime import datetime

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.db.safety import (create_write_connection, IsolationLevel, 
                                   execute_write_operation, begin_transaction, 
                                   commit_transaction, rollback_transaction,
                                   validate_connection_health)
    from common.logging import setup_logging
    _common_db_safety_available = True
    _logger = setup_logging('correlation-engine-db')
except ImportError:
    _common_db_safety_available = False
    _logger = None
    def create_write_connection(*args, **kwargs): raise RuntimeError("Database safety utilities not available")
    def execute_write_operation(*args, **kwargs): raise RuntimeError("Database safety utilities not available")
    def begin_transaction(*args, **kwargs): pass
    def commit_transaction(*args, **kwargs): pass
    def rollback_transaction(*args, **kwargs): pass
    def validate_connection_health(*args, **kwargs): return True
    class IsolationLevel: READ_COMMITTED = 2


def get_db_connection():
    """
    Get PostgreSQL database connection with explicit isolation level.
    Transaction discipline: Explicit isolation level (READ_COMMITTED).
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
    
    conn = create_write_connection(
        host=os.getenv("RANSOMEYE_DB_HOST", "localhost"),
        port=int(os.getenv("RANSOMEYE_DB_PORT", "5432")),
        database=os.getenv("RANSOMEYE_DB_NAME", "ransomeye"),
        user=db_user,  # v1.0 GA: gagan
        password=os.getenv("RANSOMEYE_DB_PASSWORD", ""),
        isolation_level=IsolationLevel.READ_COMMITTED,
        logger=_logger
    )
    return conn


def get_unprocessed_events(conn) -> List[Dict[str, Any]]:
    """
    Get events from raw_events that have not been processed by correlation engine.
    Contract compliance: Read from raw_events table (Phase 4 schema)
    Deterministic: No time-window logic, reads all unprocessed events
    Phase 5 requirement: Idempotency - events already linked to evidence are skipped
    """
    cur = conn.cursor()
    try:
        # Contract compliance: Read from raw_events table
        # Deterministic: Read events that are VALID and not yet linked to evidence
        # Phase 5 requirement: Use only persisted facts (from raw_events)
        # Phase 5 requirement: Idempotency - skip events already processed (in evidence table)
        cur.execute("""
            SELECT 
                event_id,
                machine_id,
                component,
                component_instance_id,
                observed_at,
                ingested_at,
                sequence,
                payload,
                hostname,
                boot_id,
                agent_version,
                hash_sha256,
                prev_hash_sha256,
                validation_status
            FROM raw_events
            WHERE validation_status = 'VALID'
            AND event_id NOT IN (
                SELECT DISTINCT event_id 
                FROM evidence 
                WHERE event_id IS NOT NULL
            )
            ORDER BY ingested_at ASC
        """)
        
        columns = [desc[0] for desc in cur.description]
        events = []
        for row in cur.fetchall():
            event = dict(zip(columns, row))
            # Convert datetime objects to ISO format strings for JSON serialization
            for key in ['observed_at', 'ingested_at']:
                if isinstance(event[key], datetime):
                    event[key] = event[key].isoformat()
            events.append(event)
        
        return events
    finally:
        cur.close()


def create_incident(conn, incident_id: str, machine_id: str, event: Dict[str, Any], 
                   stage: str, confidence_score: float, event_id: str):
    """
    Create incident with initial stage and evidence link.
    Contract compliance: Write to incidents, incident_stages, evidence tables (Phase 2 schema)
    Deterministic: Single transaction, atomic writes
    Transaction discipline: Explicit begin, commit on success, rollback on failure.
    Deadlock/integrity violation detection: Log and terminate (no retries).
    Connection safety: Validate health before operation.
    """
    def _do_create_incident():
        """Inner function for write operation."""
        cur = conn.cursor()
        try:
            # Fail-fast invariant: duplicate incident creation attempt
            # Check if event already linked to incident before creating
            cur.execute("SELECT COUNT(*) FROM evidence WHERE event_id = %s", (event_id,))
            count = cur.fetchone()[0]
            if count > 0:
                # No recovery, no retry - terminate immediately
                cur.close()
                error_msg = f"INVARIANT VIOLATION: Duplicate incident creation attempt for event_id={event_id}"
                if _logger:
                    _logger.fatal(error_msg)
                from common.shutdown import ExitCode, exit_fatal
                exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
            
            # Contract compliance: Extract observed_at from event (first_observed_at)
            observed_at = event['observed_at']
            if isinstance(observed_at, str):
                from dateutil import parser
                observed_at = parser.isoparse(observed_at)
            
            # Contract compliance: Insert into incidents table
            cur.execute("""
                INSERT INTO incidents (
                    incident_id, machine_id, current_stage, first_observed_at, last_observed_at,
                    stage_changed_at, total_evidence_count, confidence_score
                )
                VALUES (%s, %s, %s, %s, %s, NOW(), 1, %s)
            """, (incident_id, machine_id, stage, observed_at, observed_at, confidence_score))
            
            # Contract compliance: Insert initial stage into incident_stages table
            cur.execute("""
                INSERT INTO incident_stages (
                    incident_id, from_stage, to_stage, transitioned_at,
                    evidence_count_at_transition, confidence_score_at_transition
                )
                VALUES (%s, NULL, %s, NOW(), 1, %s)
            """, (incident_id, stage, confidence_score))
            
            # Contract compliance: Link triggering event in evidence table
            cur.execute("""
                INSERT INTO evidence (
                    incident_id, event_id, evidence_type, confidence_level, confidence_score,
                    observed_at
                )
                VALUES (%s, %s, 'CORRELATION_PATTERN', 'LOW', %s, %s)
            """, (incident_id, event_id, confidence_score, observed_at))
            
            return True
        finally:
            cur.close()
    
    # Use common database safety utilities for explicit transaction management
    # GA-BLOCKING FIX: Removed fallback transaction management path.
    # Fail-fast if common/db/safety.py utilities are not available.
    if not _common_db_safety_available:
        error_msg = "CRITICAL: Database safety utilities (common/db/safety.py) are not available. Core must terminate."
        if _logger:
            _logger.fatal(error_msg)
        else:
            print(f"FATAL: {error_msg}", file=sys.stderr)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.STARTUP_ERROR)
    
    return execute_write_operation(conn, "create_incident", _do_create_incident, _logger)


def check_event_processed(conn, event_id: str) -> bool:
    """
    Check if event has already been processed (linked to evidence).
    Contract compliance: Idempotency check (restarting engine does NOT duplicate incidents)
    Deterministic: Simple existence check, no time-window logic
    """
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT 1 FROM evidence WHERE event_id = %s
        """, (event_id,))
        return cur.fetchone() is not None
    finally:
        cur.close()


def find_existing_incident(conn, machine_id: str, dedup_key: Optional[str], event_time: datetime) -> Optional[str]:
    """
    GA-BLOCKING: Find existing incident for deduplication.
    
    Looks for unresolved incidents for the same machine_id within deduplication time window.
    
    Args:
        conn: Database connection
        machine_id: Machine identifier
        dedup_key: Deduplication key (machine_id:process_id or machine_id)
        event_time: Event observed_at timestamp
        
    Returns:
        Incident ID if found, None otherwise
    """
    cur = conn.cursor()
    try:
        # GA-BLOCKING: Find unresolved incidents for same machine within time window
        time_window_start = event_time - timedelta(seconds=3600)  # 1 hour window
        time_window_end = event_time + timedelta(seconds=3600)
        
        cur.execute("""
            SELECT incident_id, first_observed_at
            FROM incidents
            WHERE machine_id = %s
            AND resolved = FALSE
            AND first_observed_at >= %s
            AND first_observed_at <= %s
            ORDER BY first_observed_at ASC
            LIMIT 1
        """, (machine_id, time_window_start, time_window_end))
        
        result = cur.fetchone()
        if result:
            return result[0]
        return None
    finally:
        cur.close()


def add_evidence_to_incident(conn, incident_id: str, event: Dict[str, Any], 
                            event_id: str, evidence_type: str, confidence_score: float):
    """
    GA-BLOCKING: Add evidence to existing incident and update confidence.
    
    Args:
        conn: Database connection
        incident_id: Incident identifier
        event: Event dictionary
        event_id: Event identifier
        evidence_type: Type of evidence
        confidence_score: Confidence contribution from this evidence
    """
    def _do_add_evidence():
        """Inner function for write operation."""
        cur = conn.cursor()
        try:
            # Check if event already linked to this incident
            cur.execute("""
                SELECT 1 FROM evidence WHERE incident_id = %s AND event_id = %s
            """, (incident_id, event_id))
            if cur.fetchone():
                return False  # Already linked
            
            # Extract observed_at
            observed_at = event['observed_at']
            if isinstance(observed_at, str):
                from dateutil import parser
                observed_at = parser.isoparse(observed_at)
            
            # Get current incident state
            cur.execute("""
                SELECT current_stage, confidence_score, total_evidence_count, last_observed_at
                FROM incidents WHERE incident_id = %s
            """, (incident_id,))
            result = cur.fetchone()
            if not result:
                return False
            
            current_stage, current_confidence, evidence_count, last_observed = result
            
            # GA-BLOCKING: Accumulate confidence
            from state_machine import accumulate_confidence, determine_stage, should_transition_stage
            new_confidence = accumulate_confidence(float(current_confidence), confidence_score)
            new_stage = determine_stage(new_confidence)
            
            # Update last_observed_at if event is newer
            if isinstance(last_observed, datetime):
                if observed_at > last_observed:
                    last_observed = observed_at
                else:
                    last_observed = last_observed
            else:
                last_observed = observed_at
            
            # Determine confidence level
            if confidence_score >= 50.0:
                confidence_level = 'HIGH'
            elif confidence_score >= 25.0:
                confidence_level = 'MEDIUM'
            else:
                confidence_level = 'LOW'
            
            # Add evidence
            cur.execute("""
                INSERT INTO evidence (
                    incident_id, event_id, evidence_type, confidence_level, confidence_score,
                    observed_at
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (incident_id, event_id, evidence_type, confidence_level, confidence_score, observed_at))
            
            # Update incident
            stage_changed = False
            if should_transition_stage(current_stage, new_stage):
                # GA-BLOCKING: State transition
                cur.execute("""
                    INSERT INTO incident_stages (
                        incident_id, from_stage, to_stage, transitioned_at,
                        evidence_count_at_transition, confidence_score_at_transition
                    )
                    VALUES (%s, %s, %s, NOW(), %s, %s)
                """, (incident_id, current_stage, new_stage, evidence_count + 1, new_confidence))
                stage_changed = True
            
            # Update incident record
            cur.execute("""
                UPDATE incidents
                SET current_stage = %s,
                    confidence_score = %s,
                    total_evidence_count = %s,
                    last_observed_at = %s,
                    stage_changed_at = CASE WHEN %s THEN NOW() ELSE stage_changed_at END
                WHERE incident_id = %s
            """, (new_stage, new_confidence, evidence_count + 1, last_observed, stage_changed, incident_id))
            
            return True
        finally:
            cur.close()
    
    return execute_write_operation(conn, "add_evidence_to_incident", _do_add_evidence, _logger)


def apply_contradiction_to_incident(conn, incident_id: str):
    """
    GA-BLOCKING: Apply contradiction decay to incident confidence.
    
    Args:
        conn: Database connection
        incident_id: Incident identifier
    """
    def _do_apply_contradiction():
        """Inner function for write operation."""
        cur = conn.cursor()
        try:
            # Get current confidence
            cur.execute("""
                SELECT confidence_score, current_stage
                FROM incidents WHERE incident_id = %s
            """, (incident_id,))
            result = cur.fetchone()
            if not result:
                return False
            
            current_confidence, current_stage = result
            
            # GA-BLOCKING: Apply contradiction decay
            from state_machine import apply_contradiction_decay, determine_stage
            decayed_confidence = apply_contradiction_decay(float(current_confidence))
            new_stage = determine_stage(decayed_confidence)
            
            # GA-BLOCKING: State does not escalate on contradiction (only decay)
            # If new_stage would be lower, keep current stage (no backward transition)
            if new_stage != current_stage:
                # Only update if stage would remain same or if confidence decayed enough
                # But we don't allow backward transitions, so keep current stage
                new_stage = current_stage
            
            # Update incident confidence (but not stage)
            cur.execute("""
                UPDATE incidents
                SET confidence_score = %s
                WHERE incident_id = %s
            """, (decayed_confidence, incident_id))
            
            return True
        finally:
            cur.close()
    
    return execute_write_operation(conn, "apply_contradiction_to_incident", _do_apply_contradiction, _logger)
