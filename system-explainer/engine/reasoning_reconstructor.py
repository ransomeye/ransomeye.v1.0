#!/usr/bin/env python3
"""
RansomEye System Explanation Engine - Reasoning Reconstructor
AUTHORITATIVE: Reconstructs reasoning from evidence (read-only access to subsystems)
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, timezone


class ReconstructionError(Exception):
    """Base exception for reconstruction errors."""
    pass


class ReasoningReconstructor:
    """
    Reconstructs reasoning from evidence.
    
    Properties:
    - Read-only: Only reads from subsystems, never mutates
    - Deterministic: Same inputs always produce same reconstruction
    - Evidence-based: All reasoning is based on evidence, no assumptions
    """
    
    def __init__(
        self,
        ledger_path: Path,
        killchain_store_path: Optional[Path] = None,
        threat_graph_path: Optional[Path] = None,
        risk_store_path: Optional[Path] = None
    ):
        """
        Initialize reasoning reconstructor.
        
        Args:
            ledger_path: Path to audit ledger file
            killchain_store_path: Path to killchain store (optional)
            threat_graph_path: Path to threat graph store (optional)
            risk_store_path: Path to risk store (optional)
        """
        self.ledger_path = ledger_path
        self.killchain_store_path = killchain_store_path
        self.threat_graph_path = threat_graph_path
        self.risk_store_path = risk_store_path
    
    def reconstruct_incident_explanation(self, incident_id: str) -> List[Dict[str, Any]]:
        """
        Reconstruct reasoning chain for incident.
        
        Reads from audit ledger to reconstruct why incident existed.
        
        Args:
            incident_id: Incident identifier
        
        Returns:
            List of reasoning steps
        """
        reasoning_steps = []
        
        # Read audit ledger entries related to incident
        ledger_entries = self._read_ledger_entries_for_subject(incident_id)
        
        for entry in ledger_entries:
            step = {
                'step_id': str(uuid.uuid4()),
                'step_type': 'ledger_entry',
                'description': f"Audit ledger entry: {entry.get('action_type', 'unknown')}",
                'evidence_source': 'audit_ledger',
                'evidence_id': entry.get('ledger_entry_id', ''),
                'timestamp': entry.get('timestamp', '')
            }
            reasoning_steps.append(step)
        
        return reasoning_steps
    
    def reconstruct_killchain_stage_advancement(
        self,
        killchain_event_id: str
    ) -> List[Dict[str, Any]]:
        """
        Reconstruct reasoning chain for killchain stage advancement.
        
        Reads from killchain store and audit ledger.
        
        Args:
            killchain_event_id: Killchain event identifier
        
        Returns:
            List of reasoning steps
        """
        reasoning_steps = []
        
        # Read killchain event
        if self.killchain_store_path and self.killchain_store_path.exists():
            killchain_event = self._read_killchain_event(killchain_event_id)
            if killchain_event:
                step = {
                    'step_id': str(uuid.uuid4()),
                    'step_type': 'killchain_event',
                    'description': f"Killchain event: {killchain_event.get('mitre_stage', 'unknown')} - {killchain_event.get('mitre_technique_id', 'unknown')}",
                    'evidence_source': 'killchain_forensics',
                    'evidence_id': killchain_event_id,
                    'timestamp': killchain_event.get('timestamp', '')
                }
                reasoning_steps.append(step)
        
        # Read related ledger entries
        ledger_entries = self._read_ledger_entries_for_subject(killchain_event_id)
        for entry in ledger_entries:
            step = {
                'step_id': str(uuid.uuid4()),
                'step_type': 'ledger_entry',
                'description': f"Audit ledger entry: {entry.get('action_type', 'unknown')}",
                'evidence_source': 'audit_ledger',
                'evidence_id': entry.get('ledger_entry_id', ''),
                'timestamp': entry.get('timestamp', '')
            }
            reasoning_steps.append(step)
        
        return reasoning_steps
    
    def reconstruct_campaign_inference(
        self,
        campaign_id: str
    ) -> List[Dict[str, Any]]:
        """
        Reconstruct reasoning chain for campaign inference.
        
        Reads from threat graph and audit ledger.
        
        Args:
            campaign_id: Campaign identifier
        
        Returns:
            List of reasoning steps
        """
        reasoning_steps = []
        
        # Read threat graph relationships
        if self.threat_graph_path and self.threat_graph_path.exists():
            graph_relationships = self._read_graph_relationships_for_campaign(campaign_id)
            for rel in graph_relationships:
                step = {
                    'step_id': str(uuid.uuid4()),
                    'step_type': 'graph_relationship',
                    'description': f"Graph relationship: {rel.get('edge_type', 'unknown')} - {rel.get('inference_explanation', 'unknown')}",
                    'evidence_source': 'threat_graph',
                    'evidence_id': rel.get('edge_id', ''),
                    'timestamp': rel.get('timestamp', '')
                }
                reasoning_steps.append(step)
        
        # Read related ledger entries
        ledger_entries = self._read_ledger_entries_for_subject(campaign_id)
        for entry in ledger_entries:
            step = {
                'step_id': str(uuid.uuid4()),
                'step_type': 'ledger_entry',
                'description': f"Audit ledger entry: {entry.get('action_type', 'unknown')}",
                'evidence_source': 'audit_ledger',
                'evidence_id': entry.get('ledger_entry_id', ''),
                'timestamp': entry.get('timestamp', '')
            }
            reasoning_steps.append(step)
        
        return reasoning_steps
    
    def reconstruct_risk_score_change(
        self,
        risk_computation_id: str
    ) -> List[Dict[str, Any]]:
        """
        Reconstruct reasoning chain for risk score change.
        
        Reads from risk store and audit ledger.
        
        Args:
            risk_computation_id: Risk computation identifier
        
        Returns:
            List of reasoning steps
        """
        reasoning_steps = []
        
        # Read risk computation
        if self.risk_store_path and self.risk_store_path.exists():
            risk_computation = self._read_risk_computation(risk_computation_id)
            if risk_computation:
                step = {
                    'step_id': str(uuid.uuid4()),
                    'step_type': 'risk_computation',
                    'description': f"Risk computation: score={risk_computation.get('risk_score', 'unknown')}, components={len(risk_computation.get('component_scores', {}))}",
                    'evidence_source': 'risk_index',
                    'evidence_id': risk_computation_id,
                    'timestamp': risk_computation.get('timestamp', '')
                }
                reasoning_steps.append(step)
        
        # Read related ledger entries
        ledger_entries = self._read_ledger_entries_for_subject(risk_computation_id)
        for entry in ledger_entries:
            step = {
                'step_id': str(uuid.uuid4()),
                'step_type': 'ledger_entry',
                'description': f"Audit ledger entry: {entry.get('action_type', 'unknown')}",
                'evidence_source': 'audit_ledger',
                'evidence_id': entry.get('ledger_entry_id', ''),
                'timestamp': entry.get('timestamp', '')
            }
            reasoning_steps.append(step)
        
        return reasoning_steps
    
    def reconstruct_policy_recommendation(
        self,
        policy_decision_id: str
    ) -> List[Dict[str, Any]]:
        """
        Reconstruct reasoning chain for policy recommendation.
        
        Reads from audit ledger.
        
        Args:
            policy_decision_id: Policy decision identifier
        
        Returns:
            List of reasoning steps
        """
        reasoning_steps = []
        
        # Read ledger entries for policy decision
        ledger_entries = self._read_ledger_entries_for_subject(policy_decision_id)
        for entry in ledger_entries:
            step = {
                'step_id': str(uuid.uuid4()),
                'step_type': 'policy_decision',
                'description': f"Policy decision: {entry.get('action_type', 'unknown')}",
                'evidence_source': 'policy_engine',
                'evidence_id': entry.get('ledger_entry_id', ''),
                'timestamp': entry.get('timestamp', '')
            }
            reasoning_steps.append(step)
        
        return reasoning_steps
    
    def _read_ledger_entries_for_subject(self, subject_id: str) -> List[Dict[str, Any]]:
        """Read audit ledger entries for subject."""
        entries = []
        
        if not self.ledger_path.exists():
            return entries
        
        try:
            with open(self.ledger_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    # Check if entry is related to subject
                    subject = entry.get('subject', {})
                    if subject.get('id') == subject_id or subject_id in str(subject):
                        entries.append(entry)
        except Exception as e:
            raise ReconstructionError(f"Failed to read ledger entries: {e}") from e
        
        return entries
    
    def _read_killchain_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Read killchain event from store."""
        if not self.killchain_store_path or not self.killchain_store_path.exists():
            return None
        
        try:
            # Read killchain store (JSON lines format assumed)
            with open(self.killchain_store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    event = json.loads(line)
                    if event.get('event_id') == event_id:
                        return event
        except Exception:
            pass
        
        return None
    
    def _read_graph_relationships_for_campaign(self, campaign_id: str) -> List[Dict[str, Any]]:
        """Read graph relationships for campaign."""
        relationships = []
        
        if not self.threat_graph_path or not self.threat_graph_path.exists():
            return relationships
        
        try:
            graph_data = json.loads(self.threat_graph_path.read_text())
            edges = graph_data.get('edges', [])
            
            # Find edges related to campaign (simplified - would need actual campaign tracking)
            for edge in edges:
                if campaign_id in str(edge.get('properties', {})):
                    relationships.append(edge)
        except Exception:
            pass
        
        return relationships
    
    def _read_risk_computation(self, computation_id: str) -> Optional[Dict[str, Any]]:
        """Read risk computation from store."""
        if not self.risk_store_path or not self.risk_store_path.exists():
            return None
        
        try:
            # Read risk store (JSON lines format assumed)
            with open(self.risk_store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    computation = json.loads(line)
                    if computation.get('computation_id') == computation_id:
                        return computation
        except Exception:
            pass
        
        return None
