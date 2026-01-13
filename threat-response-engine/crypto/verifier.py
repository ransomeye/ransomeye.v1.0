#!/usr/bin/env python3
"""
RansomEye v1.0 Threat Response Engine - Command Verifier
AUTHORITATIVE: Cryptographic verification of TRE commands using ed25519
Python 3.10+ only
"""

import json
import base64
from typing import Dict, Any
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend


class TREVerifier:
    """
    Command verifier for TRE.
    
    CRITICAL: Agents must verify all commands before execution.
    Verification is deterministic and fail-fast.
    """
    
    def __init__(self, public_key: Ed25519PublicKey):
        """
        Initialize verifier.
        
        Args:
            public_key: ed25519 public key for verification
        """
        self.public_key = public_key
    
    def verify_payload(self, payload: Dict[str, Any], signature: str) -> bool:
        """
        Verify command payload signature.
        
        Args:
            payload: Command payload dictionary
            signature: Base64-encoded signature
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Serialize payload to canonical JSON
            payload_json = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            
            # Decode signature
            signature_bytes = base64.b64decode(signature.encode('ascii'))
            
            # Verify signature
            self.public_key.verify(
                signature_bytes,
                payload_json.encode('utf-8'),
                backend=default_backend()
            )
            
            return True
        except (InvalidSignature, ValueError, base64.binascii.Error):
            return False
    
    def verify_command(self, signed_command: Dict[str, Any]) -> bool:
        """
        Verify signed command.
        
        Args:
            signed_command: Signed command dictionary
            
        Returns:
            True if signature is valid, False otherwise
        """
        if 'payload' not in signed_command or 'signature' not in signed_command:
            return False
        
        return self.verify_payload(signed_command['payload'], signed_command['signature'])
    
    @staticmethod
    def load_public_key_from_pem(pem_data: bytes) -> Ed25519PublicKey:
        """
        Load public key from PEM format.
        
        Args:
            pem_data: PEM-encoded public key bytes
            
        Returns:
            Ed25519PublicKey instance
        """
        public_key = serialization.load_pem_public_key(pem_data, backend=default_backend())
        if not isinstance(public_key, Ed25519PublicKey):
            raise ValueError("Public key is not ed25519")
        return public_key
