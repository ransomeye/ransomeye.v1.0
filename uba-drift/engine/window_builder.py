#!/usr/bin/env python3
"""
RansomEye UBA Drift - Window Builder
AUTHORITATIVE: Build explicit observation windows (environment-driven)
"""

from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta
import os


class WindowBuildError(Exception):
    """Base exception for window building errors."""
    pass


class WindowBuilder:
    """
    Explicit observation window builder.
    
    Properties:
    - Explicit windows: Window size from env vars
    - No implicit rolling: No implicit rolling windows
    - Deterministic: Same input = same window
    """
    
    def __init__(self):
        """Initialize window builder."""
        # Load window size from environment (no hardcoded values)
        self.observation_window_days = int(os.getenv('UBA_DRIFT_OBSERVATION_WINDOW_DAYS', '7'))
    
    def build_window(
        self,
        window_end: datetime,
        window_start: datetime = None
    ) -> tuple:
        """
        Build observation window.
        
        Args:
            window_end: Window end timestamp
            window_start: Window start timestamp (if None, calculated from window_days)
        
        Returns:
            Tuple of (window_start, window_end)
        """
        if window_start is None:
            window_start = window_end - timedelta(days=self.observation_window_days)
        
        if window_start >= window_end:
            raise WindowBuildError("Window start must be before window end")
        
        return (window_start, window_end)
    
    def filter_events(
        self,
        events: List[Dict[str, Any]],
        window_start: datetime,
        window_end: datetime
    ) -> List[Dict[str, Any]]:
        """
        Filter events to observation window.
        
        Args:
            events: List of behavior events
            window_start: Window start timestamp
            window_end: Window end timestamp
        
        Returns:
            Filtered list of events
        """
        filtered = []
        
        for event in events:
            timestamp_str = event.get('timestamp', '')
            if not timestamp_str:
                continue
            
            try:
                event_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                if window_start <= event_time <= window_end:
                    filtered.append(event)
            except Exception:
                pass
        
        return filtered
