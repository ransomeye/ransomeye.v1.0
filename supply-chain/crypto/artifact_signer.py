#!/usr/bin/env python3
"""
RansomEye Supply-Chain Signing & Verification Framework - Artifact Signer
AUTHORITATIVE: Cryptographic signing of artifacts using ed25519
"""

import base64
import hashlib
import json
from pathlib import Path
from typing import Dict, Any
from cryptography.hazmat.primitives.asymmetric import ed25519


class ArtifactSigningError(Exception):
    """Base exception for artifact signing errors."""
    pass


class ArtifactSigner:
    """
    Cryptographic signing of artifacts using ed25519.
    
    Properties:
    - Deterministic: Same input always produces same signature
    - Reproducible: All steps are reproducible
    - Offline: No network or external dependencies
    """
    
    def __init__(self, private_key: ed25519.Ed25519PrivateKey, key_id: str):
        """
        Initialize artifact signer.
        
        Args:
            private_key: ed25519 private key
            key_id: Signing key identifier
        """
        self.private_key = private_key
        self.key_id = key_id
    
    def sign_manifest(self, manifest: Dict[str, Any]) -> str:
        """
        Sign artifact manifest.
        
        GA-BLOCKING: Signs manifest WITHOUT signature field (for consistency with verification).
        
        Process:
        1. Remove signature field from manifest (if present)
        2. Build canonical manifest (sorted JSON)
        3. Hash manifest
        4. Sign manifest hash
        
        Args:
            manifest: Artifact manifest dictionary (signature field will be removed before signing)
        
        Returns:
            Base64-encoded signature
        """
        try:
            # GA-BLOCKING: Create manifest copy without signature field (for signing)
            manifest_copy = manifest.copy()
            manifest_copy.pop('signature', None)
            
            # Build canonical manifest (sorted JSON, no whitespace)
            canonical_json = json.dumps(
                manifest_copy,
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=False
            )
            
            # Hash manifest
            manifest_hash = hashlib.sha256(canonical_json.encode('utf-8')).digest()
            
            # Sign manifest hash
            signature = self.private_key.sign(manifest_hash)
            
            # Return Base64-encoded signature
            return base64.b64encode(signature).decode('ascii')
            
        except Exception as e:
            raise ArtifactSigningError(f"Failed to sign manifest: {e}") from e
