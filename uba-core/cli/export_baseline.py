#!/usr/bin/env python3
"""
RansomEye UBA Core - Export Baseline CLI
AUTHORITATIVE: Command-line tool for exporting identity baselines
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_uba_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_uba_dir))

from api.uba_api import UBAAPI, UBAAPIError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Export identity baseline'
    )
    parser.add_argument(
        '--identity-id',
        required=True,
        help='Identity identifier'
    )
    parser.add_argument(
        '--baseline-id',
        help='Baseline identifier (optional, uses latest if not provided)'
    )
    parser.add_argument(
        '--identities-store',
        type=Path,
        required=True,
        help='Path to identities store'
    )
    parser.add_argument(
        '--events-store',
        type=Path,
        required=True,
        help='Path to behavior events store'
    )
    parser.add_argument(
        '--baselines-store',
        type=Path,
        required=True,
        help='Path to baselines store'
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
        required=True,
        help='Path to output baseline JSON'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize UBA API
        api = UBAAPI(
            identities_store_path=args.identities_store,
            events_store_path=args.events_store,
            baselines_store_path=args.baselines_store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Get baseline
        baseline = api.get_identity_baseline(
            identity_id=args.identity_id,
            baseline_id=args.baseline_id
        )
        
        if not baseline:
            print(f"Baseline not found for identity: {args.identity_id}", file=sys.stderr)
            sys.exit(1)
        
        # Export baseline
        args.output.write_text(json.dumps(baseline, indent=2, ensure_ascii=False))
        print(f"Baseline exported to: {args.output}")
        
        # Emit export audit entry
        try:
            api.ledger_writer.create_entry(
                component='uba-core',
                component_instance_id='uba-core',
                action_type='UBA_BASELINE_EXPORTED',
                subject={'type': 'identity', 'id': args.identity_id},
                actor={'type': 'system', 'identifier': 'uba-core'},
                payload={
                    'baseline_id': baseline.get('baseline_id', ''),
                    'export_path': str(args.output)
                }
            )
        except Exception as e:
            print(f"Warning: Failed to emit audit ledger entry: {e}", file=sys.stderr)
        
        print(f"\nBaseline Export Summary:")
        print(f"  Baseline ID: {baseline.get('baseline_id')}")
        print(f"  Identity ID: {args.identity_id}")
        print(f"  Window: {baseline.get('baseline_window_start')} to {baseline.get('baseline_window_end')}")
        print(f"  Baseline Hash: {baseline.get('baseline_hash', '')[:16]}...")
        
    except UBAAPIError as e:
        print(f"Baseline export failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
