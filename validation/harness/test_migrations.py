#!/usr/bin/env python3
"""
RansomEye v1.0 Validation Harness - Migration Tests
AUTHORITATIVE: Phase 1 schema lifecycle validation
"""

import os
from pathlib import Path
from typing import Any, Dict

from validation.harness.phase_c_executor import ValidationStatus


def _get_migrations_dir() -> Path:
    project_root = Path(__file__).parent.parent.parent
    env_dir = os.getenv("RANSOMEYE_SCHEMA_MIGRATIONS_DIR")
    return Path(env_dir) if env_dir else project_root / "schemas" / "migrations"


def _get_current_schema_version(conn) -> str:
    cur = conn.cursor()
    try:
        cur.execute("SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1")
        row = cur.fetchone()
        return row[0] if row else ""
    finally:
        cur.close()


def _run_mig_001_fresh_install(executor, conn) -> Dict[str, Any]:
    """
    MIG-001: Fresh install migration applies from base.
    """
    executor.downgrade(target_version="0")
    executor.upgrade()
    
    migrations_dir = _get_migrations_dir()
    from common.db.migration_runner import get_latest_migration_version
    expected_version = get_latest_migration_version(migrations_dir)
    current_version = _get_current_schema_version(conn)
    
    cur = conn.cursor()
    try:
        cur.execute("SELECT to_regclass('public.machines')")
        machines_exists = cur.fetchone()[0] is not None
    finally:
        cur.close()
    
    passed = (expected_version == current_version) and machines_exists
    return {
        "status": ValidationStatus.PASSED.value if passed else ValidationStatus.FAILED.value,
        "expected_version": expected_version,
        "current_version": current_version,
        "machines_table_exists": machines_exists
    }


def test_mig_001_fresh_install(executor, conn) -> None:
    result = _run_mig_001_fresh_install(executor, conn)
    assert result["status"] == ValidationStatus.PASSED.value, result


def _run_mig_002_upgrade_idempotent(executor, conn) -> Dict[str, Any]:
    """
    MIG-002: Upgrade is idempotent (no-op when already applied).
    """
    applied = executor.upgrade()
    current_version = _get_current_schema_version(conn)
    
    passed = applied == 0 and bool(current_version)
    return {
        "status": ValidationStatus.PASSED.value if passed else ValidationStatus.FAILED.value,
        "applied_count": applied,
        "current_version": current_version
    }


def test_mig_002_upgrade_idempotent(executor, conn) -> None:
    result = _run_mig_002_upgrade_idempotent(executor, conn)
    assert result["status"] == ValidationStatus.PASSED.value, result


def _run_mig_003_rollback_and_reapply(executor, conn) -> Dict[str, Any]:
    """
    MIG-003: Rollback removes schema objects and reapply restores them.
    """
    executor.downgrade(target_version="0")
    
    cur = conn.cursor()
    try:
        cur.execute("SELECT to_regclass('public.machines')")
        machines_exists_after = cur.fetchone()[0] is not None
    finally:
        cur.close()
    
    executor.upgrade()
    cur = conn.cursor()
    try:
        cur.execute("SELECT to_regclass('public.machines')")
        machines_exists_reapplied = cur.fetchone()[0] is not None
    finally:
        cur.close()
    
    passed = (not machines_exists_after) and machines_exists_reapplied
    return {
        "status": ValidationStatus.PASSED.value if passed else ValidationStatus.FAILED.value,
        "machines_exists_after_rollback": machines_exists_after,
        "machines_exists_after_reapply": machines_exists_reapplied
    }


def test_mig_003_rollback_and_reapply(executor, conn) -> None:
    result = _run_mig_003_rollback_and_reapply(executor, conn)
    assert result["status"] == ValidationStatus.PASSED.value, result
