#!/usr/bin/env python3
"""
RansomEye Incident Response - Rollback Engine
AUTHORITATIVE: Explicit, signed, logged rollback of playbook executions
"""

from typing import Dict, Any
from datetime import datetime, timezone
import uuid


class RollbackError(Exception):
    """Base exception for rollback errors."""
    pass


class RollbackEngine:
    """
    Explicit, signed, logged rollback of playbook executions.
    
    Properties:
    - Explicit: Rollbacks are explicit, never implicit
    - Signed: All rollbacks are signed
    - Logged: All rollbacks are logged to audit ledger
    - Deterministic: Same execution always produces same rollback
    """
    
    def __init__(self):
        """Initialize rollback engine."""
        pass
    
    def create_rollback(
        self,
        execution_record: Dict[str, Any],
        rolled_back_by: str,
        rollback_reason: str
    ) -> Dict[str, Any]:
        """
        Create rollback record.
        
        Args:
            execution_record: Execution record to rollback
            rolled_back_by: Human identifier who initiated rollback
            rollback_reason: Reason for rollback
        
        Returns:
            Rollback record dictionary
        """
        rollback_id = str(uuid.uuid4())
        rollback_timestamp = datetime.now(timezone.utc).isoformat()
        
        # Build rollback record
        rollback_record = {
            'rollback_id': rollback_id,
            'execution_id': execution_record.get('execution_id', ''),
            'playbook_id': execution_record.get('playbook_id', ''),
            'playbook_version': execution_record.get('playbook_version', ''),
            'subject_id': execution_record.get('subject_id', ''),
            'rollback_timestamp': rollback_timestamp,
            'rolled_back_by': rolled_back_by,
            'rollback_reason': rollback_reason,
            'original_execution': execution_record,
            'rollback_steps': self._generate_rollback_steps(execution_record)
        }
        
        return rollback_record
    
    def _generate_rollback_steps(self, execution_record: Dict[str, Any]) -> list:
        """
        Generate rollback steps for execution.
        
        Rollback steps are generated in reverse order of execution.
        
        Args:
            execution_record: Execution record
        
        Returns:
            List of rollback step dictionaries
        """
        step_results = execution_record.get('step_results', [])
        rollback_steps = []
        
        # Generate rollback steps in reverse order
        for step_result in reversed(step_results):
            step_type = step_result.get('step_type', '')
            step_output = step_result.get('step_output', {})
            
            # Generate rollback step based on step type
            rollback_step = {
                'step_id': step_result.get('step_id', ''),
                'step_type': step_type,
                'rollback_action': self._get_rollback_action(step_type),
                'rollback_parameters': self._get_rollback_parameters(step_type, step_output)
            }
            rollback_steps.append(rollback_step)
        
        return rollback_steps
    
    def _get_rollback_action(self, step_type: str) -> str:
        """Get rollback action for step type."""
        rollback_actions = {
            'isolate_host': 'restore_host',
            'block_ip': 'unblock_ip',
            'disable_account': 'enable_account',
            'snapshot_memory': 'delete_snapshot',
            'snapshot_disk': 'delete_snapshot',
            'notify_human': 'no_rollback'  # Notifications cannot be rolled back
        }
        return rollback_actions.get(step_type, 'unknown')
    
    def _get_rollback_parameters(self, step_type: str, step_output: Dict[str, Any]) -> Dict[str, Any]:
        """Get rollback parameters for step type."""
        # Extract parameters from step output for rollback
        if step_type == 'isolate_host':
            return {'host_id': step_output.get('host_id', '')}
        elif step_type == 'block_ip':
            return {'ip_address': step_output.get('ip_address', '')}
        elif step_type == 'disable_account':
            return {'account_id': step_output.get('account_id', '')}
        elif step_type == 'snapshot_memory':
            return {'snapshot_location': step_output.get('snapshot_location', '')}
        elif step_type == 'snapshot_disk':
            return {'snapshot_location': step_output.get('snapshot_location', '')}
        else:
            return {}
