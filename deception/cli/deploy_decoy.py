#!/usr/bin/env python3
"""
RansomEye Deception Framework - Deploy Decoy CLI
AUTHORITATIVE: Command-line tool for deploying decoys
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_deception_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_deception_dir))

from api.deception_api import DeceptionAPI, DeceptionAPIError


def load_decoy_config(config_path: Path) -> dict:
    """Load decoy configuration from file."""
    if not config_path.exists():
        return {}
    
    try:
        return json.loads(config_path.read_text())
    except Exception as e:
        print(f"Warning: Failed to load decoy config: {e}", file=sys.stderr)
        return {}


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Deploy decoy'
    )
    parser.add_argument(
        '--decoy-type',
        choices=['host', 'service', 'credential', 'file'],
        required=True,
        help='Type of decoy'
    )
    parser.add_argument(
        '--decoy-name',
        required=True,
        help='Human-readable decoy name'
    )
    parser.add_argument(
        '--decoy-config',
        type=Path,
        required=True,
        help='Path to decoy configuration JSON file'
    )
    parser.add_argument(
        '--deployment-target',
        required=True,
        help='Deployment target identifier (IP, hostname, or path)'
    )
    parser.add_argument(
        '--deployed-by',
        default='system',
        help='Entity deploying decoy (default: system)'
    )
    parser.add_argument(
        '--decoys-store',
        type=Path,
        required=True,
        help='Path to decoys store'
    )
    parser.add_argument(
        '--deployments-store',
        type=Path,
        required=True,
        help='Path to deployments store'
    )
    parser.add_argument(
        '--interactions-store',
        type=Path,
        required=True,
        help='Path to interactions store'
    )
    parser.add_argument(
        '--signals-store',
        type=Path,
        required=True,
        help='Path to signals store'
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
        help='Path to output deployment record JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load decoy configuration
        decoy_config = load_decoy_config(args.decoy_config)
        if not decoy_config:
            print("Error: Failed to load decoy configuration", file=sys.stderr)
            sys.exit(1)
        
        # Initialize deception API
        api = DeceptionAPI(
            decoys_store_path=args.decoys_store,
            deployments_store_path=args.deployments_store,
            interactions_store_path=args.interactions_store,
            signals_store_path=args.signals_store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Register decoy
        decoy = api.register_decoy(
            decoy_type=args.decoy_type,
            decoy_name=args.decoy_name,
            decoy_config=decoy_config,
            deployment_target=args.deployment_target
        )
        
        # Deploy decoy
        deployment = api.deploy_decoy(
            decoy_id=decoy.get('decoy_id', ''),
            deployed_by=args.deployed_by
        )
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(deployment, indent=2, ensure_ascii=False))
            print(f"Decoy deployed. Result written to: {args.output}")
        else:
            print(json.dumps(deployment, indent=2, ensure_ascii=False))
        
        print(f"\nDeployment Summary:")
        print(f"  Decoy ID: {decoy.get('decoy_id')}")
        print(f"  Decoy Type: {args.decoy_type}")
        print(f"  Decoy Name: {args.decoy_name}")
        print(f"  Deployment Status: {deployment.get('deployment_status')}")
        print(f"  Deployed At: {deployment.get('deployed_at')}")
        
    except DeceptionAPIError as e:
        print(f"Deployment failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
