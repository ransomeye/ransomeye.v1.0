#!/usr/bin/env python3
"""
RansomEye v1.0 Threat Response Engine - Enforcement Pipeline
AUTHORITATIVE: Strict execution pipeline with RBAC + HAF (NO ASSUMPTIONS)
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
    _logger = setup_logging('tre-enforcement')
except ImportError:
    _common_available = False
    _logger = None

# Add threat-response-engine to path
_threat_response_path = os.path.join(_project_root, 'threat-response-engine')
if os.path.exists(_threat_response_path) and _threat_response_path not in sys.path:
    sys.path.insert(0, _threat_response_path)

# Add rbac to path
_rbac_path = os.path.join(_project_root, 'rbac')
if os.path.exists(_rbac_path) and _rbac_path not in sys.path:
    sys.path.insert(0, _rbac_path)

# Add human-authority to path
_haf_path = os.path.join(_project_root, 'human-authority')
if os.path.exists(_haf_path) and _haf_path not in sys.path:
    sys.path.insert(0, _haf_path)

from engine.enforcement_mode import (
    TREMode, ActionClassification, classify_action, get_mode_behavior
)
from rbac.integration.tre_integration import TREPermissionEnforcer
from rbac.engine.permission_checker import PermissionDeniedError

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


class EnforcementError(Exception):
    """Exception raised when enforcement fails."""
    pass


class EnforcementPipeline:
    """
    Strict execution pipeline with RBAC + HAF enforcement.
    
    CRITICAL: Default DENY, fail fast, no assumptions.
    """
    
    def __init__(
        self,
        db_conn_params: Dict[str, Any],
        rbac_enforcer: TREPermissionEnforcer,
        haf_api: Optional[Any] = None,
        ledger: Optional[AuditLedger] = None
    ):
        """
        Initialize enforcement pipeline.
        
        Args:
            db_conn_params: Database connection parameters
            rbac_enforcer: RBAC permission enforcer
            haf_api: Optional HAF API instance
            ledger: Optional audit ledger instance
        """
        self.db_conn_params = db_conn_params
        self.rbac_enforcer = rbac_enforcer
        self.haf_api = haf_api
        self.ledger = ledger
    
    def get_current_mode(self) -> TREMode:
        """
        Get current TRE enforcement mode from database.
        
        Returns:
            Current TREMode enum value
        
        Raises:
            EnforcementError: If mode not found or multiple active modes
        """
        conn = create_write_connection(**self.db_conn_params, isolation_level=IsolationLevel.READ_COMMITTED, logger=_logger)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT mode FROM tre_execution_modes
                    WHERE is_active = TRUE
                    ORDER BY changed_at DESC
                    LIMIT 1
                """)
                row = cur.fetchone()
                if not row:
                    # Default to DRY_RUN if no mode set
                    return TREMode.DRY_RUN
                return TREMode(row[0])
        finally:
            conn.close()
    
    def check_rbac_permission(
        self,
        user_id: str,
        action_type: str,
        incident_id: Optional[str] = None
    ) -> bool:
        """
        Step 1: RBAC Permission Check (MANDATORY FIRST STEP).
        
        Args:
            user_id: User identifier
            action_type: Action type string
            incident_id: Optional incident identifier
        
        Returns:
            True if permission granted
        
        Raises:
            PermissionDeniedError: If permission denied
        """
        action_classification = classify_action(action_type)
        
        if action_classification == ActionClassification.SAFE:
            self.rbac_enforcer.check_execute_safe_permission(user_id, incident_id)
        else:
            self.rbac_enforcer.check_execute_destructive_permission(user_id, incident_id)
        
        # Emit audit ledger entry
        if self.ledger:
            self.ledger.append(
                component='rbac',
                component_instance_id=os.getenv('HOSTNAME', 'tre'),
                action_type='rbac_permission_check',
                subject={'type': 'tre_action', 'id': incident_id or 'unknown'},
                actor={'type': 'user', 'identifier': user_id},
                payload={
                    'permission': 'tre:execute',
                    'action_type': action_type,
                    'classification': action_classification.value,
                    'decision': 'ALLOW'
                }
            )
        
        return True
    
    def check_tre_mode(
        self,
        action_type: str
    ) -> Dict[str, Any]:
        """
        Step 2: TRE Mode Check.
        
        Args:
            action_type: Action type string
        
        Returns:
            Dictionary with mode behavior (execute, haf_required, etc.)
        
        Raises:
            EnforcementError: If action is blocked by mode
        """
        mode = self.get_current_mode()
        action_classification = classify_action(action_type)
        behavior = get_mode_behavior(mode, action_classification)
        
        if behavior.get('blocked'):
            raise EnforcementError(
                f"Action {action_type} blocked by mode {mode.value}: {behavior.get('reason')}"
            )
        
        return behavior
    
    def check_haf_approval(
        self,
        action_id: str,
        action_type: str,
        user_id: str,
        user_role: str,
        incident_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Step 3: HAF Approval Check (if required).
        
        Args:
            action_id: Action identifier
            action_type: Action type string
            user_id: User identifier
            user_role: User role
            incident_id: Optional incident identifier
        
        Returns:
            Approval ID if approved, None if not required
        
        Raises:
            EnforcementError: If approval required but not granted
        """
        action_classification = classify_action(action_type)
        mode = self.get_current_mode()
        behavior = get_mode_behavior(mode, action_classification)
        
        if not behavior.get('haf_required'):
            return None
        
        # Check if approval exists
        conn = create_write_connection(**self.db_conn_params, isolation_level=IsolationLevel.READ_COMMITTED, logger=_logger)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT approval_id, approval_status, approver_user_id, approver_role
                    FROM tre_action_approvals
                    WHERE action_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (action_id,))
                row = cur.fetchone()
                
                if row:
                    approval_id, status, approver_user_id, approver_role = row
                    if status == 'APPROVED':
                        return approval_id
                    elif status == 'REJECTED':
                        raise EnforcementError(
                            f"HAF approval rejected for action {action_id}"
                        )
                    elif status == 'EXPIRED':
                        raise EnforcementError(
                            f"HAF approval expired for action {action_id}"
                        )
                    else:
                        # PENDING - wait for approval
                        raise EnforcementError(
                            f"HAF approval pending for action {action_id}"
                        )
                else:
                    # Create approval request
                    approval_id = str(uuid.uuid4())
                    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
                    
                    cur.execute("""
                        INSERT INTO tre_action_approvals (
                            approval_id, action_id, requested_by_user_id, requested_by_role,
                            approval_status, expires_at
                        ) VALUES (%s, %s, %s, %s, 'PENDING', %s)
                    """, (approval_id, action_id, user_id, user_role, expires_at))
                    conn.commit()
                    
                    # Emit audit ledger entry
                    if self.ledger:
                        self.ledger.append(
                            component='threat-response-engine',
                            component_instance_id=os.getenv('HOSTNAME', 'tre'),
                            action_type='tre_action_requested',
                            subject={'type': 'tre_action', 'id': action_id},
                            actor={'type': 'user', 'identifier': user_id},
                            payload={
                                'action_type': action_type,
                                'classification': action_classification.value,
                                'approval_id': approval_id,
                                'incident_id': incident_id
                            }
                        )
                    
                    raise EnforcementError(
                        f"HAF approval required for action {action_id}. Approval request created: {approval_id}"
                    )
        finally:
            conn.close()
    
    def execute_pipeline(
        self,
        policy_decision: Dict[str, Any],
        user_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """
        Execute full enforcement pipeline.
        
        Pipeline order:
        1. Policy Decision (input)
        2. RBAC Permission Check
        3. TRE Mode Check
        4. Action Classification Check
        5. HAF Approval Check (if required)
        6. Return execution result (actual execution happens in TREAPI)
        
        Args:
            policy_decision: Policy decision dictionary
            user_id: User identifier
            user_role: User role
        
        Returns:
            Dictionary with execution result
        
        Raises:
            PermissionDeniedError: If RBAC check fails
            EnforcementError: If enforcement check fails
        """
        action_type = policy_decision.get('recommended_action', '')
        incident_id = policy_decision.get('incident_id', '')
        action_id = str(uuid.uuid4())
        
        # Step 1: RBAC Permission Check (MANDATORY FIRST)
        try:
            self.check_rbac_permission(user_id, action_type, incident_id)
        except PermissionDeniedError as e:
            # Emit audit ledger entry for denial
            if self.ledger:
                self.ledger.append(
                    component='rbac',
                    component_instance_id=os.getenv('HOSTNAME', 'tre'),
                    action_type='rbac_user_action_denied',
                    subject={'type': 'tre_action', 'id': incident_id or 'unknown'},
                    actor={'type': 'user', 'identifier': user_id},
                    payload={
                        'permission': 'tre:execute',
                        'action_type': action_type,
                        'role': user_role,
                        'reason': str(e)
                    }
                )
            raise
        
        # Step 2: TRE Mode Check
        try:
            behavior = self.check_tre_mode(action_type)
        except EnforcementError as e:
            # Emit audit ledger entry for block
            if self.ledger:
                self.ledger.append(
                    component='threat-response-engine',
                    component_instance_id=os.getenv('HOSTNAME', 'tre'),
                    action_type='tre_action_blocked',
                    subject={'type': 'tre_action', 'id': action_id},
                    actor={'type': 'user', 'identifier': user_id},
                    payload={
                        'action_type': action_type,
                        'incident_id': incident_id,
                        'reason': str(e)
                    }
                )
            raise
        
        # Step 3: Action Classification Check (implicit in mode check)
        action_classification = classify_action(action_type)
        
        # Step 4: HAF Approval Check (if required)
        approval_id = None
        if behavior.get('haf_required'):
            try:
                approval_id = self.check_haf_approval(
                    action_id, action_type, user_id, user_role, incident_id
                )
            except EnforcementError as e:
                # Emit audit ledger entry for HAF denial
                if self.ledger:
                    self.ledger.append(
                        component='threat-response-engine',
                        component_instance_id=os.getenv('HOSTNAME', 'tre'),
                        action_type='tre_haf_deny',
                        subject={'type': 'tre_action', 'id': action_id},
                        actor={'type': 'user', 'identifier': user_id},
                        payload={
                            'action_type': action_type,
                            'incident_id': incident_id,
                            'reason': str(e)
                        }
                    )
                raise
        
        # Pipeline passed - return execution metadata
        return {
            'action_id': action_id,
            'execute': behavior.get('execute', False),
            'haf_required': behavior.get('haf_required', False),
            'approval_id': approval_id,
            'classification': action_classification.value,
            'mode': self.get_current_mode().value
        }
