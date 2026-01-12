#!/usr/bin/env python3
"""
RansomEye UBA Drift - Delta Store
AUTHORITATIVE: Append-only, immutable delta storage
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import json


class DeltaStoreError(Exception):
    """Base exception for delta store errors."""
    pass


class DeltaStore:
    """
    Append-only, immutable delta storage.
    
    Properties:
    - Append-only: No updates, no deletes
    - Immutable: All records are immutable
    - Versioned: Deltas versioned by window
    """
    
    def __init__(
        self,
        deltas_store_path: Path,
        summaries_store_path: Path
    ):
        """
        Initialize delta store.
        
        Args:
            deltas_store_path: Path to deltas store
            summaries_store_path: Path to summaries store
        """
        self.deltas_store_path = Path(deltas_store_path)
        self.deltas_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.summaries_store_path = Path(summaries_store_path)
        self.summaries_store_path.parent.mkdir(parents=True, exist_ok=True)
    
    def store_delta(self, delta: Dict[str, Any]) -> None:
        """Store delta (append-only)."""
        self._store_record(self.deltas_store_path, delta)
    
    def store_summary(self, summary: Dict[str, Any]) -> None:
        """Store summary (append-only)."""
        self._store_record(self.summaries_store_path, summary)
    
    def get_delta(self, delta_id: str) -> Optional[Dict[str, Any]]:
        """Get delta by ID."""
        return self._get_record(self.deltas_store_path, 'delta_id', delta_id)
    
    def get_deltas_for_identity(
        self,
        identity_id: str,
        window_start: Optional[str] = None,
        window_end: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all deltas for identity, optionally filtered by window."""
        deltas = []
        
        if not self.deltas_store_path.exists():
            return deltas
        
        try:
            with open(self.deltas_store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    delta = json.loads(line)
                    if delta.get('identity_id') == identity_id:
                        # Filter by window if provided
                        if window_start or window_end:
                            delta_start = delta.get('observation_window_start', '')
                            if window_start and delta_start < window_start:
                                continue
                            if window_end and delta_start > window_end:
                                continue
                        deltas.append(delta)
        except Exception:
            pass
        
        return deltas
    
    def get_summary(self, summary_id: str) -> Optional[Dict[str, Any]]:
        """Get summary by ID."""
        return self._get_record(self.summaries_store_path, 'summary_id', summary_id)
    
    def get_latest_summary(self, identity_id: str) -> Optional[Dict[str, Any]]:
        """Get latest summary for identity."""
        summaries = []
        
        if not self.summaries_store_path.exists():
            return None
        
        try:
            with open(self.summaries_store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    summary = json.loads(line)
                    if summary.get('identity_id') == identity_id:
                        summaries.append(summary)
        except Exception:
            pass
        
        if not summaries:
            return None
        
        # Return summary with latest window_end
        return max(summaries, key=lambda s: s.get('observation_window_end', ''))
    
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
            raise DeltaStoreError(f"Failed to store record: {e}") from e
    
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
