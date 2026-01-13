#!/usr/bin/env python3
"""
RansomEye v1.0 Threat Response Engine - Rate Limiter
AUTHORITATIVE: Hard rate limits for response actions (NON-CONFIGURABLE, SERVER-SIDE)
Python 3.10+ only
"""

import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    from common.db.safety import create_write_connection, IsolationLevel
    _common_available = True
    _logger = setup_logging('tre-rate-limiter')
except ImportError:
    _common_available = False
    _logger = None

# Audit ledger integration
try:
    _audit_ledger_path = os.path.join(_project_root, 'audit-ledger')
    if os.path.exists(_audit_ledger_path) and _audit_ledger_path not in sys.path:
        sys.path.insert(0, _audit_ledger_path)
    from api import AuditLedger
    _audit_ledger_available = True
except ImportError:
    _audit_ledger_available = False
    AuditLedger = None


class RateLimitError(Exception):
    """Exception raised when rate limit is exceeded."""
    pass


class RateLimiter:
    """
    Hard rate limits for response actions.
    
    CRITICAL: Limits are NON-CONFIGURABLE defaults, enforced server-side.
    Limits are evaluated BEFORE HAF. Fail-closed with explicit error.
    """
    
    # NON-CONFIGURABLE DEFAULTS
    PER_USER_PER_MINUTE = 10
    PER_INCIDENT_TOTAL = 25
    PER_HOST_PER_10_MINUTES = 5
    EMERGENCY_OVERRIDE_PER_INCIDENT = 2
    
    def __init__(
        self,
        db_conn_params: Dict[str, Any],
        ledger: Optional[AuditLedger] = None
    ):
        """
        Initialize rate limiter.
        
        Args:
            db_conn_params: Database connection parameters
            ledger: Optional audit ledger instance
        """
        self.db_conn_params = db_conn_params
        self.ledger = ledger
    
    def check_rate_limit(
        self,
        user_id: str,
        incident_id: Optional[str],
        machine_id: Optional[str],
        is_emergency: bool = False
    ) -> bool:
        """
        Check rate limits for action execution.
        
        Limits checked:
        - Per user: 10 actions / minute
        - Per incident: 25 actions total
        - Per host: 5 actions / 10 minutes
        - Emergency override: 2 actions / incident
        
        Args:
            user_id: User identifier
            incident_id: Incident identifier
            machine_id: Machine identifier
            is_emergency: Whether this is an emergency override
        
        Returns:
            True if within limits
        
        Raises:
            RateLimitError: If rate limit exceeded
        """
        conn = create_write_connection(**self.db_conn_params, isolation_level=IsolationLevel.READ_COMMITTED, logger=_logger)
        try:
            now = datetime.now(timezone.utc)
            
            # Check per-user per-minute limit
            one_minute_ago = now - timedelta(minutes=1)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM response_actions
                    WHERE executed_by = %s
                    AND executed_at >= %s
                """, (user_id, one_minute_ago))
                user_count = cur.fetchone()[0]
                
                if user_count >= self.PER_USER_PER_MINUTE:
                    self._emit_rate_limit_event(
                        'ACTION_RATE_LIMIT_HIT',
                        user_id, incident_id, 'PER_USER_PER_MINUTE',
                        f"User {user_id} exceeded {self.PER_USER_PER_MINUTE} actions per minute"
                    )
                    raise RateLimitError(
                        f"Rate limit exceeded: {user_count} actions in last minute (max {self.PER_USER_PER_MINUTE})"
                    )
            
            # Check per-incident total limit
            if incident_id:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT COUNT(*) FROM response_actions
                        WHERE incident_id = %s
                    """, (incident_id,))
                    incident_count = cur.fetchone()[0]
                    
                    if is_emergency:
                        # Emergency override limit
                        if incident_count >= self.EMERGENCY_OVERRIDE_PER_INCIDENT:
                            self._emit_rate_limit_event(
                                'EMERGENCY_LIMIT_HIT',
                                user_id, incident_id, 'EMERGENCY_OVERRIDE_PER_INCIDENT',
                                f"Emergency override limit exceeded for incident {incident_id}"
                            )
                            raise RateLimitError(
                                f"Emergency override limit exceeded: {incident_count} emergency actions (max {self.EMERGENCY_OVERRIDE_PER_INCIDENT})"
                            )
                    else:
                        # Regular incident limit
                        if incident_count >= self.PER_INCIDENT_TOTAL:
                            self._emit_rate_limit_event(
                                'ACTION_RATE_LIMIT_HIT',
                                user_id, incident_id, 'PER_INCIDENT_TOTAL',
                                f"Incident {incident_id} exceeded {self.PER_INCIDENT_TOTAL} actions total"
                            )
                            raise RateLimitError(
                                f"Rate limit exceeded: {incident_count} actions for incident (max {self.PER_INCIDENT_TOTAL})"
                            )
            
            # Check per-host per-10-minutes limit
            if machine_id:
                ten_minutes_ago = now - timedelta(minutes=10)
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT COUNT(*) FROM response_actions
                        WHERE machine_id = %s
                        AND executed_at >= %s
                    """, (machine_id, ten_minutes_ago))
                    host_count = cur.fetchone()[0]
                    
                    if host_count >= self.PER_HOST_PER_10_MINUTES:
                        self._emit_rate_limit_event(
                            'ACTION_RATE_LIMIT_HIT',
                            user_id, incident_id, 'PER_HOST_PER_10_MINUTES',
                            f"Host {machine_id} exceeded {self.PER_HOST_PER_10_MINUTES} actions per 10 minutes"
                        )
                        raise RateLimitError(
                            f"Rate limit exceeded: {host_count} actions for host in last 10 minutes (max {self.PER_HOST_PER_10_MINUTES})"
                        )
            
            return True
            
        finally:
            conn.close()
    
    def _emit_rate_limit_event(
        self,
        event_type: str,
        user_id: str,
        incident_id: Optional[str],
        limit_type: str,
        reason: str
    ):
        """
        Emit rate limit audit event.
        
        Args:
            event_type: Event type (ACTION_RATE_LIMIT_HIT, EMERGENCY_LIMIT_HIT)
            user_id: User identifier
            incident_id: Incident identifier
            limit_type: Type of limit exceeded
            reason: Reason for limit hit
        """
        if self.ledger:
            self.ledger.append(
                component='threat-response-engine',
                component_instance_id=os.getenv('HOSTNAME', 'tre'),
                action_type=event_type.lower(),
                subject={'type': 'incident', 'id': incident_id or 'none'},
                actor={'type': 'user', 'identifier': user_id},
                payload={
                    'limit_type': limit_type,
                    'reason': reason,
                    'incident_id': incident_id
                }
            )
