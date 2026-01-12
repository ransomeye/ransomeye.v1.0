#!/usr/bin/env python3
"""
RansomEye Human Authority Framework - Authority API
AUTHORITATIVE: Single API for human authority actions with audit ledger integration
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

# Import authority components
_authority_dir = Path(__file__).parent.parent
if str(_authority_dir) not in sys.path:
    sys.path.insert(0, str(_authority_dir))

_key_manager_spec = importlib.util.spec_from_file_location("human_key_manager", _authority_dir / "crypto" / "human_key_manager.py")
_key_manager_module = importlib.util.module_from_spec(_key_manager_spec)
_key_manager_spec.loader.exec_module(_key_manager_module)
HumanKeyManager = _key_manager_module.HumanKeyManager

_signer_spec = importlib.util.spec_from_file_location("authority_signer", _authority_dir / "crypto" / "signer.py")
_signer_module = importlib.util.module_from_spec(_signer_spec)
_signer_spec.loader.exec_module(_signer_module)
AuthoritySigner = _signer_module.Signer

# Add authority directory to path before loading validator
if str(_authority_dir) not in sys.path:
    sys.path.insert(0, str(_authority_dir))

_validator_spec = importlib.util.spec_from_file_location("authority_validator", _authority_dir / "engine" / "authority_validator.py")
_validator_module = importlib.util.module_from_spec(_validator_spec)
_validator_spec.loader.exec_module(_validator_module)
AuthorityValidator = _validator_module.AuthorityValidator

_override_processor_spec = importlib.util.spec_from_file_location("override_processor", _authority_dir / "engine" / "override_processor.py")
_override_processor_module = importlib.util.module_from_spec(_override_processor_spec)
_override_processor_spec.loader.exec_module(_override_processor_module)
OverrideProcessor = _override_processor_module.OverrideProcessor


class AuthorityAPIError(Exception):
    """Base exception for authority API errors."""
    pass


class AuthorityAPI:
    """
    Single API for human authority actions.
    
    All operations:
    - Validate authority (role, signature, scope, timestamp)
    - Process overrides (explicit, never implicit)
    - Sign actions (per-human keypairs)
    - Emit audit ledger entries (every action)
    """
    
    def __init__(
        self,
        keys_dir: Path,
        role_assertions_path: Path,
        actions_store_path: Path,
        ledger_path: Path,
        ledger_key_dir: Path
    ):
        """
        Initialize authority API.
        
        Args:
            keys_dir: Directory containing human keypairs
            role_assertions_path: Path to role assertions store
            actions_store_path: Path to actions store
            ledger_path: Path to audit ledger file
            ledger_key_dir: Directory containing ledger signing keys
        """
        self.key_manager = HumanKeyManager(keys_dir)
        self.validator = AuthorityValidator(keys_dir, role_assertions_path)
        self.override_processor = OverrideProcessor()
        self.actions_store_path = Path(actions_store_path)
        self.actions_store_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize audit ledger
        try:
            ledger_store = AppendOnlyStore(ledger_path, read_only=False)
            ledger_key_manager = KeyManager(ledger_key_dir)
            ledger_private_key, ledger_public_key, ledger_key_id = ledger_key_manager.get_or_create_keypair()
            ledger_signer = Signer(ledger_private_key, ledger_key_id)
            self.ledger_writer = LedgerWriter(ledger_store, ledger_signer)
        except Exception as e:
            raise AuthorityAPIError(f"Failed to initialize audit ledger: {e}") from e
    
    def create_override(
        self,
        action_type: str,
        human_identifier: str,
        role_assertion_id: str,
        scope: str,
        subject_id: str,
        subject_type: str,
        reason: str,
        supersedes_automated_decision: bool = True
    ) -> Dict[str, Any]:
        """
        Create and sign human override action.
        
        Process:
        1. Create override action
        2. Get human keypair
        3. Sign action
        4. Validate authority
        5. Store action
        6. Emit audit ledger entry
        
        Args:
            action_type: Type of override action
            human_identifier: Human identifier
            role_assertion_id: Role assertion identifier
            scope: Scope of override
            subject_id: Subject identifier
            subject_type: Subject type
            reason: Structured reason for override
            supersedes_automated_decision: Whether this supersedes automated decision
        
        Returns:
            Signed authority action dictionary
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Create override action
        action = self.override_processor.create_override(
            action_type=action_type,
            human_identifier=human_identifier,
            role_assertion_id=role_assertion_id,
            scope=scope,
            subject_id=subject_id,
            subject_type=subject_type,
            reason=reason,
            supersedes_automated_decision=supersedes_automated_decision,
            timestamp=timestamp
        )
        
        # Get human keypair
        private_key, public_key, key_id = self.key_manager.get_or_create_keypair(human_identifier)
        
        # Sign action
        signer = AuthoritySigner(private_key, key_id)
        signature = signer.sign_action(action)
        action['human_signature'] = signature
        action['human_key_id'] = key_id
        
        # Validate authority
        try:
            self.validator.validate_action(action)
        except Exception as e:
            raise AuthorityAPIError(f"Authority validation failed: {e}") from e
        
        # Store action
        self._store_action(action)
        
        # Emit audit ledger entry
        try:
            ledger_entry = self.ledger_writer.create_entry(
                component='human-authority',
                component_instance_id='authority-framework',
                action_type='human_authority_action',
                subject={'type': action.get('subject_type', 'other'), 'id': subject_id},
                actor={'type': 'human', 'identifier': human_identifier},
                payload={
                    'action_type': action_type,
                    'action_id': action.get('action_id'),
                    'role_assertion_id': role_assertion_id,
                    'scope': scope,
                    'reason': reason,
                    'supersedes_automated_decision': supersedes_automated_decision
                }
            )
            action['ledger_entry_id'] = ledger_entry.get('ledger_entry_id', '')
        except Exception as e:
            raise AuthorityAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return action
    
    def _store_action(self, action: Dict[str, Any]) -> None:
        """Store action to file-based store."""
        import json
        
        try:
            action_json = json.dumps(action, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(self.actions_store_path, 'a', encoding='utf-8') as f:
                f.write(action_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise AuthorityAPIError(f"Failed to store action: {e}") from e
    
    def verify_action(self, action: Dict[str, Any]) -> bool:
        """
        Verify human authority action.
        
        Args:
            action: Authority action dictionary
        
        Returns:
            True if action is valid
        
        Raises:
            AuthorityAPIError: If verification fails
        """
        try:
            return self.validator.validate_action(action)
        except Exception as e:
            raise AuthorityAPIError(f"Action verification failed: {e}") from e
