#!/usr/bin/env python3
"""
RansomEye Enterprise Risk Index - Risk Score Store
AUTHORITATIVE: Immutable storage for historical risk scores
"""

import json
from pathlib import Path
from typing import Dict, Any, Iterator, Optional
import os


class RiskStoreError(Exception):
    """Base exception for risk store errors."""
    pass


class RiskStore:
    """
    Immutable storage for historical risk scores.
    
    Properties:
    - Immutable: Records cannot be modified after creation
    - Historical: Maintains complete timeline
    - Deterministic: Same inputs always produce same outputs
    - Offline-capable: No network or database dependencies
    """
    
    def __init__(self, store_path: Path):
        """
        Initialize risk store.
        
        Args:
            store_path: Path to risk score store file (JSON lines format)
        """
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
    
    def store_score(self, score_record: Dict[str, Any]) -> None:
        """
        Store risk score record (immutable).
        
        Args:
            score_record: Risk score record dictionary (must be complete and valid)
        
        Raises:
            RiskStoreError: If storage fails
        """
        try:
            # Serialize to JSON (compact, one line)
            record_json = json.dumps(score_record, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            
            # Append to store file
            with open(self.store_path, 'a', encoding='utf-8') as f:
                f.write(record_json)
                f.write('\n')
                f.flush()
                os.fsync(f.fileno())
            
        except Exception as e:
            raise RiskStoreError(f"Failed to store risk score: {e}") from e
    
    def read_all(self) -> Iterator[Dict[str, Any]]:
        """
        Read all risk score records from store.
        
        Yields:
            Risk score record dictionaries
        """
        if not self.store_path.exists():
            return
        
        try:
            with open(self.store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    yield json.loads(line)
        except Exception as e:
            raise RiskStoreError(f"Failed to read risk store: {e}") from e
    
    def get_latest(self) -> Optional[Dict[str, Any]]:
        """
        Get latest risk score record.
        
        Returns:
            Latest risk score record dictionary, or None if store is empty
        """
        latest = None
        for record in self.read_all():
            latest = record
        return latest
    
    def get_by_timestamp_range(
        self,
        start_timestamp: str,
        end_timestamp: str
    ) -> Iterator[Dict[str, Any]]:
        """
        Get risk scores within timestamp range.
        
        Args:
            start_timestamp: Start timestamp (RFC3339)
            end_timestamp: End timestamp (RFC3339)
        
        Yields:
            Risk score record dictionaries within range
        """
        for record in self.read_all():
            timestamp = record.get('timestamp', '')
            if start_timestamp <= timestamp <= end_timestamp:
                yield record
    
    def count_records(self) -> int:
        """
        Get count of stored risk score records.
        
        Returns:
            Number of records
        """
        count = 0
        for _ in self.read_all():
            count += 1
        return count
