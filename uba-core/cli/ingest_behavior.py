#!/usr/bin/env python3
"""
RansomEye UBA Core - Ingest Behavior CLI
AUTHORITATIVE: Command-line tool for ingesting behavior events
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_uba_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_uba_dir))

from api.uba_api import UBAAPI, UBAAPIError


def load_event(event_path: Path) -> dict:
    """Load behavior event from file."""
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
        description='Ingest behavior event'
    )
    parser.add_argument(
        '--event',
        type=Path,
        required=True,
        help='Path to behavior event JSON file'
    )
    parser.add_argument(
        '--user-id',
        required=True,
        help='User identifier'
    )
    parser.add_argument(
        '--identity-type',
        choices=['human', 'service', 'machine'],
        required=True,
        help='Identity type'
    )
    parser.add_argument(
        '--auth-domain',
        help='Authentication domain (optional, uses UBA_AUTH_DOMAIN env var if not provided)'
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
        help='Path to output normalized event JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load event
        raw_event = load_event(args.event)
        if not raw_event:
            print("Error: Failed to load event", file=sys.stderr)
            sys.exit(1)
        
        # Initialize UBA API
        api = UBAAPI(
            identities_store_path=args.identities_store,
            events_store_path=args.events_store,
            baselines_store_path=args.baselines_store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Ingest event
        normalized = api.ingest_behavior_event(
            raw_event=raw_event,
            user_id=args.user_id,
            identity_type=args.identity_type,
            auth_domain=args.auth_domain
        )
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(normalized, indent=2, ensure_ascii=False))
            print(f"Event ingested. Result written to: {args.output}")
        else:
            print(json.dumps(normalized, indent=2, ensure_ascii=False))
        
        print(f"\nIngestion Summary:")
        print(f"  Event ID: {normalized.get('event_id')}")
        print(f"  Identity ID: {normalized.get('identity_id')}")
        print(f"  Event Type: {normalized.get('event_type')}")
        print(f"  Source Component: {normalized.get('source_component')}")
        print(f"  Timestamp: {normalized.get('timestamp')}")
        
    except UBAAPIError as e:
        print(f"Event ingestion failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
