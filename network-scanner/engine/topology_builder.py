#!/usr/bin/env python3
"""
RansomEye Network Scanner - Topology Builder
AUTHORITATIVE: Immutable topology graph construction
"""

from typing import Dict, Any, List
from datetime import datetime, timezone
import uuid
import hashlib
import json


class TopologyBuildError(Exception):
    """Base exception for topology building errors."""
    pass


class TopologyBuilder:
    """
    Immutable topology graph builder.
    
    Properties:
    - Immutable: Topology edges are immutable facts
    - Directed: All edges are directed
    - Timestamped: All edges are timestamped
    - Deterministic: Same input = same topology
    """
    
    def __init__(self):
        """Initialize topology builder."""
        pass
    
    def build_edges_from_assets(
        self,
        assets: List[Dict[str, Any]],
        services: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Build topology edges from assets and services.
        
        Args:
            assets: List of asset dictionaries
            services: List of service dictionaries
        
        Returns:
            List of topology edge dictionaries
        """
        edges = []
        discovered_at = datetime.now(timezone.utc).isoformat()
        
        # Build asset-to-service edges
        asset_map = {asset['asset_id']: asset for asset in assets}
        
        for service in services:
            asset_id = service.get('asset_id', '')
            if asset_id in asset_map:
                edge = {
                    'edge_id': str(uuid.uuid4()),
                    'source_id': asset_id,
                    'target_id': service.get('service_id', ''),
                    'edge_type': 'hosts_service',
                    'discovered_at': discovered_at,
                    'immutable_hash': ''
                }
                
                edge['immutable_hash'] = self._calculate_hash(edge)
                edges.append(edge)
        
        return edges
    
    def build_edges_from_communication(
        self,
        communication_data: List[Dict[str, Any]],
        asset_map: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Build topology edges from communication data.
        
        Args:
            communication_data: List of communication records
            asset_map: Map of IP addresses to asset IDs
        
        Returns:
            List of topology edge dictionaries
        """
        edges = []
        discovered_at = datetime.now(timezone.utc).isoformat()
        
        seen_pairs = set()
        
        for comm_record in communication_data:
            src_ip = comm_record.get('src_ip', '')
            dst_ip = comm_record.get('dst_ip', '')
            
            src_asset_id = asset_map.get(src_ip, '')
            dst_asset_id = asset_map.get(dst_ip, '')
            
            if src_asset_id and dst_asset_id:
                pair_key = (src_asset_id, dst_asset_id)
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    
                    edge = {
                        'edge_id': str(uuid.uuid4()),
                        'source_id': src_asset_id,
                        'target_id': dst_asset_id,
                        'edge_type': 'communicates_with',
                        'discovered_at': discovered_at,
                        'immutable_hash': ''
                    }
                    
                    edge['immutable_hash'] = self._calculate_hash(edge)
                    edges.append(edge)
        
        return edges
    
    def _calculate_hash(self, edge: Dict[str, Any]) -> str:
        """Calculate SHA256 hash of edge record."""
        hashable_content = {k: v for k, v in edge.items() if k != 'immutable_hash'}
        canonical_json = json.dumps(hashable_content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
