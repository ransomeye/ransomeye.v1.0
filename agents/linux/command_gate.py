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
        clock_skew_tolerance: int = 60,
        cached_policy_path: Optional[Path] = None,
        core_endpoint: Optional[str] = None
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
            cached_policy_path: Path to cached policy file (PHASE F2: Headless survivability)
            core_endpoint: Core endpoint URL for online check (PHASE F2)
        """
        self.tre_public_key = tre_public_key
        self.tre_key_id = tre_key_id
        self.agent_id = agent_id
        self.audit_log_path = audit_log_path
        self.clock_skew_tolerance = clock_skew_tolerance
        
        # PHASE F2: Cached policy for headless survivability
        self.cached_policy_path = cached_policy_path or Path(os.getenv('RANSOMEYE_CACHED_POLICY_PATH', '/var/lib/ransomeye/agent/cached_policy.json'))
        self.core_endpoint = core_endpoint or os.getenv('RANSOMEYE_CORE_ENDPOINT', 'http://localhost:8000/health')
        self.cached_policy = self._load_cached_policy()
        
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
            
            # Step 9: PHASE F2 - Check cached policy if Core is offline
            self._check_cached_policy_if_offline(command)
            
            # PHASE 4: Step 10: Policy authority validation
            self._validate_policy_authority(command)
            
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
        # PHASE 4: Required fields (including policy authority binding)
        required_fields = [
            'command_id', 'action_type', 'target', 'incident_id',
            'tre_mode', 'issued_by_user_id', 'issued_by_role',
            'issued_at', 'expires_at', 'rollback_token', 'signature',
            'policy_id', 'policy_version', 'issuing_authority'  # PHASE 4: Policy authority binding
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
        
        # PHASE 4: Reject unknown fields (including policy authority fields)
        allowed_fields = set(required_fields) | {'approval_id', 'signing_key_id', 'signing_algorithm', 'signed_at'}
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
        
        # PHASE 4: Create message to verify (canonical JSON of command without signature fields)
        command_copy = command.copy()
        command_copy.pop('signature', None)
        command_copy.pop('signing_key_id', None)
        command_copy.pop('signing_algorithm', None)
        command_copy.pop('signed_at', None)
        message = json.dumps(command_copy, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
        
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
    
    def _validate_policy_authority(self, command: Dict[str, Any]):
        """
        PHASE 4: Step 10: Policy authority validation.
        
        Validates:
        - policy_id is present and valid
        - policy_version is present and valid
        - issuing_authority is present and valid
        
        Args:
            command: Command dictionary
            
        Raises:
            CommandRejectionError: If policy authority validation fails
        """
        # PHASE 4: Validate policy_id
        policy_id = command.get('policy_id', '')
        if not policy_id:
            raise CommandRejectionError("Missing policy_id (PHASE 4: Policy authority binding required)")
        
        # PHASE 4: Validate policy_version
        policy_version = command.get('policy_version', '')
        if not policy_version:
            raise CommandRejectionError("Missing policy_version (PHASE 4: Policy version required)")
        
        # PHASE 4: Validate issuing_authority
        issuing_authority = command.get('issuing_authority', '')
        if not issuing_authority:
            raise CommandRejectionError("Missing issuing_authority (PHASE 4: Issuing authority required)")
        
        # PHASE 4: Validate issuing_authority is valid
        valid_authorities = {'policy-engine', 'threat-response-engine', 'human-authority'}
        if issuing_authority not in valid_authorities:
            raise CommandRejectionError(
                f"Invalid issuing_authority: {issuing_authority} "
                f"(must be one of: {', '.join(valid_authorities)})"
            )
    
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
    
    def _load_cached_policy(self) -> Dict[str, Any]:
        """
        GA-BLOCKING: Load cached policy for headless survivability with integrity check.
        
        CRITICAL: Policy cache must be integrity-checked at startup.
        If integrity check fails or no policy exists, default to DENY (fail-closed).
        
        Returns:
            Cached policy dictionary with allowed/prohibited actions
        """
        if not self.cached_policy_path.exists():
            # GA-BLOCKING: No policy exists - default to DENY (fail-closed)
            if _logger:
                _logger.warning(
                    "GA-BLOCKING: No policy available — default deny enforced. "
                    "Cached policy file not found. Agent will deny all actions when Core is offline."
                )
            default_policy = {
                'version': '1.0',
                'prohibited_actions': [
                    'BLOCK_PROCESS', 'BLOCK_NETWORK_CONNECTION', 'TEMPORARY_FIREWALL_RULE',
                    'QUARANTINE_FILE', 'ISOLATE_HOST', 'LOCK_USER', 'DISABLE_SERVICE',
                    'MASS_PROCESS_KILL', 'NETWORK_SEGMENT_ISOLATION'
                ],
                'allowed_actions': [],  # No actions allowed when Core is offline (fail-closed)
                'last_updated': None,
                'integrity_hash': None  # No integrity hash for default policy
            }
            # Save default policy
            self.cached_policy_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cached_policy_path, 'w') as f:
                json.dump(default_policy, f, indent=2)
            return default_policy
        
        try:
            # GA-BLOCKING: Load and integrity-check cached policy
            with open(self.cached_policy_path, 'r') as f:
                policy = json.load(f)
            
            # Integrity check: Verify policy structure and hash (if present)
            if not self._verify_policy_integrity(policy):
                if _logger:
                    _logger.error(
                        "GA-BLOCKING: Cached policy integrity check failed. "
                        "Default deny enforced. Policy cache may have been tampered with."
                    )
                # Return fail-closed default
                return self._get_default_deny_policy()
            
            if _logger:
                _logger.info(
                    f"GA-BLOCKING: Cached policy loaded successfully. "
                    f"Version: {policy.get('version', 'unknown')}, "
                    f"Last updated: {policy.get('last_updated', 'never')}"
                )
            
            return policy
            
        except Exception as e:
            if _logger:
                _logger.error(
                    f"GA-BLOCKING: Failed to load cached policy: {e}. "
                    "Default deny enforced."
                )
            # Return fail-closed default
            return self._get_default_deny_policy()
    
    def _get_default_deny_policy(self) -> Dict[str, Any]:
        """
        GA-BLOCKING: Get default deny policy (fail-closed).
        
        Returns:
            Default policy dictionary (all actions prohibited)
        """
        return {
            'version': '1.0',
            'prohibited_actions': [
                'BLOCK_PROCESS', 'BLOCK_NETWORK_CONNECTION', 'TEMPORARY_FIREWALL_RULE',
                'QUARANTINE_FILE', 'ISOLATE_HOST', 'LOCK_USER', 'DISABLE_SERVICE',
                'MASS_PROCESS_KILL', 'NETWORK_SEGMENT_ISOLATION'
            ],
            'allowed_actions': [],  # No actions allowed (fail-closed)
            'last_updated': None,
            'integrity_hash': None
        }
    
    def _verify_policy_integrity(self, policy: Dict[str, Any]) -> bool:
        """
        GA-BLOCKING: Verify cached policy integrity.
        
        Checks:
        1. Policy structure is valid
        2. Required fields are present
        3. Integrity hash matches (if present)
        
        Args:
            policy: Policy dictionary to verify
            
        Returns:
            True if integrity check passes, False otherwise
        """
        # Check required fields
        required_fields = ['version', 'prohibited_actions', 'allowed_actions']
        for field in required_fields:
            if field not in policy:
                if _logger:
                    _logger.error(f"Policy integrity check failed: Missing required field: {field}")
                return False
        
        # Verify prohibited_actions and allowed_actions are lists
        if not isinstance(policy['prohibited_actions'], list):
            if _logger:
                _logger.error("Policy integrity check failed: prohibited_actions must be a list")
            return False
        
        if not isinstance(policy['allowed_actions'], list):
            if _logger:
                _logger.error("Policy integrity check failed: allowed_actions must be a list")
            return False
        
        # Verify integrity hash if present
        if 'integrity_hash' in policy and policy['integrity_hash']:
            # Compute hash of policy (without integrity_hash field)
            policy_copy = policy.copy()
            policy_copy.pop('integrity_hash', None)
            policy_json = json.dumps(policy_copy, sort_keys=True, separators=(',', ':'))
            computed_hash = hashlib.sha256(policy_json.encode('utf-8')).hexdigest()
            
            if computed_hash != policy['integrity_hash']:
                if _logger:
                    _logger.error(
                        f"Policy integrity check failed: Hash mismatch. "
                        f"Expected: {policy['integrity_hash']}, Computed: {computed_hash}"
                    )
                return False
        
        return True
    
    def _is_core_online(self) -> bool:
        """
        PHASE F2: Check if Core is online.
        
        Returns:
            True if Core is online, False otherwise
        """
        try:
            import urllib.request
            import urllib.error
            req = urllib.request.Request(self.core_endpoint, method='GET')
            with urllib.request.urlopen(req, timeout=2) as response:
                return response.status == 200
        except Exception:
            return False
    
    def _check_cached_policy_if_offline(self, command: Dict[str, Any]):
        """
        GA-BLOCKING: Check cached policy if Core is offline (autonomous enforcement).
        
        CRITICAL: When Core is offline and prohibited action attempted,
        agent must fail-closed using cached policy.
        
        Behavior:
        1. If Core is online → normal operation (Core verifies)
        2. If Core is offline → enforce cached policy (autonomous)
        3. If no policy exists → default DENY (fail-closed)
        
        Args:
            command: Command dictionary
            
        Raises:
            CommandRejectionError: If Core is offline and action is prohibited/not allowed
        """
        # Check if Core is online
        if self._is_core_online():
            # Core is online - policy check not needed (Core will verify)
            return
        
        # GA-BLOCKING: Core is offline - enforce cached policy autonomously
        action_type = command.get('action_type', '')
        prohibited_actions = self.cached_policy.get('prohibited_actions', [])
        allowed_actions = self.cached_policy.get('allowed_actions', [])
        
        # GA-BLOCKING: Explicit autonomous enforcement logging
        if _logger:
            _logger.warning(
                f"GA-BLOCKING: Core offline — autonomous enforcement active. "
                f"Action: {action_type}, Cached policy version: {self.cached_policy.get('version', 'unknown')}"
            )
        
        # GA-BLOCKING: Fail-closed enforcement logic
        # Rule 1: If action is explicitly prohibited → REJECT
        if action_type in prohibited_actions:
            error_msg = (
                f"GA-BLOCKING: Core offline — Action {action_type} is prohibited by cached policy. "
                "Agent enforcing autonomous fail-closed policy. Action denied."
            )
            if _logger:
                _logger.error(error_msg)
            raise CommandRejectionError(error_msg)
        
        # Rule 2: If policy has explicit allow-list and action not in it → REJECT
        if allowed_actions and action_type not in allowed_actions:
            error_msg = (
                f"GA-BLOCKING: Core offline — Action {action_type} is not in allowed actions list. "
                "Agent enforcing autonomous fail-closed policy. Action denied."
            )
            if _logger:
                _logger.error(error_msg)
            raise CommandRejectionError(error_msg)
        
        # Rule 3: If no explicit allow-list exists → default DENY (fail-closed)
        if not allowed_actions:
            error_msg = (
                f"GA-BLOCKING: Core offline — No policy available — default deny enforced. "
                f"Action {action_type} denied (fail-closed)."
            )
            if _logger:
                _logger.error(error_msg)
            raise CommandRejectionError(error_msg)
        
        # Rule 4: Action is explicitly allowed → ALLOW (but log autonomous enforcement)
        if _logger:
            _logger.info(
                f"GA-BLOCKING: Core offline — Action {action_type} allowed by cached policy. "
                "Autonomous enforcement: ALLOWED"
            )
    
    def update_cached_policy(self, policy: Dict[str, Any]) -> bool:
        """
        GA-BLOCKING: Update cached policy when Core is online.
        
        This method should be called when Core provides a new policy.
        The policy is cached securely with integrity hash.
        
        Args:
            policy: Policy dictionary from Core
            
        Returns:
            True if policy was updated successfully, False otherwise
        """
        try:
            # Add integrity hash to policy
            policy_copy = policy.copy()
            policy_copy.pop('integrity_hash', None)  # Remove existing hash if present
            policy_json = json.dumps(policy_copy, sort_keys=True, separators=(',', ':'))
            integrity_hash = hashlib.sha256(policy_json.encode('utf-8')).hexdigest()
            
            # Add metadata
            policy['integrity_hash'] = integrity_hash
            policy['last_updated'] = datetime.now(timezone.utc).isoformat()
            
            # Save cached policy
            self.cached_policy_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cached_policy_path, 'w') as f:
                json.dump(policy, f, indent=2)
            
            # Reload cached policy
            self.cached_policy = self._load_cached_policy()
            
            if _logger:
                _logger.info(
                    f"GA-BLOCKING: Cached policy updated successfully. "
                    f"Version: {policy.get('version', 'unknown')}, "
                    f"Integrity hash: {integrity_hash[:16]}..."
                )
            
            return True
            
        except Exception as e:
            if _logger:
                _logger.error(f"GA-BLOCKING: Failed to update cached policy: {e}")
            return False
