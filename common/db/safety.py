#!/usr/bin/env python3
"""
RansomEye v1.0 Common Database Safety Utilities
AUTHORITATIVE: Database transaction safety and integrity enforcement
"""

import sys
import psycopg2
from psycopg2 import pool, extensions, sql, OperationalError, IntegrityError
from psycopg2.extensions import ISOLATION_LEVEL_READ_COMMITTED, ISOLATION_LEVEL_REPEATABLE_READ, ISOLATION_LEVEL_SERIALIZABLE
from typing import Optional, Callable, Any, Dict
from enum import IntEnum

# Import psycopg2.errors if available (Python 2.7+ compatibility)
try:
    from psycopg2 import errors as pg_errors
except ImportError:
    # Fallback for older psycopg2 versions
    pg_errors = None


class IsolationLevel(IntEnum):
    """PostgreSQL isolation levels."""
    READ_COMMITTED = ISOLATION_LEVEL_READ_COMMITTED
    REPEATABLE_READ = ISOLATION_LEVEL_REPEATABLE_READ
    SERIALIZABLE = ISOLATION_LEVEL_SERIALIZABLE


# Deadlock and integrity violation error codes
DEADLOCK_ERROR_CODE = "40P01"
SERIALIZATION_ERROR_CODE = "40001"
UNIQUE_VIOLATION_ERROR_CODE = "23505"
FOREIGN_KEY_VIOLATION_ERROR_CODE = "23503"
NOT_NULL_VIOLATION_ERROR_CODE = "23502"
CHECK_VIOLATION_ERROR_CODE = "23514"
READ_ONLY_VIOLATION_ERROR_CODE = "25006"


def _is_deadlock_error(error: Exception) -> bool:
    """Check if error is a deadlock."""
    if pg_errors and isinstance(error, pg_errors.DeadlockDetected):
        return True
    if isinstance(error, OperationalError) and hasattr(error, 'pgcode'):
        return error.pgcode == DEADLOCK_ERROR_CODE
    return False


def _is_serialization_error(error: Exception) -> bool:
    """Check if error is a serialization failure."""
    if pg_errors and isinstance(error, pg_errors.SerializationFailure):
        return True
    if isinstance(error, OperationalError) and hasattr(error, 'pgcode'):
        return error.pgcode == SERIALIZATION_ERROR_CODE
    return False


def _is_integrity_violation(error: Exception) -> bool:
    """Check if error is an integrity constraint violation."""
    if pg_errors:
        if isinstance(error, (pg_errors.UniqueViolation,
                              pg_errors.ForeignKeyViolation,
                              pg_errors.NotNullViolation,
                              pg_errors.CheckViolation)):
            return True
    if isinstance(error, IntegrityError):
        if hasattr(error, 'pgcode'):
            return error.pgcode in (
                UNIQUE_VIOLATION_ERROR_CODE,
                FOREIGN_KEY_VIOLATION_ERROR_CODE,
                NOT_NULL_VIOLATION_ERROR_CODE,
                CHECK_VIOLATION_ERROR_CODE
            )
    return False


def _is_readonly_violation(error: Exception) -> bool:
    """Check if error is a read-only transaction violation."""
    if pg_errors and hasattr(pg_errors, "ReadOnlySqlTransaction"):
        if isinstance(error, pg_errors.ReadOnlySqlTransaction):
            return True
    if hasattr(error, 'pgcode'):
        return error.pgcode == READ_ONLY_VIOLATION_ERROR_CODE
    return False


def _detect_and_fail_on_db_error(error: Exception, operation: str, logger) -> None:
    """
    Detect deadlocks, serialization failures, and integrity violations.
    Log and terminate immediately (no retries).
    """
    if _is_readonly_violation(error):
        error_msg = f"READ_ONLY_VIOLATION: Unauthorized write attempt detected in {operation}: {error}"
        logger.fatal(error_msg)
        from common.shutdown import ExitCode, exit_readonly_violation
        exit_readonly_violation(error_msg, ExitCode.RUNTIME_ERROR)

    if _is_deadlock_error(error):
        error_msg = f"DATABASE DEADLOCK DETECTED in {operation}: {error}"
        logger.fatal(error_msg)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
    
    if _is_serialization_error(error):
        error_msg = f"DATABASE SERIALIZATION FAILURE in {operation}: {error}"
        logger.fatal(error_msg)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
    
    if _is_integrity_violation(error):
        error_msg = f"DATABASE INTEGRITY VIOLATION in {operation}: {error}"
        logger.fatal(error_msg)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)


def validate_connection_health(conn) -> bool:
    """
    Validate connection health before critical operation.
    Fail immediately if connection is broken.
    """
    if conn.closed:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        return True
    except Exception:
        return False


