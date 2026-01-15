import json
from pathlib import Path

import pytest

from common.db.migration_runner import (
    MigrationRunner,
    discover_migrations,
    _compute_checksum,
    _hash_lock_id,
    _load_sql_with_includes,
)


class _Logger:
    def info(self, *args, **kwargs):
        return None


def _write_migration(dir_path: Path, version: str, name: str, direction: str, body: str):
    filename = f"migration_{version}_{name}_{direction}.sql"
    path = dir_path / filename
    path.write_text(body, encoding="utf-8")
    return path


def test_discover_migrations_orders_versions(tmp_path):
    _write_migration(tmp_path, "20260115_000001", "init_schema", "up", "SELECT 1;")
    _write_migration(tmp_path, "20260115_000001", "init_schema", "down", "SELECT 1;")
    _write_migration(tmp_path, "20260115_000002", "rbac", "up", "SELECT 1;")
    _write_migration(tmp_path, "20260115_000002", "rbac", "down", "SELECT 1;")

    migrations = discover_migrations(tmp_path)
    assert [m.version for m in migrations] == ["20260115_000001", "20260115_000002"]


def test_discover_migrations_requires_up_and_down(tmp_path):
    _write_migration(tmp_path, "20260115_000003", "missing_down", "up", "SELECT 1;")
    with pytest.raises(RuntimeError):
        discover_migrations(tmp_path)


def test_load_sql_with_includes_expands(tmp_path):
    include_path = tmp_path / "snippet.sql"
    include_path.write_text("SELECT 42;\n", encoding="utf-8")
    migration_path = tmp_path / "migration_20260115_000004_demo_up.sql"
    migration_path.write_text(
        "-- RANSOMEYE_INCLUDE: snippet.sql\nSELECT 1;\n",
        encoding="utf-8",
    )

    sql = _load_sql_with_includes(migration_path)
    assert "SELECT 42;" in sql
    assert "SELECT 1;" in sql


def test_checksum_and_lock_id_stable():
    checksum = _compute_checksum("SELECT 1;")
    assert len(checksum) == 64
    lock_id = _hash_lock_id("ransomeye_schema_migrations_v1")
    assert -(2**63) <= lock_id < 2**63


def test_validate_applied_checksums_detects_mismatch(tmp_path):
    _write_migration(tmp_path, "20260115_000005", "demo", "up", "SELECT 1;")
    _write_migration(tmp_path, "20260115_000005", "demo", "down", "SELECT 1;")
    migrations = discover_migrations(tmp_path)
    runner = MigrationRunner(tmp_path, {"host": "", "port": "0", "database": "", "user": "", "password": ""}, _Logger())
    applied = {"20260115_000005": "badchecksum"}
    with pytest.raises(RuntimeError):
        runner._validate_applied_checksums(migrations, applied)


class _FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self._rows = []
        self._fetchone = None

    def execute(self, query, params=None):
        query = " ".join(query.split())
        if query.startswith("SELECT version, checksum_sha256 FROM schema_migrations"):
            self._rows = [(v, c) for v, c in self.conn.schema_migrations.items()]
        elif query.startswith("INSERT INTO schema_migration_audit"):
            self.conn.audit_id += 1
            self._fetchone = (self.conn.audit_id,)
        elif query.startswith("INSERT INTO schema_migrations"):
            version, _, checksum, _, _ = params
            self.conn.schema_migrations[version] = checksum
        elif query.startswith("DELETE FROM schema_migrations"):
            version = params[0]
            self.conn.schema_migrations.pop(version, None)
        elif query.startswith("SELECT pg_advisory_lock") or query.startswith("SELECT pg_advisory_unlock"):
            return None
        elif query.startswith("CREATE TABLE") or query.startswith("CREATE INDEX"):
            return None
        elif query.startswith("UPDATE schema_migration_audit"):
            return None

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._fetchone

    def close(self):
        return None


class _FakeConnection:
    def __init__(self):
        self.schema_migrations = {}
        self.audit_id = 0
        self.autocommit = False

    def cursor(self):
        return _FakeCursor(self)

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return None


def test_upgrade_and_downgrade_flow(tmp_path, monkeypatch):
    _write_migration(tmp_path, "20260115_000006", "demo", "up", "SELECT 1;")
    _write_migration(tmp_path, "20260115_000006", "demo", "down", "SELECT 1;")
    runner = MigrationRunner(
        tmp_path,
        {"host": "", "port": "0", "database": "", "user": "demo", "password": "demo"},
        _Logger(),
    )

    conn = _FakeConnection()
    audit_conn = _FakeConnection()
    monkeypatch.setattr(runner, "_connect", lambda: conn)
    monkeypatch.setattr(runner, "_connect_audit", lambda: audit_conn)

    applied = runner.upgrade()
    assert applied == 1
    assert "20260115_000006" in conn.schema_migrations

    rolled_back = runner.downgrade(target_version="0")
    assert rolled_back == 1
    assert "20260115_000006" not in conn.schema_migrations
