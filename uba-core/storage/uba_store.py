#!/usr/bin/env python3
"""
RansomEye UBA Core - UBA Store
AUTHORITATIVE: Append-only, immutable UBA storage
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import json


class UBAStoreError(Exception):
    """Base exception for UBA store errors."""
    pass


class UBAStore:
    """
    Append-only, immutable UBA storage.
    
    Properties:
    - Append-only: No updates, no deletes
    - Immutable: All records are immutable
    - Versioned baselines: Baselines are versioned by time window
    """
    
    def __init__(
        self,
        identities_store_path: Path,
        events_store_path: Path,
        baselines_store_path: Path
    ):
        """
        Initialize UBA store.
        
        Args:
            identities_store_path: Path to identities store
            events_store_path: Path to behavior events store
            baselines_store_path: Path to baselines store
        """
        self.identities_store_path = Path(identities_store_path)
        self.identities_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.events_store_path = Path(events_store_path)
        self.events_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.baselines_store_path = Path(baselines_store_path)
        self.baselines_store_path.parent.mkdir(parents=True, exist_ok=True)
    
    def store_identity(self, identity: Dict[str, Any]) -> None:
        """Store identity (append-only)."""
        self._store_record(self.identities_store_path, identity)
    
    def store_event(self, event: Dict[str, Any]) -> None:
        """Store behavior event (append-only)."""
        self._store_record(self.events_store_path, event)
    
    def store_baseline(self, baseline: Dict[str, Any]) -> None:
        """Store baseline (append-only, versioned by time window)."""
        self._store_record(self.baselines_store_path, baseline)
    
    def get_identity(self, identity_id: str) -> Optional[Dict[str, Any]]:
        """Get identity by ID."""
        return self._get_record(self.identities_store_path, 'identity_id', identity_id)
    
    def get_identity_by_canonical_hash(self, canonical_hash: str) -> Optional[Dict[str, Any]]:
        """Get identity by canonical hash."""
        return self._get_record(self.identities_store_path, 'canonical_identity_hash', canonical_hash)
    
    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get event by ID."""
        return self._get_record(self.events_store_path, 'event_id', event_id)
    
    def get_events_for_identity(
        self,
        identity_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all events for identity, optionally filtered by time range."""
        events = []
        
        if not self.events_store_path.exists():
            return events
        
        try:
            with open(self.events_store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    event = json.loads(line)
                    if event.get('identity_id') == identity_id:
                        # Filter by time if provided
                        if start_time or end_time:
                            event_time = event.get('timestamp', '')
                            if start_time and event_time < start_time:
                                continue
                            if end_time and event_time > end_time:
                                continue
                        events.append(event)
        except Exception:
            pass
        
        return events
    
    def get_baseline(self, baseline_id: str) -> Optional[Dict[str, Any]]:
        """Get baseline by ID."""
        return self._get_record(self.baselines_store_path, 'baseline_id', baseline_id)
    
    def get_latest_baseline(self, identity_id: str) -> Optional[Dict[str, Any]]:
        """Get latest baseline for identity."""
        baselines = []
        
        if not self.baselines_store_path.exists():
            return None
        
        try:
            with open(self.baselines_store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    baseline = json.loads(line)
                    if baseline.get('identity_id') == identity_id:
                        baselines.append(baseline)
        except Exception:
            pass
        
        if not baselines:
            return None
        
        # Return baseline with latest window_end
        return max(baselines, key=lambda b: b.get('baseline_window_end', ''))
    
    def _store_record(self, store_path: Path, record: Dict[str, Any]) -> None:
        """Store record to file-based store (append-only)."""
        try:
            record_json = json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(store_path, 'a', encoding='utf-8') as f:
                f.write(record_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise UBAStoreError(f"Failed to store record: {e}") from e
    
    def _get_record(self, store_path: Path, key_field: str, key_value: str) -> Optional[Dict[str, Any]]:
        """Get record by key field and value."""
        if not store_path.exists():
            return None
        
        try:
            with open(store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    record = json.loads(line)
                    if record.get(key_field) == key_value:
                        return record
        except Exception:
            pass
        
        return None
