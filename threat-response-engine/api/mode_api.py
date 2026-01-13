#!/usr/bin/env python3
"""
RansomEye v1.0 Threat Response Engine - Mode Management API
AUTHORITATIVE: API for managing TRE enforcement modes (SUPER_ADMIN only)
Python 3.10+ only
"""

import os
import sys
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone
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
    _logger = setup_logging('tre-mode-api')
except ImportError:
    _common_available = False
    _logger = None

# Add threat-response-engine to path
_threat_response_path = os.path.join(_project_root, 'threat-response-engine')
if os.path.exists(_threat_response_path) and _threat_response_path not in sys.path:
    sys.path.insert(0, _threat_response_path)

# Add rbac to path
_rbac_path = os.path.join(_project_root, 'rbac')
if os.path.exists(_rbac_path) and _rbac_path not in sys.path:
    sys.path.insert(0, _rbac_path)

from engine.enforcement_mode import TREMode
from rbac.integration.tre_integration import TREPermissionEnforcer
from rbac.engine.permission_checker import PermissionDeniedError
from db.mode_operations import get_current_mode, set_mode, get_mode_history

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


class ModeAPI:
    """
    API for managing TRE enforcement modes.
    
    CRITICAL: Only SUPER_ADMIN can change modes.
    All mode changes are logged to audit ledger.
    """
    
    def __init__(
        self,
        db_conn_params: Dict[str, Any],
        rbac_enforcer: TREPermissionEnforcer,
        ledger: Optional[AuditLedger] = None
    ):
        """
        Initialize mode API.
        
        Args:
            db_conn_params: Database connection parameters
            rbac_enforcer: RBAC permission enforcer
            ledger: Optional audit ledger instance
        """
        self.db_conn_params = db_conn_params
        self.rbac_enforcer = rbac_enforcer
        self.ledger = ledger
    
    def get_mode(self) -> Dict[str, Any]:
        """
        Get current TRE enforcement mode.
        
        Returns:
            Dictionary with current mode information
        """
        conn = create_write_connection(**self.db_conn_params, isolation_level=IsolationLevel.READ_COMMITTED, logger=_logger)
        try:
            mode = get_current_mode(conn)
            if mode:
                return {
                    'mode': mode.value,
                    'available_modes': [m.value for m in TREMode]
                }
            else:
                # Default to DRY_RUN
                return {
                    'mode': TREMode.DRY_RUN.value,
                    'available_modes': [m.value for m in TREMode],
                    'default': True
                }
        finally:
            conn.close()
    
    def set_mode(
        self,
        mode: TREMode,
        user_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Set TRE enforcement mode (SUPER_ADMIN only).
        
        Args:
            mode: New TRE mode
            user_id: User identifier (must be SUPER_ADMIN)
            reason: Optional reason for change
        
        Returns:
            Dictionary with mode change result
        
        Raises:
            PermissionDeniedError: If user is not SUPER_ADMIN
            ValueError: If mode is invalid
        """
        # Check RBAC permission (SUPER_ADMIN only)
        self.rbac_enforcer.check_admin_permission(user_id)
        
        # Validate mode
        if not isinstance(mode, TREMode):
            raise ValueError(f"Invalid mode: {mode}")
        
        # Get current mode
        conn = create_write_connection(**self.db_conn_params, isolation_level=IsolationLevel.READ_COMMITTED, logger=_logger)
        try:
            current_mode = get_current_mode(conn)
            
            # Emit audit ledger entry before change
            ledger_entry_id = str(uuid.uuid4())
            if self.ledger:
                ledger_entry = self.ledger.append(
                    component='threat-response-engine',
                    component_instance_id=os.getenv('HOSTNAME', 'tre'),
                    action_type='tre_mode_changed',
                    subject={'type': 'tre_mode', 'id': mode.value},
                    actor={'type': 'user', 'identifier': user_id},
                    payload={
                        'old_mode': current_mode.value if current_mode else None,
                        'new_mode': mode.value,
                        'reason': reason
                    }
                )
                ledger_entry_id = ledger_entry.get('ledger_entry_id', ledger_entry_id)
            
            # Set mode
            mode_id = set_mode(conn, mode, user_id, reason, ledger_entry_id)
            
            return {
                'mode_id': mode_id,
                'mode': mode.value,
                'changed_by': user_id,
                'changed_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                'ledger_entry_id': ledger_entry_id
            }
        finally:
            conn.close()
    
    def get_mode_history(self, limit: int = 10) -> list:
        """
        Get TRE mode change history.
        
        Args:
            limit: Maximum number of records to return
        
        Returns:
            List of mode change records
        """
        conn = create_write_connection(**self.db_conn_params, isolation_level=IsolationLevel.READ_COMMITTED, logger=_logger)
        try:
            return get_mode_history(conn, limit)
        finally:
            conn.close()
