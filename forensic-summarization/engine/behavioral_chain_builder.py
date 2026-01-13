#!/usr/bin/env python3
"""
RansomEye v1.0 Forensic Summarization - Behavioral Chain Builder
AUTHORITATIVE: Deterministic reconstruction of process, file, persistence, and network chains
"""

import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from collections import defaultdict

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    _logger = setup_logging('forensic-summarization-chain-builder')
except ImportError:
    import logging
    _logger = logging.getLogger('forensic-summarization-chain-builder')


class BehavioralChainBuilder:
    """
    Builds behavioral chains from evidence events.
    
    CRITICAL: All chain construction is deterministic (same inputs → same outputs).
    Missing evidence is explicitly marked (gaps in chains).
    """
    
    # Lateral preparation detection thresholds
    NETWORK_SCAN_THRESHOLD = int(os.getenv('RANSOMEYE_LATERAL_NETWORK_SCAN_THRESHOLD', '10'))
    DNS_SCAN_THRESHOLD = int(os.getenv('RANSOMEYE_LATERAL_DNS_SCAN_THRESHOLD', '10'))
    LATERAL_TIME_WINDOW_SECONDS = int(os.getenv('RANSOMEYE_LATERAL_TIME_WINDOW_SECONDS', '60'))
    
    def __init__(self):
        """Initialize behavioral chain builder."""
        pass
    
    def build_all_chains(self, evidence_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build all behavioral chains from evidence events.
        
        Args:
            evidence_events: List of evidence events (from normalized tables)
            
        Returns:
            Dictionary with all behavioral chains
        """
        return {
            'process_lineage': self.build_process_lineage(evidence_events),
            'file_modification': self.build_file_modification_chains(evidence_events),
            'persistence_establishment': self.build_persistence_chains(evidence_events),
            'network_intent_progression': self.build_network_intent_chains(evidence_events),
            'lateral_preparation': self.detect_lateral_preparation(evidence_events)
        }
    
    def build_process_lineage(self, evidence_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Build process lineage tree from process_activity events.
        
        Algorithm:
        1. Find root process (earliest PROCESS_START)
        2. Link processes by parent_pid → process_pid
        3. Build directed tree
        4. Extract chains from root to leaves
        
        Args:
            evidence_events: List of evidence events
            
        Returns:
            List of process lineage chains
        """
        # Filter process_activity events
        process_events = [
            e for e in evidence_events 
            if e.get('table') == 'process_activity' 
            and e.get('activity_type') in ['PROCESS_START', 'PROCESS_EXIT', 'PROCESS_INJECT', 'PROCESS_MODIFY']
        ]
        
        if not process_events:
            return []
        
        # Sort by observed_at (temporal order)
        process_events.sort(key=lambda e: e.get('observed_at', ''))
        
        # Find root process (earliest PROCESS_START)
        root_events = [e for e in process_events if e.get('activity_type') == 'PROCESS_START']
        if not root_events:
            return []
        
        root_event = root_events[0]
        
        # Build process tree
        process_tree = {}
        process_by_pid = {}
        
        # Add root process
        root_pid = root_event.get('process_pid')
        process_tree[root_pid] = {
            'process_pid': root_pid,
            'process_name': root_event.get('process_name', ''),
            'process_path': root_event.get('process_path'),
            'command_line': root_event.get('command_line'),
            'user_name': root_event.get('user_name'),
            'user_id': root_event.get('user_id'),
            'observed_at': root_event.get('observed_at'),
            'event_id': root_event.get('event_id'),
            'table': root_event.get('table'),
            'parent_pid': root_event.get('parent_pid'),
            'child_processes': [],
            'gaps': []
        }
        process_by_pid[root_pid] = process_tree[root_pid]
        
        # Add child processes
        for event in process_events:
            if event.get('activity_type') != 'PROCESS_START':
                continue
            
            process_pid = event.get('process_pid')
            parent_pid = event.get('parent_pid')
            
            if process_pid == root_pid:
                continue  # Skip root (already added)
            
            # Check if parent exists
            if parent_pid is not None and parent_pid not in process_by_pid:
                # Missing parent - mark gap
                if process_pid not in process_tree:
                    process_tree[process_pid] = {
                        'process_pid': process_pid,
                        'process_name': event.get('process_name', ''),
                        'process_path': event.get('process_path'),
                        'command_line': event.get('command_line'),
                        'user_name': event.get('user_name'),
                        'user_id': event.get('user_id'),
                        'observed_at': event.get('observed_at'),
                        'event_id': event.get('event_id'),
                        'table': event.get('table'),
                        'parent_pid': parent_pid,
                        'child_processes': [],
                        'gaps': [f"Missing parent process PID {parent_pid}"]
                    }
                    process_by_pid[process_pid] = process_tree[process_pid]
            else:
                # Parent exists - add as child
                if process_pid not in process_tree:
                    process_tree[process_pid] = {
                        'process_pid': process_pid,
                        'process_name': event.get('process_name', ''),
                        'process_path': event.get('process_path'),
                        'command_line': event.get('command_line'),
                        'user_name': event.get('user_name'),
                        'user_id': event.get('user_id'),
                        'observed_at': event.get('observed_at'),
                        'event_id': event.get('event_id'),
                        'table': event.get('table'),
                        'parent_pid': parent_pid,
                        'child_processes': [],
                        'gaps': []
                    }
                    process_by_pid[process_pid] = process_tree[process_pid]
                
                # Link to parent
                if parent_pid is not None and parent_pid in process_by_pid:
                    process_by_pid[parent_pid]['child_processes'].append(process_tree[process_pid])
        
        # Extract chains (root to leaves)
        chains = []
        
        def extract_chain(process_node: Dict[str, Any], chain: List[Dict[str, Any]]) -> None:
            """Recursively extract chain from process node."""
            chain.append({
                'process_pid': process_node['process_pid'],
                'process_name': process_node['process_name'],
                'process_path': process_node['process_path'],
                'command_line': process_node['command_line'],
                'user_name': process_node['user_name'],
                'user_id': process_node['user_id'],
                'observed_at': process_node['observed_at'],
                'event_id': process_node['event_id'],
                'table': process_node['table'],
                'parent_pid': process_node['parent_pid'],
                'gaps': process_node['gaps']
            })
            
            if not process_node['child_processes']:
                # Leaf node - save chain
                chains.append({
                    'chain_type': 'process_lineage',
                    'root_process': chain[0],
                    'child_processes': chain[1:],
                    'chain_length': len(chain),
                    'time_span_seconds': self._calculate_time_span(chain),
                    'gaps': [g for node in chain for g in node.get('gaps', [])]
                })
            else:
                # Continue with children
                for child in process_node['child_processes']:
                    extract_chain(child, chain.copy())
        
        # Extract chains from root
        extract_chain(process_tree[root_pid], [])
        
        return chains if chains else [{
            'chain_type': 'process_lineage',
            'root_process': {
                'process_pid': root_pid,
                'process_name': root_event.get('process_name', ''),
                'process_path': root_event.get('process_path'),
                'command_line': root_event.get('command_line'),
                'user_name': root_event.get('user_name'),
                'user_id': root_event.get('user_id'),
                'observed_at': root_event.get('observed_at'),
                'event_id': root_event.get('event_id'),
                'table': root_event.get('table'),
                'parent_pid': root_event.get('parent_pid'),
                'gaps': []
            },
            'child_processes': [],
            'chain_length': 1,
            'time_span_seconds': 0,
            'gaps': []
        }]
    
    def build_file_modification_chains(self, evidence_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Build file modification chains from file_activity events.
        
        Algorithm:
        1. Group events by file_path
        2. Order events by observed_at (ascending)
        3. Build sequence of file operations
        4. Detect entropy changes (encryption indicators)
        
        Args:
            evidence_events: List of evidence events
            
        Returns:
            List of file modification chains
        """
        # Filter file_activity events
        file_events = [
            e for e in evidence_events 
            if e.get('table') == 'file_activity'
        ]
        
        if not file_events:
            return []
        
        # Group by file_path (normalize paths)
        file_groups = defaultdict(list)
        for event in file_events:
            file_path = self._normalize_file_path(event.get('file_path', ''))
            if file_path:
                file_groups[file_path].append(event)
        
        chains = []
        
        for file_path, events in file_groups.items():
            # Sort by observed_at (temporal order)
            events.sort(key=lambda e: e.get('observed_at', ''))
            
            # Build operation sequence
            operations = []
            for event in events:
                operation = {
                    'activity_type': event.get('activity_type'),
                    'observed_at': event.get('observed_at'),
                    'event_id': event.get('event_id'),
                    'table': event.get('table'),
                    'process_pid': event.get('process_pid'),
                    'process_name': event.get('process_name'),
                    'file_size': event.get('file_size'),
                    'file_size_before': event.get('file_size_before'),
                    'file_size_after': event.get('file_size_after'),
                    'entropy_change_indicator': event.get('entropy_change_indicator', False)
                }
                
                # Add rename info if applicable
                if event.get('activity_type') == 'FILE_MODIFY' and 'old_path' in event:
                    operation['old_path'] = event.get('old_path')
                    operation['new_path'] = event.get('new_path')
                
                operations.append(operation)
            
            # Calculate time span
            if len(operations) > 1:
                start_time = operations[0].get('observed_at')
                end_time = operations[-1].get('observed_at')
                time_span = self._calculate_time_span_seconds(start_time, end_time)
            else:
                time_span = 0
            
            # Detect encryption
            encryption_detected = any(op.get('entropy_change_indicator', False) for op in operations)
            
            chains.append({
                'chain_type': 'file_modification',
                'file_path': file_path,
                'operations': operations,
                'chain_length': len(operations),
                'time_span_seconds': time_span,
                'encryption_detected': encryption_detected,
                'gaps': []
            })
        
        return chains
    
    def build_persistence_chains(self, evidence_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Build persistence establishment chains from persistence events.
        
        Algorithm:
        1. Group events by persistence_type
        2. Order events by observed_at (ascending)
        3. Build sequence of persistence mechanisms
        
        Args:
            evidence_events: List of evidence events
            
        Returns:
            List of persistence chains
        """
        # Filter persistence events
        persistence_events = [
            e for e in evidence_events 
            if e.get('table') == 'persistence'
        ]
        
        if not persistence_events:
            return []
        
        # Sort by observed_at (temporal order)
        persistence_events.sort(key=lambda e: e.get('observed_at', ''))
        
        # Build persistence mechanisms list
        mechanisms = []
        for event in persistence_events:
            mechanism = {
                'persistence_type': event.get('persistence_type'),
                'persistence_key': event.get('persistence_key', ''),
                'target_path': event.get('target_path', ''),
                'target_command_line': event.get('target_command_line'),
                'observed_at': event.get('observed_at'),
                'event_id': event.get('event_id'),
                'table': event.get('table'),
                'process_pid': event.get('process_pid'),
                'process_name': event.get('process_name', ''),
                'enabled': event.get('enabled', True)
            }
            mechanisms.append(mechanism)
        
        # Calculate time span
        if len(mechanisms) > 1:
            start_time = mechanisms[0].get('observed_at')
            end_time = mechanisms[-1].get('observed_at')
            time_span = self._calculate_time_span_seconds(start_time, end_time)
        else:
            time_span = 0
        
        return [{
            'chain_type': 'persistence_establishment',
            'persistence_mechanisms': mechanisms,
            'chain_length': len(mechanisms),
            'time_span_seconds': time_span,
            'gaps': []
        }]
    
    def build_network_intent_chains(self, evidence_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Build network intent progression chains from network_intent and dpi_flows events.
        
        Algorithm:
        1. Group events by intent_type
        2. Order events by observed_at (ascending)
        3. Correlate network_intent with dpi_flows (by IP, port, timestamp)
        
        Args:
            evidence_events: List of evidence events
            
        Returns:
            List of network intent chains
        """
        # Filter network_intent events
        network_intent_events = [
            e for e in evidence_events 
            if e.get('table') == 'network_intent'
        ]
        
        # Filter dpi_flows events
        dpi_flow_events = [
            e for e in evidence_events 
            if e.get('table') == 'dpi_flows'
        ]
        
        if not network_intent_events:
            return []
        
        # Sort by observed_at (temporal order)
        network_intent_events.sort(key=lambda e: e.get('observed_at', ''))
        
        # Build network activities list
        activities = []
        for intent_event in network_intent_events:
            activity = {
                'intent_type': intent_event.get('intent_type'),
                'observed_at': intent_event.get('observed_at'),
                'event_id': intent_event.get('event_id'),
                'table': intent_event.get('table'),
                'process_pid': intent_event.get('process_pid'),
                'process_name': intent_event.get('process_name', ''),
                'remote_host': intent_event.get('remote_host'),
                'remote_port': intent_event.get('remote_port'),
                'local_port': intent_event.get('local_port'),
                'protocol': intent_event.get('protocol'),
                'dns_query_name': intent_event.get('dns_query_name')
            }
            
            # Correlate with DPI flows (by IP, port, timestamp ±5 seconds)
            correlated_flow = self._correlate_dpi_flow(intent_event, dpi_flow_events)
            if correlated_flow:
                activity['correlated_flow'] = {
                    'flow_id': correlated_flow.get('event_id'),
                    'table': 'dpi_flows',
                    'bytes_sent': correlated_flow.get('bytes_sent', 0),
                    'bytes_received': correlated_flow.get('bytes_received', 0),
                    'packets_sent': correlated_flow.get('packets_sent', 0),
                    'packets_received': correlated_flow.get('packets_received', 0),
                    'application_protocol': correlated_flow.get('application_protocol')
                }
            
            activities.append(activity)
        
        # Calculate time span
        if len(activities) > 1:
            start_time = activities[0].get('observed_at')
            end_time = activities[-1].get('observed_at')
            time_span = self._calculate_time_span_seconds(start_time, end_time)
        else:
            time_span = 0
        
        return [{
            'chain_type': 'network_intent_progression',
            'network_activities': activities,
            'chain_length': len(activities),
            'time_span_seconds': time_span,
            'gaps': []
        }]
    
    def detect_lateral_preparation(self, evidence_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect lateral movement preparation indicators.
        
        Algorithm:
        1. Credential access detection (LSASS access, registry credential access)
        2. Network scanning detection (>10 connection attempts to different hosts)
        3. Service discovery detection (>10 DNS queries to different domains)
        
        Args:
            evidence_events: List of evidence events
            
        Returns:
            List of lateral preparation indicators
        """
        indicators = []
        
        # 1. Credential access detection
        process_events = [
            e for e in evidence_events 
            if e.get('table') == 'process_activity'
        ]
        
        for event in process_events:
            # Check for LSASS access
            target_process_name = event.get('target_process_name', '').lower()
            if 'lsass' in target_process_name and event.get('activity_type') in ['PROCESS_INJECT', 'PROCESS_MODIFY']:
                indicators.append({
                    'indicator_type': 'CREDENTIAL_ACCESS',
                    'description': f"Process accessed {target_process_name} memory",
                    'process_pid': event.get('process_pid'),
                    'process_name': event.get('process_name', ''),
                    'target_pid': event.get('target_pid'),
                    'target_process_name': event.get('target_process_name', ''),
                    'observed_at': event.get('observed_at'),
                    'event_id': event.get('event_id'),
                    'table': event.get('table')
                })
            
            # Check for registry credential access (via file_activity on registry hives)
            # This would require file_activity events with registry paths
        
        # 2. Network scanning detection
        network_intent_events = [
            e for e in evidence_events 
            if e.get('table') == 'network_intent' 
            and e.get('intent_type') == 'CONNECTION_ATTEMPT'
        ]
        
        if len(network_intent_events) >= self.NETWORK_SCAN_THRESHOLD:
            # Group by time window
            time_windows = defaultdict(list)
            for event in network_intent_events:
                observed_at = event.get('observed_at', '')
                if observed_at:
                    # Round to time window
                    try:
                        dt = datetime.fromisoformat(observed_at.replace('Z', '+00:00'))
                        window_start = dt.replace(second=0, microsecond=0)
                        time_windows[window_start.isoformat()].append(event)
                    except Exception:
                        continue
            
            # Check for scanning pattern (>10 unique hosts in time window)
            for window_start, events in time_windows.items():
                unique_hosts = set()
                for event in events:
                    remote_host = event.get('remote_host')
                    if remote_host:
                        unique_hosts.add(remote_host)
                
                if len(unique_hosts) >= self.NETWORK_SCAN_THRESHOLD:
                    event_ids = [e.get('event_id') for e in events]
                    indicators.append({
                        'indicator_type': 'NETWORK_SCANNING',
                        'description': f"Multiple connection attempts to different hosts",
                        'connection_attempts': len(events),
                        'unique_hosts': len(unique_hosts),
                        'time_window_seconds': self.LATERAL_TIME_WINDOW_SECONDS,
                        'observed_at': events[0].get('observed_at'),
                        'event_ids': event_ids,
                        'table': 'network_intent'
                    })
        
        # 3. Service discovery detection
        dns_events = [
            e for e in evidence_events 
            if e.get('table') == 'network_intent' 
            and e.get('intent_type') == 'DNS_QUERY'
        ]
        
        if len(dns_events) >= self.DNS_SCAN_THRESHOLD:
            # Group by time window
            time_windows = defaultdict(list)
            for event in dns_events:
                observed_at = event.get('observed_at', '')
                if observed_at:
                    try:
                        dt = datetime.fromisoformat(observed_at.replace('Z', '+00:00'))
                        window_start = dt.replace(second=0, microsecond=0)
                        time_windows[window_start.isoformat()].append(event)
                    except Exception:
                        continue
            
            # Check for scanning pattern (>10 unique domains in time window)
            for window_start, events in time_windows.items():
                unique_domains = set()
                for event in events:
                    dns_query_name = event.get('dns_query_name')
                    if dns_query_name:
                        unique_domains.add(dns_query_name)
                
                if len(unique_domains) >= self.DNS_SCAN_THRESHOLD:
                    event_ids = [e.get('event_id') for e in events]
                    indicators.append({
                        'indicator_type': 'SERVICE_DISCOVERY',
                        'description': f"Multiple DNS queries to different domains",
                        'dns_queries': len(events),
                        'unique_domains': len(unique_domains),
                        'time_window_seconds': self.LATERAL_TIME_WINDOW_SECONDS,
                        'observed_at': events[0].get('observed_at'),
                        'event_ids': event_ids,
                        'table': 'network_intent'
                    })
        
        return [{
            'chain_type': 'lateral_preparation',
            'indicators': indicators,
            'chain_length': len(indicators),
            'time_span_seconds': self._calculate_time_span_seconds(
                indicators[0].get('observed_at') if indicators else None,
                indicators[-1].get('observed_at') if indicators else None
            ) if indicators else 0,
            'gaps': []
        }] if indicators else []
    
    def _normalize_file_path(self, file_path: str) -> str:
        """Normalize file path (case-insensitive on Windows, case-sensitive on Linux)."""
        if not file_path:
            return ""
        
        # For now, assume case-sensitive (Linux)
        # In production, detect OS and normalize accordingly
        return file_path
    
    def _correlate_dpi_flow(
        self, 
        intent_event: Dict[str, Any], 
        dpi_flow_events: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Correlate network_intent event with dpi_flows event.
        
        Matching criteria:
        - IP address match (remote_host/remote_ip)
        - Port match (remote_port)
        - Time window (±5 seconds)
        """
        if not dpi_flow_events:
            return None
        
        intent_remote_host = intent_event.get('remote_host')
        intent_remote_port = intent_event.get('remote_port')
        intent_observed_at = intent_event.get('observed_at')
        
        if not intent_observed_at:
            return None
        
        try:
            intent_time = datetime.fromisoformat(intent_observed_at.replace('Z', '+00:00'))
        except Exception:
            return None
        
        # Find matching DPI flow
        for flow_event in dpi_flow_events:
            flow_remote_ip = flow_event.get('remote_ip')
            flow_remote_port = flow_event.get('remote_port')
            flow_observed_at = flow_event.get('observed_at')
            
            if not flow_observed_at:
                continue
            
            try:
                flow_time = datetime.fromisoformat(flow_observed_at.replace('Z', '+00:00'))
            except Exception:
                continue
            
            # Check time window (±5 seconds)
            time_diff = abs((intent_time - flow_time).total_seconds())
            if time_diff > 5:
                continue
            
            # Check IP match
            if intent_remote_host and flow_remote_ip:
                if str(intent_remote_host) != str(flow_remote_ip):
                    continue
            
            # Check port match
            if intent_remote_port and flow_remote_port:
                if intent_remote_port != flow_remote_port:
                    continue
            
            # Match found
            return flow_event
        
        return None
    
    def _calculate_time_span(self, chain: List[Dict[str, Any]]) -> int:
        """Calculate time span in seconds for a chain."""
        if len(chain) < 2:
            return 0
        
        start_time = chain[0].get('observed_at')
        end_time = chain[-1].get('observed_at')
        return self._calculate_time_span_seconds(start_time, end_time)
    
    def _calculate_time_span_seconds(
        self, 
        start_time: Optional[str], 
        end_time: Optional[str]
    ) -> int:
        """Calculate time span in seconds between two timestamps."""
        if not start_time or not end_time:
            return 0
        
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            return int((end_dt - start_dt).total_seconds())
        except Exception:
            return 0
