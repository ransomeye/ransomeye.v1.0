#!/usr/bin/env python3
"""
RansomEye Supply-Chain Signing & Verification Framework - Persistent Signing Authority
AUTHORITATIVE: Persistent vendor signing authority (no ephemeral keys)
Phase-9: Replace ephemeral CI keys with persistent authority
"""

import os
import json
import base64
from pathlib import Path
from typing import Optional, Tuple
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .key_registry import KeyRegistry, KeyRegistryError, KeyType, KeyStatus
from .vendor_key_manager import VendorKeyManagerError


class PersistentSigningAuthorityError(Exception):
    """Base exception for persistent signing authority errors."""
    pass


class EphemeralKeyError(PersistentSigningAuthorityError):
    """Raised when ephemeral key generation is attempted."""
    pass


class PersistentSigningAuthority:
    """
    Persistent vendor signing authority.
    
    Properties:
    - No ephemeral keys: CI cannot generate keys
    - Encrypted storage: Private keys encrypted at rest
    - Key registry: All keys tracked with lifecycle
    - Revocation support: Revoked keys fail verification
    - Offline verification: Public keys available independently
    
    Key Storage Model: Option B (Encrypted Software Vault)
    - Private keys encrypted with passphrase-derived key
    - Keys stored in encrypted vault directory
    - Manual unlock ceremony required for key access
    """
    
    def __init__(
        self,
        vault_dir: Path,
        registry_path: Path,
        unlock_passphrase: Optional[str] = None
    ):
        """
        Initialize persistent signing authority.
        
        Args:
            vault_dir: Directory containing encrypted key vault
            registry_path: Path to key registry JSON file
            unlock_passphrase: Passphrase to unlock encrypted keys (from env or manual)
        
        Raises:
            PersistentSigningAuthorityError: If initialization fails
        """
        self.vault_dir = Path(vault_dir)
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self.registry = KeyRegistry(registry_path)
        
        # Get passphrase from environment or parameter
        self.unlock_passphrase = unlock_passphrase or os.environ.get('RANSOMEYE_KEY_VAULT_PASSPHRASE')
        if not self.unlock_passphrase:
            raise PersistentSigningAuthorityError(
                "Key vault passphrase required. Set RANSOMEYE_KEY_VAULT_PASSPHRASE environment variable."
            )
    
    def _derive_key(self, passphrase: str, salt: bytes) -> bytes:
        """Derive encryption key from passphrase using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        return kdf.derive(passphrase.encode('utf-8'))
    
    def _encrypt_private_key(
        self,
        private_key: ed25519.Ed25519PrivateKey,
        passphrase: str
    ) -> Tuple[bytes, bytes]:
        """
        Encrypt private key with passphrase.
        
        Returns:
            Tuple of (encrypted_key_bytes, salt)
        """
        # Generate salt
        salt = os.urandom(16)
        
        # Derive encryption key
        key = self._derive_key(passphrase, salt)
        
        # Serialize private key
        private_key_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Encrypt with ChaCha20Poly1305
        cipher = ChaCha20Poly1305(key)
        nonce = os.urandom(12)
        encrypted = cipher.encrypt(nonce, private_key_bytes, None)
        
        # Combine nonce + encrypted data
        encrypted_with_nonce = nonce + encrypted
        
        return encrypted_with_nonce, salt
    
    def _decrypt_private_key(
        self,
        encrypted_key_bytes: bytes,
        salt: bytes,
        passphrase: str
    ) -> ed25519.Ed25519PrivateKey:
        """
        Decrypt private key with passphrase.
        
        Returns:
            Decrypted private key
        """
        # Derive encryption key
        key = self._derive_key(passphrase, salt)
        
        # Extract nonce and encrypted data
        nonce = encrypted_key_bytes[:12]
        encrypted = encrypted_key_bytes[12:]
        
        # Decrypt
        cipher = ChaCha20Poly1305(key)
        private_key_bytes = cipher.decrypt(nonce, encrypted, None)
        
        # Deserialize private key
        private_key = serialization.load_pem_private_key(
            private_key_bytes,
            password=None,
            backend=default_backend()
        )
        
        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
            raise PersistentSigningAuthorityError("Decrypted key is not ed25519")
        
        return private_key
    
    def get_signing_key(
        self,
        key_id: str,
        require_active: bool = True
    ) -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
        """
        Get signing key from persistent vault.
        
        Args:
            key_id: Key identifier
            require_active: If True, fail if key is not active
        
        Returns:
            Tuple of (private_key, public_key)
        
        Raises:
            PersistentSigningAuthorityError: If key not found, revoked, or decryption fails
            EphemeralKeyError: If ephemeral key generation attempted
        """
        # Check registry
        key_entry = self.registry.get_key(key_id)
        if not key_entry:
            raise PersistentSigningAuthorityError(
                f"Key not found in registry: {key_id}. "
                "Keys must be registered before use. Ephemeral key generation is forbidden."
            )
        
        # Check if key is active
        if require_active:
            if not self.registry.is_key_active(key_id):
                status = key_entry["status"]
                raise PersistentSigningAuthorityError(
                    f"Key {key_id} is not active (status: {status}). "
                    "Revoked, rotated, or compromised keys cannot be used for signing."
                )
        
        # Check revocation list
        if self.registry.is_revoked(key_id):
            raise PersistentSigningAuthorityError(
                f"Key {key_id} is revoked. Signatures from revoked keys are invalid."
            )
        
        # Load encrypted private key
        encrypted_key_path = self.vault_dir / f"{key_id}.encrypted"
        salt_path = self.vault_dir / f"{key_id}.salt"
        public_key_path = self.vault_dir / f"{key_id}.pub"
        
        if not encrypted_key_path.exists():
            raise PersistentSigningAuthorityError(
                f"Encrypted private key not found: {encrypted_key_path}. "
                "Key must be generated and stored in vault before use."
            )
        
        if not salt_path.exists():
            raise PersistentSigningAuthorityError(f"Salt file not found: {salt_path}")
        
        if not public_key_path.exists():
            raise PersistentSigningAuthorityError(f"Public key not found: {public_key_path}")
        
        # Load encrypted key and salt
        encrypted_key_bytes = encrypted_key_path.read_bytes()
        salt = salt_path.read_bytes()
        
        # Decrypt private key
        try:
            private_key = self._decrypt_private_key(
                encrypted_key_bytes,
                salt,
                self.unlock_passphrase
            )
        except Exception as e:
            raise PersistentSigningAuthorityError(
                f"Failed to decrypt private key {key_id}: {e}. "
                "Check that RANSOMEYE_KEY_VAULT_PASSPHRASE is correct."
            ) from e
        
        # Load public key
        public_key_bytes = public_key_path.read_bytes()
        public_key = serialization.load_pem_public_key(
            public_key_bytes,
            backend=default_backend()
        )
        
        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            raise PersistentSigningAuthorityError("Public key is not ed25519")
        
        return private_key, public_key
    
    def store_signing_key(
        self,
        key_id: str,
        private_key: ed25519.Ed25519PrivateKey,
        public_key: ed25519.Ed25519PublicKey,
        generation_date: str,
        generation_log_path: Optional[Path] = None
    ) -> None:
        """
        Store signing key in encrypted vault and register in registry.
        
        Args:
            key_id: Key identifier
            private_key: Private key to store
            public_key: Public key
            generation_date: ISO 8601 timestamp of key generation
            generation_log_path: Path to key generation ceremony log
        
        Raises:
            PersistentSigningAuthorityError: If key already exists or storage fails
        """
        # Check if key already exists
        if self.registry.get_key(key_id):
            raise PersistentSigningAuthorityError(f"Key already exists: {key_id}")
        
        # Encrypt and store private key
        encrypted_key_bytes, salt = self._encrypt_private_key(
            private_key,
            self.unlock_passphrase
        )
        
        encrypted_key_path = self.vault_dir / f"{key_id}.encrypted"
        salt_path = self.vault_dir / f"{key_id}.salt"
        public_key_path = self.vault_dir / f"{key_id}.pub"
        
        encrypted_key_path.write_bytes(encrypted_key_bytes)
        salt_path.write_bytes(salt)
        
        # Store public key (unencrypted)
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        public_key_path.write_bytes(public_key_bytes)
        
        # Compute public key fingerprint
        import hashlib
        fingerprint = hashlib.sha256(public_key_bytes).hexdigest()
        
        # Register key in registry
        self.registry.register_key(
            key_id=key_id,
            key_type=KeyType.SIGNING,
            public_key_fingerprint=fingerprint,
            generation_date=generation_date,
            generation_log_path=generation_log_path,
            parent_key_id=None  # Signing keys don't have parent (root key attests separately)
        )
    
    def get_public_key(self, key_id: str) -> ed25519.Ed25519PublicKey:
        """
        Get public key (no decryption required).
        
        Args:
            key_id: Key identifier
        
        Returns:
            Public key
        """
        public_key_path = self.vault_dir / f"{key_id}.pub"
        
        if not public_key_path.exists():
            raise PersistentSigningAuthorityError(f"Public key not found: {public_key_path}")
        
        public_key_bytes = public_key_path.read_bytes()
        public_key = serialization.load_pem_public_key(
            public_key_bytes,
            backend=default_backend()
        )
        
        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            raise PersistentSigningAuthorityError("Public key is not ed25519")
        
        return public_key
    
    def export_public_key_pem(self, key_id: str) -> bytes:
        """
        Export public key as PEM-encoded bytes.
        
        Args:
            key_id: Key identifier
        
        Returns:
            PEM-encoded public key bytes
        """
        public_key = self.get_public_key(key_id)
        return public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
