import json
import os
import signal
import socket
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import requests

from common.db.migration_runner import MigrationRunner
from rbac.api.rbac_api import RBACAPI


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


def _make_ui_health_token(user_id: str, signing_key: str) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=10)
    payload = {
        "sub": user_id,
        "token_type": "access",
        "role": "SUPER_ADMIN",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "iss": "ransomeye-ui",
        "aud": "ransomeye-ui",
    }
    return jwt.encode(payload, signing_key, algorithm="HS256")


def _wait_for_status(status_path: Path, state: str, timeout: int = 20) -> dict:
    start = time.time()
    while time.time() - start < timeout:
        if status_path.exists():
            payload = json.loads(status_path.read_text(encoding="utf-8"))
            if payload.get("state") == state:
                return payload
        time.sleep(0.5)
    return {}


def _wait_for_ui(base_url: str, timeout: int = 15) -> None:
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.post(
                f"{base_url}/auth/login",
                json={"username": "missing", "password": "missing"},
                timeout=2,
            )
            if response.status_code in (401, 403):
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise AssertionError("UI backend did not become ready")


def _start_core(env: dict) -> subprocess.Popen:
    core_main = PROJECT_ROOT / "core" / "main.py"
    python_bin = env.get("PYTHON") or os.environ.get("PYTHON", "python3")
    return subprocess.Popen([python_bin, str(core_main)], env=env)


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


def _init_rbac_users() -> dict:
    rbac = RBACAPI(
        {
            "host": os.getenv("RANSOMEYE_DB_HOST", "localhost"),
            "port": int(os.getenv("RANSOMEYE_DB_PORT", "5432")),
            "database": os.getenv("RANSOMEYE_DB_NAME", "ransomeye"),
            "user": os.getenv("RANSOMEYE_DB_USER"),
            "password": os.getenv("RANSOMEYE_DB_PASSWORD"),
        }
    )
    rbac.initialize_role_permissions()
    admin = rbac.get_user_by_username("core_admin")
    if not admin:
        admin = rbac.create_user("core_admin", "core_admin_pass", created_by="system")
    rbac.assign_role(admin["user_id"], "SUPER_ADMIN", assigned_by="system")
    return {
        "admin": {
            "username": "core_admin",
            "password": "core_admin_pass",
            "user_id": admin["user_id"],
        }
    }


def test_core_starts_after_migrations():
    _apply_migrations()
    temp_dir = Path(tempfile.mkdtemp(prefix="ransomeye-core-int-"))
    status_path = temp_dir / "core_status.json"
    service_key_dir = temp_dir / "service-keys"
    _generate_service_keys(service_key_dir)
    python_bin = str(PROJECT_ROOT / ".venv" / "bin" / "python")
    coverage_config = str(PROJECT_ROOT / ".coveragerc")

    env = os.environ.copy()
    env.update(
        {
            "CI": "true",
            "RANSOMEYE_ENV": "ci",
            "RANSOMEYE_ALLOW_WEAK_TEST_CREDENTIALS": "1",
            "PYTHON": python_bin,
            "RANSOMEYE_PYTHON_BIN": python_bin,
            "PYTHONPATH": str(PROJECT_ROOT),
            "COVERAGE_PROCESS_START": coverage_config,
            "RANSOMEYE_ORCHESTRATOR_STUB": "1",
            "RANSOMEYE_CORE_STATUS_PATH": str(status_path),
            "RANSOMEYE_RUN_DIR": str(temp_dir),
            "RANSOMEYE_LOG_DIR": str(temp_dir / "logs"),
            "RANSOMEYE_POLICY_DIR": str(temp_dir / "policy"),
            "RANSOMEYE_SCHEMA_MIGRATIONS_DIR": str(PROJECT_ROOT / "schemas" / "migrations"),
            "RANSOMEYE_EVENT_ENVELOPE_SCHEMA_PATH": str(PROJECT_ROOT / "contracts" / "event-envelope.schema.json"),
            "RANSOMEYE_COMMAND_SIGNING_KEY": "core-signing-key-1234567890-abcdef",
            "RANSOMEYE_SERVICE_KEY_DIR": str(service_key_dir),
        }
    )

    proc = _start_core(env)
    try:
        payload = _wait_for_status(status_path, "RUNNING", timeout=20)
        assert payload.get("state") == "RUNNING"
    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)


