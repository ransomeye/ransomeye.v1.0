#!/usr/bin/env python3
"""
RansomEye Audit Ledger - Signer
AUTHORITATIVE: ed25519 signing for audit ledger entries
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


class SignerError(Exception):
    """Base exception for signing errors."""
    pass


class Signer:
    """
    Signs audit ledger entries using ed25519.
    
    Signing process:
    1. Create canonical JSON representation (excluding entry_hash and signature)
    2. Calculate SHA256 hash of canonical JSON
    3. Sign hash with ed25519 private key
    4. Encode signature as base64
    """
    
    def __init__(self, private_key: Ed25519PrivateKey, key_id: str):
        """
        Initialize signer.
        
        Args:
            private_key: Ed25519 private key for signing
            key_id: Key identifier (SHA256 hash of public key)
        """
        if not _CRYPTO_AVAILABLE:
            raise SignerError("cryptography library not available. Install with: pip install cryptography")
        
        self.private_key = private_key
        self.key_id = key_id
    
    def canonical_json(self, entry: Dict[str, Any]) -> str:
        """
        Generate canonical JSON representation of entry (excluding entry_hash and signature).
        
        Args:
            entry: Ledger entry dictionary
        
        Returns:
            Canonical JSON string (sorted keys, no whitespace)
        """
        # Create copy without entry_hash and signature
        entry_copy = {k: v for k, v in entry.items() if k not in ('entry_hash', 'signature')}
        
        # Sort keys for deterministic serialization
        sorted_keys = sorted(entry_copy.keys())
        canonical_dict = {k: entry_copy[k] for k in sorted_keys}
        
        # Serialize to JSON (compact, no whitespace)
        return json.dumps(canonical_dict, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    
    def calculate_entry_hash(self, entry: Dict[str, Any]) -> str:
        """
        Calculate SHA256 hash of canonical JSON entry.
        
        Args:
            entry: Ledger entry dictionary
        
        Returns:
            SHA256 hash as hex string
        """
        canonical = self.canonical_json(entry)
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    
    def sign_entry(self, entry: Dict[str, Any]) -> Tuple[str, str]:
        """
        Sign a ledger entry.
        
        Process:
        1. Calculate entry_hash from canonical JSON
        2. Sign entry_hash with ed25519 private key
        3. Encode signature as base64
        
        Args:
            entry: Ledger entry dictionary (must not include entry_hash or signature)
        
        Returns:
            Tuple of (entry_hash, signature)
            entry_hash: SHA256 hash of canonical JSON
            signature: Base64-encoded ed25519 signature
        """
        # Calculate entry hash
        entry_hash = self.calculate_entry_hash(entry)
        
        # Sign the hash
        hash_bytes = bytes.fromhex(entry_hash)
        signature_bytes = self.private_key.sign(hash_bytes)
        
        # Encode signature as base64
        signature = base64.b64encode(signature_bytes).decode('ascii')
        
        return entry_hash, signature
    
    def sign_complete_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sign a ledger entry and return complete entry with entry_hash and signature.
        
        Args:
            entry: Ledger entry dictionary (must not include entry_hash or signature)
        
        Returns:
            Complete entry with entry_hash, signature, and signing_key_id added
        """
        entry_hash, signature = self.sign_entry(entry)
        
        # Add hash and signature to entry
        entry['entry_hash'] = entry_hash
        entry['signature'] = signature
        entry['signing_key_id'] = self.key_id
        
        return entry
