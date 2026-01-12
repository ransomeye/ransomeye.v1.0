#!/usr/bin/env python3
"""
RansomEye Human Authority Framework - Sign Override CLI
AUTHORITATIVE: Command-line tool for signing human override actions
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
        description='Sign human override action'
    )
    parser.add_argument(
        '--action-type',
        choices=[
            'POLICY_OVERRIDE',
            'INCIDENT_ESCALATION',
            'INCIDENT_SUPPRESSION',
            'PLAYBOOK_APPROVAL',
            'PLAYBOOK_ABORT',
            'RISK_ACCEPTANCE',
            'FALSE_POSITIVE_DECLARATION'
        ],
        required=True,
        help='Type of authority action'
    )
    parser.add_argument(
        '--human-identifier',
        required=True,
        help='Human identifier (username, email, etc.)'
    )
    parser.add_argument(
        '--role-assertion-id',
        required=True,
        help='Role assertion identifier'
    )
    parser.add_argument(
        '--scope',
        choices=['incident', 'policy', 'campaign', 'risk', 'playbook', 'global'],
        required=True,
        help='Scope of action'
    )
    parser.add_argument(
        '--subject-id',
        required=True,
        help='Subject identifier (incident ID, policy ID, etc.)'
    )
    parser.add_argument(
        '--subject-type',
        choices=['incident', 'policy', 'campaign', 'risk_computation', 'playbook', 'other'],
        required=True,
        help='Type of subject'
    )
    parser.add_argument(
        '--reason',
        required=True,
        help='Structured reason for action'
    )
    parser.add_argument(
        '--supersedes-automated',
        action='store_true',
        help='Whether this action supersedes automated decision'
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
    parser.add_argument(
        '--output',
        type=Path,
        help='Path to output action JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize authority API
        api = AuthorityAPI(
            keys_dir=args.keys_dir,
            role_assertions_path=args.role_assertions,
            actions_store_path=args.actions_store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Create override
        action = api.create_override(
            action_type=args.action_type,
            human_identifier=args.human_identifier,
            role_assertion_id=args.role_assertion_id,
            scope=args.scope,
            subject_id=args.subject_id,
            subject_type=args.subject_type,
            reason=args.reason,
            supersedes_automated_decision=args.supersedes_automated
        )
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(action, indent=2, ensure_ascii=False))
            print(f"Override action created successfully. Result written to: {args.output}")
        else:
            print(json.dumps(action, indent=2, ensure_ascii=False))
        
        print(f"\nAction Summary:")
        print(f"  Action ID: {action['action_id']}")
        print(f"  Type: {action['action_type']}")
        print(f"  Human: {action['human_identifier']}")
        print(f"  Subject: {action['subject_id']}")
        print(f"  Signed: {bool(action.get('human_signature'))}")
        print(f"  Ledger Entry: {action.get('ledger_entry_id', 'N/A')}")
        
    except AuthorityAPIError as e:
        print(f"Override creation failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
