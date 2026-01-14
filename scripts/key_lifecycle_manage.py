#!/usr/bin/env python3
"""
RansomEye v1.0 Key Lifecycle Management
AUTHORITATIVE: Key rotation, revocation, and compromise recovery
Phase-9: Complete key lifecycle management
"""

import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Add supply-chain to path
_supply_chain_dir = Path(__file__).parent.parent / "supply-chain"
sys.path.insert(0, str(_supply_chain_dir))

from crypto.key_registry import KeyRegistry, KeyRegistryError
from crypto.persistent_signing_authority import PersistentSigningAuthority, PersistentSigningAuthorityError


def revoke_key(
    key_id: str,
    reason: str,
    registry_path: Path,
    revocation_date: Optional[str] = None
) -> None:
    """Revoke a key."""
    registry = KeyRegistry(registry_path)
    
    try:
        registry.revoke_key(key_id, reason, revocation_date)
        print(f"✅ Key {key_id} revoked")
        print(f"   Reason: {reason}")
        print(f"   Revocation date: {revocation_date or datetime.now(timezone.utc).isoformat()}")
    except KeyRegistryError as e:
        print(f"❌ ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def rotate_key(
    old_key_id: str,
    new_key_id: str,
    registry_path: Path,
    rotation_date: Optional[str] = None
) -> None:
    """Mark key as rotated."""
    registry = KeyRegistry(registry_path)
    
    try:
        registry.rotate_key(old_key_id, new_key_id, rotation_date)
        print(f"✅ Key {old_key_id} marked as rotated")
        print(f"   Rotated to: {new_key_id}")
        print(f"   Rotation date: {rotation_date or datetime.now(timezone.utc).isoformat()}")
    except KeyRegistryError as e:
        print(f"❌ ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def mark_compromised(
    key_id: str,
    registry_path: Path,
    compromise_date: Optional[str] = None
) -> None:
    """Mark key as compromised (automatically revokes)."""
    registry = KeyRegistry(registry_path)
    
    try:
        registry.mark_compromised(key_id, compromise_date)
        print(f"✅ Key {key_id} marked as compromised and revoked")
        print(f"   Compromise date: {compromise_date or datetime.now(timezone.utc).isoformat()}")
        print("")
        print("⚠️  ACTION REQUIRED:")
        print("   1. Generate new key using key generation ceremony")
        print("   2. Re-sign all artifacts signed with compromised key")
        print("   3. Notify all stakeholders of key compromise")
    except KeyRegistryError as e:
        print(f"❌ ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def show_key_status(key_id: str, registry_path: Path) -> None:
    """Show key status."""
    registry = KeyRegistry(registry_path)
    
    key_entry = registry.get_key(key_id)
    if not key_entry:
        print(f"❌ ERROR: Key {key_id} not found", file=sys.stderr)
        sys.exit(1)
    
    print(f"Key ID: {key_entry['key_id']}")
    print(f"Key Type: {key_entry['key_type']}")
    print(f"Status: {key_entry['status']}")
    print(f"Public Key Fingerprint: {key_entry['public_key_fingerprint']}")
    print(f"Generation Date: {key_entry['generation_date']}")
    
    if key_entry.get('revocation_date'):
        print(f"Revocation Date: {key_entry['revocation_date']}")
        print(f"Revocation Reason: {key_entry.get('revocation_reason', 'N/A')}")
    
    if key_entry.get('rotation_date'):
        print(f"Rotation Date: {key_entry['rotation_date']}")
        print(f"Rotated To: {key_entry.get('rotated_to', 'N/A')}")
    
    if key_entry.get('compromise_date'):
        print(f"Compromise Date: {key_entry['compromise_date']}")


def list_revoked_keys(registry_path: Path) -> None:
    """List all revoked keys."""
    registry = KeyRegistry(registry_path)
    revocation_list = registry.get_revocation_list()
    
    if not revocation_list:
        print("No revoked keys")
        return
    
    print("Revoked Keys:")
    print("=" * 70)
    for entry in revocation_list:
        print(f"Key ID: {entry['key_id']}")
        print(f"  Fingerprint: {entry['public_key_fingerprint']}")
        print(f"  Revocation Date: {entry['revocation_date']}")
        print(f"  Reason: {entry['reason']}")
        print("")


def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Key Lifecycle Management'
    )
    parser.add_argument(
        '--registry-path',
        type=Path,
        default=Path('keys/registry.json'),
        help='Path to key registry JSON file'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command')
    
    # Revoke command
    revoke_parser = subparsers.add_parser('revoke', help='Revoke a key')
    revoke_parser.add_argument('--key-id', required=True, help='Key ID to revoke')
    revoke_parser.add_argument('--reason', required=True, help='Revocation reason')
    revoke_parser.add_argument('--date', help='Revocation date (ISO 8601)')
    
    # Rotate command
    rotate_parser = subparsers.add_parser('rotate', help='Mark key as rotated')
    rotate_parser.add_argument('--old-key-id', required=True, help='Old key ID')
    rotate_parser.add_argument('--new-key-id', required=True, help='New key ID')
    rotate_parser.add_argument('--date', help='Rotation date (ISO 8601)')
    
    # Compromise command
    compromise_parser = subparsers.add_parser('compromise', help='Mark key as compromised')
    compromise_parser.add_argument('--key-id', required=True, help='Key ID')
    compromise_parser.add_argument('--date', help='Compromise date (ISO 8601)')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show key status')
    status_parser.add_argument('--key-id', required=True, help='Key ID')
    
    # List revoked command
    subparsers.add_parser('list-revoked', help='List all revoked keys')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == 'revoke':
        revoke_key(args.key_id, args.reason, args.registry_path, args.date)
    elif args.command == 'rotate':
        rotate_key(args.old_key_id, args.new_key_id, args.registry_path, args.date)
    elif args.command == 'compromise':
        mark_compromised(args.key_id, args.registry_path, args.date)
    elif args.command == 'status':
        show_key_status(args.key_id, args.registry_path)
    elif args.command == 'list-revoked':
        list_revoked_keys(args.registry_path)


if __name__ == '__main__':
    main()
