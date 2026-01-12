#!/usr/bin/env python3
"""
RansomEye Network Scanner - Scan Network CLI
AUTHORITATIVE: Command-line tool for active network scanning
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_scanner_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_scanner_dir))

from api.scanner_api import ScannerAPI, ScannerAPIError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Perform active network scan'
    )
    parser.add_argument(
        '--scan-scope',
        required=True,
        help='Scan scope (CIDR notation, e.g., 192.168.1.0/24)'
    )
    parser.add_argument(
        '--ports',
        type=int,
        nargs='+',
        help='Ports to scan (default: common ports)'
    )
    parser.add_argument(
        '--scan-type',
        choices=['syn', 'connect', 'udp'],
        default='syn',
        help='Scan type (default: syn)'
    )
    parser.add_argument(
        '--rate-limit',
        type=int,
        default=100,
        help='Rate limit in packets per second (default: 100)'
    )
    parser.add_argument(
        '--assets-store',
        type=Path,
        required=True,
        help='Path to assets store'
    )
    parser.add_argument(
        '--services-store',
        type=Path,
        required=True,
        help='Path to services store'
    )
    parser.add_argument(
        '--topology-store',
        type=Path,
        required=True,
        help='Path to topology edges store'
    )
    parser.add_argument(
        '--cve-matches-store',
        type=Path,
        required=True,
        help='Path to CVE matches store'
    )
    parser.add_argument(
        '--cve-db',
        type=Path,
        required=True,
        help='Path to CVE database directory'
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
        help='Path to output scan results JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize scanner API
        api = ScannerAPI(
            assets_store_path=args.assets_store,
            services_store_path=args.services_store,
            topology_store_path=args.topology_store,
            cve_matches_store_path=args.cve_matches_store,
            cve_db_path=args.cve_db,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir,
            rate_limit=args.rate_limit
        )
        
        # Perform scan
        result = api.scan_network(
            scan_scope=args.scan_scope,
            ports=args.ports,
            scan_type=args.scan_type
        )
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False))
            print(f"Scan completed. Result written to: {args.output}")
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        print(f"\nScan Summary:")
        print(f"  Scan Scope: {args.scan_scope}")
        print(f"  Assets Discovered: {len(result.get('assets', []))}")
        print(f"  Services Discovered: {len(result.get('services', []))}")
        
    except ScannerAPIError as e:
        print(f"Scan failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
