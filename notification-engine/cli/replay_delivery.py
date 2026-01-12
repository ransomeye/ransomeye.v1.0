#!/usr/bin/env python3
"""
RansomEye Notification Engine - Replay Delivery CLI
AUTHORITATIVE: Command-line tool for replaying alert deliveries
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_notification_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_notification_dir))

from api.notification_api import NotificationAPI, NotificationAPIError


def load_alert(alert_path: Path) -> dict:
    """Load alert from file."""
    if not alert_path.exists():
        return {}
    
    try:
        return json.loads(alert_path.read_text())
    except Exception as e:
        print(f"Warning: Failed to load alert: {e}", file=sys.stderr)
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
        description='Replay alert delivery'
    )
    parser.add_argument(
        '--alert',
        type=Path,
        required=True,
        help='Path to alert JSON file'
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
        '--authority-state',
        choices=['NONE', 'REQUIRED', 'VERIFIED'],
        default='NONE',
        help='Authority state (default: NONE)'
    )
    parser.add_argument(
        '--targets-store',
        type=Path,
        required=True,
        help='Path to delivery targets store'
    )
    parser.add_argument(
        '--deliveries-store',
        type=Path,
        required=True,
        help='Path to deliveries store'
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
        help='Path to output delivery records JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load alert and routing decision
        alert = load_alert(args.alert)
        routing_decision = load_routing_decision(args.routing_decision)
        
        if not alert or not routing_decision:
            print("Error: Failed to load alert or routing decision", file=sys.stderr)
            sys.exit(1)
        
        # Initialize notification API
        api = NotificationAPI(
            targets_store_path=args.targets_store,
            deliveries_store_path=args.deliveries_store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Deliver alert
        delivery_records = api.deliver_alert(
            alert=alert,
            routing_decision=routing_decision,
            explanation_bundle_id=args.explanation_bundle_id,
            authority_state=args.authority_state
        )
        
        if not delivery_records:
            print("No delivery targets resolved")
            sys.exit(0)
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(delivery_records, indent=2, ensure_ascii=False))
            print(f"Deliveries completed. Result written to: {args.output}")
        else:
            print(json.dumps(delivery_records, indent=2, ensure_ascii=False))
        
        print(f"\nDelivery Summary:")
        print(f"  Alert ID: {alert.get('alert_id')}")
        print(f"  Deliveries: {len(delivery_records)}")
        for i, record in enumerate(delivery_records, 1):
            print(f"  Delivery {i}: {record.get('delivery_type')} -> {record.get('status')} (target: {record.get('target_id')[:8]}...)")
        
    except NotificationAPIError as e:
        print(f"Delivery failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
