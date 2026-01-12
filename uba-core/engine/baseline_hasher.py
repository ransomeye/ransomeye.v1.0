#!/usr/bin/env python3
"""
RansomEye UBA Core - Baseline Hasher
AUTHORITATIVE: Deterministic SHA256 hash of baseline content
"""

from typing import Dict, Any
import hashlib
import json


class BaselineHashError(Exception):
    """Base exception for baseline hashing errors."""
    pass


class BaselineHasher:
    """
    Deterministic baseline hasher.
    
    Properties:
    - Deterministic: Same baseline = same hash
    - Used for drift comparison: Hash changes indicate drift
    - No inference: Hashing is pure function
    """
    
    def __init__(self):
        """Initialize baseline hasher."""
        pass
    
    def calculate_hash(self, baseline: Dict[str, Any]) -> str:
        """
        Calculate deterministic SHA256 hash of baseline content.
        
        Args:
            baseline: Baseline dictionary
        
        Returns:
            SHA256 hash as hex string
        """
        # Hash only the observed features (not metadata)
        content = {
            'observed_event_types': baseline.get('observed_event_types', []),
            'observed_hosts': baseline.get('observed_hosts', []),
            'observed_time_buckets': baseline.get('observed_time_buckets', []),
            'observed_privileges': baseline.get('observed_privileges', [])
        }
        
        # Serialize to canonical JSON (deterministic)
        canonical_json = json.dumps(content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        
        # Calculate SHA256 hash
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
    
    def compare_baselines(self, baseline1: Dict[str, Any], baseline2: Dict[str, Any]) -> bool:
        """
        Compare two baselines by hash.
        
        Args:
            baseline1: First baseline dictionary
            baseline2: Second baseline dictionary
        
        Returns:
            True if baselines are identical, False otherwise
        """
        hash1 = self.calculate_hash(baseline1)
        hash2 = self.calculate_hash(baseline2)
        return hash1 == hash2
