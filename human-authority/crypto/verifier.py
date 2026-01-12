#!/usr/bin/env python3
"""
RansomEye Human Authority Framework - Action Verifier
AUTHORITATIVE: Cryptographic verification of human authority actions (ed25519)
"""

import json
import base64
from typing import Dict, Any
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature


class VerificationError(Exception):
    """Base exception for verification errors."""
    pass


class Verifier:
    """
    Cryptographic verification of human authority actions.
    
    Properties:
    - Deterministic: Same action always produces same verification result
    - Complete: Verifies signature and action integrity
    """
    
    def __init__(self, public_key: Ed25519PublicKey):
        """
        Initialize verifier.
        
        Args:
            public_key: Ed25519 public key
        """
        self.public_key = public_key
    
    def verify_action(self, action: Dict[str, Any]) -> bool:
        """
        Verify authority action signature.
        
        Process:
        1. Extract signature from action
        2. Create action copy without signature fields
        3. Serialize to canonical JSON
        4. Verify signature with ed25519 public key
        
        Args:
            action: Authority action dictionary
        
        Returns:
            True if signature is valid
        
        Raises:
            VerificationError: If verification fails
        """
        # Extract signature
        signature_b64 = action.get('human_signature', '')
        if not signature_b64:
            raise VerificationError("Action missing signature")
        
        try:
            signature_bytes = base64.b64decode(signature_b64)
        except Exception as e:
            raise VerificationError(f"Invalid signature encoding: {e}") from e
        
        # Create action copy without signature fields
        action_for_verification = {
            k: v for k, v in action.items()
            if k not in ['human_signature', 'human_key_id', 'ledger_entry_id']
        }
        
        # Serialize to canonical JSON (deterministic)
        canonical_json = json.dumps(action_for_verification, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        message_bytes = canonical_json.encode('utf-8')
        
        # Verify signature
        try:
            self.public_key.verify(signature_bytes, message_bytes)
            return True
        except InvalidSignature as e:
            raise VerificationError(f"Signature verification failed: {e}") from e
    
    def verify_role_assertion(self, assertion: Dict[str, Any]) -> bool:
        """
        Verify role assertion signature.
        
        Process:
        1. Extract signature from assertion
        2. Create assertion copy without signature fields
        3. Serialize to canonical JSON
        4. Verify signature with ed25519 public key
        
        Args:
            assertion: Role assertion dictionary
        
        Returns:
            True if signature is valid
        
        Raises:
            VerificationError: If verification fails
        """
        # Extract signature
        signature_b64 = assertion.get('assertion_signature', '')
        if not signature_b64:
            raise VerificationError("Assertion missing signature")
        
        try:
            signature_bytes = base64.b64decode(signature_b64)
        except Exception as e:
            raise VerificationError(f"Invalid signature encoding: {e}") from e
        
        # Create assertion copy without signature fields
        assertion_for_verification = {
            k: v for k, v in assertion.items()
            if k not in ['assertion_signature', 'assertion_key_id']
        }
        
        # Serialize to canonical JSON (deterministic)
        canonical_json = json.dumps(assertion_for_verification, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        message_bytes = canonical_json.encode('utf-8')
        
        # Verify signature
        try:
            self.public_key.verify(signature_bytes, message_bytes)
            return True
        except InvalidSignature as e:
            raise VerificationError(f"Signature verification failed: {e}") from e
