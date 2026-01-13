#!/usr/bin/env python3
"""
RansomEye v1.0 Windows Agent - Event Envelope Builder
AUTHORITATIVE: Constructs canonical event envelopes per event-envelope.schema.json
"""

import os
import sys
import uuid
import json
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timezone

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    _logger = setup_logging('windows-agent-telemetry-envelope')
except ImportError:
    import logging
    _logger = logging.getLogger('windows-agent-telemetry-envelope')


class EventEnvelopeBuilder:
    """
    Builds canonical event envelopes.
    
    CRITICAL: Envelopes must conform to event-envelope.schema.json exactly.
    """
    
    def __init__(
        self,
        machine_id: str,
        component_instance_id: str,
        hostname: str,
        boot_id: str,
        agent_version: str
    ):
        """
        Initialize event envelope builder.
        
        Args:
            machine_id: Machine identifier
            component_instance_id: Component instance identifier
            hostname: Hostname
            boot_id: Boot identifier
            agent_version: Agent version string
        """
        self.machine_id = machine_id
        self.component_instance_id = component_instance_id
        self.hostname = hostname
        self.boot_id = boot_id
        self.agent_version = agent_version
        
        # Sequence number (monotonic, per component instance)
        self._sequence = 0
        self._sequence_lock = threading.Lock() if 'threading' in sys.modules else None
        
        # Previous hash for integrity chain
        self._prev_hash: Optional[str] = None
    
    def build_envelope(
        self,
        payload: Dict[str, Any],
        observed_at: Optional[datetime] = None,
        prev_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build event envelope.
        
        Args:
            payload: Event payload dictionary
            observed_at: Observation timestamp (default: now)
            prev_hash: Previous event hash for integrity chain
            
        Returns:
            Event envelope dictionary (without integrity hash - added by signer)
        """
        if observed_at is None:
            observed_at = datetime.now(timezone.utc)
        
        # Generate event ID
        event_id = str(uuid.uuid4())
        
        # Get sequence number
        if self._sequence_lock:
            with self._sequence_lock:
                sequence = self._sequence
                self._sequence += 1
        else:
            sequence = self._sequence
            self._sequence += 1
        
        # Build envelope
        envelope = {
            'event_id': event_id,
            'machine_id': self.machine_id,
            'component': 'windows_agent',
            'component_instance_id': self.component_instance_id,
            'observed_at': observed_at.isoformat().replace('+00:00', 'Z'),
            'ingested_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'sequence': sequence,
            'payload': payload,
            'identity': {
                'hostname': self.hostname,
                'boot_id': self.boot_id,
                'agent_version': self.agent_version
            },
            'integrity': {
                'hash_sha256': '',  # Will be filled by signer
                'prev_hash_sha256': prev_hash or self._prev_hash
            }
        }
        
        return envelope
    
    def set_prev_hash(self, prev_hash: str):
        """
        Set previous event hash for integrity chain.
        
        Args:
            prev_hash: Previous event hash
        """
        self._prev_hash = prev_hash
    
    def get_sequence(self) -> int:
        """
        Get current sequence number.
        
        Returns:
            Current sequence number
        """
        return self._sequence
