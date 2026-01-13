#!/usr/bin/env python3
"""
RansomEye v1.0 Threat Response Engine - Post-Incident Attestation
AUTHORITATIVE: Mandatory attestation after destructive actions (NO ASSUMPTIONS)
Python 3.10+ only
"""

import os
import sys
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    from common.db.safety import create_write_connection, IsolationLevel
    _common_available = True
    _logger = setup_logging('tre-attestation')
except ImportError:
    _common_available = False
    _logger = None

# Audit ledger integration
try:
    _audit_ledger_path = os.path.join(_project_root, 'audit-ledger')
    if os.path.exists(_audit_ledger_path) and _audit_ledger_path not in sys.path:
        sys.path.insert(0, _audit_ledger_path)
    from api import AuditLedger
    _audit_ledger_available = True
except ImportError:
    _audit_ledger_available = False
    AuditLedger = None


class AttestationError(Exception):
    """Exception raised when attestation fails."""
    pass


class PostIncidentAttestation:
    """
    Mandatory attestation after destructive actions.
    
    CRITICAL: Attestation required from Security Analyst (executor) and Approver (HAF authority).
    Stored immutably. Linked to incident_id.
    UI must block incident closure until attestation complete.
    """
    
    def __init__(
        self,
        db_conn_params: Dict[str, Any],
        ledger: Optional[AuditLedger] = None
    ):
        """
        Initialize post-incident attestation.
        
        Args:
            db_conn_params: Database connection parameters
            ledger: Optional audit ledger instance
        """
        self.db_conn_params = db_conn_params
        self.ledger = ledger
    
    def create_attestation(
        self,
        incident_id: str,
        action_id: str,
        executor_user_id: str,
        executor_role: str,
        approver_user_id: Optional[str] = None,
        approver_role: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create attestation record for destructive action.
        
        Args:
            incident_id: Incident identifier
            action_id: Action identifier
            executor_user_id: Executor user identifier (Security Analyst)
            executor_role: Executor role
            approver_user_id: Optional approver user identifier (HAF authority)
            approver_role: Optional approver role
        
        Returns:
            Attestation record dictionary
        """
        attestation_id = str(uuid.uuid4())
        
        conn = create_write_connection(**self.db_conn_params, isolation_level=IsolationLevel.READ_COMMITTED, logger=_logger)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO incident_attestations (
                        attestation_id, incident_id, action_id,
                        executor_user_id, executor_role,
                        approver_user_id, approver_role,
                        attestation_status, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'PENDING', %s)
                """, (
                    attestation_id, incident_id, action_id,
                    executor_user_id, executor_role,
                    approver_user_id, approver_role,
                    datetime.now(timezone.utc)
                ))
                conn.commit()
            
            return {
                'attestation_id': attestation_id,
                'incident_id': incident_id,
                'action_id': action_id,
                'executor_user_id': executor_user_id,
                'executor_role': executor_role,
                'approver_user_id': approver_user_id,
                'approver_role': approver_role,
                'status': 'PENDING',
                'created_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
        finally:
            conn.close()
    
    def submit_executor_attestation(
        self,
        attestation_id: str,
        executor_user_id: str,
        attestation_text: str
    ) -> Dict[str, Any]:
        """
        Submit executor attestation.
        
        Args:
            attestation_id: Attestation identifier
            executor_user_id: Executor user identifier
            attestation_text: Attestation text
        
        Returns:
            Updated attestation record
        """
        conn = create_write_connection(**self.db_conn_params, isolation_level=IsolationLevel.READ_COMMITTED, logger=_logger)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE incident_attestations
                    SET executor_attestation = %s,
                        executor_attested_at = %s
                    WHERE attestation_id = %s
                    AND executor_user_id = %s
                """, (attestation_text, datetime.now(timezone.utc), attestation_id, executor_user_id))
                conn.commit()
            
            # Check if both attestations complete
            cur.execute("""
                SELECT executor_attestation, approver_attestation
                FROM incident_attestations
                WHERE attestation_id = %s
            """, (attestation_id,))
            row = cur.fetchone()
            
            if row and row[0] and row[1]:
                # Both attestations complete
                cur.execute("""
                    UPDATE incident_attestations
                    SET attestation_status = 'COMPLETE'
                    WHERE attestation_id = %s
                """, (attestation_id,))
                conn.commit()
                
                # Emit audit event
                if self.ledger:
                    cur.execute("""
                        SELECT incident_id FROM incident_attestations
                        WHERE attestation_id = %s
                    """, (attestation_id,))
                    incident_row = cur.fetchone()
                    incident_id = incident_row[0] if incident_row else None
                    
                    self.ledger.append(
                        component='threat-response-engine',
                        component_instance_id=os.getenv('HOSTNAME', 'tre'),
                        action_type='post_incident_attested',
                        subject={'type': 'incident', 'id': incident_id or 'none'},
                        actor={'type': 'user', 'identifier': executor_user_id},
                        payload={
                            'attestation_id': attestation_id,
                            'incident_id': incident_id,
                            'status': 'COMPLETE'
                        }
                    )
            
            return {
                'attestation_id': attestation_id,
                'status': 'COMPLETE' if (row and row[0] and row[1]) else 'PENDING'
            }
        finally:
            conn.close()
    
    def submit_approver_attestation(
        self,
        attestation_id: str,
        approver_user_id: str,
        attestation_text: str
    ) -> Dict[str, Any]:
        """
        Submit approver attestation.
        
        Args:
            attestation_id: Attestation identifier
            approver_user_id: Approver user identifier
            attestation_text: Attestation text
        
        Returns:
            Updated attestation record
        """
        conn = create_write_connection(**self.db_conn_params, isolation_level=IsolationLevel.READ_COMMITTED, logger=_logger)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE incident_attestations
                    SET approver_attestation = %s,
                        approver_attested_at = %s
                    WHERE attestation_id = %s
                    AND approver_user_id = %s
                """, (attestation_text, datetime.now(timezone.utc), attestation_id, approver_user_id))
                conn.commit()
            
            # Check if both attestations complete
            cur.execute("""
                SELECT executor_attestation, approver_attestation
                FROM incident_attestations
                WHERE attestation_id = %s
            """, (attestation_id,))
            row = cur.fetchone()
            
            if row and row[0] and row[1]:
                # Both attestations complete
                cur.execute("""
                    UPDATE incident_attestations
                    SET attestation_status = 'COMPLETE'
                    WHERE attestation_id = %s
                """, (attestation_id,))
                conn.commit()
            
            return {
                'attestation_id': attestation_id,
                'status': 'COMPLETE' if (row and row[0] and row[1]) else 'PENDING'
            }
        finally:
            conn.close()
    
    def check_attestation_complete(
        self,
        incident_id: str
    ) -> bool:
        """
        Check if all attestations are complete for incident.
        
        Args:
            incident_id: Incident identifier
        
        Returns:
            True if all attestations complete
        """
        conn = create_write_connection(**self.db_conn_params, isolation_level=IsolationLevel.READ_COMMITTED, logger=_logger)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM incident_attestations
                    WHERE incident_id = %s
                    AND attestation_status != 'COMPLETE'
                """, (incident_id,))
                incomplete_count = cur.fetchone()[0]
                
                return incomplete_count == 0
        finally:
            conn.close()
