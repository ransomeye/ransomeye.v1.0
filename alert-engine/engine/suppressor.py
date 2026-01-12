#!/usr/bin/env python3
"""
RansomEye Alert Engine - Suppressor
AUTHORITATIVE: Explicit, policy-driven alert suppression
"""

from typing import Dict, Any
from datetime import datetime, timezone
import uuid


class SuppressionError(Exception):
    """Base exception for suppression errors."""
    pass


class Suppressor:
    """
    Explicit, policy-driven alert suppression.
    
    Properties:
    - Explicit: All suppressions are explicit, never implicit
    - Policy-driven: Suppressions are driven by policy rules
    - Reason-coded: Suppression reasons are coded (no free-text)
    - Replayable: Suppressions can be replayed
    """
    
    def __init__(self):
        """Initialize suppressor."""
        pass
    
    def create_suppression(
        self,
        alert: Dict[str, Any],
        policy_rule_id: str,
        suppression_reason: str,
        suppressed_by: str
    ) -> Dict[str, Any]:
        """
        Create alert suppression.
        
        Args:
            alert: Alert dictionary
            policy_rule_id: Policy rule identifier that triggered suppression
            suppression_reason: Suppression reason (explicit, reason-coded)
            suppressed_by: Entity that suppressed alert
        
        Returns:
            Suppression dictionary
        """
        suppression = {
            'suppression_id': str(uuid.uuid4()),
            'alert_id': alert.get('alert_id', ''),
            'policy_rule_id': policy_rule_id,
            'suppression_reason': suppression_reason,
            'suppressed_at': datetime.now(timezone.utc).isoformat(),
            'suppressed_by': suppressed_by,
            'ledger_entry_id': ''  # Will be populated by audit ledger integration
        }
        
        return suppression
    
    def should_suppress(self, alert: Dict[str, Any], routing_decision: Dict[str, Any]) -> bool:
        """
        Determine if alert should be suppressed based on routing decision.
        
        Args:
            alert: Alert dictionary
            routing_decision: Routing decision from policy engine
        
        Returns:
            True if alert should be suppressed, False otherwise
        """
        # Check if routing action is suppress
        routing_action = routing_decision.get('routing_action', '')
        return routing_action == 'suppress'
