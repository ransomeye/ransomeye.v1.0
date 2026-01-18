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

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Fetch user by username.

        Args:
            username: Username to look up

        Returns:
            User dictionary if found, None otherwise
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
                SELECT user_id, username, email, full_name, is_active
                FROM rbac_users
                WHERE username = %s
            """, (username,))
            row = cur.fetchone()
            cur.close()

            if not row:
                return None

            return {
                'user_id': row[0],
                'username': row[1],
                'email': row[2],
                'full_name': row[3],
                'is_active': row[4]
            }
        except Exception as e:
            raise RBACAPIError(f"Failed to fetch user by username: {e}") from e
        finally:
            if conn:
                conn.close()

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch user by ID.

        Args:
            user_id: User identifier

        Returns:
            User dictionary if found, None otherwise
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
                SELECT user_id, username, email, full_name, is_active
                FROM rbac_users
                WHERE user_id = %s
            """, (user_id,))
            row = cur.fetchone()
            cur.close()

            if not row:
                return None

            return {
                'user_id': row[0],
                'username': row[1],
                'email': row[2],
                'full_name': row[3],
                'is_active': row[4]
            }
        except Exception as e:
            raise RBACAPIError(f"Failed to fetch user: {e}") from e
        finally:
            if conn:
                conn.close()

    def get_user_role(self, user_id: str) -> Optional[str]:
        """
        Fetch user's role.

        Args:
            user_id: User identifier

        Returns:
            Role name or None if not assigned
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
            row = cur.fetchone()
            cur.close()
            return row[0] if row else None
        except Exception as e:
            raise RBACAPIError(f"Failed to fetch user role: {e}") from e
        finally:
            if conn:
                conn.close()

    def store_refresh_token(
        self,
        token_id: str,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> None:
        """
        Store refresh token metadata (hashed).

        Args:
            token_id: Refresh token jti
            user_id: Token owner
            token_hash: SHA256 hash of refresh token
            expires_at: Token expiration timestamp
            user_agent: Optional user agent
            ip_address: Optional IP address
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
            cur.execute("""
                INSERT INTO rbac_refresh_tokens (
                    token_id, user_id, token_hash, issued_at, expires_at,
                    revoked_at, revoked_by, revocation_reason, user_agent, ip_address
                ) VALUES (%s, %s, %s, %s, %s, NULL, NULL, NULL, %s, %s)
            """, (
                token_id, user_id, token_hash, datetime.now(timezone.utc), expires_at,
                user_agent, ip_address
            ))
            conn.commit()
            cur.close()
        except Exception as e:
            if conn:
                conn.rollback()
            raise RBACAPIError(f"Failed to store refresh token: {e}") from e
        finally:
            if conn:
                conn.close()

    def revoke_refresh_token(
        self,
        token_id: str,
        revoked_by: str = "ui-backend",
        reason: str = "logout"
    ) -> None:
        """
        Revoke a refresh token.

        Args:
            token_id: Refresh token jti
            revoked_by: Revoker identifier
            reason: Revocation reason
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
            cur.execute("""
                UPDATE rbac_refresh_tokens
                SET revoked_at = %s, revoked_by = %s, revocation_reason = %s
                WHERE token_id = %s AND revoked_at IS NULL
            """, (datetime.now(timezone.utc), revoked_by, reason, token_id))
            conn.commit()
            cur.close()
        except Exception as e:
            if conn:
                conn.rollback()
            raise RBACAPIError(f"Failed to revoke refresh token: {e}") from e
        finally:
            if conn:
                conn.close()

    def revoke_refresh_tokens_for_user(
        self,
        user_id: str,
        revoked_by: str = "ui-backend",
        reason: str = "logout_all"
    ) -> int:
        """
        Revoke all refresh tokens for a user.

        Args:
            user_id: User identifier
            revoked_by: Revoker identifier
            reason: Revocation reason

        Returns:
            Count of revoked tokens
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
            cur.execute("""
                UPDATE rbac_refresh_tokens
                SET revoked_at = %s, revoked_by = %s, revocation_reason = %s
                WHERE user_id = %s AND revoked_at IS NULL
            """, (datetime.now(timezone.utc), revoked_by, reason, user_id))
            revoked = cur.rowcount
            conn.commit()
            cur.close()
            return revoked
        except Exception as e:
            if conn:
                conn.rollback()
            raise RBACAPIError(f"Failed to revoke refresh tokens: {e}") from e
        finally:
            if conn:
                conn.close()

    def validate_refresh_token(self, token_id: str, token_hash: str) -> Optional[Dict[str, Any]]:
        """
        Validate refresh token against stored hash and revocation state.

        Args:
            token_id: Refresh token jti
            token_hash: SHA256 hash of refresh token

        Returns:
            Dictionary with user_id if valid, None otherwise
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
                SELECT user_id, expires_at, revoked_at
                FROM rbac_refresh_tokens
                WHERE token_id = %s AND token_hash = %s
            """, (token_id, token_hash))
            row = cur.fetchone()
            cur.close()

            if not row:
                return None

            user_id, expires_at, revoked_at = row
            if revoked_at is not None:
                return None
            if expires_at <= datetime.now(timezone.utc):
                return None

            return {
                'user_id': user_id,
                'expires_at': expires_at
            }
        except Exception as e:
            raise RBACAPIError(f"Failed to validate refresh token: {e}") from e
        finally:
            if conn:
                conn.close()
