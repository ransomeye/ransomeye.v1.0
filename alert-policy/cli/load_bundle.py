#!/usr/bin/env python3
"""
RansomEye Alert Policy - Load Bundle CLI
AUTHORITATIVE: Command-line tool for loading policy bundles
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_policy_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_policy_dir))

from api.policy_api import PolicyAPI, PolicyAPIError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Load policy bundle (hot-reload)'
    )
    parser.add_argument(
        '--bundle',
        type=Path,
        required=True,
        help='Path to policy bundle file'
    )
    parser.add_argument(
        '--public-keys-dir',
        type=Path,
        required=True,
        help='Directory containing public keys for verification'
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
        help='Path to output loaded bundle JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize policy API
        api = PolicyAPI(
            public_keys_dir=args.public_keys_dir,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Load bundle
        bundle = api.load_bundle(args.bundle)
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(bundle, indent=2, ensure_ascii=False))
            print(f"Bundle loaded successfully. Result written to: {args.output}")
        else:
            print(json.dumps(bundle, indent=2, ensure_ascii=False))
        
        print(f"\nBundle Summary:")
        print(f"  Bundle ID: {bundle.get('bundle_id')}")
        print(f"  Version: {bundle.get('bundle_version')}")
        print(f"  Authority Scope: {bundle.get('authority_scope')}")
        print(f"  Rules: {len(bundle.get('rules', []))}")
        print(f"  Hot-reload: ✓ Successful")
        
    except PolicyAPIError as e:
        print(f"Bundle load failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