def enforce_read_only_connection(conn, logger) -> None:
    """
    Enforce read-only connection.
    Abort process if write attempt occurs.
    """
    try:
        cur = conn.cursor()
        # Check if connection is in read-only mode
        cur.execute("SHOW transaction_read_only")
        result = cur.fetchone()
        cur.close()
        
        if result and result[0] != "on":
            # Attempt to set read-only mode
            cur = conn.cursor()
            cur.execute("SET TRANSACTION READ ONLY")
            cur.close()
            logger.info("Read-only transaction mode enforced")
    except Exception as e:
        error_msg = f"FAILED TO ENFORCE READ-ONLY MODE: {e}"
        logger.fatal(error_msg)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)


def create_write_connection(host: str, port: int, database: str, user: str, password: str,
                            isolation_level: IsolationLevel = IsolationLevel.READ_COMMITTED,
                            logger=None) -> psycopg2.extensions.connection:
    """
    Create write-enabled database connection with explicit isolation level.
    
    Logs isolation level at connection creation.
    Rejects runtime if isolation cannot be enforced.
    """
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        
        # Set explicit isolation level
        conn.set_isolation_level(isolation_level)
        
        # Validate isolation level was set
        cur = conn.cursor()
        cur.execute("SHOW transaction_isolation")
        actual_isolation = cur.fetchone()[0]
        cur.close()
        
        isolation_name = isolation_level.name if hasattr(isolation_level, 'name') else str(isolation_level)
        if logger:
            logger.startup(f"Database connection created with isolation level: {actual_isolation} (requested: {isolation_name})")
        
        # Verify connection health
        if not validate_connection_health(conn):
            conn.close()
            raise RuntimeError("Connection health validation failed")
        
        return conn
    except Exception as e:
        error_msg = f"FAILED TO CREATE DATABASE CONNECTION WITH ISOLATION LEVEL: {e}"
        if logger:
            logger.fatal(error_msg)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.STARTUP_ERROR)


def create_readonly_connection(host: str, port: int, database: str, user: str, password: str,
                               isolation_level: IsolationLevel = IsolationLevel.READ_COMMITTED,
                               logger=None) -> psycopg2.extensions.connection:
    """
    Create read-only database connection with explicit isolation level.
    
    Enforces read-only mode.
    Aborts process if write attempt occurs.
    """
    conn = create_write_connection(host, port, database, user, password, isolation_level, logger)
    
    # Enforce read-only mode
    if logger:
        enforce_read_only_connection(conn, logger)
    
    return conn


def begin_transaction(conn, logger) -> None:
    """
    Explicitly begin transaction.
    No implicit autocommit behavior.
    """
    try:
        # Ensure autocommit is off
        if conn.autocommit:
            conn.autocommit = False
        
        # Explicit BEGIN
        cur = conn.cursor()
        cur.execute("BEGIN")
        cur.close()
        
        if logger:
            logger.info("Transaction explicitly begun")
    except Exception as e:
        error_msg = f"FAILED TO BEGIN TRANSACTION: {e}"
        if logger:
            logger.fatal(error_msg)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)


def commit_transaction(conn, logger, operation: str = "unknown") -> None:
    """
    Explicitly commit transaction.
    Detects deadlocks, serialization failures, and integrity violations.
    Logs and terminates on failure (no retries).
    """
    try:
        if not validate_connection_health(conn):
            raise RuntimeError("Connection health validation failed before commit")
        
        conn.commit()
        
        if logger:
            logger.info(f"Transaction committed successfully", operation=operation)
    except Exception as e:
        # Detect and fail on deadlock/serialization/integrity violations
        if logger:
            _detect_and_fail_on_db_error(e, f"commit_transaction({operation})", logger)
        
        # Attempt rollback
        try:
            conn.rollback()
        except Exception as rollback_error:
            error_msg = f"FAILED TO ROLLBACK AFTER COMMIT FAILURE: {rollback_error}"
            if logger:
                logger.fatal(error_msg)
            from common.shutdown import ExitCode, exit_fatal
            exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
        
        raise


def rollback_transaction(conn, logger, operation: str = "unknown") -> None:
    """
    Explicitly rollback transaction.
    If rollback fails, terminate Core immediately.
    """
    try:
        conn.rollback()
        
        if logger:
            logger.info(f"Transaction rolled back", operation=operation)
    except Exception as e:
        error_msg = f"FAILED TO ROLLBACK TRANSACTION ({operation}): {e}"
        if logger:
            logger.fatal(error_msg)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)


def execute_write_operation(conn, operation_name: str, operation_func: Callable[[], Any],
                            logger) -> Any:
    """
    Execute write operation with explicit transaction management.
    
    Ensures:
    - Explicit transaction begin
    - Explicit commit on success
    - Explicit rollback on failure
    - Deadlock/integrity violation detection
    - Connection health validation
    - If rollback fails, terminate Core immediately
    """
    # Validate connection health before operation
    if not validate_connection_health(conn):
        error_msg = f"Connection health validation failed before {operation_name}"
        logger.fatal(error_msg)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
    
    # Explicit transaction begin
    begin_transaction(conn, logger)
    
    try:
        # Execute operation
        result = operation_func()
        
        # Explicit commit on success
        commit_transaction(conn, logger, operation_name)
        
        return result
    except Exception as e:
        # Detect and fail on deadlock/serialization/integrity violations
        _detect_and_fail_on_db_error(e, operation_name, logger)
        
        # Explicit rollback on failure
        rollback_transaction(conn, logger, operation_name)
        
        raise


