#!/usr/bin/env python3
"""
RansomEye Network Scanner - Passive Discoverer
AUTHORITATIVE: Passive network discovery from DPI/flow data
"""

from typing import Dict, Any, List
from datetime import datetime, timezone
import uuid
import hashlib
import json


class PassiveDiscoveryError(Exception):
    """Base exception for passive discovery errors."""
    pass


class PassiveDiscoverer:
    """
    Passive network discoverer.
    
    Properties:
    - Read-only: Consumes DPI/flow data, no packet crafting
    - No injection: No packet injection
    - Deterministic: Same input = same output
    """
    
    def __init__(self):
        """Initialize passive discoverer."""
        pass
    
    def discover_from_dpi(self, dpi_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Discover assets from DPI probe outputs.
        
        Args:
            dpi_data: List of DPI probe output dictionaries
        
        Returns:
            List of asset dictionaries
        """
        assets = []
        discovered_at = datetime.now(timezone.utc).isoformat()
        
        seen_ips = set()
        
        for dpi_record in dpi_data:
            # Extract IP addresses from DPI data
            src_ip = dpi_record.get('src_ip', '')
            dst_ip = dpi_record.get('dst_ip', '')
            
            for ip in [src_ip, dst_ip]:
                if ip and ip not in seen_ips:
                    seen_ips.add(ip)
                    
                    asset = {
                        'asset_id': str(uuid.uuid4()),
                        'ip_address': ip,
                        'mac_address': dpi_record.get('src_mac', '') if ip == src_ip else dpi_record.get('dst_mac', ''),
                        'hostname': '',
                        'discovery_method': 'passive_dpi',
                        'discovered_at': discovered_at,
                        'last_seen_at': discovered_at,
                        'immutable_hash': ''
                    }
                    
                    # Calculate hash
                    asset['immutable_hash'] = self._calculate_hash(asset)
                    assets.append(asset)
        
        return assets
    
    def discover_from_flow(self, flow_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Discover assets from flow metadata.
        
        Args:
            flow_data: List of flow metadata dictionaries
        
        Returns:
            List of asset dictionaries
        """
        assets = []
        discovered_at = datetime.now(timezone.utc).isoformat()
        
        seen_ips = set()
        
        for flow_record in flow_data:
            # Extract IP addresses from flow data
            src_ip = flow_record.get('src_ip', '')
            dst_ip = flow_record.get('dst_ip', '')
            
            for ip in [src_ip, dst_ip]:
                if ip and ip not in seen_ips:
                    seen_ips.add(ip)
                    
                    asset = {
                        'asset_id': str(uuid.uuid4()),
                        'ip_address': ip,
                        'mac_address': '',
                        'hostname': '',
                        'discovery_method': 'passive_flow',
                        'discovered_at': discovered_at,
                        'last_seen_at': discovered_at,
                        'immutable_hash': ''
                    }
                    
                    # Calculate hash
                    asset['immutable_hash'] = self._calculate_hash(asset)
                    assets.append(asset)
        
        return assets
    
    def _calculate_hash(self, asset: Dict[str, Any]) -> str:
        """Calculate SHA256 hash of asset record."""
        hashable_content = {k: v for k, v in asset.items() if k != 'immutable_hash'}
        canonical_json = json.dumps(hashable_content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
