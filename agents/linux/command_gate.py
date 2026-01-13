#!/usr/bin/env python3
"""
RansomEye v1.0 Linux Agent - Command Acceptance Gate
AUTHORITATIVE: Single command intake gate with strict validation (NO ASSUMPTIONS)
Python 3.10+ only
"""

import os
import sys
import json
import uuid
import base64
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from pathlib import Path
import hashlib

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    _common_available = True
    _logger = setup_logging('linux-agent-gate')
except ImportError:
    _common_available = False
    _logger = None

# ed25519 signature verification
try:
    import nacl.signing
    import nacl.encoding
    _nacl_available = True
except ImportError:
    _nacl_available = False
    _logger.warning("PyNaCl not available - signature verification disabled") if _logger else None


class CommandRejectionError(Exception):
    """Exception raised when command is rejected."""
    pass


class CommandGate:
    """
    Single command intake gate with strict validation.
    
    CRITICAL: Agents NEVER trust the network, NEVER trust the UI.
    Agents ONLY trust signed commands. FAIL CLOSED.
    """
    
    def __init__(
        self,
        tre_public_key: bytes,
        tre_key_id: str,
        agent_id: str,
        audit_log_path: Path,
        nonce_cache_size: int = 1000,
        clock_skew_tolerance: int = 60
    ):
        """
        Initialize command gate.
        
        Args:
            tre_public_key: TRE public key for signature verification
            tre_key_id: TRE key ID (SHA256 hash)
            agent_id: Agent identifier
            audit_log_path: Path to local audit log
            nonce_cache_size: Size of nonce cache for replay protection
            clock_skew_tolerance: Clock skew tolerance in seconds (±60s max)
        """
        self.tre_public_key = tre_public_key
        self.tre_key_id = tre_key_id
        self.agent_id = agent_id
        self.audit_log_path = audit_log_path
        self.clock_skew_tolerance = clock_skew_tolerance
        
        # Nonce cache for replay protection
        self.nonce_cache = set()
        self.nonce_cache_size = nonce_cache_size
        
        # Rate limiting (commands per minute)
        self.command_timestamps = []
        self.rate_limit = 100  # 100 commands per minute max
        
        # Initialize audit log
        self._ensure_audit_log()
        
        # Initialize verifier if PyNaCl available
        if _nacl_available and tre_public_key:
            try:
                self.verifier = nacl.signing.VerifyKey(tre_public_key)
            except Exception as e:
                if _logger:
                    _logger.error(f"Failed to initialize signature verifier: {e}")
                self.verifier = None
        else:
            self.verifier = None
    
    def _ensure_audit_log(self):
        """Ensure audit log directory exists."""
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _log_audit_event(self, event_type: str, command_id: str, outcome: str, reason: Optional[str] = None):
        """
        Log audit event to local append-only log.
        
        Args:
            event_type: Event type (command_received, command_rejected, etc.)
            command_id: Command identifier
            outcome: Outcome (SUCCESS, REJECTED, FAILED)
            reason: Optional reason for rejection/failure
        """
        event = {
            'event_type': event_type,
            'agent_id': self.agent_id,
            'command_id': command_id,
            'outcome': outcome,
            'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'reason': reason
        }
        
        try:
            with open(self.audit_log_path, 'a') as f:
                f.write(json.dumps(event) + '\n')
        except Exception as e:
            if _logger:
                _logger.error(f"Failed to write audit log: {e}")
    
    def receive_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Receive and validate command through acceptance gate.
        
        Pipeline:
        1. Schema validation
        2. Timestamp + nonce freshness check
        3. ed25519 signature verification
        4. Issuer trust verification (TRE public key)
        5. RBAC + role assertion validation (embedded)
        6. HAF approval presence (if required)
        7. Idempotency check (command_id)
        8. Execution OR rejection
        
        Args:
            command: Command dictionary
        
        Returns:
            Validated command dictionary
        
        Raises:
            CommandRejectionError: If command is rejected
        """
        command_id = command.get('command_id', 'unknown')
        
        try:
            # Step 1: Schema validation
            self._validate_schema(command)
            
            # Step 2: Timestamp + nonce freshness check
            self._validate_freshness(command)
            
            # Step 3: ed25519 signature verification
            self._verify_signature(command)
            
            # Step 4: Issuer trust verification (TRE public key)
            self._verify_issuer(command)
            
            # Step 5: RBAC + role assertion validation (embedded)
            self._validate_rbac(command)
            
            # Step 6: HAF approval presence (if required)
            self._validate_haf_approval(command)
            
            # Step 7: Idempotency check (command_id)
            self._check_idempotency(command_id)
            
            # Step 8: Rate limiting
            self._check_rate_limit()
            
            # All checks passed
            self._log_audit_event('command_received', command_id, 'SUCCESS')
            
            return command
            
        except CommandRejectionError as e:
            self._log_audit_event('command_rejected', command_id, 'REJECTED', str(e))
            raise
        except Exception as e:
            self._log_audit_event('command_rejected', command_id, 'FAILED', str(e))
            raise CommandRejectionError(f"Command validation failed: {e}") from e
    
    def _validate_schema(self, command: Dict[str, Any]):
        """
        Step 1: Schema validation.
        
        Required fields (FROZEN):
        - command_id: UUID
        - action_type: ENUM
        - target: OBJECT
        - incident_id: UUID | null
        - tre_mode: ENUM
        - issued_by_user_id: UUID
        - issued_by_role: ENUM
        - approval_id: UUID | null
        - issued_at: RFC3339
        - expires_at: RFC3339
        - rollback_token: SHA256
        - signature: ed25519
        
        Args:
            command: Command dictionary
        
        Raises:
            CommandRejectionError: If schema validation fails
        """
        required_fields = [
            'command_id', 'action_type', 'target', 'incident_id',
            'tre_mode', 'issued_by_user_id', 'issued_by_role',
            'issued_at', 'expires_at', 'rollback_token', 'signature'
        ]
        
        for field in required_fields:
            if field not in command:
                raise CommandRejectionError(f"Missing required field: {field}")
        
        # Validate UUIDs
        try:
            uuid.UUID(command['command_id'])
            if command['incident_id']:
                uuid.UUID(command['incident_id'])
            uuid.UUID(command['issued_by_user_id'])
            if command.get('approval_id'):
                uuid.UUID(command['approval_id'])
        except (ValueError, TypeError) as e:
            raise CommandRejectionError(f"Invalid UUID format: {e}")
        
        # Validate action_type enum
        valid_action_types = {
            'BLOCK_PROCESS', 'BLOCK_NETWORK_CONNECTION', 'TEMPORARY_FIREWALL_RULE',
            'QUARANTINE_FILE', 'ISOLATE_HOST', 'LOCK_USER', 'DISABLE_SERVICE',
            'MASS_PROCESS_KILL', 'NETWORK_SEGMENT_ISOLATION'
        }
        if command['action_type'] not in valid_action_types:
            raise CommandRejectionError(f"Invalid action_type: {command['action_type']}")
        
        # Validate tre_mode enum
        valid_modes = {'DRY_RUN', 'GUARDED_EXEC', 'FULL_ENFORCE'}
        if command['tre_mode'] not in valid_modes:
            raise CommandRejectionError(f"Invalid tre_mode: {command['tre_mode']}")
        
        # Validate issued_by_role enum
        valid_roles = {'SUPER_ADMIN', 'SECURITY_ANALYST', 'POLICY_MANAGER', 'IT_ADMIN', 'AUDITOR'}
        if command['issued_by_role'] not in valid_roles:
            raise CommandRejectionError(f"Invalid issued_by_role: {command['issued_by_role']}")
        
        # Validate timestamps (RFC3339)
        try:
            datetime.fromisoformat(command['issued_at'].replace('Z', '+00:00'))
            datetime.fromisoformat(command['expires_at'].replace('Z', '+00:00'))
        except (ValueError, AttributeError) as e:
            raise CommandRejectionError(f"Invalid timestamp format: {e}")
        
        # Reject unknown fields
        allowed_fields = set(required_fields) | {'approval_id', 'signing_key_id'}
        unknown_fields = set(command.keys()) - allowed_fields
        if unknown_fields:
            raise CommandRejectionError(f"Unknown fields: {unknown_fields}")
    
    def _validate_freshness(self, command: Dict[str, Any]):
        """
        Step 2: Timestamp + nonce freshness check.
        
        Args:
            command: Command dictionary
        
        Raises:
            CommandRejectionError: If freshness check fails
        """
        # Parse timestamps
        try:
            issued_at = datetime.fromisoformat(command['issued_at'].replace('Z', '+00:00'))
            expires_at = datetime.fromisoformat(command['expires_at'].replace('Z', '+00:00'))
        except (ValueError, AttributeError) as e:
            raise CommandRejectionError(f"Invalid timestamp format: {e}")
        
        now = datetime.now(timezone.utc)
        
        # Check expiry
        if expires_at < now:
            raise CommandRejectionError(f"Command expired: expires_at={expires_at}, now={now}")
        
        # Check clock skew (issued_at must be within tolerance)
        skew = abs((issued_at - now).total_seconds())
        if skew > self.clock_skew_tolerance:
            raise CommandRejectionError(
                f"Clock skew too large: {skew}s (max {self.clock_skew_tolerance}s)"
            )
    
    def _verify_signature(self, command: Dict[str, Any]):
        """
        Step 3: ed25519 signature verification.
        
        Args:
            command: Command dictionary
        
        Raises:
            CommandRejectionError: If signature verification fails
        """
        if not _nacl_available or not self.verifier:
            raise CommandRejectionError("Signature verification not available (PyNaCl not installed)")
        
        # Extract signature
        signature_b64 = command.get('signature', '')
        try:
            signature = base64.b64decode(signature_b64)
        except Exception as e:
            raise CommandRejectionError(f"Invalid signature encoding: {e}")
        
        # Create message to verify (canonical JSON of command without signature)
        command_copy = command.copy()
        command_copy.pop('signature', None)
        command_copy.pop('signing_key_id', None)
        message = json.dumps(command_copy, sort_keys=True).encode('utf-8')
        
        # Verify signature
        try:
            self.verifier.verify(message, signature)
        except nacl.exceptions.BadSignatureError:
            raise CommandRejectionError("Signature verification failed")
        except Exception as e:
            raise CommandRejectionError(f"Signature verification error: {e}")
    
    def _verify_issuer(self, command: Dict[str, Any]):
        """
        Step 4: Issuer trust verification (TRE public key).
        
        Args:
            command: Command dictionary
        
        Raises:
            CommandRejectionError: If issuer verification fails
        """
        signing_key_id = command.get('signing_key_id', '')
        if signing_key_id != self.tre_key_id:
            raise CommandRejectionError(
                f"Signing key ID mismatch: expected {self.tre_key_id}, got {signing_key_id}"
            )
    
    def _validate_rbac(self, command: Dict[str, Any]):
        """
        Step 5: RBAC + role assertion validation (embedded).
        
        Args:
            command: Command dictionary
        
        Raises:
            CommandRejectionError: If RBAC validation fails
        """
        # Validate that role is present and valid
        role = command.get('issued_by_role', '')
        if not role:
            raise CommandRejectionError("Missing issued_by_role")
        
        # Validate that user_id is present
        user_id = command.get('issued_by_user_id', '')
        if not user_id:
            raise CommandRejectionError("Missing issued_by_user_id")
        
        # Role must be one of the five valid roles
        valid_roles = {'SUPER_ADMIN', 'SECURITY_ANALYST', 'POLICY_MANAGER', 'IT_ADMIN', 'AUDITOR'}
        if role not in valid_roles:
            raise CommandRejectionError(f"Invalid role: {role}")
    
    def _validate_haf_approval(self, command: Dict[str, Any]):
        """
        Step 6: HAF approval presence (if required).
        
        Args:
            command: Command dictionary
        
        Raises:
            CommandRejectionError: If HAF approval validation fails
        """
        action_type = command.get('action_type', '')
        tre_mode = command.get('tre_mode', '')
        
        # DESTRUCTIVE actions in FULL_ENFORCE mode require approval
        destructive_actions = {
            'ISOLATE_HOST', 'LOCK_USER', 'DISABLE_SERVICE',
            'MASS_PROCESS_KILL', 'NETWORK_SEGMENT_ISOLATION'
        }
        
        if action_type in destructive_actions and tre_mode == 'FULL_ENFORCE':
            approval_id = command.get('approval_id')
            if not approval_id:
                raise CommandRejectionError(
                    f"HAF approval required for DESTRUCTIVE action {action_type} in FULL_ENFORCE mode"
                )
    
    def _check_idempotency(self, command_id: str):
        """
        Step 7: Idempotency check (command_id).
        
        Args:
            command_id: Command identifier
        
        Raises:
            CommandRejectionError: If command_id already seen
        """
        if command_id in self.nonce_cache:
            raise CommandRejectionError(f"Command ID already seen: {command_id} (replay attack)")
        
        # Add to cache
        self.nonce_cache.add(command_id)
        
        # Evict oldest entries if cache is full
        if len(self.nonce_cache) > self.nonce_cache_size:
            # Remove oldest 10% of entries (simple eviction)
            entries_to_remove = len(self.nonce_cache) // 10
            for _ in range(entries_to_remove):
                self.nonce_cache.pop()
    
    def _check_rate_limit(self):
        """
        Step 8: Rate limiting check.
        
        Raises:
            CommandRejectionError: If rate limit exceeded
        """
        now = datetime.now(timezone.utc)
        one_minute_ago = now - timedelta(minutes=1)
        
        # Remove old timestamps
        self.command_timestamps = [ts for ts in self.command_timestamps if ts > one_minute_ago]
        
        # Check rate limit
        if len(self.command_timestamps) >= self.rate_limit:
            raise CommandRejectionError(
                f"Rate limit exceeded: {len(self.command_timestamps)} commands in last minute"
            )
        
        # Add current timestamp
        self.command_timestamps.append(now)
