#!/usr/bin/env python3
"""
RansomEye Audit Ledger - Key Manager
AUTHORITATIVE: ed25519 keypair generation and management for audit ledger signing
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
    # Stub classes for environments without cryptography library
    class Ed25519PrivateKey:
        pass
    class Ed25519PublicKey:
        pass


class KeyManagerError(Exception):
    """Base exception for key management errors."""
    pass


class KeyNotFoundError(KeyManagerError):
    """Raised when key file is not found."""
    pass


class KeyGenerationError(KeyManagerError):
    """Raised when key generation fails."""
    pass


class KeyManager:
    """
    Manages ed25519 keypairs for audit ledger signing.
    
    Key properties:
    - Private key: Never logged, never exported, stored securely
    - Public key: Exportable, used for verification
    - Key ID: SHA256 hash of public key (used as signing_key_id in entries)
    """
    
    def __init__(self, key_dir: Path):
        """
        Initialize key manager.
        
        Args:
            key_dir: Directory where keys are stored
        """
        if not _CRYPTO_AVAILABLE:
            raise KeyManagerError("cryptography library not available. Install with: pip install cryptography")
        
        self.key_dir = Path(key_dir)
        self.key_dir.mkdir(parents=True, exist_ok=True)
        
        # Key file paths
        self.private_key_path = self.key_dir / "ledger-signing-key.pem"
        self.public_key_path = self.key_dir / "ledger-signing-key.pub"
        self.key_id_path = self.key_dir / "ledger-signing-key.id"
    
    def generate_keypair(self) -> Tuple[Ed25519PrivateKey, Ed25519PublicKey, str]:
        """
        Generate a new ed25519 keypair.
        
        Returns:
            Tuple of (private_key, public_key, key_id)
            key_id is SHA256 hash of public key bytes
        
        Raises:
            KeyGenerationError: If key generation fails
        """
        try:
            # Generate ed25519 private key
            private_key = Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
            
            # Get public key bytes
            public_key_bytes = public_key.public_bytes_raw()
            
            # Calculate key ID (SHA256 hash of public key)
            key_id = hashlib.sha256(public_key_bytes).hexdigest()
            
            return private_key, public_key, key_id
            
        except Exception as e:
            raise KeyGenerationError(f"Failed to generate keypair: {e}") from e
    
    def save_keypair(self, private_key: Ed25519PrivateKey, public_key: Ed25519PublicKey, key_id: str) -> None:
        """
        Save keypair to disk.
        
        Args:
            private_key: Ed25519 private key
            public_key: Ed25519 public key
            key_id: Key identifier (SHA256 hash of public key)
        
        Raises:
            KeyManagerError: If saving fails
        """
        try:
            # Save private key (PEM format, secure permissions)
            private_key_pem = private_key.private_bytes_raw()
            self.private_key_path.write_bytes(private_key_pem)
            # Set restrictive permissions (owner read/write only)
            os.chmod(self.private_key_path, 0o600)
            
            # Save public key (raw bytes, readable)
            public_key_bytes = public_key.public_bytes_raw()
            self.public_key_path.write_bytes(public_key_bytes)
            os.chmod(self.public_key_path, 0o644)
            
            # Save key ID (text file)
            self.key_id_path.write_text(key_id)
            os.chmod(self.key_id_path, 0o644)
            
        except Exception as e:
            raise KeyManagerError(f"Failed to save keypair: {e}") from e
    
    def load_keypair(self) -> Tuple[Ed25519PrivateKey, Ed25519PublicKey, str]:
        """
        Load keypair from disk.
        
        Returns:
            Tuple of (private_key, public_key, key_id)
        
        Raises:
            KeyNotFoundError: If key files are not found
            KeyManagerError: If loading fails
        """
        if not self.private_key_path.exists():
            raise KeyNotFoundError(f"Private key not found: {self.private_key_path}")
        if not self.public_key_path.exists():
            raise KeyNotFoundError(f"Public key not found: {self.public_key_path}")
        if not self.key_id_path.exists():
            raise KeyNotFoundError(f"Key ID not found: {self.key_id_path}")
        
        try:
            # Load private key
            private_key_bytes = self.private_key_path.read_bytes()
            private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
            
            # Load public key
            public_key_bytes = self.public_key_path.read_bytes()
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            
            # Load key ID
            key_id = self.key_id_path.read_text().strip()
            
            # Verify key ID matches public key
            computed_key_id = hashlib.sha256(public_key_bytes).hexdigest()
            if computed_key_id != key_id:
                raise KeyManagerError(f"Key ID mismatch: stored={key_id}, computed={computed_key_id}")
            
            return private_key, public_key, key_id
            
        except Exception as e:
            raise KeyManagerError(f"Failed to load keypair: {e}") from e
    
    def get_or_create_keypair(self) -> Tuple[Ed25519PrivateKey, Ed25519PublicKey, str]:
        """
        Get existing keypair or create new one if it doesn't exist.
        
        Returns:
            Tuple of (private_key, public_key, key_id)
        """
        try:
            return self.load_keypair()
        except KeyNotFoundError:
            # Generate and save new keypair
            private_key, public_key, key_id = self.generate_keypair()
            self.save_keypair(private_key, public_key, key_id)
            return private_key, public_key, key_id
    
    def get_public_key(self) -> Ed25519PublicKey:
        """
        Get public key only (for verification).
        
        Returns:
            Ed25519 public key
        
        Raises:
            KeyNotFoundError: If public key file is not found
            KeyManagerError: If loading fails
        """
        if not self.public_key_path.exists():
            raise KeyNotFoundError(f"Public key not found: {self.public_key_path}")
        
        try:
            public_key_bytes = self.public_key_path.read_bytes()
            return Ed25519PublicKey.from_public_bytes(public_key_bytes)
        except Exception as e:
            raise KeyManagerError(f"Failed to load public key: {e}") from e
    
    def get_key_id(self) -> str:
        """
        Get key ID (SHA256 hash of public key).
        
        Returns:
            Key identifier as hex string
        
        Raises:
            KeyNotFoundError: If key ID file is not found
        """
        if not self.key_id_path.exists():
            raise KeyNotFoundError(f"Key ID not found: {self.key_id_path}")
        
        return self.key_id_path.read_text().strip()
    
    def export_public_key_base64(self) -> str:
        """
        Export public key as base64-encoded string.
        
        Returns:
            Base64-encoded public key
        
        Raises:
            KeyNotFoundError: If public key file is not found
        """
        public_key = self.get_public_key()
        public_key_bytes = public_key.public_bytes_raw()
        return base64.b64encode(public_key_bytes).decode('ascii')
    
    def keypair_exists(self) -> bool:
        """
        Check if keypair exists.
        
        Returns:
            True if all key files exist, False otherwise
        """
        return (
            self.private_key_path.exists() and
            self.public_key_path.exists() and
            self.key_id_path.exists()
        )
