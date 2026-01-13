#!/usr/bin/env python3
"""
RansomEye Enterprise Risk Index - Risk Aggregator
AUTHORITATIVE: Deterministic weighted aggregation of risk signals
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone


class AggregationError(Exception):
    """Base exception for aggregation errors."""
    pass


class SignalIngestionError(AggregationError):
    """Raised when signal ingestion fails."""
    pass


class Aggregator:
    """
    Deterministic weighted aggregation of risk signals.
    
    Properties:
    - Deterministic: Same inputs always produce same outputs
    - Weighted: Explicit weight configuration
    - Confidence-aware: Adjusts scores based on confidence
    - Temporal decay: Applies decay functions to aged signals
    """
    
    def __init__(
        self,
        weights: Dict[str, float],
        decay_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize aggregator.
        
        Args:
            weights: Component weights dictionary (must sum to 1.0)
            decay_config: Optional temporal decay configuration
        """
        # Validate weights sum to 1.0
        weight_sum = sum(weights.values())
        if abs(weight_sum - 1.0) > 0.001:  # Allow small floating point error
            raise AggregationError(f"Weights must sum to 1.0, got {weight_sum}")
        
        self.weights = weights
        self.decay_config = decay_config or {'function': 'none'}
    
    def ingest_incidents(self, incidents: List[Dict[str, Any]]) -> float:
        """
        Ingest incident signals (read-only).
        
        Args:
            incidents: List of incident dictionaries (read-only, no mutation)
        
        Returns:
            Aggregated incident risk score (0-100)
        """
        if not incidents:
            return 0.0
        
        # Compute risk from incidents
        # For Phase B2, we use a simple aggregation:
        # - Count of incidents weighted by severity
        # - No mutation of source data
        
        total_risk = 0.0
        for incident in incidents:
            # Extract risk contribution (read-only)
            severity = incident.get('severity', 'low')
            severity_weights = {
                'low': 10.0,
                'medium': 30.0,
                'high': 60.0,
                'critical': 100.0
            }
            risk_contribution = severity_weights.get(severity.lower(), 0.0)
            total_risk += risk_contribution
        
        # Normalize by number of incidents (bounded)
        avg_risk = total_risk / len(incidents) if incidents else 0.0
        
        # Cap at 100
        return min(100.0, avg_risk)
    
    def ingest_ai_metadata(
        self,
        ai_metadata: List[Dict[str, Any]],
        current_timestamp: datetime
    ) -> tuple:
        """
        Ingest AI metadata signals (read-only).
        
        Args:
            ai_metadata: List of AI metadata dictionaries (read-only)
            current_timestamp: Current timestamp for decay calculation
        
        Returns:
            Tuple of (aggregated_score, confidence)
        """
        if not ai_metadata:
            return 0.0, 1.0
        
        # Compute risk from AI metadata
        # Factors: novelty, clusters, drift markers
        total_risk = 0.0
        total_confidence = 0.0
        
        from engine.decay import DecayFunction
        
        for metadata in ai_metadata:
            # Extract risk indicators (read-only)
            novelty_score = metadata.get('novelty_score', 0.0)
            cluster_risk = metadata.get('cluster_risk', 0.0)
            drift_marker = metadata.get('drift_marker', 0.0)
            confidence = metadata.get('confidence', 1.0)
            
            # Compute component risk (weighted average)
            component_risk = (
                0.4 * novelty_score +
                0.4 * cluster_risk +
                0.2 * drift_marker
            )
            
            # Apply temporal decay if configured
            signal_timestamp_str = metadata.get('timestamp')
            if signal_timestamp_str and self.decay_config.get('function') != 'none':
                try:
                    signal_timestamp = datetime.fromisoformat(signal_timestamp_str.replace('Z', '+00:00'))
                    decayed_risk, _ = DecayFunction.apply_decay(
                        component_risk,
                        signal_timestamp,
                        current_timestamp,
                        self.decay_config
                    )
                    component_risk = decayed_risk
                except Exception:
                    pass  # If decay fails, use original score
            
            total_risk += component_risk
            total_confidence += confidence
        
        # Average scores
        avg_risk = total_risk / len(ai_metadata) if ai_metadata else 0.0
        avg_confidence = total_confidence / len(ai_metadata) if ai_metadata else 1.0
        
        return min(100.0, avg_risk), max(0.0, min(1.0, avg_confidence))
    
    def ingest_policy_decisions(self, policy_decisions: List[Dict[str, Any]]) -> float:
        """
        Ingest policy decision signals (read-only).
        
        Args:
            policy_decisions: List of policy decision dictionaries (read-only)
        
        Returns:
            Aggregated policy decision risk score (0-100)
        """
        if not policy_decisions:
            return 0.0
        
        # Compute risk from policy decisions
        # Factors: enforcement actions, overrides, violations
        total_risk = 0.0
        
        for decision in policy_decisions:
            # Extract risk indicators (read-only)
            action_type = decision.get('action_type', 'allow')
            risk_weights = {
                'allow': 0.0,
                'warn': 10.0,
                'block': 50.0,
                'override': 30.0,
                'violation': 80.0
            }
            risk_contribution = risk_weights.get(action_type.lower(), 0.0)
            total_risk += risk_contribution
        
        # Average risk
        avg_risk = total_risk / len(policy_decisions) if policy_decisions else 0.0
        
        return min(100.0, avg_risk)
    
    def aggregate(
        self,
        incidents: List[Dict[str, Any]],
        ai_metadata: List[Dict[str, Any]],
        policy_decisions: List[Dict[str, Any]],
        threat_correlation: Optional[List[Dict[str, Any]]] = None,
        uba: Optional[List[Dict[str, Any]]] = None,
        current_timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Aggregate all risk signals into single risk score.
        
        Args:
            incidents: List of incident signals (read-only)
            ai_metadata: List of AI metadata signals (read-only)
            policy_decisions: List of policy decision signals (read-only)
            threat_correlation: Optional list of threat correlation signals (read-only, future)
            uba: Optional list of UBA signals (read-only, future)
            current_timestamp: Current timestamp for decay calculation
        
        Returns:
            Dictionary with aggregated risk score and component scores
        """
        if current_timestamp is None:
            current_timestamp = datetime.now(timezone.utc)
        
        # Ingest signals (read-only, no mutation)
        incident_score = self.ingest_incidents(incidents)
        ai_score, ai_confidence = self.ingest_ai_metadata(ai_metadata, current_timestamp)
        policy_score = self.ingest_policy_decisions(policy_decisions)
        
        # GA-BLOCKING FIX: Removed placeholder threat_score and uba_score.
        # Threat correlation and UBA signals are not part of v1.0.
        # Component scores only include v1.0 signals.
        component_scores = {
            'incidents': incident_score,
            'ai_metadata': ai_score,
            'policy_decisions': policy_score
        }
        
        # Weighted aggregation (v1.0 signals only)
        weighted_sum = (
            self.weights.get('incidents', 0.0) * incident_score +
            self.weights.get('ai_metadata', 0.0) * ai_score +
            self.weights.get('policy_decisions', 0.0) * policy_score
        )
        
        # Normalize to 0-100
        from engine.normalizer import Normalizer
        normalized_score = Normalizer.normalize_score(weighted_sum)
        
        # Compute confidence
        component_confidence = {
            'ai_metadata': ai_confidence
        }
        signals_processed = len(incidents) + len(ai_metadata) + len(policy_decisions)
        signals_expected = signals_processed  # For Phase B2, assume all expected signals are present
        confidence = Normalizer.compute_confidence_score(
            signals_processed,
            signals_expected,
            component_confidence
        )
        
        return {
            'risk_score': normalized_score,
            'component_scores': component_scores,
            'confidence_score': confidence,
            'weights_used': self.weights.copy()
        }
