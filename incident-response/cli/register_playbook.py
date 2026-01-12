#!/usr/bin/env python3
"""
RansomEye Incident Response - Register Playbook CLI
AUTHORITATIVE: Command-line tool for registering playbooks
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_ir_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_ir_dir))

from api.ir_api import IRAPI, IRAPIError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Register playbook'
    )
    parser.add_argument(
        '--playbook',
        type=Path,
        required=True,
        help='Path to playbook JSON file'
    )
    parser.add_argument(
        '--registry',
        type=Path,
        required=True,
        help='Path to playbook registry file'
    )
    parser.add_argument(
        '--public-keys-dir',
        type=Path,
        required=True,
        help='Directory containing public keys for verification'
    )
    parser.add_argument(
        '--executions-store',
        type=Path,
        required=True,
        help='Path to executions store'
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
    parser.add_argument(
        '--output',
        type=Path,
        help='Path to output registered playbook JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load playbook
        playbook = json.loads(args.playbook.read_text())
        
        # Initialize IR API
        api = IRAPI(
            registry_path=args.registry,
            public_keys_dir=args.public_keys_dir,
            executions_store_path=args.executions_store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Register playbook
        registered_playbook = api.register_playbook(playbook)
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(registered_playbook, indent=2, ensure_ascii=False))
            print(f"Playbook registered successfully. Result written to: {args.output}")
        else:
            print(json.dumps(registered_playbook, indent=2, ensure_ascii=False))
        
        print(f"\nPlaybook Summary:")
        print(f"  Playbook ID: {registered_playbook.get('playbook_id')}")
        print(f"  Name: {registered_playbook.get('playbook_name')}")
        print(f"  Version: {registered_playbook.get('playbook_version')}")
        print(f"  Scope: {registered_playbook.get('scope')}")
        print(f"  Steps: {len(registered_playbook.get('steps', []))}")
        print(f"  Signed: {bool(registered_playbook.get('playbook_signature'))}")
        
    except IRAPIError as e:
        print(f"Playbook registration failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
