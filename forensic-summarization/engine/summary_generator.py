#!/usr/bin/env python3
"""
RansomEye v1.0 Forensic Summarization - Summary Generator
AUTHORITATIVE: Template-based text generation (non-LLM, deterministic)
"""

import os
import sys
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    _logger = setup_logging('forensic-summarization-summary-generator')
except ImportError:
    import logging
    _logger = logging.getLogger('forensic-summarization-summary-generator')


class SummaryGenerator:
    """
    Generates forensic summaries in JSON, text, and graph formats.
    
    CRITICAL: Text generation is template-based (deterministic, no LLM).
    No adjectives, no inference language, no mitigation advice.
    """
    
    def __init__(self):
        """Initialize summary generator."""
        pass
    
    def generate_summary(
        self,
        incident_id: str,
        machine_id: str,
        behavioral_chains: Dict[str, Any],
        temporal_phases: Dict[str, Any],
        evidence_links: Dict[str, Any],
        time_range: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Generate complete forensic summary.
        
        Args:
            incident_id: Incident identifier
            machine_id: Machine identifier
            behavioral_chains: Dictionary with all behavioral chains
            temporal_phases: Dictionary with temporal phases
            evidence_links: Dictionary with evidence links
            time_range: Dictionary with start_time and end_time
            
        Returns:
            Dictionary with JSON, text, and graph metadata summaries
        """
        summary_id = str(uuid.uuid4())
        generated_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        # Generate JSON summary
        json_summary = self.generate_json_summary(
            summary_id=summary_id,
            incident_id=incident_id,
            machine_id=machine_id,
            behavioral_chains=behavioral_chains,
            temporal_phases=temporal_phases,
            evidence_links=evidence_links,
            time_range=time_range,
            generated_at=generated_at
        )
        
        # Generate text summary
        text_summary = self.generate_text_summary(
            incident_id=incident_id,
            machine_id=machine_id,
            behavioral_chains=behavioral_chains,
            temporal_phases=temporal_phases,
            evidence_links=evidence_links,
            time_range=time_range
        )
        
        # Generate graph metadata
        graph_metadata = self.generate_graph_metadata(
            behavioral_chains=behavioral_chains,
            evidence_links=evidence_links
        )
        
        return {
            'summary_id': summary_id,
            'incident_id': incident_id,
            'machine_id': machine_id,
            'generated_at': generated_at,
            'json_summary': json_summary,
            'text_summary': text_summary,
            'graph_metadata': graph_metadata
        }
    
    def generate_json_summary(
        self,
        summary_id: str,
        incident_id: str,
        machine_id: str,
        behavioral_chains: Dict[str, Any],
        temporal_phases: Dict[str, Any],
        evidence_links: Dict[str, Any],
        time_range: Dict[str, str],
        generated_at: str
    ) -> Dict[str, Any]:
        """Generate JSON summary."""
        # Calculate statistics
        total_events = temporal_phases.get('total_event_count', 0)
        total_processes = sum(
            len(chain.get('child_processes', [])) + 1 
            for chain in behavioral_chains.get('process_lineage', [])
        )
        total_files = len(behavioral_chains.get('file_modification', []))
        total_persistence = sum(
            len(chain.get('persistence_mechanisms', []))
            for chain in behavioral_chains.get('persistence_establishment', [])
        )
        total_network = sum(
            len(chain.get('network_activities', []))
            for chain in behavioral_chains.get('network_intent_progression', [])
        )
        
        return {
            'summary_id': summary_id,
            'incident_id': incident_id,
            'machine_id': machine_id,
            'generated_at': generated_at,
            'time_range': time_range,
            'behavioral_chains': behavioral_chains,
            'temporal_phases': temporal_phases,
            'evidence_links': evidence_links,
            'statistics': {
                'total_events': total_events,
                'total_processes': total_processes,
                'total_files': total_files,
                'total_persistence_mechanisms': total_persistence,
                'total_network_activities': total_network
            }
        }
    
    def generate_text_summary(
        self,
        incident_id: str,
        machine_id: str,
        behavioral_chains: Dict[str, Any],
        temporal_phases: Dict[str, Any],
        evidence_links: Dict[str, Any],
        time_range: Dict[str, str]
    ) -> str:
        """Generate text summary (template-based, deterministic)."""
        lines = []
        
        # Header
        lines.append("FORENSIC SUMMARY")
        lines.append("=" * 80)
        lines.append(f"Incident ID: {incident_id}")
        lines.append(f"Machine ID: {machine_id}")
        lines.append(f"Time Range: {time_range.get('start_time')} to {time_range.get('end_time')}")
        lines.append(f"Duration: {temporal_phases.get('total_duration_seconds', 0)} seconds")
        lines.append("")
        
        # Timeline
        lines.append("TIMELINE")
        lines.append("-" * 80)
        all_events = []
        
        # Collect all events from chains
        for chain in behavioral_chains.get('process_lineage', []):
            root = chain.get('root_process', {})
            if root:
                all_events.append({
                    'observed_at': root.get('observed_at'),
                    'description': f"Process {root.get('process_pid')} ({root.get('process_name')}) started",
                    'event_id': root.get('event_id'),
                    'table': root.get('table')
                })
            for child in chain.get('child_processes', []):
                all_events.append({
                    'observed_at': child.get('observed_at'),
                    'description': f"Process {child.get('process_pid')} ({child.get('process_name')}) started, parent PID {child.get('parent_pid')}",
                    'event_id': child.get('event_id'),
                    'table': child.get('table')
                })
        
        for chain in behavioral_chains.get('file_modification', []):
            file_path = chain.get('file_path', '')
            for op in chain.get('operations', []):
                activity_type = op.get('activity_type', '')
                entropy_note = " (entropy change detected)" if op.get('entropy_change_indicator') else ""
                all_events.append({
                    'observed_at': op.get('observed_at'),
                    'description': f"File {file_path} {activity_type}{entropy_note} by process {op.get('process_pid')} ({op.get('process_name')})",
                    'event_id': op.get('event_id'),
                    'table': op.get('table')
                })
        
        for chain in behavioral_chains.get('persistence_establishment', []):
            for mechanism in chain.get('persistence_mechanisms', []):
                persistence_type = mechanism.get('persistence_type', '')
                persistence_key = mechanism.get('persistence_key', '')
                all_events.append({
                    'observed_at': mechanism.get('observed_at'),
                    'description': f"Persistence mechanism {persistence_type} established: {persistence_key}",
                    'event_id': mechanism.get('event_id'),
                    'table': mechanism.get('table')
                })
        
        for chain in behavioral_chains.get('network_intent_progression', []):
            for activity in chain.get('network_activities', []):
                intent_type = activity.get('intent_type', '')
                if intent_type == 'DNS_QUERY':
                    dns_query_name = activity.get('dns_query_name', '')
                    all_events.append({
                        'observed_at': activity.get('observed_at'),
                        'description': f"DNS query for {dns_query_name} by process {activity.get('process_pid')} ({activity.get('process_name')})",
                        'event_id': activity.get('event_id'),
                        'table': activity.get('table')
                    })
                elif intent_type == 'CONNECTION_ATTEMPT':
                    remote_host = activity.get('remote_host', '')
                    remote_port = activity.get('remote_port', '')
                    all_events.append({
                        'observed_at': activity.get('observed_at'),
                        'description': f"Connection attempt to {remote_host}:{remote_port} by process {activity.get('process_pid')} ({activity.get('process_name')})",
                        'event_id': activity.get('event_id'),
                        'table': activity.get('table')
                    })
        
        # Sort by observed_at
        all_events.sort(key=lambda e: e.get('observed_at', ''))
        
        # Write timeline
        for event in all_events:
            lines.append(f"{event['observed_at']}: {event['description']} [event_id: {event['event_id']}, table: {event['table']}]")
        
        lines.append("")
        
        # Behavioral Chains
        lines.append("BEHAVIORAL CHAINS")
        lines.append("-" * 80)
        
        # Process Lineage
        process_chains = behavioral_chains.get('process_lineage', [])
        if process_chains:
            lines.append("Process Lineage:")
            for chain in process_chains:
                root = chain.get('root_process', {})
                if root:
                    lines.append(f"  Root: Process {root.get('process_pid')} ({root.get('process_name')}) [event_id: {root.get('event_id')}, table: {root.get('table')}, timestamp: {root.get('observed_at')}]")
                for child in chain.get('child_processes', []):
                    lines.append(f"  Child: Process {child.get('process_pid')} ({child.get('process_name')}), parent PID {child.get('parent_pid')} [event_id: {child.get('event_id')}, table: {child.get('table')}, timestamp: {child.get('observed_at')}]")
            lines.append("")
        
        # File Modification
        file_chains = behavioral_chains.get('file_modification', [])
        if file_chains:
            lines.append("File Modification:")
            for chain in file_chains:
                file_path = chain.get('file_path', '')
                lines.append(f"  File: {file_path}")
                lines.append("  Operations:")
                for op in chain.get('operations', []):
                    activity_type = op.get('activity_type', '')
                    entropy_note = " (entropy change)" if op.get('entropy_change_indicator') else ""
                    lines.append(f"    - {activity_type}{entropy_note} [event_id: {op.get('event_id')}, table: {op.get('table')}, timestamp: {op.get('observed_at')}]")
            lines.append("")
        
        # Persistence
        persistence_chains = behavioral_chains.get('persistence_establishment', [])
        if persistence_chains:
            lines.append("Persistence Establishment:")
            for chain in persistence_chains:
                for mechanism in chain.get('persistence_mechanisms', []):
                    persistence_type = mechanism.get('persistence_type', '')
                    persistence_key = mechanism.get('persistence_key', '')
                    lines.append(f"  Mechanism: {persistence_type}")
                    lines.append(f"  Key: {persistence_key}")
                    lines.append(f"  Target: {mechanism.get('target_path')} [event_id: {mechanism.get('event_id')}, table: {mechanism.get('table')}, timestamp: {mechanism.get('observed_at')}]")
            lines.append("")
        
        # Network Intent
        network_chains = behavioral_chains.get('network_intent_progression', [])
        if network_chains:
            lines.append("Network Intent Progression:")
            for chain in network_chains:
                for activity in chain.get('network_activities', []):
                    intent_type = activity.get('intent_type', '')
                    if intent_type == 'DNS_QUERY':
                        dns_query_name = activity.get('dns_query_name', '')
                        lines.append(f"  - DNS query: {dns_query_name} [event_id: {activity.get('event_id')}, table: {activity.get('table')}, timestamp: {activity.get('observed_at')}]")
                    elif intent_type == 'CONNECTION_ATTEMPT':
                        remote_host = activity.get('remote_host', '')
                        remote_port = activity.get('remote_port', '')
                        lines.append(f"  - Connection attempt: {remote_host}:{remote_port} [event_id: {activity.get('event_id')}, table: {activity.get('table')}, timestamp: {activity.get('observed_at')}]")
            lines.append("")
        
        # Temporal Phases
        lines.append("TEMPORAL PHASES")
        lines.append("-" * 80)
        for phase in temporal_phases.get('temporal_phases', []):
            phase_name = phase.get('phase', '')
            start_time = phase.get('start_time', '')
            end_time = phase.get('end_time', '')
            duration = phase.get('duration_seconds', 0)
            event_count = phase.get('event_count', 0)
            lines.append(f"Phase: {phase_name} ({start_time} to {end_time}, duration: {duration} seconds)")
            lines.append(f"  Events: {event_count}")
            lines.append("")
        
        # Evidence References
        lines.append("EVIDENCE REFERENCES")
        lines.append("-" * 80)
        evidence_by_table = defaultdict(int)
        for link in evidence_links.get('evidence_links', []):
            for ref in link.get('evidence_references', []):
                table = ref.get('table', '')
                if table:
                    evidence_by_table[table] += 1
        
        for table, count in evidence_by_table.items():
            lines.append(f"  - {table}: {count} events")
        lines.append(f"Total: {evidence_links.get('total_evidence_references', 0)} evidence references")
        
        return "\n".join(lines)
    
    def generate_graph_metadata(
        self,
        behavioral_chains: Dict[str, Any],
        evidence_links: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate graph metadata (nodes and edges)."""
        nodes = []
        edges = []
        node_id_map = {}  # Map (type, id) -> node_id
        
        # Process nodes
        for chain in behavioral_chains.get('process_lineage', []):
            root = chain.get('root_process', {})
            if root:
                process_pid = root.get('process_pid')
                node_id = f"proc_{process_pid}"
                node_id_map[('PROCESS', process_pid)] = node_id
                nodes.append({
                    'node_id': node_id,
                    'node_type': 'PROCESS',
                    'properties': {
                        'process_pid': process_pid,
                        'process_name': root.get('process_name', ''),
                        'process_path': root.get('process_path', '')
                    },
                    'evidence_references': [{
                        'event_id': root.get('event_id'),
                        'table': root.get('table'),
                        'observed_at': root.get('observed_at')
                    }]
                })
            
            for child in chain.get('child_processes', []):
                child_pid = child.get('process_pid')
                parent_pid = child.get('parent_pid')
                child_node_id = f"proc_{child_pid}"
                node_id_map[('PROCESS', child_pid)] = child_node_id
                nodes.append({
                    'node_id': child_node_id,
                    'node_type': 'PROCESS',
                    'properties': {
                        'process_pid': child_pid,
                        'process_name': child.get('process_name', ''),
                        'process_path': child.get('process_path', '')
                    },
                    'evidence_references': [{
                        'event_id': child.get('event_id'),
                        'table': child.get('table'),
                        'observed_at': child.get('observed_at')
                    }]
                })
                
                # Add parent edge
                if parent_pid and ('PROCESS', parent_pid) in node_id_map:
                    parent_node_id = node_id_map[('PROCESS', parent_pid)]
                    edges.append({
                        'edge_id': f"edge_{len(edges) + 1}",
                        'edge_type': 'PARENT_OF',
                        'source_node_id': parent_node_id,
                        'target_node_id': child_node_id,
                        'properties': {
                            'observed_at': child.get('observed_at')
                        },
                        'evidence_references': [{
                            'event_id': child.get('event_id'),
                            'table': child.get('table'),
                            'observed_at': child.get('observed_at')
                        }]
                    })
        
        # File nodes
        for chain in behavioral_chains.get('file_modification', []):
            file_path = chain.get('file_path', '')
            file_node_id = f"file_{hash(file_path) % 1000000}"
            node_id_map[('FILE', file_path)] = file_node_id
            nodes.append({
                'node_id': file_node_id,
                'node_type': 'FILE',
                'properties': {
                    'file_path': file_path
                },
                'evidence_references': [
                    {
                        'event_id': op.get('event_id'),
                        'table': op.get('table'),
                        'observed_at': op.get('observed_at')
                    }
                    for op in chain.get('operations', [])
                ]
            })
            
            # Add process-file edges
            for op in chain.get('operations', []):
                process_pid = op.get('process_pid')
                if process_pid and ('PROCESS', process_pid) in node_id_map:
                    process_node_id = node_id_map[('PROCESS', process_pid)]
                    edges.append({
                        'edge_id': f"edge_{len(edges) + 1}",
                        'edge_type': 'MODIFIED',
                        'source_node_id': process_node_id,
                        'target_node_id': file_node_id,
                        'properties': {
                            'activity_type': op.get('activity_type'),
                            'observed_at': op.get('observed_at')
                        },
                        'evidence_references': [{
                            'event_id': op.get('event_id'),
                            'table': op.get('table'),
                            'observed_at': op.get('observed_at')
                        }]
                    })
        
        return {
            'graph_metadata': {
                'nodes': nodes,
                'edges': edges
            }
        }
