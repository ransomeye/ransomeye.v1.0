#!/usr/bin/env python3
"""
RansomEye Threat Intelligence - Ingest Feed CLI
AUTHORITATIVE: Command-line tool for ingesting intelligence feeds
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_intel_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_intel_dir))

from api.intel_api import IntelAPI, IntelAPIError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Ingest intelligence feed'
    )
    parser.add_argument(
        '--feed',
        type=Path,
        required=True,
        help='Path to feed file (JSON, CSV, or STIX)'
    )
    parser.add_argument(
        '--source-name',
        required=True,
        help='Intelligence source name'
    )
    parser.add_argument(
        '--source-type',
        choices=['public_feed', 'internal_deception', 'internal_incident', 'internal_forensics', 'manual_analyst'],
        required=True,
        help='Type of intelligence source'
    )
    parser.add_argument(
        '--source-version',
        required=True,
        help='Source version (semver or timestamp)'
    )
    parser.add_argument(
        '--signature',
        required=True,
        help='Ed25519 signature of feed (hex-encoded)'
    )
    parser.add_argument(
        '--public-key-id',
        required=True,
        help='Public key identifier for signature verification'
    )
    parser.add_argument(
        '--iocs-store',
        type=Path,
        required=True,
        help='Path to IOCs store'
    )
    parser.add_argument(
        '--sources-store',
        type=Path,
        required=True,
        help='Path to intelligence sources store'
    )
    parser.add_argument(
        '--correlations-store',
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
        help='Path to output ingested IOCs JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize intel API
        api = IntelAPI(
            iocs_store_path=args.iocs_store,
            sources_store_path=args.sources_store,
            correlations_store_path=args.correlations_store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Register source
        source = api.register_source(
            source_name=args.source_name,
            source_type=args.source_type,
            source_version=args.source_version,
            signature=args.signature,
            public_key_id=args.public_key_id
        )
        
        # Ingest feed
        iocs = api.ingest_feed(
            feed_path=args.feed,
            source_id=source.get('source_id', ''),
            signature=args.signature,
            public_key_id=args.public_key_id
        )
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(iocs, indent=2, ensure_ascii=False))
            print(f"Feed ingested. Result written to: {args.output}")
        else:
            print(json.dumps(iocs, indent=2, ensure_ascii=False))
        
        print(f"\nIngestion Summary:")
        print(f"  Source ID: {source.get('source_id')}")
        print(f"  Source Name: {args.source_name}")
        print(f"  Source Type: {args.source_type}")
        print(f"  IOCs Ingested: {len(iocs)}")
        
    except IntelAPIError as e:
        print(f"Feed ingestion failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
