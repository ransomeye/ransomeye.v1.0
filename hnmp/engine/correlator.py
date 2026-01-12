#!/usr/bin/env python3
"""
RansomEye HNMP Engine - Correlator
AUTHORITATIVE: Strictly factual event correlation
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
    Strictly factual event correlator.
    
    Properties:
    - Factual only: Correlations are strictly factual
    - Deterministic: Same events = same correlations
    - No inference: No campaign inference, no timelines, no killchain logic
    """
    
    def __init__(self):
        """Initialize correlator."""
        pass
    
    def correlate(
        self,
        source_event: Dict[str, Any],
        source_type: str,
        target_event: Dict[str, Any],
        target_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Correlate two events.
        
        Args:
            source_event: Source event dictionary
            source_type: Source event type (host, network, process, malware)
            target_event: Target event dictionary
            target_type: Target event type (host, network, process, malware)
        
        Returns:
            Correlation dictionary, or None if no factual correlation
        """
        # Determine correlation type
        correlation_type = self._determine_correlation_type(source_type, target_type, source_event, target_event)
        
        if not correlation_type:
            return None
        
        # Create correlation
        correlation = {
            'correlation_id': str(uuid.uuid4()),
            'source_event_type': source_type,
            'source_event_id': source_event.get('event_id', ''),
            'target_event_type': target_type,
            'target_event_id': target_event.get('event_id', ''),
            'correlation_type': correlation_type,
            'correlated_at': datetime.now(timezone.utc).isoformat(),
            'immutable_hash': '',
            'ledger_entry_id': ''
        }
        
        # Calculate hash
        correlation['immutable_hash'] = self._calculate_hash(correlation)
        
        return correlation
    
    def _determine_correlation_type(
        self,
        source_type: str,
        target_type: str,
        source_event: Dict[str, Any],
        target_event: Dict[str, Any]
    ) -> Optional[str]:
        """
        Determine correlation type based on event types and data.
        
        Returns:
            Correlation type, or None if no factual correlation
        """
        # Process ↔ Network Flow
        if source_type == 'process' and target_type == 'network':
            if self._process_matches_network(source_event, target_event):
                return 'process_network_flow'
        
        if source_type == 'network' and target_type == 'process':
            if self._process_matches_network(target_event, source_event):
                return 'process_network_flow'
        
        # Process ↔ File Artifact
        if source_type == 'process' and target_type == 'malware':
            if self._process_matches_file(source_event, target_event):
                return 'process_file_artifact'
        
        if source_type == 'malware' and target_type == 'process':
            if self._process_matches_file(target_event, source_event):
                return 'process_file_artifact'
        
        # File Artifact ↔ Malware Hash
        if source_type == 'malware' and target_type == 'malware':
            if self._file_matches_hash(source_event, target_event):
                return 'file_artifact_malware_hash'
        
        # User ↔ Process
        if source_type == 'host' and target_type == 'process':
            if self._user_matches_process(source_event, target_event):
                return 'user_process'
        
        if source_type == 'process' and target_type == 'host':
            if self._user_matches_process(target_event, source_event):
                return 'user_process'
        
        # Host ↔ Network Identity
        if source_type == 'host' and target_type == 'network':
            if self._host_matches_network(source_event, target_event):
                return 'host_network_identity'
        
        if source_type == 'network' and target_type == 'host':
            if self._host_matches_network(target_event, source_event):
                return 'host_network_identity'
        
        return None
    
    def _process_matches_network(self, process_event: Dict[str, Any], network_event: Dict[str, Any]) -> bool:
        """Check if process matches network flow (factual match only)."""
        # Factual match: process_id in network event data
        network_data = network_event.get('event_data', {})
        process_id = process_event.get('process_id', 0)
        return network_data.get('process_id') == process_id
    
    def _process_matches_file(self, process_event: Dict[str, Any], malware_event: Dict[str, Any]) -> bool:
        """Check if process matches file artifact (factual match only)."""
        # Factual match: executable_path matches file_path
        executable_path = process_event.get('executable_path', '')
        file_path = malware_event.get('file_path', '')
        return executable_path == file_path
    
    def _file_matches_hash(self, event1: Dict[str, Any], event2: Dict[str, Any]) -> bool:
        """Check if file artifact matches malware hash (factual match only)."""
        # Factual match: hashes match
        hash1_sha256 = event1.get('file_hash_sha256', '')
        hash2_sha256 = event2.get('file_hash_sha256', '')
        if hash1_sha256 and hash2_sha256:
            return hash1_sha256.lower() == hash2_sha256.lower()
        return False
    
    def _user_matches_process(self, host_event: Dict[str, Any], process_event: Dict[str, Any]) -> bool:
        """Check if user matches process (factual match only)."""
        # Factual match: user_id matches
        user_id = host_event.get('user_id', '')
        process_user_id = process_event.get('user_id', '')
        return user_id == process_user_id
    
    def _host_matches_network(self, host_event: Dict[str, Any], network_event: Dict[str, Any]) -> bool:
        """Check if host matches network identity (factual match only)."""
        # Factual match: host_id in network event data
        network_data = network_event.get('event_data', {})
        host_id = host_event.get('host_id', '')
        return network_data.get('host_id') == host_id
    
    def _calculate_hash(self, correlation: Dict[str, Any]) -> str:
        """Calculate SHA256 hash of correlation record."""
        hashable_content = {k: v for k, v in correlation.items() if k not in ['immutable_hash', 'ledger_entry_id']}
        canonical_json = json.dumps(hashable_content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
