#!/usr/bin/env python3
"""
RansomEye v1.0 RBAC Integration with Policy Engine
AUTHORITATIVE: Permission enforcement for Policy Engine operations
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


class PolicyPermissionEnforcer:
    """
    Permission enforcer for Policy Engine operations.
    
    CRITICAL: Server-side enforcement (default DENY).
    All Policy Engine operations must check permissions before execution.
    """
    
    def __init__(self, permission_checker: PermissionChecker):
        """
        Initialize Policy permission enforcer.
        
        Args:
            permission_checker: Permission checker instance
        """
        self.permission_checker = permission_checker
    
    def check_edit_permission(
        self,
        user_id: str,
        policy_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has permission to edit policies.
        
        Required permission: policy:update or policy:create
        
        Args:
            user_id: User identifier
            policy_id: Optional policy identifier (for update)
        
        Returns:
            True if permission granted
        
        Raises:
            PermissionDeniedError: If permission denied
        """
        # For updates, check policy:update
        if policy_id:
            has_permission = self.permission_checker.check_permission(
                user_id=user_id,
                permission='policy:update',
                resource_type='policy',
                resource_id=policy_id
            )
        else:
            # For creates, check policy:create
            has_permission = self.permission_checker.check_permission(
                user_id=user_id,
                permission='policy:create',
                resource_type='policy',
                resource_id=None
            )
        
        if not has_permission:
            raise PermissionDeniedError(
                f"User {user_id} lacks permission to edit policies"
            )
        
        return True
    
    def check_delete_permission(
        self,
        user_id: str,
        policy_id: str
    ) -> bool:
        """
        Check if user has permission to delete policies.
        
        Required permission: policy:delete
        
        Args:
            user_id: User identifier
            policy_id: Policy identifier
        
        Returns:
            True if permission granted
        
        Raises:
            PermissionDeniedError: If permission denied
        """
        has_permission = self.permission_checker.check_permission(
            user_id=user_id,
            permission='policy:delete',
            resource_type='policy',
            resource_id=policy_id
        )
        
        if not has_permission:
            raise PermissionDeniedError(
                f"User {user_id} lacks permission 'policy:delete'"
            )
        
        return True
    
    def check_simulate_permission(
        self,
        user_id: str,
        policy_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has permission to simulate policies.
        
        Required permission: policy:simulate
        
        Args:
            user_id: User identifier
            policy_id: Optional policy identifier
        
        Returns:
            True if permission granted
        
        Raises:
            PermissionDeniedError: If permission denied
        """
        has_permission = self.permission_checker.check_permission(
            user_id=user_id,
            permission='policy:simulate',
            resource_type='policy',
            resource_id=policy_id
        )
        
        if not has_permission:
            raise PermissionDeniedError(
                f"User {user_id} lacks permission 'policy:simulate'"
            )
        
        return True
    
    def check_view_permission(
        self,
        user_id: str,
        policy_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has permission to view policies.
        
        Required permission: policy:view
        
        Args:
            user_id: User identifier
            policy_id: Optional policy identifier
        
        Returns:
            True if permission granted
        
        Raises:
            PermissionDeniedError: If permission denied
        """
        has_permission = self.permission_checker.check_permission(
            user_id=user_id,
            permission='policy:view',
            resource_type='policy',
            resource_id=policy_id
        )
        
        if not has_permission:
            raise PermissionDeniedError(
                f"User {user_id} lacks permission 'policy:view'"
            )
        
        return True
