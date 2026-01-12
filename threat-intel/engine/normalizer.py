#!/usr/bin/env python3
"""
RansomEye Threat Intelligence - Normalizer
AUTHORITATIVE: Canonical IOC normalization
"""

from typing import Dict, Any
import re
import ipaddress


class NormalizationError(Exception):
    """Base exception for normalization errors."""
    pass


class Normalizer:
    """
    Canonical IOC normalizer.
    
    Properties:
    - Deterministic: Same IOC value = same normalized value
    - Canonical: Normalized values are canonical
    - Type-specific: Different normalization rules per IOC type
    """
    
    def __init__(self):
        """Initialize normalizer."""
        pass
    
    def normalize(self, ioc: Dict[str, Any]) -> str:
        """
        Normalize IOC value to canonical form.
        
        Args:
            ioc: IOC dictionary with ioc_type and ioc_value
        
        Returns:
            Normalized IOC value
        """
        ioc_type = ioc.get('ioc_type', '')
        ioc_value = ioc.get('ioc_value', '')
        
        if ioc_type == 'ip_address':
            return self._normalize_ip(ioc_value)
        elif ioc_type == 'domain':
            return self._normalize_domain(ioc_value)
        elif ioc_type == 'url':
            return self._normalize_url(ioc_value)
        elif ioc_type in ['file_hash_md5', 'file_hash_sha1', 'file_hash_sha256']:
            return self._normalize_hash(ioc_value)
        elif ioc_type == 'email_address':
            return self._normalize_email(ioc_value)
        elif ioc_type == 'registry_key':
            return self._normalize_registry_key(ioc_value)
        elif ioc_type == 'process_name':
            return self._normalize_process_name(ioc_value)
        elif ioc_type == 'mutex':
            return self._normalize_mutex(ioc_value)
        elif ioc_type == 'user_agent':
            return self._normalize_user_agent(ioc_value)
        else:
            raise NormalizationError(f"Unknown IOC type: {ioc_type}")
    
    def _normalize_ip(self, value: str) -> str:
        """Normalize IP address."""
        try:
            ip = ipaddress.ip_address(value.strip())
            return str(ip)
        except ValueError:
            raise NormalizationError(f"Invalid IP address: {value}")
    
    def _normalize_domain(self, value: str) -> str:
        """Normalize domain name."""
        domain = value.strip().lower()
        # Remove protocol prefix if present
        domain = re.sub(r'^https?://', '', domain)
        domain = re.sub(r'^www\.', '', domain)
        # Remove path if present
        domain = domain.split('/')[0]
        # Remove port if present
        domain = domain.split(':')[0]
        return domain
    
    def _normalize_url(self, value: str) -> str:
        """Normalize URL."""
        url = value.strip().lower()
        # Ensure protocol
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url
    
    def _normalize_hash(self, value: str) -> str:
        """Normalize file hash."""
        hash_value = value.strip().lower()
        # Remove whitespace
        hash_value = re.sub(r'\s+', '', hash_value)
        return hash_value
    
    def _normalize_email(self, value: str) -> str:
        """Normalize email address."""
        email = value.strip().lower()
        return email
    
    def _normalize_registry_key(self, value: str) -> str:
        """Normalize registry key."""
        key = value.strip()
        # Normalize to uppercase for Windows registry
        key = key.upper()
        return key
    
    def _normalize_process_name(self, value: str) -> str:
        """Normalize process name."""
        process = value.strip().lower()
        # Remove path if present
        process = process.split('\\')[-1]
        process = process.split('/')[-1]
        return process
    
    def _normalize_mutex(self, value: str) -> str:
        """Normalize mutex."""
        mutex = value.strip()
        return mutex
    
    def _normalize_user_agent(self, value: str) -> str:
        """Normalize user agent."""
        ua = value.strip()
        return ua
