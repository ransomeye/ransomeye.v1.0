"""
FAMILY-6 GROUP B: Core Runtime Database Initialization Failure Tests
Tests for database connection and initialization failure branches.
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault(
    "RANSOMEYE_EVENT_ENVELOPE_SCHEMA_PATH",
    str(_REPO_ROOT / "contracts" / "event-envelope.schema.json"),
)
os.environ.setdefault("RANSOMEYE_LOG_DIR", "/tmp")
os.environ.setdefault("RANSOMEYE_DB_PASSWORD", "bootstrap-password-12345")
os.environ.setdefault("RANSOMEYE_DB_USER", "bootstrap_user")
os.environ.setdefault(
    "RANSOMEYE_COMMAND_SIGNING_KEY",
    "bootstrap-signing-key-1234567890-abcdef-XYZ-9876543210",
)

from core import runtime


def _assert_hit_marker(capsys, marker):
    err = capsys.readouterr().err
    assert f"HIT_BRANCH: {marker}" in err


def test_db_conn_refused(monkeypatch, capsys):
    """GROUP B1: Test DB connection refused failure."""
    # Mock psycopg2.connect to raise OperationalError for connection refused
    def connection_refused_error(*args, **kwargs):
        error = runtime.psycopg2.OperationalError("could not connect to server: Connection refused")
        raise error
    
    monkeypatch.setattr(runtime.psycopg2, "connect", connection_refused_error)
    
    # Call _validate_db_connectivity() directly - it should exit
    with pytest.raises(SystemExit):
        runtime._validate_db_connectivity()
    
    _assert_hit_marker(capsys, "db_conn_refused")


def test_db_auth_failed(monkeypatch, capsys):
    """GROUP B2: Test DB authentication failure."""
    # Mock psycopg2.connect to raise OperationalError for auth failure
    def auth_failed_error(*args, **kwargs):
        error = runtime.psycopg2.OperationalError("password authentication failed for user")
        raise error
    
    monkeypatch.setattr(runtime.psycopg2, "connect", auth_failed_error)
    
    # Call _validate_db_connectivity() directly - it should exit
    with pytest.raises(SystemExit):
        runtime._validate_db_connectivity()
    
    _assert_hit_marker(capsys, "db_auth_failed")


def test_db_schema_version_mismatch(monkeypatch, capsys, tmp_path):
    """GROUP B3: Test DB schema version mismatch."""
    # Create a migrations directory
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    
    # Mock get_latest_migration_version to return expected version
    call_count = {"count": 0}
    def mock_get_version(path):
        return "20250117_120000"  # Expected version
    
    # Mock DB connection and cursor to return different current version
    class FakeCursor:
        def __init__(self):
            self._call_count = 0
        
        def execute(self, query):
            self._query = query
        
        def fetchone(self):
            self._call_count += 1
            if "to_regclass" in str(self._query):
                return ["schema_migrations"]  # Table exists
            else:  # SELECT version FROM schema_migrations
                return ["20250116_120000"]  # Different version - MISMATCH
        
        def close(self):
            pass
    
    class FakeConn:
        def cursor(self):
            return FakeCursor()
        def close(self):
            pass
    
    def fake_connect(*args, **kwargs):
        return FakeConn()
    
    monkeypatch.setenv("RANSOMEYE_SCHEMA_MIGRATIONS_DIR", str(migrations_dir))
    monkeypatch.setattr(runtime.psycopg2, "connect", fake_connect)
    
    with patch("common.db.migration_runner.get_latest_migration_version", mock_get_version):
        # Call _validate_schema_version() directly - it should exit
        with pytest.raises(SystemExit):
            runtime._validate_schema_version()
    
    _assert_hit_marker(capsys, "schema_version_mismatch")


def test_migration_dir_missing(monkeypatch, capsys, tmp_path):
    """GROUP B4: Test migration directory missing."""
    # Set migrations directory to non-existent path
    non_existent_dir = tmp_path / "nonexistent_migrations"
    monkeypatch.setenv("RANSOMEYE_SCHEMA_MIGRATIONS_DIR", str(non_existent_dir))
    
    # Call _validate_schema_version() directly - it should exit
    with pytest.raises(SystemExit):
        runtime._validate_schema_version()
    
    _assert_hit_marker(capsys, "migrations_dir_missing")


def test_migration_checksum_mismatch(monkeypatch, capsys, tmp_path):
    """GROUP B5: Test migration checksum mismatch."""
    # Create migrations directory
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    
    # Mock migration discovery
    class MockMigration:
        def __init__(self, version):
            self.version = version
            self.up_path = migrations_dir / f"{version}_up.sql"
            self.up_path.write_text("CREATE TABLE test;", encoding="utf-8")
    
    def mock_discover_migrations(path):
        return [MockMigration("20250117_120000")]
    
    def mock_compute_checksum(sql_text):
        return "computed_checksum_abc123"  # Different from stored
    
    # Mock DB connection and cursor
    class FakeCursor:
        def __init__(self):
            self._call_count = 0
        
        def execute(self, query):
            self._query = query
        
        def fetchone(self):
            self._call_count += 1
            if "to_regclass" in str(self._query):
                return ["schema_migrations"]
            elif "version DESC LIMIT 1" in str(self._query):
                return ["20250117_120000"]  # Current version matches expected
            elif "checksum_sha256" in str(self._query):
                # Return stored checksum that doesn't match computed
                return [("20250117_120000", "stored_checksum_xyz789")]
            return None
        
        def fetchall(self):
            if "checksum_sha256" in str(self._query):
                return [("20250117_120000", "stored_checksum_xyz789")]
            return []
        
        def close(self):
            pass
    
    class FakeConn:
        def cursor(self):
            return FakeCursor()
        def close(self):
            pass
    
    def fake_connect(*args, **kwargs):
        return FakeConn()
    
    def mock_get_version(path):
        return "20250117_120000"
    
    monkeypatch.setenv("RANSOMEYE_SCHEMA_MIGRATIONS_DIR", str(migrations_dir))
    monkeypatch.setattr(runtime.psycopg2, "connect", fake_connect)
    
    with patch("common.db.migration_runner.get_latest_migration_version", mock_get_version), \
         patch("common.db.migration_runner.discover_migrations", mock_discover_migrations), \
         patch("common.db.migration_runner._compute_checksum", mock_compute_checksum):
        # Call _validate_schema_version() directly - it should exit
        with pytest.raises(SystemExit):
            runtime._validate_schema_version()
    
    _assert_hit_marker(capsys, "migration_checksum_mismatch")


def test_migration_partial_apply(monkeypatch, capsys, tmp_path):
    """GROUP B6: Test partial migration detected."""
    # Create migrations directory
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    
    # Mock migration discovery - multiple migrations
    class MockMigration:
        def __init__(self, version):
            self.version = version
            self.up_path = migrations_dir / f"{version}_up.sql"
            self.up_path.write_text(f"CREATE TABLE test_{version};", encoding="utf-8")
    
    def mock_discover_migrations(path):
        return [
            MockMigration("20250117_100000"),
            MockMigration("20250117_120000"),
            MockMigration("20250117_140000"),
        ]
    
    # Mock checksum to return same value for all - so B5 doesn't fire
    def mock_compute_checksum(sql_text):
        return "matching_checksum_same_for_all"
    
    # Mock DB connection and cursor - return fewer applied than expected
    class FakeCursor:
        def __init__(self):
            self._call_count = 0
        
        def execute(self, query):
            self._query = query
        
        def fetchone(self):
            self._call_count += 1
            if "to_regclass" in str(self._query):
                return ["schema_migrations"]
            elif "version DESC LIMIT 1" in str(self._query):
                return ["20250117_140000"]  # Latest version matches expected
            return None
        
        def fetchall(self):
            if "checksum_sha256" in str(self._query):
                # Return matching checksums (so B5 doesn't fire) for only 2 migrations (partial)
                return [
                    ("20250117_100000", "matching_checksum_same_for_all"),
                    ("20250117_140000", "matching_checksum_same_for_all"),
                ]
            elif "ORDER BY version" in str(self._query) and "checksum" not in str(self._query):
                # Return only 2 applied versions (partial - missing middle one)
                return [("20250117_100000",), ("20250117_140000",)]
            return []
        
        def close(self):
            pass
    
    class FakeConn:
        def cursor(self):
            return FakeCursor()
        def close(self):
            pass
    
    def fake_connect(*args, **kwargs):
        return FakeConn()
    
    def mock_get_version(path):
        return "20250117_140000"
    
    monkeypatch.setenv("RANSOMEYE_SCHEMA_MIGRATIONS_DIR", str(migrations_dir))
    monkeypatch.setattr(runtime.psycopg2, "connect", fake_connect)
    
    with patch("common.db.migration_runner.get_latest_migration_version", mock_get_version), \
         patch("common.db.migration_runner.discover_migrations", mock_discover_migrations), \
         patch("common.db.migration_runner._compute_checksum", mock_compute_checksum):
        # Call _validate_schema_version() directly - it should exit
        with pytest.raises(SystemExit):
            runtime._validate_schema_version()
    
    _assert_hit_marker(capsys, "migration_partial_apply")
