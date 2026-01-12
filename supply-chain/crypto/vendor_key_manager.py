#!/usr/bin/env python3
"""
RansomEye Supply-Chain Signing & Verification Framework - Vendor Key Manager
AUTHORITATIVE: Management of vendor signing keys (ed25519)
"""

import hashlib
from pathlib import Path
from typing import Tuple, Optional
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


class VendorKeyManagerError(Exception):
    """Base exception for vendor key manager errors."""
    pass


class VendorKeyManager:
    """
    Management of vendor signing keys for supply-chain integrity.
    
    Properties:
    - Separate keys: Independent from Audit Ledger, Global Validator, Reporting, Model Registry
    - Offline storage: Keys stored offline (documented)
    - ed25519: Fast, deterministic, widely supported
    - Export-verifiable: Keys can be exported and verified offline
    """
    
    def __init__(self, key_dir: Path):
        """
        Initialize vendor key manager.
        
        Args:
            key_dir: Directory containing vendor signing keys
        """
        self.key_dir = Path(key_dir)
        self.key_dir.mkdir(parents=True, exist_ok=True)
    
    def get_or_create_keypair(self, key_id: str) -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey, str]:
        """
        Get or create vendor signing keypair.
        
        Args:
            key_id: Key identifier (e.g., vendor-release-key-1)
        
        Returns:
            Tuple of (private_key, public_key, key_id)
        """
        private_key_path = self.key_dir / f"{key_id}.pem"
        public_key_path = self.key_dir / f"{key_id}.pub"
        
        if private_key_path.exists() and public_key_path.exists():
            # Load existing keypair
            return self._load_keypair(private_key_path, public_key_path, key_id)
        else:
            # Generate new keypair
            return self._generate_keypair(private_key_path, public_key_path, key_id)
    
    def _generate_keypair(
        self,
        private_key_path: Path,
        public_key_path: Path,
        key_id: str
    ) -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey, str]:
        """
        Generate new ed25519 keypair.
        
        Args:
            private_key_path: Path to save private key
            public_key_path: Path to save public key
            key_id: Key identifier
        
        Returns:
            Tuple of (private_key, public_key, key_id)
        
        Raises:
            VendorKeyManagerError: If key generation fails
        """
        try:
            private_key = ed25519.Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
            
            # Save private key
            private_key_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            private_key_path.write_bytes(private_key_bytes)
            
            # Save public key
            public_key_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            public_key_path.write_bytes(public_key_bytes)
            
            return (private_key, public_key, key_id)
            
        except Exception as e:
            raise VendorKeyManagerError(f"Failed to generate keypair: {e}") from e
    
    def _load_keypair(
        self,
        private_key_path: Path,
        public_key_path: Path,
        key_id: str
    ) -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey, str]:
        """
        Load existing ed25519 keypair.
        
        Args:
            private_key_path: Path to private key file
            public_key_path: Path to public key file
            key_id: Key identifier
        
        Returns:
            Tuple of (private_key, public_key, key_id)
        
        Raises:
            VendorKeyManagerError: If key loading fails
        """
        try:
            # Load private key
            private_key_bytes = private_key_path.read_bytes()
            private_key = serialization.load_pem_private_key(
                private_key_bytes,
                password=None,
                backend=default_backend()
            )
            
            # Load public key
            public_key_bytes = public_key_path.read_bytes()
            public_key = serialization.load_pem_public_key(
                public_key_bytes,
                backend=default_backend()
            )
            
            return (private_key, public_key, key_id)
            
        except Exception as e:
            raise VendorKeyManagerError(f"Failed to load keypair: {e}") from e
    
    def get_public_key(self, key_id: str) -> Optional[ed25519.Ed25519PublicKey]:
        """
        Get public key by ID.
        
        Args:
            key_id: Key identifier
        
        Returns:
            Public key, or None if not found
        """
        public_key_path = self.key_dir / f"{key_id}.pub"
        
        if not public_key_path.exists():
            return None
        
        try:
            public_key_bytes = public_key_path.read_bytes()
            return serialization.load_pem_public_key(
                public_key_bytes,
                backend=default_backend()
            )
        except Exception as e:
            raise VendorKeyManagerError(f"Failed to load public key: {e}") from e
    
    def export_public_key(self, key_id: str) -> bytes:
        """
        Export public key as PEM-encoded bytes.
        
        Args:
            key_id: Key identifier
        
        Returns:
            Public key as PEM-encoded bytes
        
        Raises:
            VendorKeyManagerError: If key not found or export fails
        """
        public_key = self.get_public_key(key_id)
        if not public_key:
            raise VendorKeyManagerError(f"Public key not found: {key_id}")
        
        try:
            return public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        except Exception as e:
            raise VendorKeyManagerError(f"Failed to export public key: {e}") from e
