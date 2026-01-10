#!/usr/bin/env python3
"""
RansomEye v1.0 Common Configuration Loader
AUTHORITATIVE: Centralized configuration loading and validation
Phase 10 requirement: Hardened configuration, no fallback defaults for security-sensitive values
"""

import os
import sys
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path


class ConfigError(Exception):
    """Configuration error (fatal, must fail-fast)."""
    pass


class ConfigLoader:
    """
    Centralized configuration loader with explicit validation.
    Phase 10 requirement: No fallback defaults for security-sensitive values.
    """
    
    def __init__(self, component_name: str):
        """
        Initialize configuration loader.
        
        Args:
            component_name: Component name (e.g., 'ingest', 'correlation-engine')
        """
        self.component_name = component_name
        self.config: Dict[str, Any] = {}
        self.required_vars: List[str] = []
        self.validators: Dict[str, Callable[[str], Any]] = {}
        
    def require(self, var_name: str, validator: Optional[Callable[[str], Any]] = None, 
                description: str = "") -> 'ConfigLoader':
        """
        Mark environment variable as required.
        
        Phase 10 requirement: Missing required variables cause hard failure.
        
        Args:
            var_name: Environment variable name
            validator: Optional validator function (raises ConfigError on failure)
            description: Human-readable description (for error messages)
            
        Returns:
            Self for chaining
        """
        self.required_vars.append(var_name)
        if validator:
            self.validators[var_name] = validator
        if description:
            if not hasattr(self, '_descriptions'):
                self._descriptions = {}
            self._descriptions[var_name] = description
        return self
    
    def optional(self, var_name: str, default: Any = None, 
                 validator: Optional[Callable[[str], Any]] = None) -> 'ConfigLoader':
        """
        Mark environment variable as optional with default.
        
        Phase 10 requirement: Only non-security-sensitive values may have defaults.
        
        Args:
            var_name: Environment variable name
            default: Default value if not set
            validator: Optional validator function
            default: Default value
            
        Returns:
            Self for chaining
        """
        value = os.getenv(var_name, default)
        if value is not None and validator:
            try:
                value = validator(value)
            except Exception as e:
                raise ConfigError(
                    f"Invalid value for optional config {var_name}: {e}"
                ) from e
        self.config[var_name] = value
        return self
    
    def load(self) -> Dict[str, Any]:
        """
        Load and validate all configuration.
        
        Phase 10 requirement: Fail-fast on missing required or invalid configuration.
        
        Returns:
            Validated configuration dictionary
            
        Raises:
            ConfigError: If required variables are missing or validation fails
        """
        errors = []
        
        # Security: Initialize secret storage (never logged)
        self._secret_values = {}
        
        # Check required variables
        for var_name in self.required_vars:
            # Security: Check if this is a secret (password, key, token, etc.)
            is_secret = any(pattern in var_name.lower() for pattern in ['password', 'secret', 'key', 'token', 'auth'])
            
            # Security: Use secret validation for secrets
            if is_secret:
                try:
                    from common.security.secrets import validate_secret_present
                    value = validate_secret_present(var_name, min_length=8)
                    # Security: Never store secret in config dict (redacted version only)
                    self.config[var_name] = "[REDACTED]"
                    # Store actual secret separately (never logged)
                    self._secret_values[var_name] = value
                except ImportError:
                    # Fallback if security utilities not available
                    value = os.getenv(var_name)
                    if not value:
                        desc = getattr(self, '_descriptions', {}).get(var_name, "")
                        error_msg = f"Required secret {var_name} is missing or empty"
                        if desc:
                            error_msg += f" ({desc})"
                        errors.append(error_msg)
                        continue
                    if len(value) < 8:
                        errors.append(f"Secret {var_name} is too short (minimum 8 characters)")
                        continue
                    self.config[var_name] = "[REDACTED]"
                    self._secret_values[var_name] = value
            else:
                value = os.getenv(var_name)
                if value is None or value == "":
                    desc = getattr(self, '_descriptions', {}).get(var_name, "")
                    error_msg = f"Required environment variable {var_name} is missing or empty"
                    if desc:
                        error_msg += f" ({desc})"
                    errors.append(error_msg)
                    continue
                
                # Validate if validator exists
                if var_name in self.validators:
                    try:
                        validated_value = self.validators[var_name](value)
                        self.config[var_name] = validated_value
                    except Exception as e:
                        errors.append(
                            f"Invalid value for {var_name}: {e}"
                        )
                else:
                    self.config[var_name] = value
        
        if errors:
            error_summary = "\n".join(f"  - {err}" for err in errors)
            raise ConfigError(
                f"Configuration validation failed for {self.component_name}:\n{error_summary}"
            )
        
        return self.config.copy()
    
    def get_secret(self, env_var: str) -> str:
        """
        Get secret value (never logged).
        
        Security: Returns actual secret value from secure storage.
        Terminates Core immediately if secret is not available.
        
        Args:
            env_var: Environment variable name
            
        Returns:
            Secret value (never logged)
        """
        if hasattr(self, '_secret_values') and env_var in self._secret_values:
            return self._secret_values[env_var]
        # Fallback: get from environment (should not happen if secret was validated)
        value = os.getenv(env_var)
        if not value:
            error_msg = f"SECURITY VIOLATION: Secret {env_var} is not available"
            print(f"FATAL: {error_msg}", file=sys.stderr)
            sys.exit(1)  # CONFIG_ERROR
        return value
    
    def get_secret(self, env_var: str) -> str:
        """
        Get secret value (never logged).
        
        Security: Returns actual secret value from secure storage.
        Terminates Core immediately if secret is not available.
        
        Args:
            env_var: Environment variable name
            
        Returns:
            Secret value (never logged)
        """
        if hasattr(self, '_secret_values') and env_var in self._secret_values:
            return self._secret_values[env_var]
        # Fallback: get from environment (should not happen if secret was validated)
        value = os.getenv(env_var)
        if not value:
            error_msg = f"SECURITY VIOLATION: Secret {env_var} is not available"
            print(f"FATAL: {error_msg}", file=sys.stderr)
            sys.exit(1)  # CONFIG_ERROR
        return value


