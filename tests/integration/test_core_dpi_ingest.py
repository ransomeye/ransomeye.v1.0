import os
import signal
import socket
import subprocess
import tempfile
import time
from pathlib import Path

import psycopg2

from common.db.migration_runner import MigrationRunner


PROJECT_ROOT = Path(__file__).parent.parent.parent


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    _, port = sock.getsockname()
    sock.close()
    return port


def _generate_service_keys(key_dir: Path) -> None:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization

    key_dir.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    (key_dir / "ingest.key").write_bytes(private_key_bytes)
    (key_dir / "ingest.pub").write_bytes(public_key_bytes)


def _apply_migrations() -> None:
    migrations_dir = PROJECT_ROOT / "schemas" / "migrations"
    runner = MigrationRunner(
        migrations_dir=migrations_dir,
        db_config={
            "host": os.getenv("RANSOMEYE_DB_HOST", "localhost"),
            "port": os.getenv("RANSOMEYE_DB_PORT", "5432"),
            "database": os.getenv("RANSOMEYE_DB_NAME", "ransomeye"),
            "user": os.getenv("RANSOMEYE_DB_USER"),
            "password": os.getenv("RANSOMEYE_DB_PASSWORD"),
        },
        logger=type("Logger", (), {"info": lambda *a, **k: None})(),
    )
    runner.upgrade()


def _start_core(env: dict) -> subprocess.Popen:
    core_main = PROJECT_ROOT / "core" / "main.py"
    python_bin = env.get("PYTHON") or os.environ.get("PYTHON", "python3")
    return subprocess.Popen([python_bin, str(core_main)], env=env)


def test_core_dpi_ingest_pipeline():
    _apply_migrations()
    temp_dir = Path(tempfile.mkdtemp(prefix="ransomeye-core-dpi-"))
    status_path = temp_dir / "core_status.json"
    service_key_dir = temp_dir / "service-keys"
    component_key_dir = temp_dir / "component-keys"
    _generate_service_keys(service_key_dir)

    ui_port = _free_port()
    ingest_port = _free_port()
    python_bin = str(PROJECT_ROOT / ".venv" / "bin" / "python")
    coverage_config = str(PROJECT_ROOT / ".coveragerc")
    env = os.environ.copy()
    env.update(
        {
            "CI": "true",
            "RANSOMEYE_ENV": "ci",
            "PYTHON": python_bin,
            "RANSOMEYE_PYTHON_BIN": python_bin,
            "PYTHONPATH": str(PROJECT_ROOT),
            "COVERAGE_PROCESS_START": coverage_config,
            "RANSOMEYE_CORE_STATUS_PATH": str(status_path),
            "RANSOMEYE_RUN_DIR": str(temp_dir),
            "RANSOMEYE_LOG_DIR": str(temp_dir / "logs"),
            "RANSOMEYE_POLICY_DIR": str(temp_dir / "policy"),
            "RANSOMEYE_SCHEMA_MIGRATIONS_DIR": str(PROJECT_ROOT / "schemas" / "migrations"),
            "RANSOMEYE_EVENT_ENVELOPE_SCHEMA_PATH": str(PROJECT_ROOT / "contracts" / "event-envelope.schema.json"),
            "RANSOMEYE_COMMAND_SIGNING_KEY": "core-signing-key-1234567890-abcdef",
            "RANSOMEYE_UI_JWT_SIGNING_KEY": "ui-signing-key-1234567890-abcdef",
            "RANSOMEYE_AUDIT_LEDGER_PATH": str(temp_dir / "audit_ledger.jsonl"),
            "RANSOMEYE_AUDIT_LEDGER_KEY_DIR": str(temp_dir / "audit-keys"),
            "RANSOMEYE_UI_PORT": str(ui_port),
            "RANSOMEYE_INGEST_PORT": str(ingest_port),
            "RANSOMEYE_SERVICE_KEY_DIR": str(service_key_dir),
            "RANSOMEYE_COMPONENT_KEY_DIR": str(component_key_dir),
            "RANSOMEYE_DPI_CAPTURE_BACKEND": "replay",
            "RANSOMEYE_DPI_REPLAY_PATH": str(PROJECT_ROOT / "validation" / "harness" / "fixtures" / "dpi_frames.jsonl"),
            "RANSOMEYE_DPI_INTERFACE": "lo",
            "RANSOMEYE_DPI_FLOW_TIMEOUT": "1",
            "RANSOMEYE_DPI_HEARTBEAT_SECONDS": "1",
        }
    )

    proc = _start_core(env)
    try:
        start = time.time()
        while time.time() - start < 20:
            if status_path.exists():
                payload = status_path.read_text(encoding="utf-8")
                if "\"state\": \"RUNNING\"" in payload:
                    break
            time.sleep(0.5)

        start = time.time()
        event_found = False
        while time.time() - start < 30:
            conn = psycopg2.connect(
                host=os.getenv("RANSOMEYE_DB_HOST", "localhost"),
                port=int(os.getenv("RANSOMEYE_DB_PORT", "5432")),
                database=os.getenv("RANSOMEYE_DB_NAME", "ransomeye"),
                user=os.getenv("RANSOMEYE_DB_USER"),
                password=os.getenv("RANSOMEYE_DB_PASSWORD"),
            )
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    SELECT event_id FROM raw_events
                    WHERE component = 'dpi'
                    ORDER BY ingested_at DESC
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
                if row:
                    event_found = True
                    break
            finally:
                cur.close()
                conn.close()
            time.sleep(1)

        assert event_found is True
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=20)