def test_core_ui_auth_health():
    _apply_migrations()
    users = _init_rbac_users()
    temp_dir = Path(tempfile.mkdtemp(prefix="ransomeye-core-ui-"))
    status_path = temp_dir / "core_status.json"
    service_key_dir = temp_dir / "service-keys"
    component_key_dir = temp_dir / "component-keys"
    ledger_path = temp_dir / "audit_ledger.jsonl"
    ledger_key_dir = temp_dir / "audit-keys"
    policy_engine_key_dir = temp_dir / "policy-engine-keys"
    model_storage_dir = temp_dir / "models"
    _generate_service_keys(service_key_dir)
    policy_engine_key_dir.mkdir(parents=True, exist_ok=True)
    ledger_key_dir.mkdir(parents=True, exist_ok=True)
    model_storage_dir.mkdir(parents=True, exist_ok=True)

    ui_port = _free_port()
    ingest_port = _free_port()
    python_bin = str(PROJECT_ROOT / ".venv" / "bin" / "python")
    coverage_config = str(PROJECT_ROOT / ".coveragerc")
    env = os.environ.copy()
    env.update(
        {
            "CI": "true",
            "RANSOMEYE_ENV": "ci",
            "RANSOMEYE_ALLOW_WEAK_TEST_CREDENTIALS": "1",
            "PYTHON": python_bin,
            "RANSOMEYE_PYTHON_BIN": python_bin,
            "PYTHONPATH": str(PROJECT_ROOT),
            "COVERAGE_PROCESS_START": coverage_config,
            "RANSOMEYE_CORE_STATUS_PATH": str(status_path),
            "RANSOMEYE_RUN_DIR": str(temp_dir),
            "RANSOMEYE_LOG_DIR": str(temp_dir / "logs"),
            "RANSOMEYE_POLICY_DIR": str(temp_dir / "policy"),
            "RANSOMEYE_POLICY_ENGINE_KEY_DIR": str(policy_engine_key_dir),
            "RANSOMEYE_SCHEMA_MIGRATIONS_DIR": str(PROJECT_ROOT / "schemas" / "migrations"),
            "RANSOMEYE_EVENT_ENVELOPE_SCHEMA_PATH": str(PROJECT_ROOT / "contracts" / "event-envelope.schema.json"),
            "RANSOMEYE_COMMAND_SIGNING_KEY": "core-signing-key-1234567890-abcdef",
            "RANSOMEYE_UI_JWT_SIGNING_KEY": "ui-signing-key-1234567890-abcdef",
            "RANSOMEYE_UI_HEALTH_TOKEN": _make_ui_health_token(
                users["admin"]["user_id"], "ui-signing-key-1234567890-abcdef"
            ),
            "RANSOMEYE_AUDIT_LEDGER_PATH": str(ledger_path),
            "RANSOMEYE_AUDIT_LEDGER_KEY_DIR": str(ledger_key_dir),
            "RANSOMEYE_MODEL_STORAGE_DIR": str(model_storage_dir),
            "RANSOMEYE_UI_PORT": str(ui_port),
            "RANSOMEYE_INGEST_PORT": str(ingest_port),
            "RANSOMEYE_INGEST_URL": f"http://127.0.0.1:{ingest_port}/events",
            "RANSOMEYE_SERVICE_KEY_DIR": str(service_key_dir),
            "RANSOMEYE_COMPONENT_KEY_DIR": str(component_key_dir),
            "RANSOMEYE_COMPONENT_INSTANCE_ID": f"core-ui-dpi-{uuid.uuid4()}",
            "RANSOMEYE_DPI_CAPTURE_BACKEND": "replay",
            "RANSOMEYE_DPI_REPLAY_PATH": str(PROJECT_ROOT / "validation" / "harness" / "fixtures" / "dpi_frames.jsonl"),
            "RANSOMEYE_DPI_INTERFACE": "lo",
        }
    )

    proc = _start_core(env)
    try:
        payload = _wait_for_status(status_path, "RUNNING", timeout=30)
        assert payload.get("state") == "RUNNING"

        base_url = f"http://127.0.0.1:{ui_port}"
        _wait_for_ui(base_url)
        login = requests.post(
            f"{base_url}/auth/login",
            json=users["admin"],
            timeout=5,
        )
        assert login.status_code == 200
        token = login.json()["access_token"]

        unauthorized = requests.get(f"{base_url}/health", timeout=5)
        assert unauthorized.status_code == 401

        authorized = requests.get(
            f"{base_url}/health",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        assert authorized.status_code == 200
    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
