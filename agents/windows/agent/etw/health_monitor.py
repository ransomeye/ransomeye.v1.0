#!/usr/bin/env python3
"""
RansomEye v1.0 Windows Agent - Health Monitor
AUTHORITATIVE: ETW session health monitoring and telemetry loss detection
"""

import os
import sys
import time
import threading
from typing import Dict, Any, Optional, Callable
from collections import defaultdict
from datetime import datetime, timezone, timedelta

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    _logger = setup_logging('windows-agent-etw-health')
except ImportError:
    import logging
    _logger = logging.getLogger('windows-agent-etw-health')


class HealthMonitor:
    """
    ETW session health monitor.
    
    CRITICAL: Monitors provider liveness, event rates, and telemetry loss.
    """
    
    def __init__(
        self,
        health_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ):
        """
        Initialize health monitor.
        
        Args:
            health_callback: Callback for health events (event_type, data) -> None
        """
        self.health_callback = health_callback
        
        # Event rate tracking (per provider)
        self._event_counts: Dict[str, int] = defaultdict(int)
        self._event_timestamps: Dict[str, list] = defaultdict(list)
        self._rate_lock = threading.Lock()
        
        # Sequence tracking (for loss detection)
        self._last_sequence: Dict[str, int] = defaultdict(int)
        self._sequence_gaps: Dict[str, int] = defaultdict(int)
        self._sequence_lock = threading.Lock()
        
        # Provider liveness tracking
        self._provider_last_seen: Dict[str, datetime] = {}
        self._provider_failures: Dict[str, int] = defaultdict(int)
        self._liveness_lock = threading.Lock()
        
        # Session restart tracking
        self._session_restart_count = 0
        self._last_restart_time: Optional[datetime] = None
        
        # Monitoring thread
        self._monitoring_active = False
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
    
    def start_monitoring(self):
        """Start health monitoring thread."""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._stop_event.clear()
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="ETW-Health-Monitor"
        )
        self._monitoring_thread.start()
        _logger.info("Health monitoring started")
    
    def stop_monitoring(self):
        """Stop health monitoring thread."""
        if not self._monitoring_active:
            return
        
        self._monitoring_active = False
        self._stop_event.set()
        
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5.0)
        
        _logger.info("Health monitoring stopped")
    
    def record_event(self, provider_id: str, event_id: int, sequence: Optional[int] = None):
        """
        Record event for rate monitoring and loss detection.
        
        Args:
            provider_id: Provider GUID
            event_id: Event ID
            sequence: Optional sequence number for loss detection
        """
        now = datetime.now(timezone.utc)
        
        # Update event rate
        with self._rate_lock:
            self._event_counts[provider_id] += 1
            self._event_timestamps[provider_id].append(now)
            
            # Keep only last 60 seconds of timestamps
            cutoff = now - timedelta(seconds=60)
            self._event_timestamps[provider_id] = [
                ts for ts in self._event_timestamps[provider_id] if ts > cutoff
            ]
        
        # Update sequence tracking
        if sequence is not None:
            with self._sequence_lock:
                last_seq = self._last_sequence[provider_id]
                if sequence > last_seq + 1:
                    # Sequence gap detected
                    gap_size = sequence - last_seq - 1
                    self._sequence_gaps[provider_id] += gap_size
                    _logger.warning(
                        f"Sequence gap detected for provider {provider_id}: "
                        f"expected {last_seq + 1}, got {sequence} (gap: {gap_size})"
                    )
                
                self._last_sequence[provider_id] = sequence
        
        # Update provider liveness
        with self._liveness_lock:
            self._provider_last_seen[provider_id] = now
            self._provider_failures[provider_id] = 0  # Reset failure count
    
    def record_provider_failure(self, provider_id: str, error: str):
        """
        Record provider failure.
        
        Args:
            provider_id: Provider GUID
            error: Error message
        """
        with self._liveness_lock:
            self._provider_failures[provider_id] += 1
        
        _logger.error(f"Provider failure: {provider_id} - {error}")
        
        # Emit health event
        if self.health_callback:
            self.health_callback('provider_failure', {
                'provider_id': provider_id,
                'error': error,
                'failure_count': self._provider_failures[provider_id],
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
    
    def record_session_restart(self):
        """Record ETW session restart."""
        self._session_restart_count += 1
        self._last_restart_time = datetime.now(timezone.utc)
        
        _logger.info(f"ETW session restart recorded (count: {self._session_restart_count})")
        
        # Emit health event
        if self.health_callback:
            self.health_callback('session_restart', {
                'restart_count': self._session_restart_count,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
    
    def _monitoring_loop(self):
        """Main health monitoring loop."""
        _logger.info("Health monitoring loop started")
        
        try:
            while not self._stop_event.is_set():
                try:
                    # Check event rates
                    self._check_event_rates()
                    
                    # Check provider liveness
                    self._check_provider_liveness()
                    
                    # Check sequence gaps
                    self._check_sequence_gaps()
                    
                    # Sleep before next check
                    self._stop_event.wait(timeout=30.0)  # Check every 30 seconds
                    
                except Exception as e:
                    _logger.error(f"Error in health monitoring loop: {e}", exc_info=True)
                    time.sleep(5.0)
        
        except Exception as e:
            _logger.error(f"Fatal error in health monitoring loop: {e}", exc_info=True)
    
    def _check_event_rates(self):
        """Check event rates per provider."""
        with self._rate_lock:
            for provider_id, timestamps in self._event_timestamps.items():
                if not timestamps:
                    continue
                
                # Calculate events per second
                time_span = (timestamps[-1] - timestamps[0]).total_seconds()
                if time_span > 0:
                    events_per_second = len(timestamps) / time_span
                    
                    # Check for abnormal rates
                    if events_per_second > 10000:
                        _logger.warning(
                            f"High event rate for provider {provider_id}: "
                            f"{events_per_second:.2f} events/second"
                        )
                        
                        if self.health_callback:
                            self.health_callback('high_event_rate', {
                                'provider_id': provider_id,
                                'events_per_second': events_per_second,
                                'timestamp': datetime.now(timezone.utc).isoformat()
                            })
    
    def _check_provider_liveness(self):
        """Check provider liveness (no events for > 5 minutes)."""
        now = datetime.now(timezone.utc)
        threshold = timedelta(minutes=5)
        
        with self._liveness_lock:
            for provider_id, last_seen in self._provider_last_seen.items():
                if now - last_seen > threshold:
                    failure_count = self._provider_failures[provider_id]
                    if failure_count == 0:  # First time detecting issue
                        _logger.warning(
                            f"Provider {provider_id} appears inactive "
                            f"(last seen: {last_seen.isoformat()})"
                        )
                        
                        if self.health_callback:
                            self.health_callback('provider_inactive', {
                                'provider_id': provider_id,
                                'last_seen': last_seen.isoformat(),
                                'inactive_duration_seconds': (now - last_seen).total_seconds(),
                                'timestamp': datetime.now(timezone.utc).isoformat()
                            })
    
    def _check_sequence_gaps(self):
        """Check for sequence gaps (telemetry loss)."""
        with self._sequence_lock:
            for provider_id, gap_count in self._sequence_gaps.items():
                if gap_count > 0:
                    _logger.warning(
                        f"Telemetry loss detected for provider {provider_id}: "
                        f"{gap_count} events lost"
                    )
                    
                    if self.health_callback:
                        self.health_callback('telemetry_loss', {
                            'provider_id': provider_id,
                            'events_lost': gap_count,
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        })
                    
                    # Reset gap count after reporting
                    self._sequence_gaps[provider_id] = 0
    
    def get_health_stats(self) -> Dict[str, Any]:
        """
        Get health statistics.
        
        Returns:
            Dictionary with health statistics
        """
        with self._rate_lock:
            event_rates = {}
            for provider_id, timestamps in self._event_timestamps.items():
                if timestamps:
                    time_span = (timestamps[-1] - timestamps[0]).total_seconds()
                    if time_span > 0:
                        event_rates[provider_id] = len(timestamps) / time_span
                    else:
                        event_rates[provider_id] = 0.0
                else:
                    event_rates[provider_id] = 0.0
        
        with self._sequence_lock:
            sequence_gaps = dict(self._sequence_gaps)
            last_sequences = dict(self._last_sequence)
        
        with self._liveness_lock:
            provider_last_seen = {
                pid: ts.isoformat() 
                for pid, ts in self._provider_last_seen.items()
            }
            provider_failures = dict(self._provider_failures)
        
        return {
            'monitoring_active': self._monitoring_active,
            'event_rates_per_second': event_rates,
            'sequence_gaps': sequence_gaps,
            'last_sequences': last_sequences,
            'provider_last_seen': provider_last_seen,
            'provider_failures': provider_failures,
            'session_restart_count': self._session_restart_count,
            'last_restart_time': self._last_restart_time.isoformat() if self._last_restart_time else None
        }
