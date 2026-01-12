#!/usr/bin/env python3
"""
RansomEye Orchestrator - Orchestrator API
AUTHORITATIVE: Single API for workflow orchestration with audit ledger integration
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, timezone
import json

# Add audit-ledger to path
_audit_ledger_dir = Path(__file__).parent.parent.parent / "audit-ledger"
if str(_audit_ledger_dir) not in sys.path:
    sys.path.insert(0, str(_audit_ledger_dir))

# Import audit ledger components
import importlib.util

_store_spec = importlib.util.spec_from_file_location("audit_ledger_storage", _audit_ledger_dir / "storage" / "append_only_store.py")
_store_module = importlib.util.module_from_spec(_store_spec)
_store_spec.loader.exec_module(_store_module)
AppendOnlyStore = _store_module.AppendOnlyStore
LedgerWriter = _store_module.LedgerWriter

_key_manager_spec = importlib.util.spec_from_file_location("audit_ledger_key_manager", _audit_ledger_dir / "crypto" / "key_manager.py")
_key_manager_module = importlib.util.module_from_spec(_key_manager_spec)
_key_manager_spec.loader.exec_module(_key_manager_module)
KeyManager = _key_manager_module.KeyManager

_signer_spec = importlib.util.spec_from_file_location("audit_ledger_signer", _audit_ledger_dir / "crypto" / "signer.py")
_signer_module = importlib.util.module_from_spec(_signer_spec)
_signer_spec.loader.exec_module(_signer_module)
Signer = _signer_module.Signer

# Import orchestrator components
_orchestrator_dir = Path(__file__).parent.parent
if str(_orchestrator_dir) not in sys.path:
    sys.path.insert(0, str(_orchestrator_dir))

_workflow_registry_spec = importlib.util.spec_from_file_location("workflow_registry", _orchestrator_dir / "engine" / "workflow_registry.py")
_workflow_registry_module = importlib.util.module_from_spec(_workflow_registry_spec)
_workflow_registry_spec.loader.exec_module(_workflow_registry_module)
WorkflowRegistry = _workflow_registry_module.WorkflowRegistry

_dependency_resolver_spec = importlib.util.spec_from_file_location("dependency_resolver", _orchestrator_dir / "engine" / "dependency_resolver.py")
_dependency_resolver_module = importlib.util.module_from_spec(_dependency_resolver_spec)
_dependency_resolver_spec.loader.exec_module(_dependency_resolver_module)
DependencyResolver = _dependency_resolver_module.DependencyResolver

_job_executor_spec = importlib.util.spec_from_file_location("job_executor", _orchestrator_dir / "engine" / "job_executor.py")
_job_executor_module = importlib.util.module_from_spec(_job_executor_spec)
_job_executor_spec.loader.exec_module(_job_executor_module)
JobExecutor = _job_executor_module.JobExecutor

_replay_engine_spec = importlib.util.spec_from_file_location("replay_engine", _orchestrator_dir / "engine" / "replay_engine.py")
_replay_engine_module = importlib.util.module_from_spec(_replay_engine_spec)
_replay_engine_spec.loader.exec_module(_replay_engine_module)
ReplayEngine = _replay_engine_module.ReplayEngine


class OrchestratorAPIError(Exception):
    """Base exception for orchestrator API errors."""
    pass


class OrchestratorAPI:
    """
    Single API for workflow orchestration.
    
    All operations:
    - Register workflows (immutable)
    - Execute workflows (deterministic, authority-bound)
    - Replay workflows (full rehydration)
    - Emit audit ledger entries (every operation)
    """
    
    def __init__(
        self,
        workflows_store_path: Path,
        jobs_store_path: Path,
        ledger_path: Path,
        ledger_key_dir: Path
    ):
        """
        Initialize orchestrator API.
        
        Args:
            workflows_store_path: Path to workflows store
            jobs_store_path: Path to job records store
            ledger_path: Path to audit ledger file
            ledger_key_dir: Directory containing ledger signing keys
        """
        self.workflow_registry = WorkflowRegistry(workflows_store_path)
        self.dependency_resolver = DependencyResolver()
        self.job_executor = JobExecutor()
        self.replay_engine = ReplayEngine(jobs_store_path)
        self.jobs_store_path = Path(jobs_store_path)
        self.jobs_store_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize audit ledger
        try:
            ledger_store = AppendOnlyStore(ledger_path, read_only=False)
            ledger_key_manager = KeyManager(ledger_key_dir)
            ledger_private_key, ledger_public_key, ledger_key_id = ledger_key_manager.get_or_create_keypair()
            ledger_signer = Signer(ledger_private_key, ledger_key_id)
            self.ledger_writer = LedgerWriter(ledger_store, ledger_signer)
        except Exception as e:
            raise OrchestratorAPIError(f"Failed to initialize audit ledger: {e}") from e
    
    def register_workflow(self, workflow: Dict[str, Any]) -> None:
        """
        Register workflow.
        
        Args:
            workflow: Workflow dictionary
        """
        # Validate workflow
        self.workflow_registry.register_workflow(workflow)
        
        # Validate dependencies
        try:
            self.dependency_resolver.resolve_execution_order(workflow)
        except Exception as e:
            raise OrchestratorAPIError(f"Workflow dependency validation failed: {e}") from e
        
        # Emit audit ledger entry
        try:
            self.ledger_writer.create_entry(
                component='orchestrator',
                component_instance_id='orchestrator',
                action_type='workflow_registered',
                subject={'type': 'workflow', 'id': workflow.get('workflow_id', '')},
                actor={'type': 'system', 'identifier': 'orchestrator'},
                payload={
                    'workflow_id': workflow.get('workflow_id', ''),
                    'version': workflow.get('version', ''),
                    'steps_count': len(workflow.get('steps', []))
                }
            )
        except Exception as e:
            raise OrchestratorAPIError(f"Failed to emit audit ledger entry: {e}") from e
    
    def execute_workflow(
        self,
        workflow_id: str,
        trigger_type: str,
        input_data: Dict[str, Any],
        authority_state: str = 'NONE',
        explanation_bundle_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute workflow.
        
        Process:
        1. Load workflow
        2. Validate trigger type
        3. Validate authority
        4. Validate explanation
        5. Resolve execution order
        6. Execute steps in order
        7. Store job records
        8. Emit audit ledger entries
        
        Args:
            workflow_id: Workflow identifier
            trigger_type: Trigger type (manual | alert | validator)
            input_data: Input data dictionary
            authority_state: Authority state (NONE | REQUIRED | VERIFIED)
            explanation_bundle_id: Explanation bundle identifier
        
        Returns:
            List of job records
        """
        # Load workflow
        workflow = self.workflow_registry.get_workflow(workflow_id)
        if not workflow:
            raise OrchestratorAPIError(f"Workflow not found: {workflow_id}")
        
        # Validate trigger type
        allowed_triggers = workflow.get('allowed_triggers', [])
        if trigger_type not in allowed_triggers:
            raise OrchestratorAPIError(f"Trigger type {trigger_type} not allowed for workflow {workflow_id}")
        
        # Validate authority
        required_authority = workflow.get('required_authority', 'NONE')
        if required_authority != 'NONE' and authority_state != 'VERIFIED':
            raise OrchestratorAPIError(f"Workflow requires authority but state is {authority_state}")
        
        # Validate explanation
        if not explanation_bundle_id:
            raise OrchestratorAPIError("Workflow requires explanation bundle but none provided")
        
        # Resolve execution order
        execution_order = self.dependency_resolver.resolve_execution_order(workflow)
        
        # Emit workflow start audit entry
        try:
            workflow_start_entry = self.ledger_writer.create_entry(
                component='orchestrator',
                component_instance_id='orchestrator',
                action_type='workflow_started',
                subject={'type': 'workflow', 'id': workflow_id},
                actor={'type': 'system', 'identifier': 'orchestrator'},
                payload={
                    'workflow_id': workflow_id,
                    'trigger_type': trigger_type,
                    'steps_count': len(execution_order)
                }
            )
        except Exception as e:
            raise OrchestratorAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        # Execute steps
        job_records = []
        step_outputs = {}  # output_ref -> output_data
        
        for step in execution_order:
            # Prepare input data for step
            step_input_data = {}
            for input_ref in step.get('input_refs', []):
                if input_ref in step_outputs:
                    step_input_data[input_ref] = step_outputs[input_ref]
                elif input_ref in input_data:
                    step_input_data[input_ref] = input_data[input_ref]
            
            # Execute step
            job_record = self.job_executor.execute_step(
                step=step,
                workflow=workflow,
                input_data=step_input_data,
                authority_state=authority_state,
                explanation_bundle_id=explanation_bundle_id
            )
            
            # Store job record
            self._store_job_record(job_record)
            
            # Emit audit ledger entry
            try:
                ledger_entry = self.ledger_writer.create_entry(
                    component='orchestrator',
                    component_instance_id='orchestrator',
                    action_type='job_executed',
                    subject={'type': 'job', 'id': job_record.get('job_id', '')},
                    actor={'type': 'system', 'identifier': 'orchestrator'},
                    payload={
                        'job_id': job_record.get('job_id', ''),
                        'step_id': step.get('step_id', ''),
                        'status': job_record.get('status', '')
                    }
                )
                job_record['ledger_entry_id'] = ledger_entry.get('ledger_entry_id', '')
            except Exception as e:
                raise OrchestratorAPIError(f"Failed to emit audit ledger entry: {e}") from e
            
            job_records.append(job_record)
            
            # Store step outputs
            if job_record.get('status') == 'COMPLETED':
                output_data = job_record.get('output_data', {})
                for output_ref in step.get('output_refs', []):
                    step_outputs[output_ref] = output_data.get(output_ref, {})
            
            # Handle failure
            if job_record.get('status') in ['FAILED', 'TIMEOUT']:
                failure_policy = workflow.get('failure_policy', 'STOP')
                if failure_policy == 'STOP':
                    break
                elif failure_policy == 'RECORD_ONLY':
                    continue
                # ROLLBACK would require explicit rollback steps (not implemented in Phase G)
        
        # Emit workflow completion audit entry
        try:
            self.ledger_writer.create_entry(
                component='orchestrator',
                component_instance_id='orchestrator',
                action_type='workflow_completed',
                subject={'type': 'workflow', 'id': workflow_id},
                actor={'type': 'system', 'identifier': 'orchestrator'},
                payload={
                    'workflow_id': workflow_id,
                    'jobs_count': len(job_records),
                    'completed_jobs': len([j for j in job_records if j.get('status') == 'COMPLETED'])
                }
            )
        except Exception as e:
            raise OrchestratorAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return job_records
    
    def _store_job_record(self, job_record: Dict[str, Any]) -> None:
        """Store job record to file-based store."""
        try:
            job_json = json.dumps(job_record, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(self.jobs_store_path, 'a', encoding='utf-8') as f:
                f.write(job_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise OrchestratorAPIError(f"Failed to store job record: {e}") from e
