#!/usr/bin/env python3
"""
RansomEye Notification Engine - Notification API
AUTHORITATIVE: Single API for notification delivery with audit ledger integration
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, timezone
import json
import hashlib

# Add audit-ledger to path
_audit_ledger_dir = Path(__file__).parent.parent.parent / "audit-ledger"
if str(_audit_ledger_dir) not in sys.path:
    sys.path.insert(0, str(_audit_ledger_dir))

# Import audit ledger components
import importlib.util

_store_spec = importlib.util.spec_from_file_location("audit_ledger_storage", _audit_ledger_dir / "storage" / "append_only_store.py")
_store_module = importlib.util.module_from_spec(_store_spec)
_store_spec.loader.exec_module(_store_module)
AppendOnlyStore = _store_module.AppendOnlyStore
LedgerWriter = _store_module.LedgerWriter

_key_manager_spec = importlib.util.spec_from_file_location("audit_ledger_key_manager", _audit_ledger_dir / "crypto" / "key_manager.py")
_key_manager_module = importlib.util.module_from_spec(_key_manager_spec)
_key_manager_spec.loader.exec_module(_key_manager_module)
KeyManager = _key_manager_module.KeyManager

_signer_spec = importlib.util.spec_from_file_location("audit_ledger_signer", _audit_ledger_dir / "crypto" / "signer.py")
_signer_module = importlib.util.module_from_spec(_signer_spec)
_signer_spec.loader.exec_module(_signer_module)
Signer = _signer_module.Signer

# Import notification engine components
_notification_dir = Path(__file__).parent.parent
if str(_notification_dir) not in sys.path:
    sys.path.insert(0, str(_notification_dir))

_target_resolver_spec = importlib.util.spec_from_file_location("target_resolver", _notification_dir / "engine" / "target_resolver.py")
_target_resolver_module = importlib.util.module_from_spec(_target_resolver_spec)
_target_resolver_spec.loader.exec_module(_target_resolver_module)
TargetResolver = _target_resolver_module.TargetResolver

_formatter_spec = importlib.util.spec_from_file_location("formatter", _notification_dir / "engine" / "formatter.py")
_formatter_module = importlib.util.module_from_spec(_formatter_spec)
_formatter_spec.loader.exec_module(_formatter_module)
Formatter = _formatter_module.Formatter

_dispatcher_spec = importlib.util.spec_from_file_location("dispatcher", _notification_dir / "engine" / "dispatcher.py")
_dispatcher_module = importlib.util.module_from_spec(_dispatcher_spec)
_dispatcher_spec.loader.exec_module(_dispatcher_module)
Dispatcher = _dispatcher_module.Dispatcher


class NotificationAPIError(Exception):
    """Base exception for notification API errors."""
    pass


class NotificationAPI:
    """
    Single API for notification delivery.
    
    All operations:
    - Deliver alerts to targets (best-effort, no retries)
    - Record deliveries (immutable records)
    - Emit audit ledger entries (every delivery attempt)
    """
    
    def __init__(
        self,
        targets_store_path: Path,
        deliveries_store_path: Path,
        ledger_path: Path,
        ledger_key_dir: Path
    ):
        """
        Initialize notification API.
        
        Args:
            targets_store_path: Path to delivery targets store
            deliveries_store_path: Path to deliveries store
            ledger_path: Path to audit ledger file
            ledger_key_dir: Directory containing ledger signing keys
        """
        self.target_resolver = TargetResolver(targets_store_path)
        self.formatter = Formatter()
        self.dispatcher = Dispatcher()
        self.deliveries_store_path = Path(deliveries_store_path)
        self.deliveries_store_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize audit ledger
        try:
            ledger_store = AppendOnlyStore(ledger_path, read_only=False)
            ledger_key_manager = KeyManager(ledger_key_dir)
            ledger_private_key, ledger_public_key, ledger_key_id = ledger_key_manager.get_or_create_keypair()
            ledger_signer = Signer(ledger_private_key, ledger_key_id)
            self.ledger_writer = LedgerWriter(ledger_store, ledger_signer)
        except Exception as e:
            raise NotificationAPIError(f"Failed to initialize audit ledger: {e}") from e
    
    def deliver_alert(
        self,
        alert: Dict[str, Any],
        routing_decision: Dict[str, Any],
        explanation_bundle_id: str,
        authority_state: str = 'NONE'
    ) -> List[Dict[str, Any]]:
        """
        Deliver alert to targets.
        
        Process:
        1. Resolve delivery targets
        2. Format payload for each target
        3. Dispatch to adapters
        4. Record deliveries
        5. Emit audit ledger entries
        
        Args:
            alert: Alert dictionary (immutable, read-only)
            routing_decision: Routing decision from policy engine
            explanation_bundle_id: Explanation bundle identifier (SEE)
            authority_state: Authority state (NONE | REQUIRED | VERIFIED)
        
        Returns:
            List of delivery record dictionaries
        """
        # Resolve targets
        targets = self.target_resolver.resolve_targets(alert, routing_decision)
        
        if not targets:
            return []
        
        delivery_records = []
        
        # Deliver to each target
        for target in targets:
            # Format payload
            payload = self.formatter.format_payload(alert, target, explanation_bundle_id)
            payload_hash = self.formatter.calculate_payload_hash(payload)
            
            # Dispatch delivery
            delivery_success = self.dispatcher.dispatch(payload, target)
            
            # Create delivery record
            delivery_record = self._create_delivery_record(
                alert=alert,
                target=target,
                payload_hash=payload_hash,
                explanation_bundle_id=explanation_bundle_id,
                authority_state=authority_state,
                status='DELIVERED' if delivery_success else 'FAILED'
            )
            
            # Store delivery record
            self._store_delivery(delivery_record)
            
            # Emit audit ledger entry
            try:
                ledger_entry = self.ledger_writer.create_entry(
                    component='notification-engine',
                    component_instance_id='notification-engine',
                    action_type='alert_delivered',
                    subject={'type': 'alert', 'id': alert.get('alert_id', '')},
                    actor={'type': 'system', 'identifier': 'notification-engine'},
                    payload={
                        'delivery_id': delivery_record.get('delivery_id', ''),
                        'target_id': target.get('target_id', ''),
                        'delivery_type': target.get('target_type', ''),
                        'status': delivery_record.get('status', ''),
                        'payload_hash': payload_hash
                    }
                )
                delivery_record['ledger_entry_id'] = ledger_entry.get('ledger_entry_id', '')
            except Exception as e:
                raise NotificationAPIError(f"Failed to emit audit ledger entry: {e}") from e
            
            delivery_records.append(delivery_record)
        
        return delivery_records
    
    def _create_delivery_record(
        self,
        alert: Dict[str, Any],
        target: Dict[str, Any],
        payload_hash: str,
        explanation_bundle_id: str,
        authority_state: str,
        status: str
    ) -> Dict[str, Any]:
        """Create delivery record."""
        delivery_id = str(uuid.uuid4())
        delivered_at = datetime.now(timezone.utc).isoformat()
        
        # Build delivery record content (for hashing)
        record_content = {
            'delivery_id': delivery_id,
            'alert_id': alert.get('alert_id', ''),
            'target_id': target.get('target_id', ''),
            'delivery_type': target.get('target_type', ''),
            'payload_hash': payload_hash,
            'explanation_bundle_id': explanation_bundle_id,
            'authority_state': authority_state,
            'delivered_at': delivered_at,
            'status': status
        }
        
        # Calculate immutable hash
        canonical_json = json.dumps(record_content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        immutable_hash = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
        
        # Build delivery record
        delivery_record = {
            'delivery_id': delivery_id,
            'alert_id': alert.get('alert_id', ''),
            'target_id': target.get('target_id', ''),
            'delivery_type': target.get('target_type', ''),
            'payload_hash': payload_hash,
            'explanation_bundle_id': explanation_bundle_id,
            'authority_state': authority_state,
            'delivered_at': delivered_at,
            'status': status,
            'immutable_hash': immutable_hash,
            'ledger_entry_id': ''
        }
        
        return delivery_record
    
    def _store_delivery(self, delivery_record: Dict[str, Any]) -> None:
        """Store delivery record to file-based store."""
        try:
            delivery_json = json.dumps(delivery_record, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(self.deliveries_store_path, 'a', encoding='utf-8') as f:
                f.write(delivery_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise NotificationAPIError(f"Failed to store delivery: {e}") from e
