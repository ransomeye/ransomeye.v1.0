#!/usr/bin/env python3
"""
RansomEye v1.0 Threat Response Engine - Incident Freeze & Reopen
AUTHORITATIVE: Incident freeze and reopen workflow (NO ASSUMPTIONS)
Python 3.10+ only
"""

import os
import sys
import uuid
from typing import Dict, Any, Optional
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
    _logger = setup_logging('tre-incident-freeze')
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


class IncidentFreezeError(Exception):
    """Exception raised when incident freeze/reopen fails."""
    pass


class IncidentFreeze:
    """
    Incident freeze and reopen workflow.
    
    CRITICAL: After CLOSED or RESOLVED_WITH_ACTIONS, system blocks all new actions.
    Only rollback allowed. Requires SUPER_ADMIN to reopen.
    """
    
    def __init__(
        self,
        db_conn_params: Dict[str, Any],
        ledger: Optional[AuditLedger] = None
    ):
        """
        Initialize incident freeze.
        
        Args:
            db_conn_params: Database connection parameters
            ledger: Optional audit ledger instance
        """
        self.db_conn_params = db_conn_params
        self.ledger = ledger
    
    def check_incident_frozen(
        self,
        incident_id: str
    ) -> bool:
        """
        Check if incident is frozen.
        
        Args:
            incident_id: Incident identifier
        
        Returns:
            True if incident is frozen
        
        Raises:
            IncidentFreezeError: If incident not found
        """
        conn = create_write_connection(**self.db_conn_params, isolation_level=IsolationLevel.READ_COMMITTED, logger=_logger)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT status FROM incidents
                    WHERE incident_id = %s
                """, (incident_id,))
                row = cur.fetchone()
                
                if not row:
                    raise IncidentFreezeError(f"Incident not found: {incident_id}")
                
                status = row[0]
                
                # Frozen states: CLOSED, RESOLVED_WITH_ACTIONS
                return status in ('CLOSED', 'RESOLVED_WITH_ACTIONS')
        finally:
            conn.close()
    
    def reopen_incident(
        self,
        incident_id: str,
        user_id: str,
        user_role: str,
        justification: str
    ) -> Dict[str, Any]:
        """
        Reopen frozen incident.
        
        Args:
            incident_id: Incident identifier
            user_id: User identifier (must be SUPER_ADMIN)
            user_role: User role (must be SUPER_ADMIN)
            justification: Justification for reopen
        
        Returns:
            Reopen result dictionary
        
        Raises:
            IncidentFreezeError: If reopen fails
        """
        # SUPER_ADMIN only
        if user_role != 'SUPER_ADMIN':
            raise IncidentFreezeError("Incident reopen requires SUPER_ADMIN role")
        
        # Justification required
        if not justification or len(justification.strip()) < 10:
            raise IncidentFreezeError("Reopen requires justification (minimum 10 characters)")
        
        conn = create_write_connection(**self.db_conn_params, isolation_level=IsolationLevel.READ_COMMITTED, logger=_logger)
        try:
            with conn.cursor() as cur:
                # Check current status
                cur.execute("""
                    SELECT status FROM incidents
                    WHERE incident_id = %s
                """, (incident_id,))
                row = cur.fetchone()
                
                if not row:
                    raise IncidentFreezeError(f"Incident not found: {incident_id}")
                
                current_status = row[0]
                
                # Only CLOSED or RESOLVED_WITH_ACTIONS can be reopened
                if current_status not in ('CLOSED', 'RESOLVED_WITH_ACTIONS'):
                    raise IncidentFreezeError(
                        f"Incident {incident_id} is not frozen (status: {current_status})"
                    )
                
                # Update status to IN_PROGRESS
                cur.execute("""
                    UPDATE incidents
                    SET status = 'IN_PROGRESS',
                        reopened_at = %s,
                        reopened_by = %s,
                        reopen_justification = %s
                    WHERE incident_id = %s
                """, (datetime.now(timezone.utc), user_id, justification, incident_id))
                conn.commit()
            
            # Emit audit ledger event
            if self.ledger:
                self.ledger.append(
                    component='threat-response-engine',
                    component_instance_id=os.getenv('HOSTNAME', 'tre'),
                    action_type='incident_reopened',
                    subject={'type': 'incident', 'id': incident_id},
                    actor={'type': 'user', 'identifier': user_id},
                    payload={
                        'previous_status': current_status,
                        'new_status': 'IN_PROGRESS',
                        'justification': justification,
                        'reopened_by': user_id
                    }
                )
            
            return {
                'status': 'REOPENED',
                'incident_id': incident_id,
                'previous_status': current_status,
                'new_status': 'IN_PROGRESS',
                'reopened_by': user_id,
                'reopened_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
        finally:
            conn.close()
