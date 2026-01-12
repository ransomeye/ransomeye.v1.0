#!/usr/bin/env python3
"""
RansomEye UBA Signal - Interpret Signals CLI
AUTHORITATIVE: Command-line tool for interpreting drift deltas into signals
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_signal_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_signal_dir))

from api.signal_api import SignalAPI, SignalAPIError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Interpret drift deltas into signals'
    )
    parser.add_argument(
        '--identity-id',
        required=True,
        help='Identity identifier'
    )
    parser.add_argument(
        '--delta-ids',
        required=True,
        nargs='+',
        help='Delta identifiers (one or more)'
    )
    parser.add_argument(
        '--explanation-bundle-id',
        required=True,
        help='Explanation bundle identifier (SEE)'
    )
    parser.add_argument(
        '--killchain-ids',
        nargs='*',
        help='KillChain evidence IDs (optional)'
    )
    parser.add_argument(
        '--graph-ids',
        nargs='*',
        help='Threat Graph entity/edge IDs (optional)'
    )
    parser.add_argument(
        '--incident-ids',
        nargs='*',
        help='Incident IDs (optional)'
    )
    parser.add_argument(
        '--drift-deltas-store',
        type=Path,
        required=True,
        help='Path to UBA Drift deltas store'
    )
    parser.add_argument(
        '--drift-summaries-store',
        type=Path,
        required=True,
        help='Path to UBA Drift summaries store'
    )
    parser.add_argument(
        '--signals-store',
        type=Path,
        required=True,
        help='Path to signals store'
    )
    parser.add_argument(
        '--summaries-store',
        type=Path,
        required=True,
        help='Path to summaries store'
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
        help='Path to output signals JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Build contextual inputs
        contextual_inputs = {
            'killchain_ids': args.killchain_ids or [],
            'graph_ids': args.graph_ids or [],
            'incident_ids': args.incident_ids or []
        }
        
        # Initialize Signal API
        api = SignalAPI(
            drift_deltas_store_path=args.drift_deltas_store,
            drift_summaries_store_path=args.drift_summaries_store,
            signals_store_path=args.signals_store,
            summaries_store_path=args.summaries_store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Interpret deltas
        signals = api.interpret_deltas(
            identity_id=args.identity_id,
            delta_ids=args.delta_ids,
            contextual_inputs=contextual_inputs,
            explanation_bundle_id=args.explanation_bundle_id
        )
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(signals, indent=2, ensure_ascii=False))
            print(f"Signals interpreted. Result written to: {args.output}")
        else:
            print(json.dumps(signals, indent=2, ensure_ascii=False))
        
        print(f"\nSignal Interpretation Summary:")
        print(f"  Identity ID: {args.identity_id}")
        print(f"  Total Signals: {len(signals)}")
        
        # Count by type
        type_counts = {}
        authority_required_count = 0
        for signal in signals:
            interpretation_type = signal.get('interpretation_type', '')
            type_counts[interpretation_type] = type_counts.get(interpretation_type, 0) + 1
            if signal.get('authority_required', False):
                authority_required_count += 1
        
        for interpretation_type, count in sorted(type_counts.items()):
            print(f"  {interpretation_type}: {count}")
        
        if authority_required_count > 0:
            print(f"  Authority Required: {authority_required_count} signal(s)")
        
    except SignalAPIError as e:
        print(f"Signal interpretation failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
