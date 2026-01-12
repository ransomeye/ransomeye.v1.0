#!/usr/bin/env python3
"""
RansomEye Global Validator - Report Verifier
AUTHORITATIVE: ed25519 signature verification for validator reports
"""

import hashlib
import base64
from typing import Dict, Any
import json

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False
    Ed25519PublicKey = None
    InvalidSignature = Exception


class ValidatorVerifierError(Exception):
    """Base exception for validator verification errors."""
    pass


class ValidatorSignatureVerificationError(ValidatorVerifierError):
    """Raised when signature verification fails."""
    pass


class ValidatorHashMismatchError(ValidatorVerifierError):
    """Raised when report hash doesn't match calculated hash."""
    pass


class ValidatorVerifier:
    """
    Verifies validator reports using ed25519.
    
    Verification process:
    1. Calculate report_hash from canonical JSON
    2. Verify report_hash matches stored report_hash
    3. Verify signature of report_hash using public key
    """
    
    def __init__(self, public_key: Ed25519PublicKey):
        """
        Initialize validator verifier.
        
        Args:
            public_key: Ed25519 public key for verification
        """
        if not _CRYPTO_AVAILABLE:
            raise ValidatorVerifierError("cryptography library not available. Install with: pip install cryptography")
        
        self.public_key = public_key
    
    def canonical_json(self, report: Dict[str, Any]) -> str:
        """
        Generate canonical JSON representation of report (excluding report_hash and signature).
        
        Args:
            report: Validation report dictionary
        
        Returns:
            Canonical JSON string (sorted keys, no whitespace)
        """
        # Create copy without report_hash and signature
        report_copy = {k: v for k, v in report.items() if k not in ('report_hash', 'signature')}
        
        # Sort keys for deterministic serialization
        sorted_keys = sorted(report_copy.keys())
        canonical_dict = {k: report_copy[k] for k in sorted_keys}
        
        # Serialize to JSON (compact, no whitespace)
        return json.dumps(canonical_dict, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    
    def calculate_report_hash(self, report: Dict[str, Any]) -> str:
        """
        Calculate SHA256 hash of canonical JSON report.
        
        Args:
            report: Validation report dictionary
        
        Returns:
            SHA256 hash as hex string
        """
        canonical = self.canonical_json(report)
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    
    def verify_report_hash(self, report: Dict[str, Any]) -> bool:
        """
        Verify that report_hash matches calculated hash.
        
        Args:
            report: Validation report dictionary
        
        Returns:
            True if hash matches
        
        Raises:
            ValidatorHashMismatchError: If hash doesn't match
        """
        stored_hash = report.get('report_hash')
        if not stored_hash:
            raise ValidatorHashMismatchError("report_hash is missing")
        
        calculated_hash = self.calculate_report_hash(report)
        
        if stored_hash != calculated_hash:
            raise ValidatorHashMismatchError(
                f"Hash mismatch: stored={stored_hash}, calculated={calculated_hash}"
            )
        
        return True
    
    def verify_signature(self, report: Dict[str, Any]) -> bool:
        """
        Verify ed25519 signature of report.
        
        Args:
            report: Validation report dictionary
        
        Returns:
            True if signature is valid
        
        Raises:
            ValidatorSignatureVerificationError: If signature verification fails
        """
        report_hash = report.get('report_hash')
        signature = report.get('signature')
        
        if not report_hash:
            raise ValidatorSignatureVerificationError("report_hash is missing")
        if not signature:
            raise ValidatorSignatureVerificationError("signature is missing")
        
        try:
            # Decode signature from base64
            signature_bytes = base64.b64decode(signature)
            
            # Verify signature
            hash_bytes = bytes.fromhex(report_hash)
            self.public_key.verify(signature_bytes, hash_bytes)
            
            return True
            
        except InvalidSignature as e:
            raise ValidatorSignatureVerificationError(f"Invalid signature: {e}") from e
        except Exception as e:
            raise ValidatorSignatureVerificationError(f"Signature verification failed: {e}") from e
    
    def verify_report(self, report: Dict[str, Any]) -> bool:
        """
        Verify a validation report (hash and signature).
        
        Args:
            report: Validation report dictionary
        
        Returns:
            True if report is valid
        
        Raises:
            ValidatorVerifierError: If verification fails
        """
        # Verify report hash
        self.verify_report_hash(report)
        
        # Verify signature
        self.verify_signature(report)
        
        return True
