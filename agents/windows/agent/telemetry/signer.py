#!/usr/bin/env python3
"""
RansomEye v1.0 Windows Agent - Telemetry Signer
AUTHORITATIVE: Cryptographic signing of event envelopes (ed25519)
"""

import os
import sys
import json
import hashlib
import base64
from typing import Dict, Any, Optional
from pathlib import Path

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    _logger = setup_logging('windows-agent-telemetry-signer')
except ImportError:
    import logging
    _logger = logging.getLogger('windows-agent-telemetry-signer')

# ed25519 signing
try:
    import nacl.signing
    import nacl.encoding
    _nacl_available = True
except ImportError:
    _nacl_available = False
    _logger.warning("PyNaCl not available - signing will be disabled")


class TelemetrySigner:
    """
    Signs event envelopes with ed25519.
    
    CRITICAL: All events must be signed before transmission.
    """
    
    def __init__(
        self,
        private_key_path: Optional[Path] = None,
        key_id: Optional[str] = None
    ):
        """
        Initialize telemetry signer.
        
        Args:
            private_key_path: Path to ed25519 private key file
            key_id: Key identifier (SHA256 hash of public key)
        """
        self.key_id = key_id
        self.signer = None
        
        if not _nacl_available:
            _logger.warning("PyNaCl not available - signing disabled")
            return
        
        if private_key_path and private_key_path.exists():
            try:
                # Load private key
                with open(private_key_path, 'rb') as f:
                    key_data = f.read()
                
                self.signer = nacl.signing.SigningKey(key_data)
                
                # Derive key_id from public key if not provided
                if not self.key_id:
                    public_key = self.signer.verify_key.encode()
                    self.key_id = hashlib.sha256(public_key).hexdigest()
                
                _logger.info(f"Telemetry signer initialized with key_id: {self.key_id}")
                
            except Exception as e:
                _logger.error(f"Failed to load signing key: {e}", exc_info=True)
                self.signer = None
        else:
            _logger.warning("No signing key provided - signing disabled")
    
    def sign_envelope(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sign event envelope.
        
        Args:
            envelope: Event envelope dictionary (without integrity hash)
            
        Returns:
            Signed event envelope with integrity hash
        """
        # Calculate envelope hash (excluding integrity.hash_sha256)
        envelope_copy = envelope.copy()
        envelope_copy['integrity'] = envelope_copy['integrity'].copy()
        envelope_copy['integrity']['hash_sha256'] = ''
        
        # Canonical JSON serialization
        envelope_json = json.dumps(envelope_copy, sort_keys=True, ensure_ascii=False)
        envelope_bytes = envelope_json.encode('utf-8')
        
        # Calculate SHA256 hash
        envelope_hash = hashlib.sha256(envelope_bytes).hexdigest()
        
        # Sign hash with ed25519 (if signer available)
        signature = None
        if self.signer:
            try:
                signature_bytes = self.signer.sign(envelope_hash.encode('utf-8'))
                signature = base64.b64encode(signature_bytes.signature).decode('ascii')
            except Exception as e:
                _logger.error(f"Failed to sign envelope: {e}", exc_info=True)
        
        # Update envelope with hash and signature
        envelope['integrity']['hash_sha256'] = envelope_hash
        if signature:
            envelope['signature'] = signature
            envelope['signing_key_id'] = self.key_id
        
        return envelope
    
    def verify_envelope(self, envelope: Dict[str, Any], public_key_path: Path) -> bool:
        """
        Verify event envelope signature.
        
        Args:
            envelope: Event envelope dictionary
            public_key_path: Path to ed25519 public key file
            
        Returns:
            True if signature is valid, False otherwise
        """
        if not _nacl_available:
            return False
        
        if 'signature' not in envelope:
            return False
        
        try:
            # Load public key
            with open(public_key_path, 'rb') as f:
                public_key_data = f.read()
            
            verify_key = nacl.signing.VerifyKey(public_key_data)
            
            # Extract signature
            signature_b64 = envelope.get('signature', '')
            signature_bytes = base64.b64decode(signature_b64)
            
            # Recalculate hash
            envelope_copy = envelope.copy()
            envelope_copy['integrity'] = envelope_copy['integrity'].copy()
            envelope_copy['integrity']['hash_sha256'] = ''
            if 'signature' in envelope_copy:
                del envelope_copy['signature']
            if 'signing_key_id' in envelope_copy:
                del envelope_copy['signing_key_id']
            
            envelope_json = json.dumps(envelope_copy, sort_keys=True, ensure_ascii=False)
            envelope_bytes = envelope_json.encode('utf-8')
            envelope_hash = hashlib.sha256(envelope_bytes).hexdigest()
            
            # Verify signature
            verify_key.verify(envelope_hash.encode('utf-8'), signature_bytes)
            return True
            
        except Exception as e:
            _logger.error(f"Signature verification failed: {e}", exc_info=True)
            return False
