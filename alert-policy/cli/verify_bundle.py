#!/usr/bin/env python3
"""
RansomEye Alert Policy - Verify Bundle CLI
AUTHORITATIVE: Command-line tool for verifying policy bundles
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_policy_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_policy_dir))

from engine.bundle_loader import BundleLoader, BundleLoadError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Verify policy bundle'
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
    
    args = parser.parse_args()
    
    try:
        # Initialize bundle loader
        loader = BundleLoader(args.public_keys_dir)
        
        # Load and validate bundle
        bundle = loader.load_bundle(args.bundle)
        
        print("✓ Bundle verification successful")
        print(f"\nBundle Details:")
        print(f"  Bundle ID: {bundle.get('bundle_id', 'N/A')}")
        print(f"  Version: {bundle.get('bundle_version', 'N/A')}")
        print(f"  Authority Scope: {bundle.get('authority_scope', 'N/A')}")
        print(f"  Rules: {len(bundle.get('rules', []))}")
        print(f"  Created By: {bundle.get('created_by', 'N/A')}")
        print(f"  Created At: {bundle.get('created_at', 'N/A')}")
        print(f"  Signed: {bool(bundle.get('bundle_signature'))}")
        
        # Check for priority ties
        priorities = [rule.get('priority', -1) for rule in bundle.get('rules', [])]
        if len(priorities) == len(set(priorities)):
            print(f"  Priority Validation: ✓ No ties")
        else:
            print(f"  Priority Validation: ✗ Duplicate priorities found")
            sys.exit(1)
        
        sys.exit(0)
        
    except BundleLoadError as e:
        print(f"✗ Bundle verification failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
