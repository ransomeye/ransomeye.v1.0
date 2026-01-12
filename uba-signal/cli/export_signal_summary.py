#!/usr/bin/env python3
"""
RansomEye UBA Signal - Export Signal Summary CLI
AUTHORITATIVE: Command-line tool for exporting signal summaries
"""

import sys
import json
from pathlib import Path
import argparse
from datetime import datetime, timezone

# Add parent directory to path for imports
_signal_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_signal_dir))

from api.signal_api import SignalAPI, SignalAPIError


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse timestamp string to datetime."""
    try:
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except Exception as e:
        raise ValueError(f"Invalid timestamp format: {e}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Export signal summary'
    )
    parser.add_argument(
        '--identity-id',
        required=True,
        help='Identity identifier'
    )
    parser.add_argument(
        '--window-start',
        required=True,
        help='Observation window start (RFC3339)'
    )
    parser.add_argument(
        '--window-end',
        required=True,
        help='Observation window end (RFC3339)'
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
        help='Path to output summary JSON'
    )
    
    args = parser.parse_args()
    
    try:
        # Parse window timestamps
        window_start = parse_timestamp(args.window_start)
        window_end = parse_timestamp(args.window_end)
        
        # Initialize Signal API
        api = SignalAPI(
            drift_deltas_store_path=args.drift_deltas_store,
            drift_summaries_store_path=args.drift_summaries_store,
            signals_store_path=args.signals_store,
            summaries_store_path=args.summaries_store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Get or build summary
        summary = api.get_signal_summary(
            identity_id=args.identity_id,
            observation_window_start=window_start,
            observation_window_end=window_end
        )
        
        # Export summary
        args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
        print(f"Summary exported to: {args.output}")
        
        print(f"\nSignal Summary:")
        print(f"  Summary ID: {summary.get('summary_id')}")
        print(f"  Identity ID: {args.identity_id}")
        print(f"  Window: {summary.get('observation_window_start')} to {summary.get('observation_window_end')}")
        print(f"  Signal Count: {summary.get('signal_count')}")
        print(f"  Interpretation Types: {', '.join(summary.get('interpretation_types_present', []))}")
        print(f"  Summary Hash: {summary.get('summary_hash', '')[:16]}...")
        
    except SignalAPIError as e:
        print(f"Summary export failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
