#!/usr/bin/env python3
"""
RansomEye LLM Summarizer - Redaction Policy
AUTHORITATIVE: Redaction policy enforcement (STRICT | BALANCED | FORENSIC)
"""

from typing import Dict, Any
from enum import Enum


class RedactionPolicyError(Exception):
    """Base exception for redaction policy errors."""
    pass


class RedactionPolicyMode(Enum):
    """Redaction policy modes."""
    STRICT = "STRICT"
    BALANCED = "BALANCED"
    FORENSIC = "FORENSIC"


class RedactionPolicy:
    """
    Redaction policy configuration.
    
    Properties:
    - Immutable: Policy cannot be modified after creation
    - Deterministic: Same policy mode = same behavior
    """
    
    def __init__(self, mode: str):
        """
        Initialize redaction policy.
        
        Args:
            mode: Policy mode (STRICT | BALANCED | FORENSIC)
        
        Raises:
            RedactionPolicyError: If mode is invalid
        """
        try:
            self.mode = RedactionPolicyMode(mode)
        except ValueError:
            raise RedactionPolicyError(f"Invalid redaction policy mode: {mode}. Must be STRICT, BALANCED, or FORENSIC")
    
    def should_hash_ip(self) -> bool:
        """Check if IP addresses should be hashed."""
        return self.mode == RedactionPolicyMode.STRICT
    
    def should_partial_ip(self) -> bool:
        """Check if IP addresses should be partially retained."""
        return self.mode == RedactionPolicyMode.BALANCED
    
    def should_hash_hostname(self) -> bool:
        """Check if hostnames should be hashed."""
        return self.mode == RedactionPolicyMode.STRICT
    
    def should_truncate_hostname(self) -> bool:
        """Check if hostnames should be truncated."""
        return self.mode == RedactionPolicyMode.BALANCED
    
    def should_hash_username(self) -> bool:
        """Check if usernames should be hashed."""
        return self.mode in [RedactionPolicyMode.STRICT, RedactionPolicyMode.BALANCED]
    
    def should_redact_email(self) -> bool:
        """Check if emails should be fully redacted."""
        return self.mode == RedactionPolicyMode.STRICT
    
    def should_email_domain_only(self) -> bool:
        """Check if only email domain should be retained."""
        return self.mode == RedactionPolicyMode.BALANCED
    
    def should_redact_domain(self) -> bool:
        """Check if domains should be fully redacted."""
        return self.mode == RedactionPolicyMode.STRICT
    
    def should_second_level_domain(self) -> bool:
        """Check if only second-level domain should be retained."""
        return self.mode == RedactionPolicyMode.BALANCED
    
    def should_redact_secrets(self) -> bool:
        """Check if secrets should be redacted (all modes)."""
        return True  # Always redact secrets
    
    def get_mode(self) -> str:
        """Get policy mode string."""
        return self.mode.value
