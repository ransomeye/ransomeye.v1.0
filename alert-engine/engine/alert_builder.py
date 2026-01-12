#!/usr/bin/env python3
"""
RansomEye Alert Engine - Alert Builder
AUTHORITATIVE: Builds immutable alert facts from incidents and routing decisions
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
import uuid
import hashlib
import json


class AlertBuildError(Exception):
    """Base exception for alert building errors."""
    pass


class AlertBuilder:
    """
    Builds immutable alert facts.
    
    Properties:
    - Immutable: Alerts cannot be modified after creation
    - Deterministic: Same inputs always produce same alert
    - Chainable: Alerts are chainable per incident (prev_alert_hash)
    - Explainable: All alerts have explanation bundle references
    """
    
    def __init__(self):
        """Initialize alert builder."""
        pass
    
    def build_alert(
        self,
        incident: Dict[str, Any],
        routing_decision: Dict[str, Any],
        explanation_bundle_id: str,
        risk_score: float,
        prev_alert_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build alert from incident and routing decision.
        
        Args:
            incident: Incident dictionary
            routing_decision: Routing decision from policy engine
            explanation_bundle_id: Explanation bundle identifier (SEE)
            risk_score: Risk score at time of emission
            prev_alert_hash: Hash of previous alert for same incident (for chaining)
        
        Returns:
            Alert dictionary
        """
        alert_id = str(uuid.uuid4())
        incident_id = incident.get('incident_id', '')
        policy_rule_id = routing_decision.get('rule_id', '')
        routing_decision_id = routing_decision.get('decision_id', '')
        severity = self._determine_severity(incident, risk_score)
        authority_required = routing_decision.get('required_authority', 'NONE')
        emitted_at = datetime.now(timezone.utc).isoformat()
        
        # Build alert content (for hashing)
        alert_content = {
            'alert_id': alert_id,
            'incident_id': incident_id,
            'policy_rule_id': policy_rule_id,
            'severity': severity,
            'risk_score_at_emit': risk_score,
            'explanation_bundle_id': explanation_bundle_id,
            'authority_required': authority_required,
            'routing_decision_id': routing_decision_id,
            'emitted_at': emitted_at,
            'prev_alert_hash': prev_alert_hash or ''
        }
        
        # Calculate immutable hash
        immutable_hash = self._calculate_hash(alert_content)
        
        # Build alert
        alert = {
            'alert_id': alert_id,
            'incident_id': incident_id,
            'policy_rule_id': policy_rule_id,
            'severity': severity,
            'risk_score_at_emit': risk_score,
            'explanation_bundle_id': explanation_bundle_id,
            'authority_required': authority_required,
            'routing_decision_id': routing_decision_id,
            'emitted_at': emitted_at,
            'immutable_hash': immutable_hash,
            'prev_alert_hash': prev_alert_hash or '0' * 64  # Default to zero hash if no previous alert
        }
        
        return alert
    
    def _determine_severity(self, incident: Dict[str, Any], risk_score: float) -> str:
        """
        Determine alert severity from incident and risk score.
        
        Deterministic rules:
        - CRITICAL: risk_score >= 90
        - HIGH: risk_score >= 70
        - MODERATE: risk_score >= 40
        - LOW: risk_score < 40
        """
        if risk_score >= 90:
            return 'CRITICAL'
        elif risk_score >= 70:
            return 'HIGH'
        elif risk_score >= 40:
            return 'MODERATE'
        else:
            return 'LOW'
    
    def _calculate_hash(self, content: Dict[str, Any]) -> str:
        """
        Calculate SHA256 hash of alert content.
        
        Args:
            content: Alert content dictionary
        
        Returns:
            SHA256 hash as hex string
        """
        # Serialize to canonical JSON (deterministic)
        canonical_json = json.dumps(content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        
        # Calculate SHA256 hash
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
