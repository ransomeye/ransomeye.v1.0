#!/usr/bin/env python3
"""
RansomEye System Explanation Engine - Bundle Signer
AUTHORITATIVE: Cryptographic signing of explanation bundles
"""

import json
import base64
from pathlib import Path
from typing import Dict, Any
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend


class SigningError(Exception):
    """Base exception for signing errors."""
    pass


class Signer:
    """
    Cryptographic signing of explanation bundles.
    
    Properties:
    - Deterministic: Same bundle always produces same signature
    - Verifiable: Signatures can be verified with public key
    - Immutable: Signed bundles cannot be modified
    """
    
    def __init__(self, private_key_path: Path, key_id: str):
        """
        Initialize signer.
        
        Args:
            private_key_path: Path to private key file (PEM format)
            key_id: Identifier for this keypair
        """
        self.key_id = key_id
        self.private_key = self._load_private_key(private_key_path)
    
    def _load_private_key(self, key_path: Path) -> rsa.RSAPrivateKey:
        """
        Load private key from file.
        
        Args:
            key_path: Path to private key file
        
        Returns:
            RSA private key
        
        Raises:
            SigningError: If key loading fails
        """
        if not key_path.exists():
            raise SigningError(f"Private key not found: {key_path}")
        
        try:
            key_data = key_path.read_bytes()
            private_key = serialization.load_pem_private_key(
                key_data,
                password=None,
                backend=default_backend()
            )
            return private_key
        except Exception as e:
            raise SigningError(f"Failed to load private key: {e}") from e
    
    def sign_bundle(self, bundle: Dict[str, Any]) -> str:
        """
        Sign explanation bundle.
        
        Process:
        1. Create bundle copy without signature
        2. Serialize to canonical JSON
        3. Sign with private key
        4. Return base64-encoded signature
        
        Args:
            bundle: Explanation bundle dictionary
        
        Returns:
            Base64-encoded signature
        """
        # Create bundle copy without signature for signing
        bundle_for_signing = {k: v for k, v in bundle.items() if k != 'signature' and k != 'public_key_id'}
        
        # Serialize to canonical JSON (deterministic)
        canonical_json = json.dumps(bundle_for_signing, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        message_bytes = canonical_json.encode('utf-8')
        
        # Sign with private key
        try:
            signature_bytes = self.private_key.sign(
                message_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            # Encode signature as base64
            signature_b64 = base64.b64encode(signature_bytes).decode('ascii')
            return signature_b64
        except Exception as e:
            raise SigningError(f"Failed to sign bundle: {e}") from e
