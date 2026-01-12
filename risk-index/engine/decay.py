#!/usr/bin/env python3
"""
RansomEye Enterprise Risk Index - Temporal Decay Functions
AUTHORITATIVE: Deterministic temporal decay for risk signal aging
"""

from typing import Dict, Any
from datetime import datetime, timezone, timedelta
import math


class DecayError(Exception):
    """Base exception for decay function errors."""
    pass


class DecayFunction:
    """
    Deterministic temporal decay functions for risk signals.
    
    All functions are deterministic (no randomness).
    Same inputs always produce same outputs.
    """
    
    @staticmethod
    def exponential_decay(
        base_score: float,
        age_seconds: float,
        half_life_seconds: float
    ) -> float:
        """
        Exponential decay function.
        
        Formula: score * exp(-ln(2) * age / half_life)
        
        Args:
            base_score: Original risk score (0-100)
            age_seconds: Age of signal in seconds
            half_life_seconds: Half-life in seconds (time for score to halve)
        
        Returns:
            Decayed risk score (0-100)
        """
        if half_life_seconds <= 0:
            raise DecayError("Half-life must be positive")
        
        if age_seconds < 0:
            raise DecayError("Age cannot be negative")
        
        if age_seconds == 0:
            return base_score
        
        # Exponential decay: score * exp(-ln(2) * age / half_life)
        decay_factor = math.exp(-math.log(2) * age_seconds / half_life_seconds)
        decayed_score = base_score * decay_factor
        
        # Ensure score stays in valid range
        return max(0.0, min(100.0, decayed_score))
    
    @staticmethod
    def linear_decay(
        base_score: float,
        age_seconds: float,
        max_age_seconds: float
    ) -> float:
        """
        Linear decay function.
        
        Formula: score * (1 - age / max_age) for age < max_age, else 0
        
        Args:
            base_score: Original risk score (0-100)
            age_seconds: Age of signal in seconds
            max_age_seconds: Maximum age before score reaches zero
        
        Returns:
            Decayed risk score (0-100)
        """
        if max_age_seconds <= 0:
            raise DecayError("Max age must be positive")
        
        if age_seconds < 0:
            raise DecayError("Age cannot be negative")
        
        if age_seconds >= max_age_seconds:
            return 0.0
        
        # Linear decay: score * (1 - age / max_age)
        decay_factor = 1.0 - (age_seconds / max_age_seconds)
        decayed_score = base_score * decay_factor
        
        # Ensure score stays in valid range
        return max(0.0, min(100.0, decayed_score))
    
    @staticmethod
    def step_decay(
        base_score: float,
        age_seconds: float,
        step_intervals: list
    ) -> float:
        """
        Step decay function.
        
        Score remains constant within intervals, then drops at step boundaries.
        
        Args:
            base_score: Original risk score (0-100)
            age_seconds: Age of signal in seconds
            step_intervals: List of tuples (max_age_seconds, decay_factor)
                           e.g., [(3600, 1.0), (86400, 0.5), (604800, 0.25)]
        
        Returns:
            Decayed risk score (0-100)
        """
        if age_seconds < 0:
            raise DecayError("Age cannot be negative")
        
        # Find appropriate step interval
        decay_factor = 1.0
        for max_age, factor in step_intervals:
            if age_seconds <= max_age:
                decay_factor = factor
                break
        
        decayed_score = base_score * decay_factor
        
        # Ensure score stays in valid range
        return max(0.0, min(100.0, decayed_score))
    
    @staticmethod
    def apply_decay(
        base_score: float,
        signal_timestamp: datetime,
        current_timestamp: datetime,
        decay_config: Dict[str, Any]
    ) -> tuple:
        """
        Apply temporal decay to risk score.
        
        Args:
            base_score: Original risk score (0-100)
            signal_timestamp: Timestamp of signal
            current_timestamp: Current timestamp
            decay_config: Decay configuration dictionary
        
        Returns:
            Tuple of (decayed_score, decay_metadata)
        """
        if signal_timestamp > current_timestamp:
            raise DecayError("Signal timestamp cannot be in the future")
        
        age_seconds = (current_timestamp - signal_timestamp).total_seconds()
        
        decay_function = decay_config.get('function', 'none')
        
        if decay_function == 'none' or age_seconds < 0:
            return base_score, {
                'decay_function': 'none',
                'decay_parameters': {},
                'age_seconds': age_seconds
            }
        
        elif decay_function == 'exponential':
            half_life = decay_config.get('half_life_seconds', 86400)  # Default 24 hours
            decayed_score = DecayFunction.exponential_decay(base_score, age_seconds, half_life)
            return decayed_score, {
                'decay_function': 'exponential',
                'decay_parameters': {
                    'half_life_seconds': half_life,
                    'age_seconds': age_seconds
                },
                'age_seconds': age_seconds
            }
        
        elif decay_function == 'linear':
            max_age = decay_config.get('max_age_seconds', 604800)  # Default 7 days
            decayed_score = DecayFunction.linear_decay(base_score, age_seconds, max_age)
            return decayed_score, {
                'decay_function': 'linear',
                'decay_parameters': {
                    'max_age_seconds': max_age,
                    'age_seconds': age_seconds
                },
                'age_seconds': age_seconds
            }
        
        elif decay_function == 'step':
            step_intervals = decay_config.get('step_intervals', [
                (3600, 1.0),      # 1 hour: 100%
                (86400, 0.5),     # 1 day: 50%
                (604800, 0.25)    # 1 week: 25%
            ])
            decayed_score = DecayFunction.step_decay(base_score, age_seconds, step_intervals)
            return decayed_score, {
                'decay_function': 'step',
                'decay_parameters': {
                    'step_intervals': step_intervals,
                    'age_seconds': age_seconds
                },
                'age_seconds': age_seconds
            }
        
        else:
            raise DecayError(f"Unknown decay function: {decay_function}")
