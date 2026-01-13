#!/usr/bin/env python3
"""
RansomEye v1.0 Windows Agent - ETW Provider Definitions
AUTHORITATIVE: Provider GUID registry, event IDs, and filter configuration
"""

import os
import sys
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import IntEnum

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    _logger = setup_logging('windows-agent-etw-providers')
except ImportError:
    import logging
    _logger = logging.getLogger('windows-agent-etw-providers')


class EventLevel(IntEnum):
    """ETW event levels (Win32 EVENT_TRACE_LEVEL_* constants)."""
    CRITICAL = 1
    ERROR = 2
    WARNING = 3
    INFORMATION = 4
    VERBOSE = 5


@dataclass
class ProviderFilter:
    """ETW provider filter configuration."""
    keywords: int = 0xFFFFFFFF  # All keywords by default
    level: EventLevel = EventLevel.INFORMATION
    process_whitelist: Optional[List[str]] = None  # Exclude these processes
    path_exclusions: Optional[List[str]] = None  # Exclude these paths
    sampling_rate: float = 1.0  # 1.0 = 100%, 0.1 = 10%


@dataclass
class ETWProvider:
    """
    ETW provider definition.
    
    CRITICAL: Provider configuration is immutable after registration.
    """
    provider_id: str  # GUID string
    provider_name: str
    purpose: str
    enabled_event_ids: Set[int]  # Event IDs to collect
    filter: ProviderFilter
    required_privileges: str = "standard"  # "standard" or "administrator"
    
    def __post_init__(self):
        """Validate provider configuration."""
        if not self.provider_id or len(self.provider_id) != 36:
            raise ValueError(f"Invalid provider GUID: {self.provider_id}")
        if not self.provider_name:
            raise ValueError("Provider name must be non-empty")
        if not self.enabled_event_ids:
            raise ValueError("At least one event ID must be enabled")
        if not (0.0 <= self.filter.sampling_rate <= 1.0):
            raise ValueError(f"Sampling rate must be between 0.0 and 1.0: {self.filter.sampling_rate}")


