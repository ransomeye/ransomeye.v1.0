#!/usr/bin/env python3
"""
RansomEye Incident Response - Playbook Signer
AUTHORITATIVE: Cryptographic signing of playbooks (ed25519)
"""

import json
import base64
from typing import Dict, Any
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


class SigningError(Exception):
    """Base exception for signing errors."""
    pass


class PlaybookSigner:
    """
    Cryptographic signing of playbooks.
    
    Properties:
    - Deterministic: Same playbook always produces same signature
    - Verifiable: Signatures can be verified with public key
    - Immutable: Signed playbooks cannot be modified
    """
    
    def __init__(self, private_key: Ed25519PrivateKey, key_id: str):
        """
        Initialize playbook signer.
        
        Args:
            private_key: Ed25519 private key
            key_id: Key identifier
        """
        self.private_key = private_key
        self.key_id = key_id
    
    def sign_playbook(self, playbook: Dict[str, Any]) -> str:
        """
        Sign playbook.
        
        Process:
        1. Create playbook copy without signature fields
        2. Serialize to canonical JSON
        3. Sign with ed25519 private key
        4. Return base64-encoded signature
        
        Args:
            playbook: Playbook dictionary (without signature)
        
        Returns:
            Base64-encoded signature
        """
        # Create playbook copy without signature fields
        playbook_for_signing = {
            k: v for k, v in playbook.items()
            if k not in ['playbook_signature', 'playbook_key_id']
        }
        
        # Serialize to canonical JSON (deterministic)
        canonical_json = json.dumps(playbook_for_signing, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        message_bytes = canonical_json.encode('utf-8')
        
        # Sign with ed25519 private key
        try:
            signature_bytes = self.private_key.sign(message_bytes)
            
            # Encode signature as base64
            signature_b64 = base64.b64encode(signature_bytes).decode('ascii')
            return signature_b64
        except Exception as e:
            raise SigningError(f"Failed to sign playbook: {e}") from e
