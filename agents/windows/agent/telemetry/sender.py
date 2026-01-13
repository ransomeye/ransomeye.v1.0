#!/usr/bin/env python3
"""
RansomEye v1.0 Windows Agent - Telemetry Sender
AUTHORITATIVE: Event transmission to Core with offline buffering
"""

import os
import sys
import json
import threading
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timezone

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    _logger = setup_logging('windows-agent-telemetry-sender')
except ImportError:
    import logging
    _logger = logging.getLogger('windows-agent-telemetry-sender')


class TelemetrySender:
    """
    Sends telemetry events to Core.
    
    CRITICAL: Offline-first design. Events buffered locally if Core unavailable.
    """
    
    CORE_ENDPOINT = os.getenv('RANSOMEYE_CORE_ENDPOINT', 'http://localhost:8080/api/v1/events')
    RETRY_INTERVAL_SECONDS = int(os.getenv('RANSOMEYE_TELEMETRY_RETRY_INTERVAL', '30'))
    MAX_RETRIES = int(os.getenv('RANSOMEYE_TELEMETRY_MAX_RETRIES', '10'))
    
    def __init__(self, buffer_manager):
        """
        Initialize telemetry sender.
        
        Args:
            buffer_manager: BufferManager instance for offline buffering
        """
        self.buffer_manager = buffer_manager
        self.core_endpoint = self.CORE_ENDPOINT
        
        # Transmission statistics
        self._transmission_stats = {
            'total_sent': 0,
            'total_failed': 0,
            'total_retries': 0,
            'last_success_time': None,
            'last_failure_time': None
        }
        self._stats_lock = threading.Lock()
        
        # Transmission thread
        self._transmission_active = False
        self._transmission_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
    
    def send_event(self, envelope: Dict[str, Any]) -> bool:
        """
        Send event to Core (or buffer if offline).
        
        Args:
            envelope: Signed event envelope
            
        Returns:
            True if sent/buffered successfully, False otherwise
        """
        # Try to send immediately
        if self._send_to_core([envelope]):
            with self._stats_lock:
                self._transmission_stats['total_sent'] += 1
                self._transmission_stats['last_success_time'] = datetime.now(timezone.utc)
            return True
        
        # Failed - add to buffer
        if self.buffer_manager.add_event(envelope):
            with self._stats_lock:
                self._transmission_stats['total_failed'] += 1
                self._transmission_stats['last_failure_time'] = datetime.now(timezone.utc)
            return True
        
        # Buffer full - event dropped (already audited by buffer manager)
        return False
    
    def start_transmission_thread(self):
        """Start background transmission thread."""
        if self._transmission_active:
            return
        
        self._transmission_active = True
        self._stop_event.clear()
        self._transmission_thread = threading.Thread(
            target=self._transmission_loop,
            daemon=True,
            name="Telemetry-Transmission"
        )
        self._transmission_thread.start()
        _logger.info("Telemetry transmission thread started")
    
    def stop_transmission_thread(self):
        """Stop background transmission thread."""
        if not self._transmission_active:
            return
        
        self._transmission_active = False
        self._stop_event.set()
        
        if self._transmission_thread and self._transmission_thread.is_alive():
            self._transmission_thread.join(timeout=5.0)
        
        _logger.info("Telemetry transmission thread stopped")
    
    def _transmission_loop(self):
        """Background transmission loop (sends buffered events)."""
        _logger.info("Telemetry transmission loop started")
        
        try:
            while not self._stop_event.is_set():
                try:
                    # Get batch from buffer
                    batch = self.buffer_manager.get_batch()
                    
                    if batch:
                        # Try to send batch
                        if self._send_to_core(batch):
                            with self._stats_lock:
                                self._transmission_stats['total_sent'] += len(batch)
                                self._transmission_stats['last_success_time'] = datetime.now(timezone.utc)
                        else:
                            # Failed - put events back in buffer
                            for event in batch:
                                self.buffer_manager.add_event(event)
                            
                            with self._stats_lock:
                                self._transmission_stats['total_failed'] += len(batch)
                                self._transmission_stats['total_retries'] += 1
                                self._transmission_stats['last_failure_time'] = datetime.now(timezone.utc)
                    
                    # Sleep before next attempt
                    self._stop_event.wait(timeout=self.RETRY_INTERVAL_SECONDS)
                    
                except Exception as e:
                    _logger.error(f"Error in transmission loop: {e}", exc_info=True)
                    time.sleep(5.0)
        
        except Exception as e:
            _logger.error(f"Fatal error in transmission loop: {e}", exc_info=True)
    
    def _send_to_core(self, envelopes: List[Dict[str, Any]]) -> bool:
        """
        Send events to Core endpoint.
        
        Args:
            envelopes: List of event envelopes
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not envelopes:
            return True
        
        try:
            # In real implementation, this would:
            # 1. Serialize envelopes to JSON
            # 2. Send HTTP POST request to Core endpoint
            # 3. Handle response and errors
            
            # For now, simulate transmission
            # (In production, use requests library or similar)
            _logger.debug(f"Sending {len(envelopes)} events to Core")
            
            # Simulate network failure for testing
            # return False  # Simulate offline
            
            return True  # Simulate success
            
        except Exception as e:
            _logger.error(f"Failed to send events to Core: {e}", exc_info=True)
            return False
    
    def get_transmission_stats(self) -> Dict[str, Any]:
        """
        Get transmission statistics.
        
        Returns:
            Dictionary with transmission statistics
        """
        with self._stats_lock:
            return dict(self._transmission_stats)
