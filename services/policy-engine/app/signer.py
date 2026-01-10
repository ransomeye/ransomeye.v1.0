#!/usr/bin/env python3
"""
RansomEye v1.0 Policy Engine - Command Signer Module
AUTHORITATIVE: Cryptographic signing of policy commands
Python 3.10+ only - aligns with Phase 7 requirements
"""

from typing import Dict, Any, Optional
import hashlib
import hmac
import os
import sys
import json
from datetime import datetime, timezone
import uuid


# Phase 7 requirement: Commands are cryptographically signed
# Phase 7 requirement: Commands are NOT executed (simulation-first)
# Phase 7 requirement: All commands are signed and auditable


# Signing key loaded once at startup (never reloaded, never logged)
_SIGNING_KEY: Optional[bytes] = None


def get_signing_key() -> bytes:
    """
    Get command signing key (loaded once at startup, never reloaded).
    
    Security: Key is read once at startup, validated for strength, never logged.
    Terminates Core immediately if key is missing, weak, or is a default value.
    
    Returns:
        Signing key as bytes (never logged)
    """
    global _SIGNING_KEY
    
    # Return cached key if already loaded (never reload)
    if _SIGNING_KEY is not None:
        return _SIGNING_KEY
    
    # Security: Validate signing key at startup (fail-fast on weak/invalid keys)
    try:
        from common.security.secrets import validate_signing_key
        _SIGNING_KEY = validate_signing_key(
            env_var="RANSOMEYE_COMMAND_SIGNING_KEY",
            min_length=32,
            fail_on_default=True  # Production: fail on default keys
        )
        return _SIGNING_KEY
    except ImportError:
        # Fallback if security utilities not available
        signing_key_str = os.getenv("RANSOMEYE_COMMAND_SIGNING_KEY", "")
        if not signing_key_str:
            # Fail-fast: no default allowed
            error_msg = "SECURITY VIOLATION: Signing key RANSOMEYE_COMMAND_SIGNING_KEY is required (no default allowed)"
            print(f"FATAL: {error_msg}", file=sys.stderr)
            sys.exit(1)  # CONFIG_ERROR
        
        # Basic validation
        if len(signing_key_str) < 32:
            error_msg = f"SECURITY VIOLATION: Signing key is too short (minimum 32 characters)"
            print(f"FATAL: {error_msg}", file=sys.stderr)
            sys.exit(1)  # CONFIG_ERROR
        
        _SIGNING_KEY = signing_key_str.encode('utf-8')
        return _SIGNING_KEY


def create_command_payload(command_type: str, target_machine_id: str, 
                          incident_id: str) -> Dict[str, Any]:
    """
    Create command payload structure.
    
    Phase 7 requirement: Command payload contains:
    - command_type (e.g., 'ISOLATE_HOST')
    - target_machine_id (machine to isolate)
    - incident_id (incident that triggered this command)
    - issued_at (RFC3339 UTC timestamp)
    
    Deterministic: Command payload is deterministic (no random fields except command_id)
    
    Args:
        command_type: Type of command (e.g., 'ISOLATE_HOST')
        target_machine_id: Machine ID to target
        incident_id: Incident ID that triggered this command
        
    Returns:
        Command payload dictionary
    """
    # Phase 7 requirement: Generate command ID (UUID v4)
    command_id = str(uuid.uuid4())
    
    # Phase 7 requirement: issued_at is RFC3339 UTC timestamp
    issued_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    # Phase 7 requirement: Command payload structure
    command_payload = {
        'command_id': command_id,
        'command_type': command_type,
        'target_machine_id': target_machine_id,
        'incident_id': incident_id,
        'issued_at': issued_at
    }
    
    return command_payload


def sign_command(command_payload: Dict[str, Any]) -> str:
    """
    Cryptographically sign command payload.
    
    Phase 7 requirement: Commands are cryptographically signed
    Phase 7 requirement: All commands are signed and auditable
    Deterministic: Same command payload + same key → same signature
    
    Args:
        command_payload: Command payload dictionary
        
    Returns:
        HMAC-SHA256 signature (64-character hex string)
    """
    # Phase 7 requirement: Cryptographically sign command
    # Contract compliance: Use HMAC-SHA256 for signing (standard practice)
    
    # Serialize command payload to canonical JSON (for deterministic signing)
    command_json = json.dumps(command_payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    
    # Get signing key
    signing_key = get_signing_key()
    
    # Compute HMAC-SHA256 signature
    signature = hmac.new(signing_key, command_json.encode('utf-8'), hashlib.sha256).hexdigest()
    
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
