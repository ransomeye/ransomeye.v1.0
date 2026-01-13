#!/usr/bin/env python3
"""
RansomEye v1.0 UI Backend - Enforcement Controls
AUTHORITATIVE: Role-aware UI enforcement controls (NO ASSUMPTIONS)
Python 3.10+ only
"""

import os
import sys
from typing import Dict, Any, Optional, List
from pathlib import Path

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Add rbac to path
_rbac_path = os.path.join(_project_root, 'rbac')
if os.path.exists(_rbac_path) and _rbac_path not in sys.path:
    sys.path.insert(0, _rbac_path)

try:
    from common.logging import setup_logging
    _common_available = True
    _logger = setup_logging('ui-enforcement')
except ImportError:
    _common_available = False
    _logger = None

from rbac.engine.permission_checker import PermissionChecker


class UIEnforcementControls:
    """
    Role-aware UI enforcement controls.
    
    CRITICAL: UI must enforce RBAC AND server must enforce RBAC.
    Every click → auditable decision.
    """
    
    def __init__(self, permission_checker: PermissionChecker):
        """
        Initialize UI enforcement controls.
        
        Args:
            permission_checker: Permission checker instance
        """
        self.permission_checker = permission_checker
    
    def get_role_capabilities(self, user_id: str, user_role: str) -> Dict[str, Any]:
        """
        Get UI capabilities for user role.
        
        Role Capabilities:
        - SUPER_ADMIN: All actions + emergency override
        - SECURITY_ANALYST: Execute SAFE actions, request DESTRUCTIVE
        - POLICY_MANAGER: No execution, policy tuning only
        - IT_ADMIN: Agent ops only
        - AUDITOR: Read-only, no buttons
        
        Args:
            user_id: User identifier
            user_role: User role
        
        Returns:
            Dictionary with UI capabilities
        """
        capabilities = {
            'can_execute_safe': False,
            'can_execute_destructive': False,
            'can_request_destructive': False,
            'can_approve_actions': False,
            'can_manage_policies': False,
            'can_manage_agents': False,
            'can_manage_users': False,
            'can_emergency_override': False,
            'can_rollback': False,
            'read_only': False
        }
        
        if user_role == 'SUPER_ADMIN':
            capabilities.update({
                'can_execute_safe': True,
                'can_execute_destructive': True,
                'can_request_destructive': True,
                'can_approve_actions': True,
                'can_manage_policies': True,
                'can_manage_agents': True,
                'can_manage_users': True,
                'can_emergency_override': True,
                'can_rollback': True,
                'read_only': False
            })
        elif user_role == 'SECURITY_ANALYST':
            capabilities.update({
                'can_execute_safe': self.permission_checker.check_permission(
                    user_id, 'tre:execute', 'tre_action', None
                ),
                'can_execute_destructive': False,  # Requires approval
                'can_request_destructive': True,
                'can_approve_actions': self.permission_checker.check_permission(
                    user_id, 'haf:approve', 'haf_override', None
                ),
                'can_rollback': self.permission_checker.check_permission(
                    user_id, 'tre:rollback', 'tre_action', None
                ),
                'read_only': False
            })
        elif user_role == 'POLICY_MANAGER':
            capabilities.update({
                'can_manage_policies': self.permission_checker.check_permission(
                    user_id, 'policy:update', 'policy', None
                ),
                'read_only': False
            })
        elif user_role == 'IT_ADMIN':
            capabilities.update({
                'can_manage_agents': self.permission_checker.check_permission(
                    user_id, 'agent:install', 'agent', None
                ),
                'read_only': False
            })
        elif user_role == 'AUDITOR':
            capabilities.update({
                'read_only': True
            })
        
        return capabilities
    
    def check_action_permission(
        self,
        user_id: str,
        user_role: str,
        action_type: str,
        incident_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check if user can execute action (server-side check).
        
        Args:
            user_id: User identifier
            user_role: User role
            action_type: Action type
            incident_id: Optional incident identifier
        
        Returns:
            Dictionary with permission check result
        """
        # Classify action
        from threat_response_engine.engine.enforcement_mode import classify_action, ActionClassification
        
        try:
            action_classification = classify_action(action_type)
            is_destructive = action_classification == ActionClassification.DESTRUCTIVE
        except ValueError:
            return {
                'allowed': False,
                'reason': f"Unknown action type: {action_type}"
            }
        
        # Check permission
        if is_destructive:
            has_permission = self.permission_checker.check_permission(
                user_id, 'tre:execute', 'tre_action', incident_id
            )
            if not has_permission:
                return {
                    'allowed': False,
                    'reason': 'DESTRUCTIVE actions require tre:execute permission and HAF approval'
                }
        else:
            has_permission = self.permission_checker.check_permission(
                user_id, 'tre:execute', 'tre_action', incident_id
            )
            if not has_permission:
                return {
                    'allowed': False,
                    'reason': 'SAFE actions require tre:execute permission'
                }
        
        return {
            'allowed': True,
            'requires_approval': is_destructive,
            'reason': None
        }
    
    def get_action_button_state(
        self,
        user_id: str,
        user_role: str,
        action_type: str,
        incident_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get action button state for UI rendering.
        
        Args:
            user_id: User identifier
            user_role: User role
            action_type: Action type
            incident_id: Optional incident identifier
        
        Returns:
            Dictionary with button state (enabled, disabled, reason)
        """
        permission_check = self.check_action_permission(
            user_id, user_role, action_type, incident_id
        )
        
        if not permission_check['allowed']:
            return {
                'enabled': False,
                'disabled': True,
                'reason': permission_check['reason'],
                'requires_approval': False
            }
        
        return {
            'enabled': True,
            'disabled': False,
            'reason': None,
            'requires_approval': permission_check.get('requires_approval', False)
        }
