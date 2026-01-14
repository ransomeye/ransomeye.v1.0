#!/usr/bin/env python3
"""
RansomEye v1.0 GA - Correlation Engine Rules Module
AUTHORITATIVE: Correlation rules with state machine and confidence accumulation

GA-BLOCKING: Implements correlation rules with state machine logic.
Single signal → SUSPICIOUS only. Multiple signals → confidence accumulation → state transitions.
"""

from typing import Optional, Dict, Any, Tuple
import uuid

# Import state machine functions
from state_machine import (
    calculate_signal_confidence,
    determine_stage,
    CONFIDENCE_THRESHOLD_SUSPICIOUS
)


def apply_linux_agent_rule(event: Dict[str, Any]) -> Tuple[bool, Optional[str], float]:
    """
    GA-BLOCKING: Apply correlation rule for Linux Agent events.
    
    Rule: If component == 'linux_agent', then:
    - Calculate signal confidence (weighted)
    - Return should_create=True, stage=SUSPICIOUS, confidence=signal_confidence
    
    GA-BLOCKING: Single signal → SUSPICIOUS only (no direct CONFIRMED)
    
    Args:
        event: Event dictionary from raw_events table
        
    Returns:
        Tuple of (should_create_incident: bool, stage: Optional[str], confidence_score: float)
    """
    component = event.get('component')
    
    # GA-BLOCKING: Only create incidents for linux_agent events
    if component == 'linux_agent':
        # GA-BLOCKING: Calculate signal confidence (weighted)
        signal_confidence = calculate_signal_confidence(event, 'CORRELATION_PATTERN')
        
        # GA-BLOCKING: Single signal → SUSPICIOUS only
        stage = 'SUSPICIOUS'
        
        return True, stage, signal_confidence
    else:
        return False, None, 0.0


def evaluate_event(event: Dict[str, Any]) -> Tuple[bool, Optional[str], float]:
    """
    GA-BLOCKING: Evaluate event against correlation rules.
    
    Returns:
        Tuple of (should_create_incident: bool, stage: Optional[str], confidence_score: float)
    """
    # GA-BLOCKING: Evaluate against rules
    should_create, stage, confidence = apply_linux_agent_rule(event)
    
    return should_create, stage, confidence
