#!/usr/bin/env python3
"""
RansomEye Enterprise Risk Index - Compute Risk with UBA CLI
AUTHORITATIVE: Command-line tool for computing risk with UBA context
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_risk_index_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_risk_index_dir))

from api.risk_api import RiskAPI, RiskAPIError


def load_json_file(file_path: Path) -> list:
    """Load JSON array from file."""
    if not file_path.exists():
        return []
    
    try:
        return json.loads(file_path.read_text())
    except Exception as e:
        print(f"Warning: Failed to load {file_path}: {e}", file=sys.stderr)
        return []


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Compute risk with UBA context'
    )
    parser.add_argument(
        '--identity-id',
        required=True,
        help='Identity identifier'
    )
    parser.add_argument(
        '--incidents',
        type=Path,
        help='Path to incidents JSON file (optional)'
    )
    parser.add_argument(
        '--ai-metadata',
        type=Path,
        help='Path to AI metadata JSON file (optional)'
    )
    parser.add_argument(
        '--policy-decisions',
        type=Path,
        help='Path to policy decisions JSON file (optional)'
    )
    parser.add_argument(
        '--explanation-bundle-id',
        required=True,
        help='Explanation bundle identifier (SEE, mandatory)'
    )
    parser.add_argument(
        '--uba-signal-ids',
        nargs='*',
        help='UBA signal identifiers (optional)'
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
        help='Path to output risk score JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load input data
        incidents = load_json_file(args.incidents) if args.incidents else []
        ai_metadata = load_json_file(args.ai_metadata) if args.ai_metadata else []
        policy_decisions = load_json_file(args.policy_decisions) if args.policy_decisions else []
        
        # Initialize Risk API
        api = RiskAPI(
            store_path=args.store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir,
            uba_signals_store_path=args.uba_signals_store,
            uba_summaries_store_path=args.uba_summaries_store
        )
        
        # Compute risk with UBA context
        score_record = api.get_risk_with_context(
            identity_id=args.identity_id,
            incidents=incidents,
            ai_metadata=ai_metadata,
            policy_decisions=policy_decisions,
            risk_explanation_bundle_id=args.explanation_bundle_id,
            uba_signal_ids=args.uba_signal_ids
        )
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(score_record, indent=2, ensure_ascii=False))
            print(f"Risk computed. Result written to: {args.output}")
        else:
            print(json.dumps(score_record, indent=2, ensure_ascii=False))
        
        print(f"\nRisk Computation Summary:")
        print(f"  Score ID: {score_record.get('score_id')}")
        print(f"  Identity ID: {args.identity_id}")
        print(f"  Risk Score: {score_record.get('risk_score', 0.0):.2f}")
        print(f"  Severity Band: {score_record.get('severity_band', '')}")
        print(f"  UBA Context Applied: {score_record.get('uba_context_applied', False)}")
        if score_record.get('uba_context_applied', False):
            print(f"  Context Modifiers: {', '.join(score_record.get('context_modifiers', []))}")
        print(f"  Explanation Bundle ID: {score_record.get('risk_explanation_bundle_id', '')}")
        
    except RiskAPIError as e:
        print(f"Risk computation failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
