#!/usr/bin/env python3
"""
RansomEye Supply-Chain Signing & Verification Framework - Artifact Verifier
AUTHORITATIVE: Offline verification of signed artifacts
"""

import base64
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


class ArtifactVerificationError(Exception):
    """Base exception for artifact verification errors."""
    pass


class ArtifactVerifier:
    """
    Offline verification of signed artifacts.
    
    Properties:
    - Deterministic: Same input always produces same verification result
    - Offline: No network or external dependencies
    - External key support: Supports customer trust root injection
    """
    
    def __init__(self, public_key: Optional[ed25519.Ed25519PublicKey] = None, public_key_path: Optional[Path] = None):
        """
        Initialize artifact verifier.
        
        Args:
            public_key: ed25519 public key (optional, if provided directly)
            public_key_path: Path to public key file (optional, if key not provided directly)
        
        Raises:
            ArtifactVerificationError: If neither key nor path provided, or key loading fails
        """
        if public_key:
            self.public_key = public_key
        elif public_key_path:
            self.public_key = self._load_public_key(public_key_path)
        else:
            raise ArtifactVerificationError("Either public_key or public_key_path must be provided")
    
    def _load_public_key(self, public_key_path: Path) -> ed25519.Ed25519PublicKey:
        """
        Load ed25519 public key from file.
        
        Args:
            public_key_path: Path to public key file
        
        Returns:
            Public key
        
        Raises:
            ArtifactVerificationError: If key loading fails
        """
        try:
            public_key_bytes = public_key_path.read_bytes()
            return serialization.load_pem_public_key(
                public_key_bytes,
                backend=default_backend()
            )
        except Exception as e:
            raise ArtifactVerificationError(f"Failed to load public key: {e}") from e
    
    def verify_manifest_signature(self, manifest: Dict[str, Any]) -> bool:
        """
        Verify manifest signature.
        
        Process:
        1. Build canonical manifest (sorted JSON)
        2. Hash manifest
        3. Verify signature against manifest hash
        
        Args:
            manifest: Artifact manifest dictionary
        
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Extract signature from manifest
            signature_b64 = manifest.get('signature', '')
            if not signature_b64:
                return False
            
            # Build canonical manifest (sorted JSON, no whitespace)
            # Create manifest copy without signature for hashing
            manifest_copy = manifest.copy()
            manifest_copy.pop('signature', None)
            
            canonical_json = json.dumps(
                manifest_copy,
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=False
            )
            
            # Hash manifest
            manifest_hash = hashlib.sha256(canonical_json.encode('utf-8')).digest()
            
            # Decode signature
            signature_bytes = base64.b64decode(signature_b64.encode('ascii'))
            
            # Verify signature
            self.public_key.verify(signature_bytes, manifest_hash)
            return True
            
        except Exception as e:
            return False
    
    def verify_artifact_hash(self, artifact_path: Path, expected_sha256: str) -> bool:
        """
        Verify artifact SHA256 hash.
        
        Args:
            artifact_path: Path to artifact file
            expected_sha256: Expected SHA256 hash
        
        Returns:
            True if hash matches, False otherwise
        """
        try:
            # Compute SHA256 hash of artifact
            hash_obj = hashlib.sha256()
            with open(artifact_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_obj.update(chunk)
            
            computed_hash = hash_obj.hexdigest()
            return computed_hash == expected_sha256.lower()
            
        except Exception as e:
            return False
