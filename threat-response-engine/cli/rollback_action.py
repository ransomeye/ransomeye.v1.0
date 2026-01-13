#!/usr/bin/env python3
"""
RansomEye v1.0 Threat Response Engine - Rollback Action CLI
AUTHORITATIVE: CLI tool for rolling back executed actions
Python 3.10+ only
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Add project root to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Add threat-response-engine to path
_threat_response_path = os.path.join(_project_root, 'threat-response-engine')
if os.path.exists(_threat_response_path) and _threat_response_path not in sys.path:
    sys.path.insert(0, _threat_response_path)

from api.tre_api import TREAPI


def main():
    """Rollback executed action."""
    parser = argparse.ArgumentParser(
        description='Rollback executed action via Threat Response Engine'
    )
    parser.add_argument(
        '--action-id',
        required=True,
        help='Action ID to roll back (UUID)'
    )
    parser.add_argument(
        '--rollback-reason',
        choices=['FALSE_POSITIVE', 'HUMAN_OVERRIDE', 'SYSTEM_ERROR', 'POLICY_CHANGE', 'OTHER'],
        required=True,
        help='Reason for rollback'
    )
    parser.add_argument(
        '--rollback-type',
        choices=['FULL', 'PARTIAL'],
        default='FULL',
        help='Type of rollback (default: FULL)'
    )
    parser.add_argument(
        '--required-authority',
        choices=['NONE', 'HUMAN', 'ROLE'],
        default='NONE',
        help='Required authority level for rollback (default: NONE)'
    )
    parser.add_argument(
        '--authority-action-id',
        help='Human authority action ID (required if required_authority is HUMAN or ROLE)'
    )
    parser.add_argument(
        '--key-dir',
        type=Path,
        default=Path('/var/lib/ransomeye/tre/keys'),
        help='Directory for TRE signing keys (default: /var/lib/ransomeye/tre/keys)'
    )
    parser.add_argument(
        '--db-host',
        default=os.getenv('RANSOMEYE_DB_HOST', 'localhost'),
        help='Database host (default: from RANSOMEYE_DB_HOST or localhost)'
    )
    parser.add_argument(
        '--db-port',
        type=int,
        default=int(os.getenv('RANSOMEYE_DB_PORT', '5432')),
        help='Database port (default: from RANSOMEYE_DB_PORT or 5432)'
    )
    parser.add_argument(
        '--db-name',
        default=os.getenv('RANSOMEYE_DB_NAME', 'ransomeye'),
        help='Database name (default: from RANSOMEYE_DB_NAME or ransomeye)'
    )
    parser.add_argument(
        '--db-user',
        default=os.getenv('RANSOMEYE_DB_USER', 'ransomeye'),
        help='Database user (default: from RANSOMEYE_DB_USER or ransomeye)'
    )
    parser.add_argument(
        '--db-password',
        default=os.getenv('RANSOMEYE_DB_PASSWORD', ''),
        help='Database password (default: from RANSOMEYE_DB_PASSWORD)'
    )
    parser.add_argument(
        '--agent-command-endpoint',
        default=os.getenv('RANSOMEYE_AGENT_COMMAND_ENDPOINT', 'http://localhost:8001/commands'),
        help='Agent command endpoint URL (default: from RANSOMEYE_AGENT_COMMAND_ENDPOINT or http://localhost:8001/commands)'
    )
    parser.add_argument(
        '--ledger-path',
        type=Path,
        default=Path(os.getenv('RANSOMEYE_AUDIT_LEDGER', '/var/lib/ransomeye/audit/ledger.jsonl')),
        help='Audit ledger path (default: from RANSOMEYE_AUDIT_LEDGER or /var/lib/ransomeye/audit/ledger.jsonl)'
    )
    parser.add_argument(
        '--ledger-key-dir',
        type=Path,
        default=Path(os.getenv('RANSOMEYE_AUDIT_LEDGER_KEY_DIR', '/var/lib/ransomeye/audit/keys')),
        help='Audit ledger key directory (default: from RANSOMEYE_AUDIT_LEDGER_KEY_DIR or /var/lib/ransomeye/audit/keys)'
    )
    parser.add_argument(
        '--output',
        type=argparse.FileType('w'),
        default=sys.stdout,
        help='Output file for rollback result (default: stdout)'
    )
    
    args = parser.parse_args()
    
    # Validate required authority
    if args.required_authority in ('HUMAN', 'ROLE') and not args.authority_action_id:
        print(f"ERROR: authority_action_id is required when required_authority is {args.required_authority}", file=sys.stderr)
        sys.exit(1)
    
    # Initialize TRE API
    try:
        tre_api = TREAPI(
            key_dir=args.key_dir,
            db_conn_params={
                'host': args.db_host,
                'port': args.db_port,
                'database': args.db_name,
                'user': args.db_user,
                'password': args.db_password
            },
            agent_command_endpoint=args.agent_command_endpoint,
            ledger_path=args.ledger_path,
            ledger_key_dir=args.ledger_key_dir
        )
    except Exception as e:
        print(f"ERROR: Failed to initialize TRE API: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Rollback action
    try:
        result = tre_api.rollback_action(
            action_id=args.action_id,
            rollback_reason=args.rollback_reason,
            rollback_type=args.rollback_type,
            required_authority=args.required_authority,
            authority_action_id=args.authority_action_id
        )
        
        # Output result
        json.dump(result, args.output, indent=2)
        args.output.write('\n')
        
        sys.exit(0)
    except ValueError as e:
        print(f"ERROR: Validation failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Rollback failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
