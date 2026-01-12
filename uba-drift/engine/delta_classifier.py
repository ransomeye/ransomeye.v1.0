#!/usr/bin/env python3
"""
RansomEye UBA Drift - Delta Classifier
AUTHORITATIVE: Classify delta TYPE only (NOT severity, NOT intent, NOT threat)
"""

from typing import Dict, Any


class DeltaClassificationError(Exception):
    """Base exception for delta classification errors."""
    pass


class DeltaClassifier:
    """
    Delta type classifier.
    
    Properties:
    - Type only: Classifies delta TYPE only
    - NOT severity: Does NOT classify severity
    - NOT intent: Does NOT classify intent
    - NOT threat: Does NOT classify threat
    """
    
    def __init__(self):
        """Initialize delta classifier."""
        self.valid_types = [
            'NEW_EVENT_TYPE',
            'NEW_HOST',
            'NEW_TIME_BUCKET',
            'NEW_PRIVILEGE',
            'FREQUENCY_SHIFT'
        ]
    
    def classify_type(self, delta: Dict[str, Any]) -> str:
        """
        Classify delta type.
        
        Args:
            delta: Delta dictionary
        
        Returns:
            Delta type string
        """
        delta_type = delta.get('delta_type', '')
        
        if delta_type not in self.valid_types:
            raise DeltaClassificationError(f"Invalid delta type: {delta_type}")
        
        return delta_type
    
    def validate_type(self, delta_type: str) -> bool:
        """
        Validate delta type.
        
        Args:
            delta_type: Delta type string
        
        Returns:
            True if valid, False otherwise
        """
        return delta_type in self.valid_types
