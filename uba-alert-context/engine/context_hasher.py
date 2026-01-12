#!/usr/bin/env python3
"""
RansomEye UBA Alert Context Engine - Context Hasher
AUTHORITATIVE: Deterministic SHA256 hashing for alert context blocks
"""

import hashlib
import json
from typing import Dict, Any


class ContextHasherError(Exception):
    """Base exception for context hasher errors."""
    pass


class ContextHasher:
    """
    Deterministic SHA256 hashing for alert context blocks.
    
    Properties:
    - Deterministic: Same input always produces same hash
    - Order-preserving: Field ordering is canonical
    - Replayable: Validator can rebuild and verify hashes
    """
    
    @staticmethod
    def hash_context_block(context_block: Dict[str, Any]) -> str:
        """
        Compute deterministic SHA256 hash of context block.
        
        Args:
            context_block: Alert context block dictionary
        
        Returns:
            SHA256 hash as hexadecimal string
        """
        # Canonical JSON serialization (sorted keys, no whitespace)
        canonical_json = json.dumps(
            context_block,
            sort_keys=True,
            separators=(',', ':'),
            ensure_ascii=False
        )
        
        # Compute SHA256 hash
        hash_obj = hashlib.sha256()
        hash_obj.update(canonical_json.encode('utf-8'))
        return hash_obj.hexdigest()
    
    @staticmethod
    def verify_context_block(context_block: Dict[str, Any], expected_hash: str) -> bool:
        """
        Verify context block hash.
        
        Args:
            context_block: Alert context block dictionary
            expected_hash: Expected SHA256 hash
        
        Returns:
            True if hash matches, False otherwise
        """
        computed_hash = ContextHasher.hash_context_block(context_block)
        return computed_hash == expected_hash
