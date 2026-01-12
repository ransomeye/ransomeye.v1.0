#!/usr/bin/env python3
"""
RansomEye AI Model Registry - Lifecycle Management
AUTHORITATIVE: Explicit lifecycle state transitions for models
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone


class LifecycleError(Exception):
    """Base exception for lifecycle errors."""
    pass


class InvalidTransitionError(LifecycleError):
    """Raised when lifecycle transition is invalid."""
    pass


class LifecycleManager:
    """
    Manages explicit lifecycle state transitions for models.
    
    Supported states:
    - REGISTERED: Model is registered but not active
    - PROMOTED: Model is active and can be used
    - DEPRECATED: Model is deprecated but still available
    - REVOKED: Model is revoked and must not be used
    
    Rules:
    - No implicit promotion
    - No silent revocation
    - Every transition must be explicit and auditable
    """
    
    # Valid state transitions
    VALID_TRANSITIONS = {
        'REGISTERED': ['PROMOTED', 'REVOKED'],
        'PROMOTED': ['DEPRECATED', 'REVOKED'],
        'DEPRECATED': ['REVOKED'],
        'REVOKED': []  # REVOKED is terminal
    }
    
    @staticmethod
    def validate_transition(current_state: str, new_state: str) -> bool:
        """
        Validate lifecycle state transition.
        
        Args:
            current_state: Current lifecycle state
            new_state: Desired new lifecycle state
        
        Returns:
            True if transition is valid
        
        Raises:
            InvalidTransitionError: If transition is invalid
        """
        if current_state not in LifecycleManager.VALID_TRANSITIONS:
            raise InvalidTransitionError(f"Invalid current state: {current_state}")
        
        if new_state not in LifecycleManager.VALID_TRANSITIONS:
            raise InvalidTransitionError(f"Invalid new state: {new_state}")
        
        if new_state not in LifecycleManager.VALID_TRANSITIONS[current_state]:
            raise InvalidTransitionError(
                f"Invalid transition from {current_state} to {new_state}. "
                f"Valid transitions: {LifecycleManager.VALID_TRANSITIONS[current_state]}"
            )
        
        return True
    
    @staticmethod
    def create_transition_record(
        model_id: str,
        model_version: str,
        current_state: str,
        new_state: str,
        transitioned_by: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create lifecycle transition record for audit ledger.
        
        Args:
            model_id: Model identifier
            model_version: Model version
            current_state: Current lifecycle state
            new_state: New lifecycle state
            transitioned_by: Entity that performed transition
            reason: Optional reason for transition
        
        Returns:
            Transition record dictionary
        """
        # Validate transition
        LifecycleManager.validate_transition(current_state, new_state)
        
        # Determine action type based on transition
        action_type_map = {
            'PROMOTED': 'ai_model_promote',
            'DEPRECATED': 'ai_model_deprecate',
            'REVOKED': 'ai_model_revoke'
        }
        action_type = action_type_map.get(new_state, 'ai_model_lifecycle_change')
        
        return {
            'model_id': model_id,
            'model_version': model_version,
            'current_state': current_state,
            'new_state': new_state,
            'transitioned_by': transitioned_by,
            'reason': reason,
            'action_type': action_type,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    @staticmethod
    def get_valid_transitions(current_state: str) -> list:
        """
        Get list of valid transitions from current state.
        
        Args:
            current_state: Current lifecycle state
        
        Returns:
            List of valid transition states
        """
        return LifecycleManager.VALID_TRANSITIONS.get(current_state, [])
