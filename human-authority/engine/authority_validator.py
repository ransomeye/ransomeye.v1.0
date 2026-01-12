#!/usr/bin/env python3
"""
RansomEye Human Authority Framework - Authority Validator
AUTHORITATIVE: Validates human authority before accepting actions
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
import json

from crypto.human_key_manager import HumanKeyManager
from crypto.verifier import Verifier


class ValidationError(Exception):
    """Base exception for validation errors."""
    pass


class InsufficientRoleError(ValidationError):
    """Raised when role is insufficient for action."""
    pass


class InvalidSignatureError(ValidationError):
    """Raised when signature is invalid."""
    pass


class ScopeMismatchError(ValidationError):
    """Raised when scope does not match."""
    pass


class InvalidTimestampError(ValidationError):
    """Raised when timestamp is invalid."""
    pass


class AuthorityValidator:
    """
    Validates human authority before accepting actions.
    
    Properties:
    - Deterministic: Same inputs always produce same validation result
    - Complete: Validates role, signature, scope, and timestamp
    - No implicit trust: All authority must be explicit
    """
    
    # Role requirements for each action type
    ROLE_REQUIREMENTS = {
        'POLICY_OVERRIDE': ['policy_admin', 'security_manager', 'executive'],
        'INCIDENT_ESCALATION': ['analyst', 'senior_analyst', 'incident_responder', 'security_manager', 'executive'],
        'INCIDENT_SUPPRESSION': ['senior_analyst', 'incident_responder', 'security_manager', 'executive'],
        'PLAYBOOK_APPROVAL': ['incident_responder', 'security_manager', 'executive'],
        'PLAYBOOK_ABORT': ['incident_responder', 'security_manager', 'executive'],
        'RISK_ACCEPTANCE': ['security_manager', 'executive'],
        'FALSE_POSITIVE_DECLARATION': ['analyst', 'senior_analyst', 'incident_responder']
    }
    
    def __init__(self, keys_dir: Path, role_assertions_path: Path):
        """
        Initialize authority validator.
        
        Args:
            keys_dir: Directory containing human keypairs
            role_assertions_path: Path to role assertions store
        """
        self.key_manager = HumanKeyManager(keys_dir)
        self.role_assertions_path = Path(role_assertions_path)
        self.role_assertions_path.parent.mkdir(parents=True, exist_ok=True)
    
    def validate_action(self, action: Dict[str, Any]) -> bool:
        """
        Validate human authority action.
        
        Validates:
        1. Role is sufficient for action type
        2. Signature is valid
        3. Scope matches
        4. Timestamp is valid
        5. Role assertion is valid
        
        Args:
            action: Authority action dictionary
        
        Returns:
            True if action is valid
        
        Raises:
            ValidationError: If validation fails
        """
        # Load role assertion
        role_assertion = self._load_role_assertion(action.get('role_assertion_id', ''))
        if not role_assertion:
            raise ValidationError(f"Role assertion not found: {action.get('role_assertion_id', '')}")
        
        # Validate role assertion
        self._validate_role_assertion(role_assertion)
        
        # Validate role is sufficient
        self._validate_role_sufficient(action, role_assertion)
        
        # Validate signature
        self._validate_signature(action)
        
        # Validate scope
        self._validate_scope(action, role_assertion)
        
        # Validate timestamp
        self._validate_timestamp(action)
        
        return True
    
    def _load_role_assertion(self, assertion_id: str) -> Optional[Dict[str, Any]]:
        """Load role assertion from store."""
        if not self.role_assertions_path.exists():
            return None
        
        try:
            with open(self.role_assertions_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    assertion = json.loads(line)
                    if assertion.get('assertion_id') == assertion_id:
                        return assertion
        except Exception:
            pass
        
        return None
    
    def _validate_role_assertion(self, assertion: Dict[str, Any]) -> None:
        """Validate role assertion signature and validity."""
        human_identifier = assertion.get('human_identifier', '')
        
        # Get public key
        try:
            public_key, key_id = self.key_manager.get_public_key(human_identifier)
        except Exception as e:
            raise ValidationError(f"Failed to get public key for {human_identifier}: {e}") from e
        
        # Verify assertion signature
        verifier = Verifier(public_key)
        try:
            verifier.verify_role_assertion(assertion)
        except Exception as e:
            raise ValidationError(f"Role assertion signature invalid: {e}") from e
        
        # Check assertion validity period
        now = datetime.now(timezone.utc)
        valid_from = datetime.fromisoformat(assertion.get('valid_from', '').replace('Z', '+00:00'))
        valid_until_str = assertion.get('valid_until')
        
        if now < valid_from:
            raise ValidationError(f"Role assertion not yet valid: valid_from={valid_from}")
        
        if valid_until_str:
            valid_until = datetime.fromisoformat(valid_until_str.replace('Z', '+00:00'))
            if now > valid_until:
                raise ValidationError(f"Role assertion expired: valid_until={valid_until}")
    
    def _validate_role_sufficient(self, action: Dict[str, Any], role_assertion: Dict[str, Any]) -> None:
        """Validate role is sufficient for action type."""
        action_type = action.get('action_type', '')
        role = role_assertion.get('role', '')
        
        required_roles = self.ROLE_REQUIREMENTS.get(action_type, [])
        if role not in required_roles:
            raise InsufficientRoleError(
                f"Role '{role}' is insufficient for action '{action_type}'. Required roles: {required_roles}"
            )
    
    def _validate_signature(self, action: Dict[str, Any]) -> None:
        """Validate action signature."""
        human_identifier = action.get('human_identifier', '')
        human_key_id = action.get('human_key_id', '')
        
        # Get public key
        try:
            public_key, key_id = self.key_manager.get_public_key(human_identifier)
        except Exception as e:
            raise ValidationError(f"Failed to get public key for {human_identifier}: {e}") from e
        
        # Verify key ID matches
        if key_id != human_key_id:
            raise InvalidSignatureError(f"Key ID mismatch: expected={key_id}, got={human_key_id}")
        
        # Verify signature
        verifier = Verifier(public_key)
        try:
            verifier.verify_action(action)
        except Exception as e:
            raise InvalidSignatureError(f"Action signature invalid: {e}") from e
    
    def _validate_scope(self, action: Dict[str, Any], role_assertion: Dict[str, Any]) -> None:
        """Validate scope matches."""
        action_scope = action.get('scope', '')
        assertion_scope = role_assertion.get('scope', '')
        
        # Scope must match, or assertion scope must be 'global'
        if assertion_scope != 'global' and action_scope != assertion_scope:
            raise ScopeMismatchError(
                f"Scope mismatch: action_scope={action_scope}, assertion_scope={assertion_scope}"
            )
    
    def _validate_timestamp(self, action: Dict[str, Any]) -> None:
        """Validate timestamp is valid."""
        timestamp_str = action.get('timestamp', '')
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except Exception as e:
            raise InvalidTimestampError(f"Invalid timestamp format: {e}") from e
        
        # Check timestamp is not in future (with small tolerance)
        now = datetime.now(timezone.utc)
        if timestamp > now:
            raise InvalidTimestampError(f"Timestamp is in future: {timestamp}")
