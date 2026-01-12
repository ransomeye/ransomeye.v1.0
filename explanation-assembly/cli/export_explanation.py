#!/usr/bin/env python3
"""
RansomEye Explanation Assembly Engine - Export Explanation CLI
AUTHORITATIVE: Command-line tool for exporting assembled explanations
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_assembly_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_assembly_dir))

from api.assembly_api import AssemblyAPI, AssemblyAPIError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Export assembled explanation'
    )
    parser.add_argument(
        '--assembled-explanation-id',
        required=True,
        help='Assembled explanation identifier'
    )
    parser.add_argument(
        '--store',
        type=Path,
        required=True,
        help='Path to assembly store file'
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
        help='Path to output assembled explanation JSON'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize Assembly API
        api = AssemblyAPI(
            store_path=args.store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Get assembled explanation
        assembled_explanation = api.get_assembled_explanation(args.assembled_explanation_id)
        
        if not assembled_explanation:
            print(f"No assembled explanation found: {args.assembled_explanation_id}", file=sys.stderr)
            sys.exit(1)
        
        # Export assembled explanation
        args.output.write_text(json.dumps(assembled_explanation, indent=2, ensure_ascii=False))
        print(f"Assembled explanation exported to: {args.output}")
        
        print(f"\nAssembled Explanation:")
        print(f"  Assembled Explanation ID: {assembled_explanation.get('assembled_explanation_id')}")
        print(f"  Incident ID: {assembled_explanation.get('incident_id', '')}")
        print(f"  View Type: {assembled_explanation.get('view_type', '')}")
        print(f"  Content Blocks: {len(assembled_explanation.get('content_blocks', []))}")
        print(f"  Ordering Rules Applied: {', '.join(assembled_explanation.get('ordering_rules_applied', []))}")
        print(f"  Integrity Hash: {assembled_explanation.get('integrity_hash', '')}")
        
    except AssemblyAPIError as e:
        print(f"Explanation export failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
