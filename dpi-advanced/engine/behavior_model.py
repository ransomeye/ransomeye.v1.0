#!/usr/bin/env python3
"""
RansomEye DPI Advanced - Behavior Model
AUTHORITATIVE: Flow-level behavioral ML (local, bounded, explainable)
"""

from typing import Dict, Any, List
from datetime import datetime, timezone
import uuid
import hashlib
import json


class BehaviorModelError(Exception):
    """Base exception for behavior model errors."""
    pass


class BehaviorModel:
    """
    Flow-level behavioral model.
    
    Properties:
    - Local: All processing is local
    - Bounded: Bounded computation
    - Explainable: All features are explainable
    - Metadata only: No payload inspection
    """
    
    def __init__(self):
        """Initialize behavior model."""
        self.profiles = {}  # profile_id -> profile data
    
    def analyze_flow(self, flow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze flow and generate behavioral profile.
        
        Args:
            flow: Flow dictionary
        
        Returns:
            Behavioral profile dictionary
        """
        # Extract features (metadata only)
        features = self._extract_features(flow)
        
        # Generate behavioral profile ID (deterministic)
        profile_id = self._generate_profile_id(features)
        
        # Create or update profile
        if profile_id not in self.profiles:
            self.profiles[profile_id] = {
                'profile_id': profile_id,
                'features': features,
                'confidence': self._calculate_confidence(features),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
        
        return self.profiles[profile_id]
    
    def _extract_features(self, flow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract behavioral features from flow metadata.
        
        Features:
        - Packet size distribution
        - Timing patterns
        - Protocol flags
        - Flow directionality
        
        No payload inspection.
        """
        packet_count = flow.get('packet_count', 0)
        byte_count = flow.get('byte_count', 0)
        protocol = flow.get('protocol', '')
        
        # Calculate average packet size
        avg_packet_size = byte_count / packet_count if packet_count > 0 else 0
        
        # Extract timing features (stub for Phase L)
        # In production, would analyze inter-packet timing
        
        features = {
            'packet_count': packet_count,
            'byte_count': byte_count,
            'avg_packet_size': avg_packet_size,
            'protocol': protocol,
            'l7_protocol': flow.get('l7_protocol', ''),
            'flow_duration': self._calculate_duration(flow)
        }
        
        return features
    
    def _calculate_duration(self, flow: Dict[str, Any]) -> float:
        """Calculate flow duration in seconds."""
        try:
            start = datetime.fromisoformat(flow['flow_start'].replace('Z', '+00:00'))
            end = datetime.fromisoformat(flow['flow_end'].replace('Z', '+00:00'))
            return (end - start).total_seconds()
        except Exception:
            return 0.0
    
    def _generate_profile_id(self, features: Dict[str, Any]) -> str:
        """
        Generate deterministic profile ID from features.
        
        Args:
            features: Feature dictionary
        
        Returns:
            Profile ID (UUID v5 based on features)
        """
        # Create deterministic profile ID from features
        feature_json = json.dumps(features, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        feature_hash = hashlib.sha256(feature_json.encode('utf-8')).hexdigest()
        
        # Use first 32 chars as UUID (deterministic)
        profile_uuid = uuid.UUID(hex=feature_hash[:32])
        return str(profile_uuid)
    
    def _calculate_confidence(self, features: Dict[str, Any]) -> float:
        """
        Calculate confidence in behavioral profile.
        
        Args:
            features: Feature dictionary
        
        Returns:
            Confidence value (0.0 to 1.0)
        """
        # Simple confidence calculation based on feature completeness
        # In production, would use more sophisticated model
        confidence = 0.5  # Base confidence
        
        if features.get('packet_count', 0) > 10:
            confidence += 0.2
        
        if features.get('l7_protocol'):
            confidence += 0.2
        
        if features.get('flow_duration', 0) > 1.0:
            confidence += 0.1
        
        return min(confidence, 1.0)
