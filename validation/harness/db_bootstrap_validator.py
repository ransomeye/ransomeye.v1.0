#!/usr/bin/env python3
"""
RansomEye v1.0 Validation Harness - Database Bootstrap Validator
AUTHORITATIVE: Verifies PostgreSQL is correctly bootstrapped for Phase C

This module verifies that PostgreSQL is pre-provisioned with:
- Role: gagan (with LOGIN privilege)
- Database: ransomeye (owned by gagan)
- Authentication works with credentials: gagan / gagan

This is NOT an application logic change — this is infrastructure correctness enforcement.
"""

import os
import sys
import psycopg2
from typing import Dict, Any, Optional, Tuple


def verify_db_bootstrap(
    host: str = None,
    port: int = None,
    database: str = None,
    user: str = None,
    password: str = None
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Verify PostgreSQL bootstrap configuration.
    
    Verifies:
    1. Role exists and has LOGIN privilege
    2. Database exists and is owned by role
    3. Authentication works (login succeeds)
    4. Basic SELECT 1 works
    
    Args:
        host: PostgreSQL host (default: localhost)
        port: PostgreSQL port (default: 5432)
        database: Database name (default: ransomeye)
        user: Database user (default: gagan)
        password: Database password (default: gagan)
    
    Returns:
        Tuple of (success: bool, failure_reason: Optional[Dict])
        
        If success=True, failure_reason is None.
        If success=False, failure_reason contains:
        {
            "type": "authentication" | "connection" | "role_missing" | "database_missing" | "ownership" | "query_failed",
            "message": "Human-readable error message",
            "error_code": "PostgreSQL error code (if available)",
            "error_detail": "Detailed error information"
        }
    """
    # Default values
    host = host or os.getenv("RANSOMEYE_DB_HOST", "localhost")
    port = port or int(os.getenv("RANSOMEYE_DB_PORT", "5432"))
    database = database or os.getenv("RANSOMEYE_DB_NAME", "ransomeye")
    user = user or os.getenv("RANSOMEYE_DB_USER", "gagan")
    password = password or os.getenv("RANSOMEYE_DB_PASSWORD", "gagan")
    
    # Step 1: Try to connect as postgres superuser to verify role/database existence
    # (This is informational only - we'll fail if we can't connect as the target user)
    postgres_user = os.getenv("POSTGRES_SUPERUSER", "postgres")
    postgres_password = os.getenv("POSTGRES_SUPERUSER_PASSWORD", "")
    
    # Step 2: Attempt connection with target credentials
    # This will fail if:
    # - Role doesn't exist (authentication error)
    # - Password is wrong (authentication error)
    # - Database doesn't exist (connection error)
    # - Network/connection issue (connection error)
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            connect_timeout=5
        )
        
        # Step 3: Verify basic query works
        cur = conn.cursor()
        cur.execute("SELECT 1")
        result = cur.fetchone()
        cur.close()
        
        if result[0] != 1:
            conn.close()
            return False, {
                "type": "query_failed",
                "message": "Database query returned unexpected result",
                "error_code": None,
                "error_detail": f"SELECT 1 returned {result[0]}, expected 1"
            }
        
        # Step 4: Verify role exists and has LOGIN privilege
        # (We can check this as the user itself)
        cur = conn.cursor()
        cur.execute("""
            SELECT rolcanlogin, rolname
            FROM pg_roles
            WHERE rolname = %s
        """, (user,))
        role_info = cur.fetchone()
        
        if not role_info:
            conn.close()
            return False, {
                "type": "role_missing",
                "message": f"Role '{user}' does not exist in PostgreSQL",
                "error_code": None,
                "error_detail": f"Role '{user}' not found in pg_roles"
            }
        
        rolcanlogin, rolname = role_info
        if not rolcanlogin:
            conn.close()
            return False, {
                "type": "role_missing",
                "message": f"Role '{user}' exists but does not have LOGIN privilege",
                "error_code": None,
                "error_detail": f"Role '{user}' found but rolcanlogin=False"
            }
        
        # Step 5: Verify database exists and is owned by role
        cur.execute("""
            SELECT datname, pg_catalog.pg_get_userbyid(datdba) as owner
            FROM pg_database
            WHERE datname = %s
        """, (database,))
        db_info = cur.fetchone()
        
        if not db_info:
            conn.close()
            return False, {
                "type": "database_missing",
                "message": f"Database '{database}' does not exist in PostgreSQL",
                "error_code": None,
                "error_detail": f"Database '{database}' not found in pg_database"
            }
        
        datname, owner = db_info
        if owner != user:
            conn.close()
            return False, {
                "type": "ownership",
                "message": f"Database '{database}' is not owned by role '{user}'",
                "error_code": None,
                "error_detail": f"Database '{database}' owned by '{owner}', expected '{user}'"
            }
        
        conn.close()
        return True, None
        
    except psycopg2.OperationalError as e:
        # Extract PostgreSQL error code if available
        error_code = getattr(e, 'pgcode', None)
        error_message = str(e)
        
        # Check for authentication failures
        # PostgreSQL error codes:
        # 28P01 = invalid_password
        # 28000 = invalid_authorization_specification
        if error_code in ('28P01', '28000') or 'password authentication failed' in error_message.lower():
            return False, {
                "type": "authentication",
                "message": f"PostgreSQL authentication failed for user '{user}'",
                "error_code": error_code,
                "error_detail": error_message
            }
        
        # Check for database doesn't exist
        if 'database' in error_message.lower() and ('does not exist' in error_message.lower() or 'doesn\'t exist' in error_message.lower()):
            return False, {
                "type": "database_missing",
                "message": f"Database '{database}' does not exist",
                "error_code": error_code,
                "error_detail": error_message
            }
        
        # Generic connection error
        return False, {
            "type": "connection",
            "message": f"PostgreSQL connection failed",
            "error_code": error_code,
            "error_detail": error_message
        }
    
    except Exception as e:
        # Unexpected error
        return False, {
            "type": "connection",
            "message": f"Unexpected error during database bootstrap verification",
            "error_code": None,
            "error_detail": str(e)
        }


def format_bootstrap_failure_message(failure_reason: Dict[str, Any], user: str = "gagan", password: str = "gagan", database: str = "ransomeye") -> str:
    """
    Format a clear, actionable error message for bootstrap failure.
    
    Args:
        failure_reason: Failure reason dictionary from verify_db_bootstrap()
        user: Database user (for error message)
        password: Database password (for error message)
        database: Database name (for error message)
    
    Returns:
        Formatted error message string
    """
    failure_type = failure_reason.get("type", "unknown")
    
    if failure_type == "authentication":
        return (
            f"❌ FATAL: PostgreSQL authentication failed.\n"
            f"\n"
            f"Required POC credentials:\n"
            f"  user: {user}\n"
            f"  password: {password}\n"
            f"  database: {database}\n"
            f"\n"
            f"This is NOT a code issue.\n"
            f"PostgreSQL is not bootstrapped correctly.\n"
            f"\n"
            f"Fix by running (once, as postgres superuser):\n"
            f"\n"
            f"  CREATE ROLE {user} LOGIN PASSWORD '{password}';\n"
            f"  CREATE DATABASE {database} OWNER {user};\n"
            f"  GRANT ALL PRIVILEGES ON DATABASE {database} TO {user};\n"
            f"\n"
            f"Phase C cannot continue.\n"
        )
    
    elif failure_type == "role_missing":
        return (
            f"❌ FATAL: PostgreSQL role '{user}' does not exist or lacks LOGIN privilege.\n"
            f"\n"
            f"Required POC credentials:\n"
            f"  user: {user}\n"
            f"  password: {password}\n"
            f"  database: {database}\n"
            f"\n"
            f"This is NOT a code issue.\n"
            f"PostgreSQL is not bootstrapped correctly.\n"
            f"\n"
            f"Fix by running (once, as postgres superuser):\n"
            f"\n"
            f"  CREATE ROLE {user} LOGIN PASSWORD '{password}';\n"
            f"\n"
            f"Phase C cannot continue.\n"
        )
    
    elif failure_type == "database_missing":
        return (
            f"❌ FATAL: PostgreSQL database '{database}' does not exist.\n"
            f"\n"
            f"Required POC credentials:\n"
            f"  user: {user}\n"
            f"  password: {password}\n"
            f"  database: {database}\n"
            f"\n"
            f"This is NOT a code issue.\n"
            f"PostgreSQL is not bootstrapped correctly.\n"
            f"\n"
            f"Fix by running (once, as postgres superuser):\n"
            f"\n"
            f"  CREATE DATABASE {database} OWNER {user};\n"
            f"  GRANT ALL PRIVILEGES ON DATABASE {database} TO {user};\n"
            f"\n"
            f"Phase C cannot continue.\n"
        )
    
    elif failure_type == "ownership":
        return (
            f"❌ FATAL: PostgreSQL database '{database}' is not owned by role '{user}'.\n"
            f"\n"
            f"Required POC credentials:\n"
            f"  user: {user}\n"
            f"  password: {password}\n"
            f"  database: {database}\n"
            f"\n"
            f"This is NOT a code issue.\n"
            f"PostgreSQL is not bootstrapped correctly.\n"
            f"\n"
            f"Fix by running (once, as postgres superuser):\n"
            f"\n"
            f"  ALTER DATABASE {database} OWNER TO {user};\n"
            f"  GRANT ALL PRIVILEGES ON DATABASE {database} TO {user};\n"
            f"\n"
            f"Phase C cannot continue.\n"
        )
    
    else:
        # Generic connection error
        error_detail = failure_reason.get("error_detail", "Unknown error")
        return (
            f"❌ FATAL: PostgreSQL connection failed.\n"
            f"\n"
            f"Required POC credentials:\n"
            f"  user: {user}\n"
            f"  password: {password}\n"
            f"  database: {database}\n"
            f"\n"
            f"Error: {error_detail}\n"
            f"\n"
            f"This is NOT a code issue.\n"
            f"PostgreSQL is not bootstrapped correctly.\n"
            f"\n"
            f"Fix by running (once, as postgres superuser):\n"
            f"\n"
            f"  CREATE ROLE {user} LOGIN PASSWORD '{password}';\n"
            f"  CREATE DATABASE {database} OWNER {user};\n"
            f"  GRANT ALL PRIVILEGES ON DATABASE {database} TO {user};\n"
            f"\n"
            f"Phase C cannot continue.\n"
        )
