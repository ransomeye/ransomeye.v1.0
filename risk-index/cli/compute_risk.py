#!/usr/bin/env python3
"""
RansomEye Enterprise Risk Index - Risk Computation CLI
AUTHORITATIVE: Command-line tool for computing enterprise risk scores
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_risk_index_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_risk_index_dir))

from api.risk_api import RiskAPI, RiskAPIError


def load_signals(signals_path: Path) -> list:
    """Load signals from JSON file."""
    if not signals_path.exists():
        return []
    
    try:
        content = signals_path.read_text()
        # Try to parse as JSON array
        signals = json.loads(content)
        if isinstance(signals, list):
            return signals
        elif isinstance(signals, dict):
            # If it's a dict with a 'signals' key, extract that
            return signals.get('signals', [])
        else:
            return []
    except Exception as e:
        print(f"Warning: Failed to load signals from {signals_path}: {e}", file=sys.stderr)
        return []


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Compute Enterprise Risk Index score'
    )
    parser.add_argument(
        '--incidents',
        type=Path,
        help='Path to incidents signals JSON file (optional)'
    )
    parser.add_argument(
        '--ai-metadata',
        type=Path,
        help='Path to AI metadata signals JSON file (optional)'
    )
    parser.add_argument(
        '--policy-decisions',
        type=Path,
        help='Path to policy decision signals JSON file (optional)'
    )
    parser.add_argument(
        '--threat-correlation',
        type=Path,
        help='Path to threat correlation signals JSON file (optional, future)'
    )
    parser.add_argument(
        '--uba',
        type=Path,
        help='Path to UBA signals JSON file (optional, future)'
    )
    parser.add_argument(
        '--weights',
        type=Path,
        help='Path to weights configuration JSON file (optional)'
    )
    parser.add_argument(
        '--decay-config',
        type=Path,
        help='Path to temporal decay configuration JSON file (optional)'
    )
    parser.add_argument(
        '--store',
        type=Path,
        required=True,
        help='Path to risk score store file'
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
        '--computed-by',
        default='system',
        help='Entity that computed risk score (default: system)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Path to output risk score JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load signals (read-only)
        incidents = load_signals(args.incidents) if args.incidents else []
        ai_metadata = load_signals(args.ai_metadata) if args.ai_metadata else []
        policy_decisions = load_signals(args.policy_decisions) if args.policy_decisions else []
        threat_correlation = load_signals(args.threat_correlation) if args.threat_correlation else None
        uba = load_signals(args.uba) if args.uba else None
        
        # Load weights configuration
        weights = None
        if args.weights and args.weights.exists():
            weights = json.loads(args.weights.read_text())
        
        # Load decay configuration
        decay_config = None
        if args.decay_config and args.decay_config.exists():
            decay_config = json.loads(args.decay_config.read_text())
        
        # Initialize risk API
        api = RiskAPI(
            store_path=args.store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir,
            weights=weights,
            decay_config=decay_config
        )
        
        # Compute risk score
        score_record = api.compute_risk(
            incidents=incidents,
            ai_metadata=ai_metadata,
            policy_decisions=policy_decisions,
            threat_correlation=threat_correlation,
            uba=uba,
            computed_by=args.computed_by
        )
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(score_record, indent=2, ensure_ascii=False))
            print(f"Risk score computed successfully. Record written to: {args.output}")
        else:
            print(json.dumps(score_record, indent=2, ensure_ascii=False))
        
        print(f"\nRisk Score: {score_record['risk_score']:.2f}")
        print(f"Severity Band: {score_record['severity_band']}")
        print(f"Confidence: {score_record['confidence_score']:.2f}")
        print(f"Component Scores:")
        for component, score in score_record['component_scores'].items():
            print(f"  {component}: {score:.2f}")
        
    except RiskAPIError as e:
        print(f"Risk computation failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
