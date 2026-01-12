#!/usr/bin/env python3
"""
RansomEye Alert Policy - Bundle Verifier
AUTHORITATIVE: Cryptographic verification of policy bundles (ed25519)
"""

import json
import base64
from typing import Dict, Any
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature


class VerificationError(Exception):
    """Base exception for verification errors."""
    pass


class BundleVerifier:
    """
    Cryptographic verification of policy bundles.
    
    Properties:
    - Deterministic: Same bundle always produces same verification result
    - Complete: Verifies signature and bundle integrity
    """
    
    def __init__(self, public_key: Ed25519PublicKey):
        """
        Initialize bundle verifier.
        
        Args:
            public_key: Ed25519 public key
        """
        self.public_key = public_key
    
    def verify_bundle(self, bundle: Dict[str, Any]) -> bool:
        """
        Verify policy bundle signature.
        
        Process:
        1. Extract signature from bundle
        2. Create bundle copy without signature fields
        3. Serialize to canonical JSON
        4. Verify signature with ed25519 public key
        
        Args:
            bundle: Policy bundle dictionary
        
        Returns:
            True if signature is valid
        
        Raises:
            VerificationError: If verification fails
        """
        # Extract signature
        signature_b64 = bundle.get('bundle_signature', '')
        if not signature_b64:
            raise VerificationError("Bundle missing signature")
        
        try:
            signature_bytes = base64.b64decode(signature_b64)
        except Exception as e:
            raise VerificationError(f"Invalid signature encoding: {e}") from e
        
        # Create bundle copy without signature fields
        bundle_for_verification = {
            k: v for k, v in bundle.items()
            if k not in ['bundle_signature', 'bundle_key_id']
        }
        
        # Serialize to canonical JSON (deterministic)
        canonical_json = json.dumps(bundle_for_verification, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        message_bytes = canonical_json.encode('utf-8')
        
        # Verify signature
        try:
            self.public_key.verify(signature_bytes, message_bytes)
            return True
        except InvalidSignature as e:
            raise VerificationError(f"Signature verification failed: {e}") from e
