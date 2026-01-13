#!/usr/bin/env python3
"""
RansomEye v1.0 RBAC Permission Checker
AUTHORITATIVE: Server-side permission enforcement (default DENY)
Python 3.10+ only
"""

import os
import sys
import uuid
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timezone
from pathlib import Path

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    from common.db.safety import create_readonly_connection, create_write_connection, IsolationLevel
    _common_available = True
    _logger = setup_logging('rbac-permission-checker')
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


class PermissionCheckerError(Exception):
    """Base exception for permission checker errors."""
    pass


class PermissionDeniedError(PermissionCheckerError):
    """Raised when permission is denied."""
    pass


class PermissionChecker:
    """
    Server-side permission checker (default DENY).
    
    CRITICAL: All permission checks are server-side enforced.
    UI hiding is insufficient; backend must block unauthorized actions.
    """
    
    # Permission enum values (matches database enum)
    PERMISSIONS = {
        # Incident permissions
        'incident:view',
        'incident:view_all',
        'incident:acknowledge',
        'incident:resolve',
        'incident:close',
        'incident:export',
        'incident:assign',
        
        # Policy permissions
        'policy:view',
        'policy:create',
        'policy:update',
        'policy:delete',
        'policy:execute',
        'policy:simulate',
        
        # Threat Response permissions
        'tre:view',
        'tre:execute',
        'tre:rollback',
        'tre:view_all',
        
        # Human Authority permissions
        'haf:view',
        'haf:create_override',
        'haf:approve',
        'haf:reject',
        
        # Forensics permissions
        'forensics:view',
        'forensics:export',
        
        # Reporting permissions
        'report:view',
        'report:generate',
        'report:export',
        'report:view_all',
        
        # Agent permissions
        'agent:install',
        'agent:uninstall',
        'agent:update',
        'agent:view',
        
        # User management permissions
        'user:create',
        'user:delete',
        'user:role_assign',
        
        # System permissions
        'system:view_config',
        'system:modify_config',
        'system:view_logs',
        'system:manage_users',
        'system:manage_roles',
        
        # Billing permissions
        'billing:view',
        'billing:manage',
        
        # Audit permissions
        'audit:view',
        'audit:view_all',
        'audit:export'
    }
    
    # Role enum values (matches database enum)
    ROLES = {
        'SUPER_ADMIN',
        'SECURITY_ANALYST',
        'POLICY_MANAGER',
        'IT_ADMIN',
        'AUDITOR'
    }
    
    def __init__(
        self,
        db_conn_params: Dict[str, Any],
        ledger_path: Optional[Path] = None,
        ledger_key_dir: Optional[Path] = None
    ):
        """
        Initialize permission checker.
        
        Args:
            db_conn_params: Database connection parameters
            ledger_path: Optional audit ledger path
            ledger_key_dir: Optional audit ledger key directory
        """
        self.db_conn_params = db_conn_params
        
        # Audit ledger
        if _audit_ledger_available and ledger_path and ledger_key_dir:
            self.ledger = AuditLedger(
                ledger_path=ledger_path,
                key_dir=ledger_key_dir
            )
        else:
            self.ledger = None
    
    def check_permission(
        self,
        user_id: str,
        permission: str,
        resource_type: str,
        resource_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has permission (default DENY).
        
        Process:
        1. Get user's role
        2. Check if role has permission
        3. Log decision (allow/deny)
        4. Emit audit ledger entry
        5. Return True if allowed, False if denied
        
        Args:
            user_id: User identifier
            permission: Permission to check
            resource_type: Type of resource
            resource_id: Optional resource identifier
        
        Returns:
            True if permission granted, False if denied
        
        Raises:
            PermissionCheckerError: If check fails
        """
        # Validate permission
        if permission not in self.PERMISSIONS:
            raise PermissionCheckerError(f"Invalid permission: {permission}")
        
        # Get user's role
        try:
            role = self._get_user_role(user_id)
            if not role:
                # User has no role → DENY
                self._log_permission_check(
                    user_id=user_id,
                    role=None,
                    permission=permission,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    decision='DENY',
                    reason='User has no role assigned'
                )
                return False
        except Exception as e:
            raise PermissionCheckerError(f"Failed to get user role: {e}") from e
        
        # Check if role has permission
        try:
            has_permission = self._role_has_permission(role, permission)
        except Exception as e:
            raise PermissionCheckerError(f"Failed to check role permission: {e}") from e
        
        # Log decision
        decision = 'ALLOW' if has_permission else 'DENY'
        reason = 'Permission granted' if has_permission else f'Role {role} lacks permission {permission}'
        
        ledger_entry_id = self._log_permission_check(
            user_id=user_id,
            role=role,
            permission=permission,
            resource_type=resource_type,
            resource_id=resource_id,
            decision=decision,
            reason=reason
        )
        
        # Emit audit ledger entry
        if self.ledger:
            try:
                self.ledger.append(
                    component='rbac',
                    component_instance_id='permission-checker',
                    action_type='rbac_permission_check',
                    subject={'type': resource_type, 'id': resource_id or 'global'},
                    actor={'type': 'user', 'identifier': user_id},
                    payload={
                        'permission': permission,
                        'role': role,
                        'decision': decision,
                        'reason': reason,
                        'audit_id': ledger_entry_id or ''
                    }
                )
            except Exception as e:
                if _logger:
                    _logger.error(f"Failed to emit audit ledger entry: {e}")
        
        return has_permission
    
    def _get_user_role(self, user_id: str) -> Optional[str]:
        """
        Get user's role.
        
        Args:
            user_id: User identifier
        
        Returns:
            Role name or None if user has no role
        """
        conn = None
        try:
            if _common_available:
                conn = create_readonly_connection(
                    host=self.db_conn_params['host'],
                    port=int(self.db_conn_params.get('port', 5432)),
                    database=self.db_conn_params['database'],
                    user=self.db_conn_params['user'],
                    password=self.db_conn_params['password'],
                    isolation_level=IsolationLevel.READ_COMMITTED,
                    logger=_logger
                )
            else:
                import psycopg2
                conn = psycopg2.connect(
                    host=self.db_conn_params['host'],
                    port=int(self.db_conn_params.get('port', 5432)),
                    database=self.db_conn_params['database'],
                    user=self.db_conn_params['user'],
                    password=self.db_conn_params['password']
                )
            
            cur = conn.cursor()
            cur.execute("""
                SELECT role
                FROM rbac_user_roles
                WHERE user_id = %s
            """, (user_id,))
            
            result = cur.fetchone()
            cur.close()
            
            return result[0] if result else None
        except Exception as e:
            raise PermissionCheckerError(f"Failed to get user role: {e}") from e
        finally:
            if conn:
                conn.close()
    
    def _role_has_permission(self, role: str, permission: str) -> bool:
        """
        Check if role has permission.
        
        Args:
            role: Role name
            permission: Permission name
        
        Returns:
            True if role has permission, False otherwise
        """
        conn = None
        try:
            if _common_available:
                conn = create_readonly_connection(
                    host=self.db_conn_params['host'],
                    port=int(self.db_conn_params.get('port', 5432)),
                    database=self.db_conn_params['database'],
                    user=self.db_conn_params['user'],
                    password=self.db_conn_params['password'],
                    isolation_level=IsolationLevel.READ_COMMITTED,
                    logger=_logger
                )
            else:
                import psycopg2
                conn = psycopg2.connect(
                    host=self.db_conn_params['host'],
                    port=int(self.db_conn_params.get('port', 5432)),
                    database=self.db_conn_params['database'],
                    user=self.db_conn_params['user'],
                    password=self.db_conn_params['password']
                )
            
            cur = conn.cursor()
            cur.execute("""
                SELECT COUNT(*)
                FROM rbac_role_permissions
                WHERE role = %s AND permission = %s
            """, (role, permission))
            
            result = cur.fetchone()
            cur.close()
            
            return result[0] > 0 if result else False
        except Exception as e:
            raise PermissionCheckerError(f"Failed to check role permission: {e}") from e
        finally:
            if conn:
                conn.close()
    
    def _log_permission_check(
        self,
        user_id: str,
        role: Optional[str],
        permission: str,
        resource_type: str,
        resource_id: Optional[str],
        decision: str,
        reason: str
    ) -> Optional[str]:
        """
        Log permission check to database.
        
        Args:
            user_id: User identifier
            role: Role name (or None)
            permission: Permission checked
            resource_type: Resource type
            resource_id: Resource identifier
            decision: Decision (ALLOW or DENY)
            reason: Reason for decision
        
        Returns:
            Audit ID (UUID string)
        """
        audit_id = str(uuid.uuid4())
        conn = None
        try:
            if _common_available:
                conn = create_write_connection(
                    host=self.db_conn_params['host'],
                    port=int(self.db_conn_params.get('port', 5432)),
                    database=self.db_conn_params['database'],
                    user=self.db_conn_params['user'],
                    password=self.db_conn_params['password'],
                    isolation_level=IsolationLevel.READ_COMMITTED,
                    logger=_logger
                )
            else:
                import psycopg2
                conn = psycopg2.connect(
                    host=self.db_conn_params['host'],
                    port=int(self.db_conn_params.get('port', 5432)),
                    database=self.db_conn_params['database'],
                    user=self.db_conn_params['user'],
                    password=self.db_conn_params['password']
                )
            
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO rbac_permission_audit (
                    audit_id, user_id, role, permission, resource_type, resource_id,
                    decision, reason, timestamp
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                audit_id, user_id, role or 'NONE', permission, resource_type,
                resource_id, decision, reason, datetime.now(timezone.utc)
            ))
            
            conn.commit()
            cur.close()
            
            return audit_id
        except Exception as e:
            if conn:
                conn.rollback()
            if _logger:
                _logger.error(f"Failed to log permission check: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def get_user_permissions(self, user_id: str) -> Set[str]:
        """
        Get all permissions for user (via role).
        
        Args:
            user_id: User identifier
        
        Returns:
            Set of permission names
        """
        role = self._get_user_role(user_id)
        if not role:
            return set()
        
        conn = None
        try:
            if _common_available:
                conn = create_readonly_connection(
                    host=self.db_conn_params['host'],
                    port=int(self.db_conn_params.get('port', 5432)),
                    database=self.db_conn_params['database'],
                    user=self.db_conn_params['user'],
                    password=self.db_conn_params['password'],
                    isolation_level=IsolationLevel.READ_COMMITTED,
                    logger=_logger
                )
            else:
                import psycopg2
                conn = psycopg2.connect(
                    host=self.db_conn_params['host'],
                    port=int(self.db_conn_params.get('port', 5432)),
                    database=self.db_conn_params['database'],
                    user=self.db_conn_params['user'],
                    password=self.db_conn_params['password']
                )
            
            cur = conn.cursor()
            cur.execute("""
                SELECT permission
                FROM rbac_role_permissions
                WHERE role = %s
            """, (role,))
            
            permissions = {row[0] for row in cur.fetchall()}
            cur.close()
            
            return permissions
        except Exception as e:
            raise PermissionCheckerError(f"Failed to get user permissions: {e}") from e
        finally:
            if conn:
                conn.close()
