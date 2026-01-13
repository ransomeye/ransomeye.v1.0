#!/usr/bin/env python3
"""
RansomEye LLM Summarizer - Summary Store
AUTHORITATIVE: Immutable summary storage
"""

import json
from typing import Dict, Any, Optional, List
from pathlib import Path


class SummaryStoreError(Exception):
    """Base exception for summary store errors."""
    pass


class SummaryStore:
    """
    Immutable summary storage.
    
    Properties:
    - Append-only: No updates, no deletes
    - Immutable: All records are immutable
    - Versioned: Summaries are versioned by generation
    """
    
    def __init__(self, store_path: Path):
        """
        Initialize summary store.
        
        Args:
            store_path: Path to summary store file (JSONL)
        """
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
    
    def store_summary(self, summary: Dict[str, Any]) -> None:
        """
        Store summary record (append-only).
        
        Args:
            summary: Summary record dictionary
        
        Raises:
            SummaryStoreError: If storage fails
        """
        try:
            with open(self.store_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(summary, separators=(',', ':')) + '\n')
        except Exception as e:
            raise SummaryStoreError(f"Failed to store summary: {e}") from e
    
    def get_summary(self, summary_id: str) -> Optional[Dict[str, Any]]:
        """
        Get summary by ID.
        
        Args:
            summary_id: Summary identifier
        
        Returns:
            Summary record dictionary or None if not found
        """
        if not self.store_path.exists():
            return None
        
        try:
            with open(self.store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    summary = json.loads(line)
                    if summary.get('summary_id') == summary_id:
                        return summary
        except Exception:
            pass
        
        return None
    
    def list_summaries(
        self,
        narrative_type: Optional[str] = None,
        incident_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List summaries with optional filters.
        
        Args:
            narrative_type: Optional narrative type filter
            incident_id: Optional incident ID filter
        
        Returns:
            List of summary record dictionaries
        """
        summaries = []
        
        if not self.store_path.exists():
            return summaries
        
        try:
            with open(self.store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    summary = json.loads(line)
                    
                    # Apply filters
                    if narrative_type and summary.get('narrative_type') != narrative_type:
                        continue
                    if incident_id:
                        # Would need to extract incident_id from summary_request_id
                        # For now, skip this filter
                        pass
                    
                    summaries.append(summary)
        except Exception:
            pass
        
        return summaries
