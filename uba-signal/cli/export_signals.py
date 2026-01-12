#!/usr/bin/env python3
"""
RansomEye UBA Signal - Export Signals CLI
AUTHORITATIVE: Command-line tool for exporting interpreted signals
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_signal_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_signal_dir))

from api.signal_api import SignalAPI, SignalAPIError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Export interpreted signals'
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
        '--drift-deltas-store',
        type=Path,
        required=True,
        help='Path to UBA Drift deltas store'
    )
    parser.add_argument(
        '--drift-summaries-store',
        type=Path,
        required=True,
        help='Path to UBA Drift summaries store'
    )
    parser.add_argument(
        '--signals-store',
        type=Path,
        required=True,
        help='Path to signals store'
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
        help='Path to output signals JSON'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize Signal API
        api = SignalAPI(
            drift_deltas_store_path=args.drift_deltas_store,
            drift_summaries_store_path=args.drift_summaries_store,
            signals_store_path=args.signals_store,
            summaries_store_path=args.summaries_store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Get signals
        signals = api.get_signals(
            identity_id=args.identity_id,
            window_start=args.window_start,
            window_end=args.window_end
        )
        
        if not signals:
            print(f"No signals found for identity: {args.identity_id}", file=sys.stderr)
            sys.exit(1)
        
        # Export signals
        args.output.write_text(json.dumps(signals, indent=2, ensure_ascii=False))
        print(f"Signals exported to: {args.output}")
        
        # Emit export audit entry
        try:
            api.ledger_writer.create_entry(
                component='uba-signal',
                component_instance_id='uba-signal',
                action_type='UBA_SIGNAL_EXPORTED',
                subject={'type': 'identity', 'id': args.identity_id},
                actor={'type': 'system', 'identifier': 'uba-signal'},
                payload={
                    'signals_count': len(signals),
                    'export_path': str(args.output)
                }
            )
        except Exception as e:
            print(f"Warning: Failed to emit audit ledger entry: {e}", file=sys.stderr)
        
        print(f"\nSignal Export Summary:")
        print(f"  Identity ID: {args.identity_id}")
        print(f"  Total Signals: {len(signals)}")
        
    except SignalAPIError as e:
        print(f"Signal export failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
