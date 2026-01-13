#!/usr/bin/env python3
"""
RansomEye v1.0 Threat Response Engine - Rollback Manager
AUTHORITATIVE: Manages rollback of executed actions
Python 3.10+ only
"""

import os
import sys
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    _common_available = True
    _logger = setup_logging('tre-rollback')
except ImportError:
    _common_available = False
    _logger = None

# Add threat-response-engine to path
_threat_response_path = os.path.join(_project_root, 'threat-response-engine')
if os.path.exists(_threat_response_path) and _threat_response_path not in sys.path:
    sys.path.insert(0, _threat_response_path)

from crypto.signer import TRESigner
from engine.command_dispatcher import CommandDispatcher


class RollbackError(Exception):
    """Exception raised when rollback fails."""
    pass


class RollbackManager:
    """
    Manages rollback of executed actions.
    
    CRITICAL: Rollback is mandatory and first-class.
    All actions must be rollback-capable.
    """
    
    def __init__(self, signer: TRESigner, dispatcher: CommandDispatcher):
        """
        Initialize rollback manager.
        
        Args:
            signer: TRE signer for signing rollback commands
            dispatcher: Command dispatcher for sending rollback commands
        """
        self.signer = signer
        self.dispatcher = dispatcher
    
    def create_rollback_command(self, action_id: str, rollback_reason: str, 
                               rollback_type: str = 'FULL') -> Dict[str, Any]:
        """
        Create rollback command payload.
        
        Args:
            action_id: Action identifier to roll back
            rollback_reason: Reason for rollback (FALSE_POSITIVE, HUMAN_OVERRIDE, etc.)
            rollback_type: Type of rollback (FULL, PARTIAL)
            
        Returns:
            Rollback command payload dictionary
        """
        rollback_id = str(uuid.uuid4())
        rollback_command_id = str(uuid.uuid4())
        
        rollback_payload = {
            'rollback_command_id': rollback_command_id,
            'action_id': action_id,
            'rollback_type': rollback_type,
            'rollback_reason': rollback_reason,
            'issued_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }
        
        # Sign rollback command
        signed_rollback = self.signer.sign_command(rollback_payload)
        signed_rollback['rollback_id'] = rollback_id
        
        return signed_rollback
    
    def execute_rollback(self, action_id: str, machine_id: str, rollback_reason: str,
                        rollback_type: str = 'FULL') -> Dict[str, Any]:
        """
        Execute rollback of action.
        
        Args:
            action_id: Action identifier to roll back
            machine_id: Machine identifier where rollback should be executed
            rollback_reason: Reason for rollback
            rollback_type: Type of rollback (FULL, PARTIAL)
            
        Returns:
            Rollback result dictionary
            
        Raises:
            RollbackError: If rollback fails
        """
        # Create rollback command
        rollback_command = self.create_rollback_command(action_id, rollback_reason, rollback_type)
        
        # Dispatch rollback command
        try:
            dispatch_result = self.dispatcher.dispatch_command(rollback_command, machine_id)
            
            if _logger:
                _logger.info("Rollback executed successfully",
                           action_id=action_id,
                           rollback_id=rollback_command['rollback_id'],
                           machine_id=machine_id)
            
            return {
                'rollback_id': rollback_command['rollback_id'],
                'action_id': action_id,
                'machine_id': machine_id,
                'rollback_type': rollback_type,
                'rollback_reason': rollback_reason,
                'rolled_back_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                'status': 'SUCCEEDED',
                'dispatch_result': dispatch_result
            }
            
        except Exception as e:
            error_msg = f"Failed to execute rollback: {e}"
            if _logger:
                _logger.error(error_msg)
            raise RollbackError(error_msg) from e
