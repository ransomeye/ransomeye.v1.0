#!/usr/bin/env python3
"""
RansomEye Explanation Assembly Engine - Assemble Explanation CLI
AUTHORITATIVE: Command-line tool for assembling explanations into audience-specific views
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_assembly_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_assembly_dir))

from api.assembly_api import AssemblyAPI, AssemblyAPIError


def load_json_file(file_path: Path) -> dict:
    """Load JSON object from file."""
    if not file_path.exists():
        return {}
    
    try:
        return json.loads(file_path.read_text())
    except Exception as e:
        print(f"Warning: Failed to load {file_path}: {e}", file=sys.stderr)
        return {}


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Assemble incident explanation into audience-specific view'
    )
    parser.add_argument(
        '--incident-id',
        required=True,
        help='Incident identifier'
    )
    parser.add_argument(
        '--view-type',
        required=True,
        choices=['SOC_ANALYST', 'INCIDENT_COMMANDER', 'EXECUTIVE', 'REGULATOR'],
        help='View type (exactly 4 types, no others)'
    )
    parser.add_argument(
        '--source-explanation-bundle-ids',
        nargs='*',
        default=[],
        help='SEE bundle identifiers (optional)'
    )
    parser.add_argument(
        '--source-alert-ids',
        nargs='*',
        default=[],
        help='Alert identifiers (optional)'
    )
    parser.add_argument(
        '--source-context-block-ids',
        nargs='*',
        default=[],
        help='Alert context block identifiers (optional)'
    )
    parser.add_argument(
        '--source-risk-ids',
        nargs='*',
        default=[],
        help='Risk score identifiers (optional)'
    )
    parser.add_argument(
        '--source-content',
        type=Path,
        help='Path to source content JSON file (optional)'
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
        help='Path to output assembled explanation JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load source content
        source_content = load_json_file(args.source_content) if args.source_content else {}
        
        # Initialize Assembly API
        api = AssemblyAPI(
            store_path=args.store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Assemble explanation
        assembled_explanation = api.assemble_incident_explanation(
            incident_id=args.incident_id,
            view_type=args.view_type,
            source_explanation_bundle_ids=args.source_explanation_bundle_ids,
            source_alert_ids=args.source_alert_ids,
            source_context_block_ids=args.source_context_block_ids,
            source_risk_ids=args.source_risk_ids,
            source_content=source_content
        )
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(assembled_explanation, indent=2, ensure_ascii=False))
            print(f"Explanation assembled. Result written to: {args.output}")
        else:
            print(json.dumps(assembled_explanation, indent=2, ensure_ascii=False))
        
        print(f"\nAssembled Explanation Summary:")
        print(f"  Assembled Explanation ID: {assembled_explanation.get('assembled_explanation_id')}")
        print(f"  Incident ID: {args.incident_id}")
        print(f"  View Type: {assembled_explanation.get('view_type', '')}")
        print(f"  Content Blocks: {len(assembled_explanation.get('content_blocks', []))}")
        print(f"  Ordering Rules Applied: {', '.join(assembled_explanation.get('ordering_rules_applied', []))}")
        print(f"  Integrity Hash: {assembled_explanation.get('integrity_hash', '')}")
        
    except AssemblyAPIError as e:
        print(f"Explanation assembly failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
