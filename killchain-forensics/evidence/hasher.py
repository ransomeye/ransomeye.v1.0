#!/usr/bin/env python3
"""
RansomEye KillChain & Forensics - Evidence Hasher
AUTHORITATIVE: Deterministic hashing of evidence artifacts
"""

import hashlib
from pathlib import Path


class HashingError(Exception):
    """Base exception for hashing errors."""
    pass


class Hasher:
    """
    Deterministic hashing of evidence artifacts.
    
    All hashing is deterministic (no randomness).
    Same inputs always produce same outputs.
    """
    
    @staticmethod
    def calculate_sha256(file_path: Path) -> str:
        """
        Calculate SHA256 hash of file.
        
        Args:
            file_path: Path to file
        
        Returns:
            SHA256 hash as hex string
        
        Raises:
            HashingError: If hashing fails
        """
        if not file_path.exists():
            raise HashingError(f"File not found: {file_path}")
        
        try:
            sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            raise HashingError(f"Failed to calculate hash for {file_path}: {e}") from e
    
    @staticmethod
    def verify_hash(file_path: Path, expected_hash: str) -> bool:
        """
        Verify file hash matches expected hash.
        
        Args:
            file_path: Path to file
            expected_hash: Expected SHA256 hash
        
        Returns:
            True if hash matches
        
        Raises:
            HashingError: If verification fails
        """
        calculated_hash = Hasher.calculate_sha256(file_path)
        
        if calculated_hash != expected_hash:
            raise HashingError(
                f"Hash mismatch for {file_path}: expected={expected_hash}, calculated={calculated_hash}"
            )
        
        return True
