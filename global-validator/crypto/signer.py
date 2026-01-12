#!/usr/bin/env python3
"""
RansomEye Global Validator - Report Signer
AUTHORITATIVE: ed25519 signing for validator reports
"""

import hashlib
import base64
from typing import Dict, Any, Tuple
import json

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.backends import default_backend
    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False
    Ed25519PrivateKey = None


class ValidatorSignerError(Exception):
    """Base exception for validator signing errors."""
    pass


class ValidatorSigner:
    """
    Signs validator reports using ed25519.
    
    Signing process:
    1. Create canonical JSON representation (excluding report_hash and signature)
    2. Calculate SHA256 hash of canonical JSON
    3. Sign hash with ed25519 private key
    4. Encode signature as base64
    """
    
    def __init__(self, private_key: Ed25519PrivateKey, key_id: str):
        """
        Initialize validator signer.
        
        Args:
            private_key: Ed25519 private key for signing
            key_id: Key identifier (SHA256 hash of public key)
        """
        if not _CRYPTO_AVAILABLE:
            raise ValidatorSignerError("cryptography library not available. Install with: pip install cryptography")
        
        self.private_key = private_key
        self.key_id = key_id
    
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
    
    def sign_report(self, report: Dict[str, Any]) -> Tuple[str, str]:
        """
        Sign a validation report.
        
        Process:
        1. Calculate report_hash from canonical JSON
        2. Sign report_hash with ed25519 private key
        3. Encode signature as base64
        
        Args:
            report: Validation report dictionary (must not include report_hash or signature)
        
        Returns:
            Tuple of (report_hash, signature)
            report_hash: SHA256 hash of canonical JSON
            signature: Base64-encoded ed25519 signature
        """
        # Calculate report hash
        report_hash = self.calculate_report_hash(report)
        
        # Sign the hash
        hash_bytes = bytes.fromhex(report_hash)
        signature_bytes = self.private_key.sign(hash_bytes)
        
        # Encode signature as base64
        signature = base64.b64encode(signature_bytes).decode('ascii')
        
        return report_hash, signature
    
    def sign_complete_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sign a validation report and return complete report with report_hash and signature.
        
        Args:
            report: Validation report dictionary (must not include report_hash or signature)
        
        Returns:
            Complete report with report_hash, signature, and signing_key_id added
        """
        report_hash, signature = self.sign_report(report)
        
        # Add hash and signature to report
        report['report_hash'] = report_hash
        report['signature'] = signature
        report['signing_key_id'] = self.key_id
        
        return report
