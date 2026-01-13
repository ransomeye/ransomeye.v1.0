#!/usr/bin/env python3
"""
RansomEye v1.0 Forensic Summarization - Evidence Linker
AUTHORITATIVE: Evidence linking and validation for all claims
"""

import os
import sys
from typing import Dict, Any, List, Optional

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    _logger = setup_logging('forensic-summarization-evidence-linker')
except ImportError:
    import logging
    _logger = logging.getLogger('forensic-summarization-evidence-linker')


class EvidenceLinker:
    """
    Links claims to evidence and validates all claims have evidence references.
    
    CRITICAL: Every claim must have at least one evidence reference.
    Claims without evidence are rejected (not included in summary).
    """
    
    def __init__(self):
        """Initialize evidence linker."""
        pass
    
    def link_evidence(
        self,
        behavioral_chains: Dict[str, Any],
        temporal_phases: Dict[str, Any],
        evidence_events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Link all claims to evidence and validate.
        
        Args:
            behavioral_chains: Dictionary with all behavioral chains
            temporal_phases: Dictionary with temporal phases
            evidence_events: List of all evidence events
            
        Returns:
            List of evidence links (claims with evidence references)
        """
        evidence_links = []
        
        # Extract claims from behavioral chains
        chain_claims = self._extract_claims_from_chains(behavioral_chains)
        for claim in chain_claims:
            evidence_refs = self._match_claim_to_evidence(claim, evidence_events)
            if evidence_refs:
                evidence_links.append({
                    'claim': claim['claim'],
                    'evidence_references': evidence_refs
                })
            else:
                _logger.warning(f"Claim without evidence rejected: {claim['claim']}")
        
        # Extract claims from temporal phases
        phase_claims = self._extract_claims_from_phases(temporal_phases)
        for claim in phase_claims:
            evidence_refs = self._match_claim_to_evidence(claim, evidence_events)
            if evidence_refs:
                evidence_links.append({
                    'claim': claim['claim'],
                    'evidence_references': evidence_refs
                })
            else:
                _logger.warning(f"Claim without evidence rejected: {claim['claim']}")
        
        return {
            'evidence_links': evidence_links,
            'total_claims': len(chain_claims) + len(phase_claims),
            'total_evidence_references': sum(len(link['evidence_references']) for link in evidence_links)
        }
    
    def _extract_claims_from_chains(self, behavioral_chains: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract claims from behavioral chains."""
        claims = []
        
        # Process lineage claims
        for chain in behavioral_chains.get('process_lineage', []):
            root = chain.get('root_process', {})
            if root:
                claims.append({
                    'claim': f"Process {root.get('process_pid')} ({root.get('process_name')}) started",
                    'event_id': root.get('event_id'),
                    'table': root.get('table'),
                    'observed_at': root.get('observed_at')
                })
            
            for child in chain.get('child_processes', []):
                claims.append({
                    'claim': f"Process {child.get('process_pid')} ({child.get('process_name')}) started, parent PID {child.get('parent_pid')}",
                    'event_id': child.get('event_id'),
                    'table': child.get('table'),
                    'observed_at': child.get('observed_at')
                })
        
        # File modification claims
        for chain in behavioral_chains.get('file_modification', []):
            file_path = chain.get('file_path', '')
            for op in chain.get('operations', []):
                activity_type = op.get('activity_type', '')
                claims.append({
                    'claim': f"File {file_path} {activity_type}",
                    'event_id': op.get('event_id'),
                    'table': op.get('table'),
                    'observed_at': op.get('observed_at')
                })
        
        # Persistence claims
        for chain in behavioral_chains.get('persistence_establishment', []):
            for mechanism in chain.get('persistence_mechanisms', []):
                persistence_type = mechanism.get('persistence_type', '')
                persistence_key = mechanism.get('persistence_key', '')
                claims.append({
                    'claim': f"Persistence mechanism {persistence_type} established: {persistence_key}",
                    'event_id': mechanism.get('event_id'),
                    'table': mechanism.get('table'),
                    'observed_at': mechanism.get('observed_at')
                })
        
        # Network intent claims
        for chain in behavioral_chains.get('network_intent_progression', []):
            for activity in chain.get('network_activities', []):
                intent_type = activity.get('intent_type', '')
                if intent_type == 'DNS_QUERY':
                    dns_query_name = activity.get('dns_query_name', '')
                    claims.append({
                        'claim': f"DNS query for {dns_query_name}",
                        'event_id': activity.get('event_id'),
                        'table': activity.get('table'),
                        'observed_at': activity.get('observed_at')
                    })
                elif intent_type == 'CONNECTION_ATTEMPT':
                    remote_host = activity.get('remote_host', '')
                    remote_port = activity.get('remote_port', '')
                    claims.append({
                        'claim': f"Connection attempt to {remote_host}:{remote_port}",
                        'event_id': activity.get('event_id'),
                        'table': activity.get('table'),
                        'observed_at': activity.get('observed_at')
                    })
        
        # Lateral preparation claims
        for chain in behavioral_chains.get('lateral_preparation', []):
            for indicator in chain.get('indicators', []):
                indicator_type = indicator.get('indicator_type', '')
                description = indicator.get('description', '')
                claims.append({
                    'claim': f"{indicator_type}: {description}",
                    'event_id': indicator.get('event_id'),
                    'table': indicator.get('table'),
                    'observed_at': indicator.get('observed_at')
                })
        
        return claims
    
    def _extract_claims_from_phases(self, temporal_phases: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract claims from temporal phases."""
        claims = []
        
        for phase in temporal_phases.get('temporal_phases', []):
            phase_name = phase.get('phase', '')
            start_time = phase.get('start_time', '')
            end_time = phase.get('end_time', '')
            event_count = phase.get('event_count', 0)
            
            claims.append({
                'claim': f"Phase {phase_name} from {start_time} to {end_time} with {event_count} events",
                'event_id': None,  # Phase-level claim (no single event_id)
                'table': None,
                'observed_at': start_time
            })
        
        return claims
    
    def _match_claim_to_evidence(
        self, 
        claim: Dict[str, Any], 
        evidence_events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Match claim to evidence events.
        
        Matching criteria:
        - event_id match (exact)
        - table match (exact)
        - observed_at match (exact)
        """
        event_id = claim.get('event_id')
        table = claim.get('table')
        observed_at = claim.get('observed_at')
        
        if not event_id:
            # Phase-level claim - match by observed_at
            if observed_at:
                matching_events = [
                    e for e in evidence_events 
                    if e.get('observed_at') == observed_at
                ]
                return [
                    {
                        'event_id': e.get('event_id'),
                        'table': e.get('table'),
                        'observed_at': e.get('observed_at'),
                        'confidence_level': 'MEDIUM'  # Phase-level claims have lower confidence
                    }
                    for e in matching_events
                ]
            return []
        
        # Event-level claim - match by event_id, table, observed_at
        matching_events = [
            e for e in evidence_events 
            if e.get('event_id') == event_id
            and e.get('table') == table
            and e.get('observed_at') == observed_at
        ]
        
        return [
            {
                'event_id': e.get('event_id'),
                'table': e.get('table'),
                'observed_at': e.get('observed_at'),
                'confidence_level': 'HIGH'  # Direct event match has high confidence
            }
            for e in matching_events
        ]
