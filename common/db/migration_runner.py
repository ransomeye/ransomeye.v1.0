#!/usr/bin/env python3
"""
RansomEye v1.0 Migration Runner
AUTHORITATIVE: Production-grade schema lifecycle manager (Phase 1)
"""

import argparse
import hashlib
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import psycopg2

try:
    from common.logging import setup_logging
    from common.shutdown import ExitCode, exit_fatal
    _common_logging_available = True
except Exception:
    _common_logging_available = False
    class _FallbackLogger:
        def info(self, msg, **kwargs): print(msg)
        def error(self, msg, **kwargs): print(msg, file=sys.stderr)
        def fatal(self, msg, **kwargs): print(f"FATAL: {msg}", file=sys.stderr)
        def startup(self, msg, **kwargs): print(f"STARTUP: {msg}")
    def setup_logging(name, **kwargs):
        return _FallbackLogger()
    class ExitCode:
        SUCCESS = 0
        STARTUP_ERROR = 2
        RUNTIME_ERROR = 3
        FATAL_ERROR = 4
    def exit_fatal(msg, code=ExitCode.FATAL_ERROR):
        print(f"FATAL: {msg}", file=sys.stderr)
        sys.exit(int(code))


RUNNER_VERSION = "1.0.0"
MIGRATION_FILENAME_RE = re.compile(r"^migration_(\d{8}_\d{6})_(.+)_(up|down)\.sql$")
ADVISORY_LOCK_SEED = "ransomeye_schema_migrations_v1"


@dataclass(frozen=True)
class Migration:
    version: str
    description: str
    up_path: Path
    down_path: Path


def _hash_lock_id(seed: str) -> int:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    value = int(digest, 16)
    if value >= 2**63:
        value -= 2**64
    return value


def _compute_checksum(sql_text: str) -> str:
    return hashlib.sha256(sql_text.encode("utf-8")).hexdigest()


def _load_sql_with_includes(migration_path: Path) -> str:
    """
    Load SQL with support for include directives:
    -- RANSOMEYE_INCLUDE: relative/path.sql
    """
    base_dir = migration_path.parent
    sql_lines: List[str] = []
    with migration_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip().startswith("-- RANSOMEYE_INCLUDE:"):
                include_path = line.split(":", 1)[1].strip()
                include_file = (base_dir / include_path).resolve()
                if not include_file.exists():
                    raise FileNotFoundError(f"Include file not found: {include_file}")
                sql_lines.append(f"-- BEGIN INCLUDE {include_file}\n")
                sql_lines.append(include_file.read_text(encoding="utf-8"))
                if not sql_lines[-1].endswith("\n"):
                    sql_lines.append("\n")
                sql_lines.append(f"-- END INCLUDE {include_file}\n")
            else:
                sql_lines.append(line)
    return "".join(sql_lines)


def discover_migrations(migrations_dir: Path) -> List[Migration]:
    if not migrations_dir.exists():
        raise FileNotFoundError(f"Migrations directory not found: {migrations_dir}")

    migration_map: Dict[str, Dict[str, Path]] = {}
    descriptions: Dict[str, str] = {}

    for file_path in migrations_dir.iterdir():
        if not file_path.is_file():
            continue
        match = MIGRATION_FILENAME_RE.match(file_path.name)
        if not match:
            continue
        version, raw_description, direction = match.groups()
        description = raw_description.replace("_", " ").strip()
        if version not in migration_map:
            migration_map[version] = {}
            descriptions[version] = description
        migration_map[version][direction] = file_path

    migrations: List[Migration] = []
    for version, paths in migration_map.items():
        if "up" not in paths or "down" not in paths:
            raise RuntimeError(f"Migration {version} missing up/down SQL file")
        migrations.append(
            Migration(
                version=version,
                description=descriptions[version],
                up_path=paths["up"],
                down_path=paths["down"],
            )
        )

    migrations.sort(key=lambda m: m.version)
    return migrations


def get_latest_migration_version(migrations_dir: Path) -> Optional[str]:
    migrations = discover_migrations(migrations_dir)
    if not migrations:
        return None
    return migrations[-1].version


