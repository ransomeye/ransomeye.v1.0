#!/usr/bin/env python3
"""
RansomEye v1.0 Common Security - Secrets Handling
AUTHORITATIVE: Secure secrets validation and management
"""

import os
import sys
import re
from typing import Optional


def validate_secret_present(env_var: str, min_length: int = 8) -> str:
    """
    Validate that a required secret environment variable is present and meets strength requirements.
    
    Security: Terminates Core immediately if secret is missing or weak.
    
    Args:
        env_var: Environment variable name
        min_length: Minimum length requirement (default: 8)
        
    Returns:
        Secret value (never logged)
        
    Raises:
        SystemExit: Terminates Core immediately if secret missing or weak
    """
    value = os.getenv(env_var)
    
    if not value:
        error_msg = f"SECURITY VIOLATION: Required secret {env_var} is missing"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        sys.exit(1)  # CONFIG_ERROR
    
    if len(value) < min_length:
        error_msg = f"SECURITY VIOLATION: Secret {env_var} is too short (minimum {min_length} characters)"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        sys.exit(1)  # CONFIG_ERROR
    
    # Check for weak secrets (all same character, sequential, etc.)
    if len(set(value)) < 3:
        error_msg = f"SECURITY VIOLATION: Secret {env_var} is too weak (insufficient entropy)"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        sys.exit(1)  # CONFIG_ERROR
    
    return value


def validate_signing_key(env_var: str = "RANSOMEYE_COMMAND_SIGNING_KEY", 
                        min_length: int = 32, 
                        fail_on_default: bool = True) -> bytes:
    """
    Validate command signing key from environment.
    
    Security: Terminates Core immediately if key is missing, weak, or is a default value.
    Key is read once at startup and never reloaded.
    
    Args:
        env_var: Environment variable name (default: RANSOMEYE_COMMAND_SIGNING_KEY)
        min_length: Minimum key length in bytes (default: 32)
        fail_on_default: If True, fail if key is a known default value (default: True)
        
    Returns:
        Signing key as bytes (never logged)
        
    Raises:
        SystemExit: Terminates Core immediately if key is missing, weak, or default
    """
    value = os.getenv(env_var)
    
    if not value:
        if fail_on_default:
            error_msg = f"SECURITY VIOLATION: Signing key {env_var} is required (no default allowed)"
            print(f"FATAL: {error_msg}", file=sys.stderr)
            sys.exit(1)  # CONFIG_ERROR
        else:
            # Phase 7 minimal: Allow default for development (NOT SECURE FOR PRODUCTION)
            default_key = "phase7_minimal_default_key_change_in_production"
            return default_key.encode('utf-8')
    
    # Check for known default/insecure keys
    insecure_keys = [
        "phase7_minimal_default_key_change_in_production",
        "test_signing_key_minimum_32_characters_long_for_validation_long_enough",
        "test_signing_key",
        "default",
        "test",
        "changeme",
        "password",
        "secret",
    ]
    # Check if value contains any insecure pattern
    for insecure_key in insecure_keys:
        if insecure_key.lower() in value.lower():
            if fail_on_default:
                error_msg = f"SECURITY VIOLATION: Signing key {env_var} contains insecure default pattern '{insecure_key}' (not allowed)"
                print(f"FATAL: {error_msg}", file=sys.stderr)
                sys.exit(1)  # CONFIG_ERROR
    
    # Validate key strength
    if len(value) < min_length:
        error_msg = f"SECURITY VIOLATION: Signing key {env_var} is too short (minimum {min_length} characters)"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        sys.exit(1)  # CONFIG_ERROR
    
    # Check for weak keys (all same character, sequential, etc.)
    if len(set(value)) < min(len(value) * 0.3, 8):
        error_msg = f"SECURITY VIOLATION: Signing key {env_var} has insufficient entropy"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        sys.exit(1)  # CONFIG_ERROR
    
    # Validate key format (should be base64-like or hex-like, not just plain text)
    # Simple check: key should have some non-alphabetic characters for entropy
    if value.isalpha():
        error_msg = f"SECURITY VIOLATION: Signing key {env_var} format is too weak (alphabetic only)"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        sys.exit(1)  # CONFIG_ERROR
    
    return value.encode('utf-8')


def get_secret_safely(env_var: str, default: Optional[str] = None, 
                     min_length: Optional[int] = None) -> Optional[str]:
    """
    Get secret from environment variable safely (no logging).
    
    Security: Never logs the secret value.
    
    Args:
        env_var: Environment variable name
        default: Default value if not set (None means required)
        min_length: Minimum length if set
        
    Returns:
        Secret value or default (never logged)
        
    Raises:
        SystemExit: Terminates Core immediately if required secret is missing
    """
    value = os.getenv(env_var, default)
    
    if value is None:
        error_msg = f"SECURITY VIOLATION: Required secret {env_var} is missing"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        sys.exit(1)  # CONFIG_ERROR
    
    if min_length and len(value) < min_length:
        error_msg = f"SECURITY VIOLATION: Secret {env_var} is too short (minimum {min_length} characters)"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        sys.exit(1)  # CONFIG_ERROR
    
    return value
