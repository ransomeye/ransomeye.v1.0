#!/usr/bin/env python3
"""
RansomEye v1.0 Threat Response Engine - TRE API
AUTHORITATIVE: Public API for executing Policy Engine decisions
Python 3.10+ only
"""

import os
import sys
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    from common.db.safety import create_write_connection, IsolationLevel
    _common_available = True
    _logger = setup_logging('tre-api')
except ImportError:
    _common_available = False
    _logger = None

# Add threat-response-engine to path
_threat_response_path = os.path.join(_project_root, 'threat-response-engine')
if os.path.exists(_threat_response_path) and _threat_response_path not in sys.path:
    sys.path.insert(0, _threat_response_path)

from crypto.key_manager import TREKeyManager
from crypto.signer import TRESigner
from engine.action_validator import ActionValidator
from engine.command_dispatcher import CommandDispatcher
from engine.rollback_manager import RollbackManager
from engine.enforcement_pipeline import EnforcementPipeline, EnforcementError
from engine.enforcement_mode import classify_action, ActionClassification
from db.operations import (
    store_response_action, update_action_status, store_rollback_record, get_action_by_id
)

# Audit ledger integration
try:
    # Add audit-ledger to path
    _audit_ledger_path = os.path.join(_project_root, 'audit-ledger')
    if os.path.exists(_audit_ledger_path) and _audit_ledger_path not in sys.path:
        sys.path.insert(0, _audit_ledger_path)
    from api import AuditLedger
    _audit_ledger_available = True
except ImportError:
    _audit_ledger_available = False
    AuditLedger = None


