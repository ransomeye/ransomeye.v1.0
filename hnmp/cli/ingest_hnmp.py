#!/usr/bin/env python3
"""
RansomEye HNMP Engine - Ingest HNMP CLI
AUTHORITATIVE: Command-line tool for ingesting HNMP events
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_hnmp_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_hnmp_dir))

from api.hnmp_api import HNMPAPI, HNMPAPIError


def load_event(event_path: Path) -> dict:
    """Load event from file."""
    if not event_path.exists():
        return {}
    
    try:
        return json.loads(event_path.read_text())
    except Exception as e:
        print(f"Warning: Failed to load event: {e}", file=sys.stderr)
        return {}


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Ingest HNMP event'
    )
    parser.add_argument(
        '--event',
        type=Path,
        required=True,
        help='Path to event JSON file'
    )
    parser.add_argument(
        '--event-type',
        choices=['host', 'network', 'process', 'malware'],
        required=True,
        help='Type of event'
    )
    parser.add_argument(
        '--source-agent',
        choices=['linux_agent', 'windows_agent', 'dpi_probe', 'forensics_engine', 'deception_framework', 'threat_intel_engine', 'network_scanner'],
        required=True,
        help='Source agent identifier'
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
        help='Path to output normalized event JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load event
        raw_event = load_event(args.event)
        if not raw_event:
            print("Error: Failed to load event", file=sys.stderr)
            sys.exit(1)
        
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
        
        # Ingest event
        normalized = api.ingest_event(
            raw_event=raw_event,
            event_type=args.event_type,
            source_agent=args.source_agent
        )
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(normalized, indent=2, ensure_ascii=False))
            print(f"Event ingested. Result written to: {args.output}")
        else:
            print(json.dumps(normalized, indent=2, ensure_ascii=False))
        
        print(f"\nIngestion Summary:")
        print(f"  Event ID: {normalized.get('event_id')}")
        print(f"  Event Type: {args.event_type}")
        print(f"  Source Agent: {args.source_agent}")
        print(f"  Timestamp: {normalized.get('timestamp')}")
        
    except HNMPAPIError as e:
        print(f"Event ingestion failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
