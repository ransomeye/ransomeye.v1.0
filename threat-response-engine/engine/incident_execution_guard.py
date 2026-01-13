#!/usr/bin/env python3
"""
RansomEye v1.0 Threat Response Engine - Incident Execution Guard
AUTHORITATIVE: Enforces incident-bound execution (NO ASSUMPTIONS)
Python 3.10+ only
"""

import os
import sys
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
    _logger = setup_logging('tre-incident-guard')
except ImportError:
    _common_available = False
    _logger = None

# Add threat-response-engine to path
_threat_response_path = os.path.join(_project_root, 'threat-response-engine')
if os.path.exists(_threat_response_path) and _threat_response_path not in sys.path:
    sys.path.insert(0, _threat_response_path)


class IncidentExecutionError(Exception):
    """Exception raised when incident execution guard fails."""
    pass


class IncidentExecutionGuard:
    """
    Enforces incident-bound execution.
    
    CRITICAL: All response actions must be incident-scoped.
    Actions without incident context are REJECTED (except SUPER_ADMIN emergency path).
    """
    
    def __init__(self, db_conn_params: Dict[str, Any]):
        """
        Initialize incident execution guard.
        
        Args:
            db_conn_params: Database connection parameters
        """
        self.db_conn_params = db_conn_params
    
    def validate_incident_context(
        self,
        incident_id: Optional[str],
        user_id: str,
        user_role: str,
        is_emergency: bool = False
    ) -> Dict[str, Any]:
        """
        Validate incident context for action execution.
        
        Args:
            incident_id: Incident identifier (required unless emergency)
            user_id: User identifier
            user_role: User role
            is_emergency: Whether this is an emergency override
        
        Returns:
            Incident context dictionary
        
        Raises:
            IncidentExecutionError: If incident context is invalid
        """
        # Emergency override (SUPER_ADMIN only)
        if is_emergency:
            if user_role != 'SUPER_ADMIN':
                raise IncidentExecutionError(
                    "Emergency override requires SUPER_ADMIN role"
                )
            return {
                'incident_id': None,
                'incident_stage': 'EMERGENCY',
                'is_emergency': True,
                'valid': True
            }
        
        # Incident ID required for non-emergency actions
        if not incident_id:
            raise IncidentExecutionError(
                "Incident ID required for all non-emergency actions"
            )
        
        # Validate incident exists and is active
        conn = create_write_connection(**self.db_conn_params, isolation_level=IsolationLevel.READ_COMMITTED, logger=_logger)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT incident_id, stage, status
                    FROM incidents
                    WHERE incident_id = %s
                """, (incident_id,))
                row = cur.fetchone()
                
                if not row:
                    raise IncidentExecutionError(
                        f"Incident not found: {incident_id}"
                    )
                
                incident_id_db, stage, status = row
                
                # Reject if incident is CLOSED or ARCHIVED
                if status in ('CLOSED', 'ARCHIVED'):
                    raise IncidentExecutionError(
                        f"Incident {incident_id} is {status} - actions are blocked"
                    )
                
                return {
                    'incident_id': incident_id_db,
                    'incident_stage': stage,
                    'incident_status': status,
                    'is_emergency': False,
                    'valid': True
                }
        finally:
            conn.close()
    
    def validate_action_requirements(
        self,
        incident_context: Dict[str, Any],
        policy_decision_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate action requirements (incident_id, incident_stage, policy_decision_id).
        
        Args:
            incident_context: Incident context from validate_incident_context
            policy_decision_id: Optional policy decision identifier
        
        Returns:
            Validated requirements dictionary
        
        Raises:
            IncidentExecutionError: If requirements are invalid
        """
        if not incident_context.get('valid'):
            raise IncidentExecutionError("Invalid incident context")
        
        # For non-emergency actions, policy_decision_id is recommended but not mandatory
        # (some actions may be manually triggered)
        
        return {
            'incident_id': incident_context.get('incident_id'),
            'incident_stage': incident_context.get('incident_stage'),
            'policy_decision_id': policy_decision_id,
            'is_emergency': incident_context.get('is_emergency', False)
        }
