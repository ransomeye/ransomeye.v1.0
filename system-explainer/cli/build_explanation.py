#!/usr/bin/env python3
"""
RansomEye System Explanation Engine - Explanation Builder CLI
AUTHORITATIVE: Command-line tool for building explanation bundles
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_explainer_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_explainer_dir))

from api.explainer_api import ExplainerAPI, ExplainerAPIError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Build signed explanation bundle'
    )
    parser.add_argument(
        '--explanation-type',
        choices=[
            'incident_explanation',
            'killchain_stage_advancement',
            'campaign_inference',
            'risk_score_change',
            'policy_recommendation'
        ],
        required=True,
        help='Type of explanation to build'
    )
    parser.add_argument(
        '--subject-id',
        required=True,
        help='Subject identifier (incident ID, killchain event ID, etc.)'
    )
    parser.add_argument(
        '--ledger',
        type=Path,
        required=True,
        help='Path to audit ledger file'
    )
    parser.add_argument(
        '--private-key',
        type=Path,
        required=True,
        help='Path to private key file for signing'
    )
    parser.add_argument(
        '--key-id',
        required=True,
        help='Key identifier'
    )
    parser.add_argument(
        '--killchain-store',
        type=Path,
        help='Path to killchain store (optional)'
    )
    parser.add_argument(
        '--threat-graph',
        type=Path,
        help='Path to threat graph store (optional)'
    )
    parser.add_argument(
        '--risk-store',
        type=Path,
        help='Path to risk store (optional)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Path to output explanation bundle JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize explainer API
        api = ExplainerAPI(
            ledger_path=args.ledger,
            private_key_path=args.private_key,
            key_id=args.key_id,
            killchain_store_path=args.killchain_store,
            threat_graph_path=args.threat_graph,
            risk_store_path=args.risk_store
        )
        
        # Build explanation based on type
        if args.explanation_type == 'incident_explanation':
            bundle = api.explain_incident(args.subject_id)
        elif args.explanation_type == 'killchain_stage_advancement':
            bundle = api.explain_killchain_stage(args.subject_id)
        elif args.explanation_type == 'campaign_inference':
            bundle = api.explain_campaign_inference(args.subject_id)
        elif args.explanation_type == 'risk_score_change':
            bundle = api.explain_risk_score_change(args.subject_id)
        elif args.explanation_type == 'policy_recommendation':
            bundle = api.explain_policy_recommendation(args.subject_id)
        else:
            raise ExplainerAPIError(f"Unknown explanation type: {args.explanation_type}")
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(bundle, indent=2, ensure_ascii=False))
            print(f"Explanation bundle built successfully. Result written to: {args.output}")
        else:
            print(json.dumps(bundle, indent=2, ensure_ascii=False))
        
        print(f"\nExplanation Summary:")
        print(f"  Bundle ID: {bundle['bundle_id']}")
        print(f"  Type: {bundle['explanation_type']}")
        print(f"  Subject: {bundle['subject_id']}")
        print(f"  Reasoning steps: {len(bundle['reasoning_chain'])}")
        print(f"  Evidence references: {len(bundle['evidence_references'])}")
        print(f"  Causal links: {len(bundle['causal_links'])}")
        print(f"  Signed: {bool(bundle.get('signature'))}")
        
    except ExplainerAPIError as e:
        print(f"Explanation build failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
