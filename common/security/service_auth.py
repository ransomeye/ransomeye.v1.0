#!/usr/bin/env python3
"""
RansomEye v1.0 Service-to-Service Authentication
AUTHORITATIVE: Signed JWT-based service authentication for zero-trust model
Python 3.10+ only
"""

import os
import sys
import json
import time
import base64
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import jwt
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    _jwt_available = True
except ImportError:
    _jwt_available = False
    jwt = None


class ServiceAuthError(Exception):
    """Service authentication error."""
    pass


class ServiceIdentity:
    """
    Service identity for zero-trust authentication.
    
    Each service has:
    - service_name: Unique service identifier (e.g., "ingest", "correlation-engine")
    - private_key: Ed25519 private key for signing JWTs
    - public_key: Ed25519 public key for verification
    - key_id: SHA256 hash of public key (for key rotation support)
    """
    
    def __init__(
        self,
        service_name: str,
        private_key: Optional[Ed25519PrivateKey] = None,
        public_key: Optional[Ed25519PublicKey] = None,
        key_id: Optional[str] = None
    ):
        """
        Initialize service identity.
        
        Args:
            service_name: Service identifier
            private_key: Ed25519 private key (for signing)
            public_key: Ed25519 public key (for verification)
            key_id: Key identifier (SHA256 of public key)
        """
        self.service_name = service_name
        
        if private_key:
            self.private_key = private_key
            # Derive public key from private key
            self.public_key = private_key.public_key()
        elif public_key:
            self.public_key = public_key
            self.private_key = None
        else:
            raise ServiceAuthError("Either private_key or public_key must be provided")
        
        # Derive key_id from public key
        if key_id:
            self.key_id = key_id
        else:
            public_key_bytes = self.public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            self.key_id = hashlib.sha256(public_key_bytes).hexdigest()
    
    @classmethod
    def from_key_file(cls, service_name: str, key_path: Path, is_private: bool = True) -> 'ServiceIdentity':
        """
        Load service identity from key file.
        
        Args:
            service_name: Service identifier
            key_path: Path to key file (PEM format)
            is_private: True if private key, False if public key
            
        Returns:
            ServiceIdentity instance
        """
        if not key_path.exists():
            raise ServiceAuthError(f"Key file not found: {key_path}")
        
        try:
            with open(key_path, 'rb') as f:
                key_data = f.read()
            
            if is_private:
                private_key = serialization.load_pem_private_key(
                    key_data,
                    password=None,
                    backend=default_backend()
                )
                if not isinstance(private_key, Ed25519PrivateKey):
                    raise ServiceAuthError(f"Key is not Ed25519 private key: {key_path}")
                return cls(service_name, private_key=private_key)
            else:
                public_key = serialization.load_pem_public_key(
                    key_data,
                    backend=default_backend()
                )
                if not isinstance(public_key, Ed25519PublicKey):
                    raise ServiceAuthError(f"Key is not Ed25519 public key: {key_path}")
                return cls(service_name, public_key=public_key)
        except Exception as e:
            raise ServiceAuthError(f"Failed to load key from {key_path}: {e}") from e
    
    def sign_jwt(self, audience: str, expires_in: int = 300) -> str:
        """
        Sign a JWT token for service-to-service authentication.
        
        Args:
            audience: Target service name (aud claim)
            expires_in: Token expiration in seconds (default: 5 minutes)
            
        Returns:
            Signed JWT token string
        """
        if not self.private_key:
            raise ServiceAuthError("Cannot sign JWT: no private key available")
        
        if not _jwt_available:
            raise ServiceAuthError("JWT library not available (PyJWT not installed)")
        
        now = datetime.now(timezone.utc)
        payload = {
            'iss': self.service_name,  # Issuer (source service)
            'aud': audience,  # Audience (target service)
            'sub': self.service_name,  # Subject (source service)
            'iat': int(now.timestamp()),  # Issued at
            'exp': int((now + timedelta(seconds=expires_in)).timestamp()),  # Expiration
            'key_id': self.key_id  # Key identifier (for rotation support)
        }
        
        # Sign with Ed25519 private key
        try:
            # Convert Ed25519 private key to PEM for PyJWT
            private_key_bytes = self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            # PyJWT with Ed25519 expects PEM-encoded key material
            token = jwt.encode(
                payload,
                private_key_bytes,
                algorithm='EdDSA'  # Ed25519 algorithm
            )
            return token
        except Exception as e:
            raise ServiceAuthError(f"Failed to sign JWT: {e}") from e
    
    def verify_jwt(self, token: str, expected_audience: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify a JWT token.
        
        Args:
            token: JWT token string
            expected_audience: Expected audience (target service name)
            
        Returns:
            Decoded JWT payload
            
        Raises:
            ServiceAuthError: If verification fails
        """
        if not _jwt_available:
            raise ServiceAuthError("JWT library not available (PyJWT not installed)")
        
        try:
            # Convert Ed25519 public key to PEM for PyJWT
            public_key_bytes = self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            # Verify token
            options = {
                'verify_signature': True,
                'verify_exp': True,
                'verify_iat': True,
                'require': ['iss', 'aud', 'sub', 'iat', 'exp', 'key_id']
            }
            
            payload = jwt.decode(
                token,
                public_key_bytes,
                algorithms=['EdDSA'],
                options=options,
                audience=expected_audience
            )
            
            return payload
        except jwt.ExpiredSignatureError:
            raise ServiceAuthError("JWT token has expired")
        except jwt.InvalidAudienceError:
            raise ServiceAuthError(f"JWT token audience mismatch: expected {expected_audience}")
        except jwt.InvalidSignatureError:
            raise ServiceAuthError("JWT token signature verification failed")
        except Exception as e:
            raise ServiceAuthError(f"JWT verification failed: {e}") from e


class ServiceAuthManager:
    """
    Service authentication manager.
    
    Manages service identities and provides authentication utilities.
    """
    
    def __init__(self, service_name: str, key_dir: Optional[Path] = None):
        """
        Initialize service authentication manager.
        
        Args:
            service_name: Service identifier
            key_dir: Directory containing service keys (default: from RANSOMEYE_SERVICE_KEY_DIR)
        """
        self.service_name = service_name
        
        # Get key directory from environment or use default
        if key_dir:
            self.key_dir = key_dir
        else:
            key_dir_env = os.getenv('RANSOMEYE_SERVICE_KEY_DIR')
            if key_dir_env:
                self.key_dir = Path(key_dir_env)
            else:
                # Default: /opt/ransomeye/config/keys
                install_root = os.getenv('RANSOMEYE_INSTALL_ROOT', '/opt/ransomeye')
                self.key_dir = Path(install_root) / 'config' / 'keys'
        
        # Load service identity
        private_key_path = self.key_dir / f"{service_name}.key"
        public_key_path = self.key_dir / f"{service_name}.pub"
        
        if private_key_path.exists():
            self.identity = ServiceIdentity.from_key_file(service_name, private_key_path, is_private=True)
        elif public_key_path.exists():
            self.identity = ServiceIdentity.from_key_file(service_name, public_key_path, is_private=False)
        else:
            raise ServiceAuthError(
                f"Service key not found for {service_name}. "
                f"Expected: {private_key_path} or {public_key_path}"
            )
    
    def get_auth_token(self, target_service: str, expires_in: int = 300) -> str:
        """
        Get authentication token for target service.
        
        Args:
            target_service: Target service name
            expires_in: Token expiration in seconds
            
        Returns:
            JWT token string
        """
        return self.identity.sign_jwt(target_service, expires_in=expires_in)
    
    def verify_token(self, token: str, source_service: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify authentication token from source service.
        
        Args:
            token: JWT token string
            source_service: Expected source service name (for audience verification)
            
        Returns:
            Decoded JWT payload
        """
        expected_audience = self.service_name
        return self.identity.verify_jwt(token, expected_audience=expected_audience)
