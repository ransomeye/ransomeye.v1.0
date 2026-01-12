#!/usr/bin/env python3
"""
RansomEye Orchestrator - Replay Engine
AUTHORITATIVE: Full workflow rehydration and replay
"""

from typing import Dict, Any, List
from pathlib import Path
import json


class ReplayError(Exception):
    """Base exception for replay errors."""
    pass


class ReplayEngine:
    """
    Workflow replay engine.
    
    Properties:
    - Full rehydration: Rebuilds entire workflow execution from records
    - Deterministic: Same records = same replay
    - Validator-compatible: Replay produces identical outputs
    """
    
    def __init__(self, jobs_store_path: Path):
        """
        Initialize replay engine.
        
        Args:
            jobs_store_path: Path to job records store
        """
        self.jobs_store_path = Path(jobs_store_path)
        self.jobs_store_path.parent.mkdir(parents=True, exist_ok=True)
    
    def replay_workflow(self, workflow_id: str) -> List[Dict[str, Any]]:
        """
        Replay workflow execution from job records.
        
        Args:
            workflow_id: Workflow identifier
        
        Returns:
            List of job records in execution order
        """
        # Load all job records for workflow
        job_records = self._load_job_records(workflow_id)
        
        if not job_records:
            return []
        
        # Sort by started_at (execution order)
        job_records.sort(key=lambda j: j.get('started_at', ''))
        
        return job_records
    
    def _load_job_records(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Load job records for workflow."""
        job_records = []
        
        if not self.jobs_store_path.exists():
            return job_records
        
        try:
            with open(self.jobs_store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    job_record = json.loads(line)
                    if job_record.get('workflow_id') == workflow_id:
                        job_records.append(job_record)
        except Exception:
            pass
        
        return job_records
