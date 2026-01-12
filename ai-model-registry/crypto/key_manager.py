#!/usr/bin/env python3
"""
RansomEye AI Model Registry - Model Bundle Key Manager
AUTHORITATIVE: Key management for model bundle signature verification
"""

import os
import hashlib
from pathlib import Path
from typing import Tuple, Optional
import base64

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    from cryptography.hazmat.backends import default_backend
    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False
    class Ed25519PrivateKey:
        pass
    class Ed25519PublicKey:
        pass


class ModelKeyManagerError(Exception):
    """Base exception for model key management errors."""
    pass


class ModelKeyNotFoundError(ModelKeyManagerError):
    """Raised when model key file is not found."""
    pass


class ModelKeyManager:
    """
    Manages ed25519 keypairs for model bundle signature verification.
    
    Separate from audit ledger and validator keys.
    Used specifically for signing and verifying model artifacts.
    """
    
    def __init__(self, key_dir: Path):
        """
        Initialize model key manager.
        
        Args:
            key_dir: Directory where model keys are stored
        """
        if not _CRYPTO_AVAILABLE:
            raise ModelKeyManagerError("cryptography library not available. Install with: pip install cryptography")
        
        self.key_dir = Path(key_dir)
        self.key_dir.mkdir(parents=True, exist_ok=True)
        
        # Key file paths
        self.private_key_path = self.key_dir / "model-signing-key.pem"
        self.public_key_path = self.key_dir / "model-signing-key.pub"
        self.key_id_path = self.key_dir / "model-signing-key.id"
    
    def generate_keypair(self) -> Tuple[Ed25519PrivateKey, Ed25519PublicKey, str]:
        """
        Generate a new ed25519 keypair for model signing.
        
        Returns:
            Tuple of (private_key, public_key, key_id)
            key_id is SHA256 hash of public key bytes
        
        Raises:
            ModelKeyManagerError: If key generation fails
        """
        try:
            private_key = Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
            
            public_key_bytes = public_key.public_bytes_raw()
            key_id = hashlib.sha256(public_key_bytes).hexdigest()
            
            return private_key, public_key, key_id
            
        except Exception as e:
            raise ModelKeyManagerError(f"Failed to generate model keypair: {e}") from e
    
    def save_keypair(self, private_key: Ed25519PrivateKey, public_key: Ed25519PublicKey, key_id: str) -> None:
        """
        Save model keypair to disk.
        
        Args:
            private_key: Ed25519 private key
            public_key: Ed25519 public key
            key_id: Key identifier (SHA256 hash of public key)
        """
        try:
            private_key_pem = private_key.private_bytes_raw()
            self.private_key_path.write_bytes(private_key_pem)
            os.chmod(self.private_key_path, 0o600)
            
            public_key_bytes = public_key.public_bytes_raw()
            self.public_key_path.write_bytes(public_key_bytes)
            os.chmod(self.public_key_path, 0o644)
            
            self.key_id_path.write_text(key_id)
            os.chmod(self.key_id_path, 0o644)
            
        except Exception as e:
            raise ModelKeyManagerError(f"Failed to save model keypair: {e}") from e
    
    def load_keypair(self) -> Tuple[Ed25519PrivateKey, Ed25519PublicKey, str]:
        """
        Load model keypair from disk.
        
        Returns:
            Tuple of (private_key, public_key, key_id)
        """
        if not self.private_key_path.exists():
            raise ModelKeyNotFoundError(f"Model private key not found: {self.private_key_path}")
        if not self.public_key_path.exists():
            raise ModelKeyNotFoundError(f"Model public key not found: {self.public_key_path}")
        if not self.key_id_path.exists():
            raise ModelKeyNotFoundError(f"Model key ID not found: {self.key_id_path}")
        
        try:
            private_key_bytes = self.private_key_path.read_bytes()
            private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
            
            public_key_bytes = self.public_key_path.read_bytes()
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            
            key_id = self.key_id_path.read_text().strip()
            
            computed_key_id = hashlib.sha256(public_key_bytes).hexdigest()
            if computed_key_id != key_id:
                raise ModelKeyManagerError(f"Model key ID mismatch: stored={key_id}, computed={computed_key_id}")
            
            return private_key, public_key, key_id
            
        except Exception as e:
            raise ModelKeyManagerError(f"Failed to load model keypair: {e}") from e
    
    def get_or_create_keypair(self) -> Tuple[Ed25519PrivateKey, Ed25519PublicKey, str]:
        """
        Get existing model keypair or create new one if it doesn't exist.
        
        Returns:
            Tuple of (private_key, public_key, key_id)
        """
        try:
            return self.load_keypair()
        except ModelKeyNotFoundError:
            private_key, public_key, key_id = self.generate_keypair()
            self.save_keypair(private_key, public_key, key_id)
            return private_key, public_key, key_id
    
    def get_public_key(self) -> Ed25519PublicKey:
        """
        Get public key only (for verification).
        
        Returns:
            Ed25519 public key
        """
        if not self.public_key_path.exists():
            raise ModelKeyNotFoundError(f"Model public key not found: {self.public_key_path}")
        
        try:
            public_key_bytes = self.public_key_path.read_bytes()
            return Ed25519PublicKey.from_public_bytes(public_key_bytes)
        except Exception as e:
            raise ModelKeyManagerError(f"Failed to load model public key: {e}") from e
    
    def get_key_id(self) -> str:
        """
        Get key ID (SHA256 hash of public key).
        
        Returns:
            Key identifier as hex string
        """
        if not self.key_id_path.exists():
            raise ModelKeyNotFoundError(f"Model key ID not found: {self.key_id_path}")
        
        return self.key_id_path.read_text().strip()