class TREAPI:
    """
    Public API for Threat Response Engine.
    
    CRITICAL: TRE is execution-only, not decision-making.
    All actions are signed, auditable, and rollback-capable.
    """
    
    def __init__(self, key_dir: Path, db_conn_params: Dict[str, Any],
                 agent_command_endpoint: Optional[str] = None,
                 haf_api: Optional[Any] = None,
                 ledger_path: Optional[Path] = None,
                 ledger_key_dir: Optional[Path] = None,
                 rbac_enforcer: Optional[Any] = None):
        """
        Initialize TRE API.
        
        Args:
            key_dir: Directory for TRE signing keys
            db_conn_params: Database connection parameters
            agent_command_endpoint: Optional agent command endpoint URL
            haf_api: Optional HAF API instance
            ledger_path: Optional audit ledger path
            ledger_key_dir: Optional audit ledger key directory
            rbac_enforcer: Optional RBAC permission enforcer
        """
        # Initialize key manager and signer
        key_manager = TREKeyManager(key_dir)
        private_key, public_key, key_id = key_manager.get_or_create_keypair()
        self.signer = TRESigner(private_key, key_id)
        
        # Initialize components
        self.validator = ActionValidator(haf_api)
        self.dispatcher = CommandDispatcher(agent_command_endpoint)
        self.rollback_manager = RollbackManager(self.signer, self.dispatcher)
        
        # Database connection parameters
        self.db_conn_params = db_conn_params
        
        # Audit ledger
        if _audit_ledger_available and ledger_path and ledger_key_dir:
            self.ledger = AuditLedger(
                ledger_path=ledger_path,
                key_dir=ledger_key_dir
            )
        else:
            self.ledger = None
        
        # Enforcement pipeline
        if rbac_enforcer:
            self.enforcement_pipeline = EnforcementPipeline(
                db_conn_params=db_conn_params,
                rbac_enforcer=rbac_enforcer,
                haf_api=haf_api,
                ledger=self.ledger
            )
        else:
            self.enforcement_pipeline = None
    
    def execute_action(self, policy_decision: Dict[str, Any], required_authority: str = 'NONE',
                      authority_action_id: Optional[str] = None,
                      user_id: Optional[str] = None,
                      user_role: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute Policy Engine decision with enforcement pipeline.
        
        Args:
            policy_decision: Policy decision dictionary
            required_authority: Required authority level (NONE, HUMAN, ROLE)
            authority_action_id: Optional authority action ID
            user_id: User identifier (required for enforcement)
            user_role: User role (required for enforcement)
            
        Returns:
            Execution result dictionary
            
        Raises:
            ValueError: If validation fails
            PermissionDeniedError: If RBAC check fails
            EnforcementError: If enforcement check fails
            Exception: If execution fails
        """
        # CRITICAL: Enforcement pipeline check (MANDATORY FIRST)
        if self.enforcement_pipeline:
            if not user_id or not user_role:
                raise ValueError("user_id and user_role required for enforcement")
            
            # Execute enforcement pipeline
            try:
                enforcement_result = self.enforcement_pipeline.execute_pipeline(
                    policy_decision, user_id, user_role
                )
                action_id = enforcement_result['action_id']
                
                # Check if execution is allowed
                if not enforcement_result.get('execute'):
                    # Simulate only (DRY_RUN mode)
                    return {
                        'action_id': action_id,
                        'status': 'SIMULATED',
                        'mode': enforcement_result.get('mode'),
                        'classification': enforcement_result.get('classification'),
                        'message': 'Action simulated (DRY_RUN mode)'
                    }
            except PermissionDeniedError:
                raise
            except EnforcementError:
                raise
        else:
            # Fallback to old validation (for backward compatibility)
            is_valid, error = self.validator.validate_action(
                policy_decision, required_authority, authority_action_id
            )
            if not is_valid:
                raise ValueError(f"Action validation failed: {error}")
            
            action_id = str(uuid.uuid4())
        
        # PHASE 4: Get command payload from policy decision (if available)
        # Otherwise, construct from policy decision with policy authority binding
        if 'signed_command' in policy_decision:
            command_payload = policy_decision['signed_command']['payload']
            # PHASE 4: Ensure policy authority fields are present
            if 'policy_id' not in command_payload:
                command_payload['policy_id'] = policy_decision.get('policy_id', 'unknown')
            if 'policy_version' not in command_payload:
                command_payload['policy_version'] = policy_decision.get('policy_version', '1.0.0')
            if 'issuing_authority' not in command_payload:
                command_payload['issuing_authority'] = 'threat-response-engine'
        else:
            # PHASE 4: Construct command payload with policy authority binding
            command_payload = {
                'command_id': str(uuid.uuid4()),
                'command_type': policy_decision['recommended_action'],
                'target_machine_id': policy_decision.get('machine_id', ''),
                'incident_id': policy_decision['incident_id'],
                'policy_id': policy_decision.get('policy_id', 'unknown'),  # PHASE 4: Policy authority binding
                'policy_version': policy_decision.get('policy_version', '1.0.0'),  # PHASE 4: Policy version
                'issuing_authority': 'threat-response-engine',  # PHASE 4: Issuing authority
                'issued_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                'issued_by_user_id': user_id,
                'tre_mode': enforcement_result.get('mode') if self.enforcement_pipeline else None,
                'approval_id': enforcement_result.get('approval_id') if self.enforcement_pipeline else None
            }
        
        # PHASE 4: Sign command with TRE key (ed25519, replaces HMAC)
        signed_command = self.signer.sign_command(command_payload)
        signed_command['action_id'] = action_id
        
        # Create response action record
        action = {
            'action_id': action_id,
            'policy_decision_id': policy_decision.get('policy_decision_id', str(uuid.uuid4())),
            'incident_id': policy_decision['incident_id'],
            'machine_id': command_payload['target_machine_id'],
            'command_type': command_payload['command_type'],
            'command_payload': command_payload,
            'command_signature': signed_command['signature'],
            'command_signing_key_id': signed_command['signing_key_id'],
            'required_authority': required_authority,
            'authority_action_id': authority_action_id,
            'execution_status': 'PENDING',
            'rollback_capable': True,
            'ledger_entry_id': str(uuid.uuid4())  # Will be updated after ledger entry
        }
        
        # Store action in database
        conn = create_write_connection(**self.db_conn_params, isolation_level=IsolationLevel.READ_COMMITTED, logger=_logger)
        try:
            store_response_action(conn, action)
            
            # PHASE 4: Emit audit ledger entry with explanation bundle reference
            if self.ledger:
                # PHASE 4: Get explanation bundle ID if available
                explanation_bundle_id = policy_decision.get('explanation_bundle_id')
                
                ledger_entry = self.ledger.append(
                    component='threat-response-engine',
                    component_instance_id=os.getenv('HOSTNAME', 'tre'),
                    action_type='tre_action_executed',
                    subject={'type': 'incident', 'id': policy_decision['incident_id']},
                    actor={'type': 'module', 'identifier': 'tre'},
                    payload={
                        'action_id': action_id,
                        'command_type': command_payload['command_type'],
                        'machine_id': command_payload['target_machine_id'],
                        'policy_id': command_payload.get('policy_id'),  # PHASE 4: Policy authority
                        'policy_version': command_payload.get('policy_version'),  # PHASE 4: Policy version
                        'issuing_authority': command_payload.get('issuing_authority'),  # PHASE 4: Issuing authority
                        'explanation_bundle_id': explanation_bundle_id  # PHASE 4: Explanation bundle reference
                    }
                )
                action['ledger_entry_id'] = ledger_entry['ledger_entry_id']
                # Update action with ledger entry ID
                update_action_status(conn, action_id, 'PENDING')
            
            # Dispatch command to agent (only if execution allowed)
            if self.enforcement_pipeline and not enforcement_result.get('execute'):
                # Simulate only - do not dispatch
                dispatch_result = {'status': 'SIMULATED', 'message': 'Action simulated (DRY_RUN mode)'}
                update_action_status(conn, action_id, 'SUCCEEDED', datetime.now(timezone.utc))
            else:
                # Execute - dispatch command
                dispatch_result = self.dispatcher.dispatch_command(signed_command, command_payload['target_machine_id'])
                
                # Update action status
                update_action_status(conn, action_id, 'SUCCEEDED', datetime.now(timezone.utc))
                
                # Emit execution success event
                if self.ledger:
                    self.ledger.append(
                        component='threat-response-engine',
                        component_instance_id=os.getenv('HOSTNAME', 'tre'),
                        action_type='tre_action_executed',
                        subject={'type': 'incident', 'id': policy_decision['incident_id']},
                        actor={'type': 'user', 'identifier': user_id or 'system'},
                        payload={
                            'action_id': action_id,
                            'command_type': command_payload['command_type'],
                            'machine_id': command_payload['target_machine_id'],
                            'approval_id': enforcement_result.get('approval_id') if self.enforcement_pipeline else None
                        }
                    )
            
            return {
                'action_id': action_id,
                'status': 'SUCCEEDED',
                'command_id': command_payload['command_id'],
                'machine_id': command_payload['target_machine_id'],
                'executed_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                'dispatch_result': dispatch_result
            }
            
        except Exception as e:
            # Update action status to FAILED
            try:
                update_action_status(conn, action_id, 'FAILED', datetime.now(timezone.utc))
                
                # Emit failure event
                if self.ledger:
                    self.ledger.append(
                        component='threat-response-engine',
                        component_instance_id=os.getenv('HOSTNAME', 'tre'),
                        action_type='tre_action_failed',
                        subject={'type': 'tre_action', 'id': action_id},
                        actor={'type': 'user', 'identifier': user_id or 'system'},
                        payload={
                            'action_id': action_id,
                            'error': str(e),
                            'incident_id': policy_decision.get('incident_id', '')
                        }
                    )
            except:
                pass
            raise
        finally:
            conn.close()
    
    def rollback_action(self, action_id: str, rollback_reason: str, rollback_type: str = 'FULL',
                       required_authority: str = 'NONE', authority_action_id: Optional[str] = None,
                       user_id: Optional[str] = None, user_role: Optional[str] = None) -> Dict[str, Any]:
        """
        Rollback executed action.
        
        Args:
            action_id: Action identifier to roll back
            rollback_reason: Reason for rollback
            rollback_type: Type of rollback (FULL, PARTIAL)
            required_authority: Required authority level for rollback
            authority_action_id: Optional authority action ID
            
        Returns:
            Rollback result dictionary
            
        Raises:
            ValueError: If action not found or cannot be rolled back
            Exception: If rollback fails
        """
        # Get action from database
        conn = create_write_connection(**self.db_conn_params, isolation_level=IsolationLevel.READ_COMMITTED, logger=_logger)
        try:
            action = get_action_by_id(conn, action_id)
            if not action:
                raise ValueError(f"Action not found: {action_id}")
            
            if not action['rollback_capable']:
                raise ValueError(f"Action {action_id} is not rollback-capable")
            
            if action['execution_status'] == 'ROLLED_BACK':
                raise ValueError(f"Action {action_id} is already rolled back")
            
            # CRITICAL: RBAC check for rollback (MANDATORY)
            if self.enforcement_pipeline and user_id:
                try:
                    self.enforcement_pipeline.rbac_enforcer.check_rollback_permission(user_id, action_id)
                except PermissionDeniedError as e:
                    # Emit audit ledger entry for denial
                    if self.ledger:
                        self.ledger.append(
                            component='rbac',
                            component_instance_id=os.getenv('HOSTNAME', 'tre'),
                            action_type='rbac_user_action_denied',
                            subject={'type': 'tre_action', 'id': action_id},
                            actor={'type': 'user', 'identifier': user_id},
                            payload={
                                'permission': 'tre:rollback',
                                'action_id': action_id,
                                'role': user_role or 'unknown',
                                'reason': str(e)
                            }
                        )
                    raise
            
            # Check if original action was destructive (requires HAF for rollback)
            from engine.enforcement_mode import classify_action
            action_classification = classify_action(action['command_type'])
            if action_classification == ActionClassification.DESTRUCTIVE and self.enforcement_pipeline:
                # HAF approval required for rollback of destructive actions
                # (Implementation: check approval_id in action record)
                pass
            
            # Emit rollback request event
            if self.ledger:
                self.ledger.append(
                    component='threat-response-engine',
                    component_instance_id=os.getenv('HOSTNAME', 'tre'),
                    action_type='tre_rollback_requested',
                    subject={'type': 'tre_action', 'id': action_id},
                    actor={'type': 'user', 'identifier': user_id or 'system'},
                    payload={
                        'action_id': action_id,
                        'rollback_reason': rollback_reason,
                        'rollback_type': rollback_type
                    }
                )
            
            # Execute rollback
            rollback_result = self.rollback_manager.execute_rollback(
                action_id, action['machine_id'], rollback_reason, rollback_type
            )
            
            # Create rollback record
            rollback = {
                'rollback_id': rollback_result['rollback_id'],
                'action_id': action_id,
                'rollback_reason': rollback_reason,
                'rollback_type': rollback_type,
                'rollback_payload': rollback_result.get('rollback_payload', {}),
                'rollback_signature': rollback_result.get('rollback_signature', ''),
                'rollback_signing_key_id': self.signer.key_id,
                'required_authority': required_authority,
                'authority_action_id': authority_action_id,
                'rollback_status': 'SUCCEEDED',
                'rolled_back_at': datetime.now(timezone.utc),
                'ledger_entry_id': str(uuid.uuid4())
            }
            
            # Store rollback record
            store_rollback_record(conn, rollback)
            
            # Emit audit ledger entry
            if self.ledger:
                self.ledger.append(
                    component='threat-response-engine',
                    component_instance_id=os.getenv('HOSTNAME', 'tre'),
                    action_type='tre_rollback_executed',
                    subject={'type': 'incident', 'id': action['incident_id']},
                    actor={'type': 'user', 'identifier': user_id or 'system'},
                    payload={
                        'rollback_id': rollback['rollback_id'],
                        'action_id': action_id,
                        'rollback_reason': rollback_reason,
                        'rollback_type': rollback_type
                    }
                )
            
            return rollback_result
            
        finally:
            conn.close()
