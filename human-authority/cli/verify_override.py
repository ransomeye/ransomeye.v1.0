#!/usr/bin/env python3
"""
RansomEye Human Authority Framework - Verify Override CLI
AUTHORITATIVE: Command-line tool for verifying human override actions
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_authority_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_authority_dir))

from api.authority_api import AuthorityAPI, AuthorityAPIError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Verify human override action'
    )
    parser.add_argument(
        '--action',
        type=Path,
        required=True,
        help='Path to action JSON file'
    )
    parser.add_argument(
        '--keys-dir',
        type=Path,
        required=True,
        help='Directory containing human keypairs'
    )
    parser.add_argument(
        '--role-assertions',
        type=Path,
        required=True,
        help='Path to role assertions store'
    )
    parser.add_argument(
        '--actions-store',
        type=Path,
        required=True,
        help='Path to actions store'
    )
    parser.add_argument(
        '--ledger',
        type=Path,
        required=True,
        help='Path to audit ledger file'
    )
    parser.add_argument(
        '--ledger-key-dir',
        type=Path,
        required=True,
        help='Directory containing ledger signing keys'
    )
    
    args = parser.parse_args()
    
    try:
        # Load action
        action = json.loads(args.action.read_text())
        
        # Initialize authority API
        api = AuthorityAPI(
            keys_dir=args.keys_dir,
            role_assertions_path=args.role_assertions,
            actions_store_path=args.actions_store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Verify action
        is_valid = api.verify_action(action)
        
        if is_valid:
            print("✓ Action verification successful")
            print(f"\nAction Details:")
            print(f"  Action ID: {action.get('action_id', 'N/A')}")
            print(f"  Type: {action.get('action_type', 'N/A')}")
            print(f"  Human: {action.get('human_identifier', 'N/A')}")
            print(f"  Subject: {action.get('subject_id', 'N/A')}")
            print(f"  Scope: {action.get('scope', 'N/A')}")
            print(f"  Timestamp: {action.get('timestamp', 'N/A')}")
            print(f"  Ledger Entry: {action.get('ledger_entry_id', 'N/A')}")
            sys.exit(0)
        else:
            print("✗ Action verification failed", file=sys.stderr)
            sys.exit(1)
        
    except AuthorityAPIError as e:
        print(f"✗ Action verification failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
