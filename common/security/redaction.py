#!/usr/bin/env python3
"""
RansomEye v1.0 Common Security - Log Redaction
AUTHORITATIVE: Prevent secret leakage in logs and exceptions
"""

import re
import sys
from typing import Any, Dict, List, Union


# Patterns that indicate secrets (case-insensitive)
SECRET_PATTERNS = [
    r'password',
    r'passwd',
    r'pwd',
    r'secret',
    r'key',
    r'token',
    r'auth',
    r'credential',
    r'api[_-]?key',
    r'access[_-]?token',
    r'bearer[_-]?token',
    r'authorization',
    r'signing[_-]?key',
    r'private[_-]?key',
    r'hmac[_-]?key',
]


REDACTION_STRING = "[REDACTED]"
MAX_VALUE_LENGTH_TO_CHECK = 1000  # Don't check very long strings for secrets


def _contains_secret_pattern(text: str) -> bool:
    """
    Check if text contains patterns that suggest secrets.
    
    Args:
        text: Text to check
        
    Returns:
        True if text contains secret patterns, False otherwise
    """
    text_lower = text.lower()
    for pattern in SECRET_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def _is_likely_secret(value: Any) -> bool:
    """
    Heuristic to detect if a value is likely a secret.
    
    Security: Only flags values that look like actual secrets (random strings, not normal text).
    
    Args:
        value: Value to check
        
    Returns:
        True if value looks like a secret, False otherwise
    """
    if not isinstance(value, str):
        return False
    
    # Skip very long strings (unlikely to be secrets in logs)
    if len(value) > MAX_VALUE_LENGTH_TO_CHECK:
        return False
    
    # Skip normal sentences (contain spaces, common words) - not secrets
    if ' ' in value or '\n' in value or '\t' in value:
        # Normal text with spaces is not a secret
        # Only check if it contains explicit secret patterns (password=, key=, etc.)
        return False
    
    # Check for common secret patterns (must be explicit pattern, not just containing word)
    # Only flag if pattern suggests a secret value (e.g., "password=xyz", not just "password")
    if _contains_secret_pattern(value):
        # Only flag if it looks like a key-value pair or assignment (e.g., "password=secret123")
        if '=' in value or ':' in value or value.strip().startswith(('password', 'key', 'token', 'secret')):
            return True
    
    # Check for high entropy (likely random/secret strings)
    # Secrets typically have high entropy (random characters, no spaces, no common words)
    if len(value) >= 16 and ' ' not in value:
        # Check if string looks random (not all same character, mixed case, numbers, symbols)
        # Must have high entropy AND no spaces (random strings don't have spaces)
        if len(set(value)) > len(value) * 0.6 and not value.isalnum() and not value.isalpha():
            return True
    
    return False


def redact_secrets(data: Any) -> Any:
    """
    Recursively redact secrets from data structures.
    
    Security: Prevents secrets from appearing in logs or exceptions.
    Terminates Core immediately if a secret is detected in a log attempt.
    
    Args:
        data: Data structure to redact (dict, list, str, etc.)
        
    Returns:
        Redacted data structure
    """
    if isinstance(data, dict):
        redacted = {}
        for key, value in data.items():
            # Check key name for secret patterns
            if _contains_secret_pattern(str(key)):
                # Redact the value if key suggests it's a secret
                redacted[key] = REDACTION_STRING
            else:
                # Recursively redact value
                redacted[key] = redact_secrets(value)
        return redacted
    elif isinstance(data, list):
        return [redact_secrets(item) for item in data]
    elif isinstance(data, str):
        # Check if string value is a secret
        if _is_likely_secret(data):
            return REDACTION_STRING
        return data
    else:
        # For other types, convert to string and check
        if isinstance(data, (int, float, bool, type(None))):
            return data
        str_repr = str(data)
        if _is_likely_secret(str_repr):
            return REDACTION_STRING
        return data


def sanitize_string_for_logging(text: str) -> str:
    """
    Sanitize a string for safe logging.
    
    Security: Redacts secrets from strings before logging.
    
    Args:
        text: String to sanitize
        
    Returns:
        Sanitized string with secrets redacted
    """
    if not isinstance(text, str):
        text = str(text)
    
    # Check for secrets in the string
    if _is_likely_secret(text):
        return REDACTION_STRING
    
    # Check for secret patterns in the string
    if _contains_secret_pattern(text):
        # Try to redact potential secrets while preserving structure
        # Simple heuristic: redact quoted values after secret keywords
        redacted = re.sub(
            r'(["\']?)(password|passwd|pwd|secret|key|token|auth|credential|api[_-]?key|access[_-]?token|bearer[_-]?token|authorization|signing[_-]?key|private[_-]?key|hmac[_-]?key)\s*[:=]\s*["\']?([^"\'}\s,]+)["\']?',
            r'\1\2 = ' + REDACTION_STRING,
            text,
            flags=re.IGNORECASE
        )
        return redacted
    
    return text


def validate_secret_not_logged(value: Any, context: str = "") -> None:
    """
    Validate that a value is not being logged (security check).
    
    Security: Terminates Core immediately if a secret is detected in a log attempt.
    
    Args:
        value: Value being logged
        context: Context description for error message
        
    Raises:
        SystemExit: Terminates Core immediately if secret detected
    """
    if _is_likely_secret(value):
        error_msg = f"SECURITY VIOLATION: Attempt to log secret detected{': ' + context if context else ''}"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        sys.exit(4)  # FATAL_ERROR


def sanitize_exception(exception: Exception) -> str:
    """
    Sanitize exception message for safe logging.
    
    Security: Redacts secrets from exception messages.
    
    Args:
        exception: Exception to sanitize
        
    Returns:
        Sanitized exception message
    """
    message = str(exception)
    return sanitize_string_for_logging(message)


def get_redacted_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get redacted version of configuration for logging.
    
    Security: Redacts all secret values from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Redacted configuration dictionary
    """
    return redact_secrets(config)
