#!/usr/bin/env python3
"""
RansomEye HNMP Engine - HNMP Store
AUTHORITATIVE: Immutable HNMP event storage
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import json


class HNMPStoreError(Exception):
    """Base exception for HNMP store errors."""
    pass


class HNMPStore:
    """
    Immutable HNMP event storage.
    
    Properties:
    - Immutable: Events cannot be modified after storage
    - Deterministic: Same event = same storage result
    - Type-separated: Events stored by type
    """
    
    def __init__(
        self,
        host_events_path: Path,
        network_events_path: Path,
        process_events_path: Path,
        malware_events_path: Path,
        correlations_path: Path
    ):
        """
        Initialize HNMP store.
        
        Args:
            host_events_path: Path to host events store
            network_events_path: Path to network events store
            process_events_path: Path to process events store
            malware_events_path: Path to malware events store
            correlations_path: Path to correlations store
        """
        self.host_events_path = Path(host_events_path)
        self.host_events_path.parent.mkdir(parents=True, exist_ok=True)
        self.network_events_path = Path(network_events_path)
        self.network_events_path.parent.mkdir(parents=True, exist_ok=True)
        self.process_events_path = Path(process_events_path)
        self.process_events_path.parent.mkdir(parents=True, exist_ok=True)
        self.malware_events_path = Path(malware_events_path)
        self.malware_events_path.parent.mkdir(parents=True, exist_ok=True)
        self.correlations_path = Path(correlations_path)
        self.correlations_path.parent.mkdir(parents=True, exist_ok=True)
    
    def store_host_event(self, event: Dict[str, Any]) -> None:
        """Store host event."""
        self._store_event(self.host_events_path, event)
    
    def store_network_event(self, event: Dict[str, Any]) -> None:
        """Store network event."""
        self._store_event(self.network_events_path, event)
    
    def store_process_event(self, event: Dict[str, Any]) -> None:
        """Store process event."""
        self._store_event(self.process_events_path, event)
    
    def store_malware_event(self, event: Dict[str, Any]) -> None:
        """Store malware event."""
        self._store_event(self.malware_events_path, event)
    
    def store_correlation(self, correlation: Dict[str, Any]) -> None:
        """Store correlation."""
        self._store_event(self.correlations_path, correlation)
    
    def _store_event(self, store_path: Path, event: Dict[str, Any]) -> None:
        """Store event to file-based store."""
        try:
            event_json = json.dumps(event, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(store_path, 'a', encoding='utf-8') as f:
                f.write(event_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise HNMPStoreError(f"Failed to store event: {e}") from e
    
    def get_event(self, event_id: str, event_type: str) -> Optional[Dict[str, Any]]:
        """
        Get event by ID and type.
        
        Args:
            event_id: Event identifier
            event_type: Event type (host, network, process, malware)
        
        Returns:
            Event dictionary, or None if not found
        """
        if event_type == 'host':
            store_path = self.host_events_path
        elif event_type == 'network':
            store_path = self.network_events_path
        elif event_type == 'process':
            store_path = self.process_events_path
        elif event_type == 'malware':
            store_path = self.malware_events_path
        else:
            return None
        
        if not store_path.exists():
            return None
        
        try:
            with open(store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    event = json.loads(line)
                    if event.get('event_id') == event_id:
                        return event
        except Exception:
            pass
        
        return None
