#!/usr/bin/env python3
"""
RansomEye Deception Framework - Collect Interactions CLI
AUTHORITATIVE: Command-line tool for collecting decoy interactions
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_deception_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_deception_dir))

from api.deception_api import DeceptionAPI, DeceptionAPIError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Collect decoy interaction'
    )
    parser.add_argument(
        '--decoy-id',
        required=True,
        help='Decoy identifier'
    )
    parser.add_argument(
        '--interaction-type',
        choices=['auth_attempt', 'scan', 'access', 'command'],
        required=True,
        help='Type of interaction'
    )
    parser.add_argument(
        '--source-ip',
        required=True,
        help='Source IP address'
    )
    parser.add_argument(
        '--source-host',
        default='',
        help='Source hostname (optional)'
    )
    parser.add_argument(
        '--source-process',
        default='',
        help='Source process identifier (optional)'
    )
    parser.add_argument(
        '--evidence-reference',
        default='',
        help='Evidence reference identifier (optional)'
    )
    parser.add_argument(
        '--decoys-store',
        type=Path,
        required=True,
        help='Path to decoys store'
    )
    parser.add_argument(
        '--deployments-store',
        type=Path,
        required=True,
        help='Path to deployments store'
    )
    parser.add_argument(
        '--interactions-store',
        type=Path,
        required=True,
        help='Path to interactions store'
    )
    parser.add_argument(
        '--signals-store',
        type=Path,
        required=True,
        help='Path to signals store'
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
        help='Path to output interaction record JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize deception API
        api = DeceptionAPI(
            decoys_store_path=args.decoys_store,
            deployments_store_path=args.deployments_store,
            interactions_store_path=args.interactions_store,
            signals_store_path=args.signals_store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Collect interaction
        interaction = api.collect_interaction(
            decoy_id=args.decoy_id,
            interaction_type=args.interaction_type,
            source_ip=args.source_ip,
            source_host=args.source_host,
            source_process=args.source_process,
            evidence_reference=args.evidence_reference
        )
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(interaction, indent=2, ensure_ascii=False))
            print(f"Interaction collected. Result written to: {args.output}")
        else:
            print(json.dumps(interaction, indent=2, ensure_ascii=False))
        
        print(f"\nInteraction Summary:")
        print(f"  Interaction ID: {interaction.get('interaction_id')}")
        print(f"  Decoy ID: {args.decoy_id}")
        print(f"  Interaction Type: {args.interaction_type}")
        print(f"  Source IP: {args.source_ip}")
        print(f"  Confidence Level: {interaction.get('confidence_level')}")
        print(f"  Evidence Reference: {interaction.get('evidence_reference')}")
        
    except DeceptionAPIError as e:
        print(f"Interaction collection failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
