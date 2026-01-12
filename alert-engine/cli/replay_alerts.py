#!/usr/bin/env python3
"""
RansomEye Alert Engine - Replay Alerts CLI
AUTHORITATIVE: Command-line tool for replaying alerts from audit ledger
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_alert_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_alert_dir))

from api.alert_api import AlertAPI, AlertAPIError


def load_incident(incident_path: Path) -> dict:
    """Load incident from file."""
    if not incident_path.exists():
        return {}
    
    try:
        return json.loads(incident_path.read_text())
    except Exception as e:
        print(f"Warning: Failed to load incident: {e}", file=sys.stderr)
        return {}


def load_routing_decision(decision_path: Path) -> dict:
    """Load routing decision from file."""
    if not decision_path.exists():
        return {}
    
    try:
        return json.loads(decision_path.read_text())
    except Exception as e:
        print(f"Warning: Failed to load routing decision: {e}", file=sys.stderr)
        return {}


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Replay alerts from incidents and routing decisions'
    )
    parser.add_argument(
        '--incident',
        type=Path,
        required=True,
        help='Path to incident JSON file'
    )
    parser.add_argument(
        '--routing-decision',
        type=Path,
        required=True,
        help='Path to routing decision JSON file'
    )
    parser.add_argument(
        '--explanation-bundle-id',
        required=True,
        help='Explanation bundle identifier (SEE)'
    )
    parser.add_argument(
        '--risk-score',
        type=float,
        required=True,
        help='Risk score at time of emission'
    )
    parser.add_argument(
        '--alerts-store',
        type=Path,
        required=True,
        help='Path to alerts store'
    )
    parser.add_argument(
        '--suppressions-store',
        type=Path,
        required=True,
        help='Path to suppressions store'
    )
    parser.add_argument(
        '--escalations-store',
        type=Path,
        required=True,
        help='Path to escalations store'
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
        help='Path to output alert JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load incident and routing decision
        incident = load_incident(args.incident)
        routing_decision = load_routing_decision(args.routing_decision)
        
        if not incident or not routing_decision:
            print("Error: Failed to load incident or routing decision", file=sys.stderr)
            sys.exit(1)
        
        # Initialize alert API
        api = AlertAPI(
            alerts_store_path=args.alerts_store,
            suppressions_store_path=args.suppressions_store,
            escalations_store_path=args.escalations_store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Emit alert
        alert = api.emit_alert(
            incident=incident,
            routing_decision=routing_decision,
            explanation_bundle_id=args.explanation_bundle_id,
            risk_score=args.risk_score
        )
        
        if alert is None:
            print("Alert was suppressed or duplicate (check audit ledger for details)")
            sys.exit(0)
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(alert, indent=2, ensure_ascii=False))
            print(f"Alert emitted successfully. Result written to: {args.output}")
        else:
            print(json.dumps(alert, indent=2, ensure_ascii=False))
        
        print(f"\nAlert Summary:")
        print(f"  Alert ID: {alert.get('alert_id')}")
        print(f"  Incident ID: {alert.get('incident_id')}")
        print(f"  Severity: {alert.get('severity')}")
        print(f"  Risk Score: {alert.get('risk_score_at_emit')}")
        print(f"  Explanation Bundle: {alert.get('explanation_bundle_id')}")
        print(f"  Authority Required: {alert.get('authority_required')}")
        print(f"  Immutable Hash: {alert.get('immutable_hash')[:16]}...")
        
    except AlertAPIError as e:
        print(f"Alert emission failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
