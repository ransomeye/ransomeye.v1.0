#!/usr/bin/env python3
"""
RansomEye UBA Drift - Drift API
AUTHORITATIVE: Single API for drift operations with audit ledger integration
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

# Import UBA Core components (read-only)
_uba_core_dir = Path(__file__).parent.parent.parent / "uba-core"
if str(_uba_core_dir) not in sys.path:
    sys.path.insert(0, str(_uba_core_dir))

_uba_store_spec = importlib.util.spec_from_file_location("uba_store", _uba_core_dir / "storage" / "uba_store.py")
_uba_store_module = importlib.util.module_from_spec(_uba_store_spec)
_uba_store_spec.loader.exec_module(_uba_store_module)
UBAStore = _uba_store_module.UBAStore

# Import drift components
_drift_dir = Path(__file__).parent.parent
if str(_drift_dir) not in sys.path:
    sys.path.insert(0, str(_drift_dir))

_delta_comparator_spec = importlib.util.spec_from_file_location("delta_comparator", _drift_dir / "engine" / "delta_comparator.py")
_delta_comparator_module = importlib.util.module_from_spec(_delta_comparator_spec)
_delta_comparator_spec.loader.exec_module(_delta_comparator_module)
DeltaComparator = _delta_comparator_module.DeltaComparator

_window_builder_spec = importlib.util.spec_from_file_location("window_builder", _drift_dir / "engine" / "window_builder.py")
_window_builder_module = importlib.util.module_from_spec(_window_builder_spec)
_window_builder_spec.loader.exec_module(_window_builder_module)
WindowBuilder = _window_builder_module.WindowBuilder

_delta_hasher_spec = importlib.util.spec_from_file_location("delta_hasher", _drift_dir / "engine" / "delta_hasher.py")
_delta_hasher_module = importlib.util.module_from_spec(_delta_hasher_spec)
_delta_hasher_spec.loader.exec_module(_delta_hasher_module)
DeltaHasher = _delta_hasher_module.DeltaHasher

_delta_classifier_spec = importlib.util.spec_from_file_location("delta_classifier", _drift_dir / "engine" / "delta_classifier.py")
_delta_classifier_module = importlib.util.module_from_spec(_delta_classifier_spec)
_delta_classifier_spec.loader.exec_module(_delta_classifier_module)
DeltaClassifier = _delta_classifier_module.DeltaClassifier

_delta_store_spec = importlib.util.spec_from_file_location("delta_store", _drift_dir / "storage" / "delta_store.py")
_delta_store_module = importlib.util.module_from_spec(_delta_store_spec)
_delta_store_spec.loader.exec_module(_delta_store_module)
DeltaStore = _delta_store_module.DeltaStore


class DriftAPIError(Exception):
    """Base exception for drift API errors."""
    pass


class DriftAPI:
    """
    Single API for drift operations.
    
    All operations:
    - Compute behavior deltas (baseline vs observation)
    - Get behavior deltas (read-only)
    - Get delta summary (read-only)
    - Emit audit ledger entries (every operation)
    """
    
    def __init__(
        self,
        uba_identities_store_path: Path,
        uba_events_store_path: Path,
        uba_baselines_store_path: Path,
        deltas_store_path: Path,
        summaries_store_path: Path,
        ledger_path: Path,
        ledger_key_dir: Path
    ):
        """
        Initialize Drift API.
        
        Args:
            uba_identities_store_path: Path to UBA Core identities store (read-only)
            uba_events_store_path: Path to UBA Core events store (read-only)
            uba_baselines_store_path: Path to UBA Core baselines store (read-only)
            deltas_store_path: Path to deltas store
            summaries_store_path: Path to summaries store
            ledger_path: Path to audit ledger file
            ledger_key_dir: Directory containing ledger signing keys
        """
        self.delta_comparator = DeltaComparator()
        self.window_builder = WindowBuilder()
        self.delta_hasher = DeltaHasher()
        self.delta_classifier = DeltaClassifier()
        
        # UBA Core stores (read-only)
        self.uba_store = UBAStore(
            identities_store_path=uba_identities_store_path,
            events_store_path=uba_events_store_path,
            baselines_store_path=uba_baselines_store_path
        )
        
        # Drift stores
        self.delta_store = DeltaStore(
            deltas_store_path=deltas_store_path,
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
            raise DriftAPIError(f"Failed to initialize audit ledger: {e}") from e
    
    def compute_behavior_deltas(
        self,
        identity_id: str,
        baseline_id: Optional[str] = None,
        observation_window_start: Optional[datetime] = None,
        observation_window_end: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Compute behavior deltas.
        
        Process:
        1. Load baseline from UBA Core (read-only)
        2. Build observation window
        3. Load events in observation window
        4. Compare baseline to observation
        5. Store deltas (immutable)
        6. Emit audit ledger entry
        
        Args:
            identity_id: Identity identifier
            baseline_id: Optional baseline identifier (if None, uses latest)
            observation_window_start: Optional observation window start
            observation_window_end: Optional observation window end (if None, uses current time)
        
        Returns:
            List of delta dictionaries
        """
        # Load baseline from UBA Core (read-only)
        baseline = self.uba_store.get_baseline(baseline_id) if baseline_id else self.uba_store.get_latest_baseline(identity_id)
        
        if not baseline:
            raise DriftAPIError(f"Baseline not found for identity: {identity_id}")
        
        if baseline.get('identity_id') != identity_id:
            raise DriftAPIError(f"Baseline identity mismatch: {baseline.get('identity_id')} != {identity_id}")
        
        # Build observation window
        if observation_window_end is None:
            observation_window_end = datetime.now(timezone.utc)
        
        window_start, window_end = self.window_builder.build_window(
            window_end=observation_window_end,
            window_start=observation_window_start
        )
        
        # Load events in observation window
        all_events = self.uba_store.get_events_for_identity(identity_id)
        observation_events = self.window_builder.filter_events(all_events, window_start, window_end)
        
        if not observation_events:
            raise DriftAPIError(f"No events found in observation window for identity: {identity_id}")
        
        # Compare baseline to observation
        deltas = self.delta_comparator.compare(
            baseline=baseline,
            observation_events=observation_events,
            observation_window_start=window_start,
            observation_window_end=window_end
        )
        
        # Store deltas
        for delta in deltas:
            self.delta_store.store_delta(delta)
            
            # Emit audit ledger entry
            try:
                ledger_entry = self.ledger_writer.create_entry(
                    component='uba-drift',
                    component_instance_id='uba-drift',
                    action_type='UBA_DELTA_COMPUTED',
                    subject={'type': 'identity', 'id': identity_id},
                    actor={'type': 'system', 'identifier': 'uba-drift'},
                    payload={
                        'delta_id': delta.get('delta_id', ''),
                        'delta_type': delta.get('delta_type', ''),
                        'baseline_hash': delta.get('baseline_hash', '')
                    }
                )
                delta['ledger_entry_id'] = ledger_entry.get('ledger_entry_id', '')
            except Exception as e:
                raise DriftAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return deltas
    
    def get_behavior_deltas(
        self,
        identity_id: str,
        window_start: Optional[str] = None,
        window_end: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get behavior deltas for identity.
        
        Args:
            identity_id: Identity identifier
            window_start: Optional window start filter
            window_end: Optional window end filter
        
        Returns:
            List of delta dictionaries
        """
        return self.delta_store.get_deltas_for_identity(
            identity_id=identity_id,
            window_start=window_start,
            window_end=window_end
        )
    
    def get_delta_summary(
        self,
        identity_id: str,
        baseline_hash: str,
        observation_window_start: datetime,
        observation_window_end: datetime
    ) -> Dict[str, Any]:
        """
        Get delta summary for identity.
        
        Process:
        1. Get deltas for identity and window
        2. Build summary (aggregation only)
        3. Store summary (immutable)
        4. Emit audit ledger entry
        
        Args:
            identity_id: Identity identifier
            baseline_hash: Baseline hash
            observation_window_start: Observation window start
            observation_window_end: Observation window end
        
        Returns:
            Summary dictionary
        """
        # Get deltas
        deltas = self.delta_store.get_deltas_for_identity(identity_id)
        
        # Filter by window
        filtered_deltas = [
            d for d in deltas
            if d.get('observation_window_start') == observation_window_start.isoformat() and
               d.get('observation_window_end') == observation_window_end.isoformat() and
               d.get('baseline_hash') == baseline_hash
        ]
        
        # Build summary
        delta_types_present = set()
        for delta in filtered_deltas:
            delta_type = delta.get('delta_type', '')
            if delta_type:
                delta_types_present.add(delta_type)
        
        summary = {
            'summary_id': str(uuid.uuid4()),
            'identity_id': identity_id,
            'baseline_hash': baseline_hash,
            'observation_window_start': observation_window_start.isoformat(),
            'observation_window_end': observation_window_end.isoformat(),
            'total_deltas': len(filtered_deltas),
            'delta_types_present': sorted(list(delta_types_present)),
            'summary_hash': '',
            'immutable_hash': '',
            'ledger_entry_id': ''
        }
        
        # Calculate summary hash
        summary['summary_hash'] = self.delta_hasher.calculate_summary_hash(summary)
        
        # Calculate immutable hash
        hashable_content = {k: v for k, v in summary.items() if k not in ['immutable_hash', 'ledger_entry_id']}
        canonical_json = json.dumps(hashable_content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        summary['immutable_hash'] = hashlib.sha256(content_bytes).hexdigest()
        
        # Store summary
        self.delta_store.store_summary(summary)
        
        # Emit audit ledger entry
        try:
            ledger_entry = self.ledger_writer.create_entry(
                component='uba-drift',
                component_instance_id='uba-drift',
                action_type='UBA_DELTA_SUMMARY_BUILT',
                subject={'type': 'identity', 'id': identity_id},
                actor={'type': 'system', 'identifier': 'uba-drift'},
                payload={
                    'summary_id': summary.get('summary_id', ''),
                    'total_deltas': summary.get('total_deltas', 0)
                }
            )
            summary['ledger_entry_id'] = ledger_entry.get('ledger_entry_id', '')
        except Exception as e:
            raise DriftAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return summary
