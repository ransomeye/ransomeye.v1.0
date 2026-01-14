#!/usr/bin/env python3
"""
RansomEye v1.0 Key Generation Ceremony
AUTHORITATIVE: Key generation ceremony for persistent signing keys
Phase-9: Generate and register persistent signing keys
"""

import os
import sys
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Add supply-chain to path
_supply_chain_dir = Path(__file__).parent.parent / "supply-chain"
sys.path.insert(0, str(_supply_chain_dir))

from crypto.persistent_signing_authority import PersistentSigningAuthority, PersistentSigningAuthorityError
from crypto.key_registry import KeyRegistry, KeyType


def generate_keypair() -> tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
    """Generate new ed25519 keypair."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key


def compute_public_key_fingerprint(public_key: ed25519.Ed25519PublicKey) -> str:
    """Compute SHA256 fingerprint of public key."""
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return hashlib.sha256(public_key_bytes).hexdigest()


def log_ceremony(
    log_path: Path,
    key_id: str,
    key_type: str,
    public_key_fingerprint: str,
    generation_date: str,
    participants: list[str],
    witness: Optional[str] = None
) -> None:
    """Log key generation ceremony."""
    log_entry = {
        "ceremony_type": "key_generation",
        "key_id": key_id,
        "key_type": key_type,
        "public_key_fingerprint": public_key_fingerprint,
        "generation_date": generation_date,
        "participants": participants,
        "witness": witness,
        "logged_at": datetime.now(timezone.utc).isoformat()
    }
    
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'w') as f:
        json.dump(log_entry, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Ceremony log written to {log_path}")


def main():
    """Main key generation ceremony."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Key Generation Ceremony for Persistent Signing Keys'
    )
    parser.add_argument(
        '--key-id',
        required=True,
        help='Key identifier (e.g., vendor-signing-key-1)'
    )
    parser.add_argument(
        '--key-type',
        choices=['root', 'signing'],
        default='signing',
        help='Key type (default: signing)'
    )
    parser.add_argument(
        '--vault-dir',
        type=Path,
        default=Path('keys/vault'),
        help='Directory for encrypted key vault'
    )
    parser.add_argument(
        '--registry-path',
        type=Path,
        default=Path('keys/registry.json'),
        help='Path to key registry JSON file'
    )
    parser.add_argument(
        '--log-dir',
        type=Path,
        default=Path('keys/ceremony-logs'),
        help='Directory for ceremony logs'
    )
    parser.add_argument(
        '--participants',
        nargs='+',
        required=True,
        help='List of ceremony participants'
    )
    parser.add_argument(
        '--witness',
        help='Witness name (optional)'
    )
    parser.add_argument(
        '--passphrase',
        help='Vault passphrase (if not set, will prompt or use RANSOMEYE_KEY_VAULT_PASSPHRASE)'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("RansomEye v1.0 Key Generation Ceremony")
    print("=" * 70)
    print(f"Key ID: {args.key_id}")
    print(f"Key Type: {args.key_type}")
    print(f"Participants: {', '.join(args.participants)}")
    if args.witness:
        print(f"Witness: {args.witness}")
    print("")
    
    # Get passphrase
    passphrase = args.passphrase or os.environ.get('RANSOMEYE_KEY_VAULT_PASSPHRASE')
    if not passphrase:
        import getpass
        passphrase = getpass.getpass("Enter vault passphrase: ")
        passphrase_confirm = getpass.getpass("Confirm vault passphrase: ")
        if passphrase != passphrase_confirm:
            print("❌ ERROR: Passphrases do not match", file=sys.stderr)
            sys.exit(1)
    
    # Check if key already exists
    registry = KeyRegistry(args.registry_path)
    if registry.get_key(args.key_id):
        print(f"❌ ERROR: Key {args.key_id} already exists in registry", file=sys.stderr)
        sys.exit(1)
    
    # Generate keypair
    print("Generating ed25519 keypair...")
    private_key, public_key = generate_keypair()
    public_key_fingerprint = compute_public_key_fingerprint(public_key)
    
    print(f"✅ Keypair generated")
    print(f"   Public key fingerprint: {public_key_fingerprint}")
    print("")
    
    # Store key in vault
    print("Storing key in encrypted vault...")
    try:
        authority = PersistentSigningAuthority(
            vault_dir=args.vault_dir,
            registry_path=args.registry_path,
            unlock_passphrase=passphrase
        )
        
        generation_date = datetime.now(timezone.utc).isoformat()
        log_path = args.log_dir / f"{args.key_id}-generation-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.json"
        
        authority.store_signing_key(
            key_id=args.key_id,
            private_key=private_key,
            public_key=public_key,
            generation_date=generation_date,
            generation_log_path=log_path
        )
        
        print(f"✅ Key stored in vault: {args.vault_dir}")
        print(f"✅ Key registered in registry: {args.registry_path}")
        
        # Log ceremony
        log_ceremony(
            log_path=log_path,
            key_id=args.key_id,
            key_type=args.key_type,
            public_key_fingerprint=public_key_fingerprint,
            generation_date=generation_date,
            participants=args.participants,
            witness=args.witness
        )
        
        print("")
        print("=" * 70)
        print("✅ Key Generation Ceremony Complete")
        print("=" * 70)
        print(f"Key ID: {args.key_id}")
        print(f"Public Key Fingerprint: {public_key_fingerprint}")
        print(f"Ceremony Log: {log_path}")
        print("")
        print("⚠️  IMPORTANT: Store the vault passphrase securely.")
        print("⚠️  IMPORTANT: Backup the encrypted vault and registry.")
        print("⚠️  IMPORTANT: Distribute public key to all stakeholders.")
        
    except PersistentSigningAuthorityError as e:
        print(f"❌ ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
