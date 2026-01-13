#!/usr/bin/env python3
"""
RansomEye v1.0 Threat Response Engine - Command Dispatcher
AUTHORITATIVE: Dispatches signed commands to agents for execution
Python 3.10+ only
"""

import os
import sys
import json
import uuid
import requests
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
    _common_available = True
    _logger = setup_logging('tre-dispatcher')
except ImportError:
    _common_available = False
    _logger = None


class DispatchError(Exception):
    """Exception raised when command dispatch fails."""
    pass


class CommandDispatcher:
    """
    Dispatches signed commands to agents.
    
    CRITICAL: Agents validate and execute commands but never decide.
    All commands are signed with ed25519 before dispatch.
    """
    
    def __init__(self, agent_command_endpoint: Optional[str] = None):
        """
        Initialize command dispatcher.
        
        Args:
            agent_command_endpoint: Optional agent command endpoint URL
        """
        self.agent_command_endpoint = agent_command_endpoint or os.getenv(
            'RANSOMEYE_AGENT_COMMAND_ENDPOINT',
            'http://localhost:8001/commands'
        )
    
    def dispatch_command(self, signed_command: Dict[str, Any], machine_id: str) -> Dict[str, Any]:
        """
        Dispatch signed command to agent.
        
        Args:
            signed_command: Signed command dictionary
            machine_id: Machine identifier where command should be executed
            
        Returns:
            Dispatch result dictionary
            
        Raises:
            DispatchError: If dispatch fails
        """
        # Build agent command payload (matches agent-command.schema.json)
        command_payload = signed_command['payload']
        agent_command = {
            'command_id': command_payload['command_id'],
            'command_type': command_payload['command_type'],
            'target_machine_id': command_payload['target_machine_id'],
            'incident_id': command_payload['incident_id'],
            'issued_at': command_payload['issued_at'],
            'signature': signed_command['signature'],
            'signing_key_id': signed_command['signing_key_id'],
            'action_id': signed_command.get('action_id', str(uuid.uuid4()))
        }
        
        # Dispatch to agent endpoint
        try:
            response = requests.post(
                self.agent_command_endpoint,
                json=agent_command,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if not response.ok:
                error_msg = f"Agent command endpoint returned error: {response.status_code} - {response.text}"
                if _logger:
                    _logger.error(error_msg)
                raise DispatchError(error_msg)
            
            # Parse response
            result = response.json()
            
            if _logger:
                _logger.info("Command dispatched successfully", 
                           command_id=command_payload['command_id'],
                           machine_id=machine_id)
            
            return {
                'dispatched': True,
                'command_id': command_payload['command_id'],
                'machine_id': machine_id,
                'dispatched_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                'agent_response': result
            }
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to dispatch command to agent: {e}"
            if _logger:
                _logger.error(error_msg)
            raise DispatchError(error_msg) from e
