#!/usr/bin/env python3
"""
RansomEye UBA Core - UBA API
AUTHORITATIVE: Single API for UBA operations with audit ledger integration
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json
import os

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

# Import UBA components
_uba_dir = Path(__file__).parent.parent
if str(_uba_dir) not in sys.path:
    sys.path.insert(0, str(_uba_dir))

_identity_resolver_spec = importlib.util.spec_from_file_location("identity_resolver", _uba_dir / "engine" / "identity_resolver.py")
_identity_resolver_module = importlib.util.module_from_spec(_identity_resolver_spec)
_identity_resolver_spec.loader.exec_module(_identity_resolver_module)
IdentityResolver = _identity_resolver_module.IdentityResolver

_behavior_normalizer_spec = importlib.util.spec_from_file_location("behavior_normalizer", _uba_dir / "engine" / "behavior_normalizer.py")
_behavior_normalizer_module = importlib.util.module_from_spec(_behavior_normalizer_spec)
_behavior_normalizer_spec.loader.exec_module(_behavior_normalizer_module)
BehaviorNormalizer = _behavior_normalizer_module.BehaviorNormalizer

_baseline_builder_spec = importlib.util.spec_from_file_location("baseline_builder", _uba_dir / "engine" / "baseline_builder.py")
_baseline_builder_module = importlib.util.module_from_spec(_baseline_builder_spec)
_baseline_builder_spec.loader.exec_module(_baseline_builder_module)
BaselineBuilder = _baseline_builder_module.BaselineBuilder

_baseline_hasher_spec = importlib.util.spec_from_file_location("baseline_hasher", _uba_dir / "engine" / "baseline_hasher.py")
_baseline_hasher_module = importlib.util.module_from_spec(_baseline_hasher_spec)
_baseline_hasher_spec.loader.exec_module(_baseline_hasher_module)
BaselineHasher = _baseline_hasher_module.BaselineHasher

_uba_store_spec = importlib.util.spec_from_file_location("uba_store", _uba_dir / "storage" / "uba_store.py")
_uba_store_module = importlib.util.module_from_spec(_uba_store_spec)
_uba_store_spec.loader.exec_module(_uba_store_module)
UBAStore = _uba_store_module.UBAStore


class UBAAPIError(Exception):
    """Base exception for UBA API errors."""
    pass


class UBAAPI:
    """
    Single API for UBA operations.
    
    All operations:
    - Ingest behavior events (normalized, canonical)
    - Build identity baselines (historical, immutable)
    - Get identity baselines (read-only)
    - Emit audit ledger entries (every operation)
    """
    
    def __init__(
        self,
        identities_store_path: Path,
        events_store_path: Path,
        baselines_store_path: Path,
        ledger_path: Path,
        ledger_key_dir: Path
    ):
        """
        Initialize UBA API.
        
        Args:
            identities_store_path: Path to identities store
            events_store_path: Path to behavior events store
            baselines_store_path: Path to baselines store
            ledger_path: Path to audit ledger file
            ledger_key_dir: Directory containing ledger signing keys
        """
        self.identity_resolver = IdentityResolver()
        self.behavior_normalizer = BehaviorNormalizer()
        self.baseline_builder = BaselineBuilder()
        self.baseline_hasher = BaselineHasher()
        self.store = UBAStore(
            identities_store_path=identities_store_path,
            events_store_path=events_store_path,
            baselines_store_path=baselines_store_path
        )
        
        # Initialize audit ledger
        try:
            ledger_store = AppendOnlyStore(ledger_path, read_only=False)
            ledger_key_manager = KeyManager(ledger_key_dir)
            ledger_private_key, ledger_public_key, ledger_key_id = ledger_key_manager.get_or_create_keypair()
            ledger_signer = Signer(ledger_private_key, ledger_key_id)
            self.ledger_writer = LedgerWriter(ledger_store, ledger_signer)
        except Exception as e:
            raise UBAAPIError(f"Failed to initialize audit ledger: {e}") from e
    
    def ingest_behavior_event(
        self,
        raw_event: Dict[str, Any],
        user_id: str,
        identity_type: str,
        auth_domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingest behavior event.
        
        Process:
        1. Resolve identity (canonical)
        2. Normalize event (canonical)
        3. Store event (immutable)
        4. Emit audit ledger entry
        
        Args:
            raw_event: Raw behavior event from source component
            user_id: User identifier
            identity_type: Identity type (human, service, machine)
            auth_domain: Authentication domain (optional)
        
        Returns:
            Normalized behavior event dictionary
        """
        # Resolve identity
        identity = self.identity_resolver.resolve_identity(
            user_id=user_id,
            identity_type=identity_type,
            auth_domain=auth_domain
        )
        
        # Check if identity already exists
        existing = self.store.get_identity_by_canonical_hash(identity['canonical_identity_hash'])
        if not existing:
            # Store new identity
            self.store.store_identity(identity)
            
            # Emit identity creation audit entry
            try:
                self.ledger_writer.create_entry(
                    component='uba-core',
                    component_instance_id='uba-core',
                    action_type='UBA_IDENTITY_CREATED',
                    subject={'type': 'identity', 'id': identity.get('identity_id', '')},
                    actor={'type': 'system', 'identifier': 'uba-core'},
                    payload={
                        'identity_id': identity.get('identity_id', ''),
                        'user_id': user_id,
                        'identity_type': identity_type
                    }
                )
            except Exception as e:
                raise UBAAPIError(f"Failed to emit audit ledger entry: {e}") from e
        else:
            identity = existing
        
        # Normalize event
        normalized = self.behavior_normalizer.normalize(raw_event, identity['identity_id'])
        
        # Store event
        self.store.store_event(normalized)
        
        # Emit audit ledger entry
        try:
            ledger_entry = self.ledger_writer.create_entry(
                component='uba-core',
                component_instance_id='uba-core',
                action_type='UBA_BEHAVIOR_INGESTED',
                subject={'type': 'identity', 'id': identity.get('identity_id', '')},
                actor={'type': 'system', 'identifier': 'uba-core'},
                payload={
                    'event_id': normalized.get('event_id', ''),
                    'event_type': normalized.get('event_type', ''),
                    'source_component': normalized.get('source_component', '')
                }
            )
            normalized['ledger_entry_id'] = ledger_entry.get('ledger_entry_id', '')
        except Exception as e:
            raise UBAAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return normalized
    
    def build_identity_baseline(
        self,
        identity_id: str,
        window_start: Optional[datetime] = None,
        window_end: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Build identity baseline.
        
        Process:
        1. Load events for identity
        2. Build baseline (aggregation only)
        3. Store baseline (immutable)
        4. Emit audit ledger entry
        
        Args:
            identity_id: Identity identifier
            window_start: Baseline window start (optional)
            window_end: Baseline window end (optional)
        
        Returns:
            Baseline dictionary
        """
        # Get events for identity
        events = self.store.get_events_for_identity(identity_id)
        
        if not events:
            raise UBAAPIError(f"No events found for identity: {identity_id}")
        
        # Build baseline
        baseline = self.baseline_builder.build_baseline(
            identity_id=identity_id,
            events=events,
            window_start=window_start,
            window_end=window_end
        )
        
        # Store baseline
        self.store.store_baseline(baseline)
        
        # Emit audit ledger entry
        try:
            ledger_entry = self.ledger_writer.create_entry(
                component='uba-core',
                component_instance_id='uba-core',
                action_type='UBA_BASELINE_BUILT',
                subject={'type': 'identity', 'id': identity_id},
                actor={'type': 'system', 'identifier': 'uba-core'},
                payload={
                    'baseline_id': baseline.get('baseline_id', ''),
                    'baseline_window_start': baseline.get('baseline_window_start', ''),
                    'baseline_window_end': baseline.get('baseline_window_end', '')
                }
            )
            baseline['ledger_entry_id'] = ledger_entry.get('ledger_entry_id', '')
        except Exception as e:
            raise UBAAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return baseline
    
    def get_identity_baseline(
        self,
        identity_id: str,
        baseline_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get identity baseline.
        
        Args:
            identity_id: Identity identifier
            baseline_id: Optional baseline identifier (if None, returns latest)
        
        Returns:
            Baseline dictionary, or None if not found
        """
        if baseline_id:
            return self.store.get_baseline(baseline_id)
        else:
            return self.store.get_latest_baseline(identity_id)
