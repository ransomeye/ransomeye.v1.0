#!/usr/bin/env python3
"""
Validation harness pytest fixtures.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict
from urllib.parse import urlparse

import psycopg2
import pytest

from common.db.migration_runner import MigrationRunner
from common.logging import setup_logging


def _parse_db_url(db_url: str) -> Dict[str, str]:
    parsed = urlparse(db_url)
    if parsed.scheme not in ("postgres", "postgresql"):
        raise ValueError(f"Unsupported database URL scheme: {parsed.scheme}")
    if not parsed.path or parsed.path == "/":
        raise ValueError("Database name is required in test DB URL")

    return {
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "database": parsed.path.lstrip("/"),
        "user": parsed.username or "",
        "password": parsed.password or "",
    }


@pytest.fixture(scope="session")
def test_db_url() -> str:
    db_user = os.getenv("RANSOMEYE_DB_USER", "gagan")
    db_password = os.getenv("RANSOMEYE_DB_PASSWORD", "gagan")
    db_host = os.getenv("RANSOMEYE_DB_HOST", "localhost")
    db_port = os.getenv("RANSOMEYE_DB_PORT", "5432")
    db_name = os.getenv("RANSOMEYE_DB_NAME", "ransomeye_test")
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


@pytest.fixture(scope="function")
def executor(test_db_url: str):
    db_config = _parse_db_url(test_db_url)
    if not db_config["user"] or not db_config["password"]:
        raise ValueError("Database user and password are required for migration tests")

    migrations_env = os.getenv("RANSOMEYE_SCHEMA_MIGRATIONS_DIR")
    migrations_dir = Path(migrations_env) if migrations_env else Path(__file__).parent.parent.parent / "schemas" / "migrations"
    logger = setup_logging("migration-tests")
    runner = MigrationRunner(migrations_dir, db_config, logger)
    yield runner


@pytest.fixture(scope="function")
def conn(test_db_url: str):
    connection = psycopg2.connect(test_db_url)
    yield connection
    connection.close()