def validate_db_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate database configuration.
    
    Phase 10 requirement: Database password must not be empty.
    """
    password = config.get('RANSOMEYE_DB_PASSWORD')
    if not password or password == "":
        raise ConfigError("RANSOMEYE_DB_PASSWORD is required and cannot be empty (security-sensitive)")
    
    return config


def validate_path(path_str: str, must_exist: bool = False, 
                  must_be_writable: bool = False) -> Path:
    """
    Validate path configuration.
    
    Phase 10 requirement: All paths must be absolute, no relative paths.
    
    Args:
        path_str: Path string to validate
        must_exist: Path must exist (default: False)
        must_be_writable: Path must be writable (default: False)
        
    Returns:
        Path object
        
    Raises:
        ConfigError: If path is invalid
    """
    path = Path(path_str)
    
    # Must be absolute
    if not path.is_absolute():
        raise ConfigError(f"Path must be absolute: {path_str}")
    
    # Must not end with slash (for directories)
    if str(path).endswith('/'):
        raise ConfigError(f"Path must not end with slash: {path_str}")
    
    # Existence check
    if must_exist and not path.exists():
        raise ConfigError(f"Path does not exist: {path_str}")
    
    # Writable check
    if must_be_writable:
        if not path.exists():
            # Check parent directory is writable
            parent = path.parent
            if not parent.exists() or not os.access(parent, os.W_OK):
                raise ConfigError(f"Parent directory not writable: {parent}")
        elif not os.access(path, os.W_OK):
            raise ConfigError(f"Path not writable: {path_str}")
    
    return path


def validate_port(port_str: str) -> int:
    """
    Validate port number.
    
    Args:
        port_str: Port string to validate
        
    Returns:
        Port number (int)
        
    Raises:
        ConfigError: If port is invalid
    """
    try:
        port = int(port_str)
    except ValueError:
        raise ConfigError(f"Invalid port number: {port_str}")
    
    if port < 1 or port > 65535:
        raise ConfigError(f"Port out of range [1, 65535]: {port}")
    
    return port


def validate_int(int_str: str, min_value: Optional[int] = None, 
                 max_value: Optional[int] = None) -> int:
    """
    Validate integer value.
    
    Args:
        int_str: Integer string to validate
        min_value: Minimum value (optional)
        max_value: Maximum value (optional)
        
    Returns:
        Integer value
        
    Raises:
        ConfigError: If integer is invalid
    """
    try:
        value = int(int_str)
    except ValueError:
        raise ConfigError(f"Invalid integer: {int_str}")
    
    if min_value is not None and value < min_value:
        raise ConfigError(f"Value below minimum {min_value}: {value}")
    
    if max_value is not None and value > max_value:
        raise ConfigError(f"Value above maximum {max_value}: {value}")
    
    return value


def validate_bool(bool_str: str) -> bool:
    """
    Validate boolean value.
    
    Args:
        bool_str: Boolean string ('true', 'false', '1', '0', etc.)
        
    Returns:
        Boolean value
        
    Raises:
        ConfigError: If boolean is invalid
    """
    normalized = bool_str.lower().strip()
    if normalized in ('true', '1', 'yes', 'on', 'enabled'):
        return True
    elif normalized in ('false', '0', 'no', 'off', 'disabled'):
        return False
    else:
        raise ConfigError(f"Invalid boolean value: {bool_str}")


def check_disk_space(path: Path, min_bytes: int = 1024 * 1024) -> None:
    """
    Check available disk space.
    
    Phase 10 requirement: Detect disk full condition (fail-closed).
    
    Args:
        path: Path to check disk space for
        min_bytes: Minimum required bytes (default: 1MB)
        
    Raises:
        ConfigError: If disk space is insufficient
    """
    import shutil
    
    statvfs = os.statvfs(path)
    free_bytes = statvfs.f_bavail * statvfs.f_frsize
    
    if free_bytes < min_bytes:
        raise ConfigError(
            f"Insufficient disk space: {free_bytes} bytes available, "
            f"{min_bytes} bytes required at {path}"
        )


def create_db_config_loader(component_name: str) -> ConfigLoader:
    """
    Create database configuration loader with standard validations.
    
    Phase 10 requirement: Database password is required (no defaults).
    
    Args:
        component_name: Component name
        
    Returns:
        Configured ConfigLoader instance
    """
    loader = ConfigLoader(component_name)
    
    loader.require(
        'RANSOMEYE_DB_PASSWORD',
        description='Database password (security-sensitive, required)'
    )
    loader.optional('RANSOMEYE_DB_HOST', default='localhost')
    loader.optional('RANSOMEYE_DB_PORT', default='5432', 
                   validator=lambda v: validate_port(v))
    loader.optional('RANSOMEYE_DB_NAME', default='ransomeye')
    loader.optional('RANSOMEYE_DB_USER', default='ransomeye')
    
    return loader
