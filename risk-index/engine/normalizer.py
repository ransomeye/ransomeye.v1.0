#!/usr/bin/env python3
"""
RansomEye Enterprise Risk Index - Score Normalization
AUTHORITATIVE: Deterministic normalization to 0-100 range with severity bands
"""

from typing import Dict, Any


class NormalizationError(Exception):
    """Base exception for normalization errors."""
    pass


class Normalizer:
    """
    Deterministic normalization of risk scores to 0-100 range.
    
    All normalization is deterministic (no randomness).
    Same inputs always produce same outputs.
    """
    
    # Severity band thresholds
    SEVERITY_BANDS = {
        'LOW': (0, 25),
        'MODERATE': (25, 50),
        'HIGH': (50, 75),
        'CRITICAL': (75, 100)
    }
    
    @staticmethod
    def normalize_score(raw_score: float) -> float:
        """
        Normalize raw score to 0-100 range.
        
        Args:
            raw_score: Raw risk score (may be outside 0-100)
        
        Returns:
            Normalized score in range 0-100
        """
        # Clamp to valid range
        normalized = max(0.0, min(100.0, raw_score))
        return normalized
    
    @staticmethod
    def determine_severity_band(score: float) -> str:
        """
        Determine severity band from normalized score.
        
        Args:
            score: Normalized risk score (0-100)
        
        Returns:
            Severity band (LOW, MODERATE, HIGH, CRITICAL)
        """
        if score < 25:
            return 'LOW'
        elif score < 50:
            return 'MODERATE'
        elif score < 75:
            return 'HIGH'
        else:
            return 'CRITICAL'
    
    @staticmethod
    def normalize_component_scores(component_scores: Dict[str, float]) -> Dict[str, float]:
        """
        Normalize all component scores to 0-100 range.
        
        Args:
            component_scores: Dictionary of component scores
        
        Returns:
            Dictionary of normalized component scores
        """
        normalized = {}
        for component, score in component_scores.items():
            normalized[component] = Normalizer.normalize_score(score)
        return normalized
    
    @staticmethod
    def compute_confidence_score(
        signals_processed: int,
        signals_expected: int,
        component_confidence: Dict[str, float]
    ) -> float:
        """
        Compute overall confidence score based on signal completeness and component confidence.
        
        Args:
            signals_processed: Number of signals processed
            signals_expected: Number of signals expected
            component_confidence: Dictionary of component confidence scores (0-1)
        
        Returns:
            Overall confidence score (0-1)
        """
        # Signal completeness factor
        if signals_expected > 0:
            completeness = min(1.0, signals_processed / signals_expected)
        else:
            completeness = 1.0
        
        # Average component confidence
        if component_confidence:
            avg_confidence = sum(component_confidence.values()) / len(component_confidence)
        else:
            avg_confidence = 1.0
        
        # Combined confidence (weighted average)
        # Completeness weight: 0.3, Component confidence weight: 0.7
        confidence = (0.3 * completeness) + (0.7 * avg_confidence)
        
        # Ensure confidence stays in valid range
        return max(0.0, min(1.0, confidence))
