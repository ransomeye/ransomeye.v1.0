#!/usr/bin/env python3
"""
RansomEye v1.0 Policy Engine - Command Signer Module
AUTHORITATIVE: Cryptographic signing of policy commands using ed25519
Python 3.10+ only
PHASE 4: ed25519 signing (replaces HMAC-SHA256)
"""

from typing import Dict, Any, Optional
import os
import sys
import json
import base64
from datetime import datetime, timezone
import uuid
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.backends import default_backend

from key_manager import PolicyEngineKeyManager


# PHASE 4: ed25519 signing (replaces HMAC-SHA256)
# Signing keypair loaded once at startup (never reloaded, never logged)
_SIGNER: Optional['PolicyEngineSigner'] = None


class PolicyEngineSigner:
    """
    PHASE 4: Command signer for Policy Engine using ed25519.
    
    Replaces HMAC-SHA256 with ed25519 for consistency with TRE and agents.
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


def get_signer() -> PolicyEngineSigner:
    """
    PHASE 4: Get command signer (loaded once at startup, never reloaded).
    
    Security: Keypair is read once at startup, never logged.
    Terminates Core immediately if keypair is missing or invalid.
    
    Returns:
        PolicyEngineSigner instance (never logged)
    """
    global _SIGNER
    
    # Return cached signer if already loaded (never reload)
    if _SIGNER is not None:
        return _SIGNER
    
    # PHASE 4: Load ed25519 keypair from key directory
    key_dir_env = os.getenv('RANSOMEYE_POLICY_ENGINE_KEY_DIR')
    if not key_dir_env:
        error_msg = "SECURITY VIOLATION: RANSOMEYE_POLICY_ENGINE_KEY_DIR is required (no default allowed)"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        sys.exit(1)  # CONFIG_ERROR
    
    key_dir = Path(key_dir_env)
    key_manager = PolicyEngineKeyManager(key_dir)
    
    try:
        private_key, public_key, key_id = key_manager.get_or_create_keypair()
        _SIGNER = PolicyEngineSigner(private_key, key_id)
        return _SIGNER
    except Exception as e:
        error_msg = f"SECURITY VIOLATION: Failed to load Policy Engine signing keypair: {e}"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        sys.exit(1)  # CONFIG_ERROR


def create_command_payload(command_type: str, target_machine_id: str, 
                          incident_id: str, policy_id: str, policy_version: str,
                          issuing_authority: str) -> Dict[str, Any]:
    """
    PHASE 4: Create command payload structure with policy authority binding.
    
    Command payload contains:
    - command_type (e.g., 'ISOLATE_HOST')
    - target_machine_id (machine to isolate)
    - incident_id (incident that triggered this command)
    - policy_id (policy that authorized this command)
    - policy_version (version of policy)
    - issuing_authority (authority that issued this command)
    - issued_at (RFC3339 UTC timestamp)
    
    Deterministic: Command payload is deterministic (no random fields except command_id)
    
    Args:
        command_type: Type of command (e.g., 'ISOLATE_HOST')
        target_machine_id: Machine ID to target
        incident_id: Incident ID that triggered this command
        policy_id: Policy ID that authorized this command
        policy_version: Version of policy
        issuing_authority: Authority that issued this command (e.g., 'policy-engine')
        
    Returns:
        Command payload dictionary
    """
    # PHASE 4: Generate command ID (UUID v4)
    command_id = str(uuid.uuid4())
    
    # PHASE 4: issued_at is RFC3339 UTC timestamp
    issued_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    # PHASE 4: Command payload structure with policy authority binding
    command_payload = {
        'command_id': command_id,
        'command_type': command_type,
        'target_machine_id': target_machine_id,
        'incident_id': incident_id,
        'policy_id': policy_id,  # PHASE 4: Policy authority binding
        'policy_version': policy_version,  # PHASE 4: Policy version
        'issuing_authority': issuing_authority,  # PHASE 4: Issuing authority
        'issued_at': issued_at
    }
    
    return command_payload


def sign_command(command_payload: Dict[str, Any]) -> str:
    """
    PHASE 4: Cryptographically sign command payload with ed25519.
    
    Commands are cryptographically signed with ed25519 (replaces HMAC-SHA256).
    All commands are signed and auditable.
    Deterministic: Same command payload + same key → same signature
    
    Args:
        command_payload: Command payload dictionary
        
    Returns:
        Base64-encoded ed25519 signature
    """
    # PHASE 4: Cryptographically sign command with ed25519
    signer = get_signer()
    signature = signer.sign_payload(command_payload)
    
    return signature


def create_signed_command(command_type: str, target_machine_id: str, 
                         incident_id: str) -> Dict[str, Any]:
    """
    Create signed command (command payload + signature).
    
    Phase 7 requirement: Generate command payload and sign it
    Phase 7 requirement: Store signed command (not execute it)
    
    Args:
        command_type: Type of command (e.g., 'ISOLATE_HOST')
        target_machine_id: Machine ID to target
        incident_id: Incident ID that triggered this command
        
    Returns:
        Signed command dictionary (payload + signature)
    """
    # Phase 7 requirement: Create command payload
    command_payload = create_command_payload(command_type, target_machine_id, incident_id)
    
    # Phase 7 requirement: Sign command
    signature = sign_command(command_payload)
    
    # Phase 7 requirement: Create signed command structure
    signed_command = {
        'payload': command_payload,
        'signature': signature,
        'signing_algorithm': 'HMAC-SHA256',
        'signed_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }
    
    return signed_command
