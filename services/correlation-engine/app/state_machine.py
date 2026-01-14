#!/usr/bin/env python3
"""
RansomEye v1.0 GA - Correlation State Machine
AUTHORITATIVE: State machine and confidence accumulation for correlation engine

GA-BLOCKING: Implements incident state machine (SUSPICIOUS → PROBABLE → CONFIRMED)
with confidence accumulation, deduplication, and contradiction handling.
"""

import os
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal

# PHASE 3: State machine states (ordered progression)
# CLEAN is implicit (no incident exists), incidents start at SUSPICIOUS
INCIDENT_STAGES = ['CLEAN', 'SUSPICIOUS', 'PROBABLE', 'CONFIRMED']

# GA-BLOCKING: Confidence thresholds (configurable via environment)
CONFIDENCE_THRESHOLD_SUSPICIOUS = float(os.getenv('RANSOMEYE_CONFIDENCE_THRESHOLD_SUSPICIOUS', '0.0'))
CONFIDENCE_THRESHOLD_PROBABLE = float(os.getenv('RANSOMEYE_CONFIDENCE_THRESHOLD_PROBABLE', '30.0'))
CONFIDENCE_THRESHOLD_CONFIRMED = float(os.getenv('RANSOMEYE_CONFIDENCE_THRESHOLD_CONFIRMED', '70.0'))

# GA-BLOCKING: Signal weights (deterministic, configurable)
SIGNAL_WEIGHTS = {
    'CORRELATION_PATTERN': float(os.getenv('RANSOMEYE_SIGNAL_WEIGHT_CORRELATION', '10.0')),
    'PROCESS_ACTIVITY': float(os.getenv('RANSOMEYE_SIGNAL_WEIGHT_PROCESS', '15.0')),
    'FILE_ACTIVITY': float(os.getenv('RANSOMEYE_SIGNAL_WEIGHT_FILE', '15.0')),
    'NETWORK_INTENT': float(os.getenv('RANSOMEYE_SIGNAL_WEIGHT_NETWORK', '12.0')),
    'DPI_FLOW': float(os.getenv('RANSOMEYE_SIGNAL_WEIGHT_DPI', '20.0')),
    'DNS_QUERY': float(os.getenv('RANSOMEYE_SIGNAL_WEIGHT_DNS', '8.0')),
    'DECEPTION': float(os.getenv('RANSOMEYE_SIGNAL_WEIGHT_DECEPTION', '25.0')),
    'AI_SIGNAL': float(os.getenv('RANSOMEYE_SIGNAL_WEIGHT_AI', '18.0')),
}

# GA-BLOCKING: Contradiction decay factor (confidence reduction on contradiction)
CONTRADICTION_DECAY_FACTOR = float(os.getenv('RANSOMEYE_CONTRADICTION_DECAY', '0.1'))  # 10% decay

# GA-BLOCKING: Deduplication time window (seconds)
DEDUPLICATION_TIME_WINDOW = int(os.getenv('RANSOMEYE_DEDUP_TIME_WINDOW', '3600'))  # 1 hour


def calculate_signal_confidence(event: Dict[str, Any], evidence_type: str = 'CORRELATION_PATTERN') -> float:
    """
    GA-BLOCKING: Calculate confidence contribution from a single signal.
    
    Args:
        event: Event dictionary
        evidence_type: Type of evidence (determines weight)
        
    Returns:
        Confidence score contribution (0.0 to 100.0)
    """
    base_weight = SIGNAL_WEIGHTS.get(evidence_type, 10.0)
    
    # GA-BLOCKING: Confidence is bounded (0.0 to 100.0)
    confidence = min(max(base_weight, 0.0), 100.0)
    
    return confidence


def accumulate_confidence(current_confidence: float, new_signal_confidence: float) -> float:
    """
    GA-BLOCKING: Accumulate confidence from new signal.
    
    Formula: confidence = min(current + new, 100.0)
    Confidence is incremental and bounded.
    
    Args:
        current_confidence: Current accumulated confidence
        new_signal_confidence: New signal confidence contribution
        
    Returns:
        Updated confidence score (0.0 to 100.0)
    """
    # GA-BLOCKING: Incremental accumulation with saturation
    new_confidence = current_confidence + new_signal_confidence
    
    # GA-BLOCKING: Bound confidence to [0.0, 100.0]
    new_confidence = min(max(new_confidence, 0.0), 100.0)
    
    return new_confidence


def apply_contradiction_decay(current_confidence: float) -> float:
    """
    GA-BLOCKING: Apply contradiction decay to confidence.
    
    When contradictory evidence appears, confidence decays by CONTRADICTION_DECAY_FACTOR.
    State does not escalate on contradiction.
    
    Args:
        current_confidence: Current confidence score
        
    Returns:
        Decayed confidence score (0.0 to 100.0)
    """
    # GA-BLOCKING: Decay confidence by fixed factor
    decayed_confidence = current_confidence * (1.0 - CONTRADICTION_DECAY_FACTOR)
    
    # GA-BLOCKING: Bound confidence to [0.0, 100.0]
    decayed_confidence = min(max(decayed_confidence, 0.0), 100.0)
    
    return decayed_confidence


