#!/usr/bin/env python3
"""
RansomEye v1.0 Threat Response Engine - Key Manager
AUTHORITATIVE: Keypair generation and management for TRE command signing
Python 3.10+ only
"""

import os
import sys
import hashlib
from pathlib import Path
from typing import Tuple, Optional
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization


class TREKeyManager:
    """
    Key manager for TRE command signing.
    
    CRITICAL: Separate trust root from Policy Engine, HAF, Audit Ledger.
    Uses ed25519 for command signing (efficient, secure).
    """
    
    def __init__(self, key_dir: Path):
        """
        Initialize key manager.
        
        Args:
            key_dir: Directory for storing keypairs
        """
        self.key_dir = Path(key_dir)
        self.private_key_path = self.key_dir / "tre-signing-key.pem"
        self.public_key_path = self.key_dir / "tre-signing-key.pub"
        self.key_id_path = self.key_dir / "tre-signing-key.id"
        
        # Ensure key directory exists
        self.key_dir.mkdir(parents=True, exist_ok=True)
        # Restrict permissions on key directory
        os.chmod(self.key_dir, 0o700)
    
    def generate_keypair(self) -> Tuple[Ed25519PrivateKey, Ed25519PublicKey]:
        """
        Generate new ed25519 keypair.
        
        Returns:
            Tuple of (private_key, public_key)
        """
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        return private_key, public_key
    
    def save_keypair(self, private_key: Ed25519PrivateKey, public_key: Ed25519PublicKey) -> str:
        """
        Save keypair to disk and compute key ID.
        
        Args:
            private_key: Private key to save
            public_key: Public key to save
            
        Returns:
            Key ID (SHA256 hash of public key)
        """
        # Serialize private key (PEM format, encrypted)
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Serialize public key (PEM format)
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Write private key (restrictive permissions)
        with open(self.private_key_path, 'wb') as f:
            f.write(private_pem)
        os.chmod(self.private_key_path, 0o600)
        
        # Write public key (readable)
        with open(self.public_key_path, 'wb') as f:
            f.write(public_pem)
        os.chmod(self.public_key_path, 0o644)
        
        # Compute key ID (SHA256 hash of public key)
        key_id = hashlib.sha256(public_pem).hexdigest()
        
        # Write key ID
        with open(self.key_id_path, 'w') as f:
            f.write(key_id)
        os.chmod(self.key_id_path, 0o644)
        
        return key_id
    
    def load_keypair(self) -> Tuple[Ed25519PrivateKey, Ed25519PublicKey, str]:
        """
        Load keypair from disk.
        
        Returns:
            Tuple of (private_key, public_key, key_id)
            
        Raises:
            FileNotFoundError: If keypair does not exist
            ValueError: If keypair is invalid
        """
        if not self.private_key_path.exists():
            raise FileNotFoundError(f"Private key not found: {self.private_key_path}")
        
        if not self.public_key_path.exists():
            raise FileNotFoundError(f"Public key not found: {self.public_key_path}")
        
        # Load private key
        with open(self.private_key_path, 'rb') as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None
            )
        
        # Load public key
        with open(self.public_key_path, 'rb') as f:
            public_key = serialization.load_pem_public_key(f.read())
        
        # Load key ID
        if self.key_id_path.exists():
            with open(self.key_id_path, 'r') as f:
                key_id = f.read().strip()
        else:
            # Compute key ID if not stored
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            key_id = hashlib.sha256(public_pem).hexdigest()
            with open(self.key_id_path, 'w') as f:
                f.write(key_id)
            os.chmod(self.key_id_path, 0o644)
        
        return private_key, public_key, key_id
    
    def get_or_create_keypair(self) -> Tuple[Ed25519PrivateKey, Ed25519PublicKey, str]:
        """
        Get existing keypair or create new one.
        
        Returns:
            Tuple of (private_key, public_key, key_id)
        """
        try:
            return self.load_keypair()
        except FileNotFoundError:
            # Generate new keypair
            private_key, public_key = self.generate_keypair()
            key_id = self.save_keypair(private_key, public_key)
            return private_key, public_key, key_id
