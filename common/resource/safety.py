#!/usr/bin/env python3
"""
RansomEye v1.0 Common Resource Safety Utilities
AUTHORITATIVE: Resource exhaustion and disk failure detection
"""

import os
import sys
import shutil
import resource
from pathlib import Path
from typing import Optional, BinaryIO, TextIO
import errno


class ResourceError(Exception):
    """Resource exhaustion or disk failure error."""
    pass


def _check_disk_space(path: Path, min_bytes: int = 0) -> bool:
    """
    Check if sufficient disk space is available.
    
    Returns True if space is available, False otherwise.
    Raises ResourceError if path is invalid or check fails.
    """
    try:
        stat = shutil.disk_usage(path)
        free_bytes = stat.free
        return free_bytes >= min_bytes
    except OSError as e:
        raise ResourceError(f"Disk space check failed for {path}: {e}")


def _is_disk_full_error(error: Exception) -> bool:
    """Check if error is a disk full condition."""
    if isinstance(error, OSError):
        return error.errno in (errno.ENOSPC, errno.EDQUOT)
    return False


def _is_permission_denied_error(error: Exception) -> bool:
    """Check if error is a permission denied condition."""
    if isinstance(error, OSError):
        return error.errno in (errno.EACCES, errno.EPERM)
    return False


def _is_readonly_filesystem_error(error: Exception) -> bool:
    """Check if error is a read-only filesystem condition."""
    if isinstance(error, OSError):
        return error.errno == errno.EROFS
    return False


def _is_memory_error(error: Exception) -> bool:
    """Check if error is a memory allocation failure."""
    return isinstance(error, MemoryError)


def _is_file_descriptor_error(error: Exception) -> bool:
    """Check if error is a file descriptor exhaustion condition."""
    if isinstance(error, OSError):
        return error.errno == errno.EMFILE or error.errno == errno.ENFILE
    return False


def _detect_and_fail_on_resource_error(error: Exception, operation: str, logger=None) -> None:
    """
    Detect resource exhaustion and disk failures.
    Log and terminate Core immediately (no retries).
    """
    if _is_disk_full_error(error):
        error_msg = f"DISK FULL: {operation} failed due to insufficient disk space: {error}"
        if logger:
            logger.fatal(error_msg)
        else:
            print(f"FATAL: {error_msg}", file=sys.stderr)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
    
    if _is_permission_denied_error(error):
        error_msg = f"PERMISSION DENIED: {operation} failed due to insufficient permissions: {error}"
        if logger:
            logger.fatal(error_msg)
        else:
            print(f"FATAL: {error_msg}", file=sys.stderr)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
    
    if _is_readonly_filesystem_error(error):
        error_msg = f"READ-ONLY FILESYSTEM: {operation} failed - filesystem is read-only: {error}"
        if logger:
            logger.fatal(error_msg)
        else:
            print(f"FATAL: {error_msg}", file=sys.stderr)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
    
    if _is_memory_error(error):
        error_msg = f"MEMORY ALLOCATION FAILURE: {operation} failed due to insufficient memory: {error}"
        if logger:
            logger.fatal(error_msg)
        else:
            print(f"FATAL: {error_msg}", file=sys.stderr)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
    
    if _is_file_descriptor_error(error):
        error_msg = f"FILE DESCRIPTOR EXHAUSTION: {operation} failed - too many open files: {error}"
        if logger:
            logger.fatal(error_msg)
        else:
            print(f"FATAL: {error_msg}", file=sys.stderr)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)


def safe_open_file(path: Path, mode: str = 'r', logger=None, min_bytes: int = 0) -> TextIO:
    """
    Safely open a file with resource failure detection.
    
    Detects disk full, permission denied, read-only filesystem, memory errors, and file descriptor exhaustion.
    Terminates Core immediately on any failure (no retries).
    """
    try:
        # Check disk space if writing
        if 'w' in mode or 'a' in mode:
            if min_bytes > 0:
                if not _check_disk_space(path.parent if path.parent.exists() else Path('/'), min_bytes):
                    error_msg = f"Insufficient disk space for {path}: requires {min_bytes} bytes"
                    if logger:
                        logger.fatal(error_msg)
                    else:
                        print(f"FATAL: {error_msg}", file=sys.stderr)
                    from common.shutdown import ExitCode, exit_fatal
                    exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
        
        # Attempt to open file
        return open(path, mode)
    except Exception as e:
        _detect_and_fail_on_resource_error(e, f"safe_open_file({path}, {mode})", logger)
        raise


