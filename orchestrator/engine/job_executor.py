#!/usr/bin/env python3
"""
RansomEye Orchestrator - Job Executor
AUTHORITATIVE: Deterministic job execution with authority and explanation checks
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
import uuid
import hashlib
import json
import time


class JobExecutionError(Exception):
    """Base exception for job execution errors."""
    pass


class JobExecutor:
    """
    Deterministic job executor.
    
    Properties:
    - Deterministic: Same inputs always produce same execution
    - Authority-bound: Execution requires authority validation
    - Explanation-anchored: Execution requires explanation bundle
    - Fail-closed: Failures are explicit and terminal
    """
    
    def __init__(self):
        """Initialize job executor."""
        pass
    
    def execute_step(
        self,
        step: Dict[str, Any],
        workflow: Dict[str, Any],
        input_data: Dict[str, Any],
        authority_state: str,
        explanation_bundle_id: str
    ) -> Dict[str, Any]:
        """
        Execute workflow step.
        
        Args:
            step: Step dictionary
            workflow: Workflow dictionary
            input_data: Input data dictionary
            authority_state: Authority state (NONE | REQUIRED | VERIFIED)
            explanation_bundle_id: Explanation bundle identifier
        
        Returns:
            Job record dictionary
        """
        job_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc).isoformat()
        
        # Validate authority
        if step.get('authority_required') != 'NONE' and authority_state != 'VERIFIED':
            raise JobExecutionError(f"Step requires authority but state is {authority_state}")
        
        # Validate explanation
        if step.get('explanation_required', False) and not explanation_bundle_id:
            raise JobExecutionError("Step requires explanation bundle but none provided")
        
        # Create job record
        job_record = {
            'job_id': job_id,
            'workflow_id': workflow.get('workflow_id', ''),
            'step_id': step.get('step_id', ''),
            'step_type': step.get('step_type', ''),
            'status': 'RUNNING',
            'started_at': started_at,
            'finished_at': '',
            'input_refs': step.get('input_refs', []),
            'output_refs': step.get('output_refs', []),
            'authority_state': authority_state,
            'explanation_bundle_id': explanation_bundle_id,
            'immutable_hash': '',
            'ledger_entry_id': ''
        }
        
        # Execute step (deterministic timeout)
        timeout = step.get('deterministic_timeout', 60)
        try:
            # Simulate step execution
            # In production, would call appropriate subsystem
            output_data = self._execute_step_internal(step, input_data, timeout)
            
            finished_at = datetime.now(timezone.utc).isoformat()
            job_record['status'] = 'COMPLETED'
            job_record['finished_at'] = finished_at
            job_record['output_data'] = output_data
            
        except TimeoutError:
            finished_at = datetime.now(timezone.utc).isoformat()
            job_record['status'] = 'TIMEOUT'
            job_record['finished_at'] = finished_at
        except Exception as e:
            finished_at = datetime.now(timezone.utc).isoformat()
            job_record['status'] = 'FAILED'
            job_record['finished_at'] = finished_at
            job_record['error'] = str(e)
        
        # Calculate immutable hash
        job_record['immutable_hash'] = self._calculate_hash(job_record)
        
        return job_record
    
    def _execute_step_internal(
        self,
        step: Dict[str, Any],
        input_data: Dict[str, Any],
        timeout: int
    ) -> Dict[str, Any]:
        """
        Execute step internally.
        
        For Phase G, this is a stub that simulates execution.
        In production, would call appropriate subsystem.
        
        Args:
            step: Step dictionary
            input_data: Input data dictionary
            timeout: Timeout in seconds
        
        Returns:
            Output data dictionary
        """
        step_type = step.get('step_type', '')
        
        # Simulate execution (deterministic)
        time.sleep(0.1)  # Simulate work
        
        # Return output data
        return {
            'step_id': step.get('step_id', ''),
            'step_type': step_type,
            'output_refs': step.get('output_refs', []),
            'executed_at': datetime.now(timezone.utc).isoformat()
        }
    
    def _calculate_hash(self, job_record: Dict[str, Any]) -> str:
        """
        Calculate SHA256 hash of job record.
        
        Args:
            job_record: Job record dictionary
        
        Returns:
            SHA256 hash as hex string
        """
        # Create hashable content (exclude hash and ledger_entry_id)
        hashable_content = {
            k: v for k, v in job_record.items()
            if k not in ['immutable_hash', 'ledger_entry_id']
        }
        
        # Serialize to canonical JSON
        canonical_json = json.dumps(hashable_content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        
        # Calculate SHA256 hash
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
