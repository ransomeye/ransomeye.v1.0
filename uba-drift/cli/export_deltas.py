#!/usr/bin/env python3
"""
RansomEye UBA Drift - Export Deltas CLI
AUTHORITATIVE: Command-line tool for exporting behavior deltas
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_drift_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_drift_dir))

from api.drift_api import DriftAPI, DriftAPIError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Export behavior deltas'
    )
    parser.add_argument(
        '--identity-id',
        required=True,
        help='Identity identifier'
    )
    parser.add_argument(
        '--window-start',
        help='Window start filter (optional)'
    )
    parser.add_argument(
        '--window-end',
        help='Window end filter (optional)'
    )
    parser.add_argument(
        '--deltas-store',
        type=Path,
        required=True,
        help='Path to deltas store'
    )
    parser.add_argument(
        '--summaries-store',
        type=Path,
        required=True,
        help='Path to summaries store'
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
        help='Path to output deltas JSON'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize Drift API (minimal for export)
        # Note: We need UBA stores for full API, but for export we can use minimal
        from storage.delta_store import DeltaStore
        
        delta_store = DeltaStore(
            deltas_store_path=args.deltas_store,
            summaries_store_path=args.summaries_store
        )
        
        # Get deltas
        deltas = delta_store.get_deltas_for_identity(
            identity_id=args.identity_id,
            window_start=args.window_start,
            window_end=args.window_end
        )
        
        if not deltas:
            print(f"No deltas found for identity: {args.identity_id}", file=sys.stderr)
            sys.exit(1)
        
        # Export deltas
        args.output.write_text(json.dumps(deltas, indent=2, ensure_ascii=False))
        print(f"Deltas exported to: {args.output}")
        
        # Emit export audit entry
        try:
            from audit_ledger import AppendOnlyStore, KeyManager, Signer, LedgerWriter
            
            ledger_store = AppendOnlyStore(args.ledger, read_only=False)
            ledger_key_manager = KeyManager(args.ledger_key_dir)
            ledger_private_key, ledger_public_key, ledger_key_id = ledger_key_manager.get_or_create_keypair()
            ledger_signer = Signer(ledger_private_key, ledger_key_id)
            ledger_writer = LedgerWriter(ledger_store, ledger_signer)
            
            ledger_writer.create_entry(
                component='uba-drift',
                component_instance_id='uba-drift',
                action_type='UBA_DELTA_EXPORTED',
                subject={'type': 'identity', 'id': args.identity_id},
                actor={'type': 'system', 'identifier': 'uba-drift'},
                payload={
                    'deltas_count': len(deltas),
                    'export_path': str(args.output)
                }
            )
        except Exception as e:
            print(f"Warning: Failed to emit audit ledger entry: {e}", file=sys.stderr)
        
        print(f"\nDelta Export Summary:")
        print(f"  Identity ID: {args.identity_id}")
        print(f"  Total Deltas: {len(deltas)}")
        
    except Exception as e:
        print(f"Delta export failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
