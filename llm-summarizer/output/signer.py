#!/usr/bin/env python3
"""
RansomEye LLM Summarizer - Output Signer
AUTHORITATIVE: ed25519 output signing and verification
"""

import hashlib
from typing import Dict, Any, Optional
from pathlib import Path

try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    from cryptography.exceptions import InvalidSignature
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False


class OutputSignerError(Exception):
    """Base exception for output signer errors."""
    pass


class SignatureVerificationError(OutputSignerError):
    """Raised when signature verification fails."""
    pass


class OutputSigner:
    """
    Output hash calculation and ed25519 signing.
    
    Properties:
    - Deterministic: Same output always produces same hash
    - Cryptographic: Uses ed25519 for signing
    - Fail-closed: Signing failures cause rejection
    """
    
    def __init__(self, private_key_path: Optional[Path] = None, key_id: Optional[str] = None):
        """
        Initialize output signer.
        
        Args:
            private_key_path: Path to ed25519 private key file
            key_id: Signing key identifier
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            raise OutputSignerError("cryptography library not available. Install with: pip install cryptography")
        
        self.key_id = key_id or "llm-summarizer-signing-key"
        self.private_key = None
        
        if private_key_path:
            self._load_private_key(private_key_path)
    
    def _load_private_key(self, key_path: Path) -> None:
        """Load ed25519 private key from file."""
        if not key_path.exists():
            raise OutputSignerError(f"Private key file not found: {key_path}")
        
        try:
            with open(key_path, 'rb') as f:
                key_data = f.read()
            self.private_key = serialization.load_pem_private_key(key_data, password=None)
        except Exception as e:
            raise OutputSignerError(f"Failed to load private key: {e}") from e
    
    def calculate_output_hash(self, generated_text: str) -> str:
        """
        Calculate SHA256 hash of generated text.
        
        Args:
            generated_text: Generated text to hash
        
        Returns:
            SHA256 hash (64 hex characters)
        """
        if not isinstance(generated_text, str):
            raise OutputSignerError(f"Generated text must be string, got {type(generated_text)}")
        
        hash_obj = hashlib.sha256(generated_text.encode('utf-8'))
        return hash_obj.hexdigest()
    
    def sign_hash(self, output_hash: str) -> str:
        """
        Sign output hash with ed25519.
        
        Args:
            output_hash: SHA256 hash to sign
        
        Returns:
            Base64-encoded signature
        
        Raises:
            OutputSignerError: If signing fails
        """
        if self.private_key is None:
            raise OutputSignerError("Private key not loaded. Cannot sign.")
        
        try:
            signature_bytes = self.private_key.sign(output_hash.encode('utf-8'))
            import base64
            signature = base64.b64encode(signature_bytes).decode('utf-8')
            return signature
        except Exception as e:
            raise OutputSignerError(f"Signing failed: {e}") from e
    
    def sign_output(self, generated_text: str) -> Dict[str, Any]:
        """
        Calculate hash and sign output.
        
        Args:
            generated_text: Generated text to sign
        
        Returns:
            Dictionary with:
            - output_hash: SHA256 hash
            - signature: ed25519 signature
            - signing_key_id: Key identifier
        """
        output_hash = self.calculate_output_hash(generated_text)
        signature = self.sign_hash(output_hash)
        
        return {
            'output_hash': output_hash,
            'signature': signature,
            'signing_key_id': self.key_id
        }
    
    @staticmethod
    def verify_signature(
        output_hash: str,
        signature: str,
        public_key_path: Path
    ) -> bool:
        """
        Verify output signature.
        
        Args:
            output_hash: SHA256 hash that was signed
            signature: Base64-encoded signature
            public_key_path: Path to ed25519 public key file
        
        Returns:
            True if signature is valid, False otherwise
        
        Raises:
            SignatureVerificationError: If verification fails
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            raise OutputSignerError("cryptography library not available")
        
        if not public_key_path.exists():
            raise SignatureVerificationError(f"Public key file not found: {public_key_path}")
        
        try:
            with open(public_key_path, 'rb') as f:
                key_data = f.read()
            public_key = serialization.load_pem_public_key(key_data)
            
            import base64
            signature_bytes = base64.b64decode(signature)
            
            public_key.verify(signature_bytes, output_hash.encode('utf-8'))
            return True
        except InvalidSignature:
            return False
        except Exception as e:
            raise SignatureVerificationError(f"Signature verification failed: {e}") from e
