#!/usr/bin/env python3
"""
RansomEye Human Authority Framework - Action Signer
AUTHORITATIVE: Cryptographic signing of human authority actions (ed25519)
"""

import json
import base64
from typing import Dict, Any
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


class SigningError(Exception):
    """Base exception for signing errors."""
    pass


class Signer:
    """
    Cryptographic signing of human authority actions.
    
    Properties:
    - Deterministic: Same action always produces same signature
    - Per-human: Each human signs with their own key
    - Non-repudiation: Signatures provide non-repudiation
    """
    
    def __init__(self, private_key: Ed25519PrivateKey, key_id: str):
        """
        Initialize signer.
        
        Args:
            private_key: Ed25519 private key
            key_id: Key identifier
        """
        self.private_key = private_key
        self.key_id = key_id
    
    def sign_action(self, action: Dict[str, Any]) -> str:
        """
        Sign authority action.
        
        Process:
        1. Create action copy without signature fields
        2. Serialize to canonical JSON
        3. Sign with ed25519 private key
        4. Return base64-encoded signature
        
        Args:
            action: Authority action dictionary (without signature)
        
        Returns:
            Base64-encoded signature
        """
        # Create action copy without signature fields
        action_for_signing = {
            k: v for k, v in action.items()
            if k not in ['human_signature', 'human_key_id', 'ledger_entry_id']
        }
        
        # Serialize to canonical JSON (deterministic)
        canonical_json = json.dumps(action_for_signing, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        message_bytes = canonical_json.encode('utf-8')
        
        # Sign with ed25519 private key
        try:
            signature_bytes = self.private_key.sign(message_bytes)
            
            # Encode signature as base64
            signature_b64 = base64.b64encode(signature_bytes).decode('ascii')
            return signature_b64
        except Exception as e:
            raise SigningError(f"Failed to sign action: {e}") from e
    
    def sign_role_assertion(self, assertion: Dict[str, Any]) -> str:
        """
        Sign role assertion.
        
        Process:
        1. Create assertion copy without signature fields
        2. Serialize to canonical JSON
        3. Sign with ed25519 private key
        4. Return base64-encoded signature
        
        Args:
            assertion: Role assertion dictionary (without signature)
        
        Returns:
            Base64-encoded signature
        """
        # Create assertion copy without signature fields
        assertion_for_signing = {
            k: v for k, v in assertion.items()
            if k not in ['assertion_signature', 'assertion_key_id']
        }
        
        # Serialize to canonical JSON (deterministic)
        canonical_json = json.dumps(assertion_for_signing, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        message_bytes = canonical_json.encode('utf-8')
        
        # Sign with ed25519 private key
        try:
            signature_bytes = self.private_key.sign(message_bytes)
            
            # Encode signature as base64
            signature_b64 = base64.b64encode(signature_bytes).decode('ascii')
            return signature_b64
        except Exception as e:
            raise SigningError(f"Failed to sign assertion: {e}") from e
