#!/usr/bin/env python3
"""
RansomEye AI Model Registry - Model Revocation CLI
AUTHORITATIVE: Command-line tool for revoking models (terminal state)
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_registry_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_registry_dir))

from api.registry_api import RegistryAPI, RegistryAPIError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Revoke a model in the AI Model Registry (terminal state)'
    )
    parser.add_argument(
        '--model-id',
        required=True,
        help='Model identifier (UUID)'
    )
    parser.add_argument(
        '--model-version',
        required=True,
        help='Model version'
    )
    parser.add_argument(
        '--revoked-by',
        required=True,
        help='Entity that revoked model (user, system, etc.)'
    )
    parser.add_argument(
        '--reason',
        help='Reason for revocation (optional)'
    )
    parser.add_argument(
        '--registry',
        type=Path,
        required=True,
        help='Path to registry file'
    )
    parser.add_argument(
        '--model-key-dir',
        type=Path,
        required=True,
        help='Directory containing model signing keys'
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
        help='Path to output updated model record JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize registry API
        api = RegistryAPI(
            registry_path=args.registry,
            model_key_dir=args.model_key_dir,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Revoke model
        model_record = api.revoke_model(
            model_id=args.model_id,
            model_version=args.model_version,
            revoked_by=args.revoked_by,
            reason=args.reason
        )
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(model_record, indent=2, ensure_ascii=False))
            print(f"Model revoked successfully. Record written to: {args.output}")
        else:
            print(json.dumps(model_record, indent=2, ensure_ascii=False))
        
        print(f"Model ID: {model_record['model_id']}")
        print(f"Model Version: {model_record['model_version']}")
        print(f"Lifecycle State: {model_record['lifecycle_state']}")
        
    except RegistryAPIError as e:
        print(f"Revocation failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
