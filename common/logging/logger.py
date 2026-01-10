#!/usr/bin/env python3
"""
RansomEye v1.0 Common Logging
AUTHORITATIVE: Structured logging with explicit severity levels
Phase 10 requirement: Explicit logging (startup, shutdown, failure), no silent crashes
"""

import sys
import logging
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum

# Security: Import redaction utilities
try:
    from common.security.redaction import (redact_secrets, sanitize_string_for_logging,
                                          validate_secret_not_logged, sanitize_exception,
                                          get_redacted_config)
    _security_redaction_available = True
except ImportError:
    _security_redaction_available = False
    def redact_secrets(data): return data
    def sanitize_string_for_logging(text): return text
    def validate_secret_not_logged(value, context=""): pass
    def sanitize_exception(exception): return str(exception)
    def get_redacted_config(config): return config


class LogLevel(Enum):
    """Log severity levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


class StructuredLogger:
    """
    Structured logger for RansomEye services.
    
    Phase 10 requirement: Explicit logging with clear severity levels.
    """
    
    def __init__(self, component_name: str, log_to_stderr: bool = True):
        """
        Initialize structured logger.
        
        Args:
            component_name: Component name (e.g., 'ingest', 'correlation-engine')
            log_to_stderr: Log to stderr (default: True)
        """
        self.component_name = component_name
        self.logger = logging.getLogger(component_name)
        self.logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Add stderr handler
        if log_to_stderr:
            handler = logging.StreamHandler(sys.stderr)
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _log(self, level: LogLevel, message: str, **kwargs):
        """
        Internal logging method with structured fields.
        
        Security: Redacts secrets from logs. Terminates Core if secret detected.
        Resource safety: If logging fails, terminate Core immediately (fail-fast).
        Prevents unbounded log growth by limiting message size.
        """
        try:
            # Security: Validate no secrets in message
            if _security_redaction_available:
                validate_secret_not_logged(message, f"log message in {self.component_name}")
            
            # Security: Sanitize message for secrets
            if _security_redaction_available:
                message = sanitize_string_for_logging(message)
            
            # Limit message size to prevent unbounded log growth (1MB max per message)
            MAX_LOG_MESSAGE_SIZE = 1024 * 1024  # 1MB
            if len(message.encode('utf-8')) > MAX_LOG_MESSAGE_SIZE:
                message = message[:MAX_LOG_MESSAGE_SIZE] + "... (truncated)"
            
            # Security: Redact secrets from kwargs
            if _security_redaction_available:
                kwargs = redact_secrets(kwargs)
            
            log_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'component': self.component_name,
                'level': level.value,
                'message': message,
                **kwargs
            }
            
            # Log with appropriate level
            log_msg = json.dumps(log_entry) if kwargs else message
            if level == LogLevel.DEBUG:
                self.logger.debug(log_msg)
            elif level == LogLevel.INFO:
                self.logger.info(log_msg)
            elif level == LogLevel.WARNING:
                self.logger.warning(log_msg)
            elif level == LogLevel.ERROR:
                self.logger.error(log_msg)
            elif level == LogLevel.FATAL:
                self.logger.critical(log_msg)
                # Fatal errors should also be written to stderr explicitly (sanitized)
                if _security_redaction_available:
                    safe_msg = sanitize_string_for_logging(message)
                else:
                    safe_msg = message
                print(f"FATAL: {self.component_name}: {safe_msg}", file=sys.stderr)
        except MemoryError:
            # Memory allocation failure during logging - terminate Core immediately
            error_msg = f"LOGGING FAILURE: Memory allocation failed while logging: {self.component_name}: {message[:100]}"
            print(f"FATAL: {error_msg}", file=sys.stderr)
            sys.exit(4)  # FATAL_ERROR
        except (OSError, IOError) as e:
            # Disk/logging failure - terminate Core immediately
            if _security_redaction_available:
                safe_error = sanitize_exception(e)
            else:
                safe_error = str(e)
            error_msg = f"LOGGING FAILURE: Disk/logging operation failed: {safe_error}"
            print(f"FATAL: {error_msg}", file=sys.stderr)
            sys.exit(4)  # FATAL_ERROR
        except Exception as e:
            # Unexpected logging failure - terminate Core immediately
            if _security_redaction_available:
                safe_error = sanitize_exception(e)
            else:
                safe_error = str(e)
            error_msg = f"LOGGING FAILURE: Unexpected error in logging: {safe_error}"
            print(f"FATAL: {error_msg}", file=sys.stderr)
            sys.exit(4)  # FATAL_ERROR
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self._log(LogLevel.ERROR, message, **kwargs)
    
    def fatal(self, message: str, **kwargs):
        """Log fatal error (must exit after)."""
        self._log(LogLevel.FATAL, message, **kwargs)
    
    def startup(self, message: str, **kwargs):
        """Log startup message."""
        self.info(f"STARTUP: {message}", **kwargs)
    
    def shutdown(self, message: str, **kwargs):
        """Log shutdown message."""
        self.info(f"SHUTDOWN: {message}", **kwargs)
    
    def config_error(self, error: str, **kwargs):
        """Log configuration error (fatal)."""
        self.fatal(f"Configuration error: {error}", error_type='CONFIG_ERROR', **kwargs)
    
    def db_error(self, error: str, operation: str, **kwargs):
        """
        Log database error.
        
        Security: Sanitizes error message to prevent secret leakage.
        """
        # Security: Sanitize error message
        if _security_redaction_available:
            safe_error = sanitize_string_for_logging(error)
        else:
            safe_error = error
        self.error(f"Database error in {operation}: {safe_error}", 
                  error_type='DB_ERROR', operation=operation, **kwargs)
    
    def resource_error(self, resource: str, error: str, **kwargs):
        """Log resource error (e.g., disk full, connection limit)."""
        self.error(f"Resource error ({resource}): {error}",
                  error_type='RESOURCE_ERROR', resource=resource, **kwargs)


def setup_logging(component_name: str, log_to_stderr: bool = True) -> StructuredLogger:
    """
    Setup structured logging for component.
    
    Args:
        component_name: Component name
        log_to_stderr: Log to stderr (default: True)
        
    Returns:
        Configured StructuredLogger instance
    """
    return StructuredLogger(component_name, log_to_stderr)
