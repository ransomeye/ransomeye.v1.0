#!/usr/bin/env python3
"""
RansomEye UBA Core - Behavior Normalizer
AUTHORITATIVE: Canonicalize behavior events
"""

from typing import Dict, Any
from datetime import datetime, timezone
import uuid
import hashlib
import json


class BehaviorNormalizationError(Exception):
    """Base exception for behavior normalization errors."""
    pass


class BehaviorNormalizer:
    """
    Canonical behavior event normalizer.
    
    Properties:
    - Canonical timestamps: RFC3339 UTC timestamps
    - Canonical event types: Explicit enumeration
    - Canonical identity references: UUID-based
    """
    
    def __init__(self):
        """Initialize behavior normalizer."""
        pass
    
    def normalize(
        self,
        raw_event: Dict[str, Any],
        identity_id: str
    ) -> Dict[str, Any]:
        """
        Normalize behavior event to canonical form.
        
        Args:
            raw_event: Raw behavior event from source component
            identity_id: Identity identifier (resolved)
        
        Returns:
            Normalized behavior event dictionary
        """
        # Extract and validate required fields
        event_type = raw_event.get('event_type', '')
        source_component = raw_event.get('source_component', '')
        resource_id = raw_event.get('resource_id', '')
        action = raw_event.get('action', '')
        timestamp = raw_event.get('timestamp', '')
        host_id = raw_event.get('host_id', '')
        evidence_ref = raw_event.get('evidence_ref', '')
        
        # Validate event type
        valid_types = ['login', 'file_access', 'process_start', 'network_access', 'privilege_use', 'policy_override']
        if event_type not in valid_types:
            raise BehaviorNormalizationError(f"Invalid event type: {event_type}")
        
        # Validate source component
        valid_components = ['linux-agent', 'windows-agent', 'dpi', 'hnmp', 'ir', 'deception']
        if source_component not in valid_components:
            raise BehaviorNormalizationError(f"Invalid source component: {source_component}")
        
        # Normalize timestamp (canonical RFC3339 UTC)
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                normalized_timestamp = dt.isoformat()
            except Exception:
                normalized_timestamp = datetime.now(timezone.utc).isoformat()
        else:
            normalized_timestamp = datetime.now(timezone.utc).isoformat()
        
        # Create normalized event
        normalized = {
            'event_id': str(uuid.uuid4()),
            'identity_id': identity_id,
            'event_type': event_type,
            'source_component': source_component,
            'resource_id': resource_id,
            'action': action,
            'timestamp': normalized_timestamp,
            'host_id': host_id,
            'evidence_ref': evidence_ref,
            'immutable_hash': '',
            'ledger_entry_id': ''
        }
        
        # Calculate hash
        normalized['immutable_hash'] = self._calculate_hash(normalized)
        
        return normalized
    
    def _calculate_hash(self, event: Dict[str, Any]) -> str:
        """Calculate SHA256 hash of event record."""
        hashable_content = {k: v for k, v in event.items() if k not in ['immutable_hash', 'ledger_entry_id']}
        canonical_json = json.dumps(hashable_content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
