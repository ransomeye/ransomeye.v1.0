#!/usr/bin/env python3
"""
RansomEye v1.0 RBAC FastAPI Middleware
AUTHORITATIVE: Server-side permission enforcement for FastAPI
Python 3.10+ only
"""

import os
import sys
from datetime import datetime, timezone
from typing import Optional, Callable, Dict, Any
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

try:
    import jwt
    _jwt_available = True
except ImportError:
    jwt = None
    _jwt_available = False

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Add rbac to path
_rbac_path = os.path.join(_project_root, 'rbac')
if os.path.exists(_rbac_path) and _rbac_path not in sys.path:
    sys.path.insert(0, _rbac_path)

from rbac.api.rbac_api import RBACAPI, RBACAPIError
from rbac.engine.permission_checker import PermissionChecker, PermissionDeniedError

# Security scheme (explicit 401 handling)
security = HTTPBearer(auto_error=False)


class RBACAuth:
    """
    RBAC authentication and authorization for FastAPI.
    
    CRITICAL: Server-side enforcement (default DENY).
    UI hiding is insufficient; backend must block unauthorized actions.
    """
    
    def __init__(
        self,
        rbac_api: RBACAPI,
        jwt_signing_key: str,
        jwt_issuer: str = "ransomeye-ui",
        jwt_audience: str = "ransomeye-ui",
        leeway_seconds: int = 30,
        logger: Optional[Any] = None,
        auth_audit_logger: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        Initialize RBAC auth.
        
        Args:
            rbac_api: RBAC API instance
            jwt_signing_key: JWT signing key (HS256)
            jwt_issuer: JWT issuer claim
            jwt_audience: JWT audience claim
            leeway_seconds: Allowed clock skew in seconds
            logger: Optional logger instance
            auth_audit_logger: Optional auth decision audit logger
        """
        self.rbac_api = rbac_api
        self.permission_checker = rbac_api.permission_checker
        self.jwt_signing_key = jwt_signing_key
        self.jwt_issuer = jwt_issuer
        self.jwt_audience = jwt_audience
        self.leeway_seconds = leeway_seconds
        self.logger = logger
        self.auth_audit_logger = auth_audit_logger

        if not self.jwt_signing_key:
            raise RBACAPIError("JWT signing key is required")
        if not _jwt_available:
            raise RBACAPIError("JWT library not available (PyJWT not installed)")

    def _audit_auth(self, payload: Dict[str, Any]) -> None:
        if self.auth_audit_logger:
            try:
                self.auth_audit_logger(payload)
            except Exception:
                if self.logger:
                    self.logger.warning("Auth audit logging failed")

    def _decode_token(self, token: str) -> Dict[str, Any]:
        return jwt.decode(
            token,
            self.jwt_signing_key,
            algorithms=["HS256"],
            audience=self.jwt_audience,
            issuer=self.jwt_issuer,
            options={
                "require": ["sub", "iat", "exp", "token_type"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True
            },
            leeway=self.leeway_seconds
        )

    def _extract_subject_unverified(self, token: str) -> Optional[str]:
        if not _jwt_available:
            return None
        try:
            payload = jwt.decode(
                token,
                options={
                    "verify_signature": False,
                    "verify_exp": False,
                    "verify_iat": False,
                    "verify_aud": False,
                    "verify_iss": False
                }
            )
            return payload.get("sub")
        except Exception:
            return None
    
    async def get_current_user(
        self,
        request: Request,
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
        if not credentials or not credentials.credentials:
            self._audit_auth({
                "decision": "DENY",
                "reason": "missing_token",
                "path": str(request.url.path),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            raise HTTPException(status_code=401, detail="Missing token")

        token = credentials.credentials
        try:
            payload = self._decode_token(token)
        except jwt.ExpiredSignatureError as exc:
            self._audit_auth({
                "decision": "DENY",
                "reason": "token_expired",
                "path": str(request.url.path),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            raise HTTPException(status_code=401, detail="Token expired") from exc
        except jwt.InvalidSignatureError as exc:
            subject = self._extract_subject_unverified(token)
            entry = {
                "decision": "DENY",
                "reason": "token_tampered",
                "error": "invalid_signature",
                "path": str(request.url.path),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            if subject:
                entry["user_id"] = subject
            self._audit_auth(entry)
            raise HTTPException(status_code=401, detail="Invalid token") from exc
        except jwt.InvalidTokenError as exc:
            subject = self._extract_subject_unverified(token)
            entry = {
                "decision": "DENY",
                "reason": "invalid_token",
                "path": str(request.url.path),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            if subject:
                entry["user_id"] = subject
            self._audit_auth(entry)
            raise HTTPException(status_code=401, detail="Invalid token") from exc
        token_type = payload.get("token_type")
        if token_type not in ("access", "service"):
            self._audit_auth({
                "decision": "DENY",
                "reason": "invalid_token_type",
                "token_type": token_type,
                "path": str(request.url.path),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id = payload.get("sub")
        if not user_id:
            self._audit_auth({
                "decision": "DENY",
                "reason": "missing_subject",
                "path": str(request.url.path),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            raise HTTPException(status_code=401, detail="Invalid token subject")

        try:
            user = self.rbac_api.get_user_by_id(user_id)
        except Exception as exc:
            self._audit_auth({
                "decision": "DENY",
                "reason": "rbac_user_lookup_failed",
                "user_id": user_id,
                "path": str(request.url.path),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            raise HTTPException(status_code=503, detail="Authentication backend unavailable") from exc

        if not user or not user.get("is_active"):
            self._audit_auth({
                "decision": "DENY",
                "reason": "user_inactive",
                "user_id": user_id,
                "path": str(request.url.path),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            raise HTTPException(status_code=401, detail="User inactive or missing")

        current_user = {
            "user_id": user_id,
            "username": payload.get("username", user.get("username")),
            "role": payload.get("role"),
            "token_type": token_type
        }

        self._audit_auth({
            "decision": "ALLOW",
            "reason": "token_valid",
            "user_id": user_id,
            "path": str(request.url.path),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        return current_user
    
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
