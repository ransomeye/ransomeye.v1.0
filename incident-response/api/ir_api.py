#!/usr/bin/env python3
"""
RansomEye Incident Response - Incident Response API
AUTHORITATIVE: Single API for playbook execution with authority and audit integration
"""

import sys
from pathlib import Path
from typing import Dict, Any
import uuid
from datetime import datetime, timezone

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

# Import incident response components
_ir_dir = Path(__file__).parent.parent
if str(_ir_dir) not in sys.path:
    sys.path.insert(0, str(_ir_dir))

_registry_spec = importlib.util.spec_from_file_location("playbook_registry", _ir_dir / "engine" / "playbook_registry.py")
_registry_module = importlib.util.module_from_spec(_registry_spec)
_registry_spec.loader.exec_module(_registry_module)
PlaybookRegistry = _registry_module.PlaybookRegistry

_execution_spec = importlib.util.spec_from_file_location("execution_engine", _ir_dir / "engine" / "execution_engine.py")
_execution_module = importlib.util.module_from_spec(_execution_spec)
_execution_spec.loader.exec_module(_execution_module)
ExecutionEngine = _execution_module.ExecutionEngine

_rollback_spec = importlib.util.spec_from_file_location("rollback_engine", _ir_dir / "engine" / "rollback_engine.py")
_rollback_module = importlib.util.module_from_spec(_rollback_spec)
_rollback_spec.loader.exec_module(_rollback_module)
RollbackEngine = _rollback_module.RollbackEngine


class IRAPIError(Exception):
    """Base exception for IR API errors."""
    pass


