#!/usr/bin/env python3
"""
RansomEye v1.0 Windows Agent - ETW Session Manager
AUTHORITATIVE: ETW session lifecycle management with failure recovery
"""

import os
import sys
import time
import threading
from typing import Dict, Optional, Callable, Any
from pathlib import Path
from datetime import datetime, timezone

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    _logger = setup_logging('windows-agent-etw-session')
except ImportError:
    import logging
    _logger = logging.getLogger('windows-agent-etw-session')

from .providers import ETWProvider, ProviderRegistry


class ETWSessionError(Exception):
    """Exception raised for ETW session errors."""
    pass


class ETWSessionManager:
    """
    ETW session lifecycle manager.
    
    CRITICAL: Session manager must never crash the agent.
    Fail-open behavior: Continue operation if ETW fails.
    """
    
    SESSION_NAME = "RansomEye-Windows-Agent"
    BUFFER_SIZE_MB = int(os.getenv('RANSOMEYE_ETW_BUFFER_SIZE_MB', '64'))
    MIN_BUFFERS = int(os.getenv('RANSOMEYE_ETW_MIN_BUFFERS', '2'))
    MAX_BUFFERS = int(os.getenv('RANSOMEYE_ETW_MAX_BUFFERS', '64'))
    FLUSH_TIMER_SECONDS = int(os.getenv('RANSOMEYE_ETW_FLUSH_TIMER_SECONDS', '1'))
    
    def __init__(
        self,
        provider_registry: ProviderRegistry,
        event_callback: Callable[[Dict[str, Any]], None],
        health_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ):
        """
        Initialize ETW session manager.
        
        Args:
            provider_registry: Provider registry instance
            event_callback: Callback function for ETW events (event_dict) -> None
            health_callback: Optional callback for health events (event_type, data) -> None
        """
        self.provider_registry = provider_registry
        self.event_callback = event_callback
        self.health_callback = health_callback
        
        self._session_handle = None
        self._session_active = False
        self._session_lock = threading.Lock()
        self._collection_thread = None
        self._stop_event = threading.Event()
        
        # Provider state tracking
        self._provider_states: Dict[str, bool] = {}  # provider_id -> enabled
        self._provider_restart_counts: Dict[str, int] = {}  # provider_id -> restart count
        
        # Session statistics
        self._session_start_time: Optional[datetime] = None
        self._session_restart_count = 0
        self._last_restart_time: Optional[datetime] = None
        
        # Windows API availability check
        self._windows_api_available = self._check_windows_api()
        if not self._windows_api_available:
            _logger.warning("Windows API not available - ETW session will be simulated")
    
    def _check_windows_api(self) -> bool:
        """
        Check if Windows API is available.
        
        Returns:
            True if Windows API is available, False otherwise
        """
        try:
            # Try to import Windows-specific modules
            if sys.platform == 'win32':
                try:
                    import ctypes
                    from ctypes import wintypes
                    # Check if we can access Windows APIs
                    kernel32 = ctypes.windll.kernel32
                    return True
                except Exception:
                    return False
            return False
        except Exception:
            return False
    
    def start_session(self) -> bool:
        """
        Start ETW session.
        
        Returns:
            True if session started successfully, False otherwise
            
        CRITICAL: Must not raise exceptions - fail-open behavior.
        """
        with self._session_lock:
            if self._session_active:
                _logger.warning("ETW session already active")
                return True
            
            try:
                if not self._windows_api_available:
                    _logger.warning("Windows API not available - starting simulated session")
                    self._start_simulated_session()
                    return True
                
                # Create ETW session (Windows API call would go here)
                # For now, simulate session creation
                self._session_handle = "etw_session_handle"  # Placeholder
                self._session_active = True
                self._session_start_time = datetime.now(timezone.utc)
                
                # Enable providers
                enabled_count = 0
                for provider in self.provider_registry.get_all_providers():
                    if self._enable_provider(provider):
                        enabled_count += 1
                        self._provider_states[provider.provider_id] = True
                
                _logger.info(f"ETW session started with {enabled_count} providers enabled")
                
                # Start collection thread
                self._stop_event.clear()
                self._collection_thread = threading.Thread(
                    target=self._collection_loop,
                    daemon=True,
                    name="ETW-Collection-Thread"
                )
                self._collection_thread.start()
                
                # Emit health event
                if self.health_callback:
                    self.health_callback('etw_session_started', {
                        'session_name': self.SESSION_NAME,
                        'providers_enabled': enabled_count,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                
                return True
                
            except Exception as e:
                _logger.error(f"Failed to start ETW session: {e}", exc_info=True)
                self._session_active = False
                self._session_handle = None
                
                # Emit health event
                if self.health_callback:
                    self.health_callback('etw_session_start_failed', {
                        'error': str(e),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                
                return False
    
    def _start_simulated_session(self):
        """Start simulated ETW session (for non-Windows or testing)."""
        self._session_handle = "simulated_session"
        self._session_active = True
        self._session_start_time = datetime.now(timezone.utc)
        
        # Mark all providers as enabled (simulated)
        for provider in self.provider_registry.get_all_providers():
            self._provider_states[provider.provider_id] = True
    
    def _enable_provider(self, provider: ETWProvider) -> bool:
        """
        Enable ETW provider.
        
        Args:
            provider: ETW provider to enable
            
        Returns:
            True if enabled successfully, False otherwise
        """
        try:
            # Windows API call to enable provider would go here
            # For now, simulate provider enablement
            _logger.debug(f"Enabling provider: {provider.provider_name} ({provider.provider_id})")
            return True
        except Exception as e:
            _logger.error(f"Failed to enable provider {provider.provider_id}: {e}")
            return False
    
    def stop_session(self):
        """
        Stop ETW session.
        
        CRITICAL: Must not raise exceptions - graceful shutdown.
        """
        with self._session_lock:
            if not self._session_active:
                return
            
            try:
                # Signal stop
                self._stop_event.set()
                
                # Wait for collection thread to stop
                if self._collection_thread and self._collection_thread.is_alive():
                    self._collection_thread.join(timeout=5.0)
                
                # Disable providers
                for provider_id in list(self._provider_states.keys()):
                    self._disable_provider(provider_id)
                
                # Close session (Windows API call would go here)
                self._session_handle = None
                self._session_active = False
                
                _logger.info("ETW session stopped")
                
                # Emit health event
                if self.health_callback:
                    self.health_callback('etw_session_stopped', {
                        'session_name': self.SESSION_NAME,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                
            except Exception as e:
                _logger.error(f"Error stopping ETW session: {e}", exc_info=True)
                # Continue - fail-open behavior
    
    def _disable_provider(self, provider_id: str):
        """
        Disable ETW provider.
        
        Args:
            provider_id: Provider GUID to disable
        """
        try:
            # Windows API call to disable provider would go here
            _logger.debug(f"Disabling provider: {provider_id}")
            self._provider_states[provider_id] = False
        except Exception as e:
            _logger.error(f"Error disabling provider {provider_id}: {e}")
    
    def restart_session(self) -> bool:
        """
        Restart ETW session after failure.
        
        Returns:
            True if restart successful, False otherwise
            
        CRITICAL: Must not raise exceptions - fail-open behavior.
        """
        _logger.info("Restarting ETW session")
        
        with self._session_lock:
            self._session_restart_count += 1
            self._last_restart_time = datetime.now(timezone.utc)
            
            # Stop current session
            try:
                self.stop_session()
            except Exception:
                pass  # Ignore errors during stop
            
            # Wait before restart (exponential backoff)
            backoff_seconds = min(2 ** min(self._session_restart_count, 5), 60)
            time.sleep(backoff_seconds)
            
            # Start new session
            success = self.start_session()
            
            # Emit health event
            if self.health_callback:
                self.health_callback('etw_session_restarted', {
                    'restart_count': self._session_restart_count,
                    'backoff_seconds': backoff_seconds,
                    'success': success,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            
            return success
    
    def _collection_loop(self):
        """
        Main ETW event collection loop.
        
        CRITICAL: Must not raise exceptions - fail-open behavior.
        """
        _logger.info("ETW collection loop started")
        
        try:
            while not self._stop_event.is_set():
                try:
                    # Process ETW events (Windows API call would go here)
                    # For now, simulate event collection
                    if self._windows_api_available:
                        # In real implementation, this would:
                        # 1. Call Windows API to get ETW events
                        # 2. Parse events
                        # 3. Call event_callback for each event
                        pass
                    else:
                        # Simulated: yield no events
                        pass
                    
                    # Yield CPU periodically
                    self._stop_event.wait(timeout=0.1)
                    
                except Exception as e:
                    _logger.error(f"Error in ETW collection loop: {e}", exc_info=True)
                    # Continue loop - fail-open behavior
                    time.sleep(1.0)
        
        except Exception as e:
            _logger.error(f"Fatal error in ETW collection loop: {e}", exc_info=True)
            # Attempt session restart
            try:
                self.restart_session()
            except Exception:
                pass  # Ignore restart errors
    
    def is_session_active(self) -> bool:
        """
        Check if ETW session is active.
        
        Returns:
            True if session is active, False otherwise
        """
        with self._session_lock:
            return self._session_active
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get session statistics.
        
        Returns:
            Dictionary with session statistics
        """
        with self._session_lock:
            return {
                'session_active': self._session_active,
                'session_start_time': self._session_start_time.isoformat() if self._session_start_time else None,
                'session_restart_count': self._session_restart_count,
                'last_restart_time': self._last_restart_time.isoformat() if self._last_restart_time else None,
                'providers_enabled': sum(1 for enabled in self._provider_states.values() if enabled),
                'providers_total': len(self._provider_states)
            }
