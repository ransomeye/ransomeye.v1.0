#!/usr/bin/env python3
"""
RansomEye UBA Core - Build Baseline CLI
AUTHORITATIVE: Command-line tool for building identity baselines
"""

import sys
import json
from pathlib import Path
import argparse
from datetime import datetime, timezone

# Add parent directory to path for imports
_uba_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_uba_dir))

from api.uba_api import UBAAPI, UBAAPIError


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse timestamp string to datetime."""
    try:
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except Exception as e:
        raise ValueError(f"Invalid timestamp format: {e}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Build identity baseline'
    )
    parser.add_argument(
        '--identity-id',
        required=True,
        help='Identity identifier'
    )
    parser.add_argument(
        '--window-start',
        help='Baseline window start (RFC3339, optional)'
    )
    parser.add_argument(
        '--window-end',
        help='Baseline window end (RFC3339, optional)'
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
        help='Path to output baseline JSON (optional)'
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
        
        # Initialize UBA API
        api = UBAAPI(
            identities_store_path=args.identities_store,
            events_store_path=args.events_store,
            baselines_store_path=args.baselines_store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Build baseline
        baseline = api.build_identity_baseline(
            identity_id=args.identity_id,
            window_start=window_start,
            window_end=window_end
        )
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(baseline, indent=2, ensure_ascii=False))
            print(f"Baseline built. Result written to: {args.output}")
        else:
            print(json.dumps(baseline, indent=2, ensure_ascii=False))
        
        print(f"\nBaseline Summary:")
        print(f"  Baseline ID: {baseline.get('baseline_id')}")
        print(f"  Identity ID: {args.identity_id}")
        print(f"  Window: {baseline.get('baseline_window_start')} to {baseline.get('baseline_window_end')}")
        print(f"  Event Types: {len(baseline.get('observed_event_types', []))}")
        print(f"  Hosts: {len(baseline.get('observed_hosts', []))}")
        print(f"  Time Buckets: {len(baseline.get('observed_time_buckets', []))}")
        print(f"  Privileges: {len(baseline.get('observed_privileges', []))}")
        print(f"  Baseline Hash: {baseline.get('baseline_hash', '')[:16]}...")
        
    except UBAAPIError as e:
        print(f"Baseline build failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
