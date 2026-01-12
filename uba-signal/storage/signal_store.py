#!/usr/bin/env python3
"""
RansomEye UBA Signal - Signal Store
AUTHORITATIVE: Append-only, immutable signal storage
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import json


class SignalStoreError(Exception):
    """Base exception for signal store errors."""
    pass


class SignalStore:
    """
    Append-only, immutable signal storage.
    
    Properties:
    - Append-only: No updates, no deletes
    - Immutable: All records are immutable
    - Versioned: Signals versioned by observation window
    """
    
    def __init__(
        self,
        signals_store_path: Path,
        summaries_store_path: Path
    ):
        """
        Initialize signal store.
        
        Args:
            signals_store_path: Path to signals store
            summaries_store_path: Path to summaries store
        """
        self.signals_store_path = Path(signals_store_path)
        self.signals_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.summaries_store_path = Path(summaries_store_path)
        self.summaries_store_path.parent.mkdir(parents=True, exist_ok=True)
    
    def store_signal(self, signal: Dict[str, Any]) -> None:
        """Store signal (append-only)."""
        self._store_record(self.signals_store_path, signal)
    
    def store_summary(self, summary: Dict[str, Any]) -> None:
        """Store summary (append-only)."""
        self._store_record(self.summaries_store_path, summary)
    
    def get_signal(self, signal_id: str) -> Optional[Dict[str, Any]]:
        """Get signal by ID."""
        return self._get_record(self.signals_store_path, 'signal_id', signal_id)
    
    def get_signals_for_identity(
        self,
        identity_id: str,
        window_start: Optional[str] = None,
        window_end: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all signals for identity, optionally filtered by window."""
        signals = []
        
        if not self.signals_store_path.exists():
            return signals
        
        try:
            with open(self.signals_store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    signal = json.loads(line)
                    if signal.get('identity_id') == identity_id:
                        # Filter by window if provided
                        if window_start or window_end:
                            signal_time = signal.get('created_timestamp', '')
                            if window_start and signal_time < window_start:
                                continue
                            if window_end and signal_time > window_end:
                                continue
                        signals.append(signal)
        except Exception:
            pass
        
        return signals
    
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
            raise SignalStoreError(f"Failed to store record: {e}") from e
    
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
