#!/usr/bin/env python3
"""
RansomEye Alert Engine - Escalator
AUTHORITATIVE: Deterministic alert escalation
"""

from typing import Dict, Any
from datetime import datetime, timezone
import uuid


class EscalationError(Exception):
    """Base exception for escalation errors."""
    pass


class Escalator:
    """
    Deterministic alert escalation.
    
    Properties:
    - Deterministic: Same inputs always produce same escalation decision
    - Policy-driven: Escalation requires policy match
    - Explanation-required: Escalation requires explanation reference
    - No auto-execution: Escalation NEVER auto-executes IR
    """
    
    def __init__(self):
        """Initialize escalator."""
        pass
    
    def create_escalation(
        self,
        alert: Dict[str, Any],
        policy_rule_id: str,
        explanation_bundle_id: str,
        authority_required: str,
        escalated_by: str
    ) -> Dict[str, Any]:
        """
        Create alert escalation.
        
        Args:
            alert: Alert dictionary
            policy_rule_id: Policy rule identifier that triggered escalation
            explanation_bundle_id: Explanation bundle identifier (SEE) - mandatory
            authority_required: Required authority level
            escalated_by: Entity that escalated alert
        
        Returns:
            Escalation dictionary
        """
        escalation = {
            'escalation_id': str(uuid.uuid4()),
            'alert_id': alert.get('alert_id', ''),
            'policy_rule_id': policy_rule_id,
            'explanation_bundle_id': explanation_bundle_id,
            'authority_required': authority_required,
            'escalated_at': datetime.now(timezone.utc).isoformat(),
            'escalated_by': escalated_by,
            'ledger_entry_id': ''  # Will be populated by audit ledger integration
        }
        
        return escalation
    
    def should_escalate(self, alert: Dict[str, Any], routing_decision: Dict[str, Any]) -> bool:
        """
        Determine if alert should be escalated based on routing decision.
        
        Args:
            alert: Alert dictionary
            routing_decision: Routing decision from policy engine
        
        Returns:
            True if alert should be escalated, False otherwise
        """
        # Check if routing action is escalate
        routing_action = routing_decision.get('routing_action', '')
        return routing_action == 'escalate'
