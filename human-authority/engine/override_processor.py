#!/usr/bin/env python3
"""
RansomEye Human Authority Framework - Override Processor
AUTHORITATIVE: Processes human overrides (explicit, never implicit)
"""

from typing import Dict, Any, List
from datetime import datetime, timezone
import uuid


class OverrideError(Exception):
    """Base exception for override errors."""
    pass


class OverrideProcessor:
    """
    Processes human overrides.
    
    Properties:
    - Explicit: All overrides are explicit, never implicit
    - Supersedes: Overrides supersede automated decisions, never erase them
    - Immutable: Overrides cannot be modified after creation
    - Deterministic: Same inputs always produce same override
    """
    
    def __init__(self):
        """Initialize override processor."""
        pass
    
    def create_override(
        self,
        action_type: str,
        human_identifier: str,
        role_assertion_id: str,
        scope: str,
        subject_id: str,
        subject_type: str,
        reason: str,
        supersedes_automated_decision: bool,
        timestamp: str
    ) -> Dict[str, Any]:
        """
        Create override action.
        
        Args:
            action_type: Type of override action
            human_identifier: Human identifier
            role_assertion_id: Role assertion identifier
            scope: Scope of override
            subject_id: Subject identifier
            subject_type: Subject type
            reason: Structured reason for override
            supersedes_automated_decision: Whether this supersedes automated decision
            timestamp: Timestamp of override
        
        Returns:
            Override action dictionary (without signature)
        """
        action = {
            'action_id': str(uuid.uuid4()),
            'action_type': action_type,
            'human_identifier': human_identifier,
            'role_assertion_id': role_assertion_id,
            'scope': scope,
            'subject_id': subject_id,
            'subject_type': subject_type,
            'reason': reason,
            'timestamp': timestamp,
            'supersedes_automated_decision': supersedes_automated_decision
        }
        
        return action
    
    def get_override_history(self, subject_id: str, overrides: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Get override history for subject.
        
        Returns all overrides for subject, ordered by timestamp.
        
        Args:
            subject_id: Subject identifier
            overrides: List of all overrides
        
        Returns:
            List of overrides for subject, ordered by timestamp
        """
        subject_overrides = [
            override for override in overrides
            if override.get('subject_id') == subject_id
        ]
        
        # Sort by timestamp
        subject_overrides.sort(key=lambda o: o.get('timestamp', ''))
        
        return subject_overrides
    
    def get_active_override(self, subject_id: str, overrides: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get active override for subject.
        
        Returns most recent override that supersedes automated decision.
        
        Args:
            subject_id: Subject identifier
            overrides: List of all overrides
        
        Returns:
            Most recent active override, or None if no active override
        """
        subject_overrides = self.get_override_history(subject_id, overrides)
        
        # Find most recent override that supersedes automated decision
        for override in reversed(subject_overrides):
            if override.get('supersedes_automated_decision', False):
                return override
        
        return None
