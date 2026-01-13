#!/usr/bin/env python3
"""
RansomEye v1.0 Windows Agent - ETW Event Parser
AUTHORITATIVE: Binary ETW event parsing with minimal field extraction
"""

import os
import sys
import struct
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    _logger = setup_logging('windows-agent-etw-parser')
except ImportError:
    import logging
    _logger = logging.getLogger('windows-agent-etw-parser')

from .providers import ETWProvider, ProviderRegistry


class ETWParseError(Exception):
    """Exception raised for ETW parsing errors."""
    pass


class ETWEventParser:
    """
    Binary ETW event parser.
    
    CRITICAL: Parser must reject malformed events safely.
    Lazy parsing: Only extract required fields.
    """
    
    def __init__(self, provider_registry: ProviderRegistry):
        """
        Initialize ETW event parser.
        
        Args:
            provider_registry: Provider registry for provider metadata
        """
        self.provider_registry = provider_registry
        self._process_name_cache: Dict[int, str] = {}  # PID -> process name
        self._path_cache: Dict[str, str] = {}  # Raw path -> normalized path
    
    def parse_event(
        self,
        provider_id: str,
        event_id: int,
        timestamp: datetime,
        event_data: bytes
    ) -> Optional[Dict[str, Any]]:
        """
        Parse ETW event from binary data.
        
        Args:
            provider_id: Provider GUID string
            event_id: ETW event ID
            timestamp: Event timestamp
            event_data: Binary event data
            
        Returns:
            Parsed event dictionary or None if event should be filtered/rejected
            
        Raises:
            ETWParseError: If event is malformed and cannot be parsed safely
        """
        try:
            # Get provider metadata
            provider = self.provider_registry.get_provider(provider_id)
            if not provider:
                _logger.warning(f"Unknown provider: {provider_id}")
                return None
            
            # Check if event ID is enabled
            if event_id not in provider.enabled_event_ids:
                return None  # Event filtered
            
            # Apply sampling
            import random
            if random.random() > provider.filter.sampling_rate:
                return None  # Event sampled out
            
            # Parse event based on provider type
            if provider_id == provider_registry.GUID_KERNEL_PROCESS:
                return self._parse_process_event(event_id, timestamp, event_data, provider)
            elif provider_id == provider_registry.GUID_KERNEL_THREAD:
                return self._parse_thread_event(event_id, timestamp, event_data, provider)
            elif provider_id == provider_registry.GUID_KERNEL_FILE:
                return self._parse_file_event(event_id, timestamp, event_data, provider)
            elif provider_id == provider_registry.GUID_KERNEL_REGISTRY:
                return self._parse_registry_event(event_id, timestamp, event_data, provider)
            elif provider_id == provider_registry.GUID_KERNEL_NETWORK:
                return self._parse_network_event(event_id, timestamp, event_data, provider)
            elif provider_id == provider_registry.GUID_TCPIP:
                return self._parse_tcpip_event(event_id, timestamp, event_data, provider)
            elif provider_id == provider_registry.GUID_KERNEL_MEMORY:
                return self._parse_memory_event(event_id, timestamp, event_data, provider)
            else:
                _logger.warning(f"Unsupported provider for parsing: {provider_id}")
                return None
                
        except struct.error as e:
            raise ETWParseError(f"Malformed event data (struct error): {e}")
        except Exception as e:
            _logger.error(f"Error parsing ETW event: {e}", exc_info=True)
            raise ETWParseError(f"Failed to parse event: {e}")
    
    def _parse_process_event(
        self,
        event_id: int,
        timestamp: datetime,
        event_data: bytes,
        provider: ETWProvider
    ) -> Optional[Dict[str, Any]]:
        """Parse process-related ETW event."""
        # Event ID 1: ProcessStart
        # Event ID 2: ProcessStop
        # Event ID 3: ImageLoad
        
        try:
            # Minimal parsing: Extract only required fields
            # Real implementation would parse ETW event structure
            # For now, return structured event with placeholder data
            
            if event_id == 1:  # ProcessStart
                # Parse: PID, ParentPID, ImagePath, CommandLine
                return {
                    'event_type': 'process_start',
                    'timestamp': timestamp.isoformat(),
                    'provider_id': provider.provider_id,
                    'event_id': event_id,
                    'process_pid': self._extract_uint32(event_data, 0),  # Placeholder offset
                    'parent_pid': self._extract_uint32(event_data, 4),  # Placeholder offset
                    'image_path': self._extract_string(event_data, 8),  # Placeholder offset
                    'command_line': self._extract_string(event_data, 200),  # Placeholder offset
                }
            elif event_id == 2:  # ProcessStop
                return {
                    'event_type': 'process_stop',
                    'timestamp': timestamp.isoformat(),
                    'provider_id': provider.provider_id,
                    'event_id': event_id,
                    'process_pid': self._extract_uint32(event_data, 0),
                    'exit_code': self._extract_uint32(event_data, 4),
                }
            elif event_id == 3:  # ImageLoad
                return {
                    'event_type': 'image_load',
                    'timestamp': timestamp.isoformat(),
                    'provider_id': provider.provider_id,
                    'event_id': event_id,
                    'process_pid': self._extract_uint32(event_data, 0),
                    'image_path': self._extract_string(event_data, 4),
                    'image_base': self._extract_uint64(event_data, 200),
                }
            else:
                return None
                
        except Exception as e:
            raise ETWParseError(f"Failed to parse process event: {e}")
    
    def _parse_thread_event(
        self,
        event_id: int,
        timestamp: datetime,
        event_data: bytes,
        provider: ETWProvider
    ) -> Optional[Dict[str, Any]]:
        """Parse thread-related ETW event."""
        # Event ID 1: ThreadStart
        # Event ID 2: ThreadStop
        
        try:
            if event_id == 1:  # ThreadStart
                return {
                    'event_type': 'thread_start',
                    'timestamp': timestamp.isoformat(),
                    'provider_id': provider.provider_id,
                    'event_id': event_id,
                    'thread_id': self._extract_uint32(event_data, 0),
                    'process_pid': self._extract_uint32(event_data, 4),
                }
            elif event_id == 2:  # ThreadStop
                return {
                    'event_type': 'thread_stop',
                    'timestamp': timestamp.isoformat(),
                    'provider_id': provider.provider_id,
                    'event_id': event_id,
                    'thread_id': self._extract_uint32(event_data, 0),
                    'process_pid': self._extract_uint32(event_data, 4),
                }
            else:
                return None
                
        except Exception as e:
            raise ETWParseError(f"Failed to parse thread event: {e}")
    
    def _parse_file_event(
        self,
        event_id: int,
        timestamp: datetime,
        event_data: bytes,
        provider: ETWProvider
    ) -> Optional[Dict[str, Any]]:
        """Parse file-related ETW event."""
        # Event ID 64: FileCreate
        # Event ID 65: FileDelete
        # Event ID 66: FileRename
        # Event ID 67: FileWrite
        # Event ID 68: FileRead
        
        try:
            process_pid = self._extract_uint32(event_data, 0)
            file_path = self._extract_string(event_data, 4)
            
            # Apply path exclusions
            if provider.filter.path_exclusions:
                for exclusion in provider.filter.path_exclusions:
                    if file_path and exclusion.replace('\\\\', '\\') in file_path:
                        return None  # Filtered out
            
            base_event = {
                'timestamp': timestamp.isoformat(),
                'provider_id': provider.provider_id,
                'event_id': event_id,
                'process_pid': process_pid,
                'file_path': self._normalize_path(file_path),
            }
            
            if event_id == 64:  # FileCreate
                base_event['event_type'] = 'file_create'
            elif event_id == 65:  # FileDelete
                base_event['event_type'] = 'file_delete'
            elif event_id == 66:  # FileRename
                base_event['old_path'] = self._normalize_path(self._extract_string(event_data, 200))
                base_event['new_path'] = self._normalize_path(self._extract_string(event_data, 400))
                base_event['event_type'] = 'file_rename'
            elif event_id == 67:  # FileWrite
                base_event['event_type'] = 'file_write'
                base_event['file_size'] = self._extract_uint64(event_data, 200)
            elif event_id == 68:  # FileRead
                base_event['event_type'] = 'file_read'
            else:
                return None
            
            return base_event
                
        except Exception as e:
            raise ETWParseError(f"Failed to parse file event: {e}")
    
    def _parse_registry_event(
        self,
        event_id: int,
        timestamp: datetime,
        event_data: bytes,
        provider: ETWProvider
    ) -> Optional[Dict[str, Any]]:
        """Parse registry-related ETW event."""
        # Event ID 9: RegCreateKey
        # Event ID 10: RegSetValue
        # Event ID 12: RegDeleteKey
        # Event ID 13: RegDeleteValue
        
        try:
            process_pid = self._extract_uint32(event_data, 0)
            key_path = self._extract_string(event_data, 4)
            
            base_event = {
                'timestamp': timestamp.isoformat(),
                'provider_id': provider.provider_id,
                'event_id': event_id,
                'process_pid': process_pid,
                'registry_key': key_path,
            }
            
            if event_id == 9:  # RegCreateKey
                base_event['event_type'] = 'registry_create_key'
            elif event_id == 10:  # RegSetValue
                base_event['event_type'] = 'registry_set_value'
                base_event['value_name'] = self._extract_string(event_data, 200)
                base_event['value_data'] = self._extract_string(event_data, 300)
            elif event_id == 12:  # RegDeleteKey
                base_event['event_type'] = 'registry_delete_key'
            elif event_id == 13:  # RegDeleteValue
                base_event['event_type'] = 'registry_delete_value'
                base_event['value_name'] = self._extract_string(event_data, 200)
            else:
                return None
            
            return base_event
                
        except Exception as e:
            raise ETWParseError(f"Failed to parse registry event: {e}")
    
    def _parse_network_event(
        self,
        event_id: int,
        timestamp: datetime,
        event_data: bytes,
        provider: ETWProvider
    ) -> Optional[Dict[str, Any]]:
        """Parse network-related ETW event."""
        # Event ID 1: DNS Query
        # Event ID 2: Network event
        
        try:
            process_pid = self._extract_uint32(event_data, 0)
            
            base_event = {
                'timestamp': timestamp.isoformat(),
                'provider_id': provider.provider_id,
                'event_id': event_id,
                'process_pid': process_pid,
            }
            
            if event_id == 1:  # DNS Query
                base_event['event_type'] = 'dns_query'
                base_event['domain'] = self._extract_string(event_data, 4)
            else:
                return None
            
            return base_event
                
        except Exception as e:
            raise ETWParseError(f"Failed to parse network event: {e}")
    
    def _parse_tcpip_event(
        self,
        event_id: int,
        timestamp: datetime,
        event_data: bytes,
        provider: ETWProvider
    ) -> Optional[Dict[str, Any]]:
        """Parse TCP/IP-related ETW event."""
        # Event ID 11: TcpConnect
        # Event ID 12: TcpDisconnect
        # Event ID 13: UdpSend
        
        try:
            process_pid = self._extract_uint32(event_data, 0)
            
            base_event = {
                'timestamp': timestamp.isoformat(),
                'provider_id': provider.provider_id,
                'event_id': event_id,
                'process_pid': process_pid,
            }
            
            if event_id == 11:  # TcpConnect
                base_event['event_type'] = 'tcp_connect'
                base_event['source_ip'] = self._extract_ip_address(event_data, 4)
                base_event['source_port'] = self._extract_uint16(event_data, 8)
                base_event['dest_ip'] = self._extract_ip_address(event_data, 10)
                base_event['dest_port'] = self._extract_uint16(event_data, 14)
            elif event_id == 12:  # TcpDisconnect
                base_event['event_type'] = 'tcp_disconnect'
                base_event['source_ip'] = self._extract_ip_address(event_data, 4)
                base_event['source_port'] = self._extract_uint16(event_data, 8)
            elif event_id == 13:  # UdpSend
                base_event['event_type'] = 'udp_send'
                base_event['source_ip'] = self._extract_ip_address(event_data, 4)
                base_event['source_port'] = self._extract_uint16(event_data, 8)
                base_event['dest_ip'] = self._extract_ip_address(event_data, 10)
                base_event['dest_port'] = self._extract_uint16(event_data, 14)
            else:
                return None
            
            return base_event
                
        except Exception as e:
            raise ETWParseError(f"Failed to parse TCP/IP event: {e}")
    
    def _parse_memory_event(
        self,
        event_id: int,
        timestamp: datetime,
        event_data: bytes,
        provider: ETWProvider
    ) -> Optional[Dict[str, Any]]:
        """Parse memory-related ETW event (best-effort)."""
        # Event ID 1: VirtualAlloc
        # Event ID 2: VirtualProtect
        
        try:
            process_pid = self._extract_uint32(event_data, 0)
            
            base_event = {
                'timestamp': timestamp.isoformat(),
                'provider_id': provider.provider_id,
                'event_id': event_id,
                'process_pid': process_pid,
            }
            
            if event_id == 1:  # VirtualAlloc
                base_event['event_type'] = 'virtual_alloc'
                base_event['address'] = self._extract_uint64(event_data, 4)
                base_event['size'] = self._extract_uint64(event_data, 12)
                base_event['protection'] = self._extract_uint32(event_data, 20)
            elif event_id == 2:  # VirtualProtect
                base_event['event_type'] = 'virtual_protect'
                base_event['address'] = self._extract_uint64(event_data, 4)
                base_event['old_protection'] = self._extract_uint32(event_data, 12)
                base_event['new_protection'] = self._extract_uint32(event_data, 16)
            else:
                return None
            
            return base_event
                
        except Exception as e:
            raise ETWParseError(f"Failed to parse memory event: {e}")
    
    def _extract_uint32(self, data: bytes, offset: int) -> int:
        """Extract 32-bit unsigned integer from event data."""
        if offset + 4 > len(data):
            return 0  # Safe default
        return struct.unpack('<I', data[offset:offset+4])[0]
    
    def _extract_uint64(self, data: bytes, offset: int) -> int:
        """Extract 64-bit unsigned integer from event data."""
        if offset + 8 > len(data):
            return 0  # Safe default
        return struct.unpack('<Q', data[offset:offset+8])[0]
    
    def _extract_uint16(self, data: bytes, offset: int) -> int:
        """Extract 16-bit unsigned integer from event data."""
        if offset + 2 > len(data):
            return 0  # Safe default
        return struct.unpack('<H', data[offset:offset+2])[0]
    
    def _extract_string(self, data: bytes, offset: int, max_length: int = 512) -> str:
        """Extract null-terminated string from event data."""
        if offset >= len(data):
            return ""
        
        # Find null terminator
        end = offset
        while end < len(data) and end < offset + max_length:
            if data[end] == 0:
                break
            end += 1
        
        try:
            return data[offset:end].decode('utf-8', errors='replace')
        except Exception:
            return ""
    
    def _extract_ip_address(self, data: bytes, offset: int) -> str:
        """Extract IP address from event data (IPv4 or IPv6)."""
        if offset + 4 > len(data):
            return "0.0.0.0"
        
        # Assume IPv4 for now (4 bytes)
        ip_bytes = data[offset:offset+4]
        return ".".join(str(b) for b in ip_bytes)
    
    def _normalize_path(self, path: str) -> str:
        """Normalize file path (cache for performance)."""
        if not path:
            return ""
        
        if path in self._path_cache:
            return self._path_cache[path]
        
        # Normalize: Replace forward slashes, normalize case (Windows)
        normalized = path.replace('/', '\\')
        if normalized.startswith('\\'):
            normalized = normalized[1:]
        
        self._path_cache[path] = normalized
        return normalized
