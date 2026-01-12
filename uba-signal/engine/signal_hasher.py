#!/usr/bin/env python3
"""
RansomEye UBA Signal - Signal Hasher
AUTHORITATIVE: Deterministic SHA256 hash of signal content
"""

from typing import Dict, Any
import hashlib
import json


class SignalHashError(Exception):
    """Base exception for signal hashing errors."""
    pass


class SignalHasher:
    """
    Deterministic signal hasher.
    
    Properties:
    - Deterministic: Same signal = same hash
    - Enables validator replay: Hashes enable replay verification
    - No inference: Hashing is pure function
    """
    
    def __init__(self):
        """Initialize signal hasher."""
        pass
    
    def calculate_hash(self, signal: Dict[str, Any]) -> str:
        """
        Calculate deterministic SHA256 hash of signal content.
        
        Args:
            signal: Signal dictionary
        
        Returns:
            SHA256 hash as hex string
        """
        # Hash signal content (excluding metadata)
        content = {
            'delta_ids': sorted(signal.get('delta_ids', [])),
            'interpretation_type': signal.get('interpretation_type', ''),
            'contextual_inputs': signal.get('contextual_inputs', {})
        }
        
        # Serialize to canonical JSON (deterministic)
        canonical_json = json.dumps(content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        
        # Calculate SHA256 hash
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
    
    def calculate_summary_hash(self, summary: Dict[str, Any]) -> str:
        """
        Calculate deterministic SHA256 hash of summary content.
        
        Args:
            summary: Summary dictionary
        
        Returns:
            SHA256 hash as hex string
        """
        # Hash summary content (excluding metadata)
        content = {
            'signal_count': summary.get('signal_count', 0),
            'interpretation_types_present': sorted(summary.get('interpretation_types_present', []))
        }
        
        # Serialize to canonical JSON (deterministic)
        canonical_json = json.dumps(content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        
        # Calculate SHA256 hash
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
