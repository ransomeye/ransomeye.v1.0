#!/usr/bin/env python3
"""
RansomEye Threat Intelligence - Deduplicator
AUTHORITATIVE: Hash-based IOC deduplication
"""

from typing import Dict, Any, List, Set
import hashlib
import json


class DeduplicationError(Exception):
    """Base exception for deduplication errors."""
    pass


class Deduplicator:
    """
    Hash-based IOC deduplicator.
    
    Properties:
    - Hash-based: Deduplication based on normalized value hash
    - Deterministic: Same IOC = same deduplication result
    - Immutable: Deduplication records are immutable
    """
    
    def __init__(self):
        """Initialize deduplicator."""
        self.seen_iocs: Set[str] = set()  # Set of normalized IOC hashes
    
    def is_duplicate(self, ioc: Dict[str, Any]) -> bool:
        """
        Check if IOC is duplicate.
        
        Deduplication is based on normalized value hash.
        
        Args:
            ioc: IOC dictionary with normalized_value
        
        Returns:
            True if IOC is duplicate, False otherwise
        """
        normalized_value = ioc.get('normalized_value', '')
        ioc_type = ioc.get('ioc_type', '')
        
        # Build deduplication key
        dedup_key = f"{ioc_type}:{normalized_value}"
        
        # Calculate hash
        dedup_hash = hashlib.sha256(dedup_key.encode('utf-8')).hexdigest()
        
        # Check if seen
        if dedup_hash in self.seen_iocs:
            return True
        
        # Mark as seen
        self.seen_iocs.add(dedup_hash)
        return False
    
    def get_existing_ioc(
        self,
        iocs: List[Dict[str, Any]],
        normalized_value: str,
        ioc_type: str
    ) -> Dict[str, Any]:
        """
        Get existing IOC by normalized value and type.
        
        Args:
            iocs: List of IOC dictionaries
            normalized_value: Normalized IOC value
            ioc_type: IOC type
        
        Returns:
            Existing IOC dictionary, or None if not found
        """
        for ioc in iocs:
            if (ioc.get('normalized_value') == normalized_value and
                ioc.get('ioc_type') == ioc_type):
                return ioc
        
        return None
