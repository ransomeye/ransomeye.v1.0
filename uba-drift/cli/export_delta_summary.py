#!/usr/bin/env python3
"""
RansomEye UBA Drift - Export Delta Summary CLI
AUTHORITATIVE: Command-line tool for exporting delta summaries
"""

import sys
import json
from pathlib import Path
import argparse
from datetime import datetime, timezone

# Add parent directory to path for imports
_drift_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_drift_dir))

from api.drift_api import DriftAPI, DriftAPIError


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse timestamp string to datetime."""
    try:
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except Exception as e:
        raise ValueError(f"Invalid timestamp format: {e}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Export delta summary'
    )
    parser.add_argument(
        '--identity-id',
        required=True,
        help='Identity identifier'
    )
    parser.add_argument(
        '--baseline-hash',
        required=True,
        help='Baseline hash'
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
        '--uba-identities-store',
        type=Path,
        required=True,
        help='Path to UBA Core identities store'
    )
    parser.add_argument(
        '--uba-events-store',
        type=Path,
        required=True,
        help='Path to UBA Core events store'
    )
    parser.add_argument(
        '--uba-baselines-store',
        type=Path,
        required=True,
        help='Path to UBA Core baselines store'
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
        help='Path to output summary JSON'
    )
    
    args = parser.parse_args()
    
    try:
        # Parse window timestamps
        window_start = parse_timestamp(args.window_start)
        window_end = parse_timestamp(args.window_end)
        
        # Initialize Drift API
        api = DriftAPI(
            uba_identities_store_path=args.uba_identities_store,
            uba_events_store_path=args.uba_events_store,
            uba_baselines_store_path=args.uba_baselines_store,
            deltas_store_path=args.deltas_store,
            summaries_store_path=args.summaries_store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Get or build summary
        summary = api.get_delta_summary(
            identity_id=args.identity_id,
            baseline_hash=args.baseline_hash,
            observation_window_start=window_start,
            observation_window_end=window_end
        )
        
        # Export summary
        args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
        print(f"Summary exported to: {args.output}")
        
        print(f"\nDelta Summary:")
        print(f"  Summary ID: {summary.get('summary_id')}")
        print(f"  Identity ID: {args.identity_id}")
        print(f"  Baseline Hash: {args.baseline_hash[:16]}...")
        print(f"  Window: {summary.get('observation_window_start')} to {summary.get('observation_window_end')}")
        print(f"  Total Deltas: {summary.get('total_deltas')}")
        print(f"  Delta Types: {', '.join(summary.get('delta_types_present', []))}")
        print(f"  Summary Hash: {summary.get('summary_hash', '')[:16]}...")
        
    except DriftAPIError as e:
        print(f"Summary export failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
