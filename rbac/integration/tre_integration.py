#!/usr/bin/env python3
"""
RansomEye v1.0 RBAC Integration with Threat Response Engine (TRE)
AUTHORITATIVE: Permission enforcement for TRE operations
Python 3.10+ only
"""

import os
import sys
from typing import Dict, Any, Optional
from pathlib import Path

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Add rbac to path
_rbac_path = os.path.join(_project_root, 'rbac')
if os.path.exists(_rbac_path) and _rbac_path not in sys.path:
    sys.path.insert(0, _rbac_path)

from engine.permission_checker import PermissionChecker, PermissionDeniedError


class TREPermissionEnforcer:
    """
    Permission enforcer for Threat Response Engine operations.
    
    CRITICAL: Server-side enforcement (default DENY).
    All TRE operations must check permissions before execution.
    """
    
    def __init__(self, permission_checker: PermissionChecker):
        """
        Initialize TRE permission enforcer.
        
        Args:
            permission_checker: Permission checker instance
        """
        self.permission_checker = permission_checker
    
    def check_execute_safe_permission(
        self,
        user_id: str,
        incident_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has permission to execute SAFE TRE actions.
        
        Required permission: tre:execute (for SAFE actions)
        
        Args:
            user_id: User identifier
            incident_id: Optional incident identifier
        
        Returns:
            True if permission granted
        
        Raises:
            PermissionDeniedError: If permission denied
        """
        has_permission = self.permission_checker.check_permission(
            user_id=user_id,
            permission='tre:execute',
            resource_type='tre_action',
            resource_id=incident_id
        )
        
        if not has_permission:
            raise PermissionDeniedError(
                f"User {user_id} lacks permission 'tre:execute' for SAFE actions"
            )
        
        return True
    
    def check_execute_destructive_permission(
        self,
        user_id: str,
        incident_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has permission to execute DESTRUCTIVE TRE actions.
        
        Required permission: tre:execute (for DESTRUCTIVE actions)
        
        Args:
            user_id: User identifier
            incident_id: Optional incident identifier
        
        Returns:
            True if permission granted
        
        Raises:
            PermissionDeniedError: If permission denied
        """
        has_permission = self.permission_checker.check_permission(
            user_id=user_id,
            permission='tre:execute',
            resource_type='tre_action',
            resource_id=incident_id
        )
        
        if not has_permission:
            raise PermissionDeniedError(
                f"User {user_id} lacks permission 'tre:execute' for DESTRUCTIVE actions"
            )
        
        return True
    
    def check_admin_permission(
        self,
        user_id: str
    ) -> bool:
        """
        Check if user has permission to change TRE mode.
        
        Required permission: system:modify_config (SUPER_ADMIN only)
        
        Args:
            user_id: User identifier
        
        Returns:
            True if permission granted
        
        Raises:
            PermissionDeniedError: If permission denied
        """
        has_permission = self.permission_checker.check_permission(
            user_id=user_id,
            permission='system:modify_config',
            resource_type='tre_mode',
            resource_id=None
        )
        
        if not has_permission:
            raise PermissionDeniedError(
                f"User {user_id} lacks permission to change TRE mode (requires SUPER_ADMIN)"
            )
        
        return True
    
    def check_rollback_permission(
        self,
        user_id: str,
        action_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has permission to rollback TRE actions.
        
        Required permission: tre:rollback
        
        Args:
            user_id: User identifier
            action_id: Optional action identifier
        
        Returns:
            True if permission granted
        
        Raises:
            PermissionDeniedError: If permission denied
        """
        has_permission = self.permission_checker.check_permission(
            user_id=user_id,
            permission='tre:rollback',
            resource_type='tre_action',
            resource_id=action_id
        )
        
        if not has_permission:
            raise PermissionDeniedError(
                f"User {user_id} lacks permission 'tre:rollback'"
            )
        
        return True
    
    def check_view_permission(
        self,
        user_id: str,
        incident_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has permission to view TRE actions.
        
        Required permission: tre:view or tre:view_all
        
        Args:
            user_id: User identifier
            incident_id: Optional incident identifier
        
        Returns:
            True if permission granted
        
        Raises:
            PermissionDeniedError: If permission denied
        """
        # Check tre:view_all first (broader permission)
        has_view_all = self.permission_checker.check_permission(
            user_id=user_id,
            permission='tre:view_all',
            resource_type='tre_action',
            resource_id=None
        )
        
        if has_view_all:
            return True
        
        # Check tre:view (specific resource)
        has_view = self.permission_checker.check_permission(
            user_id=user_id,
            permission='tre:view',
            resource_type='tre_action',
            resource_id=incident_id
        )
        
        if not has_view:
            raise PermissionDeniedError(
                f"User {user_id} lacks permission 'tre:view' or 'tre:view_all'"
            )
        
        return True
