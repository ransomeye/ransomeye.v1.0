#!/usr/bin/env python3
"""
RansomEye v1.0 RBAC FastAPI Middleware
AUTHORITATIVE: Server-side permission enforcement for FastAPI
Python 3.10+ only
"""

import os
import sys
from typing import Optional, Callable, Dict, Any
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Add rbac to path
_rbac_path = os.path.join(_project_root, 'rbac')
if os.path.exists(_rbac_path) and _rbac_path not in sys.path:
    sys.path.insert(0, _rbac_path)

from api.rbac_api import RBACAPI, RBACAPIError
from engine.permission_checker import PermissionChecker, PermissionDeniedError

# Security scheme
security = HTTPBearer()


class RBACAuth:
    """
    RBAC authentication and authorization for FastAPI.
    
    CRITICAL: Server-side enforcement (default DENY).
    UI hiding is insufficient; backend must block unauthorized actions.
    """
    
    def __init__(self, rbac_api: RBACAPI):
        """
        Initialize RBAC auth.
        
        Args:
            rbac_api: RBAC API instance
        """
        self.rbac_api = rbac_api
        self.permission_checker = rbac_api.permission_checker
    
    async def get_current_user(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> Dict[str, Any]:
        """
        Get current authenticated user from token.
        
        Args:
            credentials: HTTP Bearer token credentials
        
        Returns:
            User dictionary
        
        Raises:
            HTTPException: If authentication fails
        """
        # TODO: Implement JWT token validation
        # For now, extract user_id from token (placeholder)
        token = credentials.credentials
        
        # Simple token format: user_id:username (temporary)
        # In production, use JWT with proper signing
        try:
            user_id, username = token.split(':', 1)
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid token format")
        
        # Verify user exists and is active
        # This is a simplified check; in production, validate JWT signature
        try:
            # For now, return user dict (in production, validate JWT)
            return {
                'user_id': user_id,
                'username': username
            }
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")
    
    def require_permission(
        self,
        permission: str,
        resource_type: str = 'global',
        resource_id: Optional[str] = None
    ) -> Callable:
        """
        Decorator to require permission for endpoint.
        
        Args:
            permission: Permission name
            resource_type: Resource type
            resource_id: Optional resource identifier
        
        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            async def wrapper(
                request: Request,
                current_user: Dict[str, Any] = Depends(self.get_current_user),
                *args,
                **kwargs
            ):
                user_id = current_user.get('user_id')
                if not user_id:
                    raise HTTPException(status_code=401, detail="User not authenticated")
                
                # Check permission
                try:
                    has_permission = self.permission_checker.check_permission(
                        user_id=user_id,
                        permission=permission,
                        resource_type=resource_type,
                        resource_id=resource_id
                    )
                    
                    if not has_permission:
                        raise HTTPException(
                            status_code=403,
                            detail=f"Permission denied: {permission}"
                        )
                except PermissionDeniedError:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Permission denied: {permission}"
                    )
                except Exception as e:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Permission check failed: {e}"
                    )
                
                # Add user to request state
                request.state.user = current_user
                request.state.user_id = user_id
                
                return await func(request, current_user, *args, **kwargs)
            
            return wrapper
        return decorator
    
    def get_user_permissions(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's permissions (for UI rendering).
        
        Args:
            user_id: User identifier
        
        Returns:
            Dictionary with permissions list
        """
        try:
            permissions = self.permission_checker.get_user_permissions(user_id)
            return {
                'permissions': list(permissions),
                'user_id': user_id
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get user permissions: {e}"
            )
