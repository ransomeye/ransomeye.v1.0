#!/usr/bin/env python3
"""
RansomEye Enterprise Risk Index - Export Risk with Context CLI
AUTHORITATIVE: Command-line tool for exporting risk scores with UBA context
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_risk_index_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_risk_index_dir))

from api.risk_api import RiskAPI, RiskAPIError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Export risk score with UBA context'
    )
    parser.add_argument(
        '--identity-id',
        required=True,
        help='Identity identifier'
    )
    parser.add_argument(
        '--store',
        type=Path,
        required=True,
        help='Path to risk score store'
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
        help='Path to output risk score JSON'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize Risk API
        api = RiskAPI(
            store_path=args.store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Get risk explanation
        explanation = api.get_risk_explanation(args.identity_id)
        
        if not explanation:
            print(f"No risk score found for identity: {args.identity_id}", file=sys.stderr)
            sys.exit(1)
        
        # Export explanation
        args.output.write_text(json.dumps(explanation, indent=2, ensure_ascii=False))
        print(f"Risk explanation exported to: {args.output}")
        
        print(f"\nRisk Explanation:")
        print(f"  Score ID: {explanation.get('score_id')}")
        print(f"  Identity ID: {args.identity_id}")
        print(f"  Risk Score: {explanation.get('risk_score', 0.0):.2f}")
        print(f"  Severity Band: {explanation.get('severity_band', '')}")
        print(f"  UBA Context Applied: {explanation.get('uba_context_applied', False)}")
        if explanation.get('uba_context_applied', False):
            print(f"  Context Modifiers: {', '.join(explanation.get('context_modifiers', []))}")
        print(f"  Explanation Bundle ID: {explanation.get('risk_explanation_bundle_id', '')}")
        print(f"  Explanation Chain: {explanation.get('explanation_chain', '')}")
        
    except RiskAPIError as e:
        print(f"Risk export failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
