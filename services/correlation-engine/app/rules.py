#!/usr/bin/env python3
"""
RansomEye v1.0 Correlation Engine - Rules Module
AUTHORITATIVE: Deterministic correlation rules for Phase 5
Python 3.10+ only - aligns with Phase 5 requirements
"""

from typing import Optional, Dict, Any, Tuple
import uuid


# Phase 5 requirement: Exactly ONE rule defined
# Deterministic: Rule is purely deterministic (no probabilistic logic, no time windows)


def apply_linux_agent_rule(event: Dict[str, Any]) -> Tuple[bool, Optional[str], float]:
    """
    Apply minimal deterministic rule for Linux Agent events.
    
    Phase 5 requirement: Exactly ONE rule
    Rule: If a Linux Agent event exists with component = linux_agent, THEN:
          Either create zero incidents, OR
          Create exactly one incident with:
          - stage = SUSPICIOUS
          - confidence = deterministic constant (0.3)
    
    Deterministic properties:
    - No time-window logic: Rule applies to single event only
    - No probabilistic logic: Deterministic constant confidence (0.3)
    - No heuristics: Explicit boolean condition (component == 'linux_agent')
    - No ML/AI: Pure boolean logic only
    
    Args:
        event: Event dictionary from raw_events table
        
    Returns:
        Tuple of (should_create_incident: bool, stage: Optional[str], confidence_score: float)
        - should_create_incident: True if incident should be created, False otherwise
        - stage: Incident stage if incident should be created, None otherwise
        - confidence_score: Deterministic confidence score (constant 0.3)
    """
    # Phase 5 requirement: Explicit rule condition
    # Deterministic: Simple boolean check (component == 'linux_agent')
    component = event.get('component')
    
    # Contract compliance: component enum value matches exactly 'linux_agent'
    # Deterministic: Exact string match, no fuzzy logic
    if component == 'linux_agent':
        # Phase 5 requirement: Create exactly one incident with:
        # - stage = SUSPICIOUS
        # - confidence = deterministic constant (0.3)
        # Deterministic: Constants only, no computation
        stage = 'SUSPICIOUS'
        confidence_score = 0.3  # Deterministic constant (Phase 5 requirement)
        return True, stage, confidence_score
    else:
        # Phase 5 requirement: Either create zero incidents, OR create exactly one
        # If component != 'linux_agent', create zero incidents
        return False, None, 0.0


def evaluate_event(event: Dict[str, Any]) -> Tuple[bool, Optional[str], float]:
    """
    Evaluate event against all correlation rules.
    
    Phase 5 requirement: At most one incident per event
    Deterministic: Rules are evaluated in deterministic order
    
    Args:
        event: Event dictionary from raw_events table
        
    Returns:
        Tuple of (should_create_incident: bool, stage: Optional[str], confidence_score: float)
    """
    # Phase 5 requirement: Exactly ONE rule for this phase
    # Deterministic: Single rule evaluation, no rule ordering dependency
    should_create, stage, confidence = apply_linux_agent_rule(event)
    
    # Phase 5 requirement: At most one incident per event
    # Deterministic: Return first rule that matches (only one rule exists)
    return should_create, stage, confidence
