#!/usr/bin/env python3
"""
RansomEye Explanation Assembly Engine - Assembly Engine
AUTHORITATIVE: Deterministic assembly of explanations into audience-specific views
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid


class AssemblyError(Exception):
    """Base exception for assembly errors."""
    pass


class AssemblyEngine:
    """
    Deterministic assembly of explanations into audience-specific views.
    
    Properties:
    - Deterministic: Same inputs always produce same outputs
    - Read-only: Never modifies source explanations
    - No generation: Only reorders, filters, and presents
    - No inference: No new facts, no summarization
    """
    
    # View-specific ordering rules (explicit, no heuristics)
    VIEW_ORDERING_RULES = {
        'SOC_ANALYST': ['CHRONOLOGICAL', 'TECHNICAL_HIERARCHY'],
        'INCIDENT_COMMANDER': ['RISK_IMPACT', 'ACCOUNTABILITY_CHAIN', 'CHRONOLOGICAL'],
        'EXECUTIVE': ['RISK_IMPACT', 'ACCOUNTABILITY_CHAIN'],
        'REGULATOR': ['LEDGER_ORDER', 'CHAIN_OF_CUSTODY', 'CHRONOLOGICAL']
    }
    
    def __init__(self):
        """Initialize assembly engine."""
        pass
    
    def assemble_explanation(
        self,
        incident_id: str,
        view_type: str,
        source_explanation_bundle_ids: List[str],
        source_alert_ids: List[str],
        source_context_block_ids: List[str],
        source_risk_ids: List[str],
        source_content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assemble explanation into audience-specific view.
        
        Rules:
        - Deterministic: Same inputs → same output
        - No text generation
        - No paraphrasing
        - No new facts
        - No inference
        - Only reordering and filtering
        
        Args:
            incident_id: Incident identifier
            view_type: View type (SOC_ANALYST, INCIDENT_COMMANDER, EXECUTIVE, REGULATOR)
            source_explanation_bundle_ids: SEE bundle identifiers
            source_alert_ids: Alert identifiers
            source_context_block_ids: Alert context block identifiers
            source_risk_ids: Risk score identifiers
            source_content: Dictionary of source content (read-only references)
        
        Returns:
            Assembled explanation dictionary
        """
        # Validate view_type
        valid_view_types = ['SOC_ANALYST', 'INCIDENT_COMMANDER', 'EXECUTIVE', 'REGULATOR']
        if view_type not in valid_view_types:
            raise AssemblyError(f"Invalid view_type: {view_type}. Must be one of {valid_view_types}")
        
        # Get ordering rules for view_type
        ordering_rules = self.VIEW_ORDERING_RULES.get(view_type, [])
        
        # Build content blocks from source content (read-only, no modification)
        content_blocks = []
        display_order = 0
        
        # Process SEE bundles
        for bundle_id in source_explanation_bundle_ids:
            if bundle_id in source_content.get('see_bundles', {}):
                content_blocks.append({
                    'block_id': str(uuid.uuid4()),
                    'source_type': 'SEE_BUNDLE',
                    'source_id': bundle_id,
                    'content_type': 'CAUSALITY',
                    'content_reference': source_content['see_bundles'][bundle_id].get('reference', ''),
                    'display_order': display_order
                })
                display_order += 1
        
        # Process alerts
        for alert_id in source_alert_ids:
            if alert_id in source_content.get('alerts', {}):
                content_blocks.append({
                    'block_id': str(uuid.uuid4()),
                    'source_type': 'ALERT',
                    'source_id': alert_id,
                    'content_type': 'TECHNICAL_DETAIL',
                    'content_reference': source_content['alerts'][alert_id].get('reference', ''),
                    'display_order': display_order
                })
                display_order += 1
        
        # Process alert contexts
        for context_block_id in source_context_block_ids:
            if context_block_id in source_content.get('alert_contexts', {}):
                content_blocks.append({
                    'block_id': str(uuid.uuid4()),
                    'source_type': 'ALERT_CONTEXT',
                    'source_id': context_block_id,
                    'content_type': 'BEHAVIORAL_CONTEXT',
                    'content_reference': source_content['alert_contexts'][context_block_id].get('reference', ''),
                    'display_order': display_order
                })
                display_order += 1
        
        # Process risk scores
        for risk_id in source_risk_ids:
            if risk_id in source_content.get('risk_scores', {}):
                content_blocks.append({
                    'block_id': str(uuid.uuid4()),
                    'source_type': 'RISK_SCORE',
                    'source_id': risk_id,
                    'content_type': 'RISK_ASSESSMENT',
                    'content_reference': source_content['risk_scores'][risk_id].get('reference', ''),
                    'display_order': display_order
                })
                display_order += 1
        
        # Apply ordering rules (deterministic)
        content_blocks = self._apply_ordering_rules(content_blocks, ordering_rules, source_content)
        
        # Reassign display_order after sorting
        for idx, block in enumerate(content_blocks):
            block['display_order'] = idx
        
        # Create assembled explanation
        assembled_explanation_id = str(uuid.uuid4())
        assembled_explanation = {
            'assembled_explanation_id': assembled_explanation_id,
            'incident_id': incident_id,
            'view_type': view_type,
            'source_explanation_bundle_ids': source_explanation_bundle_ids,
            'source_alert_ids': source_alert_ids,
            'source_context_block_ids': source_context_block_ids,
            'source_risk_ids': source_risk_ids,
            'ordering_rules_applied': ordering_rules,
            'content_blocks': content_blocks,
            'integrity_hash': '',  # Will be set by hasher
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        
        return assembled_explanation
    
    def _apply_ordering_rules(
        self,
        content_blocks: List[Dict[str, Any]],
        ordering_rules: List[str],
        source_content: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Apply explicit ordering rules (deterministic, no heuristics).
        
        Args:
            content_blocks: List of content blocks
            ordering_rules: List of ordering rule names
            source_content: Source content dictionary (read-only)
        
        Returns:
            Ordered list of content blocks
        """
        if not ordering_rules:
            return content_blocks
        
        # Apply rules in order (deterministic)
        ordered_blocks = content_blocks.copy()
        
        for rule in ordering_rules:
            if rule == 'CHRONOLOGICAL':
                # Sort by timestamp if available (deterministic)
                ordered_blocks.sort(key=lambda x: source_content.get('timestamps', {}).get(x['source_id'], ''))
            elif rule == 'TECHNICAL_HIERARCHY':
                # Sort by source_type hierarchy (deterministic)
                type_order = {
                    'SEE_BUNDLE': 0,
                    'ALERT': 1,
                    'ALERT_CONTEXT': 2,
                    'RISK_SCORE': 3,
                    'KILLCHAIN': 4,
                    'THREAT_GRAPH': 5
                }
                ordered_blocks.sort(key=lambda x: type_order.get(x['source_type'], 999))
            elif rule == 'RISK_IMPACT':
                # Sort by risk score if available (deterministic)
                ordered_blocks.sort(key=lambda x: source_content.get('risk_scores', {}).get(x['source_id'], {}).get('score', 0), reverse=True)
            elif rule == 'ACCOUNTABILITY_CHAIN':
                # Sort by accountability order (deterministic)
                ordered_blocks.sort(key=lambda x: source_content.get('accountability', {}).get(x['source_id'], 999))
            elif rule == 'LEDGER_ORDER':
                # Sort by ledger entry order (deterministic)
                ordered_blocks.sort(key=lambda x: source_content.get('ledger_order', {}).get(x['source_id'], 999))
            elif rule == 'CHAIN_OF_CUSTODY':
                # Sort by chain-of-custody order (deterministic)
                ordered_blocks.sort(key=lambda x: source_content.get('chain_of_custody', {}).get(x['source_id'], 999))
        
        return ordered_blocks
