#!/usr/bin/env python3
"""
RansomEye v1.0 GA - Ingest Service Metrics Collection
AUTHORITATIVE: Lightweight, in-memory metrics collection for operational telemetry

GA-BLOCKING: Operational telemetry ("glass cockpit") for SRE/admin visibility.
This module monitors the system, not threats.

STRICT SECURITY & PRIVACY RULES:
❌ No hostnames
❌ No IP addresses
❌ No tenant identifiers
❌ No incident metadata
❌ No file paths
❌ No payload samples

This is operational telemetry only.
"""

import time
import threading
from collections import deque
from typing import Deque, Optional
from datetime import datetime, timezone, timedelta


class IngestMetrics:
    """
    Lightweight, thread-safe metrics collection for ingest service.
    
    Metrics collected:
    - ingest_rate_eps: 1-minute moving average of events per second
    - db_write_latency_ms: Average of last ~100 DB writes
    - queue_depth: Current size of ingest/processing buffer (0 if no queue)
    - agent_heartbeat_lag_sec: Max time since last valid agent heartbeat
    
    All metrics are computed efficiently without per-query instrumentation overhead.
    """
    
    def __init__(self):
        """Initialize metrics collection."""
        self._lock = threading.Lock()
        
        # Ingest rate tracking (1-minute moving average)
        self._event_timestamps: Deque[float] = deque(maxlen=1000)  # Store timestamps, auto-prune old ones
        
        # DB write latency tracking (last ~100 writes)
        self._db_latencies_ms: Deque[float] = deque(maxlen=100)
        
        # Queue depth (connection pool exhaustion count)
        self._pool_exhaustion_count = 0
        
        # Agent heartbeat tracking (updated from external query)
        self._max_heartbeat_lag_sec: Optional[float] = None
        self._heartbeat_last_updated: Optional[float] = None
    
    def record_event_ingested(self):
        """Record that an event was ingested (for rate calculation)."""
        with self._lock:
            self._event_timestamps.append(time.time())
    
    def record_db_write(self, latency_ms: float):
        """Record a DB write latency (for average calculation)."""
        with self._lock:
            self._db_latencies_ms.append(latency_ms)
    
    def record_pool_exhaustion(self):
        """Record connection pool exhaustion (for queue depth calculation)."""
        with self._lock:
            self._pool_exhaustion_count += 1
    
    def update_agent_heartbeat_lag(self, max_lag_sec: float):
        """Update agent heartbeat lag (called from metrics endpoint query)."""
        with self._lock:
            self._max_heartbeat_lag_sec = max_lag_sec
            self._heartbeat_last_updated = time.time()
    
    def get_ingest_rate_eps(self) -> float:
        """
        Calculate 1-minute moving average of events per second.
        
        Returns:
            Events per second (float), or 0.0 if no events in window
        """
        with self._lock:
            now = time.time()
            one_minute_ago = now - 60.0
            
            # Count events in last minute
            count = sum(1 for ts in self._event_timestamps if ts >= one_minute_ago)
            
            if count == 0:
                return 0.0
            
            # Calculate rate (events per second)
            return count / 60.0
    
    def get_db_write_latency_ms(self) -> float:
        """
        Calculate average of last ~100 DB writes.
        
        Returns:
            Average latency in milliseconds (float), or 0.0 if no writes recorded
        """
        with self._lock:
            if not self._db_latencies_ms:
                return 0.0
            
            return sum(self._db_latencies_ms) / len(self._db_latencies_ms)
    
    def get_queue_depth(self) -> int:
        """
        Get current queue depth (connection pool exhaustion count).
        
        Returns:
            Queue depth (int), currently returns 0 as there's no explicit queue
            Pool exhaustion count is tracked but not exposed as queue depth
        """
        with self._lock:
            # For now, return 0 (no explicit queue)
            # Could be enhanced to track pool exhaustion if needed
            return 0
    
    def get_agent_heartbeat_lag_sec(self) -> Optional[float]:
        """
        Get max time since last valid agent heartbeat.
        
        Returns:
            Max heartbeat lag in seconds (float), or None if not yet queried
        """
        with self._lock:
            return self._max_heartbeat_lag_sec
    
    def get_system_status(self, db_reachable: bool) -> str:
        """
        Determine system status based on metrics.
        
        Args:
            db_reachable: Whether database is currently reachable
            
        Returns:
            "HEALTHY" | "DEGRADED" | "CRITICAL"
        """
        if not db_reachable:
            return "CRITICAL"
        
        # Check for degraded conditions
        db_latency_ms = self.get_db_write_latency_ms()
        heartbeat_lag = self.get_agent_heartbeat_lag_sec()
        
        # CRITICAL: Very high DB latency (>1000ms) or very old heartbeat (>5 minutes)
        if db_latency_ms > 1000.0:
            return "CRITICAL"
        if heartbeat_lag is not None and heartbeat_lag > 300.0:  # 5 minutes
            return "CRITICAL"
        
        # DEGRADED: Elevated latency (>500ms) or old heartbeat (>2 minutes)
        if db_latency_ms > 500.0:
            return "DEGRADED"
        if heartbeat_lag is not None and heartbeat_lag > 120.0:  # 2 minutes
            return "DEGRADED"
        
        return "HEALTHY"


# Global metrics instance (thread-safe)
_metrics = IngestMetrics()


def get_metrics() -> IngestMetrics:
    """Get global metrics instance."""
    return _metrics
