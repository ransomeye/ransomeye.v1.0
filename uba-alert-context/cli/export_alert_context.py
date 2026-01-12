#!/usr/bin/env python3
"""
RansomEye UBA Alert Context Engine - Export Alert Context CLI
AUTHORITATIVE: Command-line tool for exporting alert context blocks
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_alert_context_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_alert_context_dir))

from api.alert_context_api import AlertContextAPI, AlertContextAPIError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Export alert context block'
    )
    parser.add_argument(
        '--alert-id',
        required=True,
        help='Alert identifier'
    )
    parser.add_argument(
        '--store',
        type=Path,
        required=True,
        help='Path to context store file'
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
        required=True,
        help='Path to output context block JSON'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize Alert Context API
        api = AlertContextAPI(
            store_path=args.store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Get alert context
        context_block = api.get_alert_context(args.alert_id)
        
        if not context_block:
            print(f"No context block found for alert: {args.alert_id}", file=sys.stderr)
            sys.exit(1)
        
        # Export context block
        args.output.write_text(json.dumps(context_block, indent=2, ensure_ascii=False))
        print(f"Alert context exported to: {args.output}")
        
        print(f"\nAlert Context:")
        print(f"  Context Block ID: {context_block.get('context_block_id')}")
        print(f"  Alert ID: {args.alert_id}")
        print(f"  UBA Signal IDs: {len(context_block.get('uba_signal_ids', []))}")
        print(f"  Context Types: {', '.join(context_block.get('context_types', []))}")
        print(f"  Human Readable Summary: {context_block.get('human_readable_summary', '')}")
        print(f"  Interpretation Guidance: {context_block.get('interpretation_guidance', '')}")
        print(f"  Explanation Bundle ID: {context_block.get('explanation_bundle_id', '')}")
        
    except AlertContextAPIError as e:
        print(f"Alert context export failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
