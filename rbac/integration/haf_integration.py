#!/usr/bin/env python3
"""
RansomEye v1.0 RBAC Integration with Human Authority Framework (HAF)
AUTHORITATIVE: Permission enforcement for HAF operations
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


class HAFPermissionEnforcer:
    """
    Permission enforcer for Human Authority Framework operations.
    
    CRITICAL: RBAC check happens BEFORE authority check.
    All HAF operations must check permissions before execution.
    """
    
    def __init__(self, permission_checker: PermissionChecker):
        """
        Initialize HAF permission enforcer.
        
        Args:
            permission_checker: Permission checker instance
        """
        self.permission_checker = permission_checker
    
    def check_create_override_permission(
        self,
        user_id: str,
        subject_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has permission to create HAF overrides.
        
        Required permission: haf:create_override
        
        Args:
            user_id: User identifier
            subject_id: Optional subject identifier
        
        Returns:
            True if permission granted
        
        Raises:
            PermissionDeniedError: If permission denied
        """
        has_permission = self.permission_checker.check_permission(
            user_id=user_id,
            permission='haf:create_override',
            resource_type='haf_override',
            resource_id=subject_id
        )
        
        if not has_permission:
            raise PermissionDeniedError(
                f"User {user_id} lacks permission 'haf:create_override'"
            )
        
        return True
    
    def check_approve_permission(
        self,
        user_id: str,
        override_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has permission to approve HAF overrides.
        
        Required permission: haf:approve
        
        Args:
            user_id: User identifier
            override_id: Optional override identifier
        
        Returns:
            True if permission granted
        
        Raises:
            PermissionDeniedError: If permission denied
        """
        has_permission = self.permission_checker.check_permission(
            user_id=user_id,
            permission='haf:approve',
            resource_type='haf_override',
            resource_id=override_id
        )
        
        if not has_permission:
            raise PermissionDeniedError(
                f"User {user_id} lacks permission 'haf:approve'"
            )
        
        return True
    
    def check_view_permission(
        self,
        user_id: str,
        override_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has permission to view HAF overrides.
        
        Required permission: haf:view
        
        Args:
            user_id: User identifier
            override_id: Optional override identifier
        
        Returns:
            True if permission granted
        
        Raises:
            PermissionDeniedError: If permission denied
        """
        has_permission = self.permission_checker.check_permission(
            user_id=user_id,
            permission='haf:view',
            resource_type='haf_override',
            resource_id=override_id
        )
        
        if not has_permission:
            raise PermissionDeniedError(
                f"User {user_id} lacks permission 'haf:view'"
            )
        
        return True