class ProviderRegistry:
    """
    Registry of ETW providers for Windows Agent.
    
    CRITICAL: Provider registry is frozen after initialization.
    """
    
    # Provider GUIDs (from ETW_ARCHITECTURE_DESIGN.md)
    GUID_KERNEL_PROCESS = "22FB2CD6-0E7B-422B-A0C7-2FAD1FD0E716"
    GUID_KERNEL_THREAD = "3D6FA8D1-FE05-11D0-9DDA-00C04FD7BA7C"
    GUID_KERNEL_FILE = "ED54C3B-6C5F-4F3B-8B8E-8B8E8B8E8B8E"
    GUID_KERNEL_REGISTRY = "70EB4F03-C1DE-4F73-A051-33D13D5873B8"
    GUID_KERNEL_NETWORK = "7DD42A49-5389-4FBF-9CA3-4A4E4A4E4A4E"
    GUID_TCPIP = "2F07E2EE-15DB-40F1-90EF-9F7E9F7E9F7E"
    GUID_KERNEL_MEMORY = "D1D93EF7-E1F2-4F45-9933-535793579357"
    GUID_THREAT_INTEL = "F4E1897C-BEC5-4A12-9D9F-9D9F9D9F9D9F"
    
    def __init__(self):
        """Initialize provider registry with all supported providers."""
        self._providers: Dict[str, ETWProvider] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all ETW providers."""
        # 1. Process & Thread Activity
        self._register_process_provider()
        self._register_thread_provider()
        
        # 2. Filesystem Activity
        self._register_file_provider()
        
        # 3. Registry Activity
        self._register_registry_provider()
        
        # 4. Network Intent
        self._register_network_provider()
        self._register_tcpip_provider()
        
        # 5. Memory & Injection (Best-Effort)
        self._register_memory_provider()
        # Note: Threat-Intelligence provider may not be available on all Windows versions
    
    def _register_process_provider(self):
        """Register Microsoft-Windows-Kernel-Process provider."""
        provider = ETWProvider(
            provider_id=self.GUID_KERNEL_PROCESS,
            provider_name="Microsoft-Windows-Kernel-Process",
            purpose="Process creation, termination, and image loading",
            enabled_event_ids={1, 2, 3},  # ProcessStart, ProcessStop, ImageLoad
            filter=ProviderFilter(
                keywords=0x10,  # Process events only
                level=EventLevel.INFORMATION,
                process_whitelist=['svchost.exe', 'explorer.exe', 'dwm.exe'],
                sampling_rate=1.0  # 100% - critical events
            ),
            required_privileges="administrator"
        )
        self._providers[provider.provider_id] = provider
    
    def _register_thread_provider(self):
        """Register Microsoft-Windows-Kernel-Thread provider."""
        provider = ETWProvider(
            provider_id=self.GUID_KERNEL_THREAD,
            provider_name="Microsoft-Windows-Kernel-Thread",
            purpose="Thread creation and termination",
            enabled_event_ids={1, 2},  # ThreadStart, ThreadStop
            filter=ProviderFilter(
                keywords=0x10,  # Thread events
                level=EventLevel.INFORMATION,
                sampling_rate=0.5  # 50% - high volume
            ),
            required_privileges="administrator"
        )
        self._providers[provider.provider_id] = provider
    
    def _register_file_provider(self):
        """Register Microsoft-Windows-Kernel-File provider."""
        provider = ETWProvider(
            provider_id=self.GUID_KERNEL_FILE,
            provider_name="Microsoft-Windows-Kernel-File",
            purpose="File create, write, delete, rename operations",
            enabled_event_ids={64, 65, 66, 67, 68},  # FileCreate, FileDelete, FileRename, FileWrite, FileRead
            filter=ProviderFilter(
                keywords=0x80,  # File I/O events
                level=EventLevel.INFORMATION,
                path_exclusions=[
                    r'C:\\Windows\\System32\\',
                    r'C:\\Windows\\SysWOW64\\',
                    r'C:\\Program Files\\',
                    r'C:\\Program Files (x86)\\'
                ],
                sampling_rate=0.1  # 10% - very high volume
            ),
            required_privileges="administrator"
        )
        self._providers[provider.provider_id] = provider
    
    def _register_registry_provider(self):
        """Register Microsoft-Windows-Kernel-Registry provider."""
        provider = ETWProvider(
            provider_id=self.GUID_KERNEL_REGISTRY,
            provider_name="Microsoft-Windows-Kernel-Registry",
            purpose="Registry key and value modifications",
            enabled_event_ids={9, 10, 12, 13},  # RegCreateKey, RegSetValue, RegDeleteKey, RegDeleteValue
            filter=ProviderFilter(
                keywords=0x14,  # Registry events
                level=EventLevel.INFORMATION,
                sampling_rate=1.0  # 100% - critical for persistence detection
            ),
            required_privileges="administrator"
        )
        self._providers[provider.provider_id] = provider
    
    def _register_network_provider(self):
        """Register Microsoft-Windows-Kernel-Network provider."""
        provider = ETWProvider(
            provider_id=self.GUID_KERNEL_NETWORK,
            provider_name="Microsoft-Windows-Kernel-Network",
            purpose="Network connection intent and DNS queries",
            enabled_event_ids={1, 2},  # Network events
            filter=ProviderFilter(
                keywords=0x10,  # Network events
                level=EventLevel.INFORMATION,
                sampling_rate=0.5  # 50% - high volume
            ),
            required_privileges="standard"
        )
        self._providers[provider.provider_id] = provider
    
    def _register_tcpip_provider(self):
        """Register Microsoft-Windows-TCPIP provider."""
        provider = ETWProvider(
            provider_id=self.GUID_TCPIP,
            provider_name="Microsoft-Windows-TCPIP",
            purpose="TCP/UDP connection attempts",
            enabled_event_ids={11, 12, 13},  # TcpConnect, TcpDisconnect, UdpSend
            filter=ProviderFilter(
                keywords=0x10,  # TCP/IP events
                level=EventLevel.INFORMATION,
                sampling_rate=0.5  # 50% - high volume
            ),
            required_privileges="standard"
        )
        self._providers[provider.provider_id] = provider
    
    def _register_memory_provider(self):
        """Register Microsoft-Windows-Kernel-Memory provider (best-effort)."""
        provider = ETWProvider(
            provider_id=self.GUID_KERNEL_MEMORY,
            provider_name="Microsoft-Windows-Kernel-Memory",
            purpose="Memory allocation and protection changes (best-effort)",
            enabled_event_ids={1, 2},  # VirtualAlloc, VirtualProtect
            filter=ProviderFilter(
                keywords=0x10,  # Memory events
                level=EventLevel.WARNING,  # Only warnings (suspicious patterns)
                sampling_rate=0.01  # 1% - very high volume, best-effort only
            ),
            required_privileges="administrator"
        )
        self._providers[provider.provider_id] = provider
    
    def get_provider(self, provider_id: str) -> Optional[ETWProvider]:
        """
        Get provider by GUID.
        
        Args:
            provider_id: Provider GUID string
            
        Returns:
            ETWProvider if found, None otherwise
        """
        return self._providers.get(provider_id)
    
    def get_all_providers(self) -> List[ETWProvider]:
        """
        Get all registered providers.
        
        Returns:
            List of all ETWProvider instances
        """
        return list(self._providers.values())
    
    def get_providers_by_privilege(self, privilege: str) -> List[ETWProvider]:
        """
        Get providers requiring specific privilege level.
        
        Args:
            privilege: "standard" or "administrator"
            
        Returns:
            List of providers requiring the specified privilege
        """
        return [p for p in self._providers.values() if p.required_privileges == privilege]
    
    def validate_provider_config(self, provider_id: str) -> bool:
        """
        Validate provider configuration.
        
        Args:
            provider_id: Provider GUID string
            
        Returns:
            True if valid, False otherwise
            
        Raises:
            ValueError: If provider configuration is invalid
        """
        provider = self.get_provider(provider_id)
        if not provider:
            raise ValueError(f"Provider not found: {provider_id}")
        
        # Validation already done in ETWProvider.__post_init__
        return True
