#!/usr/bin/env python3
"""
RansomEye Human Authority Framework - Human Key Manager
AUTHORITATIVE: Per-human keypair management (ed25519)
"""

import hashlib
from pathlib import Path
from typing import Tuple
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


class KeyManagerError(Exception):
    """Base exception for key manager errors."""
    pass


class HumanKeyManager:
    """
    Per-human keypair management.
    
    Properties:
    - Per-human keypairs: Each human has their own keypair
    - Separate trust root: Keys are separate from other subsystems
    - No shared keys: No keys shared between humans or subsystems
    - Deterministic key IDs: Key IDs are deterministic (SHA256 of public key)
    """
    
    def __init__(self, keys_dir: Path):
        """
        Initialize human key manager.
        
        Args:
            keys_dir: Directory for storing human keypairs
        """
        self.keys_dir = Path(keys_dir)
        self.keys_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_keypair(self, human_identifier: str) -> Tuple[Ed25519PrivateKey, Ed25519PublicKey, str]:
        """
        Generate new keypair for human.
        
        Args:
            human_identifier: Human identifier (username, email, etc.)
        
        Returns:
            Tuple of (private_key, public_key, key_id)
        """
        # Generate ed25519 keypair
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        
        # Calculate key ID (SHA256 of public key)
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        key_id = hashlib.sha256(public_key_bytes).hexdigest()
        
        # Save keypair
        self._save_keypair(human_identifier, private_key, public_key, key_id)
        
        return private_key, public_key, key_id
    
    def get_or_create_keypair(self, human_identifier: str) -> Tuple[Ed25519PrivateKey, Ed25519PublicKey, str]:
        """
        Get existing keypair or create new one.
        
        Args:
            human_identifier: Human identifier
        
        Returns:
            Tuple of (private_key, public_key, key_id)
        """
        private_key_path = self.keys_dir / f"{human_identifier}_private.pem"
        public_key_path = self.keys_dir / f"{human_identifier}_public.pem"
        
        if private_key_path.exists() and public_key_path.exists():
            return self._load_keypair(human_identifier)
        else:
            return self.generate_keypair(human_identifier)
    
    def _save_keypair(
        self,
        human_identifier: str,
        private_key: Ed25519PrivateKey,
        public_key: Ed25519PublicKey,
        key_id: str
    ) -> None:
        """Save keypair to disk."""
        private_key_path = self.keys_dir / f"{human_identifier}_private.pem"
        public_key_path = self.keys_dir / f"{human_identifier}_public.pem"
        
        # Serialize private key
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        private_key_path.write_bytes(private_key_pem)
        private_key_path.chmod(0o600)  # Restrict permissions
        
        # Serialize public key
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        public_key_path.write_bytes(public_key_pem)
        public_key_path.chmod(0o644)
    
    def _load_keypair(self, human_identifier: str) -> Tuple[Ed25519PrivateKey, Ed25519PublicKey, str]:
        """Load keypair from disk."""
        private_key_path = self.keys_dir / f"{human_identifier}_private.pem"
        public_key_path = self.keys_dir / f"{human_identifier}_public.pem"
        
        if not private_key_path.exists() or not public_key_path.exists():
            raise KeyManagerError(f"Keypair not found for human: {human_identifier}")
        
        # Load private key
        private_key_data = private_key_path.read_bytes()
        private_key = serialization.load_pem_private_key(
            private_key_data,
            password=None,
            backend=default_backend()
        )
        
        # Load public key
        public_key_data = public_key_path.read_bytes()
        public_key = serialization.load_pem_public_key(
            public_key_data,
            backend=default_backend()
        )
        
        # Calculate key ID
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        key_id = hashlib.sha256(public_key_bytes).hexdigest()
        
        return private_key, public_key, key_id
    
    def get_public_key(self, human_identifier: str) -> Tuple[Ed25519PublicKey, str]:
        """
        Get public key for human.
        
        Args:
            human_identifier: Human identifier
        
        Returns:
            Tuple of (public_key, key_id)
        """
        public_key_path = self.keys_dir / f"{human_identifier}_public.pem"
        
        if not public_key_path.exists():
            raise KeyManagerError(f"Public key not found for human: {human_identifier}")
        
        public_key_data = public_key_path.read_bytes()
        public_key = serialization.load_pem_public_key(
            public_key_data,
            backend=default_backend()
        )
        
        # Calculate key ID
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        key_id = hashlib.sha256(public_key_bytes).hexdigest()
        
        return public_key, key_id
