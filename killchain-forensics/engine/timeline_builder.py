#!/usr/bin/env python3
"""
RansomEye KillChain & Forensics - Timeline Builder
AUTHORITATIVE: Deterministic timeline reconstruction with immutable events
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid


class TimelineError(Exception):
    """Base exception for timeline errors."""
    pass


class TimelineBuilder:
    """
    Deterministic timeline reconstruction.
    
    Properties:
    - Immutable: Events cannot be modified after creation
    - Ordered: Events are ordered by timestamp
    - Cross-host: Events from multiple hosts are stitched together
    - Deterministic: Same inputs always produce same timeline
    """
    
    def __init__(self):
        """Initialize timeline builder."""
        self.events: List[Dict[str, Any]] = []
    
    def add_event(
        self,
        source_event: Dict[str, Any],
        mitre_mapping: Dict[str, str],
        evidence_references: List[str],
        campaign_id: str,
        correlation_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add event to timeline.
        
        Args:
            source_event: Source event from correlation engine or ingest
            mitre_mapping: MITRE ATT&CK mapping (technique_id, tactic, stage)
            evidence_references: List of evidence record IDs
            campaign_id: Campaign identifier
            correlation_metadata: Metadata for cross-host correlation
        
        Returns:
            Killchain event dictionary
        """
        event_id = str(uuid.uuid4())
        
        # Extract event data (read-only, no mutation)
        timestamp = source_event.get('timestamp', datetime.utcnow().isoformat())
        host_id = source_event.get('host_id', '')
        user_id = source_event.get('user_id', '')
        process_id = source_event.get('process_id', '')
        event_type = source_event.get('event_type', 'other')
        source_event_id = source_event.get('event_id', '')
        
        # Create killchain event
        killchain_event = {
            'event_id': event_id,
            'timestamp': timestamp,
            'host_id': host_id,
            'user_id': user_id,
            'process_id': process_id,
            'mitre_technique_id': mitre_mapping['mitre_technique_id'],
            'mitre_tactic': mitre_mapping['mitre_tactic'],
            'mitre_stage': mitre_mapping['mitre_stage'],
            'event_type': event_type,
            'source_event_id': source_event_id,
            'evidence_references': evidence_references,
            'campaign_id': campaign_id,
            'correlation_metadata': correlation_metadata
        }
        
        # Add to timeline (immutable after addition)
        self.events.append(killchain_event)
        
        return killchain_event
    
    def build_timeline(self) -> List[Dict[str, Any]]:
        """
        Build ordered timeline from events.
        
        Returns:
            Ordered list of killchain events (sorted by timestamp)
        """
        # Sort by timestamp (deterministic ordering)
        sorted_events = sorted(self.events, key=lambda e: e.get('timestamp', ''))
        return sorted_events
    
    def get_timeline_by_stage(self, stage: str) -> List[Dict[str, Any]]:
        """
        Get timeline events for specific MITRE stage.
        
        Args:
            stage: MITRE stage (e.g., 'execution', 'persistence')
        
        Returns:
            List of events for specified stage
        """
        timeline = self.build_timeline()
        return [e for e in timeline if e.get('mitre_stage') == stage]
    
    def get_timeline_by_host(self, host_id: str) -> List[Dict[str, Any]]:
        """
        Get timeline events for specific host.
        
        Args:
            host_id: Host identifier
        
        Returns:
            List of events for specified host
        """
        timeline = self.build_timeline()
        return [e for e in timeline if e.get('host_id') == host_id]
    
    def get_timeline_by_campaign(self, campaign_id: str) -> List[Dict[str, Any]]:
        """
        Get timeline events for specific campaign.
        
        Args:
            campaign_id: Campaign identifier
        
        Returns:
            List of events for specified campaign
        """
        timeline = self.build_timeline()
        return [e for e in timeline if e.get('campaign_id') == campaign_id]
    
    def detect_stage_transitions(self) -> List[Dict[str, Any]]:
        """
        Detect explicit stage transitions in timeline.
        
        Returns:
            List of stage transition records
        """
        timeline = self.build_timeline()
        transitions = []
        
        prev_stage = None
        for event in timeline:
            current_stage = event.get('mitre_stage')
            if prev_stage and current_stage != prev_stage:
                transitions.append({
                    'from_stage': prev_stage,
                    'to_stage': current_stage,
                    'transition_event_id': event.get('event_id'),
                    'transition_timestamp': event.get('timestamp')
                })
            prev_stage = current_stage
        
        return transitions
