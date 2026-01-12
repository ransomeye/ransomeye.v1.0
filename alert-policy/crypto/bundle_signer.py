#!/usr/bin/env python3
"""
RansomEye Alert Policy - Bundle Signer
AUTHORITATIVE: Cryptographic signing of policy bundles (ed25519)
"""

import json
import base64
from typing import Dict, Any
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


class SigningError(Exception):
    """Base exception for signing errors."""
    pass


class BundleSigner:
    """
    Cryptographic signing of policy bundles.
    
    Properties:
    - Deterministic: Same bundle always produces same signature
    - Verifiable: Signatures can be verified with public key
    - Immutable: Signed bundles cannot be modified
    """
    
    def __init__(self, private_key: Ed25519PrivateKey, key_id: str):
        """
        Initialize bundle signer.
        
        Args:
            private_key: Ed25519 private key
            key_id: Key identifier
        """
        self.private_key = private_key
        self.key_id = key_id
    
    def sign_bundle(self, bundle: Dict[str, Any]) -> str:
        """
        Sign policy bundle.
        
        Process:
        1. Create bundle copy without signature fields
        2. Serialize to canonical JSON
        3. Sign with ed25519 private key
        4. Return base64-encoded signature
        
        Args:
            bundle: Policy bundle dictionary (without signature)
        
        Returns:
            Base64-encoded signature
        """
        # Create bundle copy without signature fields
        bundle_for_signing = {
            k: v for k, v in bundle.items()
            if k not in ['bundle_signature', 'bundle_key_id']
        }
        
        # Serialize to canonical JSON (deterministic)
        canonical_json = json.dumps(bundle_for_signing, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        message_bytes = canonical_json.encode('utf-8')
        
        # Sign with ed25519 private key
        try:
            signature_bytes = self.private_key.sign(message_bytes)
            
            # Encode signature as base64
            signature_b64 = base64.b64encode(signature_bytes).decode('ascii')
            return signature_b64
        except Exception as e:
            raise SigningError(f"Failed to sign bundle: {e}") from e
