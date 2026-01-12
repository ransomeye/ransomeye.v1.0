#!/usr/bin/env python3
"""
RansomEye Deception Framework - Interaction Collector
AUTHORITATIVE: Evidence-grade interaction capture
"""

from typing import Dict, Any
from datetime import datetime, timezone
import uuid
import hashlib
import json


class InteractionCollectionError(Exception):
    """Base exception for interaction collection errors."""
    pass


class InteractionCollector:
    """
    Evidence-grade interaction collector.
    
    Properties:
    - Immutable: Interactions are immutable facts
    - High confidence: All interactions are HIGH confidence by default
    - No aggregation: No aggregation at capture time
    - No drops: No interactions are dropped
    """
    
    def __init__(self):
        """Initialize interaction collector."""
        pass
    
    def collect_interaction(
        self,
        decoy_id: str,
        interaction_type: str,
        source_ip: str,
        source_host: str = '',
        source_process: str = '',
        evidence_reference: str = ''
    ) -> Dict[str, Any]:
        """
        Collect interaction with decoy.
        
        Args:
            decoy_id: Decoy identifier
            interaction_type: Type of interaction (auth_attempt, scan, access, command)
            source_ip: Source IP address
            source_host: Source hostname (optional)
            source_process: Source process identifier (optional)
            evidence_reference: Evidence reference identifier (optional)
        
        Returns:
            Interaction record dictionary
        """
        # Validate interaction type
        valid_types = ['auth_attempt', 'scan', 'access', 'command']
        if interaction_type not in valid_types:
            raise InteractionCollectionError(f"Invalid interaction type: {interaction_type}")
        
        # Generate evidence reference if not provided
        if not evidence_reference:
            evidence_reference = str(uuid.uuid4())
        
        # Create interaction record
        interaction = {
            'interaction_id': str(uuid.uuid4()),
            'decoy_id': decoy_id,
            'interaction_type': interaction_type,
            'source_ip': source_ip,
            'source_host': source_host,
            'source_process': source_process,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'evidence_reference': evidence_reference,
            'confidence_level': 'HIGH',  # HIGH by default for deception interactions
            'immutable_hash': '',
            'ledger_entry_id': ''
        }
        
        # Calculate hash
        interaction['immutable_hash'] = self._calculate_hash(interaction)
        
        return interaction
    
    def _calculate_hash(self, interaction: Dict[str, Any]) -> str:
        """Calculate SHA256 hash of interaction record."""
        hashable_content = {k: v for k, v in interaction.items() if k not in ['immutable_hash', 'ledger_entry_id']}
        canonical_json = json.dumps(hashable_content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
