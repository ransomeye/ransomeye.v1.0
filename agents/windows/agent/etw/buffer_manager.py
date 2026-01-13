#!/usr/bin/env python3
"""
RansomEye v1.0 Windows Agent - Buffer Manager
AUTHORITATIVE: Offline-capable event buffering with loss detection
"""

import os
import sys
import json
import threading
from typing import Dict, Any, List, Optional
from pathlib import Path
from collections import deque
from datetime import datetime, timezone

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    _logger = setup_logging('windows-agent-etw-buffer')
except ImportError:
    import logging
    _logger = logging.getLogger('windows-agent-etw-buffer')


class BufferFullError(Exception):
    """Exception raised when buffer is full."""
    pass


class BufferManager:
    """
    Event buffer manager with offline capability.
    
    CRITICAL: No drops without audit. Offline-first design.
    """
    
    MAX_MEMORY_EVENTS = int(os.getenv('RANSOMEYE_ETW_MAX_MEMORY_EVENTS', '10000'))
    MAX_DISK_EVENTS = int(os.getenv('RANSOMEYE_ETW_MAX_DISK_EVENTS', '100000'))
    BATCH_SIZE = int(os.getenv('RANSOMEYE_ETW_BATCH_SIZE', '500'))
    FLUSH_INTERVAL_SECONDS = int(os.getenv('RANSOMEYE_ETW_FLUSH_INTERVAL_SECONDS', '5'))
    
    def __init__(self, buffer_dir: Path):
        """
        Initialize buffer manager.
        
        Args:
            buffer_dir: Directory for disk-backed buffer
        """
        self.buffer_dir = Path(buffer_dir)
        self.buffer_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory ring buffer
        self._memory_buffer: deque = deque(maxlen=self.MAX_MEMORY_EVENTS)
        self._memory_lock = threading.Lock()
        
        # Disk-backed buffer
        self._disk_buffer_path = self.buffer_dir / "etw_events_buffer.jsonl"
        self._disk_lock = threading.Lock()
        self._disk_event_count = 0
        
        # Statistics
        self._total_events_added = 0
        self._total_events_removed = 0
        self._total_events_dropped = 0
        self._total_events_flushed = 0
        self._stats_lock = threading.Lock()
        
        # Load existing disk buffer count
        self._load_disk_buffer_count()
    
    def add_event(self, event: Dict[str, Any]) -> bool:
        """
        Add event to buffer.
        
        Args:
            event: Event dictionary to buffer
            
        Returns:
            True if added successfully, False if dropped (with audit)
        """
        with self._stats_lock:
            self._total_events_added += 1
        
        # Try memory buffer first
        with self._memory_lock:
            if len(self._memory_buffer) < self.MAX_MEMORY_EVENTS:
                self._memory_buffer.append(event)
                return True
        
        # Memory buffer full, try disk buffer
        return self._add_to_disk_buffer(event)
    
    def _add_to_disk_buffer(self, event: Dict[str, Any]) -> bool:
        """
        Add event to disk buffer.
        
        Args:
            event: Event dictionary to buffer
            
        Returns:
            True if added, False if dropped (with audit)
        """
        with self._disk_lock:
            if self._disk_event_count >= self.MAX_DISK_EVENTS:
                # Buffer full - drop with audit
                with self._stats_lock:
                    self._total_events_dropped += 1
                
                _logger.warning(
                    f"Buffer full - event dropped. "
                    f"Memory: {len(self._memory_buffer)}, Disk: {self._disk_event_count}"
                )
                
                # Emit audit event (would be sent to health monitor)
                self._emit_buffer_full_audit(event)
                return False
            
            try:
                # Append to disk buffer (JSONL format)
                with open(self._disk_buffer_path, 'a', encoding='utf-8') as f:
                    json.dump(event, f, ensure_ascii=False)
                    f.write('\n')
                
                self._disk_event_count += 1
                return True
                
            except Exception as e:
                _logger.error(f"Failed to write to disk buffer: {e}", exc_info=True)
                with self._stats_lock:
                    self._total_events_dropped += 1
                return False
    
    def get_batch(self, max_events: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get batch of events from buffer.
        
        Args:
            max_events: Maximum events to return (default: BATCH_SIZE)
            
        Returns:
            List of event dictionaries
        """
        if max_events is None:
            max_events = self.BATCH_SIZE
        
        batch = []
        
        # Get from memory buffer first
        with self._memory_lock:
            while len(batch) < max_events and self._memory_buffer:
                batch.append(self._memory_buffer.popleft())
        
        # If needed, get from disk buffer
        if len(batch) < max_events:
            disk_batch = self._get_from_disk_buffer(max_events - len(batch))
            batch.extend(disk_batch)
        
        with self._stats_lock:
            self._total_events_removed += len(batch)
        
        return batch
    
    def _get_from_disk_buffer(self, max_events: int) -> List[Dict[str, Any]]:
        """
        Get events from disk buffer.
        
        Args:
            max_events: Maximum events to return
            
        Returns:
            List of event dictionaries
        """
        batch = []
        
        if not self._disk_buffer_path.exists():
            return batch
        
        with self._disk_lock:
            try:
                # Read events from disk buffer
                temp_buffer_path = self.buffer_dir / "etw_events_buffer_temp.jsonl"
                
                with open(self._disk_buffer_path, 'r', encoding='utf-8') as infile:
                    with open(temp_buffer_path, 'w', encoding='utf-8') as outfile:
                        for _ in range(max_events):
                            line = infile.readline()
                            if not line:
                                break
                            
                            try:
                                event = json.loads(line.strip())
                                batch.append(event)
                                self._disk_event_count -= 1
                            except json.JSONDecodeError as e:
                                _logger.warning(f"Invalid JSON in disk buffer: {e}")
                                continue
                        
                        # Copy remaining lines
                        for line in infile:
                            outfile.write(line)
                
                # Replace buffer file
                if temp_buffer_path.exists():
                    temp_buffer_path.replace(self._disk_buffer_path)
                else:
                    # All events consumed
                    self._disk_buffer_path.unlink(missing_ok=True)
                
            except Exception as e:
                _logger.error(f"Failed to read from disk buffer: {e}", exc_info=True)
        
        return batch
    
    def flush_to_disk(self):
        """Flush memory buffer to disk (periodic operation)."""
        with self._memory_lock:
            if not self._memory_buffer:
                return
            
            events_to_flush = list(self._memory_buffer)
            self._memory_buffer.clear()
        
        # Add to disk buffer
        for event in events_to_flush:
            self._add_to_disk_buffer(event)
        
        with self._stats_lock:
            self._total_events_flushed += len(events_to_flush)
    
    def get_buffer_stats(self) -> Dict[str, Any]:
        """
        Get buffer statistics.
        
        Returns:
            Dictionary with buffer statistics
        """
        with self._memory_lock:
            memory_count = len(self._memory_buffer)
        
        with self._disk_lock:
            disk_count = self._disk_event_count
        
        with self._stats_lock:
            return {
                'memory_events': memory_count,
                'disk_events': disk_count,
                'total_events_added': self._total_events_added,
                'total_events_removed': self._total_events_removed,
                'total_events_dropped': self._total_events_dropped,
                'total_events_flushed': self._total_events_flushed,
                'buffer_full': (memory_count >= self.MAX_MEMORY_EVENTS and 
                               disk_count >= self.MAX_DISK_EVENTS)
            }
    
    def _load_disk_buffer_count(self):
        """Load disk buffer event count from file."""
        if not self._disk_buffer_path.exists():
            self._disk_event_count = 0
            return
        
        try:
            with open(self._disk_buffer_path, 'r', encoding='utf-8') as f:
                self._disk_event_count = sum(1 for _ in f)
        except Exception as e:
            _logger.warning(f"Failed to load disk buffer count: {e}")
            self._disk_event_count = 0
    
    def _emit_buffer_full_audit(self, event: Dict[str, Any]):
        """
        Emit audit event for buffer full condition.
        
        Args:
            event: Event that was dropped
        """
        audit_event = {
            'event_type': 'buffer_full',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'dropped_event_type': event.get('event_type'),
            'dropped_event_id': event.get('event_id'),
            'memory_buffer_size': len(self._memory_buffer),
            'disk_buffer_size': self._disk_event_count
        }
        
        # Would be sent to health monitor
        _logger.warning(f"Buffer full audit: {json.dumps(audit_event)}")
