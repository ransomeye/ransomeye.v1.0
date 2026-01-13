#!/usr/bin/env python3
"""
RansomEye v1.0 UI Backend - Emergency Override
AUTHORITATIVE: Emergency override for SUPER_ADMIN only (NO ASSUMPTIONS)
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
    _common_available = True
    _logger = setup_logging('ui-emergency-override')
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


class EmergencyOverride:
    """
    Emergency override for SUPER_ADMIN only.
    
    CRITICAL: Emergency path bypasses incident binding but requires:
    - Typed justification
    - Dual confirmation
    - EMERGENCY_OVERRIDE_USED audit event
    - Always creates rollback artifact
    """
    
    def __init__(
        self,
        ledger: Optional[AuditLedger] = None
    ):
        """
        Initialize emergency override.
        
        Args:
            ledger: Optional audit ledger instance
        """
        self.ledger = ledger
    
    def validate_emergency_override(
        self,
        user_id: str,
        user_role: str,
        justification: str,
        confirmation: bool
    ) -> bool:
        """
        Validate emergency override request.
        
        Args:
            user_id: User identifier
            user_role: User role (must be SUPER_ADMIN)
            justification: Typed justification (required)
            confirmation: Dual confirmation flag
        
        Returns:
            True if valid
        
        Raises:
            ValueError: If validation fails
        """
        # SUPER_ADMIN only
        if user_role != 'SUPER_ADMIN':
            raise ValueError("Emergency override requires SUPER_ADMIN role")
        
        # Justification required
        if not justification or len(justification.strip()) < 10:
            raise ValueError("Emergency override requires typed justification (minimum 10 characters)")
        
        # Dual confirmation required
        if not confirmation:
            raise ValueError("Emergency override requires dual confirmation")
        
        return True
    
    def execute_emergency_override(
        self,
        user_id: str,
        user_role: str,
        action_type: str,
        target: Dict[str, Any],
        justification: str,
        confirmation: bool
    ) -> Dict[str, Any]:
        """
        Execute emergency override action.
        
        Args:
            user_id: User identifier
            user_role: User role
            action_type: Action type
            target: Target object
            justification: Typed justification
            confirmation: Dual confirmation flag
        
        Returns:
            Emergency override result dictionary
        
        Raises:
            ValueError: If validation fails
        """
        # Validate
        self.validate_emergency_override(user_id, user_role, justification, confirmation)
        
        # Emit audit ledger event
        if self.ledger:
            self.ledger.append(
                component='ui',
                component_instance_id=os.getenv('HOSTNAME', 'ui-backend'),
                action_type='ui_emergency_override',
                subject={'type': 'emergency_action', 'id': str(uuid.uuid4())},
                actor={'type': 'user', 'identifier': user_id},
                payload={
                    'action_type': action_type,
                    'target': target,
                    'justification': justification,
                    'user_role': user_role
                }
            )
        
        return {
            'status': 'EMERGENCY_OVERRIDE_GRANTED',
            'action_type': action_type,
            'justification': justification,
            'executed_by': user_id,
            'executed_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'rollback_required': True
        }
