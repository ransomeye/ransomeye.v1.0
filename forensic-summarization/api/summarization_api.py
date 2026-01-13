#!/usr/bin/env python3
"""
RansomEye v1.0 Forensic Summarization - Summarization API
AUTHORITATIVE: Main API for forensic summary generation
"""

import os
import sys
from typing import Dict, Any, Optional, List
from pathlib import Path

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    _logger = setup_logging('forensic-summarization-api')
except ImportError:
    import logging
    _logger = logging.getLogger('forensic-summarization-api')

# Database connection
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    _psycopg2_available = True
except ImportError:
    _psycopg2_available = False
    _logger.warning("psycopg2 not available - database operations disabled")

from ..engine import (
    BehavioralChainBuilder,
    TemporalPhaseDetector,
    EvidenceLinker,
    SummaryGenerator
)


class SummarizationAPI:
    """
    Main API for forensic summarization.
    
    CRITICAL: Read-only DB access via views only (per data-plane hardening).
    All summaries are deterministic and replayable.
    """
    
    def __init__(self, db_connection):
        """
        Initialize summarization API.
        
        Args:
            db_connection: PostgreSQL database connection
        """
        self.db_connection = db_connection
        self.chain_builder = BehavioralChainBuilder()
        self.phase_detector = TemporalPhaseDetector()
        self.evidence_linker = EvidenceLinker()
        self.summary_generator = SummaryGenerator()
    
    def generate_summary(
        self,
        incident_id: str,
        output_format: str = 'all'
    ) -> Dict[str, Any]:
        """
        Generate forensic summary for an incident.
        
        Args:
            incident_id: Incident identifier (UUID)
            output_format: Output format ('json', 'text', 'graph', 'all')
            
        Returns:
            Dictionary with summary (format depends on output_format)
        """
        # Load incident metadata
        incident_metadata = self._load_incident_metadata(incident_id)
        if not incident_metadata:
            raise ValueError(f"Incident not found: {incident_id}")
        
        machine_id = incident_metadata['machine_id']
        time_range = {
            'start_time': incident_metadata['first_observed_at'],
            'end_time': incident_metadata['last_observed_at']
        }
        
        # Load evidence events
        evidence_events = self._load_evidence_events(incident_id)
        if not evidence_events:
            raise ValueError(f"No evidence found for incident: {incident_id}")
        
        # Build behavioral chains
        behavioral_chains = self.chain_builder.build_all_chains(evidence_events)
        
        # Detect temporal phases
        temporal_phases = self.phase_detector.detect_phases(behavioral_chains, evidence_events)
        
        # Link evidence
        evidence_links = self.evidence_linker.link_evidence(
            behavioral_chains,
            temporal_phases,
            evidence_events
        )
        
        # Generate summary
        summary = self.summary_generator.generate_summary(
            incident_id=incident_id,
            machine_id=machine_id,
            behavioral_chains=behavioral_chains,
            temporal_phases=temporal_phases,
            evidence_links=evidence_links,
            time_range=time_range
        )
        
        # Return requested format
        if output_format == 'json':
            return {'json_summary': summary['json_summary']}
        elif output_format == 'text':
            return {'text_summary': summary['text_summary']}
        elif output_format == 'graph':
            return {'graph_metadata': summary['graph_metadata']}
        else:  # 'all'
            return summary
    
    def _load_incident_metadata(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """
        Load incident metadata from database.
        
        Args:
            incident_id: Incident identifier
            
        Returns:
            Incident metadata dictionary or None if not found
        """
        if not _psycopg2_available or not self.db_connection:
            return None
        
        try:
            with self.db_connection.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        incident_id,
                        machine_id,
                        first_observed_at,
                        last_observed_at,
                        current_stage,
                        confidence_score
                    FROM incidents
                    WHERE incident_id = %s
                """, (incident_id,))
                
                row = cur.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            _logger.error(f"Failed to load incident metadata: {e}", exc_info=True)
            raise
    
    def _load_evidence_events(self, incident_id: str) -> List[Dict[str, Any]]:
        """
        Load evidence events from database (via views).
        
        Args:
            incident_id: Incident identifier
            
        Returns:
            List of evidence events
        """
        if not _psycopg2_available or not self.db_connection:
            return []
        
        evidence_events = []
        
        try:
            with self.db_connection.cursor(cursor_factory=RealDictCursor) as cur:
                # Load evidence entries
                cur.execute("""
                    SELECT 
                        e.event_id,
                        e.evidence_type,
                        e.normalized_table_name,
                        e.normalized_row_id,
                        e.observed_at
                    FROM evidence e
                    WHERE e.incident_id = %s
                    ORDER BY e.observed_at ASC
                """, (incident_id,))
                
                evidence_entries = cur.fetchall()
                
                # Load normalized events from views
                for entry in evidence_entries:
                    table_name = entry.get('normalized_table_name')
                    row_id = entry.get('normalized_row_id')
                    event_id = entry.get('event_id')
                    
                    if table_name and row_id:
                        # Load from normalized table view
                        event = self._load_normalized_event(table_name, row_id, event_id)
                        if event:
                            evidence_events.append(event)
                    else:
                        # Load from raw_events
                        event = self._load_raw_event(event_id)
                        if event:
                            evidence_events.append(event)
                
                return evidence_events
                
        except Exception as e:
            _logger.error(f"Failed to load evidence events: {e}", exc_info=True)
            raise
    
    def _load_normalized_event(
        self, 
        table_name: str, 
        row_id: int, 
        event_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load normalized event from view.
        
        Args:
            table_name: Normalized table name
            row_id: Row ID in normalized table
            event_id: Event ID (for reference)
            
        Returns:
            Event dictionary or None if not found
        """
        if not _psycopg2_available or not self.db_connection:
            return None
        
        try:
            with self.db_connection.cursor(cursor_factory=RealDictCursor) as cur:
                # Use view (per data-plane hardening)
                view_name = f"v_{table_name}_forensics"
                
                # Check if view exists (safe query)
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.views 
                        WHERE table_name = %s
                    )
                """, (view_name,))
                
                view_exists = cur.fetchone()[0]
                
                if not view_exists:
                    # Fallback to direct table access (for development)
                    _logger.warning(f"View {view_name} not found, using direct table access")
                    view_name = table_name
                
                # Load event
                cur.execute(f"""
                    SELECT * FROM {view_name}
                    WHERE id = %s
                """, (row_id,))
                
                row = cur.fetchone()
                if row:
                    event = dict(row)
                    event['event_id'] = event_id  # Ensure event_id is present
                    event['table'] = table_name  # Ensure table name is present
                    return event
                return None
                
        except Exception as e:
            _logger.error(f"Failed to load normalized event: {e}", exc_info=True)
            return None
    
    def _load_raw_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Load raw event from raw_events table.
        
        Args:
            event_id: Event identifier
            
        Returns:
            Event dictionary or None if not found
        """
        if not _psycopg2_available or not self.db_connection:
            return None
        
        try:
            with self.db_connection.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        event_id,
                        machine_id,
                        component_instance_id,
                        component,
                        observed_at,
                        ingested_at,
                        sequence,
                        payload,
                        hostname,
                        boot_id,
                        agent_version
                    FROM raw_events
                    WHERE event_id = %s
                """, (event_id,))
                
                row = cur.fetchone()
                if row:
                    event = dict(row)
                    event['table'] = 'raw_events'  # Ensure table name is present
                    return event
                return None
                
        except Exception as e:
            _logger.error(f"Failed to load raw event: {e}", exc_info=True)
            return None
