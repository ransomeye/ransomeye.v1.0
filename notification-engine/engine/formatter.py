#!/usr/bin/env python3
"""
RansomEye Notification Engine - Formatter
AUTHORITATIVE: Deterministic payload formatting for delivery
"""

from typing import Dict, Any
import hashlib
import json


class FormattingError(Exception):
    """Base exception for formatting errors."""
    pass


class Formatter:
    """
    Deterministic payload formatting for delivery.
    
    Properties:
    - Deterministic: Same alert + same target = same payload hash
    - Idempotent: Formatting is idempotent
    - Type-specific: Different formats for different delivery types
    """
    
    def __init__(self):
        """Initialize formatter."""
        pass
    
    def format_payload(
        self,
        alert: Dict[str, Any],
        target: Dict[str, Any],
        explanation_bundle_id: str
    ) -> Dict[str, Any]:
        """
        Format delivery payload.
        
        Args:
            alert: Alert dictionary
            target: Target dictionary
            explanation_bundle_id: Explanation bundle identifier
        
        Returns:
            Formatted payload dictionary
        """
        delivery_type = target.get('target_type', '')
        
        if delivery_type == 'email':
            return self._format_email(alert, target, explanation_bundle_id)
        elif delivery_type == 'webhook':
            return self._format_webhook(alert, target, explanation_bundle_id)
        elif delivery_type == 'ticket':
            return self._format_ticket(alert, target, explanation_bundle_id)
        elif delivery_type == 'siem':
            return self._format_siem(alert, target, explanation_bundle_id)
        else:
            raise FormattingError(f"Unknown delivery type: {delivery_type}")
    
    def calculate_payload_hash(self, payload: Dict[str, Any]) -> str:
        """
        Calculate SHA256 hash of payload.
        
        Args:
            payload: Payload dictionary
        
        Returns:
            SHA256 hash as hex string
        """
        # Serialize to canonical JSON (deterministic)
        canonical_json = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        payload_bytes = canonical_json.encode('utf-8')
        
        # Calculate SHA256 hash
        hash_obj = hashlib.sha256(payload_bytes)
        return hash_obj.hexdigest()
    
    def _format_email(self, alert: Dict[str, Any], target: Dict[str, Any], explanation_bundle_id: str) -> Dict[str, Any]:
        """Format email payload."""
        return {
            'type': 'email',
            'to': target.get('target_config', {}).get('email_address', ''),
            'subject': f"RansomEye Alert: {alert.get('severity', 'UNKNOWN')} - {alert.get('alert_id', '')}",
            'body': {
                'alert_id': alert.get('alert_id', ''),
                'incident_id': alert.get('incident_id', ''),
                'severity': alert.get('severity', ''),
                'risk_score': alert.get('risk_score_at_emit', 0),
                'explanation_bundle_id': explanation_bundle_id,
                'emitted_at': alert.get('emitted_at', '')
            }
        }
    
    def _format_webhook(self, alert: Dict[str, Any], target: Dict[str, Any], explanation_bundle_id: str) -> Dict[str, Any]:
        """Format webhook payload."""
        return {
            'type': 'webhook',
            'url': target.get('target_config', {}).get('webhook_url', ''),
            'payload': {
                'alert_id': alert.get('alert_id', ''),
                'incident_id': alert.get('incident_id', ''),
                'severity': alert.get('severity', ''),
                'risk_score': alert.get('risk_score_at_emit', 0),
                'explanation_bundle_id': explanation_bundle_id,
                'emitted_at': alert.get('emitted_at', ''),
                'immutable_hash': alert.get('immutable_hash', '')
            }
        }
    
    def _format_ticket(self, alert: Dict[str, Any], target: Dict[str, Any], explanation_bundle_id: str) -> Dict[str, Any]:
        """Format ticket payload."""
        return {
            'type': 'ticket',
            'system': target.get('target_config', {}).get('ticket_system', ''),
            'title': f"RansomEye Alert: {alert.get('severity', 'UNKNOWN')}",
            'description': {
                'alert_id': alert.get('alert_id', ''),
                'incident_id': alert.get('incident_id', ''),
                'severity': alert.get('severity', ''),
                'risk_score': alert.get('risk_score_at_emit', 0),
                'explanation_bundle_id': explanation_bundle_id
            }
        }
    
    def _format_siem(self, alert: Dict[str, Any], target: Dict[str, Any], explanation_bundle_id: str) -> Dict[str, Any]:
        """Format SIEM payload."""
        return {
            'type': 'siem',
            'format': target.get('target_config', {}).get('siem_format', 'json'),
            'event': {
                'alert_id': alert.get('alert_id', ''),
                'incident_id': alert.get('incident_id', ''),
                'severity': alert.get('severity', ''),
                'risk_score': alert.get('risk_score_at_emit', 0),
                'explanation_bundle_id': explanation_bundle_id,
                'emitted_at': alert.get('emitted_at', ''),
                'immutable_hash': alert.get('immutable_hash', '')
            }
        }
