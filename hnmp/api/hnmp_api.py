#!/usr/bin/env python3
"""
RansomEye HNMP Engine - HNMP API
AUTHORITATIVE: Single API for HNMP operations with audit ledger integration
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
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

# Import HNMP components
_hnmp_dir = Path(__file__).parent.parent
if str(_hnmp_dir) not in sys.path:
    sys.path.insert(0, str(_hnmp_dir))

_host_normalizer_spec = importlib.util.spec_from_file_location("host_normalizer", _hnmp_dir / "engine" / "host_normalizer.py")
_host_normalizer_module = importlib.util.module_from_spec(_host_normalizer_spec)
_host_normalizer_spec.loader.exec_module(_host_normalizer_module)
HostNormalizer = _host_normalizer_module.HostNormalizer

_network_normalizer_spec = importlib.util.spec_from_file_location("network_normalizer", _hnmp_dir / "engine" / "network_normalizer.py")
_network_normalizer_module = importlib.util.module_from_spec(_network_normalizer_spec)
_network_normalizer_spec.loader.exec_module(_network_normalizer_module)
NetworkNormalizer = _network_normalizer_module.NetworkNormalizer

_process_normalizer_spec = importlib.util.spec_from_file_location("process_normalizer", _hnmp_dir / "engine" / "process_normalizer.py")
_process_normalizer_module = importlib.util.module_from_spec(_process_normalizer_spec)
_process_normalizer_spec.loader.exec_module(_process_normalizer_module)
ProcessNormalizer = _process_normalizer_module.ProcessNormalizer

_malware_normalizer_spec = importlib.util.spec_from_file_location("malware_normalizer", _hnmp_dir / "engine" / "malware_normalizer.py")
_malware_normalizer_module = importlib.util.module_from_spec(_malware_normalizer_spec)
_malware_normalizer_spec.loader.exec_module(_malware_normalizer_module)
MalwareNormalizer = _malware_normalizer_module.MalwareNormalizer

_correlator_spec = importlib.util.spec_from_file_location("correlator", _hnmp_dir / "engine" / "correlator.py")
_correlator_module = importlib.util.module_from_spec(_correlator_spec)
_correlator_spec.loader.exec_module(_correlator_module)
Correlator = _correlator_module.Correlator

_hnmp_store_spec = importlib.util.spec_from_file_location("hnmp_store", _hnmp_dir / "storage" / "hnmp_store.py")
_hnmp_store_module = importlib.util.module_from_spec(_hnmp_store_spec)
_hnmp_store_spec.loader.exec_module(_hnmp_store_module)
HNMPStore = _hnmp_store_module.HNMPStore


class HNMPAPIError(Exception):
    """Base exception for HNMP API errors."""
    pass


class HNMPAPI:
    """
    Single API for HNMP operations.
    
    All operations:
    - Ingest events (host, network, process, malware)
    - Normalize events (canonical form)
    - Correlate events (strictly factual)
    - Store events (immutable)
    - Emit audit ledger entries (every operation)
    """
    
    def __init__(
        self,
        host_events_path: Path,
        network_events_path: Path,
        process_events_path: Path,
        malware_events_path: Path,
        correlations_path: Path,
        ledger_path: Path,
        ledger_key_dir: Path
    ):
        """
        Initialize HNMP API.
        
        Args:
            host_events_path: Path to host events store
            network_events_path: Path to network events store
            process_events_path: Path to process events store
            malware_events_path: Path to malware events store
            correlations_path: Path to correlations store
            ledger_path: Path to audit ledger file
            ledger_key_dir: Directory containing ledger signing keys
        """
        self.host_normalizer = HostNormalizer()
        self.network_normalizer = NetworkNormalizer()
        self.process_normalizer = ProcessNormalizer()
        self.malware_normalizer = MalwareNormalizer()
        self.correlator = Correlator()
        self.store = HNMPStore(
            host_events_path=host_events_path,
            network_events_path=network_events_path,
            process_events_path=process_events_path,
            malware_events_path=malware_events_path,
            correlations_path=correlations_path
        )
        
        # Initialize audit ledger
        try:
            ledger_store = AppendOnlyStore(ledger_path, read_only=False)
            ledger_key_manager = KeyManager(ledger_key_dir)
            ledger_private_key, ledger_public_key, ledger_key_id = ledger_key_manager.get_or_create_keypair()
            ledger_signer = Signer(ledger_private_key, ledger_key_id)
            self.ledger_writer = LedgerWriter(ledger_store, ledger_signer)
        except Exception as e:
            raise HNMPAPIError(f"Failed to initialize audit ledger: {e}") from e
    
    def ingest_event(
        self,
        raw_event: Dict[str, Any],
        event_type: str,
        source_agent: str
    ) -> Dict[str, Any]:
        """
        Ingest and normalize event.
        
        Args:
            raw_event: Raw event from agent
            event_type: Event type (host, network, process, malware)
            source_agent: Source agent identifier
        
        Returns:
            Normalized event dictionary
        """
        # Normalize event
        if event_type == 'host':
            normalized = self.host_normalizer.normalize(raw_event, source_agent)
            self.store.store_host_event(normalized)
        elif event_type == 'network':
            normalized = self.network_normalizer.normalize(raw_event, source_agent)
            self.store.store_network_event(normalized)
        elif event_type == 'process':
            normalized = self.process_normalizer.normalize(raw_event, source_agent)
            self.store.store_process_event(normalized)
        elif event_type == 'malware':
            normalized = self.malware_normalizer.normalize(raw_event, source_agent)
            self.store.store_malware_event(normalized)
        else:
            raise HNMPAPIError(f"Unknown event type: {event_type}")
        
        # Emit audit ledger entry
        try:
            ledger_entry = self.ledger_writer.create_entry(
                component='hnmp',
                component_instance_id='hnmp',
                action_type='event_ingested',
                subject={'type': 'event', 'id': normalized.get('event_id', '')},
                actor={'type': 'system', 'identifier': 'hnmp'},
                payload={
                    'event_id': normalized.get('event_id', ''),
                    'event_type': event_type,
                    'source_agent': source_agent
                }
            )
            normalized['ledger_entry_id'] = ledger_entry.get('ledger_entry_id', '')
        except Exception as e:
            raise HNMPAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return normalized
    
    def correlate_events(
        self,
        source_event_id: str,
        source_type: str,
        target_event_id: str,
        target_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Correlate two events.
        
        Args:
            source_event_id: Source event identifier
            source_type: Source event type
            target_event_id: Target event identifier
            target_type: Target event type
        
        Returns:
            Correlation dictionary, or None if no correlation
        """
        # Get events
        source_event = self.store.get_event(source_event_id, source_type)
        target_event = self.store.get_event(target_event_id, target_type)
        
        if not source_event or not target_event:
            return None
        
        # Correlate
        correlation = self.correlator.correlate(source_event, source_type, target_event, target_type)
        
        if not correlation:
            return None
        
        # Store correlation
        self.store.store_correlation(correlation)
        
        # Emit audit ledger entry
        try:
            ledger_entry = self.ledger_writer.create_entry(
                component='hnmp',
                component_instance_id='hnmp',
                action_type='events_correlated',
                subject={'type': 'correlation', 'id': correlation.get('correlation_id', '')},
                actor={'type': 'system', 'identifier': 'hnmp'},
                payload={
                    'correlation_id': correlation.get('correlation_id', ''),
                    'correlation_type': correlation.get('correlation_type', '')
                }
            )
            correlation['ledger_entry_id'] = ledger_entry.get('ledger_entry_id', '')
        except Exception as e:
            raise HNMPAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return correlation
