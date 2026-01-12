#!/usr/bin/env python3
"""
RansomEye Signed Reporting Engine - Report Store
AUTHORITATIVE: Immutable, append-only storage for signed reports
"""

import json
from pathlib import Path
from typing import Dict, Any, Iterator, Optional, List
import os


class ReportStoreError(Exception):
    """Base exception for report store errors."""
    pass


class ReportStore:
    """
    Immutable, append-only storage for signed reports.
    
    Properties:
    - Immutable: Records cannot be modified after creation
    - Append-only: Only additions allowed, no updates or deletes
    - Deterministic: Same inputs always produce same outputs
    - Offline-capable: No network or database dependencies
    - Long-term archival: Supports years-long retention
    """
    
    def __init__(self, store_path: Path):
        """
        Initialize report store.
        
        Args:
            store_path: Path to report store file (JSON lines format)
        """
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
    
    def store_report(self, report_record: Dict[str, Any]) -> None:
        """
        Store signed report record (immutable).
        
        Args:
            report_record: Signed report record dictionary (must be complete and valid)
        
        Raises:
            ReportStoreError: If storage fails
        """
        try:
            # Serialize to JSON (compact, one line)
            record_json = json.dumps(report_record, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            
            # Append to store file
            with open(self.store_path, 'a', encoding='utf-8') as f:
                f.write(record_json)
                f.write('\n')
                f.flush()
                os.fsync(f.fileno())
            
        except Exception as e:
            raise ReportStoreError(f"Failed to store report: {e}") from e
    
    def get_report_by_id(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        Get signed report by ID.
        
        Args:
            report_id: Report identifier
        
        Returns:
            Report record dictionary, or None if not found
        """
        for report in self.read_all():
            if report.get('report_id') == report_id:
                return report
        return None
    
    def get_reports_by_incident_id(self, incident_id: str) -> List[Dict[str, Any]]:
        """
        Get all signed reports for incident ID.
        
        Args:
            incident_id: Incident identifier
        
        Returns:
            List of report record dictionaries
        """
        reports = []
        for report in self.read_all():
            if report.get('incident_id') == incident_id:
                reports.append(report)
        return reports
    
    def read_all(self) -> Iterator[Dict[str, Any]]:
        """
        Read all signed reports from store.
        
        Yields:
            Report record dictionaries
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
            raise ReportStoreError(f"Failed to read report store: {e}") from e
    
    def count_reports(self) -> int:
        """
        Get count of stored signed reports.
        
        Returns:
            Number of reports
        """
        count = 0
        for _ in self.read_all():
            count += 1
        return count
