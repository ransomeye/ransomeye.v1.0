#!/usr/bin/env python3
"""
RansomEye v1.0 Validation Harness - Database Bootstrap Validator
AUTHORITATIVE: Diagnostic-only preflight validation for PostgreSQL authentication

PHASE A1 REQUIREMENT: This module is diagnostic-only. It detects PostgreSQL
authentication failure reasons and provides explicit instructions. It does NOT:
- Auto-edit files
- Downgrade security
- Continue execution on failure

This is NOT an application logic change — this is infrastructure correctness enforcement.
"""

import os
import sys
import glob
import psycopg2
from typing import Dict, Any, Optional, Tuple


def _detect_pg_hba_location(host: str = "localhost", port: int = 5432) -> Optional[str]:
    """
    Detect pg_hba.conf location (read-only, no modifications).
    
    Attempts (in order):
    1. Query PostgreSQL: SHOW hba_file; (if connection available)
    2. Fall back to known defaults:
       - /etc/postgresql/*/main/pg_hba.conf (Ubuntu/Debian)
       - /var/lib/pgsql/data/pg_hba.conf (RHEL/CentOS)
    
    Args:
        host: PostgreSQL host
        port: PostgreSQL port
    
    Returns:
        Path to pg_hba.conf if detected, None otherwise
    """
    # Strategy 1: Try to query PostgreSQL directly
    # This only works if we can connect (which we probably can't in auth failure cases)
    try:
        # Try connecting to postgres database as postgres user (might work with socket auth)
        if host in ('localhost', '127.0.0.1', ''):
            try:
                meta_conn = psycopg2.connect(
                    host='',  # Unix socket
                    port=port,
                    database='postgres',
                    user='postgres',
                    password='',
                    connect_timeout=2
                )
                cur = meta_conn.cursor()
                cur.execute("SHOW hba_file;")
                result = cur.fetchone()
                meta_conn.close()
                if result and result[0]:
                    return result[0]
            except:
                pass
        
        # Try with explicit host
        try:
            meta_conn = psycopg2.connect(
                host=host,
                port=port,
                database='postgres',
                user='postgres',
                password='',
                connect_timeout=2
            )
            cur = meta_conn.cursor()
            cur.execute("SHOW hba_file;")
            result = cur.fetchone()
            meta_conn.close()
            if result and result[0]:
                return result[0]
        except:
            pass
    except:
        pass
    
    # Strategy 2: Fall back to known defaults
    # Ubuntu/Debian: /etc/postgresql/*/main/pg_hba.conf
    ubuntu_patterns = glob.glob("/etc/postgresql/*/main/pg_hba.conf")
    if ubuntu_patterns:
        return ubuntu_patterns[0]
    
    # RHEL/CentOS: /var/lib/pgsql/data/pg_hba.conf
    if os.path.exists("/var/lib/pgsql/data/pg_hba.conf"):
        return "/var/lib/pgsql/data/pg_hba.conf"
    
    # Alternative RHEL/CentOS: /var/lib/pgsql/*/data/pg_hba.conf
    rhel_patterns = glob.glob("/var/lib/pgsql/*/data/pg_hba.conf")
    if rhel_patterns:
        return rhel_patterns[0]
    
    # Generic fallback: try common locations
    common_paths = [
        "/etc/postgresql/14/main/pg_hba.conf",
        "/etc/postgresql/13/main/pg_hba.conf",
        "/etc/postgresql/12/main/pg_hba.conf",
        "/var/lib/pgsql/data/pg_hba.conf",
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    return None


def verify_db_bootstrap(
    host: str = None,
    port: int = None,
    database: str = None,
    user: str = None,
    password: str = None
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Verify PostgreSQL bootstrap configuration with precise failure mode detection.
    
    Verifies:
    1. Role exists and has LOGIN privilege
    2. Database exists and is owned by role
    3. Authentication works (login succeeds)
    4. Basic SELECT 1 works
    
    Distinguishes between:
    - CASE 1: Role does not exist
    - CASE 2: Peer authentication (password ignored)
    - CASE 3: Wrong password
    - CASE 4: Database does not exist
    - CASE 5: Database exists but wrong owner
    - CASE 6: pg_hba blocks password auth entirely
    
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
            "status": "FAIL",
            "reason": "peer_auth" | "role_missing" | "password_mismatch" | 
                      "db_missing" | "wrong_owner" | "pg_hba_blocked" | 
                      "connection" | "query_failed",
            "type": "authentication" | "connection" | "role_missing" | 
                    "database_missing" | "ownership" | "query_failed",
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
    
    # STEP 1: Attempt password-based connection to target database
    # This will capture authentication errors that we need to parse
    password_error = None
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            connect_timeout=5
        )
        
        # Connection succeeded - verify everything
        cur = conn.cursor()
        cur.execute("SELECT 1")
        result = cur.fetchone()
        
        if result[0] != 1:
            conn.close()
            return False, {
                "status": "FAIL",
                "reason": "query_failed",
                "type": "query_failed",
                "message": "Database query returned unexpected result",
                "error_code": None,
                "error_detail": f"SELECT 1 returned {result[0]}, expected 1"
            }
        
        # Verify role exists and has LOGIN privilege
        cur.execute("""
            SELECT rolcanlogin, rolname
            FROM pg_roles
            WHERE rolname = %s
        """, (user,))
        role_info = cur.fetchone()
        
        if not role_info:
            conn.close()
            return False, {
                "status": "FAIL",
                "reason": "role_missing",
                "type": "role_missing",
                "message": f"Role '{user}' does not exist in PostgreSQL",
                "error_code": None,
                "error_detail": f"Role '{user}' not found in pg_roles"
            }
        
        rolcanlogin, rolname = role_info
        if not rolcanlogin:
            conn.close()
            return False, {
                "status": "FAIL",
                "reason": "role_missing",
                "type": "role_missing",
                "message": f"Role '{user}' exists but does not have LOGIN privilege",
                "error_code": None,
                "error_detail": f"Role '{user}' found but rolcanlogin=False"
            }
        
        # Verify database exists and is owned by role
        cur.execute("""
            SELECT datname, pg_catalog.pg_get_userbyid(datdba) as owner
            FROM pg_database
            WHERE datname = %s
        """, (database,))
        db_info = cur.fetchone()
        
        if not db_info:
            conn.close()
            return False, {
                "status": "FAIL",
                "reason": "db_missing",
                "type": "database_missing",
                "message": f"Database '{database}' does not exist in PostgreSQL",
                "error_code": None,
                "error_detail": f"Database '{database}' not found in pg_database"
            }
        
        datname, owner = db_info
        if owner != user:
            conn.close()
            return False, {
                "status": "FAIL",
                "reason": "wrong_owner",
                "type": "ownership",
                "message": f"Database '{database}' is not owned by role '{user}'",
                "error_code": None,
                "error_detail": f"Database '{database}' owned by '{owner}', expected '{user}'"
            }
        
        conn.close()
        return True, None
        
    except psycopg2.OperationalError as e:
        password_error = e
        error_code = getattr(e, 'pgcode', None)
        error_message = str(e).lower()
        
        # CASE 2: Peer authentication (password ignored)
        # Detectable by: "peer authentication failed" or "password ignored"
        if 'peer authentication failed' in error_message or 'password ignored' in error_message:
            # Detect pg_hba.conf location (read-only)
            pg_hba_path = _detect_pg_hba_location(host, port)
            return False, {
                "status": "FAIL",
                "reason": "peer_auth",
                "type": "authentication",
                "message": f"PostgreSQL is using PEER authentication",
                "error_code": error_code,
                "error_detail": str(e),
                "pg_hba_path": pg_hba_path,
                "auth_method": "peer"
            }
        
        # CASE 6: pg_hba blocks password auth entirely
        # Detectable by: "no pg_hba.conf entry" or "authentication method not supported"
        if 'no pg_hba.conf entry' in error_message or 'authentication method not supported' in error_message:
            # Detect pg_hba.conf location (read-only)
            pg_hba_path = _detect_pg_hba_location(host, port)
            return False, {
                "status": "FAIL",
                "reason": "pg_hba_blocked",
                "type": "authentication",
                "message": f"pg_hba.conf blocks password authentication",
                "error_code": error_code,
                "error_detail": str(e),
                "pg_hba_path": pg_hba_path
            }
        
        # CASE 4: Database does not exist
        # Detectable by: "database" + "does not exist" or "doesn't exist"
        if 'database' in error_message and ('does not exist' in error_message or "doesn't exist" in error_message):
            return False, {
                "status": "FAIL",
                "reason": "db_missing",
                "type": "database_missing",
                "message": f"Database '{database}' does not exist",
                "error_code": error_code,
                "error_detail": str(e)
            }
        
        # CASE 3 vs CASE 1: Need to distinguish wrong password from role missing
        # Both can produce "password authentication failed" or error code 28P01
        # We need to check if role exists by connecting to postgres database
        
        # CASE 3: Wrong password (role exists, but password is wrong)
        # CASE 1: Role doesn't exist
        # Both show up as authentication failures, but we can check role existence
        
        if error_code in ('28P01', '28000') or 'password authentication failed' in error_message:
            # Try to connect to postgres database to check if role exists
            # Use socket connection (no password) if on localhost
            role_exists = False
            role_check_error = None
            
            try:
                # Strategy: Try to connect to postgres database using socket authentication
                # This works on localhost when pg_hba.conf allows peer/trust for local connections
                # If socket auth works, the role exists
                
                if host in ('localhost', '127.0.0.1', ''):
                    # Try socket connection (empty host = Unix socket)
                    try:
                        meta_conn = psycopg2.connect(
                            host='',  # Empty host = Unix socket
                            port=port,
                            database='postgres',
                            user=user,
                            password='',
                            connect_timeout=2
                        )
                        # If we got here, role exists (socket auth worked)
                        meta_conn.close()
                        role_exists = True
                    except psycopg2.OperationalError as sock_err:
                        role_check_error = sock_err
                        # Socket auth failed - try with explicit localhost
                        try:
                            meta_conn = psycopg2.connect(
                                host='localhost',
                                port=port,
                                database='postgres',
                                user=user,
                                password='',
                                connect_timeout=2
                            )
                            meta_conn.close()
                            role_exists = True
                        except:
                            pass
                
                # If socket didn't work, try querying pg_roles via postgres superuser
                # This is a fallback - we don't assume superuser, but if it's available, use it
                if not role_exists:
                    try:
                        # Try connecting as postgres user (common default superuser)
                        # This may work if postgres user has no password or uses trust auth
                        meta_conn = psycopg2.connect(
                            host=host,
                            port=port,
                            database='postgres',
                            user='postgres',
                            password='',
                            connect_timeout=2
                        )
                        cur = meta_conn.cursor()
                        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (user,))
                        role_exists = cur.fetchone() is not None
                        meta_conn.close()
                    except:
                        # Can't check role existence via postgres user
                        pass
                
                # If still can't determine, check error message for hints
                # PostgreSQL sometimes includes "role" in the error message
                if not role_exists and 'role' in error_message and 'does not exist' in error_message:
                    # Error explicitly says role doesn't exist
                    role_exists = False
                elif not role_exists and 'password authentication failed' in error_message:
                    # Password auth failed - could be either case
                    # Default to role missing (more common bootstrap issue)
                    role_exists = False
                    
            except Exception as meta_err:
                # Can't determine role existence - default to role missing
                role_exists = False
            
            if role_exists:
                # CASE 3: Role exists, password is wrong
                return False, {
                    "status": "FAIL",
                    "reason": "password_mismatch",
                    "type": "authentication",
                    "message": f"PostgreSQL password mismatch for role '{user}'",
                    "error_code": error_code,
                    "error_detail": str(e)
                }
            else:
                # CASE 1: Role does not exist
                return False, {
                    "status": "FAIL",
                    "reason": "role_missing",
                    "type": "role_missing",
                    "message": f"PostgreSQL role '{user}' does not exist",
                    "error_code": error_code,
                    "error_detail": str(e)
                }
        
        # Generic connection error
        return False, {
            "status": "FAIL",
            "reason": "connection",
            "type": "connection",
            "message": f"PostgreSQL connection failed",
            "error_code": error_code,
            "error_detail": str(e)
        }
    
    except Exception as e:
        # Unexpected error
        return False, {
            "status": "FAIL",
            "reason": "connection",
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
        Formatted error message string with exact diagnostic information
    """
    failure_reason_str = failure_reason.get("reason", "unknown")
    
    # CASE 1: Role does not exist
    if failure_reason_str == "role_missing":
        return (
            f"❌ FATAL: PostgreSQL role '{user}' does not exist.\n"
            f"\n"
            f"Phase C requires:\n"
            f"  CREATE ROLE {user} LOGIN PASSWORD '{password}';\n"
            f"\n"
            f"Phase C cannot continue.\n"
        )
    
    # CASE 2: Peer authentication (password ignored)
    elif failure_reason_str == "peer_auth":
        pg_hba_path = failure_reason.get("pg_hba_path")
        auth_method = failure_reason.get("auth_method", "peer")
        
        # Build pg_hba path display
        if pg_hba_path:
            pg_hba_display = f"  {pg_hba_path}"
        else:
            pg_hba_display = "  (location not detected - check PostgreSQL data directory)"
        
        # OS-aware guidance
        os_guidance = ""
        if pg_hba_path and "/etc/postgresql" in pg_hba_path:
            os_guidance = (
                f"\n"
                f"On Ubuntu/Debian, PostgreSQL defaults to PEER auth for local sockets.\n"
            )
        elif pg_hba_path and "/var/lib/pgsql" in pg_hba_path:
            os_guidance = (
                f"\n"
                f"On RHEL/CentOS, PostgreSQL may use PEER auth for local connections.\n"
            )
        
        return (
            f"❌ FATAL: PostgreSQL is using PEER authentication.\n"
            f"\n"
            f"Password-based login for role '{user}' is ignored.\n"
            f"PostgreSQL is configured to use PEER authentication, which requires\n"
            f"the system user to match the database role name.\n"
            f"\n"
            f"Detected authentication method: {auth_method}\n"
            f"Detected pg_hba.conf location:\n"
            f"{pg_hba_display}\n"
            f"{os_guidance}"
            f"\n"
            f"EXPLICIT INSTRUCTION:\n"
            f"To allow password authentication, edit pg_hba.conf and change:\n"
            f"\n"
            f"  local   all   {user}   peer\n"
            f"\n"
            f"to:\n"
            f"\n"
            f"  local   all   {user}   md5\n"
            f"\n"
            f"OR for TCP/IP connections:\n"
            f"\n"
            f"  host    all   {user}   127.0.0.1/32   md5\n"
            f"\n"
            f"After editing pg_hba.conf:\n"
            f"  1. Save the file\n"
            f"  2. Restart PostgreSQL service:\n"
            f"     - systemctl restart postgresql  (systemd)\n"
            f"     - service postgresql restart    (SysV init)\n"
            f"\n"
            f"This is NOT a code issue.\n"
            f"PostgreSQL is not bootstrapped correctly.\n"
            f"\n"
            f"Phase C cannot continue.\n"
        )
    
    # CASE 3: Wrong password (role exists, password wrong)
    elif failure_reason_str == "password_mismatch":
        return (
            f"❌ FATAL: PostgreSQL password mismatch for role '{user}'.\n"
            f"\n"
            f"The role exists, but the password is NOT '{password}'.\n"
            f"\n"
            f"Fix by running:\n"
            f"\n"
            f"  ALTER ROLE {user} PASSWORD '{password}';\n"
            f"\n"
            f"Phase C cannot continue.\n"
        )
    
    # CASE 4: Database does not exist
    elif failure_reason_str == "db_missing":
        return (
            f"❌ FATAL: Database '{database}' does not exist.\n"
            f"\n"
            f"Fix by running:\n"
            f"\n"
            f"  CREATE DATABASE {database} OWNER {user};\n"
            f"\n"
            f"Phase C cannot continue.\n"
        )
    
    # CASE 5: Database exists but wrong owner
    elif failure_reason_str == "wrong_owner":
        return (
            f"❌ FATAL: Database '{database}' is not owned by role '{user}'.\n"
            f"\n"
            f"Fix by running:\n"
            f"\n"
            f"  ALTER DATABASE {database} OWNER TO {user};\n"
            f"\n"
            f"Phase C cannot continue.\n"
        )
    
    # CASE 6: pg_hba blocks password auth entirely
    elif failure_reason_str == "pg_hba_blocked":
        pg_hba_path = failure_reason.get("pg_hba_path")
        
        # Build pg_hba path display
        if pg_hba_path:
            pg_hba_display = f"  {pg_hba_path}"
        else:
            pg_hba_display = "  (location not detected)"
        
        return (
            f"❌ FATAL: pg_hba.conf blocks password authentication.\n"
            f"\n"
            f"Detected pg_hba.conf location:\n"
            f"{pg_hba_display}\n"
            f"\n"
            f"Ensure an entry exists like:\n"
            f"\n"
            f"  local   all   {user}   md5\n"
            f"\n"
            f"Then restart PostgreSQL.\n"
            f"\n"
            f"Phase C cannot continue.\n"
        )
    
    else:
        # Generic connection error or unknown
        error_detail = failure_reason.get("error_detail", "Unknown error")
        return (
            f"❌ FATAL: PostgreSQL connection failed.\n"
            f"\n"
            f"Error: {error_detail}\n"
            f"\n"
            f"Phase C cannot continue.\n"
        )
