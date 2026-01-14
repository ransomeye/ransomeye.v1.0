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
    PHASE 3: Determine incident stage based on confidence score.
    
    State transitions (deterministic):
    - confidence == 0.0 → CLEAN (no signals, incident should not exist)
    - 0.0 < confidence < PROBABLE_THRESHOLD → SUSPICIOUS
    - PROBABLE_THRESHOLD <= confidence < CONFIRMED_THRESHOLD → PROBABLE
    - confidence >= CONFIRMED_THRESHOLD → CONFIRMED
    
    Args:
        confidence: Current confidence score
        
    Returns:
        Incident stage string
    """
    if confidence == 0.0:
        return 'CLEAN'  # PHASE 3: CLEAN state (no signals)
    elif confidence >= CONFIDENCE_THRESHOLD_CONFIRMED:
        return 'CONFIRMED'
    elif confidence >= CONFIDENCE_THRESHOLD_PROBABLE:
        return 'PROBABLE'
    else:
        return 'SUSPICIOUS'


def should_transition_stage(current_stage: str, new_stage: str) -> bool:
    """
    PHASE 3: Determine if stage transition should occur (deterministic guards).
    
    Rules:
    - Transitions only forward: CLEAN → SUSPICIOUS → PROBABLE → CONFIRMED
    - No backward transitions
    - No direct jump to CONFIRMED from SUSPICIOUS (must go through PROBABLE)
    - No time-based escalation (transitions based on confidence only)
    - No single-signal CONFIRMED (must accumulate confidence)
    
    Args:
        current_stage: Current incident stage
        new_stage: Proposed new stage
        
    Returns:
        True if transition should occur, False otherwise
    """
    # PHASE 3: No backward transitions
    if current_stage == 'CONFIRMED':
        return False  # CONFIRMED is terminal
    
    if current_stage == 'PROBABLE' and new_stage in ['SUSPICIOUS', 'CLEAN']:
        return False  # No backward transition
    
    if current_stage == 'SUSPICIOUS' and new_stage in ['CLEAN', 'CONFIRMED']:
        return False  # No backward transition, no direct jump to CONFIRMED
    
    if current_stage == 'CLEAN' and new_stage != 'SUSPICIOUS':
        return False  # CLEAN can only transition to SUSPICIOUS
    
    # PHASE 3: Forward transitions only (deterministic, one step at a time)
    current_index = INCIDENT_STAGES.index(current_stage) if current_stage in INCIDENT_STAGES else -1
    new_index = INCIDENT_STAGES.index(new_stage) if new_stage in INCIDENT_STAGES else -1
    
    if current_index == -1 or new_index == -1:
        return False  # Invalid stage
    
    # PHASE 3: Only allow forward progression (one step at a time, deterministic)
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


def detect_contradiction(event: Dict[str, Any], existing_evidence: list) -> Tuple[bool, Optional[str]]:
    """
    PHASE 3: Detect if event contradicts existing evidence (deterministic).
    
    Contradiction types:
    1. Host vs Network: Host signals suspicious activity but network shows benign traffic
    2. Execution vs Timing: Execution signals present but timing indicates normal operation
    3. Persistence vs Silence: Persistence signals but no ongoing activity
    4. Deception vs Absence: Deception signals but no deception artifacts found
    
    Args:
        event: New event
        existing_evidence: List of existing evidence dictionaries
        
    Returns:
        Tuple of (is_contradiction: bool, contradiction_type: Optional[str])
    """
    if not existing_evidence:
        return False, None  # No existing evidence, no contradiction possible
    
    payload = event.get('payload', {})
    if not isinstance(payload, dict):
        return False, None
    
    component = event.get('component', '')
    
    # PHASE 3: Contradiction Type 1 - Host vs Network
    # Host signals suspicious but network shows benign
    host_components = ['linux_agent', 'windows_agent']
    network_components = ['dpi']
    
    if component in network_components:
        # Network component showing benign traffic
        if payload.get('threat_level') == 'BENIGN' or payload.get('flow_type') == 'NORMAL':
            # Check if existing evidence has host-based suspicious signals
            for evidence in existing_evidence:
                evidence_component = evidence.get('component', '')
                if evidence_component in host_components:
                    evidence_payload = evidence.get('payload', {})
                    if isinstance(evidence_payload, dict):
                        if evidence_payload.get('threat_level') in ['SUSPICIOUS', 'MALICIOUS']:
                            return True, 'HOST_VS_NETWORK'
    
    # PHASE 3: Contradiction Type 2 - Execution vs Timing
    # Execution signals present but timing indicates normal operation
    if component in host_components:
        if payload.get('event_type') in ['PROCESS_EXECUTION', 'FILE_MODIFICATION']:
            # Check timing - if execution happened during normal business hours with normal patterns
            if payload.get('timing_pattern') == 'NORMAL' or payload.get('business_hours') == True:
                # Check if existing evidence has high-confidence suspicious execution
                for evidence in existing_evidence:
                    evidence_payload = evidence.get('payload', {})
                    if isinstance(evidence_payload, dict):
                        if evidence_payload.get('event_type') in ['PROCESS_EXECUTION', 'FILE_MODIFICATION']:
                            if evidence_payload.get('threat_level') in ['SUSPICIOUS', 'MALICIOUS']:
                                return True, 'EXECUTION_VS_TIMING'
    
    # PHASE 3: Contradiction Type 3 - Persistence vs Silence
    # Persistence signals but no ongoing activity
    if payload.get('event_type') == 'PERSISTENCE':
        # Persistence mechanism detected
        if payload.get('activity_level') == 'NONE' or payload.get('ongoing_activity') == False:
            # Check if existing evidence has persistence indicators
            for evidence in existing_evidence:
                evidence_payload = evidence.get('payload', {})
                if isinstance(evidence_payload, dict):
                    if evidence_payload.get('event_type') == 'PERSISTENCE':
                        # Persistence detected but no activity - contradiction
                        return True, 'PERSISTENCE_VS_SILENCE'
    
    # PHASE 3: Contradiction Type 4 - Deception vs Absence
    # Deception signals but no deception artifacts found
    if component == 'deception':
        if payload.get('deception_triggered') == False or payload.get('artifacts_found') == False:
            # Check if existing evidence has deception signals
            for evidence in existing_evidence:
                evidence_component = evidence.get('component', '')
                if evidence_component == 'deception':
                    evidence_payload = evidence.get('payload', {})
                    if isinstance(evidence_payload, dict):
                        if evidence_payload.get('deception_triggered') == True:
                            # Deception was triggered but no artifacts found - contradiction
                            return True, 'DECEPTION_VS_ABSENCE'
    
    # PHASE 3: Generic contradiction - health monitor indicates healthy
    if component == 'health_monitor' and payload.get('status') == 'HEALTHY':
        if existing_evidence:
            return True, 'HEALTHY_VS_SUSPICIOUS'
    
    # PHASE 3: Generic contradiction - explicit benign threat level
    if payload.get('threat_level') == 'BENIGN' and existing_evidence:
        return True, 'BENIGN_VS_SUSPICIOUS'
    
    return False, None
