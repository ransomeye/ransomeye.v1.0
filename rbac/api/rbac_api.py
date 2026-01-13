#!/usr/bin/env python3
"""
RansomEye v1.0 RBAC API
AUTHORITATIVE: Public API for RBAC operations
Python 3.10+ only
"""

import os
import sys
import uuid
import bcrypt
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    from common.db.safety import create_write_connection, create_readonly_connection, IsolationLevel
    _common_available = True
    _logger = setup_logging('rbac-api')
except ImportError:
    _common_available = False
    _logger = None

# Add rbac to path
_rbac_path = os.path.join(_project_root, 'rbac')
if os.path.exists(_rbac_path) and _rbac_path not in sys.path:
    sys.path.insert(0, _rbac_path)

from engine.permission_checker import PermissionChecker, PermissionCheckerError
from engine.role_permission_mapper import ROLE_PERMISSIONS, get_role_permissions

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


class RBACAPIError(Exception):
    """Base exception for RBAC API errors."""
    pass


class RBACAPI:
    """
    Public API for RBAC operations.
    
    All operations:
    - Create users
    - Assign roles
    - Check permissions
    - Emit audit ledger entries
    """
    
    def __init__(
        self,
        db_conn_params: Dict[str, Any],
        ledger_path: Optional[Path] = None,
        ledger_key_dir: Optional[Path] = None
    ):
        """
        Initialize RBAC API.
        
        Args:
            db_conn_params: Database connection parameters
            ledger_path: Optional audit ledger path
            ledger_key_dir: Optional audit ledger key directory
        """
        self.db_conn_params = db_conn_params
        self.permission_checker = PermissionChecker(db_conn_params, ledger_path, ledger_key_dir)
        
        # Audit ledger
        if _audit_ledger_available and ledger_path and ledger_key_dir:
            self.ledger = AuditLedger(
                ledger_path=ledger_path,
                key_dir=ledger_key_dir
            )
        else:
            self.ledger = None
    
    def create_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        created_by: str = 'system'
    ) -> Dict[str, Any]:
        """
        Create user account.
        
        Args:
            username: Username
            password: Plaintext password (will be hashed)
            email: Optional email address
            full_name: Optional full name
            created_by: User who created this account
        
        Returns:
            User dictionary
        """
        user_id = str(uuid.uuid4())
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
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
                INSERT INTO rbac_users (
                    user_id, username, password_hash, email, full_name, is_active, created_at, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id, username, password_hash, email, full_name, True,
                datetime.now(timezone.utc), created_by
            ))
            
            conn.commit()
            cur.close()
            
            user = {
                'user_id': user_id,
                'username': username,
                'email': email,
                'full_name': full_name,
                'is_active': True,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Emit audit ledger entry
            if self.ledger:
                try:
                    self.ledger.append(
                        component='rbac',
                        component_instance_id='rbac-api',
                        action_type='admin_user_action',
                        subject={'type': 'user', 'id': user_id},
                        actor={'type': 'user', 'identifier': created_by},
                        payload={
                            'action': 'create_user',
                            'username': username
                        }
                    )
                except Exception as e:
                    if _logger:
                        _logger.error(f"Failed to emit audit ledger entry: {e}")
            
            return user
        except Exception as e:
            if conn:
                conn.rollback()
            raise RBACAPIError(f"Failed to create user: {e}") from e
        finally:
            if conn:
                conn.close()
    
    def assign_role(
        self,
        user_id: str,
        role: str,
        assigned_by: str
    ) -> Dict[str, Any]:
        """
        Assign role to user (one role per user).
        
        Args:
            user_id: User identifier
            role: Role name
            assigned_by: User who assigned this role
        
        Returns:
            User-role assignment dictionary
        """
        if role not in ROLE_PERMISSIONS:
            raise RBACAPIError(f"Invalid role: {role}")
        
        user_role_id = str(uuid.uuid4())
        
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
            # Delete existing role assignment (one role per user)
            cur.execute("DELETE FROM rbac_user_roles WHERE user_id = %s", (user_id,))
            
            # Insert new role assignment
            cur.execute("""
                INSERT INTO rbac_user_roles (
                    user_role_id, user_id, role, assigned_at, assigned_by
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                user_role_id, user_id, role, datetime.now(timezone.utc), assigned_by
            ))
            
            conn.commit()
            cur.close()
            
            assignment = {
                'user_role_id': user_role_id,
                'user_id': user_id,
                'role': role,
                'assigned_at': datetime.now(timezone.utc).isoformat(),
                'assigned_by': assigned_by
            }
            
            # Emit audit ledger entry
            if self.ledger:
                try:
                    self.ledger.append(
                        component='rbac',
                        component_instance_id='rbac-api',
                        action_type='admin_user_action',
                        subject={'type': 'user', 'id': user_id},
                        actor={'type': 'user', 'identifier': assigned_by},
                        payload={
                            'action': 'assign_role',
                            'role': role
                        }
                    )
                except Exception as e:
                    if _logger:
                        _logger.error(f"Failed to emit audit ledger entry: {e}")
            
            return assignment
        except Exception as e:
            if conn:
                conn.rollback()
            raise RBACAPIError(f"Failed to assign role: {e}") from e
        finally:
            if conn:
                conn.close()
    
    def initialize_role_permissions(self, created_by: str = 'system') -> None:
        """
        Initialize role-permission mappings in database.
        
        This should be called once during system setup.
        
        Args:
            created_by: User who initialized mappings
        """
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
            
            # Insert role-permission mappings
            for role, permissions in ROLE_PERMISSIONS.items():
                for permission in permissions:
                    role_permission_id = str(uuid.uuid4())
                    try:
                        cur.execute("""
                            INSERT INTO rbac_role_permissions (
                                role_permission_id, role, permission, created_at, created_by
                            ) VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (role, permission) DO NOTHING
                        """, (
                            role_permission_id, role, permission,
                            datetime.now(timezone.utc), created_by
                        ))
                    except Exception:
                        # Ignore conflicts (already exists)
                        pass
            
            conn.commit()
            cur.close()
            
            # Emit audit ledger entry
            if self.ledger:
                try:
                    self.ledger.append(
                        component='rbac',
                        component_instance_id='rbac-api',
                        action_type='admin_config_change',
                        subject={'type': 'config', 'id': 'role_permissions'},
                        actor={'type': 'user', 'identifier': created_by},
                        payload={
                            'action': 'initialize_role_permissions'
                        }
                    )
                except Exception as e:
                    if _logger:
                        _logger.error(f"Failed to emit audit ledger entry: {e}")
        except Exception as e:
            if conn:
                conn.rollback()
            raise RBACAPIError(f"Failed to initialize role permissions: {e}") from e
        finally:
            if conn:
                conn.close()
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate user.
        
        Args:
            username: Username
            password: Plaintext password
        
        Returns:
            User dictionary if authenticated, None otherwise
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
                SELECT user_id, username, password_hash, email, full_name, is_active
                FROM rbac_users
                WHERE username = %s
            """, (username,))
            
            result = cur.fetchone()
            cur.close()
            
            if not result:
                return None
            
            user_id, username_db, password_hash, email, full_name, is_active = result
            
            if not is_active:
                return None
            
            # Verify password
            if not bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                return None
            
            # Update last login
            if _common_available:
                conn.close()
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
                UPDATE rbac_users
                SET last_login_at = %s
                WHERE user_id = %s
            """, (datetime.now(timezone.utc), user_id))
            
            conn.commit()
            cur.close()
            
            # Get user's role
            cur = conn.cursor()
            cur.execute("""
                SELECT role
                FROM rbac_user_roles
                WHERE user_id = %s
            """, (user_id,))
            
            role_result = cur.fetchone()
            role = role_result[0] if role_result else None
            cur.close()
            
            user = {
                'user_id': user_id,
                'username': username_db,
                'email': email,
                'full_name': full_name,
                'is_active': is_active,
                'role': role
            }
            
            return user
        except Exception as e:
            raise RBACAPIError(f"Failed to authenticate user: {e}") from e
        finally:
            if conn:
                conn.close()
