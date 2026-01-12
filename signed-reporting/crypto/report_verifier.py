#!/usr/bin/env python3
"""
RansomEye Signed Reporting Engine - Report Verifier
AUTHORITATIVE: Offline verification of signed reports
"""

import base64
from pathlib import Path
from typing import bytes as BytesType


class VerificationError(Exception):
    """Base exception for verification errors."""
    pass


class ReportVerifier:
    """
    Offline verification of signed reports.
    
    Properties:
    - Deterministic: Same input always produces same verification result
    - Offline: No network or external dependencies
    - Used by auditors / courts
    """
    
    def __init__(self, public_key_path: Path):
        """
        Initialize report verifier.
        
        Args:
            public_key_path: Path to ed25519 public key file
        """
        self.public_key_path = Path(public_key_path)
        self.public_key = None
        
        if not self.public_key_path.exists():
            raise VerificationError(f"Public key file not found: {public_key_path}")
        
        self._load_public_key()
    
    def _load_public_key(self) -> None:
        """
        Load ed25519 public key from file.
        
        Raises:
            VerificationError: If key loading fails
        """
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend
            
            public_key_bytes = self.public_key_path.read_bytes()
            self.public_key = serialization.load_pem_public_key(
                public_key_bytes,
                backend=default_backend()
            )
            
        except Exception as e:
            raise VerificationError(f"Failed to load public key: {e}") from e
    
    def verify_signature(self, content: BytesType, signature: str) -> bool:
        """
        Verify signature against content.
        
        Args:
            content: Report content as bytes
            signature: Base64-encoded signature
        
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            signature_bytes = base64.b64decode(signature.encode('ascii'))
            self.public_key.verify(signature_bytes, content)
            return True
        except Exception as e:
            return False
