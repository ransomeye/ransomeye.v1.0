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
        # PHASE 4: Build agent command payload (matches agent-command.schema.json)
        command_payload = signed_command['payload']
        
        # PHASE 4: Compute expires_at (default: 1 hour from issued_at)
        from dateutil import parser
        issued_at_dt = parser.isoparse(command_payload['issued_at'])
        expires_at_dt = issued_at_dt + timedelta(hours=1)
        expires_at = expires_at_dt.isoformat().replace('+00:00', 'Z')
        
        # PHASE 4: Generate rollback_token (SHA256 hash of command_id + action_type)
        import hashlib
        rollback_data = f"{command_payload['command_id']}:{command_payload.get('command_type', command_payload.get('action_type', ''))}"
        rollback_token = hashlib.sha256(rollback_data.encode('utf-8')).hexdigest()
        
        agent_command = {
            'command_id': command_payload['command_id'],
            'action_type': command_payload.get('command_type', command_payload.get('action_type')),  # Support both field names
            'target': {'machine_id': command_payload['target_machine_id']},  # PHASE 4: Target object
            'incident_id': command_payload['incident_id'],
            'tre_mode': command_payload.get('tre_mode', 'FULL_ENFORCE'),
            'issued_by_user_id': command_payload.get('issued_by_user_id', ''),
            'issued_by_role': command_payload.get('issued_by_role', 'SECURITY_ANALYST'),
            'issued_at': command_payload['issued_at'],
            'expires_at': command_payload.get('expires_at', expires_at),  # PHASE 4: Expiry timestamp
            'rollback_token': command_payload.get('rollback_token', rollback_token),  # PHASE 4: Rollback token
            'signature': signed_command['signature'],
            'signing_key_id': signed_command['signing_key_id'],
            'signing_algorithm': signed_command.get('signing_algorithm', 'ed25519'),  # PHASE 4: Signing algorithm
            'signed_at': signed_command.get('signed_at', ''),  # PHASE 4: Signed timestamp
            'policy_id': command_payload.get('policy_id', ''),  # PHASE 4: Policy authority binding
            'policy_version': command_payload.get('policy_version', ''),  # PHASE 4: Policy version
            'issuing_authority': command_payload.get('issuing_authority', 'threat-response-engine')  # PHASE 4: Issuing authority
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
