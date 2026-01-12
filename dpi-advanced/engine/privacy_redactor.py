#!/usr/bin/env python3
"""
RansomEye DPI Advanced - Privacy Redactor
AUTHORITATIVE: Policy-driven privacy redaction
"""

from typing import Dict, Any
import hashlib
import ipaddress


class PrivacyRedactionError(Exception):
    """Base exception for privacy redaction errors."""
    pass


class PrivacyRedactor:
    """
    Policy-driven privacy redactor.
    
    Properties:
    - Policy-driven: Redaction based on privacy policy
    - Deterministic: Same input + same policy = same output
    - Before storage: Redaction happens before storage and upload
    """
    
    def __init__(self, privacy_policy: Dict[str, Any]):
        """
        Initialize privacy redactor.
        
        Args:
            privacy_policy: Privacy policy dictionary
        """
        self.policy = privacy_policy
        self.privacy_mode = privacy_policy.get('privacy_mode', 'FORENSIC')
        self.ip_redaction = privacy_policy.get('ip_redaction', 'none')
        self.port_redaction = privacy_policy.get('port_redaction', 'none')
        self.dns_redaction = privacy_policy.get('dns_redaction', 'none')
    
    def redact_flow(self, flow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact flow according to privacy policy.
        
        Args:
            flow: Flow dictionary
        
        Returns:
            Redacted flow dictionary
        """
        redacted = flow.copy()
        
        # Redact IPs
        if self.ip_redaction == 'hash':
            redacted['src_ip'] = self._hash_ip(flow.get('src_ip', ''))
            redacted['dst_ip'] = self._hash_ip(flow.get('dst_ip', ''))
        elif self.ip_redaction == 'partial':
            redacted['src_ip'] = self._partial_ip(flow.get('src_ip', ''))
            redacted['dst_ip'] = self._partial_ip(flow.get('dst_ip', ''))
        # 'none' means no redaction
        
        # Redact ports
        if self.port_redaction == 'truncate':
            redacted['src_port'] = redacted.get('src_port', 0) & 0xFF00  # Keep high byte
            redacted['dst_port'] = redacted.get('dst_port', 0) & 0xFF00
        # 'none' means no redaction
        
        # DNS redaction (if DNS data in event_data)
        if self.dns_redaction == 'second_level_only':
            event_data = redacted.get('event_data', {})
            if 'dns_query' in event_data:
                event_data['dns_query'] = self._second_level_domain(event_data['dns_query'])
        elif self.dns_redaction == 'hash':
            event_data = redacted.get('event_data', {})
            if 'dns_query' in event_data:
                event_data['dns_query'] = self._hash_domain(event_data['dns_query'])
        
        return redacted
    
    def _hash_ip(self, ip: str) -> str:
        """Hash IP address deterministically."""
        try:
            ip_obj = ipaddress.ip_address(ip)
            ip_bytes = ip_obj.packed
            hash_obj = hashlib.sha256(ip_bytes)
            return hash_obj.hexdigest()[:16]  # Return first 16 chars as identifier
        except Exception:
            return ip
    
    def _partial_ip(self, ip: str) -> str:
        """Partially redact IP (keep first two octets)."""
        try:
            parts = ip.split('.')
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.0.0"
            return ip
        except Exception:
            return ip
    
    def _second_level_domain(self, domain: str) -> str:
        """Extract second-level domain only."""
        parts = domain.split('.')
        if len(parts) >= 2:
            return '.'.join(parts[-2:])
        return domain
    
    def _hash_domain(self, domain: str) -> str:
        """Hash domain name deterministically."""
        hash_obj = hashlib.sha256(domain.encode('utf-8'))
        return hash_obj.hexdigest()[:16]
