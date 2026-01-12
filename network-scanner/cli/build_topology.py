#!/usr/bin/env python3
"""
RansomEye Network Scanner - Build Topology CLI
AUTHORITATIVE: Command-line tool for building network topology
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_scanner_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_scanner_dir))

from api.scanner_api import ScannerAPI, ScannerAPIError


def load_assets(assets_path: Path) -> list:
    """Load assets from file."""
    if not assets_path.exists():
        return []
    
    assets = []
    try:
        with open(assets_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                assets.append(json.loads(line))
    except Exception as e:
        print(f"Warning: Failed to load assets: {e}", file=sys.stderr)
    
    return assets


def load_services(services_path: Path) -> list:
    """Load services from file."""
    if not services_path.exists():
        return []
    
    services = []
    try:
        with open(services_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                services.append(json.loads(line))
    except Exception as e:
        print(f"Warning: Failed to load services: {e}", file=sys.stderr)
    
    return services


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Build network topology'
    )
    parser.add_argument(
        '--assets',
        type=Path,
        required=True,
        help='Path to assets JSONL file'
    )
    parser.add_argument(
        '--services',
        type=Path,
        required=True,
        help='Path to services JSONL file'
    )
    parser.add_argument(
        '--communication-data',
        type=Path,
        help='Path to communication data JSON file (optional)'
    )
    parser.add_argument(
        '--topology-store',
        type=Path,
        required=True,
        help='Path to topology edges store'
    )
    parser.add_argument(
        '--assets-store',
        type=Path,
        required=True,
        help='Path to assets store (for API initialization)'
    )
    parser.add_argument(
        '--services-store',
        type=Path,
        required=True,
        help='Path to services store (for API initialization)'
    )
    parser.add_argument(
        '--cve-matches-store',
        type=Path,
        required=True,
        help='Path to CVE matches store (for API initialization)'
    )
    parser.add_argument(
        '--cve-db',
        type=Path,
        required=True,
        help='Path to CVE database directory (for API initialization)'
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
        help='Path to output topology edges JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load assets and services
        assets = load_assets(args.assets)
        services = load_services(args.services)
        
        # Load communication data if provided
        communication_data = None
        if args.communication_data and args.communication_data.exists():
            try:
                communication_data = json.loads(args.communication_data.read_text())
            except Exception as e:
                print(f"Warning: Failed to load communication data: {e}", file=sys.stderr)
        
        # Initialize scanner API
        api = ScannerAPI(
            assets_store_path=args.assets_store,
            services_store_path=args.services_store,
            topology_store_path=args.topology_store,
            cve_matches_store_path=args.cve_matches_store,
            cve_db_path=args.cve_db,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Build topology
        edges = api.build_topology(
            assets=assets,
            services=services,
            communication_data=communication_data
        )
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(edges, indent=2, ensure_ascii=False))
            print(f"Topology built. Result written to: {args.output}")
        else:
            print(json.dumps(edges, indent=2, ensure_ascii=False))
        
        print(f"\nTopology Summary:")
        print(f"  Assets: {len(assets)}")
        print(f"  Services: {len(services)}")
        print(f"  Edges: {len(edges)}")
        
    except ScannerAPIError as e:
        print(f"Topology build failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
