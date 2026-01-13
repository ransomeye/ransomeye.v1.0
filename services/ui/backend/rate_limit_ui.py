#!/usr/bin/env python3
"""
RansomEye v1.0 UI Backend - Rate Limit UI Controls
AUTHORITATIVE: UI safety controls for rate limiting (NO ASSUMPTIONS)
Python 3.10+ only
"""

import os
import sys
from typing import Dict, Any, Optional
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
    _logger = setup_logging('ui-rate-limit')
except ImportError:
    _common_available = False
    _logger = None


class RateLimitUI:
    """
    UI safety controls for rate limiting.
    
    CRITICAL: UI must display remaining action quota, warnings, and incident freeze banner.
    No silent failures.
    """
    
    # NON-CONFIGURABLE DEFAULTS (matches RateLimiter)
    PER_USER_PER_MINUTE = 10
    PER_INCIDENT_TOTAL = 25
    PER_HOST_PER_10_MINUTES = 5
    EMERGENCY_OVERRIDE_PER_INCIDENT = 2
    
    def __init__(self, db_conn_params: Dict[str, Any]):
        """
        Initialize rate limit UI.
        
        Args:
            db_conn_params: Database connection parameters
        """
        self.db_conn_params = db_conn_params
    
    def get_user_quota(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get remaining action quota for user.
        
        Args:
            user_id: User identifier
        
        Returns:
            Dictionary with quota information
        """
        from datetime import datetime, timezone, timedelta
        
        conn = create_write_connection(**self.db_conn_params, isolation_level=IsolationLevel.READ_COMMITTED, logger=_logger)
        try:
            now = datetime.now(timezone.utc)
            one_minute_ago = now - timedelta(minutes=1)
            
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM response_actions
                    WHERE executed_by = %s
                    AND executed_at >= %s
                """, (user_id, one_minute_ago))
                user_count = cur.fetchone()[0]
            
            remaining = max(0, self.PER_USER_PER_MINUTE - user_count)
            
            return {
                'limit': self.PER_USER_PER_MINUTE,
                'used': user_count,
                'remaining': remaining,
                'window': '1 minute'
            }
        finally:
            conn.close()
    
    def get_incident_quota(
        self,
        incident_id: str,
        is_emergency: bool = False
    ) -> Dict[str, Any]:
        """
        Get remaining action quota for incident.
        
        Args:
            incident_id: Incident identifier
            is_emergency: Whether this is an emergency override
        
        Returns:
            Dictionary with quota information
        """
        conn = create_write_connection(**self.db_conn_params, isolation_level=IsolationLevel.READ_COMMITTED, logger=_logger)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM response_actions
                    WHERE incident_id = %s
                """, (incident_id,))
                incident_count = cur.fetchone()[0]
            
            if is_emergency:
                limit = self.EMERGENCY_OVERRIDE_PER_INCIDENT
            else:
                limit = self.PER_INCIDENT_TOTAL
            
            remaining = max(0, limit - incident_count)
            
            return {
                'limit': limit,
                'used': incident_count,
                'remaining': remaining,
                'window': 'total' if not is_emergency else 'emergency total'
            }
        finally:
            conn.close()
    
    def get_host_quota(
        self,
        machine_id: str
    ) -> Dict[str, Any]:
        """
        Get remaining action quota for host.
        
        Args:
            machine_id: Machine identifier
        
        Returns:
            Dictionary with quota information
        """
        from datetime import datetime, timezone, timedelta
        
        conn = create_write_connection(**self.db_conn_params, isolation_level=IsolationLevel.READ_COMMITTED, logger=_logger)
        try:
            now = datetime.now(timezone.utc)
            ten_minutes_ago = now - timedelta(minutes=10)
            
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM response_actions
                    WHERE machine_id = %s
                    AND executed_at >= %s
                """, (machine_id, ten_minutes_ago))
                host_count = cur.fetchone()[0]
            
            remaining = max(0, self.PER_HOST_PER_10_MINUTES - host_count)
            
            return {
                'limit': self.PER_HOST_PER_10_MINUTES,
                'used': host_count,
                'remaining': remaining,
                'window': '10 minutes'
            }
        finally:
            conn.close()
