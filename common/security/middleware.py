#!/usr/bin/env python3
"""
RansomEye v1.0 Service Authentication Middleware
AUTHORITATIVE: FastAPI middleware for service-to-service authentication
Python 3.10+ only
"""

import os
from typing import Optional, Callable
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

try:
    from common.security.service_auth import ServiceAuthManager, ServiceAuthError
    _service_auth_available = True
except ImportError:
    _service_auth_available = False


class ServiceAuthMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for service-to-service authentication.
    
    Verifies JWT tokens in Authorization header for all requests.
    """
    
    def __init__(self, app, service_name: str, key_dir: Optional[str] = None):
        """
        Initialize service authentication middleware.
        
        Args:
            app: FastAPI application
            service_name: Service identifier (for audience verification)
            key_dir: Directory containing service keys
        """
        super().__init__(app)
        self.service_name = service_name
        
        if not _service_auth_available:
            raise RuntimeError("Service authentication not available (common.security.service_auth not found)")
        
        try:
            key_dir_path = None
            if key_dir:
                from pathlib import Path
                key_dir_path = Path(key_dir)
            
            self.auth_manager = ServiceAuthManager(service_name, key_dir_path)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize service authentication: {e}") from e
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Process request with service authentication.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response
        """
        # Skip authentication for health checks and public endpoints
        if request.url.path in ['/health', '/health/metrics', '/docs', '/openapi.json', '/redoc']:
            return await call_next(request)

        # CI-only: allow unauthenticated ingest events when explicitly enabled
        if (
            request.url.path == '/events'
            and os.getenv("CI") == "true"
            and os.getenv("RANSOMEYE_ENV") == "ci"
            and os.getenv("RANSOMEYE_ALLOW_UNAUTH_INGEST") == "1"
        ):
            return await call_next(request)
        
        # Get Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error_code": "MISSING_AUTHORIZATION", "message": "Authorization header required"}
            )
        
        # Extract Bearer token
        if not auth_header.startswith('Bearer '):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error_code": "INVALID_AUTHORIZATION_FORMAT", "message": "Authorization header must be 'Bearer <token>'"}
            )
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        # Verify token
        try:
            payload = self.auth_manager.verify_token(token)
            
            # Add service identity to request state
            request.state.service_identity = {
                'iss': payload.get('iss'),  # Issuer (source service)
                'aud': payload.get('aud'),  # Audience (target service)
                'sub': payload.get('sub'),  # Subject (source service)
                'key_id': payload.get('key_id')  # Key identifier
            }
        except ServiceAuthError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error_code": "AUTHENTICATION_FAILED", "message": str(e)}
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error_code": "AUTHENTICATION_ERROR", "message": "Internal authentication error"}
            )
        
        # Continue to next middleware/handler
        return await call_next(request)


def get_service_identity(request: Request) -> dict:
    """
    Get service identity from request state.
    
    Args:
        request: FastAPI request
        
    Returns:
        Service identity dictionary
    """
    return getattr(request.state, 'service_identity', {})
