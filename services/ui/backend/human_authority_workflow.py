#!/usr/bin/env python3
"""
RansomEye v1.0 UI Backend - Human Authority Workflow
AUTHORITATIVE: Two-step approval workflow for destructive actions (NO ASSUMPTIONS)
Python 3.10+ only
"""

import os
import sys
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
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
    _logger = setup_logging('ui-haf-workflow')
except ImportError:
    _common_available = False
    _logger = None


class HumanAuthorityWorkflow:
    """
    Two-step approval workflow for destructive actions.
    
    Workflow:
    1. Analyst submits destructive action request
    2. Approver (SUPER_ADMIN or delegated authority) approves
    3. TRE executes ONLY after approval_id is present
    """
    
    def __init__(self, db_conn_params: Dict[str, Any]):
        """
        Initialize human authority workflow.
        
        Args:
            db_conn_params: Database connection parameters
        """
        self.db_conn_params = db_conn_params
    
    def submit_destructive_action_request(
        self,
        user_id: str,
        user_role: str,
        action_type: str,
        incident_id: str,
        target: Dict[str, Any],
        justification: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit destructive action request for approval.
        
        Args:
            user_id: User identifier (analyst)
            user_role: User role (analyst)
            action_type: Action type
            incident_id: Incident identifier
            target: Target object
            justification: Optional justification
        
        Returns:
            Approval request dictionary
        """
        approval_id = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        
        conn = create_write_connection(**self.db_conn_params, isolation_level=IsolationLevel.READ_COMMITTED, logger=_logger)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO tre_action_approvals (
                        approval_id, action_id, requested_by_user_id, requested_by_role,
                        approval_status, expires_at, reason
                    ) VALUES (%s, %s, %s, %s, 'PENDING', %s, %s)
                """, (
                    approval_id,
                    str(uuid.uuid4()),  # Temporary action_id (will be updated when action is created)
                    user_id,
                    user_role,
                    expires_at,
                    justification
                ))
                conn.commit()
            
            return {
                'approval_id': approval_id,
                'status': 'PENDING',
                'requested_by': user_id,
                'requested_by_role': user_role,
                'action_type': action_type,
                'incident_id': incident_id,
                'expires_at': expires_at.isoformat().replace('+00:00', 'Z'),
                'justification': justification
            }
        finally:
            conn.close()
    
    def approve_action(
        self,
        approval_id: str,
        approver_user_id: str,
        approver_role: str,
        approval_decision: str = 'APPROVED',
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Approve or reject destructive action request.
        
        Args:
            approval_id: Approval identifier
            approver_user_id: Approver user identifier
            approver_role: Approver role (must be SUPER_ADMIN or SECURITY_ANALYST with approval rights)
            approval_decision: Approval decision (APPROVED or REJECTED)
            reason: Optional reason
        
        Returns:
            Approval result dictionary
        
        Raises:
            ValueError: If approval fails
        """
        # Validate approver role
        if approver_role not in ('SUPER_ADMIN', 'SECURITY_ANALYST'):
            raise ValueError(f"Approver role {approver_role} cannot approve actions")
        
        conn = create_write_connection(**self.db_conn_params, isolation_level=IsolationLevel.READ_COMMITTED, logger=_logger)
        try:
            with conn.cursor() as cur:
                # Get approval request
                cur.execute("""
                    SELECT approval_id, approval_status, expires_at
                    FROM tre_action_approvals
                    WHERE approval_id = %s
                """, (approval_id,))
                row = cur.fetchone()
                
                if not row:
                    raise ValueError(f"Approval request not found: {approval_id}")
                
                approval_id_db, status, expires_at = row
                
                if status != 'PENDING':
                    raise ValueError(f"Approval request {approval_id} is not pending (status: {status})")
                
                if datetime.fromisoformat(expires_at.replace('Z', '+00:00')) < datetime.now(timezone.utc):
                    # Mark as expired
                    cur.execute("""
                        UPDATE tre_action_approvals
                        SET approval_status = 'EXPIRED',
                            approver_user_id = %s,
                            approver_role = %s,
                            approval_timestamp = %s
                        WHERE approval_id = %s
                    """, (approver_user_id, approver_role, datetime.now(timezone.utc), approval_id))
                    conn.commit()
                    raise ValueError(f"Approval request {approval_id} has expired")
                
                # Update approval
                cur.execute("""
                    UPDATE tre_action_approvals
                    SET approval_status = %s,
                        approver_user_id = %s,
                        approver_role = %s,
                        approval_decision = %s,
                        approval_timestamp = %s,
                        reason = %s
                    WHERE approval_id = %s
                """, (
                    approval_decision,
                    approver_user_id,
                    approver_role,
                    approval_decision,
                    datetime.now(timezone.utc),
                    reason,
                    approval_id
                ))
                conn.commit()
            
            return {
                'approval_id': approval_id,
                'status': approval_decision,
                'approver': approver_user_id,
                'approver_role': approver_role,
                'approved_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                'reason': reason
            }
        finally:
            conn.close()
    
    def get_pending_approvals(
        self,
        user_id: Optional[str] = None,
        incident_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get pending approval requests.
        
        Args:
            user_id: Optional user identifier filter
            incident_id: Optional incident identifier filter
        
        Returns:
            List of pending approval requests
        """
        conn = create_write_connection(**self.db_conn_params, isolation_level=IsolationLevel.READ_COMMITTED, logger=_logger)
        try:
            with conn.cursor() as cur:
                query = """
                    SELECT approval_id, action_id, requested_by_user_id, requested_by_role,
                           approval_status, expires_at, reason, created_at
                    FROM tre_action_approvals
                    WHERE approval_status = 'PENDING'
                """
                params = []
                
                if user_id:
                    query += " AND requested_by_user_id = %s"
                    params.append(user_id)
                
                if incident_id:
                    # Note: incident_id would need to be joined from response_actions
                    # This is a simplified version
                    pass
                
                query += " ORDER BY created_at DESC"
                
                cur.execute(query, params)
                rows = cur.fetchall()
                
                return [
                    {
                        'approval_id': row[0],
                        'action_id': row[1],
                        'requested_by': row[2],
                        'requested_by_role': row[3],
                        'status': row[4],
                        'expires_at': row[5].isoformat() if row[5] else None,
                        'reason': row[6],
                        'created_at': row[7].isoformat() if row[7] else None
                    }
                    for row in rows
                ]
        finally:
            conn.close()
