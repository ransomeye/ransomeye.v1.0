#!/usr/bin/env python3
"""
RansomEye UBA Alert Context Engine - Context Store
AUTHORITATIVE: Immutable, append-only storage for alert context blocks
"""

import json
from pathlib import Path
from typing import Dict, Any, Iterator, Optional
import os


class ContextStoreError(Exception):
    """Base exception for context store errors."""
    pass


class ContextStore:
    """
    Immutable, append-only storage for alert context blocks.
    
    Properties:
    - Immutable: Records cannot be modified after creation
    - Append-only: Only additions allowed, no updates or deletes
    - Deterministic: Same inputs always produce same outputs
    - Offline-capable: No network or database dependencies
    """
    
    def __init__(self, store_path: Path):
        """
        Initialize context store.
        
        Args:
            store_path: Path to context store file (JSON lines format)
        """
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
    
    def store_context(self, context_block: Dict[str, Any]) -> None:
        """
        Store alert context block (immutable).
        
        Args:
            context_block: Alert context block dictionary (must be complete and valid)
        
        Raises:
            ContextStoreError: If storage fails
        """
        try:
            # Serialize to JSON (compact, one line)
            record_json = json.dumps(context_block, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            
            # Append to store file
            with open(self.store_path, 'a', encoding='utf-8') as f:
                f.write(record_json)
                f.write('\n')
                f.flush()
                os.fsync(f.fileno())
            
        except Exception as e:
            raise ContextStoreError(f"Failed to store context block: {e}") from e
    
    def get_context_by_alert_id(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """
        Get context block for alert ID.
        
        Args:
            alert_id: Alert identifier
        
        Returns:
            Context block dictionary, or None if not found
        """
        for context_block in self.read_all():
            if context_block.get('alert_id') == alert_id:
                return context_block
        return None
    
    def get_contexts_by_incident_id(self, incident_id: str) -> List[Dict[str, Any]]:
        """
        Get all context blocks for incident ID.
        
        Note: This requires reading alert_id and correlating with Alert Engine.
        For Phase M5, we return contexts where alert_id matches pattern.
        
        Args:
            incident_id: Incident identifier
        
        Returns:
            List of context block dictionaries
        """
        contexts = []
        for context_block in self.read_all():
            # For now, we can't directly correlate without Alert Engine
            # This would need Alert Engine integration for full implementation
            # Phase M5: Return empty list (would need Alert Engine read-only access)
            pass
        return contexts
    
    def read_all(self) -> Iterator[Dict[str, Any]]:
        """
        Read all context blocks from store.
        
        Yields:
            Context block dictionaries
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
            raise ContextStoreError(f"Failed to read context store: {e}") from e
    
    def count_contexts(self) -> int:
        """
        Get count of stored context blocks.
        
        Returns:
            Number of context blocks
        """
        count = 0
        for _ in self.read_all():
            count += 1
        return count
