#!/usr/bin/env python3
"""
RansomEye Alert Engine - Deduplicator
AUTHORITATIVE: Content-based, deterministic alert deduplication
"""

from typing import Dict, Any, List, Set
import hashlib
import json


class DeduplicationError(Exception):
    """Base exception for deduplication errors."""
    pass


class Deduplicator:
    """
    Content-based, deterministic alert deduplication.
    
    Properties:
    - Content-based: Deduplication based on alert content, not time
    - Deterministic: Same alerts always produce same deduplication result
    - Immutable: Deduplication records are immutable
    """
    
    def __init__(self):
        """Initialize deduplicator."""
        self.seen_alerts: Set[str] = set()  # Set of alert content hashes
    
    def is_duplicate(self, alert: Dict[str, Any]) -> bool:
        """
        Check if alert is duplicate.
        
        Deduplication is content-based:
        - Same incident_id + policy_rule_id + severity + risk_score = duplicate
        
        Args:
            alert: Alert dictionary
        
        Returns:
            True if alert is duplicate, False otherwise
        """
        # Build content hash for deduplication
        content_hash = self._calculate_content_hash(alert)
        
        # Check if seen
        if content_hash in self.seen_alerts:
            return True
        
        # Mark as seen
        self.seen_alerts.add(content_hash)
        return False
    
    def _calculate_content_hash(self, alert: Dict[str, Any]) -> str:
        """
        Calculate content hash for deduplication.
        
        Content includes: incident_id, policy_rule_id, severity, risk_score_at_emit
        
        Args:
            alert: Alert dictionary
        
        Returns:
            Content hash as hex string
        """
        # Build deduplication content (deterministic fields only)
        content = {
            'incident_id': alert.get('incident_id', ''),
            'policy_rule_id': alert.get('policy_rule_id', ''),
            'severity': alert.get('severity', ''),
            'risk_score_at_emit': alert.get('risk_score_at_emit', 0)
        }
        
        # Serialize to canonical JSON
        canonical_json = json.dumps(content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        
        # Calculate SHA256 hash
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
    
    def get_previous_alert_hash(self, incident_id: str, alerts: List[Dict[str, Any]]) -> str:
        """
        Get hash of previous alert for same incident (for chaining).
        
        Args:
            incident_id: Incident identifier
            alerts: List of all alerts (ordered by emitted_at)
        
        Returns:
            Hash of previous alert, or zero hash if no previous alert
        """
        # Find previous alert for same incident
        incident_alerts = [a for a in alerts if a.get('incident_id') == incident_id]
        
        if len(incident_alerts) < 2:
            return '0' * 64  # No previous alert
        
        # Sort by emitted_at (most recent last)
        sorted_alerts = sorted(incident_alerts, key=lambda a: a.get('emitted_at', ''))
        
        # Get second-to-last alert (previous to current)
        if len(sorted_alerts) >= 2:
            prev_alert = sorted_alerts[-2]
            return prev_alert.get('immutable_hash', '0' * 64)
        
        return '0' * 64
