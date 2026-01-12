#!/usr/bin/env python3
"""
RansomEye HNMP Engine - Correlate HNMP CLI
AUTHORITATIVE: Command-line tool for correlating HNMP events
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_hnmp_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_hnmp_dir))

from api.hnmp_api import HNMPAPI, HNMPAPIError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Correlate HNMP events'
    )
    parser.add_argument(
        '--source-event-id',
        required=True,
        help='Source event identifier'
    )
    parser.add_argument(
        '--source-type',
        choices=['host', 'network', 'process', 'malware'],
        required=True,
        help='Source event type'
    )
    parser.add_argument(
        '--target-event-id',
        required=True,
        help='Target event identifier'
    )
    parser.add_argument(
        '--target-type',
        choices=['host', 'network', 'process', 'malware'],
        required=True,
        help='Target event type'
    )
    parser.add_argument(
        '--host-events',
        type=Path,
        required=True,
        help='Path to host events store'
    )
    parser.add_argument(
        '--network-events',
        type=Path,
        required=True,
        help='Path to network events store'
    )
    parser.add_argument(
        '--process-events',
        type=Path,
        required=True,
        help='Path to process events store'
    )
    parser.add_argument(
        '--malware-events',
        type=Path,
        required=True,
        help='Path to malware events store'
    )
    parser.add_argument(
        '--correlations',
        type=Path,
        required=True,
        help='Path to correlations store'
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
        help='Path to output correlation JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize HNMP API
        api = HNMPAPI(
            host_events_path=args.host_events,
            network_events_path=args.network_events,
            process_events_path=args.process_events,
            malware_events_path=args.malware_events,
            correlations_path=args.correlations,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Correlate events
        correlation = api.correlate_events(
            source_event_id=args.source_event_id,
            source_type=args.source_type,
            target_event_id=args.target_event_id,
            target_type=args.target_type
        )
        
        if not correlation:
            print("No factual correlation found between events")
            sys.exit(0)
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(correlation, indent=2, ensure_ascii=False))
            print(f"Correlation completed. Result written to: {args.output}")
        else:
            print(json.dumps(correlation, indent=2, ensure_ascii=False))
        
        print(f"\nCorrelation Summary:")
        print(f"  Correlation ID: {correlation.get('correlation_id')}")
        print(f"  Correlation Type: {correlation.get('correlation_type')}")
        print(f"  Source: {args.source_type} ({args.source_event_id[:8]}...)")
        print(f"  Target: {args.target_type} ({args.target_event_id[:8]}...)")
        
    except HNMPAPIError as e:
        print(f"Correlation failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
