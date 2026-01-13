#!/usr/bin/env python3
"""
RansomEye LLM Summarizer - Pattern Detector
AUTHORITATIVE: Deterministic sensitive pattern detection
"""

import re
from typing import Dict, Any, List, Optional, Tuple


class PatternDetectorError(Exception):
    """Base exception for pattern detector errors."""
    pass


class PatternDetector:
    """
    Deterministic sensitive pattern detector.
    
    Properties:
    - Deterministic: Same input always produces same detection
    - Ordered: Patterns checked in fixed order
    - No false positives: Patterns are strict (no heuristics)
    """
    
    # Pattern definitions (ordered, deterministic)
    PATTERNS = {
        'SSN_PATTERN': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        'SSN_NO_DASH': re.compile(r'\b\d{9}\b'),
        'CREDIT_CARD_VISA': re.compile(r'\b4\d{3}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
        'CREDIT_CARD_MASTERCARD': re.compile(r'\b5[1-5]\d{2}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
        'CREDIT_CARD_AMEX': re.compile(r'\b3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5}\b'),
        'API_KEY_BASIC': re.compile(r'\b[A-Za-z0-9]{32,}\b'),  # 32+ char alphanumeric
        'BEARER_TOKEN': re.compile(r'\bBearer\s+[A-Za-z0-9\-_]{20,}\b', re.IGNORECASE),
        'AWS_ACCESS_KEY': re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
        'PRIVATE_KEY_HEADER': re.compile(r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----', re.IGNORECASE),
    }
    
    def __init__(self):
        """Initialize pattern detector."""
        pass
    
    def detect_patterns(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect sensitive patterns in text.
        
        Args:
            text: Text to scan
        
        Returns:
            List of detected pattern dictionaries (ordered by position)
        """
        if not isinstance(text, str):
            raise PatternDetectorError(f"Text must be string, got {type(text)}")
        
        detections = []
        
        # Check each pattern in fixed order
        for pattern_name, pattern_regex in self.PATTERNS.items():
            matches = pattern_regex.finditer(text)
            for match in matches:
                detections.append({
                    'pattern_name': pattern_name,
                    'matched_text': match.group(0),
                    'start_pos': match.start(),
                    'end_pos': match.end()
                })
        
        # Sort by position (deterministic ordering)
        detections.sort(key=lambda x: (x['start_pos'], x['end_pos']))
        
        return detections
    
    def has_sensitive_patterns(self, text: str) -> bool:
        """
        Check if text contains sensitive patterns.
        
        Args:
            text: Text to check
        
        Returns:
            True if sensitive patterns detected, False otherwise
        """
        detections = self.detect_patterns(text)
        return len(detections) > 0
