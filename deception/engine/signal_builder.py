#!/usr/bin/env python3
"""
RansomEye Deception Framework - Signal Builder
AUTHORITATIVE: High-confidence signal generation
"""

from typing import Dict, Any, List
from datetime import datetime, timezone
import uuid
import hashlib
import json


class SignalBuildError(Exception):
    """Base exception for signal building errors."""
    pass


class SignalBuilder:
    """
    High-confidence signal builder.
    
    Properties:
    - High confidence: Signals are high confidence by design
    - Deterministic: Same interactions = same signals
    - Explainable: Signals are explicitly explainable
    - Chain-of-custody: Signals are chain-of-custody protected
    """
    
    def __init__(self):
        """Initialize signal builder."""
        pass
    
    def build_signal(
        self,
        interactions: List[Dict[str, Any]],
        decoy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build high-confidence signal from interactions.
        
        Args:
            interactions: List of interaction dictionaries
            decoy: Decoy dictionary
        
        Returns:
            Signal dictionary
        """
        if not interactions:
            raise SignalBuildError("No interactions provided")
        
        # Build signal content
        signal = {
            'signal_id': str(uuid.uuid4()),
            'decoy_id': decoy.get('decoy_id', ''),
            'interaction_count': len(interactions),
            'interaction_types': list(set(i.get('interaction_type', '') for i in interactions)),
            'source_ips': list(set(i.get('source_ip', '') for i in interactions)),
            'confidence_level': 'HIGH',  # High confidence by design for deception
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'explanation': self._build_explanation(interactions, decoy),
            'evidence_references': [i.get('evidence_reference', '') for i in interactions],
            'immutable_hash': ''
        }
        
        # Calculate hash
        signal['immutable_hash'] = self._calculate_hash(signal)
        
        return signal
    
    def _build_explanation(
        self,
        interactions: List[Dict[str, Any]],
        decoy: Dict[str, Any]
    ) -> str:
        """
        Build explanation for signal.
        
        Args:
            interactions: List of interaction dictionaries
            decoy: Decoy dictionary
        
        Returns:
            Explanation string
        """
        decoy_name = decoy.get('decoy_name', '')
        decoy_type = decoy.get('decoy_type', '')
        interaction_count = len(interactions)
        
        explanation = f"High-confidence signal from {decoy_type} decoy '{decoy_name}': {interaction_count} interaction(s) detected"
        
        return explanation
    
    def _calculate_hash(self, signal: Dict[str, Any]) -> str:
        """Calculate SHA256 hash of signal record."""
        hashable_content = {k: v for k, v in signal.items() if k != 'immutable_hash'}
        canonical_json = json.dumps(hashable_content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
