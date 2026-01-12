#!/usr/bin/env python3
"""
RansomEye System Explanation Engine - Bundle Verifier
AUTHORITATIVE: Cryptographic verification of explanation bundles
"""

import json
import base64
from pathlib import Path
from typing import Dict, Any
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend


class VerificationError(Exception):
    """Base exception for verification errors."""
    pass


class Verifier:
    """
    Cryptographic verification of explanation bundles.
    
    Properties:
    - Deterministic: Same bundle always produces same verification result
    - Complete: Verifies signature and bundle integrity
    """
    
    def __init__(self, public_key_path: Path):
        """
        Initialize verifier.
        
        Args:
            public_key_path: Path to public key file (PEM format)
        """
        self.public_key = self._load_public_key(public_key_path)
    
    def _load_public_key(self, key_path: Path) -> rsa.RSAPublicKey:
        """
        Load public key from file.
        
        Args:
            key_path: Path to public key file
        
        Returns:
            RSA public key
        
        Raises:
            VerificationError: If key loading fails
        """
        if not key_path.exists():
            raise VerificationError(f"Public key not found: {key_path}")
        
        try:
            key_data = key_path.read_bytes()
            public_key = serialization.load_pem_public_key(
                key_data,
                backend=default_backend()
            )
            return public_key
        except Exception as e:
            raise VerificationError(f"Failed to load public key: {e}") from e
    
    def verify_bundle(self, bundle: Dict[str, Any]) -> bool:
        """
        Verify explanation bundle signature.
        
        Process:
        1. Extract signature from bundle
        2. Create bundle copy without signature
        3. Serialize to canonical JSON
        4. Verify signature with public key
        
        Args:
            bundle: Explanation bundle dictionary
        
        Returns:
            True if signature is valid
        
        Raises:
            VerificationError: If verification fails
        """
        # Extract signature
        signature_b64 = bundle.get('signature', '')
        if not signature_b64:
            raise VerificationError("Bundle missing signature")
        
        try:
            signature_bytes = base64.b64decode(signature_b64)
        except Exception as e:
            raise VerificationError(f"Invalid signature encoding: {e}") from e
        
        # Create bundle copy without signature for verification
        bundle_for_verification = {k: v for k, v in bundle.items() if k != 'signature' and k != 'public_key_id'}
        
        # Serialize to canonical JSON (deterministic)
        canonical_json = json.dumps(bundle_for_verification, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        message_bytes = canonical_json.encode('utf-8')
        
        # Verify signature
        try:
            self.public_key.verify(
                signature_bytes,
                message_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            raise VerificationError(f"Signature verification failed: {e}") from e
