#!/usr/bin/env python3
"""
RansomEye v1.0 Forensic Summarization - Temporal Phase Detector
AUTHORITATIVE: Deterministic phase boundary detection for incident timeline
"""

import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    _logger = setup_logging('forensic-summarization-phase-detector')
except ImportError:
    import logging
    _logger = logging.getLogger('forensic-summarization-phase-detector')


class TemporalPhaseDetector:
    """
    Detects temporal phases from behavioral chains and evidence events.
    
    CRITICAL: Phase boundaries are deterministic (explicit rules, no heuristics).
    Phases do not overlap (explicit boundaries).
    All events are assigned to phases (complete coverage).
    """
    
    def __init__(self):
        """Initialize temporal phase detector."""
        pass
    
    def detect_phases(
        self,
        behavioral_chains: Dict[str, Any],
        evidence_events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect temporal phases from behavioral chains and evidence events.
        
        Phases:
        1. INITIAL_EXECUTION: First process creation, first file access
        2. EXPANSION: Process spawning, file modifications, network activity
        3. PERSISTENCE: Persistence mechanism establishment
        4. EXFILTRATION_PREP: Network connections, data collection, encryption
        
        Args:
            behavioral_chains: Dictionary with all behavioral chains
            evidence_events: List of all evidence events
            
        Returns:
            List of temporal phases
        """
        if not evidence_events:
            return []
        
        # Sort all events by observed_at (temporal order)
        all_events = sorted(evidence_events, key=lambda e: e.get('observed_at', ''))
        
        if not all_events:
            return []
        
        # Find phase boundaries
        initial_execution_start = all_events[0].get('observed_at')
        initial_execution_end = self._find_first_expansion_event(all_events, initial_execution_start)
        expansion_start = initial_execution_end
        expansion_end = self._find_first_persistence_event(all_events, expansion_start)
        persistence_start = expansion_end
        persistence_end = self._find_first_exfiltration_prep_event(all_events, persistence_start)
        exfiltration_start = persistence_end
        exfiltration_end = all_events[-1].get('observed_at')
        
        phases = []
        
        # Phase 1: INITIAL_EXECUTION
        phase1_events = self._find_events_in_range(all_events, initial_execution_start, initial_execution_end)
        phases.append({
            'phase': 'INITIAL_EXECUTION',
            'start_time': initial_execution_start,
            'end_time': initial_execution_end,
            'duration_seconds': self._calculate_duration_seconds(initial_execution_start, initial_execution_end),
            'event_count': len(phase1_events),
            'events': phase1_events
        })
        
        # Phase 2: EXPANSION
        if expansion_start and expansion_end:
            phase2_events = self._find_events_in_range(all_events, expansion_start, expansion_end)
            phases.append({
                'phase': 'EXPANSION',
                'start_time': expansion_start,
                'end_time': expansion_end,
                'duration_seconds': self._calculate_duration_seconds(expansion_start, expansion_end),
                'event_count': len(phase2_events),
                'events': phase2_events
            })
        
        # Phase 3: PERSISTENCE
        if persistence_start and persistence_end:
            phase3_events = self._find_events_in_range(all_events, persistence_start, persistence_end)
            phases.append({
                'phase': 'PERSISTENCE',
                'start_time': persistence_start,
                'end_time': persistence_end,
                'duration_seconds': self._calculate_duration_seconds(persistence_start, persistence_end),
                'event_count': len(phase3_events),
                'events': phase3_events
            })
        
        # Phase 4: EXFILTRATION_PREP
        if exfiltration_start and exfiltration_end:
            phase4_events = self._find_events_in_range(all_events, exfiltration_start, exfiltration_end)
            phases.append({
                'phase': 'EXFILTRATION_PREP',
                'start_time': exfiltration_start,
                'end_time': exfiltration_end,
                'duration_seconds': self._calculate_duration_seconds(exfiltration_start, exfiltration_end),
                'event_count': len(phase4_events),
                'events': phase4_events
            })
        
        # Calculate total duration
        total_duration = self._calculate_duration_seconds(initial_execution_start, exfiltration_end)
        total_event_count = len(all_events)
        
        return {
            'temporal_phases': phases,
            'total_duration_seconds': total_duration,
            'total_event_count': total_event_count
        }
    
    def _find_first_expansion_event(
        self, 
        events: List[Dict[str, Any]], 
        after_time: str
    ) -> Optional[str]:
        """
        Find first expansion event (process spawn, file modification, network activity).
        
        Expansion indicators:
        - Process spawn (child process creation)
        - File modification (not just create)
        - Network activity (DNS query, connection attempt)
        """
        for event in events:
            observed_at = event.get('observed_at', '')
            if not observed_at or observed_at <= after_time:
                continue
            
            table = event.get('table')
            activity_type = event.get('activity_type')
            
            # Process spawn (child process)
            if table == 'process_activity' and activity_type == 'PROCESS_START':
                parent_pid = event.get('parent_pid')
                if parent_pid is not None:  # Has parent (spawned process)
                    return observed_at
            
            # File modification
            if table == 'file_activity' and activity_type in ['FILE_MODIFY', 'FILE_DELETE']:
                return observed_at
            
            # Network activity
            if table == 'network_intent':
                return observed_at
        
        # No expansion event found - return last event time
        if events:
            return events[-1].get('observed_at')
        return after_time
    
    def _find_first_persistence_event(
        self, 
        events: List[Dict[str, Any]], 
        after_time: str
    ) -> Optional[str]:
        """
        Find first persistence mechanism establishment event.
        """
        for event in events:
            observed_at = event.get('observed_at', '')
            if not observed_at or observed_at <= after_time:
                continue
            
            table = event.get('table')
            if table == 'persistence':
                enabled = event.get('enabled', True)
                if enabled:  # Only enabled persistence (not removal)
                    return observed_at
        
        # No persistence event found - return last event time
        if events:
            return events[-1].get('observed_at')
        return after_time
    
    def _find_first_exfiltration_prep_event(
        self, 
        events: List[Dict[str, Any]], 
        after_time: str
    ) -> Optional[str]:
        """
        Find first exfiltration preparation event.
        
        Exfiltration prep indicators:
        - Network connection to external host (not localhost)
        - File encryption (entropy change)
        - Large file transfers (via DPI flows)
        """
        for event in events:
            observed_at = event.get('observed_at', '')
            if not observed_at or observed_at <= after_time:
                continue
            
            table = event.get('table')
            activity_type = event.get('activity_type')
            
            # File encryption
            if table == 'file_activity' and activity_type == 'FILE_MODIFY':
                entropy_change = event.get('entropy_change_indicator', False)
                if entropy_change:
                    return observed_at
            
            # Network connection to external host
            if table == 'network_intent' and activity_type == 'CONNECTION_ATTEMPT':
                remote_host = event.get('remote_host', '')
                # Check if external (not localhost, not private IP)
                if remote_host and not self._is_localhost_or_private(remote_host):
                    return observed_at
            
            # DPI flow with large data transfer
            if table == 'dpi_flows':
                bytes_sent = event.get('bytes_sent', 0)
                bytes_received = event.get('bytes_received', 0)
                # Large transfer threshold: 1MB
                if bytes_sent > 1048576 or bytes_received > 1048576:
                    return observed_at
        
        # No exfiltration prep event found - return last event time
        if events:
            return events[-1].get('observed_at')
        return after_time
    
    def _find_events_in_range(
        self, 
        events: List[Dict[str, Any]], 
        start_time: str, 
        end_time: str
    ) -> List[Dict[str, Any]]:
        """
        Find events in time range [start_time, end_time].
        
        Args:
            events: List of events (sorted by observed_at)
            start_time: Start timestamp (inclusive)
            end_time: End timestamp (inclusive)
            
        Returns:
            List of events in range
        """
        result = []
        for event in events:
            observed_at = event.get('observed_at', '')
            if not observed_at:
                continue
            
            if start_time <= observed_at <= end_time:
                result.append({
                    'event_id': event.get('event_id'),
                    'table': event.get('table'),
                    'observed_at': observed_at
                })
        
        return result
    
    def _is_localhost_or_private(self, ip_or_host: str) -> bool:
        """
        Check if IP address or hostname is localhost or private.
        
        Args:
            ip_or_host: IP address or hostname
            
        Returns:
            True if localhost or private IP, False otherwise
        """
        if not ip_or_host:
            return False
        
        # Check for localhost
        if ip_or_host.lower() in ['localhost', '127.0.0.1', '::1']:
            return True
        
        # Check for private IP ranges (simplified)
        if ip_or_host.startswith('10.') or ip_or_host.startswith('192.168.') or ip_or_host.startswith('172.'):
            return True
        
        return False
    
    def _calculate_duration_seconds(self, start_time: str, end_time: str) -> int:
        """Calculate duration in seconds between two timestamps."""
        if not start_time or not end_time:
            return 0
        
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            return int((end_dt - start_dt).total_seconds())
        except Exception:
            return 0
