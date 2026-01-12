#!/usr/bin/env python3
"""
RansomEye DPI Advanced - Run Probe CLI
AUTHORITATIVE: Command-line tool for running DPI probe
"""

import sys
import json
from pathlib import Path
import argparse
from datetime import datetime, timezone

# Add parent directory to path for imports
_dpi_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_dpi_dir))

from api.dpi_api import DPIAPI, DPIAPIError


def load_privacy_policy(policy_path: Path) -> dict:
    """Load privacy policy from file."""
    if not policy_path.exists():
        return {
            'privacy_mode': 'FORENSIC',
            'ip_redaction': 'none',
            'port_redaction': 'none',
            'dns_redaction': 'none'
        }
    
    try:
        return json.loads(policy_path.read_text())
    except Exception as e:
        print(f"Warning: Failed to load privacy policy: {e}", file=sys.stderr)
        return {
            'privacy_mode': 'FORENSIC',
            'ip_redaction': 'none',
            'port_redaction': 'none',
            'dns_redaction': 'none'
        }


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Run DPI probe'
    )
    parser.add_argument(
        '--interface',
        required=True,
        help='Network interface to monitor'
    )
    parser.add_argument(
        '--privacy-policy',
        type=Path,
        required=True,
        help='Path to privacy policy JSON file'
    )
    parser.add_argument(
        '--flows-store',
        type=Path,
        required=True,
        help='Path to flows store'
    )
    parser.add_argument(
        '--asset-profiles-store',
        type=Path,
        required=True,
        help='Path to asset profiles store'
    )
    parser.add_argument(
        '--upload-chunks-store',
        type=Path,
        required=True,
        help='Path to upload chunks store'
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
        '--flow-timeout',
        type=int,
        default=300,
        help='Flow timeout in seconds (default: 300)'
    )
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=1000,
        help='Chunk size for uploads (default: 1000)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load privacy policy
        privacy_policy = load_privacy_policy(args.privacy_policy)
        
        # Initialize DPI API
        api = DPIAPI(
            flows_store_path=args.flows_store,
            asset_profiles_store_path=args.asset_profiles_store,
            upload_chunks_store_path=args.upload_chunks_store,
            privacy_policy=privacy_policy,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir,
            flow_timeout=args.flow_timeout,
            chunk_size=args.chunk_size
        )
        
        print(f"DPI Probe started on interface: {args.interface}")
        print(f"Privacy mode: {privacy_policy.get('privacy_mode', 'FORENSIC')}")
        print("Press Ctrl+C to stop")
        
        # For Phase L, this is a stub
        # In production, would start actual packet capture loop
        # Simulate processing
        import time
        try:
            while True:
                time.sleep(1)
                # In production, would process packets from AF_PACKET or eBPF
        except KeyboardInterrupt:
            print("\nDPI Probe stopped")
        
    except DPIAPIError as e:
        print(f"DPI probe failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
