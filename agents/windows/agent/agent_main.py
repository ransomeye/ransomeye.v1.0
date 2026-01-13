#!/usr/bin/env python3
"""
RansomEye v1.0 Windows Agent - Main Entry Point
AUTHORITATIVE: Integrates ETW telemetry with command gate
"""

import os
import sys
import socket
import uuid
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timezone

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    _logger = setup_logging('windows-agent-main')
except ImportError:
    import logging
    _logger = logging.getLogger('windows-agent-main')

from .etw import (
    ProviderRegistry,
    ETWSessionManager,
    ETWEventParser,
    SchemaMapper,
    BufferManager,
    HealthMonitor
)
from .telemetry import (
    EventEnvelopeBuilder,
    TelemetrySigner,
    TelemetrySender
)


class WindowsAgent:
    """
    Windows Agent - ETW telemetry and command execution.
    
    CRITICAL: Agents NEVER trust the network, NEVER trust the UI.
    Agents ONLY trust signed commands. FAIL CLOSED.
    """
    
    def __init__(
        self,
        agent_id: str,
        machine_id: Optional[str] = None,
        hostname: Optional[str] = None,
        boot_id: Optional[str] = None,
        agent_version: str = "1.0.0",
        etw_buffer_dir: Optional[Path] = None,
        signing_key_path: Optional[Path] = None,
        signing_key_id: Optional[str] = None,
        core_endpoint: Optional[str] = None
    ):
        """
        Initialize Windows agent.
        
        Args:
            agent_id: Agent identifier
            machine_id: Machine identifier (default: hostname)
            hostname: Hostname (default: socket.gethostname())
            boot_id: Boot identifier (default: generated)
            agent_version: Agent version string
            etw_buffer_dir: Directory for ETW event buffering
            signing_key_path: Path to ed25519 private key for telemetry signing
            signing_key_id: Key identifier
            core_endpoint: Core endpoint URL for telemetry transmission
        """
        self.agent_id = agent_id
        self.machine_id = machine_id or socket.gethostname()
        self.hostname = hostname or socket.gethostname()
        self.boot_id = boot_id or str(uuid.uuid4())
        self.agent_version = agent_version
        
        # Initialize ETW components
        self.provider_registry = ProviderRegistry()
        self.buffer_manager = BufferManager(
            etw_buffer_dir or Path(os.getenv('RANSOMEYE_ETW_BUFFER_DIR', './etw_buffer'))
        )
        
        # Initialize telemetry components
        self.envelope_builder = EventEnvelopeBuilder(
            machine_id=self.machine_id,
            component_instance_id=self.agent_id,
            hostname=self.hostname,
            boot_id=self.boot_id,
            agent_version=self.agent_version
        )
        self.telemetry_signer = TelemetrySigner(
            private_key_path=signing_key_path,
            key_id=signing_key_id
        )
        self.telemetry_sender = TelemetrySender(self.buffer_manager)
        if core_endpoint:
            self.telemetry_sender.core_endpoint = core_endpoint
        
        # Initialize ETW processing components
        self.event_parser = ETWEventParser(self.provider_registry)
        self.schema_mapper = SchemaMapper()
        
        # Initialize health monitor
        self.health_monitor = HealthMonitor(health_callback=self._on_health_event)
        
        # Initialize ETW session manager
        self.session_manager = ETWSessionManager(
            provider_registry=self.provider_registry,
            event_callback=self._on_etw_event,
            health_callback=self._on_health_event
        )
        
        # Sequence tracking for integrity chain
        self._last_envelope_hash: Optional[str] = None
    
    def start(self):
        """Start agent (ETW collection and telemetry transmission)."""
        _logger.info("Starting Windows Agent")
        
        try:
            # Start health monitoring
            self.health_monitor.start_monitoring()
            
            # Start ETW session
            if not self.session_manager.start_session():
                _logger.error("Failed to start ETW session")
                return False
            
            # Start telemetry transmission thread
            self.telemetry_sender.start_transmission_thread()
            
            _logger.info("Windows Agent started successfully")
            return True
            
        except Exception as e:
            _logger.error(f"Failed to start Windows Agent: {e}", exc_info=True)
            return False
    
    def stop(self):
        """Stop agent (graceful shutdown)."""
        _logger.info("Stopping Windows Agent")
        
        try:
            # Stop ETW session
            self.session_manager.stop_session()
            
            # Stop telemetry transmission
            self.telemetry_sender.stop_transmission_thread()
            
            # Stop health monitoring
            self.health_monitor.stop_monitoring()
            
            _logger.info("Windows Agent stopped")
            
        except Exception as e:
            _logger.error(f"Error stopping Windows Agent: {e}", exc_info=True)
    
    def _on_etw_event(self, event_dict: Dict[str, Any]):
        """
        Handle ETW event from session manager.
        
        Args:
            event_dict: Raw ETW event dictionary
        """
        try:
            # Parse ETW event
            provider_id = event_dict.get('provider_id')
            event_id = event_dict.get('event_id')
            timestamp_str = event_dict.get('timestamp')
            event_data = event_dict.get('event_data', b'')
            
            if not provider_id or not event_id:
                return
            
            # Parse timestamp
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except Exception:
                timestamp = datetime.now(timezone.utc)
            
            # Parse event
            parsed_event = self.event_parser.parse_event(
                provider_id=provider_id,
                event_id=event_id,
                timestamp=timestamp,
                event_data=event_data
            )
            
            if not parsed_event:
                return  # Event filtered or rejected
            
            # Map to normalized schema
            normalized_event = self.schema_mapper.map_to_normalized(parsed_event)
            
            if not normalized_event:
                return  # Event filtered
            
            # Record event for health monitoring
            sequence = self.envelope_builder.get_sequence()
            self.health_monitor.record_event(provider_id, event_id, sequence)
            
            # Build event envelope
            observed_at = datetime.fromisoformat(parsed_event.get('timestamp', '').replace('Z', '+00:00'))
            envelope = self.envelope_builder.build_envelope(
                payload=normalized_event,
                observed_at=observed_at,
                prev_hash=self._last_envelope_hash
            )
            
            # Sign envelope
            signed_envelope = self.telemetry_signer.sign_envelope(envelope)
            
            # Update previous hash for integrity chain
            self._last_envelope_hash = signed_envelope['integrity']['hash_sha256']
            
            # Send event (or buffer if offline)
            self.telemetry_sender.send_event(signed_envelope)
            
        except Exception as e:
            _logger.error(f"Error processing ETW event: {e}", exc_info=True)
            # Continue - fail-open behavior
    
    def _on_health_event(self, event_type: str, data: Dict[str, Any]):
        """
        Handle health event from health monitor or session manager.
        
        Args:
            event_type: Health event type
            data: Health event data
        """
        try:
            # Build health event envelope
            health_payload = {
                'health_event_type': event_type,
                **data
            }
            
            envelope = self.envelope_builder.build_envelope(
                payload=health_payload,
                prev_hash=self._last_envelope_hash
            )
            
            # Sign envelope
            signed_envelope = self.telemetry_signer.sign_envelope(envelope)
            
            # Update previous hash
            self._last_envelope_hash = signed_envelope['integrity']['hash_sha256']
            
            # Send health event
            self.telemetry_sender.send_event(signed_envelope)
            
        except Exception as e:
            _logger.error(f"Error processing health event: {e}", exc_info=True)
    
    def get_agent_stats(self) -> Dict[str, Any]:
        """
        Get agent statistics.
        
        Returns:
            Dictionary with agent statistics
        """
        return {
            'agent_id': self.agent_id,
            'machine_id': self.machine_id,
            'hostname': self.hostname,
            'boot_id': self.boot_id,
            'agent_version': self.agent_version,
            'etw_session_active': self.session_manager.is_session_active(),
            'etw_session_stats': self.session_manager.get_session_stats(),
            'buffer_stats': self.buffer_manager.get_buffer_stats(),
            'health_stats': self.health_monitor.get_health_stats(),
            'transmission_stats': self.telemetry_sender.get_transmission_stats()
        }