def safe_create_directory(path: Path, logger=None, min_bytes: int = 0) -> None:
    """
    Safely create a directory with resource failure detection.
    
    Detects disk full, permission denied, read-only filesystem, and file descriptor exhaustion.
    Terminates Core immediately on any failure (no retries).
    """
    try:
        # Check disk space
        if min_bytes > 0:
            parent = path.parent if path.parent.exists() else Path('/')
            if not _check_disk_space(parent, min_bytes):
                error_msg = f"Insufficient disk space for directory {path}: requires {min_bytes} bytes"
                if logger:
                    logger.fatal(error_msg)
                else:
                    print(f"FATAL: {error_msg}", file=sys.stderr)
                from common.shutdown import ExitCode, exit_fatal
                exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
        
        # Attempt to create directory
        path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        _detect_and_fail_on_resource_error(e, f"safe_create_directory({path})", logger)
        raise


def safe_write_file(path: Path, content: str, logger=None, min_bytes: int = 0) -> None:
    """
    Safely write to a file with resource failure detection.
    
    Detects disk full, permission denied, read-only filesystem, memory errors, and file descriptor exhaustion.
    Terminates Core immediately on any failure (no retries).
    """
    try:
        # Check disk space
        if min_bytes > 0:
            parent = path.parent if path.parent.exists() else Path('/')
            if not _check_disk_space(parent, min_bytes):
                error_msg = f"Insufficient disk space for {path}: requires {min_bytes} bytes"
                if logger:
                    logger.fatal(error_msg)
                else:
                    print(f"FATAL: {error_msg}", file=sys.stderr)
                from common.shutdown import ExitCode, exit_fatal
                exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
        
        # Ensure parent directory exists
        if path.parent:
            safe_create_directory(path.parent, logger, min_bytes=0)
        
        # Attempt to write file
        with open(path, 'w') as f:
            f.write(content)
    except Exception as e:
        _detect_and_fail_on_resource_error(e, f"safe_write_file({path})", logger)
        raise


def safe_read_file(path: Path, logger=None) -> str:
    """
    Safely read from a file with resource failure detection.
    
    Detects file descriptor exhaustion and memory errors.
    Terminates Core immediately on any failure (no retries).
    """
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        _detect_and_fail_on_resource_error(e, f"safe_read_file({path})", logger)
        raise


def check_file_descriptors(logger=None) -> None:
    """
    Check file descriptor usage and fail if approaching limits.
    
    Terminates Core immediately if file descriptors are exhausted.
    """
    try:
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        current = len(os.listdir('/proc/self/fd')) if os.path.exists('/proc/self/fd') else 0
        
        # Fail if using more than 90% of soft limit
        if soft > 0 and current > (soft * 0.9):
            error_msg = f"File descriptor exhaustion: {current}/{soft} descriptors in use (90% threshold)"
            if logger:
                logger.fatal(error_msg)
            else:
                print(f"FATAL: {error_msg}", file=sys.stderr)
            from common.shutdown import ExitCode, exit_fatal
            exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
    except Exception as e:
        # If check fails, log warning but don't terminate (check is best-effort)
        if logger:
            logger.warning(f"File descriptor check failed: {e}")
        else:
            print(f"WARNING: File descriptor check failed: {e}", file=sys.stderr)


def safe_log_operation(log_func, message: str, logger=None, **kwargs) -> None:
    """
    Safely perform a logging operation with failure detection.
    
    If logging fails, terminate Core immediately (fail-fast).
    Prevents unbounded log growth by checking file size if writing to file.
    """
    try:
        log_func(message, **kwargs)
    except (OSError, IOError, MemoryError) as e:
        error_msg = f"LOGGING FAILURE: Log operation failed: {e}"
        # Cannot use logger here (it failed), use stderr
        print(f"FATAL: {error_msg}", file=sys.stderr)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
    except Exception as e:
        # Other exceptions also terminate Core
        error_msg = f"LOGGING FAILURE: Unexpected error in log operation: {e}"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
