#!/usr/bin/env python3
"""
RansomEye v1.0 GA - Correlation Engine Rules Module
AUTHORITATIVE: Correlation rules with state machine and confidence accumulation

GA-BLOCKING: Implements correlation rules with state machine logic.
Single signal → SUSPICIOUS only. Multiple signals → confidence accumulation → state transitions.
"""

from typing import Optional, Dict, Any, Tuple
import os
import uuid

# Import state machine functions
from state_machine import calculate_signal_confidence


# GA-BLOCKING: Minimum evidence thresholds for incident creation (configurable)
MIN_AGENT_EVIDENCE_COUNT = int(os.getenv('RANSOMEYE_MIN_AGENT_EVIDENCE_COUNT', '2'))
MIN_AGENT_CONFIDENCE_SCORE = float(os.getenv('RANSOMEYE_MIN_AGENT_CONFIDENCE_SCORE', '25.0'))


def apply_linux_agent_rule(event: Dict[str, Any], evidence_count: int) -> Tuple[bool, Optional[str], float, Optional[str]]:
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
        signal_confidence = calculate_signal_confidence(event, 'PROCESS_ACTIVITY')

        # GA-BLOCKING: Require minimum evidence or confidence threshold
        has_min_evidence = evidence_count >= MIN_AGENT_EVIDENCE_COUNT
        meets_confidence = signal_confidence >= MIN_AGENT_CONFIDENCE_SCORE
        if not (has_min_evidence or meets_confidence):
            return False, None, 0.0, None

        # GA-BLOCKING: Single-domain agent telemetry → SUSPICIOUS only
        stage = 'SUSPICIOUS'

        return True, stage, float(signal_confidence), 'PROCESS_ACTIVITY'
    else:
        return False, None, 0.0, None


def apply_dpi_rule(event: Dict[str, Any]) -> Tuple[bool, Optional[str], float, Optional[str]]:
    """
    GA-BLOCKING: Apply correlation rule for DPI events.

    Args:
        event: Event dictionary from raw_events table

    Returns:
        Tuple of (should_create_incident: bool, stage: Optional[str],
                 confidence_score: float, evidence_type: Optional[str])
    """
    component = event.get('component')
    if component == 'dpi':
        signal_confidence = calculate_signal_confidence(event, 'DPI_FLOW')
        stage = 'SUSPICIOUS'
        return True, stage, float(signal_confidence), 'DPI_FLOW'
    return False, None, 0.0, None


def evaluate_event(event: Dict[str, Any], evidence_count: int = 1) -> Tuple[bool, Optional[str], float, Optional[str]]:
    """
    GA-BLOCKING: Evaluate event against correlation rules.
    
    Returns:
        Tuple of (should_create_incident: bool, stage: Optional[str], confidence_score: float)
    """
    # GA-BLOCKING: Evaluate against rules
    should_create, stage, confidence, evidence_type = apply_linux_agent_rule(event, evidence_count)
    if should_create:
        return should_create, stage, confidence, evidence_type

    should_create, stage, confidence, evidence_type = apply_dpi_rule(event)
    return should_create, stage, confidence, evidence_type
