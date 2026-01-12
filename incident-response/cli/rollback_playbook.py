#!/usr/bin/env python3
"""
RansomEye Incident Response - Rollback Playbook CLI
AUTHORITATIVE: Command-line tool for rolling back playbook executions
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
        description='Rollback playbook execution'
    )
    parser.add_argument(
        '--execution-id',
        required=True,
        help='Execution identifier'
    )
    parser.add_argument(
        '--rolled-back-by',
        required=True,
        help='Human identifier who initiated rollback'
    )
    parser.add_argument(
        '--rollback-reason',
        required=True,
        help='Reason for rollback'
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
        help='Path to output rollback record JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize IR API
        api = IRAPI(
            registry_path=args.registry,
            public_keys_dir=args.public_keys_dir,
            executions_store_path=args.executions_store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Rollback execution
        rollback_record = api.rollback_execution(
            execution_id=args.execution_id,
            rolled_back_by=args.rolled_back_by,
            rollback_reason=args.rollback_reason
        )
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(rollback_record, indent=2, ensure_ascii=False))
            print(f"Rollback created successfully. Result written to: {args.output}")
        else:
            print(json.dumps(rollback_record, indent=2, ensure_ascii=False))
        
        print(f"\nRollback Summary:")
        print(f"  Rollback ID: {rollback_record.get('rollback_id')}")
        print(f"  Execution ID: {rollback_record.get('execution_id')}")
        print(f"  Rolled back by: {rollback_record.get('rolled_back_by')}")
        print(f"  Rollback steps: {len(rollback_record.get('rollback_steps', []))}")
        
    except IRAPIError as e:
        print(f"Rollback failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
