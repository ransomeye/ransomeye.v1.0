#!/usr/bin/env python3
"""
RansomEye UBA Alert Context Engine - Build Alert Context CLI
AUTHORITATIVE: Command-line tool for building alert context blocks
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
        description='Build alert context block from UBA signals'
    )
    parser.add_argument(
        '--alert-id',
        required=True,
        help='Alert identifier'
    )
    parser.add_argument(
        '--uba-signal-ids',
        nargs='+',
        required=True,
        help='UBA signal identifiers (one or more)'
    )
    parser.add_argument(
        '--explanation-bundle-id',
        required=True,
        help='Explanation bundle identifier (SEE, mandatory)'
    )
    parser.add_argument(
        '--uba-signals-store',
        type=Path,
        help='Path to UBA Signal signals store (optional)'
    )
    parser.add_argument(
        '--uba-summaries-store',
        type=Path,
        help='Path to UBA Signal summaries store (optional)'
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
        help='Path to output context block JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize Alert Context API
        api = AlertContextAPI(
            store_path=args.store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir,
            uba_signals_store_path=args.uba_signals_store,
            uba_summaries_store_path=args.uba_summaries_store
        )
        
        # Build context block
        context_block = api.build_context(
            alert_id=args.alert_id,
            uba_signal_ids=args.uba_signal_ids,
            explanation_bundle_id=args.explanation_bundle_id
        )
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(context_block, indent=2, ensure_ascii=False))
            print(f"Alert context built. Result written to: {args.output}")
        else:
            print(json.dumps(context_block, indent=2, ensure_ascii=False))
        
        print(f"\nAlert Context Summary:")
        print(f"  Context Block ID: {context_block.get('context_block_id')}")
        print(f"  Alert ID: {args.alert_id}")
        print(f"  UBA Signal IDs: {len(context_block.get('uba_signal_ids', []))}")
        print(f"  Context Types: {', '.join(context_block.get('context_types', []))}")
        print(f"  Interpretation Guidance: {context_block.get('interpretation_guidance', '')}")
        print(f"  Explanation Bundle ID: {context_block.get('explanation_bundle_id', '')}")
        
    except AlertContextAPIError as e:
        print(f"Alert context build failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
