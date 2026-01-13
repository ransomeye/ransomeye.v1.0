#!/usr/bin/env python3
"""
RansomEye v1.0 Linux Agent - Main Entry Point
AUTHORITATIVE: Agent command receiver and executor
Python 3.10+ only
"""

import os
import sys
import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timezone

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    _common_available = True
    _logger = setup_logging('linux-agent')
except ImportError:
    _common_available = False
    _logger = None

from command_gate import CommandGate, CommandRejectionError
from execution.process_blocker import ProcessBlocker, ProcessBlockError
from execution.rollback_engine import RollbackEngine, RollbackError


class LinuxAgent:
    """
    Linux Agent - Command receiver and executor.
    
    CRITICAL: Agents NEVER trust the network, NEVER trust the UI.
    Agents ONLY trust signed commands. FAIL CLOSED.
    """
    
    def __init__(
        self,
        tre_public_key: bytes,
        tre_key_id: str,
        agent_id: str,
        audit_log_path: Path,
        rollback_store_path: Path
    ):
        """
        Initialize Linux agent.
        
        Args:
            tre_public_key: TRE public key for signature verification
            tre_key_id: TRE key ID (SHA256 hash)
            agent_id: Agent identifier
            audit_log_path: Path to local audit log
            rollback_store_path: Path to rollback artifact store
        """
        self.agent_id = agent_id
        self.command_gate = CommandGate(
            tre_public_key=tre_public_key,
            tre_key_id=tre_key_id,
            agent_id=agent_id,
            audit_log_path=audit_log_path
        )
        self.process_blocker = ProcessBlocker(rollback_store_path)
        self.rollback_engine = RollbackEngine(rollback_store_path)
    
    def receive_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Receive and execute command.
        
        Args:
            command: Command dictionary
        
        Returns:
            Execution result dictionary
        
        Raises:
            CommandRejectionError: If command is rejected
        """
        # Step 1: Command acceptance gate
        validated_command = self.command_gate.receive_command(command)
        
        # Step 2: Execute action based on action_type
        action_type = validated_command.get('action_type')
        
        try:
            if action_type == 'BLOCK_PROCESS':
                result = self.process_blocker.execute(validated_command)
            else:
                raise CommandRejectionError(f"Unsupported action type: {action_type}")
            
            # Step 3: Log execution
            self.command_gate._log_audit_event(
                'command_executed',
                validated_command['command_id'],
                'SUCCESS'
            )
            
            # Step 4: Emit execution receipt
            return {
                'status': 'SUCCEEDED',
                'command_id': validated_command['command_id'],
                'action_type': action_type,
                'rollback_token': result.get('rollback_token'),
                'executed_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                'agent_id': self.agent_id
            }
            
        except ProcessBlockError as e:
            self.command_gate._log_audit_event(
                'command_failed',
                validated_command['command_id'],
                'FAILED',
                str(e)
            )
            raise CommandRejectionError(f"Command execution failed: {e}") from e
        except Exception as e:
            self.command_gate._log_audit_event(
                'command_failed',
                validated_command['command_id'],
                'FAILED',
                str(e)
            )
            raise CommandRejectionError(f"Unexpected error: {e}") from e
    
    def execute_rollback(self, rollback_command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute rollback operation.
        
        Args:
            rollback_command: Signed rollback command dictionary
        
        Returns:
            Rollback result dictionary
        
        Raises:
            RollbackError: If rollback fails
        """
        try:
            result = self.rollback_engine.execute_rollback(rollback_command)
            
            # Log rollback
            self.command_gate._log_audit_event(
                'rollback_executed',
                rollback_command.get('command_id', 'unknown'),
                'SUCCESS'
            )
            
            return result
            
        except RollbackError as e:
            self.command_gate._log_audit_event(
                'rollback_failed',
                rollback_command.get('command_id', 'unknown'),
                'FAILED',
                str(e)
            )
            raise
