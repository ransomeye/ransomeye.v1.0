#!/usr/bin/env python3
"""
RansomEye Explanation Assembly Engine - Assembly Hasher
AUTHORITATIVE: Deterministic SHA256 hashing for assembled explanations
"""

import hashlib
import json
from typing import Dict, Any


class AssemblyHasherError(Exception):
    """Base exception for assembly hasher errors."""
    pass


class AssemblyHasher:
    """
    Deterministic SHA256 hashing for assembled explanations.
    
    Properties:
    - Deterministic: Same input always produces same hash
    - Order-preserving: Field ordering is canonical
    - Replayable: Validator can rebuild and verify hashes
    """
    
    @staticmethod
    def hash_assembled_explanation(assembled_explanation: Dict[str, Any]) -> str:
        """
        Compute deterministic SHA256 hash of assembled explanation.
        
        Args:
            assembled_explanation: Assembled explanation dictionary
        
        Returns:
            SHA256 hash as hexadecimal string
        """
        # Canonical JSON serialization (sorted keys, no whitespace)
        canonical_json = json.dumps(
            assembled_explanation,
            sort_keys=True,
            separators=(',', ':'),
            ensure_ascii=False
        )
        
        # Compute SHA256 hash
        hash_obj = hashlib.sha256()
        hash_obj.update(canonical_json.encode('utf-8'))
        return hash_obj.hexdigest()
    
    @staticmethod
    def verify_assembled_explanation(assembled_explanation: Dict[str, Any], expected_hash: str) -> bool:
        """
        Verify assembled explanation hash.
        
        Args:
            assembled_explanation: Assembled explanation dictionary
            expected_hash: Expected SHA256 hash
        
        Returns:
            True if hash matches, False otherwise
        """
        computed_hash = AssemblyHasher.hash_assembled_explanation(assembled_explanation)
        return computed_hash == expected_hash
