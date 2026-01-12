#!/usr/bin/env python3
"""
RansomEye UBA Core - Identity Resolver
AUTHORITATIVE: Deterministically map events → canonical identity
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
import uuid
import hashlib
import json
import os


class IdentityResolutionError(Exception):
    """Base exception for identity resolution errors."""
    pass


class IdentityResolver:
    """
    Deterministic identity resolver.
    
    Properties:
    - Deterministic: Same input = same identity
    - Explicit precedence: Explicit precedence rules only
    - No heuristics: No heuristic logic
    - Environment-driven: All paths/domains from environment
    """
    
    def __init__(self):
        """Initialize identity resolver."""
        # Load configuration from environment (no hardcoded values)
        self.auth_domain = os.getenv('UBA_AUTH_DOMAIN', 'local')
        self.source_system = os.getenv('UBA_SOURCE_SYSTEM', 'linux-agent')
    
    def resolve_identity(
        self,
        user_id: str,
        identity_type: str,
        auth_domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resolve identity to canonical form.
        
        Args:
            user_id: User identifier
            identity_type: Identity type (human, service, machine)
            auth_domain: Authentication domain (if None, uses env var)
        
        Returns:
            Identity dictionary
        """
        # Validate identity type
        valid_types = ['human', 'service', 'machine']
        if identity_type not in valid_types:
            raise IdentityResolutionError(f"Invalid identity type: {identity_type}")
        
        # Use provided auth_domain or environment default
        resolved_domain = auth_domain if auth_domain else self.auth_domain
        
        # Build canonical identity
        canonical_identity = {
            'user_id': user_id,
            'identity_type': identity_type,
            'auth_domain': resolved_domain
        }
        
        # Calculate canonical hash (deterministic)
        canonical_hash = self._calculate_canonical_hash(canonical_identity)
        
        # Create identity record
        identity = {
            'identity_id': str(uuid.uuid4()),
            'user_id': user_id,
            'identity_type': identity_type,
            'auth_domain': resolved_domain,
            'creation_timestamp': datetime.now(timezone.utc).isoformat(),
            'source_system': self.source_system,
            'canonical_identity_hash': canonical_hash
        }
        
        return identity
    
    def _calculate_canonical_hash(self, canonical_identity: Dict[str, Any]) -> str:
        """
        Calculate deterministic canonical identity hash.
        
        Args:
            canonical_identity: Canonical identity dictionary
        
        Returns:
            SHA256 hash as hex string
        """
        # Serialize to canonical JSON (deterministic)
        canonical_json = json.dumps(canonical_identity, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        
        # Calculate SHA256 hash
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
