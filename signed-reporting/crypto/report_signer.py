#!/usr/bin/env python3
"""
RansomEye Signed Reporting Engine - Report Signer
AUTHORITATIVE: Cryptographic signing of reports using ed25519
"""

import base64
from pathlib import Path
from typing import Optional
import os


class SigningError(Exception):
    """Base exception for signing errors."""
    pass


class ReportSigner:
    """
    Cryptographic signing of reports using ed25519.
    
    Choice: ed25519
    Justification:
    - Fast signing and verification
    - Small signature size (64 bytes)
    - Strong security (128-bit security level)
    - Deterministic (RFC 8032)
    - Widely supported in regulatory contexts
    - Separate from Audit Ledger and Global Validator keys
    
    Properties:
    - Deterministic: Same input always produces same signature
    - Export-verifiable: Keys can be exported and verified offline
    - Separate keypair: Independent from other subsystems
    """
    
    def __init__(self, private_key_path: Path, key_id: str):
        """
        Initialize report signer.
        
        Args:
            private_key_path: Path to ed25519 private key file
            key_id: Signing key identifier
        """
        self.private_key_path = Path(private_key_key_path)
        self.key_id = key_id
        
        # Load or generate private key
        if not self.private_key_path.exists():
            self._generate_keypair()
        else:
            self._load_private_key()
    
    def _generate_keypair(self) -> None:
        """
        Generate ed25519 keypair.
        
        Raises:
            SigningError: If key generation fails
        """
        try:
            # Generate ed25519 keypair using cryptography library
            from cryptography.hazmat.primitives.asymmetric import ed25519
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend
            
            private_key = ed25519.Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
            
            # Save private key
            private_key_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            self.private_key_path.parent.mkdir(parents=True, exist_ok=True)
            self.private_key_path.write_bytes(private_key_bytes)
            
            # Save public key
            public_key_path = self.private_key_path.parent / f"{self.private_key_path.stem}.pub"
            public_key_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            public_key_path.write_bytes(public_key_bytes)
            
            self.private_key = private_key
            
        except Exception as e:
            raise SigningError(f"Failed to generate keypair: {e}") from e
    
    def _load_private_key(self) -> None:
        """
        Load ed25519 private key from file.
        
        Raises:
            SigningError: If key loading fails
        """
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend
            
            private_key_bytes = self.private_key_path.read_bytes()
            self.private_key = serialization.load_pem_private_key(
                private_key_bytes,
                password=None,
                backend=default_backend()
            )
            
        except Exception as e:
            raise SigningError(f"Failed to load private key: {e}") from e
    
    def sign_content(self, content: bytes) -> str:
        """
        Sign content using ed25519.
        
        Args:
            content: Content to sign (as bytes)
        
        Returns:
            Base64-encoded signature
        """
        try:
            signature = self.private_key.sign(content)
            return base64.b64encode(signature).decode('ascii')
        except Exception as e:
            raise SigningError(f"Failed to sign content: {e}") from e
    
    def get_public_key_bytes(self) -> bytes:
        """
        Get public key as bytes for export.
        
        Returns:
            Public key as PEM-encoded bytes
        """
        try:
            from cryptography.hazmat.primitives import serialization
            
            public_key = self.private_key.public_key()
            return public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        except Exception as e:
            raise SigningError(f"Failed to export public key: {e}") from e
