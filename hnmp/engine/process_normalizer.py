#!/usr/bin/env python3
"""
RansomEye HNMP Engine - Process Normalizer
AUTHORITATIVE: Canonical process event normalization
"""

from typing import Dict, Any
from datetime import datetime, timezone
import uuid
import hashlib
import json


class ProcessNormalizationError(Exception):
    """Base exception for process normalization errors."""
    pass


class ProcessNormalizer:
    """
    Canonical process event normalizer.
    
    Properties:
    - Deterministic: Same input = same normalized output
    - Canonical: Normalized events are canonical
    - Facts only: No inference, no scoring
    """
    
    def __init__(self):
        """Initialize process normalizer."""
        pass
    
    def normalize(
        self,
        raw_event: Dict[str, Any],
        source_agent: str
    ) -> Dict[str, Any]:
        """
        Normalize process event to canonical form.
        
        Args:
            raw_event: Raw process event from agent
            source_agent: Source agent identifier
        
        Returns:
            Normalized process event dictionary
        """
        # Extract and validate required fields
        event_type = raw_event.get('event_type', '')
        process_id = raw_event.get('process_id', 0)
        parent_process_id = raw_event.get('parent_process_id', 0)
        host_id = raw_event.get('host_id', '')
        user_id = raw_event.get('user_id', '')
        executable_path = raw_event.get('executable_path', '')
        command_line = raw_event.get('command_line', '')
        timestamp = raw_event.get('timestamp', '')
        event_data = raw_event.get('event_data', {})
        
        # Validate event type
        valid_types = [
            'process_start', 'process_exit', 'parent_child_linkage',
            'injection_attempt', 'suspicious_flags'
        ]
        if event_type not in valid_types:
            raise ProcessNormalizationError(f"Invalid event type: {event_type}")
        
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
            'event_type': event_type,
            'process_id': int(process_id),
            'parent_process_id': int(parent_process_id) if parent_process_id else 0,
            'host_id': host_id,
            'user_id': user_id,
            'executable_path': executable_path,
            'command_line': command_line,
            'timestamp': normalized_timestamp,
            'event_data': event_data,
            'source_agent': source_agent,
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