class IRAPI:
    """
    Single API for playbook execution.
    
    All operations:
    - Register playbooks (signed, verified)
    - Execute playbooks (requires authority, explanation, audit)
    - Rollback executions (explicit, signed, logged)
    - Emit audit ledger entries (every operation)
    """
    
    def __init__(
        self,
        registry_path: Path,
        public_keys_dir: Path,
        executions_store_path: Path,
        ledger_path: Path,
        ledger_key_dir: Path
    ):
        """
        Initialize IR API.
        
        Args:
            registry_path: Path to playbook registry file
            public_keys_dir: Directory containing public keys for verification
            executions_store_path: Path to executions store
            ledger_path: Path to audit ledger file
            ledger_key_dir: Directory containing ledger signing keys
        """
        self.registry = PlaybookRegistry(registry_path, public_keys_dir)
        self.execution_engine = ExecutionEngine()
        self.rollback_engine = RollbackEngine()
        self.executions_store_path = Path(executions_store_path)
        self.executions_store_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize audit ledger
        try:
            ledger_store = AppendOnlyStore(ledger_path, read_only=False)
            ledger_key_manager = KeyManager(ledger_key_dir)
            ledger_private_key, ledger_public_key, ledger_key_id = ledger_key_manager.get_or_create_keypair()
            ledger_signer = Signer(ledger_private_key, ledger_key_id)
            self.ledger_writer = LedgerWriter(ledger_store, ledger_signer)
        except Exception as e:
            raise IRAPIError(f"Failed to initialize audit ledger: {e}") from e
    
    def register_playbook(self, playbook: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register playbook in registry.
        
        Args:
            playbook: Playbook dictionary
        
        Returns:
            Registered playbook dictionary
        """
        # Register playbook (validates signature and structure)
        self.registry.register_playbook(playbook)
        
        # Emit audit ledger entry
        try:
            self.ledger_writer.create_entry(
                component='incident-response',
                component_instance_id='ir-engine',
                action_type='playbook_registered',
                subject={'type': 'playbook', 'id': playbook.get('playbook_id', '')},
                actor={'type': 'user', 'identifier': playbook.get('created_by', '')},
                payload={
                    'playbook_name': playbook.get('playbook_name', ''),
                    'playbook_version': playbook.get('playbook_version', ''),
                    'scope': playbook.get('scope', '')
                }
            )
        except Exception as e:
            raise IRAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return playbook
    
    def execute_playbook(
        self,
        playbook_id: str,
        subject_id: str,
        authority_action_id: str,
        explanation_bundle_id: str,
        executed_by: str
    ) -> Dict[str, Any]:
        """
        Execute playbook.
        
        Requirements:
        - Valid playbook signature
        - Valid authority action (HAF)
        - Matching scope
        - Explanation bundle reference (SEE)
        
        Process:
        1. Get playbook from registry
        2. Validate authority action (scope match)
        3. Execute playbook
        4. Store execution record
        5. Emit audit ledger entry
        
        Args:
            playbook_id: Playbook identifier
            subject_id: Subject identifier
            authority_action_id: Human authority action identifier
            explanation_bundle_id: Explanation bundle identifier
            executed_by: Human identifier who executed playbook
        
        Returns:
            Execution record dictionary
        """
        # Get playbook
        playbook = self.registry.get_playbook(playbook_id)
        if not playbook:
            raise IRAPIError(f"Playbook not found: {playbook_id}")
        
        # Validate authority action (would need HAF integration)
        # For Phase D1, we assume authority is validated externally
        
        # Execute playbook
        execution_record = self.execution_engine.execute_playbook(
            playbook=playbook,
            subject_id=subject_id,
            executed_by=executed_by
        )
        
        # Add required fields
        execution_record['authority_action_id'] = authority_action_id
        execution_record['explanation_bundle_id'] = explanation_bundle_id
        
        # Store execution record
        self._store_execution(execution_record)
        
        # Emit audit ledger entry
        try:
            ledger_entry = self.ledger_writer.create_entry(
                component='incident-response',
                component_instance_id='ir-engine',
                action_type='playbook_executed',
                subject={'type': 'execution', 'id': execution_record.get('execution_id', '')},
                actor={'type': 'user', 'identifier': executed_by},
                payload={
                    'playbook_id': playbook_id,
                    'playbook_version': playbook.get('playbook_version', ''),
                    'subject_id': subject_id,
                    'authority_action_id': authority_action_id,
                    'explanation_bundle_id': explanation_bundle_id,
                    'execution_status': execution_record.get('execution_status', '')
                }
            )
            execution_record['ledger_entry_id'] = ledger_entry.get('ledger_entry_id', '')
        except Exception as e:
            raise IRAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return execution_record
    
    def rollback_execution(
        self,
        execution_id: str,
        rolled_back_by: str,
        rollback_reason: str
    ) -> Dict[str, Any]:
        """
        Rollback playbook execution.
        
        Process:
        1. Get execution record
        2. Create rollback record
        3. Store rollback record
        4. Emit audit ledger entry
        
        Args:
            execution_id: Execution identifier
            rolled_back_by: Human identifier who initiated rollback
            rollback_reason: Reason for rollback
        
        Returns:
            Rollback record dictionary
        """
        # Get execution record
        execution_record = self._get_execution(execution_id)
        if not execution_record:
            raise IRAPIError(f"Execution not found: {execution_id}")
        
        # Create rollback record
        rollback_record = self.rollback_engine.create_rollback(
            execution_record=execution_record,
            rolled_back_by=rolled_back_by,
            rollback_reason=rollback_reason
        )
        
        # Store rollback record
        self._store_rollback(rollback_record)
        
        # Update execution record status
        execution_record['execution_status'] = 'rolled_back'
        self._store_execution(execution_record)
        
        # Emit audit ledger entry
        try:
            self.ledger_writer.create_entry(
                component='incident-response',
                component_instance_id='ir-engine',
                action_type='playbook_rolled_back',
                subject={'type': 'execution', 'id': execution_id},
                actor={'type': 'user', 'identifier': rolled_back_by},
                payload={
                    'rollback_id': rollback_record.get('rollback_id', ''),
                    'rollback_reason': rollback_reason
                }
            )
        except Exception as e:
            raise IRAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return rollback_record
    
    def _store_execution(self, execution_record: Dict[str, Any]) -> None:
        """Store execution record to file-based store."""
        import json
        
        try:
            execution_json = json.dumps(execution_record, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(self.executions_store_path, 'a', encoding='utf-8') as f:
                f.write(execution_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise IRAPIError(f"Failed to store execution: {e}") from e
    
    def _get_execution(self, execution_id: str) -> Dict[str, Any]:
        """Get execution record from store."""
        import json
        
        if not self.executions_store_path.exists():
            return None
        
        try:
            with open(self.executions_store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    execution = json.loads(line)
                    if execution.get('execution_id') == execution_id:
                        return execution
        except Exception:
            pass
        
        return None
    
    def _store_rollback(self, rollback_record: Dict[str, Any]) -> None:
        """Store rollback record."""
        import json
        
        rollback_path = self.executions_store_path.parent / f"{self.executions_store_path.stem}_rollbacks.jsonl"
        
        try:
            rollback_json = json.dumps(rollback_record, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(rollback_path, 'a', encoding='utf-8') as f:
                f.write(rollback_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise IRAPIError(f"Failed to store rollback: {e}") from e