def main():
    """Main entry point for Windows Agent."""
    import argparse
    
    parser = argparse.ArgumentParser(description='RansomEye Windows Agent')
    parser.add_argument('--agent-id', required=True, help='Agent identifier')
    parser.add_argument('--machine-id', help='Machine identifier')
    parser.add_argument('--hostname', help='Hostname')
    parser.add_argument('--boot-id', help='Boot identifier')
    parser.add_argument('--etw-buffer-dir', type=Path, help='ETW buffer directory')
    parser.add_argument('--signing-key-path', type=Path, help='Path to signing key')
    parser.add_argument('--signing-key-id', help='Signing key identifier')
    parser.add_argument('--core-endpoint', help='Core endpoint URL')
    
    args = parser.parse_args()
    
    # Create agent
    agent = WindowsAgent(
        agent_id=args.agent_id,
        machine_id=args.machine_id,
        hostname=args.hostname,
        boot_id=args.boot_id,
        etw_buffer_dir=args.etw_buffer_dir,
        signing_key_path=args.signing_key_path,
        signing_key_id=args.signing_key_id,
        core_endpoint=args.core_endpoint
    )
    
    # Start agent
    if not agent.start():
        _logger.error("Failed to start agent")
        sys.exit(1)
    
    # Run until interrupted
    try:
        import signal
        signal.signal(signal.SIGINT, lambda s, f: agent.stop())
        signal.signal(signal.SIGTERM, lambda s, f: agent.stop())
        
        # Keep running
        import time
        while True:
            time.sleep(1.0)
    
    except KeyboardInterrupt:
        _logger.info("Received interrupt signal")
    finally:
        agent.stop()


if __name__ == '__main__':
    main()
