#!/usr/bin/env python3
"""
RansomEye UBA Signal - Signal API
AUTHORITATIVE: Single API for signal operations with audit ledger integration
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json
import uuid
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

# Import UBA Drift components (read-only)
_drift_dir = Path(__file__).parent.parent.parent / "uba-drift"
if str(_drift_dir) not in sys.path:
    sys.path.insert(0, str(_drift_dir))

_delta_store_spec = importlib.util.spec_from_file_location("delta_store", _drift_dir / "storage" / "delta_store.py")
_delta_store_module = importlib.util.module_from_spec(_delta_store_spec)
_delta_store_spec.loader.exec_module(_delta_store_module)
DeltaStore = _delta_store_module.DeltaStore

# Import signal components
_signal_dir = Path(__file__).parent.parent
if str(_signal_dir) not in sys.path:
    sys.path.insert(0, str(_signal_dir))

_signal_interpreter_spec = importlib.util.spec_from_file_location("signal_interpreter", _signal_dir / "engine" / "signal_interpreter.py")
_signal_interpreter_module = importlib.util.module_from_spec(_signal_interpreter_spec)
_signal_interpreter_spec.loader.exec_module(_signal_interpreter_module)
SignalInterpreter = _signal_interpreter_module.SignalInterpreter

_context_resolver_spec = importlib.util.spec_from_file_location("context_resolver", _signal_dir / "engine" / "context_resolver.py")
_context_resolver_module = importlib.util.module_from_spec(_context_resolver_spec)
_context_resolver_spec.loader.exec_module(_context_resolver_module)
ContextResolver = _context_resolver_module.ContextResolver

_signal_hasher_spec = importlib.util.spec_from_file_location("signal_hasher", _signal_dir / "engine" / "signal_hasher.py")
_signal_hasher_module = importlib.util.module_from_spec(_signal_hasher_spec)
_signal_hasher_spec.loader.exec_module(_signal_hasher_module)
SignalHasher = _signal_hasher_module.SignalHasher

_signal_store_spec = importlib.util.spec_from_file_location("signal_store", _signal_dir / "storage" / "signal_store.py")
_signal_store_module = importlib.util.module_from_spec(_signal_store_spec)
_signal_store_spec.loader.exec_module(_signal_store_module)
SignalStore = _signal_store_module.SignalStore


class SignalAPIError(Exception):
    """Base exception for signal API errors."""
    pass


class SignalAPI:
    """
    Single API for signal operations.
    
    All operations:
    - Interpret deltas (context-aware interpretation)
    - Get signals (read-only)
    - Get signal summary (read-only)
    - Emit audit ledger entries (every operation)
    """
    
    def __init__(
        self,
        drift_deltas_store_path: Path,
        drift_summaries_store_path: Path,
        signals_store_path: Path,
        summaries_store_path: Path,
        ledger_path: Path,
        ledger_key_dir: Path,
        killchain_store_path: Optional[Path] = None,
        threat_graph_store_path: Optional[Path] = None,
        incident_store_path: Optional[Path] = None
    ):
        """
        Initialize Signal API.
        
        Args:
            drift_deltas_store_path: Path to UBA Drift deltas store (read-only)
            drift_summaries_store_path: Path to UBA Drift summaries store (read-only)
            signals_store_path: Path to signals store
            summaries_store_path: Path to summaries store
            ledger_path: Path to audit ledger file
            ledger_key_dir: Directory containing ledger signing keys
            killchain_store_path: Path to KillChain store (optional, read-only)
            threat_graph_store_path: Path to Threat Graph store (optional, read-only)
            incident_store_path: Path to Incident store (optional, read-only)
        """
        self.signal_interpreter = SignalInterpreter()
        self.context_resolver = ContextResolver(
            killchain_store_path=killchain_store_path,
            threat_graph_store_path=threat_graph_store_path,
            incident_store_path=incident_store_path
        )
        self.signal_hasher = SignalHasher()
        
        # UBA Drift stores (read-only)
        self.drift_delta_store = DeltaStore(
            deltas_store_path=drift_deltas_store_path,
            summaries_store_path=drift_summaries_store_path
        )
        
        # Signal stores
        self.signal_store = SignalStore(
            signals_store_path=signals_store_path,
            summaries_store_path=summaries_store_path
        )
        
        # Initialize audit ledger
        try:
            ledger_store = AppendOnlyStore(ledger_path, read_only=False)
            ledger_key_manager = KeyManager(ledger_key_dir)
            ledger_private_key, ledger_public_key, ledger_key_id = ledger_key_manager.get_or_create_keypair()
            ledger_signer = Signer(ledger_private_key, ledger_key_id)
            self.ledger_writer = LedgerWriter(ledger_store, ledger_signer)
        except Exception as e:
            raise SignalAPIError(f"Failed to initialize audit ledger: {e}") from e
    
    def interpret_deltas(
        self,
        identity_id: str,
        delta_ids: List[str],
        contextual_inputs: Dict[str, Any],
        explanation_bundle_id: str
    ) -> List[Dict[str, Any]]:
        """
        Interpret deltas into signals.
        
        Process:
        1. Load deltas from UBA Drift (read-only)
        2. Resolve context (read-only)
        3. Interpret deltas (explicit mappings)
        4. Store signals (immutable)
        5. Emit audit ledger entry
        
        Args:
            identity_id: Identity identifier
            delta_ids: List of delta identifiers
            contextual_inputs: Context references (read-only)
            explanation_bundle_id: Explanation bundle identifier (SEE)
        
        Returns:
            List of interpreted signal dictionaries
        """
        # Load deltas from UBA Drift (read-only)
        deltas = []
        for delta_id in delta_ids:
            delta = self.drift_delta_store.get_delta(delta_id)
            if delta:
                deltas.append(delta)
        
        if not deltas:
            raise SignalAPIError(f"No deltas found for provided delta IDs")
        
        # Resolve context (read-only)
        resolved_context = self.context_resolver.resolve_context(
            killchain_ids=contextual_inputs.get('killchain_ids'),
            graph_ids=contextual_inputs.get('graph_ids'),
            incident_ids=contextual_inputs.get('incident_ids')
        )
        
        # Interpret deltas
        signals = self.signal_interpreter.interpret_deltas(
            deltas=deltas,
            identity_id=identity_id,
            contextual_inputs=resolved_context,
            explanation_bundle_id=explanation_bundle_id
        )
        
        # Store signals
        for signal in signals:
            self.signal_store.store_signal(signal)
            
            # Emit audit ledger entry
            try:
                ledger_entry = self.ledger_writer.create_entry(
                    component='uba-signal',
                    component_instance_id='uba-signal',
                    action_type='UBA_SIGNAL_INTERPRETED',
                    subject={'type': 'identity', 'id': identity_id},
                    actor={'type': 'system', 'identifier': 'uba-signal'},
                    payload={
                        'signal_id': signal.get('signal_id', ''),
                        'interpretation_type': signal.get('interpretation_type', ''),
                        'authority_required': signal.get('authority_required', False)
                    }
                )
                signal['ledger_entry_id'] = ledger_entry.get('ledger_entry_id', '')
            except Exception as e:
                raise SignalAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return signals
    
    def get_signals(
        self,
        identity_id: str,
        window_start: Optional[str] = None,
        window_end: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get signals for identity.
        
        Args:
            identity_id: Identity identifier
            window_start: Optional window start filter
            window_end: Optional window end filter
        
        Returns:
            List of signal dictionaries
        """
        return self.signal_store.get_signals_for_identity(
            identity_id=identity_id,
            window_start=window_start,
            window_end=window_end
        )
    
    def get_signal_summary(
        self,
        identity_id: str,
        observation_window_start: datetime,
        observation_window_end: datetime
    ) -> Dict[str, Any]:
        """
        Get signal summary for identity.
        
        Process:
        1. Get signals for identity and window
        2. Build summary (aggregation only)
        3. Store summary (immutable)
        4. Emit audit ledger entry
        
        Args:
            identity_id: Identity identifier
            observation_window_start: Observation window start
            observation_window_end: Observation window end
        
        Returns:
            Summary dictionary
        """
        # Get signals
        signals = self.signal_store.get_signals_for_identity(identity_id)
        
        # Filter by window
        filtered_signals = [
            s for s in signals
            if observation_window_start.isoformat() <= s.get('created_timestamp', '') <= observation_window_end.isoformat()
        ]
        
        # Build summary
        interpretation_types_present = set()
        for signal in filtered_signals:
            interpretation_type = signal.get('interpretation_type', '')
            if interpretation_type:
                interpretation_types_present.add(interpretation_type)
        
        summary = {
            'summary_id': str(uuid.uuid4()),
            'identity_id': identity_id,
            'observation_window_start': observation_window_start.isoformat(),
            'observation_window_end': observation_window_end.isoformat(),
            'signal_count': len(filtered_signals),
            'interpretation_types_present': sorted(list(interpretation_types_present)),
            'summary_hash': '',
            'immutable_hash': '',
            'ledger_entry_id': ''
        }
        
        # Calculate summary hash
        summary['summary_hash'] = self.signal_hasher.calculate_summary_hash(summary)
        
        # Calculate immutable hash
        hashable_content = {k: v for k, v in summary.items() if k not in ['immutable_hash', 'ledger_entry_id']}
        canonical_json = json.dumps(hashable_content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        summary['immutable_hash'] = hashlib.sha256(content_bytes).hexdigest()
        
        # Store summary
        self.signal_store.store_summary(summary)
        
        # Emit audit ledger entry
        try:
            ledger_entry = self.ledger_writer.create_entry(
                component='uba-signal',
                component_instance_id='uba-signal',
                action_type='UBA_SIGNAL_SUMMARY_BUILT',
                subject={'type': 'identity', 'id': identity_id},
                actor={'type': 'system', 'identifier': 'uba-signal'},
                payload={
                    'summary_id': summary.get('summary_id', ''),
                    'signal_count': summary.get('signal_count', 0)
                }
            )
            summary['ledger_entry_id'] = ledger_entry.get('ledger_entry_id', '')
        except Exception as e:
            raise SignalAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return summary
