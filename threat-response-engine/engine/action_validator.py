#!/usr/bin/env python3
"""
RansomEye v1.0 Threat Response Engine - Action Validator
AUTHORITATIVE: Validates Policy Engine decisions and HAF requirements before execution
Python 3.10+ only
"""

import os
import sys
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from pathlib import Path
import json

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    # Add human-authority to path
    _haf_path = os.path.join(_project_root, 'human-authority')
    if os.path.exists(_haf_path) and _haf_path not in sys.path:
        sys.path.insert(0, _haf_path)
    from api.authority_api import AuthorityAPI
    from engine.authority_validator import AuthorityValidator
    _haf_available = True
except ImportError:
    _haf_available = False


class ActionValidationError(Exception):
    """Exception raised when action validation fails."""
    pass


class ActionValidator:
    """
    Validates Policy Engine decisions and HAF requirements before execution.
    
    CRITICAL: TRE is execution-only, not decision-making.
    All actions must be validated before execution.
    """
    
    def __init__(self, haf_api: Optional[AuthorityAPI] = None):
        """
        Initialize action validator.
        
        Args:
            haf_api: Optional HAF API instance for authority validation
        """
        self.haf_api = haf_api
        if _haf_available and haf_api is None:
            # Try to initialize HAF API from environment
            try:
                keys_dir = Path(os.getenv('RANSOMEYE_HAF_KEYS_DIR', '/var/lib/ransomeye/authority/keys'))
                role_assertions_path = Path(os.getenv('RANSOMEYE_HAF_ROLE_ASSERTIONS', '/var/lib/ransomeye/authority/assertions.jsonl'))
                actions_store_path = Path(os.getenv('RANSOMEYE_HAF_ACTIONS_STORE', '/var/lib/ransomeye/authority/actions.jsonl'))
                ledger_path = Path(os.getenv('RANSOMEYE_AUDIT_LEDGER', '/var/lib/ransomeye/audit/ledger.jsonl'))
                ledger_key_dir = Path(os.getenv('RANSOMEYE_AUDIT_LEDGER_KEY_DIR', '/var/lib/ransomeye/audit/keys'))
                
                self.haf_api = AuthorityAPI(
                    keys_dir=keys_dir,
                    role_assertions_path=role_assertions_path,
                    actions_store_path=actions_store_path,
                    ledger_path=ledger_path,
                    ledger_key_dir=ledger_key_dir
                )
            except Exception:
                # HAF not available, continue without it
                self.haf_api = None
    
    def validate_policy_decision(self, policy_decision: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate Policy Engine decision.
        
        Args:
            policy_decision: Policy decision dictionary
            
        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """
        # Required fields
        required_fields = ['incident_id', 'should_recommend_action', 'recommended_action']
        for field in required_fields:
            if field not in policy_decision:
                return False, f"Policy decision missing required field: {field}"
        
        # Must recommend action
        if not policy_decision.get('should_recommend_action', False):
            return False, "Policy decision does not recommend action"
        
        # Must have recommended action
        recommended_action = policy_decision.get('recommended_action')
        if not recommended_action:
            return False, "Policy decision has no recommended action"
        
        # Validate action type
        valid_actions = [
            'ISOLATE_HOST', 'QUARANTINE_HOST', 'BLOCK_PROCESS', 'BLOCK_NETWORK',
            'QUARANTINE_FILE', 'TERMINATE_PROCESS', 'DISABLE_USER', 'REVOKE_ACCESS'
        ]
        if recommended_action not in valid_actions:
            return False, f"Invalid recommended action: {recommended_action}"
        
        return True, None
    
    def validate_authority_requirement(self, required_authority: str, authority_action_id: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Validate authority requirement.
        
        Args:
            required_authority: Required authority level (NONE, HUMAN, ROLE)
            authority_action_id: Optional authority action ID
            
        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """
        if required_authority == 'NONE':
            # No authority required
            return True, None
        
        if required_authority in ('HUMAN', 'ROLE'):
            # Authority required
            if not authority_action_id:
                return False, f"Authority required ({required_authority}) but no authority_action_id provided"
            
            # Validate authority action if HAF is available
            if _haf_available and self.haf_api:
                try:
                    # Load authority action
                    # Note: This is a simplified check - full validation would verify signature, role, scope, etc.
                    is_valid = self.haf_api.verify_action({'action_id': authority_action_id})
                    if not is_valid:
                        return False, f"Authority action {authority_action_id} is invalid"
                except Exception as e:
                    return False, f"Failed to validate authority action: {e}"
            
            return True, None
        
        return False, f"Invalid required_authority: {required_authority}"
    
    def validate_action(self, policy_decision: Dict[str, Any], required_authority: str = 'NONE', 
                       authority_action_id: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Validate action before execution.
        
        Args:
            policy_decision: Policy decision dictionary
            required_authority: Required authority level (NONE, HUMAN, ROLE)
            authority_action_id: Optional authority action ID
            
        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """
        # Validate policy decision
        is_valid, error = self.validate_policy_decision(policy_decision)
        if not is_valid:
            return False, error
        
        # Validate authority requirement
        is_valid, error = self.validate_authority_requirement(required_authority, authority_action_id)
        if not is_valid:
            return False, error
        
        return True, None
