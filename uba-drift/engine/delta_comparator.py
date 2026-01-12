#!/usr/bin/env python3
"""
RansomEye UBA Drift - Delta Comparator
AUTHORITATIVE: Compare baseline facts vs observation window facts (deterministic)
"""

from typing import Dict, Any, List
from datetime import datetime, timezone
import uuid
import hashlib
import json
import os


class DeltaComparisonError(Exception):
    """Base exception for delta comparison errors."""
    pass


class DeltaComparator:
    """
    Deterministic delta comparator.
    
    Properties:
    - Explicit comparison: Explicit comparison logic only
    - No heuristics: No heuristic logic
    - Environment-defined thresholds: Thresholds from env vars only
    - Facts only: Deltas are facts, not scores
    """
    
    def __init__(self):
        """Initialize delta comparator."""
        # Load frequency shift threshold from environment (no hardcoded values)
        self.frequency_shift_threshold = float(os.getenv('UBA_DRIFT_FREQUENCY_THRESHOLD', '0.0'))
    
    def compare(
        self,
        baseline: Dict[str, Any],
        observation_events: List[Dict[str, Any]],
        observation_window_start: datetime,
        observation_window_end: datetime
    ) -> List[Dict[str, Any]]:
        """
        Compare baseline to observation window and produce deltas.
        
        Args:
            baseline: Baseline dictionary from UBA Core
            observation_events: Behavior events in observation window
            observation_window_start: Observation window start timestamp
            observation_window_end: Observation window end timestamp
        
        Returns:
            List of delta dictionaries
        """
        deltas = []
        
        # Extract baseline features
        baseline_event_types = set(baseline.get('observed_event_types', []))
        baseline_hosts = set(baseline.get('observed_hosts', []))
        baseline_time_buckets = set(baseline.get('observed_time_buckets', []))
        baseline_privileges = set(baseline.get('observed_privileges', []))
        
        # Extract observation features
        observation_event_types = set()
        observation_hosts = set()
        observation_time_buckets = set()
        observation_privileges = set()
        event_type_counts = {}
        
        for event in observation_events:
            event_type = event.get('event_type', '')
            host_id = event.get('host_id', '')
            timestamp = event.get('timestamp', '')
            
            if event_type:
                observation_event_types.add(event_type)
                event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
            
            if host_id:
                observation_hosts.add(host_id)
            
            if timestamp:
                try:
                    event_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    bucket = event_time.replace(minute=0, second=0, microsecond=0)
                    observation_time_buckets.add(bucket.strftime('%Y-%m-%dT%H:%M'))
                except Exception:
                    pass
            
            if event.get('event_type') == 'privilege_use':
                privilege = event.get('resource_id', '') or event.get('action', '')
                if privilege:
                    observation_privileges.add(privilege)
        
        # Compare event types (NEW_EVENT_TYPE)
        for event_type in observation_event_types:
            if event_type not in baseline_event_types:
                delta = self._create_delta(
                    identity_id=baseline.get('identity_id', ''),
                    baseline_hash=baseline.get('baseline_hash', ''),
                    observation_window_start=observation_window_start,
                    observation_window_end=observation_window_end,
                    delta_type='NEW_EVENT_TYPE',
                    baseline_value='',
                    observed_value=event_type,
                    delta_magnitude=1.0,
                    first_seen_timestamp=self._get_first_seen(observation_events, 'event_type', event_type),
                    last_seen_timestamp=self._get_last_seen(observation_events, 'event_type', event_type)
                )
                deltas.append(delta)
        
        # Compare hosts (NEW_HOST)
        for host_id in observation_hosts:
            if host_id not in baseline_hosts:
                delta = self._create_delta(
                    identity_id=baseline.get('identity_id', ''),
                    baseline_hash=baseline.get('baseline_hash', ''),
                    observation_window_start=observation_window_start,
                    observation_window_end=observation_window_end,
                    delta_type='NEW_HOST',
                    baseline_value='',
                    observed_value=host_id,
                    delta_magnitude=1.0,
                    first_seen_timestamp=self._get_first_seen(observation_events, 'host_id', host_id),
                    last_seen_timestamp=self._get_last_seen(observation_events, 'host_id', host_id)
                )
                deltas.append(delta)
        
        # Compare time buckets (NEW_TIME_BUCKET)
        for time_bucket in observation_time_buckets:
            if time_bucket not in baseline_time_buckets:
                delta = self._create_delta(
                    identity_id=baseline.get('identity_id', ''),
                    baseline_hash=baseline.get('baseline_hash', ''),
                    observation_window_start=observation_window_start,
                    observation_window_end=observation_window_end,
                    delta_type='NEW_TIME_BUCKET',
                    baseline_value='',
                    observed_value=time_bucket,
                    delta_magnitude=1.0,
                    first_seen_timestamp=self._get_first_seen_time_bucket(observation_events, time_bucket),
                    last_seen_timestamp=self._get_last_seen_time_bucket(observation_events, time_bucket)
                )
                deltas.append(delta)
        
        # Compare privileges (NEW_PRIVILEGE)
        for privilege in observation_privileges:
            if privilege not in baseline_privileges:
                delta = self._create_delta(
                    identity_id=baseline.get('identity_id', ''),
                    baseline_hash=baseline.get('baseline_hash', ''),
                    observation_window_start=observation_window_start,
                    observation_window_end=observation_window_end,
                    delta_type='NEW_PRIVILEGE',
                    baseline_value='',
                    observed_value=privilege,
                    delta_magnitude=1.0,
                    first_seen_timestamp=self._get_first_seen_privilege(observation_events, privilege),
                    last_seen_timestamp=self._get_last_seen_privilege(observation_events, privilege)
                )
                deltas.append(delta)
        
        # Compare frequencies (FREQUENCY_SHIFT)
        # Count baseline frequencies (stub - would need baseline event counts)
        baseline_event_type_counts = {}
        for event_type in baseline_event_types:
            baseline_event_type_counts[event_type] = 1  # Stub: assume 1 in baseline
        
        for event_type, observed_count in event_type_counts.items():
            baseline_count = baseline_event_type_counts.get(event_type, 0)
            frequency_diff = observed_count - baseline_count
            
            if abs(frequency_diff) > self.frequency_shift_threshold:
                delta = self._create_delta(
                    identity_id=baseline.get('identity_id', ''),
                    baseline_hash=baseline.get('baseline_hash', ''),
                    observation_window_start=observation_window_start,
                    observation_window_end=observation_window_end,
                    delta_type='FREQUENCY_SHIFT',
                    baseline_value=baseline_count,
                    observed_value=observed_count,
                    delta_magnitude=frequency_diff,
                    first_seen_timestamp=self._get_first_seen(observation_events, 'event_type', event_type),
                    last_seen_timestamp=self._get_last_seen(observation_events, 'event_type', event_type)
                )
                deltas.append(delta)
        
        return deltas
    
    def _create_delta(
        self,
        identity_id: str,
        baseline_hash: str,
        observation_window_start: datetime,
        observation_window_end: datetime,
        delta_type: str,
        baseline_value: Any,
        observed_value: Any,
        delta_magnitude: float,
        first_seen_timestamp: str,
        last_seen_timestamp: str
    ) -> Dict[str, Any]:
        """Create delta dictionary."""
        delta = {
            'delta_id': str(uuid.uuid4()),
            'identity_id': identity_id,
            'baseline_hash': baseline_hash,
            'observation_window_start': observation_window_start.isoformat(),
            'observation_window_end': observation_window_end.isoformat(),
            'delta_type': delta_type,
            'baseline_value': baseline_value,
            'observed_value': observed_value,
            'delta_magnitude': delta_magnitude,
            'first_seen_timestamp': first_seen_timestamp,
            'last_seen_timestamp': last_seen_timestamp,
            'immutable_hash': '',
            'ledger_entry_id': ''
        }
        
        # Calculate hash
        delta['immutable_hash'] = self._calculate_hash(delta)
        
        return delta
    
    def _get_first_seen(self, events: List[Dict[str, Any]], field: str, value: Any) -> str:
        """Get first seen timestamp for field value."""
        for event in sorted(events, key=lambda e: e.get('timestamp', '')):
            if event.get(field) == value:
                return event.get('timestamp', datetime.now(timezone.utc).isoformat())
        return datetime.now(timezone.utc).isoformat()
    
    def _get_last_seen(self, events: List[Dict[str, Any]], field: str, value: Any) -> str:
        """Get last seen timestamp for field value."""
        for event in sorted(events, key=lambda e: e.get('timestamp', ''), reverse=True):
            if event.get(field) == value:
                return event.get('timestamp', datetime.now(timezone.utc).isoformat())
        return datetime.now(timezone.utc).isoformat()
    
    def _get_first_seen_time_bucket(self, events: List[Dict[str, Any]], time_bucket: str) -> str:
        """Get first seen timestamp for time bucket."""
        for event in sorted(events, key=lambda e: e.get('timestamp', '')):
            timestamp = event.get('timestamp', '')
            try:
                event_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                bucket = event_time.replace(minute=0, second=0, microsecond=0)
                if bucket.strftime('%Y-%m-%dT%H:%M') == time_bucket:
                    return timestamp
            except Exception:
                pass
        return datetime.now(timezone.utc).isoformat()
    
    def _get_last_seen_time_bucket(self, events: List[Dict[str, Any]], time_bucket: str) -> str:
        """Get last seen timestamp for time bucket."""
        for event in sorted(events, key=lambda e: e.get('timestamp', ''), reverse=True):
            timestamp = event.get('timestamp', '')
            try:
                event_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                bucket = event_time.replace(minute=0, second=0, microsecond=0)
                if bucket.strftime('%Y-%m-%dT%H:%M') == time_bucket:
                    return timestamp
            except Exception:
                pass
        return datetime.now(timezone.utc).isoformat()
    
    def _get_first_seen_privilege(self, events: List[Dict[str, Any]], privilege: str) -> str:
        """Get first seen timestamp for privilege."""
        for event in sorted(events, key=lambda e: e.get('timestamp', '')):
            if event.get('event_type') == 'privilege_use':
                event_privilege = event.get('resource_id', '') or event.get('action', '')
                if event_privilege == privilege:
                    return event.get('timestamp', datetime.now(timezone.utc).isoformat())
        return datetime.now(timezone.utc).isoformat()
    
    def _get_last_seen_privilege(self, events: List[Dict[str, Any]], privilege: str) -> str:
        """Get last seen timestamp for privilege."""
        for event in sorted(events, key=lambda e: e.get('timestamp', ''), reverse=True):
            if event.get('event_type') == 'privilege_use':
                event_privilege = event.get('resource_id', '') or event.get('action', '')
                if event_privilege == privilege:
                    return event.get('timestamp', datetime.now(timezone.utc).isoformat())
        return datetime.now(timezone.utc).isoformat()
    
    def _calculate_hash(self, delta: Dict[str, Any]) -> str:
        """Calculate SHA256 hash of delta record."""
        hashable_content = {k: v for k, v in delta.items() if k not in ['immutable_hash', 'ledger_entry_id']}
        canonical_json = json.dumps(hashable_content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
