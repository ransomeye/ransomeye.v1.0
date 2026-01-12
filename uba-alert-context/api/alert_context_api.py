#!/usr/bin/env python3
"""
RansomEye UBA Alert Context Engine - Alert Context API
AUTHORITATIVE: API for building and retrieving human-facing alert context
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

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

# Import UBA Signal components (read-only)
_uba_signal_dir = Path(__file__).parent.parent.parent / "uba-signal"
if str(_uba_signal_dir) not in sys.path:
    sys.path.insert(0, str(_uba_signal_dir))

_signal_store_spec = importlib.util.spec_from_file_location("signal_store", _uba_signal_dir / "storage" / "signal_store.py")
_signal_store_module = importlib.util.module_from_spec(_signal_store_spec)
_signal_store_spec.loader.exec_module(_signal_store_module)
SignalStore = _signal_store_module.SignalStore

# Import alert context engine components
_alert_context_dir = Path(__file__).parent.parent
if str(_alert_context_dir) not in sys.path:
    sys.path.insert(0, str(_alert_context_dir))

_context_builder_spec = importlib.util.spec_from_file_location("context_builder", _alert_context_dir / "engine" / "context_builder.py")
_context_builder_module = importlib.util.module_from_spec(_context_builder_spec)
_context_builder_spec.loader.exec_module(_context_builder_module)
ContextBuilder = _context_builder_module.ContextBuilder

_context_hasher_spec = importlib.util.spec_from_file_location("context_hasher", _alert_context_dir / "engine" / "context_hasher.py")
_context_hasher_module = importlib.util.module_from_spec(_context_hasher_spec)
_context_hasher_spec.loader.exec_module(_context_hasher_module)
ContextHasher = _context_hasher_module.ContextHasher

_context_store_spec = importlib.util.spec_from_file_location("context_store", _alert_context_dir / "storage" / "context_store.py")
_context_store_module = importlib.util.module_from_spec(_context_store_spec)
_context_store_spec.loader.exec_module(_context_store_module)
ContextStore = _context_store_module.ContextStore


class AlertContextAPIError(Exception):
    """Base exception for alert context API errors."""
    pass


class AlertContextAPI:
    """
    API for building and retrieving alert context blocks.
    
    All operations:
    - Read-only access to Alert Engine (via alert_id)
    - Read-only access to UBA Signal Store
    - Write ONLY to context_store
    - Emit audit ledger entries
    - Never modify alerts
    """
    
    def __init__(
        self,
        store_path: Path,
        ledger_path: Path,
        ledger_key_dir: Path,
        uba_signals_store_path: Optional[Path] = None,
        uba_summaries_store_path: Optional[Path] = None
    ):
        """
        Initialize alert context API.
        
        Args:
            store_path: Path to context store file
            ledger_path: Path to audit ledger file
            ledger_key_dir: Directory containing ledger signing keys
            uba_signals_store_path: Optional path to UBA Signal signals store
            uba_summaries_store_path: Optional path to UBA Signal summaries store
        """
        self.store = ContextStore(store_path)
        self.context_builder = ContextBuilder()
        self.context_hasher = ContextHasher()
        
        # UBA Signal store (read-only, optional)
        if uba_signals_store_path and uba_summaries_store_path:
            self.uba_signal_store = SignalStore(
                signals_store_path=uba_signals_store_path,
                summaries_store_path=uba_summaries_store_path
            )
        else:
            self.uba_signal_store = None
        
        # Initialize audit ledger
        try:
            ledger_store = AppendOnlyStore(ledger_path, read_only=False)
            ledger_key_manager = KeyManager(ledger_key_dir)
            ledger_private_key, ledger_public_key, ledger_key_id = ledger_key_manager.get_or_create_keypair()
            ledger_signer = Signer(ledger_private_key, ledger_key_id)
            self.ledger_writer = LedgerWriter(ledger_store, ledger_signer)
        except Exception as e:
            raise AlertContextAPIError(f"Failed to initialize audit ledger: {e}") from e
    
    def build_context(
        self,
        alert_id: str,
        uba_signal_ids: List[str],
        explanation_bundle_id: str
    ) -> Dict[str, Any]:
        """
        Build alert context block from UBA signals.
        
        Args:
            alert_id: Alert identifier (read-only reference to Alert Engine)
            uba_signal_ids: List of UBA signal identifiers
            explanation_bundle_id: Explanation bundle identifier (SEE, mandatory)
        
        Returns:
            Alert context block dictionary
        """
        if not self.uba_signal_store:
            raise AlertContextAPIError("UBA Signal store not configured")
        
        # Load UBA signals (read-only)
        uba_signals = []
        for signal_id in uba_signal_ids:
            signal = self.uba_signal_store.get_signal(signal_id)
            if signal:
                uba_signals.append(signal)
        
        if not uba_signals:
            raise AlertContextAPIError("No valid UBA signals found")
        
        # Build context block
        try:
            context_block = self.context_builder.build_context(
                alert_id=alert_id,
                uba_signals=uba_signals,
                explanation_bundle_id=explanation_bundle_id
            )
        except Exception as e:
            raise AlertContextAPIError(f"Failed to build context: {e}") from e
        
        # Store context block (immutable)
        try:
            self.store.store_context(context_block)
        except Exception as e:
            raise AlertContextAPIError(f"Failed to store context block: {e}") from e
        
        # Emit audit ledger entry
        try:
            self.ledger_writer.create_entry(
                component='uba-alert-context',
                component_instance_id='alert-context-engine',
                action_type='UBA_ALERT_CONTEXT_BUILT',
                subject={'type': 'alert', 'id': alert_id},
                actor={'type': 'system', 'identifier': 'uba-alert-context'},
                payload={
                    'context_block_id': context_block.get('context_block_id', ''),
                    'uba_signal_ids': uba_signal_ids,
                    'explanation_bundle_id': explanation_bundle_id
                }
            )
        except Exception as e:
            raise AlertContextAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return context_block
    
    def get_alert_context(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """
        Get alert context block for alert ID.
        
        Args:
            alert_id: Alert identifier
        
        Returns:
            Context block dictionary, or None if not found
        """
        context_block = self.store.get_context_by_alert_id(alert_id)
        
        if context_block:
            # Emit audit ledger entry
            try:
                self.ledger_writer.create_entry(
                    component='uba-alert-context',
                    component_instance_id='alert-context-engine',
                    action_type='UBA_ALERT_CONTEXT_RETRIEVED',
                    subject={'type': 'alert', 'id': alert_id},
                    actor={'type': 'system', 'identifier': 'uba-alert-context'},
                    payload={
                        'context_block_id': context_block.get('context_block_id', '')
                    }
                )
            except Exception as e:
                raise AlertContextAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return context_block
    
    def list_alert_contexts(self, incident_id: str) -> List[Dict[str, Any]]:
        """
        List all alert contexts for incident ID.
        
        Note: This requires Alert Engine integration for full implementation.
        For Phase M5, returns contexts that can be correlated.
        
        Args:
            incident_id: Incident identifier
        
        Returns:
            List of context block dictionaries
        """
        # Phase M5: Would need Alert Engine read-only access to correlate
        # For now, return empty list (full implementation requires Alert Engine integration)
        contexts = self.store.get_contexts_by_incident_id(incident_id)
        return contexts
