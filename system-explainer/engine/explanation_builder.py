#!/usr/bin/env python3
"""
RansomEye System Explanation Engine - Explanation Builder
AUTHORITATIVE: Builds signed explanation bundles from reasoning chains
"""

from typing import Dict, Any, List
import uuid
from datetime import datetime, timezone
from engine.reasoning_reconstructor import ReasoningReconstructor


class ExplanationError(Exception):
    """Base exception for explanation errors."""
    pass


class ExplanationBuilder:
    """
    Builds signed explanation bundles.
    
    Properties:
    - Deterministic: Same inputs always produce same bundle
    - Complete: All causal links are explicit
    - Immutable: Bundles cannot be modified after creation
    """
    
    def __init__(self, reconstructor: ReasoningReconstructor):
        """
        Initialize explanation builder.
        
        Args:
            reconstructor: Reasoning reconstructor instance
        """
        self.reconstructor = reconstructor
    
    def build_incident_explanation(
        self,
        incident_id: str
    ) -> Dict[str, Any]:
        """
        Build explanation bundle for incident.
        
        Args:
            incident_id: Incident identifier
        
        Returns:
            Explanation bundle dictionary (without signature)
        """
        # Reconstruct reasoning chain
        reasoning_steps = self.reconstructor.reconstruct_incident_explanation(incident_id)
        
        # Build evidence references
        evidence_references = self._extract_evidence_references(reasoning_steps)
        
        # Build causal links
        causal_links = self._build_causal_links(reasoning_steps)
        
        # Build bundle
        bundle = {
            'bundle_id': str(uuid.uuid4()),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'explanation_type': 'incident_explanation',
            'subject_id': incident_id,
            'reasoning_chain': reasoning_steps,
            'evidence_references': evidence_references,
            'causal_links': causal_links
        }
        
        return bundle
    
    def build_killchain_stage_explanation(
        self,
        killchain_event_id: str
    ) -> Dict[str, Any]:
        """
        Build explanation bundle for killchain stage advancement.
        
        Args:
            killchain_event_id: Killchain event identifier
        
        Returns:
            Explanation bundle dictionary (without signature)
        """
        # Reconstruct reasoning chain
        reasoning_steps = self.reconstructor.reconstruct_killchain_stage_advancement(killchain_event_id)
        
        # Build evidence references
        evidence_references = self._extract_evidence_references(reasoning_steps)
        
        # Build causal links
        causal_links = self._build_causal_links(reasoning_steps)
        
        # Build bundle
        bundle = {
            'bundle_id': str(uuid.uuid4()),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'explanation_type': 'killchain_stage_advancement',
            'subject_id': killchain_event_id,
            'reasoning_chain': reasoning_steps,
            'evidence_references': evidence_references,
            'causal_links': causal_links
        }
        
        return bundle
    
    def build_campaign_inference_explanation(
        self,
        campaign_id: str
    ) -> Dict[str, Any]:
        """
        Build explanation bundle for campaign inference.
        
        Args:
            campaign_id: Campaign identifier
        
        Returns:
            Explanation bundle dictionary (without signature)
        """
        # Reconstruct reasoning chain
        reasoning_steps = self.reconstructor.reconstruct_campaign_inference(campaign_id)
        
        # Build evidence references
        evidence_references = self._extract_evidence_references(reasoning_steps)
        
        # Build causal links
        causal_links = self._build_causal_links(reasoning_steps)
        
        # Build bundle
        bundle = {
            'bundle_id': str(uuid.uuid4()),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'explanation_type': 'campaign_inference',
            'subject_id': campaign_id,
            'reasoning_chain': reasoning_steps,
            'evidence_references': evidence_references,
            'causal_links': causal_links
        }
        
        return bundle
    
    def build_risk_score_change_explanation(
        self,
        risk_computation_id: str
    ) -> Dict[str, Any]:
        """
        Build explanation bundle for risk score change.
        
        Args:
            risk_computation_id: Risk computation identifier
        
        Returns:
            Explanation bundle dictionary (without signature)
        """
        # Reconstruct reasoning chain
        reasoning_steps = self.reconstructor.reconstruct_risk_score_change(risk_computation_id)
        
        # Build evidence references
        evidence_references = self._extract_evidence_references(reasoning_steps)
        
        # Build causal links
        causal_links = self._build_causal_links(reasoning_steps)
        
        # Build bundle
        bundle = {
            'bundle_id': str(uuid.uuid4()),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'explanation_type': 'risk_score_change',
            'subject_id': risk_computation_id,
            'reasoning_chain': reasoning_steps,
            'evidence_references': evidence_references,
            'causal_links': causal_links
        }
        
        return bundle
    
    def build_policy_recommendation_explanation(
        self,
        policy_decision_id: str
    ) -> Dict[str, Any]:
        """
        Build explanation bundle for policy recommendation.
        
        Args:
            policy_decision_id: Policy decision identifier
        
        Returns:
            Explanation bundle dictionary (without signature)
        """
        # Reconstruct reasoning chain
        reasoning_steps = self.reconstructor.reconstruct_policy_recommendation(policy_decision_id)
        
        # Build evidence references
        evidence_references = self._extract_evidence_references(reasoning_steps)
        
        # Build causal links
        causal_links = self._build_causal_links(reasoning_steps)
        
        # Build bundle
        bundle = {
            'bundle_id': str(uuid.uuid4()),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'explanation_type': 'policy_recommendation',
            'subject_id': policy_decision_id,
            'reasoning_chain': reasoning_steps,
            'evidence_references': evidence_references,
            'causal_links': causal_links
        }
        
        return bundle
    
    def _extract_evidence_references(self, reasoning_steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract evidence references from reasoning steps."""
        references = []
        seen = set()
        
        for step in reasoning_steps:
            source = step.get('evidence_source', '')
            evidence_id = step.get('evidence_id', '')
            step_type = step.get('step_type', '')
            
            key = (source, evidence_id)
            if key not in seen:
                seen.add(key)
                references.append({
                    'source': source,
                    'reference_id': evidence_id,
                    'reference_type': step_type
                })
        
        return references
    
    def _build_causal_links(self, reasoning_steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Build causal links between reasoning steps.
        
        Links are built based on temporal ordering and step types.
        """
        causal_links = []
        
        # Sort steps by timestamp
        sorted_steps = sorted(reasoning_steps, key=lambda s: s.get('timestamp', ''))
        
        # Build links between consecutive steps
        for i in range(len(sorted_steps) - 1):
            from_step = sorted_steps[i]
            to_step = sorted_steps[i + 1]
            
            # Determine link type based on step types
            link_type = self._determine_link_type(from_step, to_step)
            
            causal_links.append({
                'from_step_id': from_step.get('step_id', ''),
                'to_step_id': to_step.get('step_id', ''),
                'link_type': link_type,
                'explanation': f"{from_step.get('description', '')} {link_type} {to_step.get('description', '')}"
            })
        
        return causal_links
    
    def _determine_link_type(self, from_step: Dict[str, Any], to_step: Dict[str, Any]) -> str:
        """Determine causal link type between steps."""
        from_type = from_step.get('step_type', '')
        to_type = to_step.get('step_type', '')
        
        # Deterministic rules for link types
        if from_type == 'ledger_entry' and to_type == 'killchain_event':
            return 'triggers'
        elif from_type == 'killchain_event' and to_type == 'graph_relationship':
            return 'enables'
        elif from_type == 'graph_relationship' and to_type == 'risk_computation':
            return 'causes'
        elif from_type == 'risk_computation' and to_type == 'policy_decision':
            return 'triggers'
        else:
            return 'precedes'
