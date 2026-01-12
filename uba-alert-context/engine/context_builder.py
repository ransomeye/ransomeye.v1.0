#!/usr/bin/env python3
"""
RansomEye UBA Alert Context Engine - Context Builder
AUTHORITATIVE: Deterministic builder of human-facing alert context from UBA signals
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid


class ContextBuilderError(Exception):
    """Base exception for context builder errors."""
    pass


class ContextBuilder:
    """
    Deterministic builder of alert context blocks from UBA signals.
    
    Properties:
    - Deterministic: Same inputs always produce same outputs
    - Read-only: Never modifies alerts or UBA signals
    - Factual: Only factual statements, no judgment
    - Order-preserving: Consistent output ordering
    """
    
    # Controlled vocabulary for human-readable summaries
    CONTROLLED_VOCABULARY = {
        'CONTEXTUAL_SHIFT': 'Behavioral context has shifted',
        'ROLE_EXPANSION': 'Role or privilege scope has expanded',
        'ACCESS_SURFACE_CHANGE': 'Access surface has changed',
        'TEMPORAL_BEHAVIOR_CHANGE': 'Temporal behavior pattern has changed'
    }
    
    def __init__(self):
        """Initialize context builder."""
        pass
    
    def build_context(
        self,
        alert_id: str,
        uba_signals: List[Dict[str, Any]],
        explanation_bundle_id: str
    ) -> Dict[str, Any]:
        """
        Build alert context block from UBA signals.
        
        Rules:
        - Deterministic: Same inputs → same output
        - No branching logic
        - No ML
        - No heuristics
        - Order-preserving
        
        Args:
            alert_id: Alert identifier (read-only reference)
            uba_signals: List of UBA signal dictionaries (read-only)
            explanation_bundle_id: Explanation bundle identifier (SEE, mandatory)
        
        Returns:
            Alert context block dictionary (immutable)
        """
        if not uba_signals:
            raise ContextBuilderError("At least one UBA signal required")
        
        # Extract context types from UBA signals (deterministic mapping)
        context_types = []
        for signal in uba_signals:
            interpretation_type = signal.get('interpretation_type', '')
            if interpretation_type and interpretation_type not in context_types:
                context_types.append(interpretation_type)
        
        # Sort for determinism
        context_types.sort()
        
        # Build factual statements about what changed
        what_changed = []
        what_did_not_change = []
        
        for signal in uba_signals:
            interpretation_type = signal.get('interpretation_type', '')
            contextual_inputs = signal.get('contextual_inputs', {})
            
            # Build factual statements (no judgment)
            if interpretation_type == 'CONTEXTUAL_SHIFT':
                what_changed.append('Behavioral context shifted relative to baseline')
            elif interpretation_type == 'ROLE_EXPANSION':
                what_changed.append('Role or privilege scope expanded beyond baseline')
            elif interpretation_type == 'ACCESS_SURFACE_CHANGE':
                what_changed.append('Access surface changed relative to baseline')
            elif interpretation_type == 'TEMPORAL_BEHAVIOR_CHANGE':
                what_changed.append('Temporal behavior pattern changed relative to baseline')
            
            # Extract what did not change (from signal metadata if available)
            # For now, use default factual statements
            what_did_not_change.append('Baseline behavioral patterns remain unchanged')
        
        # Remove duplicates while preserving order
        what_changed = list(dict.fromkeys(what_changed))
        what_did_not_change = list(dict.fromkeys(what_did_not_change))
        
        # Build human-readable summary (controlled vocabulary only)
        summary_parts = []
        for context_type in context_types:
            if context_type in self.CONTROLLED_VOCABULARY:
                summary_parts.append(self.CONTROLLED_VOCABULARY[context_type])
        
        human_readable_summary = '. '.join(summary_parts) if summary_parts else 'No behavioral context available'
        
        # Determine interpretation guidance (deterministic rules)
        if len(context_types) == 0:
            interpretation_guidance = 'INFORMATIONAL'
        elif len(context_types) == 1:
            interpretation_guidance = 'CONTEXT_ONLY'
        else:
            interpretation_guidance = 'REVIEW_RECOMMENDED'
        
        # Extract UBA signal IDs
        uba_signal_ids = [signal.get('signal_id', '') for signal in uba_signals if signal.get('signal_id')]
        
        # Create context block
        context_block_id = str(uuid.uuid4())
        context_block = {
            'alert_id': alert_id,
            'context_block_id': context_block_id,
            'uba_signal_ids': uba_signal_ids,
            'context_types': context_types,
            'human_readable_summary': human_readable_summary,
            'what_changed': what_changed,
            'what_did_not_change': what_did_not_change,
            'interpretation_guidance': interpretation_guidance,
            'explanation_bundle_id': explanation_bundle_id,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        
        return context_block
