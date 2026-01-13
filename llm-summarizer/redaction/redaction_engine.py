#!/usr/bin/env python3
"""
RansomEye LLM Summarizer - Redaction Engine
AUTHORITATIVE: Deterministic PII redaction before LLM generation
"""

import json
import hashlib
import uuid
from typing import Dict, Any, List
from datetime import datetime, timezone
from pathlib import Path

from .redaction_policy import RedactionPolicy, RedactionPolicyError
from .pattern_detector import PatternDetector, PatternDetectorError


class RedactionEngineError(Exception):
    """Base exception for redaction engine errors."""
    pass


class RedactionEngine:
    """
    Deterministic PII redaction engine.
    
    Properties:
    - Deterministic: Same input + policy = same output
    - Ordered: Redaction rules applied in fixed order
    - Immutable: Redaction log is immutable
    """
    
    def __init__(self, policy: RedactionPolicy):
        """
        Initialize redaction engine.
        
        Args:
            policy: Redaction policy instance
        """
        self.policy = policy
        self.pattern_detector = PatternDetector()
    
    def redact(self, data: Dict[str, Any], summary_request_id: str, redacted_by: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Redact PII from data structure.
        
        Process:
        1. Deep copy data (no mutation of input)
        2. Apply redaction rules in fixed order
        3. Generate redaction log
        4. Return redacted data and log
        
        Args:
            data: Input data structure (will be deep copied)
            summary_request_id: Summary request identifier
            redacted_by: Entity performing redaction
        
        Returns:
            Tuple of (redacted_data, redaction_log)
        
        Raises:
            RedactionEngineError: If redaction fails
        """
        # Deep copy input (no mutation)
        redacted_data = json.loads(json.dumps(data))
        
        redactions = []
        
        # Apply redaction rules in fixed order
        self._redact_recursive(redacted_data, "", redactions)
        
        # Generate redaction log
        redaction_log = self._create_redaction_log(
            summary_request_id=summary_request_id,
            redactions=redactions,
            redacted_by=redacted_by
        )
        
        return redacted_data, redaction_log
    
    def _redact_recursive(self, obj: Any, path: str, redactions: List[Dict[str, Any]]) -> None:
        """
        Recursively redact PII from data structure.
        
        Args:
            obj: Object to redact (modified in place)
            path: Current JSONPath
            redactions: List to append redactions to
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                if isinstance(value, (dict, list)):
                    self._redact_recursive(value, current_path, redactions)
                else:
                    redacted_value, redaction_type = self._redact_value(value, current_path, redactions)
                    if redacted_value != value:
                        obj[key] = redacted_value
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                current_path = f"{path}[{idx}]"
                if isinstance(item, (dict, list)):
                    self._redact_recursive(item, current_path, redactions)
                else:
                    redacted_value, redaction_type = self._redact_value(item, current_path, redactions)
                    if redacted_value != item:
                        obj[idx] = redacted_value
    
    def _redact_value(self, value: Any, path: str, redactions: List[Dict[str, Any]]) -> tuple:
        """
        Redact a single value.
        
        Args:
            value: Value to redact
            path: JSONPath to value
            redactions: List to append redactions to
        
        Returns:
            Tuple of (redacted_value, redaction_type or None)
        """
        if not isinstance(value, str):
            return value, None
        
        original_value = value
        
        # Check for sensitive patterns first (all modes)
        if self.pattern_detector.has_sensitive_patterns(value):
            redacted_value = "[SECRET_REDACTED]"
            redactions.append({
                'field_path': path,
                'original_value': original_value,
                'redacted_value': redacted_value,
                'redaction_type': 'SECRET_PATTERN'
            })
            return redacted_value, 'SECRET_PATTERN'
        
        # IP address redaction
        if self._is_ip_address(value):
            if self.policy.should_hash_ip():
                redacted_value = self._hash_value(value, 8)
                redactions.append({
                    'field_path': path,
                    'original_value': original_value,
                    'redacted_value': redacted_value,
                    'redaction_type': 'IP_HASH'
                })
                return redacted_value, 'IP_HASH'
            elif self.policy.should_partial_ip():
                redacted_value = self._partial_ip(value)
                redactions.append({
                    'field_path': path,
                    'original_value': original_value,
                    'redacted_value': redacted_value,
                    'redaction_type': 'IP_PARTIAL'
                })
                return redacted_value, 'IP_PARTIAL'
        
        # Hostname redaction
        if self._is_hostname(value):
            if self.policy.should_hash_hostname():
                redacted_value = self._hash_value(value, 8)
                redactions.append({
                    'field_path': path,
                    'original_value': original_value,
                    'redacted_value': redacted_value,
                    'redaction_type': 'HOSTNAME_HASH'
                })
                return redacted_value, 'HOSTNAME_HASH'
            elif self.policy.should_truncate_hostname():
                redacted_value = self._truncate_hostname(value)
                redactions.append({
                    'field_path': path,
                    'original_value': original_value,
                    'redacted_value': redacted_value,
                    'redaction_type': 'HOSTNAME_TRUNCATE'
                })
                return redacted_value, 'HOSTNAME_TRUNCATE'
        
        # Username redaction
        if self._is_username(value):
            if self.policy.should_hash_username():
                redacted_value = self._hash_value(value, 8)
                redactions.append({
                    'field_path': path,
                    'original_value': original_value,
                    'redacted_value': redacted_value,
                    'redaction_type': 'USERNAME_HASH'
                })
                return redacted_value, 'USERNAME_HASH'
        
        # Email redaction
        if self._is_email(value):
            if self.policy.should_redact_email():
                redacted_value = "[EMAIL_REDACTED]"
                redactions.append({
                    'field_path': path,
                    'original_value': original_value,
                    'redacted_value': redacted_value,
                    'redaction_type': 'EMAIL_REDACT'
                })
                return redacted_value, 'EMAIL_REDACT'
            elif self.policy.should_email_domain_only():
                redacted_value = self._email_domain_only(value)
                redactions.append({
                    'field_path': path,
                    'original_value': original_value,
                    'redacted_value': redacted_value,
                    'redaction_type': 'EMAIL_DOMAIN_ONLY'
                })
                return redacted_value, 'EMAIL_DOMAIN_ONLY'
        
        # Domain redaction
        if self._is_domain(value):
            if self.policy.should_redact_domain():
                redacted_value = "[DOMAIN_REDACTED]"
                redactions.append({
                    'field_path': path,
                    'original_value': original_value,
                    'redacted_value': redacted_value,
                    'redaction_type': 'DOMAIN_REDACT'
                })
                return redacted_value, 'DOMAIN_REDACT'
            elif self.policy.should_second_level_domain():
                redacted_value = self._second_level_domain(value)
                redactions.append({
                    'field_path': path,
                    'original_value': original_value,
                    'redacted_value': redacted_value,
                    'redaction_type': 'DOMAIN_SECOND_LEVEL'
                })
                return redacted_value, 'DOMAIN_SECOND_LEVEL'
        
        return value, None
    
    def _is_ip_address(self, value: str) -> bool:
        """Check if value is an IP address."""
        import ipaddress
        try:
            ipaddress.ip_address(value)
            return True
        except ValueError:
            return False
    
    def _is_hostname(self, value: str) -> bool:
        """Check if value is a hostname."""
        # Simple heuristic: contains dots, no spaces, alphanumeric + dots/hyphens
        if '.' in value and ' ' not in value and value.replace('.', '').replace('-', '').isalnum():
            return True
        return False
    
    def _is_username(self, value: str) -> bool:
        """Check if value is a username."""
        # Simple heuristic: alphanumeric + underscore, no spaces, reasonable length
        if value.replace('_', '').isalnum() and ' ' not in value and 1 <= len(value) <= 64:
            return True
        return False
    
    def _is_email(self, value: str) -> bool:
        """Check if value is an email address."""
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        return bool(email_pattern.match(value))
    
    def _is_domain(self, value: str) -> bool:
        """Check if value is a domain name."""
        import re
        domain_pattern = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$')
        return bool(domain_pattern.match(value))
    
    def _hash_value(self, value: str, length: int = 8) -> str:
        """Hash value deterministically."""
        hash_obj = hashlib.sha256(value.encode('utf-8'))
        return hash_obj.hexdigest()[:length]
    
    def _partial_ip(self, ip: str) -> str:
        """Partially redact IP (first two octets only)."""
        parts = ip.split('.')
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.x.x"
        return ip
    
    def _truncate_hostname(self, hostname: str) -> str:
        """Truncate hostname to first component."""
        return hostname.split('.')[0]
    
    def _email_domain_only(self, email: str) -> str:
        """Extract domain only from email."""
        if '@' in email:
            return f"[REDACTED]@{email.split('@')[1]}"
        return email
    
    def _second_level_domain(self, domain: str) -> str:
        """Extract second-level domain only."""
        parts = domain.split('.')
        if len(parts) >= 2:
            return '.'.join(parts[-2:])
        return domain
    
    def _create_redaction_log(
        self,
        summary_request_id: str,
        redactions: List[Dict[str, Any]],
        redacted_by: str
    ) -> Dict[str, Any]:
        """
        Create redaction log.
        
        Args:
            summary_request_id: Summary request identifier
            redactions: List of redactions performed
            redacted_by: Entity that performed redaction
        
        Returns:
            Redaction log dictionary
        """
        redaction_log_id = str(uuid.uuid4())
        redacted_at = datetime.now(timezone.utc).isoformat()
        
        # Calculate redaction hash (deterministic)
        log_data = {
            'redaction_log_id': redaction_log_id,
            'summary_request_id': summary_request_id,
            'redaction_policy': self.policy.get_mode(),
            'redactions': redactions,
            'redacted_at': redacted_at,
            'redacted_by': redacted_by
        }
        
        # Calculate hash (exclude hash field itself)
        hash_input = json.dumps(log_data, sort_keys=True, separators=(',', ':'))
        redaction_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
        
        log_data['redaction_hash'] = redaction_hash
        
        return log_data
