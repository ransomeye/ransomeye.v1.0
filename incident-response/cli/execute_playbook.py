#!/usr/bin/env python3
"""
RansomEye Incident Response - Execute Playbook CLI
AUTHORITATIVE: Command-line tool for executing playbooks
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
        description='Execute playbook'
    )
    parser.add_argument(
        '--playbook-id',
        required=True,
        help='Playbook identifier'
    )
    parser.add_argument(
        '--subject-id',
        required=True,
        help='Subject identifier (incident ID, etc.)'
    )
    parser.add_argument(
        '--authority-action-id',
        required=True,
        help='Human authority action identifier (HAF)'
    )
    parser.add_argument(
        '--explanation-bundle-id',
        required=True,
        help='Explanation bundle identifier (SEE)'
    )
    parser.add_argument(
        '--executed-by',
        required=True,
        help='Human identifier who executed playbook'
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
        help='Path to output execution record JSON (optional)'
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
        
        # Execute playbook
        execution_record = api.execute_playbook(
            playbook_id=args.playbook_id,
            subject_id=args.subject_id,
            authority_action_id=args.authority_action_id,
            explanation_bundle_id=args.explanation_bundle_id,
            executed_by=args.executed_by
        )
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(execution_record, indent=2, ensure_ascii=False))
            print(f"Playbook executed successfully. Result written to: {args.output}")
        else:
            print(json.dumps(execution_record, indent=2, ensure_ascii=False))
        
        print(f"\nExecution Summary:")
        print(f"  Execution ID: {execution_record.get('execution_id')}")
        print(f"  Playbook ID: {execution_record.get('playbook_id')}")
        print(f"  Status: {execution_record.get('execution_status')}")
        print(f"  Steps executed: {len(execution_record.get('step_results', []))}")
        print(f"  Rollback available: {execution_record.get('rollback_available', False)}")
        print(f"  Ledger Entry: {execution_record.get('ledger_entry_id', 'N/A')}")
        
    except IRAPIError as e:
        print(f"Playbook execution failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
