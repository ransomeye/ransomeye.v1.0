#!/usr/bin/env python3
"""
RansomEye UBA Drift - Delta Hasher
AUTHORITATIVE: Deterministic SHA256 hash of delta content
"""

from typing import Dict, Any
import hashlib
import json


class DeltaHashError(Exception):
    """Base exception for delta hashing errors."""
    pass


class DeltaHasher:
    """
    Deterministic delta hasher.
    
    Properties:
    - Deterministic: Same delta = same hash
    - Enables validator replay: Hashes enable replay verification
    - No inference: Hashing is pure function
    """
    
    def __init__(self):
        """Initialize delta hasher."""
        pass
    
    def calculate_hash(self, delta: Dict[str, Any]) -> str:
        """
        Calculate deterministic SHA256 hash of delta content.
        
        Args:
            delta: Delta dictionary
        
        Returns:
            SHA256 hash as hex string
        """
        # Hash delta content (excluding metadata)
        content = {
            'delta_type': delta.get('delta_type', ''),
            'baseline_value': delta.get('baseline_value'),
            'observed_value': delta.get('observed_value'),
            'delta_magnitude': delta.get('delta_magnitude', 0.0)
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
            'total_deltas': summary.get('total_deltas', 0),
            'delta_types_present': sorted(summary.get('delta_types_present', []))
        }
        
        # Serialize to canonical JSON (deterministic)
        canonical_json = json.dumps(content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        
        # Calculate SHA256 hash
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
