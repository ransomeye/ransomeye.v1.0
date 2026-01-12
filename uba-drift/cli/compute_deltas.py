#!/usr/bin/env python3
"""
RansomEye UBA Drift - Compute Deltas CLI
AUTHORITATIVE: Command-line tool for computing behavior deltas
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
        description='Compute behavior deltas'
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
        '--window-start',
        help='Observation window start (RFC3339, optional)'
    )
    parser.add_argument(
        '--window-end',
        help='Observation window end (RFC3339, optional)'
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
        help='Path to output deltas JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Parse window timestamps
        window_start = None
        if args.window_start:
            window_start = parse_timestamp(args.window_start)
        
        window_end = None
        if args.window_end:
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
        
        # Compute deltas
        deltas = api.compute_behavior_deltas(
            identity_id=args.identity_id,
            baseline_id=args.baseline_id,
            observation_window_start=window_start,
            observation_window_end=window_end
        )
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(deltas, indent=2, ensure_ascii=False))
            print(f"Deltas computed. Result written to: {args.output}")
        else:
            print(json.dumps(deltas, indent=2, ensure_ascii=False))
        
        print(f"\nDelta Computation Summary:")
        print(f"  Identity ID: {args.identity_id}")
        print(f"  Total Deltas: {len(deltas)}")
        
        # Count by type
        type_counts = {}
        for delta in deltas:
            delta_type = delta.get('delta_type', '')
            type_counts[delta_type] = type_counts.get(delta_type, 0) + 1
        
        for delta_type, count in sorted(type_counts.items()):
            print(f"  {delta_type}: {count}")
        
    except DriftAPIError as e:
        print(f"Delta computation failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