class MigrationRunner:
    def __init__(self, migrations_dir: Path, db_config: Dict[str, str], logger):
        self.migrations_dir = migrations_dir
        self.db_config = db_config
        self.logger = logger
        self.lock_id = _hash_lock_id(ADVISORY_LOCK_SEED)

    def _connect(self):
        return psycopg2.connect(
            host=self.db_config["host"],
            port=int(self.db_config["port"]),
            database=self.db_config["database"],
            user=self.db_config["user"],
            password=self.db_config["password"],
        )

    def _connect_audit(self):
        conn = self._connect()
        conn.autocommit = True
        return conn

    def _applied_by(self) -> str:
        return f"{self.db_config['user']}@{self.db_config['host']}"

    def _ensure_schema_tables(self, conn) -> None:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(32) PRIMARY KEY,
                    description TEXT NOT NULL,
                    checksum_sha256 CHAR(64) NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    applied_by TEXT NOT NULL,
                    execution_time_ms INTEGER NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migration_audit (
                    id BIGSERIAL PRIMARY KEY,
                    version VARCHAR(32) NOT NULL,
                    description TEXT NOT NULL,
                    checksum_sha256 CHAR(64) NOT NULL,
                    started_at TIMESTAMPTZ NOT NULL,
                    finished_at TIMESTAMPTZ,
                    success BOOLEAN NOT NULL DEFAULT FALSE,
                    error_message TEXT,
                    applied_by TEXT NOT NULL,
                    execution_time_ms INTEGER,
                    runner_version TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_schema_migration_audit_version
                ON schema_migration_audit(version)
                """
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    def _acquire_lock(self, conn) -> None:
        cur = conn.cursor()
        try:
            cur.execute("SELECT pg_advisory_lock(%s)", (self.lock_id,))
        finally:
            cur.close()

    def _release_lock(self, conn) -> None:
        cur = conn.cursor()
        try:
            cur.execute("SELECT pg_advisory_unlock(%s)", (self.lock_id,))
        finally:
            cur.close()

    def _get_applied_migrations(self, conn) -> Dict[str, str]:
        cur = conn.cursor()
        try:
            cur.execute("SELECT version, checksum_sha256 FROM schema_migrations ORDER BY version")
            return {row[0]: row[1] for row in cur.fetchall()}
        finally:
            cur.close()

    def _insert_audit_start(self, conn, migration: Migration, checksum: str) -> int:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO schema_migration_audit (
                version, description, checksum_sha256, started_at,
                applied_by, runner_version
            )
            VALUES (%s, %s, %s, NOW(), %s, %s)
            RETURNING id
            """,
            (migration.version, migration.description, checksum, self._applied_by(), RUNNER_VERSION),
        )
        audit_id = cur.fetchone()[0]
        cur.close()
        return audit_id

    def _update_audit(self, conn, audit_id: int, success: bool,
                      execution_time_ms: Optional[int], error_message: Optional[str]) -> None:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE schema_migration_audit
            SET finished_at = NOW(),
                success = %s,
                execution_time_ms = %s,
                error_message = %s
            WHERE id = %s
            """,
            (success, execution_time_ms, error_message, audit_id),
        )
        cur.close()

    def _validate_applied_checksums(self, migrations: List[Migration], applied: Dict[str, str]) -> None:
        for migration in migrations:
            if migration.version in applied:
                sql_text = _load_sql_with_includes(migration.up_path)
                checksum = _compute_checksum(sql_text)
                if applied[migration.version] != checksum:
                    raise RuntimeError(
                        f"Checksum mismatch for migration {migration.version}: "
                        f"database={applied[migration.version]} file={checksum}"
                    )

    def upgrade(self, target_version: Optional[str] = None) -> int:
        migrations = discover_migrations(self.migrations_dir)
        if not migrations:
            self.logger.info("No migrations found; nothing to apply")
            return 0

        conn = self._connect()
        audit_conn = self._connect_audit()
        applied_count = 0
        try:
            self._acquire_lock(conn)
            self._ensure_schema_tables(conn)
            applied = self._get_applied_migrations(conn)
            self._validate_applied_checksums(migrations, applied)

            for migration in migrations:
                if target_version and migration.version > target_version:
                    break
                if migration.version in applied:
                    continue

                sql_text = _load_sql_with_includes(migration.up_path)
                checksum = _compute_checksum(sql_text)
                audit_id = self._insert_audit_start(audit_conn, migration, checksum)
                start = time.time()
                try:
                    cur = conn.cursor()
                    cur.execute(sql_text)
                    execution_time_ms = int((time.time() - start) * 1000)
                    cur.execute(
                        """
                        INSERT INTO schema_migrations (
                            version, description, checksum_sha256,
                            applied_at, applied_by, execution_time_ms
                        )
                        VALUES (%s, %s, %s, NOW(), %s, %s)
                        """,
                        (
                            migration.version,
                            migration.description,
                            checksum,
                            self._applied_by(),
                            execution_time_ms,
                        ),
                    )
                    cur.close()
                    conn.commit()
                    self._update_audit(audit_conn, audit_id, True, execution_time_ms, None)
                    applied_count += 1
                    self.logger.info(
                        f"Applied migration {migration.version} ({migration.description})"
                    )
                except Exception as exc:
                    conn.rollback()
                    execution_time_ms = int((time.time() - start) * 1000)
                    self._update_audit(audit_conn, audit_id, False, execution_time_ms, str(exc))
                    raise
        finally:
            try:
                self._release_lock(conn)
            except Exception:
                pass
            conn.close()
            audit_conn.close()

        return applied_count

    def downgrade(self, target_version: Optional[str]) -> int:
        migrations = discover_migrations(self.migrations_dir)
        if not migrations:
            self.logger.info("No migrations found; nothing to rollback")
            return 0

        conn = self._connect()
        audit_conn = self._connect_audit()
        rolled_back = 0
        try:
            self._acquire_lock(conn)
            self._ensure_schema_tables(conn)
            applied = self._get_applied_migrations(conn)
            self._validate_applied_checksums(migrations, applied)

            applied_versions = [m for m in migrations if m.version in applied]
            applied_versions.sort(key=lambda m: m.version, reverse=True)

            for migration in applied_versions:
                if target_version and migration.version <= target_version:
                    break

                sql_text = _load_sql_with_includes(migration.down_path)
                checksum = _compute_checksum(sql_text)
                audit_id = self._insert_audit_start(audit_conn, migration, checksum)
                start = time.time()
                try:
                    cur = conn.cursor()
                    cur.execute(sql_text)
                    execution_time_ms = int((time.time() - start) * 1000)
                    cur.execute(
                        "DELETE FROM schema_migrations WHERE version = %s",
                        (migration.version,),
                    )
                    cur.close()
                    conn.commit()
                    self._update_audit(audit_conn, audit_id, True, execution_time_ms, None)
                    rolled_back += 1
                    self.logger.info(
                        f"Rolled back migration {migration.version} ({migration.description})"
                    )
                except Exception as exc:
                    conn.rollback()
                    execution_time_ms = int((time.time() - start) * 1000)
                    self._update_audit(audit_conn, audit_id, False, execution_time_ms, str(exc))
                    raise
        finally:
            try:
                self._release_lock(conn)
            except Exception:
                pass
            conn.close()
            audit_conn.close()

        return rolled_back


def _load_db_config_from_env() -> Dict[str, str]:
    db_user = os.getenv("RANSOMEYE_DB_USER")
    db_password = os.getenv("RANSOMEYE_DB_PASSWORD")
    if not db_user:
        exit_fatal("RANSOMEYE_DB_USER is required for migrations", ExitCode.STARTUP_ERROR)
    if not db_password:
        exit_fatal("RANSOMEYE_DB_PASSWORD is required for migrations", ExitCode.STARTUP_ERROR)

    return {
        "host": os.getenv("RANSOMEYE_DB_HOST", "localhost"),
        "port": os.getenv("RANSOMEYE_DB_PORT", "5432"),
        "database": os.getenv("RANSOMEYE_DB_NAME", "ransomeye"),
        "user": db_user,
        "password": db_password,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="RansomEye schema migration runner")
    parser.add_argument(
        "command",
        choices=["upgrade", "downgrade"],
        nargs="?",
        default="upgrade",
        help="Migration command (default: upgrade)",
    )
    parser.add_argument(
        "--migrations-dir",
        default=os.getenv("RANSOMEYE_SCHEMA_MIGRATIONS_DIR", ""),
        help="Path to migrations directory",
    )
    parser.add_argument(
        "--target-version",
        default=None,
        help="Target migration version (inclusive for upgrade, exclusive for downgrade)",
    )
    args = parser.parse_args()

    migrations_dir = Path(args.migrations_dir).resolve()
    if not migrations_dir.exists():
        exit_fatal(f"Migrations directory not found: {migrations_dir}", ExitCode.STARTUP_ERROR)

    logger = setup_logging("schema-migrations")
    db_config = _load_db_config_from_env()
    runner = MigrationRunner(migrations_dir, db_config, logger)

    try:
        if args.command == "upgrade":
            applied = runner.upgrade(target_version=args.target_version)
            logger.startup(f"Migration upgrade complete (applied: {applied})")
        elif args.command == "downgrade":
            target = args.target_version
            rolled_back = runner.downgrade(target_version=target)
            logger.startup(f"Migration downgrade complete (rolled back: {rolled_back})")
        sys.exit(ExitCode.SUCCESS)
    except Exception as exc:
        logger.fatal(f"Migration failed: {exc}")
        exit_fatal(f"Migration failed: {exc}", ExitCode.RUNTIME_ERROR)


if __name__ == "__main__":
    main()
