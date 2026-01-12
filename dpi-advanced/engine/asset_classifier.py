#!/usr/bin/env python3
"""
RansomEye DPI Advanced - Asset Classifier
AUTHORITATIVE: Deterministic asset classification (device type and role)
"""

from typing import Dict, Any, List
from datetime import datetime, timezone
import uuid
import hashlib
import json
from collections import defaultdict


class AssetClassificationError(Exception):
    """Base exception for asset classification errors."""
    pass


class AssetClassifier:
    """
    Deterministic asset classifier.
    
    Properties:
    - Deterministic: Same flows → same classification
    - Explainable: All classifications are explainable
    - Replayable: Classifications can be replayed
    """
    
    def __init__(self):
        """Initialize asset classifier."""
        self.profiles = {}  # asset_ip -> profile
    
    def classify_asset(
        self,
        asset_ip: str,
        flows: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Classify asset based on flow behavior.
        
        Args:
            asset_ip: Asset IP address
            flows: List of flows involving this asset
        
        Returns:
            Asset profile dictionary
        """
        # Extract classification features
        features = self._extract_classification_features(asset_ip, flows)
        
        # Classify device type
        device_type = self._classify_device_type(features)
        
        # Classify role
        role = self._classify_role(features)
        
        # Calculate confidence
        confidence = self._calculate_confidence(features, device_type, role)
        
        # Create or update profile
        if asset_ip not in self.profiles:
            self.profiles[asset_ip] = {
                'profile_id': str(uuid.uuid4()),
                'asset_ip': asset_ip,
                'device_type': device_type,
                'role': role,
                'confidence': confidence,
                'classification_features': features,
                'first_seen': datetime.now(timezone.utc).isoformat(),
                'last_seen': datetime.now(timezone.utc).isoformat(),
                'immutable_hash': ''
            }
        else:
            # Update existing profile
            profile = self.profiles[asset_ip]
            profile['device_type'] = device_type
            profile['role'] = role
            profile['confidence'] = confidence
            profile['classification_features'] = features
            profile['last_seen'] = datetime.now(timezone.utc).isoformat()
        
        profile = self.profiles[asset_ip]
        
        # Calculate hash
        profile['immutable_hash'] = self._calculate_hash(profile)
        
        return profile
    
    def _extract_classification_features(
        self,
        asset_ip: str,
        flows: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract features for classification."""
        # Port behavior
        ports = set()
        protocols = set()
        inbound_count = 0
        outbound_count = 0
        
        for flow in flows:
            if flow.get('src_ip') == asset_ip:
                outbound_count += 1
                ports.add(flow.get('dst_port', 0))
            else:
                inbound_count += 1
                ports.add(flow.get('src_port', 0))
            
            protocols.add(flow.get('protocol', ''))
            if flow.get('l7_protocol'):
                protocols.add(flow.get('l7_protocol', ''))
        
        features = {
            'unique_ports': len(ports),
            'unique_protocols': len(protocols),
            'inbound_flows': inbound_count,
            'outbound_flows': outbound_count,
            'common_ports': sorted(list(ports))[:10],  # Top 10 ports
            'protocols': sorted(list(protocols))
        }
        
        return features
    
    def _classify_device_type(self, features: Dict[str, Any]) -> str:
        """Classify device type based on features."""
        unique_ports = features.get('unique_ports', 0)
        protocols = features.get('protocols', [])
        
        # Deterministic classification rules
        if 'tcp' in protocols and 'udp' in protocols:
            if unique_ports > 50:
                return 'server'
            elif unique_ports > 10:
                return 'workstation'
            else:
                return 'iot'
        elif 'tcp' in protocols:
            if unique_ports > 20:
                return 'server'
            else:
                return 'workstation'
        else:
            return 'network_device'
    
    def _classify_role(self, features: Dict[str, Any]) -> str:
        """Classify role based on features."""
        common_ports = features.get('common_ports', [])
        protocols = features.get('protocols', [])
        
        # Deterministic role classification
        if 3306 in common_ports or 5432 in common_ports:
            return 'database'
        elif 389 in common_ports or 636 in common_ports:
            return 'domain_controller'
        elif 3128 in common_ports or 8080 in common_ports:
            return 'proxy'
        elif 9100 in common_ports or 515 in common_ports:
            return 'printer'
        elif 80 in common_ports or 443 in common_ports:
            return 'web_server'
        elif 25 in common_ports or 587 in common_ports:
            return 'mail_server'
        elif 53 in common_ports:
            return 'dns_server'
        else:
            return 'unknown'
    
    def _calculate_confidence(
        self,
        features: Dict[str, Any],
        device_type: str,
        role: str
    ) -> float:
        """Calculate classification confidence."""
        confidence = 0.5  # Base confidence
        
        # Increase confidence based on feature quality
        if features.get('unique_ports', 0) > 5:
            confidence += 0.2
        
        if features.get('unique_protocols', 0) > 1:
            confidence += 0.2
        
        if role != 'unknown':
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _calculate_hash(self, profile: Dict[str, Any]) -> str:
        """Calculate SHA256 hash of asset profile."""
        hashable_content = {k: v for k, v in profile.items() if k != 'immutable_hash'}
        canonical_json = json.dumps(hashable_content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
