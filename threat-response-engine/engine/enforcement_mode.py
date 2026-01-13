#!/usr/bin/env python3
"""
RansomEye v1.0 Threat Response Engine - Enforcement Mode
AUTHORITATIVE: Defines and manages TRE enforcement modes (FROZEN)
Python 3.10+ only
"""

from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class TREMode(Enum):
    """
    TRE Enforcement Modes (FROZEN - exactly three modes).
    
    DRY_RUN: Simulate only (no execution)
    GUARDED_EXEC: Execute SAFE actions only, block DESTRUCTIVE
    FULL_ENFORCE: Execute all actions, HAF required for DESTRUCTIVE
    """
    DRY_RUN = 'DRY_RUN'
    GUARDED_EXEC = 'GUARDED_EXEC'
    FULL_ENFORCE = 'FULL_ENFORCE'


class ActionClassification(Enum):
    """
    Action Classification (FROZEN - immutable).
    
    SAFE: Actions that can be executed without HAF approval
    DESTRUCTIVE: Actions that require HAF approval in FULL_ENFORCE mode
    """
    SAFE = 'SAFE'
    DESTRUCTIVE = 'DESTRUCTIVE'


# ============================================================================
# ACTION CLASSIFICATION (FROZEN - IMMUTABLE)
# ============================================================================

SAFE_ACTIONS = {
    'BLOCK_PROCESS',
    'BLOCK_NETWORK_CONNECTION',
    'TEMPORARY_FIREWALL_RULE',
    'QUARANTINE_FILE'
}

DESTRUCTIVE_ACTIONS = {
    'ISOLATE_HOST',
    'LOCK_USER',
    'DISABLE_SERVICE',
    'MASS_PROCESS_KILL',
    'NETWORK_SEGMENT_ISOLATION'
}

# Map existing command types to new classifications
COMMAND_TYPE_MAPPING = {
    'BLOCK_PROCESS': 'BLOCK_PROCESS',
    'BLOCK_NETWORK': 'BLOCK_NETWORK_CONNECTION',
    'QUARANTINE_FILE': 'QUARANTINE_FILE',
    'ISOLATE_HOST': 'ISOLATE_HOST',
    'QUARANTINE_HOST': 'ISOLATE_HOST',  # Map to ISOLATE_HOST
    'TERMINATE_PROCESS': 'MASS_PROCESS_KILL',  # Map to MASS_PROCESS_KILL
    'DISABLE_USER': 'LOCK_USER',  # Map to LOCK_USER
    'REVOKE_ACCESS': 'LOCK_USER'  # Map to LOCK_USER
}


def classify_action(action_type: str) -> ActionClassification:
    """
    Classify action as SAFE or DESTRUCTIVE.
    
    Args:
        action_type: Action type string
    
    Returns:
        ActionClassification enum value
    
    Raises:
        ValueError: If action type is unknown
    """
    # Normalize action type
    normalized = COMMAND_TYPE_MAPPING.get(action_type, action_type)
    
    if normalized in SAFE_ACTIONS:
        return ActionClassification.SAFE
    elif normalized in DESTRUCTIVE_ACTIONS:
        return ActionClassification.DESTRUCTIVE
    else:
        raise ValueError(f"Unknown action type: {action_type}")


def is_safe_action(action_type: str) -> bool:
    """
    Check if action is SAFE.
    
    Args:
        action_type: Action type string
    
    Returns:
        True if SAFE, False if DESTRUCTIVE
    """
    try:
        return classify_action(action_type) == ActionClassification.SAFE
    except ValueError:
        return False


def is_destructive_action(action_type: str) -> bool:
    """
    Check if action is DESTRUCTIVE.
    
    Args:
        action_type: Action type string
    
    Returns:
        True if DESTRUCTIVE, False if SAFE
    """
    try:
        return classify_action(action_type) == ActionClassification.DESTRUCTIVE
    except ValueError:
        return False


def get_mode_behavior(mode: TREMode, action_classification: ActionClassification) -> Dict[str, Any]:
    """
    Get behavior for mode and action classification.
    
    Args:
        mode: TRE enforcement mode
        action_classification: Action classification
    
    Returns:
        Dictionary with 'execute' and 'haf_required' flags
    """
    if mode == TREMode.DRY_RUN:
        return {
            'execute': False,
            'haf_required': False,
            'simulate_only': True
        }
    elif mode == TREMode.GUARDED_EXEC:
        if action_classification == ActionClassification.SAFE:
            return {
                'execute': True,
                'haf_required': False,
                'simulate_only': False
            }
        else:
            return {
                'execute': False,
                'haf_required': False,
                'simulate_only': False,
                'blocked': True,
                'reason': 'DESTRUCTIVE actions blocked in GUARDED_EXEC mode'
            }
    else:  # FULL_ENFORCE
        if action_classification == ActionClassification.SAFE:
            return {
                'execute': True,
                'haf_required': False,
                'simulate_only': False
            }
        else:
            return {
                'execute': True,
                'haf_required': True,
                'simulate_only': False
            }