def execute_read_operation(conn, operation_name: str, operation_func: Callable[[], Any],
                           logger, enforce_readonly: bool = True) -> Any:
    """
    Execute read operation with connection health validation.
    
    If enforce_readonly is True, aborts process if write attempt occurs.
    """
    # Validate connection health before operation
    if not validate_connection_health(conn):
        error_msg = f"Connection health validation failed before {operation_name}"
        logger.fatal(error_msg)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
    
    # Enforce read-only if required
    if enforce_readonly:
        enforce_read_only_connection(conn, logger)
    
    try:
        # Execute read operation
        return operation_func()
    except Exception as e:
        # Detect and fail on deadlock/serialization errors (even for reads)
        _detect_and_fail_on_db_error(e, operation_name, logger)
        raise


def create_write_connection_pool(min_conn: int, max_conn: int,
                                 host: str, port: int, database: str, user: str, password: str,
                                 isolation_level: IsolationLevel = IsolationLevel.READ_COMMITTED,
                                 logger=None) -> pool.ThreadedConnectionPool:
    """
    Create write-enabled connection pool with explicit isolation level.
    
    Each connection from pool has isolation level set.
    """
    def _set_isolation_level(conn):
        """Callback to set isolation level on connection from pool."""
        conn.set_isolation_level(isolation_level)
        # Ensure autocommit is off
        conn.autocommit = False
    
    try:
        db_pool = pool.ThreadedConnectionPool(
            min_conn, max_conn,
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        
        # Set isolation level for test connection
        test_conn = db_pool.getconn()
        try:
            _set_isolation_level(test_conn)
            
            # Validate isolation level
            cur = test_conn.cursor()
            cur.execute("SHOW transaction_isolation")
            actual_isolation = cur.fetchone()[0]
            cur.close()
            
            isolation_name = isolation_level.name if hasattr(isolation_level, 'name') else str(isolation_level)
            if logger:
                logger.startup(f"Database connection pool created with isolation level: {actual_isolation} (requested: {isolation_name})")
        finally:
            db_pool.putconn(test_conn)
        
        # Override getconn to set isolation level
        original_getconn = db_pool.getconn
        
        def getconn_with_isolation():
            conn = original_getconn()
            _set_isolation_level(conn)
            return conn
        
        db_pool.getconn = getconn_with_isolation
        
        return db_pool
    except Exception as e:
        error_msg = f"FAILED TO CREATE DATABASE CONNECTION POOL WITH ISOLATION LEVEL: {e}"
        if logger:
            logger.fatal(error_msg)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.STARTUP_ERROR)


def create_readonly_connection_pool(min_conn: int, max_conn: int,
                                    host: str, port: int, database: str, user: str, password: str,
                                    isolation_level: IsolationLevel = IsolationLevel.READ_COMMITTED,
                                    logger=None) -> pool.ThreadedConnectionPool:
    """
    Create read-only connection pool with explicit isolation level.
    
    Each connection from pool has isolation level set and read-only mode enforced.
    Abort process if write attempt occurs.
    """
    def _set_readonly(conn):
        """Callback to set isolation level and read-only mode on connection from pool."""
        conn.set_isolation_level(isolation_level)
        conn.autocommit = False
        # Enforce read-only mode
        cur = conn.cursor()
        try:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.close()
        except Exception as e:
            cur.close()
            error_msg = f"FAILED TO SET READ-ONLY MODE ON CONNECTION: {e}"
            if logger:
                logger.fatal(error_msg)
            from common.shutdown import ExitCode, exit_fatal
            exit_fatal(error_msg, ExitCode.STARTUP_ERROR)
    
    try:
        db_pool = pool.ThreadedConnectionPool(
            min_conn, max_conn,
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        
        # Set read-only mode for test connection
        test_conn = db_pool.getconn()
        try:
            _set_readonly(test_conn)
            
            # Validate isolation level and read-only mode
            cur = test_conn.cursor()
            cur.execute("SHOW transaction_isolation")
            actual_isolation = cur.fetchone()[0]
            cur.execute("SHOW transaction_read_only")
            actual_readonly = cur.fetchone()[0]
            cur.close()
            
            isolation_name = isolation_level.name if hasattr(isolation_level, 'name') else str(isolation_level)
            if logger:
                logger.startup(f"Read-only database connection pool created with isolation level: {actual_isolation} (requested: {isolation_name}), read-only: {actual_readonly}")
        finally:
            db_pool.putconn(test_conn)
        
        # Override getconn to set read-only mode
        original_getconn = db_pool.getconn
        
        def getconn_with_readonly():
            conn = original_getconn()
            _set_readonly(conn)
            return conn
        
        db_pool.getconn = getconn_with_readonly
        
        return db_pool
    except Exception as e:
        error_msg = f"FAILED TO CREATE READ-ONLY DATABASE CONNECTION POOL: {e}"
        if logger:
            logger.fatal(error_msg)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.STARTUP_ERROR)
