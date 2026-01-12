#!/usr/bin/env python3
"""
RansomEye AI Model Registry - Model Bundle Verifier
AUTHORITATIVE: Cryptographic verification of model bundles before registry entry
"""

import hashlib
import base64
from pathlib import Path
from typing import Tuple

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False
    Ed25519PublicKey = None
    InvalidSignature = Exception


class BundleVerificationError(Exception):
    """Base exception for bundle verification errors."""
    pass


class HashMismatchError(BundleVerificationError):
    """Raised when artifact hash doesn't match."""
    pass


class SignatureVerificationError(BundleVerificationError):
    """Raised when signature verification fails."""
    pass


class BundleVerifier:
    """
    Verifies model bundles before registry entry.
    
    Verification process:
    1. Calculate SHA256 hash of model artifact
    2. Verify hash matches provided hash
    3. Verify signature of hash using public key
    """
    
    def __init__(self, public_key: Ed25519PublicKey):
        """
        Initialize bundle verifier.
        
        Args:
            public_key: Ed25519 public key for verification
        """
        if not _CRYPTO_AVAILABLE:
            raise BundleVerificationError("cryptography library not available. Install with: pip install cryptography")
        
        self.public_key = public_key
    
    def calculate_artifact_hash(self, artifact_path: Path) -> str:
        """
        Calculate SHA256 hash of model artifact.
        
        Args:
            artifact_path: Path to model artifact file
        
        Returns:
            SHA256 hash as hex string
        
        Raises:
            BundleVerificationError: If artifact cannot be read
        """
        if not artifact_path.exists():
            raise BundleVerificationError(f"Artifact not found: {artifact_path}")
        
        try:
            sha256 = hashlib.sha256()
            with open(artifact_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            raise BundleVerificationError(f"Failed to calculate artifact hash: {e}") from e
    
    def verify_hash(self, artifact_path: Path, expected_hash: str) -> bool:
        """
        Verify artifact hash matches expected hash.
        
        Args:
            artifact_path: Path to model artifact file
            expected_hash: Expected SHA256 hash
        
        Returns:
            True if hash matches
        
        Raises:
            HashMismatchError: If hash doesn't match
        """
        calculated_hash = self.calculate_artifact_hash(artifact_path)
        
        if calculated_hash != expected_hash:
            raise HashMismatchError(
                f"Hash mismatch: expected={expected_hash}, calculated={calculated_hash}"
            )
        
        return True
    
    def verify_signature(self, artifact_hash: str, signature: str) -> bool:
        """
        Verify ed25519 signature of artifact hash.
        
        Args:
            artifact_hash: SHA256 hash of artifact
            signature: Base64-encoded ed25519 signature
        
        Returns:
            True if signature is valid
        
        Raises:
            SignatureVerificationError: If signature verification fails
        """
        try:
            signature_bytes = base64.b64decode(signature)
            hash_bytes = bytes.fromhex(artifact_hash)
            self.public_key.verify(signature_bytes, hash_bytes)
            return True
            
        except InvalidSignature as e:
            raise SignatureVerificationError(f"Invalid signature: {e}") from e
        except Exception as e:
            raise SignatureVerificationError(f"Signature verification failed: {e}") from e
    
    def verify_bundle(self, artifact_path: Path, expected_hash: str, signature: str) -> bool:
        """
        Verify complete model bundle (hash and signature).
        
        Args:
            artifact_path: Path to model artifact file
            expected_hash: Expected SHA256 hash
            signature: Base64-encoded ed25519 signature
        
        Returns:
            True if bundle is valid
        
        Raises:
            BundleVerificationError: If verification fails
        """
        # Verify hash
        self.verify_hash(artifact_path, expected_hash)
        
        # Verify signature
        self.verify_signature(expected_hash, signature)
        
        return True
