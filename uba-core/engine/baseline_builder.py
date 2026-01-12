#!/usr/bin/env python3
"""
RansomEye UBA Core - Baseline Builder
AUTHORITATIVE: Build historical baselines (facts only, no scoring)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import uuid
import hashlib
import json
import os


class BaselineBuildError(Exception):
    """Base exception for baseline building errors."""
    pass


class BaselineBuilder:
    """
    Historical baseline builder.
    
    Properties:
    - Explicit window: Window is explicit (env-configured)
    - Immutable output: Output is immutable
    - No scoring: Only aggregation, no scoring
    - Facts only: Baselines are facts, not conclusions
    """
    
    def __init__(self):
        """Initialize baseline builder."""
        # Load baseline window from environment (no hardcoded values)
        self.baseline_window_days = int(os.getenv('UBA_BASELINE_WINDOW_DAYS', '30'))
    
    def build_baseline(
        self,
        identity_id: str,
        events: List[Dict[str, Any]],
        window_start: Optional[datetime] = None,
        window_end: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Build identity baseline from events.
        
        Args:
            identity_id: Identity identifier
            events: List of behavior events for this identity
            window_start: Baseline window start (if None, calculated from window_days)
            window_end: Baseline window end (if None, uses current time)
        
        Returns:
            Baseline dictionary
        """
        if not events:
            raise BaselineBuildError("Cannot build baseline from empty event list")
        
        # Determine window
        if window_end is None:
            window_end = datetime.now(timezone.utc)
        
        if window_start is None:
            window_start = window_end - timedelta(days=self.baseline_window_days)
        
        # Filter events within window
        window_events = [
            e for e in events
            if self._is_in_window(e, window_start, window_end)
        ]
        
        if not window_events:
            raise BaselineBuildError("No events found in baseline window")
        
        # Aggregate observed features
        observed_event_types = self._aggregate_event_types(window_events)
        observed_hosts = self._aggregate_hosts(window_events)
        observed_time_buckets = self._aggregate_time_buckets(window_events)
        observed_privileges = self._aggregate_privileges(window_events)
        
        # Create baseline
        baseline = {
            'baseline_id': str(uuid.uuid4()),
            'identity_id': identity_id,
            'baseline_window_start': window_start.isoformat(),
            'baseline_window_end': window_end.isoformat(),
            'observed_event_types': sorted(list(observed_event_types)),
            'observed_hosts': sorted(list(observed_hosts)),
            'observed_time_buckets': sorted(list(observed_time_buckets)),
            'observed_privileges': sorted(list(observed_privileges)),
            'baseline_hash': '',
            'immutable_hash': '',
            'ledger_entry_id': ''
        }
        
        # Calculate baseline hash (for drift comparison)
        baseline['baseline_hash'] = self._calculate_baseline_hash(baseline)
        
        # Calculate immutable hash
        baseline['immutable_hash'] = self._calculate_hash(baseline)
        
        return baseline
    
    def _is_in_window(self, event: Dict[str, Any], window_start: datetime, window_end: datetime) -> bool:
        """Check if event is within baseline window."""
        try:
            event_time = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
            return window_start <= event_time <= window_end
        except Exception:
            return False
    
    def _aggregate_event_types(self, events: List[Dict[str, Any]]) -> set:
        """Aggregate observed event types."""
        return set(e.get('event_type', '') for e in events if e.get('event_type'))
    
    def _aggregate_hosts(self, events: List[Dict[str, Any]]) -> set:
        """Aggregate observed host identifiers."""
        return set(e.get('host_id', '') for e in events if e.get('host_id'))
    
    def _aggregate_time_buckets(self, events: List[Dict[str, Any]]) -> set:
        """Aggregate observed time buckets (hourly)."""
        buckets = set()
        for event in events:
            try:
                event_time = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                # Round to hour
                bucket = event_time.replace(minute=0, second=0, microsecond=0)
                buckets.add(bucket.strftime('%Y-%m-%dT%H:%M'))
            except Exception:
                pass
        return buckets
    
    def _aggregate_privileges(self, events: List[Dict[str, Any]]) -> set:
        """Aggregate observed privileges."""
        privileges = set()
        for event in events:
            if event.get('event_type') == 'privilege_use':
                # Extract privilege from resource_id or action
                privilege = event.get('resource_id', '') or event.get('action', '')
                if privilege:
                    privileges.add(privilege)
        return privileges
    
    def _calculate_baseline_hash(self, baseline: Dict[str, Any]) -> str:
        """Calculate SHA256 hash of baseline content (for drift comparison)."""
        # Hash only the observed features (not metadata)
        content = {
            'observed_event_types': baseline.get('observed_event_types', []),
            'observed_hosts': baseline.get('observed_hosts', []),
            'observed_time_buckets': baseline.get('observed_time_buckets', []),
            'observed_privileges': baseline.get('observed_privileges', [])
        }
        canonical_json = json.dumps(content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
    
    def _calculate_hash(self, baseline: Dict[str, Any]) -> str:
        """Calculate SHA256 hash of baseline record."""
        hashable_content = {k: v for k, v in baseline.items() if k not in ['immutable_hash', 'ledger_entry_id']}
        canonical_json = json.dumps(hashable_content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
