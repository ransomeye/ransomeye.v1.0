#!/usr/bin/env python3
"""
RansomEye Audit Ledger - Verifier
AUTHORITATIVE: ed25519 signature verification for audit ledger entries
"""

import hashlib
import base64
from typing import Dict, Any, Optional
import json

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False
    Ed25519PublicKey = None
    InvalidSignature = Exception


class VerificationError(Exception):
    """Base exception for verification errors."""
    pass


class SignatureVerificationError(VerificationError):
    """Raised when signature verification fails."""
    pass


class HashMismatchError(VerificationError):
    """Raised when entry hash doesn't match calculated hash."""
    pass


class Verifier:
    """
    Verifies audit ledger entries using ed25519.
    
    Verification process:
    1. Calculate entry_hash from canonical JSON
    2. Verify entry_hash matches stored entry_hash
    3. Verify signature of entry_hash using public key
    4. Verify hash chain (prev_entry_hash matches previous entry's entry_hash)
    """
    
    def __init__(self, public_key: Ed25519PublicKey):
        """
        Initialize verifier.
        
        Args:
            public_key: Ed25519 public key for verification
        """
        if not _CRYPTO_AVAILABLE:
            raise VerificationError("cryptography library not available. Install with: pip install cryptography")
        
        self.public_key = public_key
    
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
    
    def verify_entry_hash(self, entry: Dict[str, Any]) -> bool:
        """
        Verify that entry_hash matches calculated hash.
        
        Args:
            entry: Ledger entry dictionary
        
        Returns:
            True if hash matches, False otherwise
        
        Raises:
            HashMismatchError: If hash doesn't match
        """
        stored_hash = entry.get('entry_hash')
        if not stored_hash:
            raise HashMismatchError("entry_hash is missing")
        
        calculated_hash = self.calculate_entry_hash(entry)
        
        if stored_hash != calculated_hash:
            raise HashMismatchError(
                f"Hash mismatch: stored={stored_hash}, calculated={calculated_hash}"
            )
        
        return True
    
    def verify_signature(self, entry: Dict[str, Any]) -> bool:
        """
        Verify ed25519 signature of entry.
        
        Args:
            entry: Ledger entry dictionary
        
        Returns:
            True if signature is valid, False otherwise
        
        Raises:
            SignatureVerificationError: If signature verification fails
        """
        entry_hash = entry.get('entry_hash')
        signature = entry.get('signature')
        
        if not entry_hash:
            raise SignatureVerificationError("entry_hash is missing")
        if not signature:
            raise SignatureVerificationError("signature is missing")
        
        try:
            # Decode signature from base64
            signature_bytes = base64.b64decode(signature)
            
            # Verify signature
            hash_bytes = bytes.fromhex(entry_hash)
            self.public_key.verify(signature_bytes, hash_bytes)
            
            return True
            
        except InvalidSignature as e:
            raise SignatureVerificationError(f"Invalid signature: {e}") from e
        except Exception as e:
            raise SignatureVerificationError(f"Signature verification failed: {e}") from e
    
    def verify_hash_chain(self, current_entry: Dict[str, Any], prev_entry: Optional[Dict[str, Any]]) -> bool:
        """
        Verify hash chain integrity.
        
        Args:
            current_entry: Current ledger entry
            prev_entry: Previous ledger entry (None for first entry)
        
        Returns:
            True if hash chain is valid
        
        Raises:
            VerificationError: If hash chain is broken
        """
        current_prev_hash = current_entry.get('prev_entry_hash', '')
        
        if prev_entry is None:
            # First entry should have empty prev_entry_hash
            if current_prev_hash != '':
                raise VerificationError(
                    f"First entry has non-empty prev_entry_hash: {current_prev_hash}"
                )
        else:
            # Verify prev_entry_hash matches previous entry's entry_hash
            prev_entry_hash = prev_entry.get('entry_hash')
            if not prev_entry_hash:
                raise VerificationError("Previous entry missing entry_hash")
            
            if current_prev_hash != prev_entry_hash:
                raise VerificationError(
                    f"Hash chain broken: current.prev_entry_hash={current_prev_hash}, "
                    f"prev.entry_hash={prev_entry_hash}"
                )
        
        return True
    
    def verify_entry(self, entry: Dict[str, Any], prev_entry: Optional[Dict[str, Any]] = None) -> bool:
        """
        Verify a ledger entry (hash, signature, and hash chain).
        
        Args:
            entry: Ledger entry dictionary
            prev_entry: Previous ledger entry (None for first entry)
        
        Returns:
            True if entry is valid
        
        Raises:
            VerificationError: If verification fails
        """
        # Verify entry hash
        self.verify_entry_hash(entry)
        
        # Verify signature
        self.verify_signature(entry)
        
        # Verify hash chain
        self.verify_hash_chain(entry, prev_entry)
        
        return True
