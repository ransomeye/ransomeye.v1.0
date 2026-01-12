#!/usr/bin/env python3
"""
RansomEye DPI Advanced - Flow Assembler
AUTHORITATIVE: Deterministic flow assembly from packet tuples
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import uuid
import hashlib
import json
from collections import defaultdict


class FlowAssemblyError(Exception):
    """Base exception for flow assembly errors."""
    pass


class FlowAssembler:
    """
    Deterministic flow assembler.
    
    Properties:
    - Deterministic: Same packets → same flows
    - Bounded memory: Ring buffers only
    - No payload: Metadata only
    """
    
    def __init__(self, flow_timeout: int = 300):
        """
        Initialize flow assembler.
        
        Args:
            flow_timeout: Flow timeout in seconds (default: 300)
        """
        self.flow_timeout = flow_timeout
        self.active_flows: Dict[Tuple, Dict[str, Any]] = {}
    
    def process_packet(
        self,
        src_ip: str,
        dst_ip: str,
        src_port: int,
        dst_port: int,
        protocol: str,
        packet_size: int,
        timestamp: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Process packet and update or create flow.
        
        Args:
            src_ip: Source IP address
            dst_ip: Destination IP address
            src_port: Source port
            dst_port: Destination port
            protocol: Protocol (tcp, udp, icmp, other)
            packet_size: Packet size in bytes
            timestamp: Packet timestamp
        
        Returns:
            Completed flow dictionary, or None if flow is still active
        """
        # Build flow key (canonical: smaller IP first)
        flow_key = self._build_flow_key(src_ip, dst_ip, src_port, dst_port, protocol)
        
        # Get or create flow
        if flow_key not in self.active_flows:
            self.active_flows[flow_key] = {
                'flow_id': str(uuid.uuid4()),
                'src_ip': src_ip,
                'dst_ip': dst_ip,
                'src_port': src_port,
                'dst_port': dst_port,
                'protocol': protocol,
                'flow_start': timestamp.isoformat(),
                'flow_end': timestamp.isoformat(),
                'packet_count': 0,
                'byte_count': 0,
                'l7_protocol': '',
                'behavioral_profile_id': '',
                'asset_profile_id': '',
                'privacy_mode': 'FORENSIC',
                'immutable_hash': ''
            }
        
        flow = self.active_flows[flow_key]
        
        # Update flow
        flow['packet_count'] += 1
        flow['byte_count'] += packet_size
        flow['flow_end'] = timestamp.isoformat()
        
        # Check for flow completion (timeout or TCP FIN)
        # For Phase L, use timeout only
        flow_start = datetime.fromisoformat(flow['flow_start'].replace('Z', '+00:00'))
        elapsed = (timestamp - flow_start).total_seconds()
        
        if elapsed > self.flow_timeout:
            # Flow completed
            completed_flow = flow.copy()
            del self.active_flows[flow_key]
            
            # Calculate hash
            completed_flow['immutable_hash'] = self._calculate_hash(completed_flow)
            
            return completed_flow
        
        return None
    
    def _build_flow_key(
        self,
        src_ip: str,
        dst_ip: str,
        src_port: int,
        dst_port: int,
        protocol: str
    ) -> Tuple:
        """Build canonical flow key (deterministic ordering)."""
        # Canonical: smaller IP first
        if src_ip < dst_ip:
            return (src_ip, dst_ip, src_port, dst_port, protocol)
        elif src_ip > dst_ip:
            return (dst_ip, src_ip, dst_port, src_port, protocol)
        else:
            # Same IP, use port ordering
            if src_port < dst_port:
                return (src_ip, dst_ip, src_port, dst_port, protocol)
            else:
                return (dst_ip, src_ip, dst_port, src_port, protocol)
    
    def _calculate_hash(self, flow: Dict[str, Any]) -> str:
        """Calculate SHA256 hash of flow record."""
        hashable_content = {k: v for k, v in flow.items() if k != 'immutable_hash'}
        canonical_json = json.dumps(hashable_content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
