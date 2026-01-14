#!/usr/bin/env python3
"""
RansomEye v1.0 Windows Agent - Command Signature Verifier
AUTHORITATIVE: ed25519 signature verification for Windows agent
Python 3.10+ only
PHASE 4: Real ed25519 verification (replaces placeholder)
"""

import sys
import json
import base64
import argparse
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend


def verify_command_signature(command_payload: dict, signature: str, public_key_path: Path) -> bool:
    """
    PHASE 4: Verify ed25519 signature of command payload.
    
    Args:
        command_payload: Command payload dictionary (without signature fields)
        signature: Base64-encoded ed25519 signature
        public_key_path: Path to ed25519 public key file
        
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Load public key
        if not public_key_path.exists():
            print(f"ERROR: Public key file not found: {public_key_path}", file=sys.stderr)
            return False
        
        with open(public_key_path, 'rb') as f:
            public_key_data = f.read()
        
        public_key = serialization.load_pem_public_key(
            public_key_data,
            backend=default_backend()
        )
        
        if not isinstance(public_key, Ed25519PublicKey):
            print("ERROR: Public key is not ed25519", file=sys.stderr)
            return False
        
        # Serialize payload to canonical JSON (same as signing)
        payload_json = json.dumps(command_payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        
        # Decode signature
        try:
            signature_bytes = base64.b64decode(signature.encode('ascii'))
        except Exception as e:
            print(f"ERROR: Invalid signature encoding: {e}", file=sys.stderr)
            return False
        
        # Verify signature
        try:
            public_key.verify(
                signature_bytes,
                payload_json.encode('utf-8'),
                backend=default_backend()
            )
            return True
        except InvalidSignature:
            print("ERROR: Signature verification failed", file=sys.stderr)
            return False
        
    except Exception as e:
        print(f"ERROR: Signature verification error: {e}", file=sys.stderr)
        return False


def main():
    """
    PHASE 4: Main entry point for signature verification.
    
    Command-line interface for Windows agent to verify command signatures.
    """
    parser = argparse.ArgumentParser(description='PHASE 4: Verify ed25519 command signature')
    parser.add_argument('--command-payload', type=str, required=True,
                       help='Command payload JSON (without signature fields)')
    parser.add_argument('--signature', type=str, required=True,
                       help='Base64-encoded ed25519 signature')
    parser.add_argument('--public-key-path', type=Path, required=True,
                       help='Path to ed25519 public key file')
    
    args = parser.parse_args()
    
    # Parse command payload
    try:
        command_payload = json.loads(args.command_payload)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid command payload JSON: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Verify signature
    is_valid = verify_command_signature(
        command_payload,
        args.signature,
        args.public_key_path
    )
    
    if is_valid:
        print("SUCCESS")
        sys.exit(0)
    else:
        print("FAILED")
        sys.exit(1)


if __name__ == '__main__':
    main()
