#!/usr/bin/env python3
"""
RansomEye UBA Signal - Signal Interpreter
AUTHORITATIVE: Interpret drift deltas in context (consumer-only, no new facts)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid
import hashlib
import json
import os


class SignalInterpretationError(Exception):
    """Base exception for signal interpretation errors."""
    pass


class SignalInterpreter:
    """
    Signal interpreter (consumer-only).
    
    Properties:
    - Consumes deltas: Never produces facts
    - Explicit mappings: Explicit mappings only
    - No implicit logic: No implicit logic
    - Environment-defined: Thresholds from env vars only
    - Context-aware: Uses context references (read-only)
    """
    
    def __init__(self):
        """Initialize signal interpreter."""
        # Load configuration from environment (no hardcoded values)
        self.min_deltas_for_signal = int(os.getenv('UBA_SIGNAL_MIN_DELTAS', '1'))
    
    def interpret_deltas(
        self,
        deltas: List[Dict[str, Any]],
        identity_id: str,
        contextual_inputs: Dict[str, Any],
        explanation_bundle_id: str
    ) -> List[Dict[str, Any]]:
        """
        Interpret deltas into signals.
        
        Args:
            deltas: List of delta dictionaries
            identity_id: Identity identifier
            contextual_inputs: Context references (read-only)
            explanation_bundle_id: Explanation bundle identifier (SEE)
        
        Returns:
            List of interpreted signal dictionaries
        """
        if not deltas:
            return []
        
        if len(deltas) < self.min_deltas_for_signal:
            return []
        
        signals = []
        
        # Group deltas by type
        delta_groups = {}
        for delta in deltas:
            delta_type = delta.get('delta_type', '')
            if delta_type not in delta_groups:
                delta_groups[delta_type] = []
            delta_groups[delta_type].append(delta)
        
        # Interpret each group
        for delta_type, group_deltas in delta_groups.items():
            interpretation_type = self._map_delta_to_interpretation(delta_type, group_deltas)
            
            if interpretation_type:
                signal = self._create_signal(
                    identity_id=identity_id,
                    delta_ids=[d.get('delta_id', '') for d in group_deltas],
                    interpretation_type=interpretation_type,
                    contextual_inputs=contextual_inputs,
                    explanation_bundle_id=explanation_bundle_id,
                    downstream_consumers=self._determine_consumers(interpretation_type)
                )
                signals.append(signal)
        
        return signals
    
    def _map_delta_to_interpretation(
        self,
        delta_type: str,
        deltas: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Map delta type to interpretation type (explicit mapping only).
        
        Args:
            delta_type: Delta type
            deltas: List of deltas
        
        Returns:
            Interpretation type, or None if no mapping
        """
        # Explicit mappings (no heuristics)
        mapping = {
            'NEW_EVENT_TYPE': 'CONTEXTUAL_SHIFT',
            'NEW_HOST': 'ACCESS_SURFACE_CHANGE',
            'NEW_TIME_BUCKET': 'TEMPORAL_BEHAVIOR_CHANGE',
            'NEW_PRIVILEGE': 'ROLE_EXPANSION',
            'FREQUENCY_SHIFT': 'CONTEXTUAL_SHIFT'
        }
        
        return mapping.get(delta_type)
    
    def _determine_consumers(self, interpretation_type: str) -> List[str]:
        """
        Determine downstream consumers for interpretation type.
        
        Args:
            interpretation_type: Interpretation type
        
        Returns:
            List of consumer identifiers
        """
        # Explicit consumer mapping (no heuristics)
        consumer_map = {
            'CONTEXTUAL_SHIFT': ['risk_index', 'policy_engine', 'see'],
            'ROLE_EXPANSION': ['risk_index', 'policy_engine', 'ir_engine', 'see'],
            'ACCESS_SURFACE_CHANGE': ['risk_index', 'policy_engine', 'alert_engine', 'see'],
            'TEMPORAL_BEHAVIOR_CHANGE': ['risk_index', 'see']
        }
        
        return consumer_map.get(interpretation_type, ['see'])
    
    def _create_signal(
        self,
        identity_id: str,
        delta_ids: List[str],
        interpretation_type: str,
        contextual_inputs: Dict[str, Any],
        explanation_bundle_id: str,
        downstream_consumers: List[str]
    ) -> Dict[str, Any]:
        """Create signal dictionary."""
        # Determine if authority is required (explicit rules)
        authority_required = interpretation_type in ['ROLE_EXPANSION', 'ACCESS_SURFACE_CHANGE']
        
        signal = {
            'signal_id': str(uuid.uuid4()),
            'identity_id': identity_id,
            'delta_ids': delta_ids,
            'interpretation_type': interpretation_type,
            'contextual_inputs': contextual_inputs,
            'explanation_bundle_id': explanation_bundle_id,
            'authority_required': authority_required,
            'downstream_consumers': downstream_consumers,
            'signal_hash': '',
            'created_timestamp': datetime.now(timezone.utc).isoformat(),
            'immutable_hash': '',
            'ledger_entry_id': ''
        }
        
        # Calculate signal hash
        signal['signal_hash'] = self._calculate_signal_hash(signal)
        
        # Calculate immutable hash
        signal['immutable_hash'] = self._calculate_hash(signal)
        
        return signal
    
    def _calculate_signal_hash(self, signal: Dict[str, Any]) -> str:
        """Calculate SHA256 hash of signal content."""
        content = {
            'delta_ids': sorted(signal.get('delta_ids', [])),
            'interpretation_type': signal.get('interpretation_type', ''),
            'contextual_inputs': signal.get('contextual_inputs', {})
        }
        canonical_json = json.dumps(content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
    
    def _calculate_hash(self, signal: Dict[str, Any]) -> str:
        """Calculate SHA256 hash of signal record."""
        hashable_content = {k: v for k, v in signal.items() if k not in ['immutable_hash', 'ledger_entry_id']}
        canonical_json = json.dumps(hashable_content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
