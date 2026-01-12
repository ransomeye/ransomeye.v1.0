#!/usr/bin/env python3
"""
RansomEye Signed Reporting Engine - Render Hasher
AUTHORITATIVE: Deterministic SHA256 hashing for rendered reports
"""

import hashlib
from typing import bytes as BytesType


class RenderHasherError(Exception):
    """Base exception for render hasher errors."""
    pass


class RenderHasher:
    """
    Deterministic SHA256 hashing for rendered reports.
    
    Properties:
    - Deterministic: Same input always produces same hash
    - Bit-for-bit reproducible
    - Used for content integrity verification
    """
    
    @staticmethod
    def hash_content(content: BytesType) -> str:
        """
        Compute deterministic SHA256 hash of rendered content.
        
        Args:
            content: Rendered report content as bytes
        
        Returns:
            SHA256 hash as hexadecimal string
        """
        hash_obj = hashlib.sha256()
        hash_obj.update(content)
        return hash_obj.hexdigest()
    
    @staticmethod
    def verify_content(content: BytesType, expected_hash: str) -> bool:
        """
        Verify rendered content hash.
        
        Args:
            content: Rendered report content as bytes
            expected_hash: Expected SHA256 hash
        
        Returns:
            True if hash matches, False otherwise
        """
        computed_hash = RenderHasher.hash_content(content)
        return computed_hash == expected_hash
