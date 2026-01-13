#!/usr/bin/env python3
"""
RansomEye v1.0 Threat Response Engine - Command Signer
AUTHORITATIVE: Cryptographic signing of TRE commands using ed25519
Python 3.10+ only
"""

import json
import base64
from typing import Dict, Any
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


class TRESigner:
    """
    Command signer for TRE.
    
    CRITICAL: Uses ed25519 for command signing (separate from Policy Engine's HMAC).
    All commands are signed before dispatch to agents.
    """
    
    def __init__(self, private_key: Ed25519PrivateKey, key_id: str):
        """
        Initialize signer.
        
        Args:
            private_key: ed25519 private key for signing
            key_id: Key identifier (SHA256 hash of public key)
        """
        self.private_key = private_key
        self.key_id = key_id
    
    def sign_payload(self, payload: Dict[str, Any]) -> str:
        """
        Sign command payload with ed25519.
        
        Args:
            payload: Command payload dictionary
            
        Returns:
            Base64-encoded signature
        """
        # Serialize payload to canonical JSON
        payload_json = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        
        # Sign payload
        signature_bytes = self.private_key.sign(
            payload_json.encode('utf-8'),
            backend=default_backend()
        )
        
        # Encode signature as base64
        signature = base64.b64encode(signature_bytes).decode('ascii')
        
        return signature
    
    def sign_command(self, command_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sign command and return signed command structure.
        
        Args:
            command_payload: Command payload dictionary
            
        Returns:
            Signed command dictionary with signature and key_id
        """
        signature = self.sign_payload(command_payload)
        
        signed_command = {
            'payload': command_payload,
            'signature': signature,
            'signing_key_id': self.key_id,
            'signing_algorithm': 'ed25519',
            'signed_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }
        
        return signed_command