def determine_stage(confidence: float) -> str:
    """
    GA-BLOCKING: Determine incident stage based on confidence score.
    
    State transitions:
    - confidence < PROBABLE_THRESHOLD → SUSPICIOUS
    - PROBABLE_THRESHOLD <= confidence < CONFIRMED_THRESHOLD → PROBABLE
    - confidence >= CONFIRMED_THRESHOLD → CONFIRMED
    
    Args:
        confidence: Current confidence score
        
    Returns:
        Incident stage string
    """
    if confidence >= CONFIDENCE_THRESHOLD_CONFIRMED:
        return 'CONFIRMED'
    elif confidence >= CONFIDENCE_THRESHOLD_PROBABLE:
        return 'PROBABLE'
    else:
        return 'SUSPICIOUS'


def should_transition_stage(current_stage: str, new_stage: str) -> bool:
    """
    GA-BLOCKING: Determine if stage transition should occur.
    
    Rules:
    - Transitions only forward: SUSPICIOUS → PROBABLE → CONFIRMED
    - No backward transitions
    - No direct jump to CONFIRMED from SUSPICIOUS (must go through PROBABLE)
    
    Args:
        current_stage: Current incident stage
        new_stage: Proposed new stage
        
    Returns:
        True if transition should occur, False otherwise
    """
    # GA-BLOCKING: No backward transitions
    if current_stage == 'CONFIRMED':
        return False  # CONFIRMED is terminal
    
    if current_stage == 'PROBABLE' and new_stage == 'SUSPICIOUS':
        return False  # No backward transition
    
    if current_stage == 'SUSPICIOUS' and new_stage == 'CONFIRMED':
        return False  # No direct jump to CONFIRMED (must go through PROBABLE)
    
    # GA-BLOCKING: Forward transitions only
    current_index = INCIDENT_STAGES.index(current_stage) if current_stage in INCIDENT_STAGES else -1
    new_index = INCIDENT_STAGES.index(new_stage) if new_stage in INCIDENT_STAGES else -1
    
    if current_index == -1 or new_index == -1:
        return False  # Invalid stage
    
    # GA-BLOCKING: Only allow forward progression (one step at a time)
    return new_index > current_index and new_index == current_index + 1


def get_deduplication_key(event: Dict[str, Any]) -> Optional[str]:
    """
    GA-BLOCKING: Generate deduplication key for event.
    
    Logical identity: machine_id + process_id (if available) + time window
    
    Args:
        event: Event dictionary
        
    Returns:
        Deduplication key string, or None if key cannot be generated
    """
    machine_id = event.get('machine_id')
    if not machine_id:
        return None
    
    # Extract process_id from payload if available
    payload = event.get('payload', {})
    process_id = payload.get('process_id') if isinstance(payload, dict) else None
    
    # GA-BLOCKING: Deduplication key = machine_id + process_id (if available)
    if process_id:
        return f"{machine_id}:{process_id}"
    else:
        return machine_id


def is_within_deduplication_window(event_time: datetime, incident_time: datetime) -> bool:
    """
    GA-BLOCKING: Check if event is within deduplication time window of incident.
    
    Args:
        event_time: Event observed_at timestamp
        incident_time: Incident first_observed_at timestamp
        
    Returns:
        True if within time window, False otherwise
    """
    time_diff = abs((event_time - incident_time).total_seconds())
    return time_diff <= DEDUPLICATION_TIME_WINDOW


def detect_contradiction(event: Dict[str, Any], existing_evidence: list) -> bool:
    """
    GA-BLOCKING: Detect if event contradicts existing evidence.
    
    Simple contradiction detection (logic only, no new rules):
    - If event indicates "clean" behavior but incident has "suspicious" evidence → contradiction
    - If event indicates "benign" process but incident has "malicious" evidence → contradiction
    
    Args:
        event: New event
        existing_evidence: List of existing evidence dictionaries
        
    Returns:
        True if contradiction detected, False otherwise
    """
    # GA-BLOCKING: Simple contradiction detection (logic only)
    # Check if event payload indicates benign/clean behavior
    payload = event.get('payload', {})
    if not isinstance(payload, dict):
        return False
    
    # Check for explicit "clean" indicators in payload
    component = event.get('component', '')
    
    # GA-BLOCKING: If event is from health monitor indicating "healthy" → contradiction
    if component == 'health_monitor' and payload.get('status') == 'HEALTHY':
        # If we have suspicious evidence, this is a contradiction
        if existing_evidence:
            return True
    
    # GA-BLOCKING: If event indicates "benign" process but we have suspicious evidence
    if payload.get('threat_level') == 'BENIGN' and existing_evidence:
        return True
    
    return False
