#!/usr/bin/env python3
"""
RansomEye Threat Intelligence - Correlator
AUTHORITATIVE: Evidence ↔ IOC correlation
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid
import hashlib
import json


class CorrelationError(Exception):
    """Base exception for correlation errors."""
    pass


class Correlator:
    """
    Evidence ↔ IOC correlator.
    
    Properties:
    - Deterministic: Same evidence + same IOC = same correlation
    - Evidence-based: Correlations are evidence-based
    - Non-mutating: Correlations do not mutate evidence
    """
    
    def __init__(self):
        """Initialize correlator."""
        pass
    
    def correlate(
        self,
        ioc: Dict[str, Any],
        evidence: Dict[str, Any],
        evidence_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Correlate IOC with evidence.
        
        Args:
            ioc: IOC dictionary
            evidence: Evidence dictionary
            evidence_type: Type of evidence (forensic_artifact, network_scan, alert, etc.)
        
        Returns:
            Correlation dictionary, or None if no match
        """
        ioc_type = ioc.get('ioc_type', '')
        ioc_normalized = ioc.get('normalized_value', '')
        
        # Determine correlation method based on IOC type and evidence
        correlation_method = self._determine_method(ioc_type, evidence_type)
        
        if not correlation_method:
            return None
        
        # Perform correlation
        if correlation_method == 'hash_match':
            if self._hash_match(ioc_normalized, evidence):
                return self._create_correlation(ioc, evidence, evidence_type, correlation_method)
        elif correlation_method == 'exact_match':
            if self._exact_match(ioc_normalized, evidence):
                return self._create_correlation(ioc, evidence, evidence_type, correlation_method)
        elif correlation_method == 'domain_match':
            if self._domain_match(ioc_normalized, evidence):
                return self._create_correlation(ioc, evidence, evidence_type, correlation_method)
        elif correlation_method == 'ip_match':
            if self._ip_match(ioc_normalized, evidence):
                return self._create_correlation(ioc, evidence, evidence_type, correlation_method)
        
        return None
    
    def _determine_method(self, ioc_type: str, evidence_type: str) -> Optional[str]:
        """Determine correlation method."""
        # Hash-based correlation for file hashes
        if ioc_type in ['file_hash_md5', 'file_hash_sha1', 'file_hash_sha256']:
            if evidence_type == 'forensic_artifact':
                return 'hash_match'
        
        # Exact match for IPs, domains, URLs
        if ioc_type == 'ip_address':
            if evidence_type in ['network_scan', 'alert', 'deception_interaction']:
                return 'ip_match'
        
        if ioc_type == 'domain':
            if evidence_type in ['network_scan', 'alert']:
                return 'domain_match'
        
        if ioc_type == 'url':
            if evidence_type in ['alert', 'deception_interaction']:
                return 'exact_match'
        
        # Process name, mutex, registry key
        if ioc_type in ['process_name', 'mutex', 'registry_key']:
            if evidence_type == 'forensic_artifact':
                return 'exact_match'
        
        return None
    
    def _hash_match(self, ioc_value: str, evidence: Dict[str, Any]) -> bool:
        """Check hash match."""
        evidence_hash = evidence.get('hash', '') or evidence.get('file_hash', '')
        if not evidence_hash:
            return False
        
        return ioc_value.lower() == evidence_hash.lower()
    
    def _exact_match(self, ioc_value: str, evidence: Dict[str, Any]) -> bool:
        """Check exact match."""
        evidence_value = evidence.get('value', '') or evidence.get('name', '')
        if not evidence_value:
            return False
        
        return ioc_value.lower() == evidence_value.lower()
    
    def _domain_match(self, ioc_value: str, evidence: Dict[str, Any]) -> bool:
        """Check domain match."""
        evidence_domain = evidence.get('domain', '') or evidence.get('hostname', '')
        if not evidence_domain:
            return False
        
        # Extract domain from evidence
        domain = evidence_domain.lower()
        domain = domain.split('/')[0]
        domain = domain.split(':')[0]
        
        return ioc_value.lower() == domain
    
    def _ip_match(self, ioc_value: str, evidence: Dict[str, Any]) -> bool:
        """Check IP match."""
        evidence_ip = evidence.get('ip', '') or evidence.get('ip_address', '') or evidence.get('source_ip', '')
        if not evidence_ip:
            return False
        
        return ioc_value == str(evidence_ip)
    
    def _create_correlation(
        self,
        ioc: Dict[str, Any],
        evidence: Dict[str, Any],
        evidence_type: str,
        correlation_method: str
    ) -> Dict[str, Any]:
        """Create correlation record."""
        correlation = {
            'correlation_id': str(uuid.uuid4()),
            'ioc_id': ioc.get('ioc_id', ''),
            'evidence_type': evidence_type,
            'evidence_id': evidence.get('evidence_id', '') or evidence.get('id', ''),
            'correlation_method': correlation_method,
            'correlated_at': datetime.now(timezone.utc).isoformat(),
            'immutable_hash': '',
            'ledger_entry_id': ''
        }
        
        # Calculate hash
        correlation['immutable_hash'] = self._calculate_hash(correlation)
        
        return correlation
    
    def _calculate_hash(self, correlation: Dict[str, Any]) -> str:
        """Calculate SHA256 hash of correlation record."""
        hashable_content = {k: v for k, v in correlation.items() if k not in ['immutable_hash', 'ledger_entry_id']}
        canonical_json = json.dumps(hashable_content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
