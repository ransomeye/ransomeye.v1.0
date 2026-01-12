#!/usr/bin/env python3
"""
RansomEye Alert Engine - Alert API
AUTHORITATIVE: Single API for alert operations with audit ledger integration
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, timezone
import json

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

# Import alert engine components
_alert_dir = Path(__file__).parent.parent
if str(_alert_dir) not in sys.path:
    sys.path.insert(0, str(_alert_dir))

_alert_builder_spec = importlib.util.spec_from_file_location("alert_builder", _alert_dir / "engine" / "alert_builder.py")
_alert_builder_module = importlib.util.module_from_spec(_alert_builder_spec)
_alert_builder_spec.loader.exec_module(_alert_builder_module)
AlertBuilder = _alert_builder_module.AlertBuilder

_deduplicator_spec = importlib.util.spec_from_file_location("deduplicator", _alert_dir / "engine" / "deduplicator.py")
_deduplicator_module = importlib.util.module_from_spec(_deduplicator_spec)
_deduplicator_spec.loader.exec_module(_deduplicator_module)
Deduplicator = _deduplicator_module.Deduplicator

_suppressor_spec = importlib.util.spec_from_file_location("suppressor", _alert_dir / "engine" / "suppressor.py")
_suppressor_module = importlib.util.module_from_spec(_suppressor_spec)
_suppressor_spec.loader.exec_module(_suppressor_module)
Suppressor = _suppressor_module.Suppressor

_escalator_spec = importlib.util.spec_from_file_location("escalator", _alert_dir / "engine" / "escalator.py")
_escalator_module = importlib.util.module_from_spec(_escalator_spec)
_escalator_spec.loader.exec_module(_escalator_module)
Escalator = _escalator_module.Escalator


class AlertAPIError(Exception):
    """Base exception for alert API errors."""
    pass


class AlertAPI:
    """
    Single API for alert operations.
    
    All operations:
    - Emit alerts (from incidents + routing decisions)
    - Deduplicate alerts (content-based, deterministic)
    - Suppress alerts (explicit, policy-driven)
    - Escalate alerts (deterministic, explanation-required)
    - Emit audit ledger entries (every operation)
    """
    
    def __init__(
        self,
        alerts_store_path: Path,
        suppressions_store_path: Path,
        escalations_store_path: Path,
        ledger_path: Path,
        ledger_key_dir: Path
    ):
        """
        Initialize alert API.
        
        Args:
            alerts_store_path: Path to alerts store
            suppressions_store_path: Path to suppressions store
            escalations_store_path: Path to escalations store
            ledger_path: Path to audit ledger file
            ledger_key_dir: Directory containing ledger signing keys
        """
        self.alert_builder = AlertBuilder()
        self.deduplicator = Deduplicator()
        self.suppressor = Suppressor()
        self.escalator = Escalator()
        
        self.alerts_store_path = Path(alerts_store_path)
        self.alerts_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.suppressions_store_path = Path(suppressions_store_path)
        self.suppressions_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.escalations_store_path = Path(escalations_store_path)
        self.escalations_store_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize audit ledger
        try:
            ledger_store = AppendOnlyStore(ledger_path, read_only=False)
            ledger_key_manager = KeyManager(ledger_key_dir)
            ledger_private_key, ledger_public_key, ledger_key_id = ledger_key_manager.get_or_create_keypair()
            ledger_signer = Signer(ledger_private_key, ledger_key_id)
            self.ledger_writer = LedgerWriter(ledger_store, ledger_signer)
        except Exception as e:
            raise AlertAPIError(f"Failed to initialize audit ledger: {e}") from e
    
    def emit_alert(
        self,
        incident: Dict[str, Any],
        routing_decision: Dict[str, Any],
        explanation_bundle_id: str,
        risk_score: float
    ) -> Optional[Dict[str, Any]]:
        """
        Emit alert from incident and routing decision.
        
        Process:
        1. Get previous alert hash (for chaining)
        2. Build alert
        3. Check for duplicates
        4. Check for suppression
        5. Store alert
        6. Emit audit ledger entry
        
        Args:
            incident: Incident dictionary
            routing_decision: Routing decision from policy engine
            explanation_bundle_id: Explanation bundle identifier (SEE)
            risk_score: Risk score at time of emission
        
        Returns:
            Alert dictionary, or None if suppressed or duplicate
        """
        # Get previous alert hash
        prev_alert_hash = self._get_previous_alert_hash(incident.get('incident_id', ''))
        
        # Build alert
        alert = self.alert_builder.build_alert(
            incident=incident,
            routing_decision=routing_decision,
            explanation_bundle_id=explanation_bundle_id,
            risk_score=risk_score,
            prev_alert_hash=prev_alert_hash
        )
        
        # Check for duplicates
        if self.deduplicator.is_duplicate(alert):
            # Duplicate alert - emit audit entry but don't store
            try:
                self.ledger_writer.create_entry(
                    component='alert-engine',
                    component_instance_id='alert-engine',
                    action_type='alert_duplicate_detected',
                    subject={'type': 'alert', 'id': alert.get('alert_id', '')},
                    actor={'type': 'system', 'identifier': 'alert-engine'},
                    payload={
                        'incident_id': incident.get('incident_id', ''),
                        'duplicate_reason': 'content_based_deduplication'
                    }
                )
            except Exception:
                pass
            return None
        
        # Check for suppression
        if self.suppressor.should_suppress(alert, routing_decision):
            # Suppress alert
            suppression = self.suppressor.create_suppression(
                alert=alert,
                policy_rule_id=routing_decision.get('rule_id', ''),
                suppression_reason='policy_suppression',
                suppressed_by='system'
            )
            
            # Store suppression
            self._store_suppression(suppression)
            
            # Emit audit ledger entry
            try:
                ledger_entry = self.ledger_writer.create_entry(
                    component='alert-engine',
                    component_instance_id='alert-engine',
                    action_type='alert_suppressed',
                    subject={'type': 'alert', 'id': alert.get('alert_id', '')},
                    actor={'type': 'system', 'identifier': 'alert-engine'},
                    payload={
                        'suppression_id': suppression.get('suppression_id', ''),
                        'suppression_reason': suppression.get('suppression_reason', '')
                    }
                )
                suppression['ledger_entry_id'] = ledger_entry.get('ledger_entry_id', '')
            except Exception as e:
                raise AlertAPIError(f"Failed to emit audit ledger entry: {e}") from e
            
            # Alert is suppressed, but still recorded as fact
            # Store alert with suppression marker
            alert['suppressed'] = True
            self._store_alert(alert)
            
            return alert
        
        # Store alert
        self._store_alert(alert)
        
        # Emit audit ledger entry
        try:
            ledger_entry = self.ledger_writer.create_entry(
                component='alert-engine',
                component_instance_id='alert-engine',
                action_type='alert_emitted',
                subject={'type': 'alert', 'id': alert.get('alert_id', '')},
                actor={'type': 'system', 'identifier': 'alert-engine'},
                payload={
                    'incident_id': incident.get('incident_id', ''),
                    'severity': alert.get('severity', ''),
                    'risk_score': risk_score,
                    'explanation_bundle_id': explanation_bundle_id
                }
            )
        except Exception as e:
            raise AlertAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        # Check for escalation
        if self.escalator.should_escalate(alert, routing_decision):
            escalation = self.escalator.create_escalation(
                alert=alert,
                policy_rule_id=routing_decision.get('rule_id', ''),
                explanation_bundle_id=explanation_bundle_id,
                authority_required=routing_decision.get('required_authority', 'NONE'),
                escalated_by='system'
            )
            
            # Store escalation
            self._store_escalation(escalation)
            
            # Emit audit ledger entry
            try:
                ledger_entry = self.ledger_writer.create_entry(
                    component='alert-engine',
                    component_instance_id='alert-engine',
                    action_type='alert_escalated',
                    subject={'type': 'alert', 'id': alert.get('alert_id', '')},
                    actor={'type': 'system', 'identifier': 'alert-engine'},
                    payload={
                        'escalation_id': escalation.get('escalation_id', ''),
                        'authority_required': escalation.get('authority_required', '')
                    }
                )
                escalation['ledger_entry_id'] = ledger_entry.get('ledger_entry_id', '')
            except Exception as e:
                raise AlertAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return alert
    
    def _get_previous_alert_hash(self, incident_id: str) -> Optional[str]:
        """Get previous alert hash for incident."""
        if not self.alerts_store_path.exists():
            return None
        
        alerts = []
        try:
            with open(self.alerts_store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    alert = json.loads(line)
                    if alert.get('incident_id') == incident_id:
                        alerts.append(alert)
        except Exception:
            pass
        
        return self.deduplicator.get_previous_alert_hash(incident_id, alerts)
    
    def _store_alert(self, alert: Dict[str, Any]) -> None:
        """Store alert to file-based store."""
        try:
            alert_json = json.dumps(alert, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(self.alerts_store_path, 'a', encoding='utf-8') as f:
                f.write(alert_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise AlertAPIError(f"Failed to store alert: {e}") from e
    
    def _store_suppression(self, suppression: Dict[str, Any]) -> None:
        """Store suppression to file-based store."""
        try:
            suppression_json = json.dumps(suppression, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(self.suppressions_store_path, 'a', encoding='utf-8') as f:
                f.write(suppression_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise AlertAPIError(f"Failed to store suppression: {e}") from e
    
    def _store_escalation(self, escalation: Dict[str, Any]) -> None:
        """Store escalation to file-based store."""
        try:
            escalation_json = json.dumps(escalation, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(self.escalations_store_path, 'a', encoding='utf-8') as f:
                f.write(escalation_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise AlertAPIError(f"Failed to store escalation: {e}") from e
