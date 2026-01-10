#!/usr/bin/env python3
"""
RansomEye v1.0 Policy Engine - Rules Module
AUTHORITATIVE: Deterministic policy rules for Phase 7
Python 3.10+ only - aligns with Phase 7 requirements
"""

from typing import Optional, Dict, Any, Tuple


# Phase 7 requirement: Exactly ONE policy rule defined
# Deterministic: Rule is purely deterministic (no probabilistic logic, no time windows)


# Policy action enumeration (command types)
class PolicyAction:
    ISOLATE_HOST = "ISOLATE_HOST"
    QUARANTINE_HOST = "QUARANTINE_HOST"
    NO_ACTION = "NO_ACTION"


def evaluate_suspicious_incident_rule(incident: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Apply minimal deterministic rule for suspicious incidents.
    
    Phase 7 requirement: Exactly ONE rule
    Rule: IF incident.stage == SUSPICIOUS, THEN recommend action: ISOLATE_HOST
    
    Deterministic properties:
    - No time-window logic: Rule applies to single incident only
    - No probabilistic logic: Deterministic boolean condition
    - No heuristics: Explicit boolean condition (current_stage == 'SUSPICIOUS')
    - Recommendation only: Returns action recommendation, does not execute
    
    Args:
        incident: Incident dictionary from incidents table
        
    Returns:
        Tuple of (should_recommend_action: bool, action: Optional[str])
        - should_recommend_action: True if action should be recommended, False otherwise
        - action: Action recommendation (e.g., 'ISOLATE_HOST') or None
    """
    # Phase 7 requirement: Explicit rule condition
    # Deterministic: Simple boolean check (current_stage == 'SUSPICIOUS')
    current_stage = incident.get('current_stage')
    
    # Contract compliance: current_stage enum matches exactly 'SUSPICIOUS'
    # Deterministic: Exact string match, no fuzzy logic
    if current_stage == 'SUSPICIOUS':
        # Phase 7 requirement: Recommend action: ISOLATE_HOST
        # Deterministic: Constant action recommendation (no computation)
        action = PolicyAction.ISOLATE_HOST
        return True, action
    else:
        # Phase 7 requirement: Recommendation only (no action if rule does not match)
        return False, None


def evaluate_policy(incident: Dict[str, Any]) -> Tuple[bool, Optional[str], str]:
    """
    Evaluate incident against all policy rules.
    
    Phase 7 requirement: Recommendation only, no execution
    Deterministic: Rules are evaluated in deterministic order
    
    Args:
        incident: Incident dictionary from incidents table
        
    Returns:
        Tuple of (should_recommend_action: bool, action: Optional[str], reason: str)
    """
    # Phase 7 requirement: Exactly ONE rule for this phase
    # Deterministic: Single rule evaluation, no rule ordering dependency
    should_recommend, action = evaluate_suspicious_incident_rule(incident)
    
    # Phase 7 requirement: Generate reason for policy decision (for audit trail)
    if should_recommend:
        reason = f"Policy rule matched: incident.stage == 'SUSPICIOUS', recommended action: {action}"
    else:
        reason = "No policy rule matched, no action recommended"
    
    return should_recommend, action, reason
