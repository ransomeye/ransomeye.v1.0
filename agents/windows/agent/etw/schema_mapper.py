#!/usr/bin/env python3
"""
RansomEye v1.0 Windows Agent - Schema Mapper
AUTHORITATIVE: Deterministic mapping from ETW events to normalized schemas
"""

import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime, timezone

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    _logger = setup_logging('windows-agent-etw-schema')
except ImportError:
    import logging
    _logger = logging.getLogger('windows-agent-etw-schema')


class SchemaMapper:
    """
    Maps ETW events to normalized schemas.
    
    CRITICAL: Mapping must be deterministic (same ETW event → same normalized event).
    Schemas must align with Linux Agent where possible.
    """
    
    def __init__(self):
        """Initialize schema mapper."""
        pass
    
    def map_to_normalized(self, parsed_event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Map parsed ETW event to normalized schema.
        
        Args:
            parsed_event: Parsed ETW event dictionary
            
        Returns:
            Normalized event dictionary or None if event should be filtered
        """
        event_type = parsed_event.get('event_type')
        
        if event_type in ['process_start', 'process_stop', 'image_load']:
            return self._map_process_activity(parsed_event)
        elif event_type in ['file_create', 'file_write', 'file_delete', 'file_rename', 'file_read']:
            return self._map_file_activity(parsed_event)
        elif event_type.startswith('registry_'):
            return self._map_registry_activity(parsed_event)
        elif event_type in ['tcp_connect', 'tcp_disconnect', 'udp_send', 'dns_query']:
            return self._map_network_intent(parsed_event)
        elif event_type in ['virtual_alloc', 'virtual_protect']:
            return self._map_memory_activity(parsed_event)
        else:
            _logger.warning(f"Unknown event type for mapping: {event_type}")
            return None
    
    def _map_process_activity(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Map to process_activity normalized schema."""
        event_type = event.get('event_type')
        
        if event_type == 'process_start':
            activity_type = 'PROCESS_START'
        elif event_type == 'process_stop':
            activity_type = 'PROCESS_EXIT'
        elif event_type == 'image_load':
            # Check if suspicious (DLL injection indicator)
            image_path = event.get('image_path', '').lower()
            if any(susp in image_path for susp in ['temp', 'appdata', 'downloads']):
                activity_type = 'PROCESS_INJECT'
            else:
                return None  # Normal image load, not interesting
        else:
            return None
        
        normalized = {
            'activity_type': activity_type,
            'process_pid': event.get('process_pid', 0),
            'parent_pid': event.get('parent_pid'),
            'process_name': self._extract_process_name(event.get('image_path', '')),
            'process_path': event.get('image_path'),
            'command_line': event.get('command_line'),
            'user_name': None,  # Would need additional lookup
            'user_id': None,  # Would need additional lookup
            'target_pid': None,
            'target_process_name': None,
            'etw_provider_id': event.get('provider_id'),
            'etw_event_id': event.get('event_id'),
            'etw_timestamp': event.get('timestamp')
        }
        
        # Add exit code for process_stop
        if activity_type == 'PROCESS_EXIT':
            normalized['exit_code'] = event.get('exit_code')
        
        return normalized
    
    def _map_file_activity(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Map to file_activity normalized schema."""
        event_type = event.get('event_type')
        
        activity_type_map = {
            'file_create': 'FILE_CREATE',
            'file_write': 'FILE_MODIFY',
            'file_delete': 'FILE_DELETE',
            'file_read': 'FILE_READ',
            'file_rename': 'FILE_MODIFY'  # Rename is a modification
        }
        
        activity_type = activity_type_map.get(event_type)
        if not activity_type:
            return None
        
        normalized = {
            'activity_type': activity_type,
            'file_path': event.get('file_path'),
            'file_size': event.get('file_size'),
            'file_size_before': None,
            'file_size_after': None,
            'entropy_change_indicator': False,
            'process_pid': event.get('process_pid', 0),
            'process_name': None,  # Would need process lookup
            'etw_provider_id': event.get('provider_id'),
            'etw_event_id': event.get('event_id'),
            'etw_timestamp': event.get('timestamp')
        }
        
        # Handle file_write with size change (entropy indicator)
        if event_type == 'file_write' and 'file_size' in event:
            normalized['file_size_after'] = event.get('file_size')
            # Entropy change heuristic: size change > 10%
            # (Would need previous size from cache)
            normalized['entropy_change_indicator'] = True  # Placeholder
        
        # Handle file_rename
        if event_type == 'file_rename':
            normalized['old_path'] = event.get('old_path')
            normalized['new_path'] = event.get('new_path')
        
        return normalized
    
    def _map_registry_activity(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Map to persistence normalized schema (if persistence location)."""
        event_type = event.get('event_type')
        registry_key = event.get('registry_key', '').upper()
        
        # Check if this is a persistence location
        persistence_type = None
        if 'RUN' in registry_key or 'RUNONCE' in registry_key:
            persistence_type = 'REGISTRY_RUN_KEY'
        elif 'SERVICES' in registry_key:
            persistence_type = 'SERVICE'
        elif 'SCHEDULED TASK' in registry_key or 'TASKS' in registry_key:
            persistence_type = 'SCHEDULED_TASK'
        else:
            return None  # Not a persistence location
        
        normalized = {
            'persistence_type': persistence_type,
            'registry_key': event.get('registry_key'),
            'registry_value': event.get('value_name'),
            'registry_data': event.get('value_data'),
            'process_pid': event.get('process_pid', 0),
            'process_name': None,  # Would need process lookup
            'etw_provider_id': event.get('provider_id'),
            'etw_event_id': event.get('event_id'),
            'etw_timestamp': event.get('timestamp')
        }
        
        return normalized
    
    def _map_network_intent(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Map to network_intent normalized schema."""
        event_type = event.get('event_type')
        
        activity_type_map = {
            'tcp_connect': 'CONNECTION_ATTEMPT',
            'udp_send': 'CONNECTION_ATTEMPT',
            'dns_query': 'DNS_QUERY',
            'tcp_disconnect': None  # Not mapped (connection closed)
        }
        
        activity_type = activity_type_map.get(event_type)
        if not activity_type:
            return None
        
        normalized = {
            'activity_type': activity_type,
            'source_ip': event.get('source_ip'),
            'source_port': event.get('source_port'),
            'dest_ip': event.get('dest_ip'),
            'dest_port': event.get('dest_port'),
            'protocol': 'TCP' if 'tcp' in event_type else 'UDP' if 'udp' in event_type else None,
            'domain': event.get('domain'),  # For DNS queries
            'process_pid': event.get('process_pid', 0),
            'process_name': None,  # Would need process lookup
            'etw_provider_id': event.get('provider_id'),
            'etw_event_id': event.get('event_id'),
            'etw_timestamp': event.get('timestamp')
        }
        
        return normalized
    
    def _map_memory_activity(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Map to process_activity normalized schema (PROCESS_MODIFY for suspicious memory)."""
        event_type = event.get('event_type')
        
        # Only map suspicious memory patterns
        if event_type == 'virtual_alloc':
            protection = event.get('protection', 0)
            # Check for RWX (0x40 = PAGE_EXECUTE_READWRITE)
            if protection & 0x40:
                return {
                    'activity_type': 'PROCESS_MODIFY',
                    'process_pid': event.get('process_pid', 0),
                    'process_name': None,
                    'target_pid': event.get('process_pid', 0),
                    'target_process_name': None,
                    'etw_provider_id': event.get('provider_id'),
                    'etw_event_id': event.get('event_id'),
                    'etw_timestamp': event.get('timestamp'),
                    'memory_address': event.get('address'),
                    'memory_size': event.get('size'),
                    'memory_protection': protection
                }
        elif event_type == 'virtual_protect':
            new_protection = event.get('new_protection', 0)
            # Check for RWX
            if new_protection & 0x40:
                return {
                    'activity_type': 'PROCESS_MODIFY',
                    'process_pid': event.get('process_pid', 0),
                    'process_name': None,
                    'target_pid': event.get('process_pid', 0),
                    'target_process_name': None,
                    'etw_provider_id': event.get('provider_id'),
                    'etw_event_id': event.get('event_id'),
                    'etw_timestamp': event.get('timestamp'),
                    'memory_address': event.get('address'),
                    'old_protection': event.get('old_protection'),
                    'new_protection': new_protection
                }
        
        return None  # Not suspicious
    
    def _extract_process_name(self, image_path: str) -> str:
        """Extract process name from image path."""
        if not image_path:
            return ""
        
        # Extract filename from path
        path_parts = image_path.replace('\\', '/').split('/')
        if path_parts:
            return path_parts[-1]
        return ""
    
    def normalize_timestamp(self, timestamp_str: str) -> str:
        """
        Normalize timestamp to RFC3339 UTC format.
        
        Args:
            timestamp_str: Timestamp string (various formats)
            
        Returns:
            RFC3339 UTC timestamp string
        """
        try:
            # Parse timestamp (assume ISO format)
            if 'T' in timestamp_str or ' ' in timestamp_str:
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                # Try other formats
                dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
            
            # Ensure UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            
            # Format as RFC3339
            return dt.isoformat().replace('+00:00', 'Z')
        except Exception as e:
            _logger.warning(f"Failed to normalize timestamp {timestamp_str}: {e}")
            # Return current UTC time as fallback
            return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
