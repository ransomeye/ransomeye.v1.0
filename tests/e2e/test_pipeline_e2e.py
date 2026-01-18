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
import psycopg2
import requests

from common.db.migration_runner import MigrationRunner
from rbac.api.rbac_api import RBACAPI
from validation.harness.test_helpers import launch_linux_agent_and_wait_for_event, verify_ai_metadata_exists


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


def _wait_for_ai_metadata_event(conn, incident_id: str, timeout: int = 30) -> str:
    start = time.time()
    while time.time() - start < timeout:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT e.event_id
                FROM evidence e
                WHERE e.incident_id = %s
                  AND (
                      EXISTS (SELECT 1 FROM feature_vectors fv WHERE fv.event_id = e.event_id)
                      OR EXISTS (SELECT 1 FROM shap_explanations se WHERE se.event_id = e.event_id)
                      OR EXISTS (SELECT 1 FROM cluster_memberships cm WHERE cm.event_id = e.event_id)
                      OR EXISTS (SELECT 1 FROM novelty_scores ns WHERE ns.event_id = e.event_id)
                  )
                ORDER BY e.created_at DESC
                LIMIT 1
                """,
                (incident_id,),
            )
            row = cur.fetchone()
            if row:
                return row[0]
        time.sleep(1)
    raise AssertionError("AI metadata not found for incident evidence within timeout")
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
    admin = rbac.get_user_by_username("e2e_admin")
    if not admin:
        admin = rbac.create_user("e2e_admin", "e2e_admin_pass", created_by="system")
    rbac.assign_role(admin["user_id"], "SUPER_ADMIN", assigned_by="system")
    return {
        "admin": {
            "username": "e2e_admin",
            "password": "e2e_admin_pass",
            "user_id": admin["user_id"],
        }
    }


def _start_core(env: dict) -> subprocess.Popen:
    core_main = PROJECT_ROOT / "core" / "main.py"
    python_bin = env.get("PYTHON") or os.environ.get("PYTHON", "python3")
    return subprocess.Popen([python_bin, str(core_main)], env=env)


def _wait_for_incident(timeout: int = 30) -> str:
    start = time.time()
    while time.time() - start < timeout:
        conn = psycopg2.connect(
            host=os.getenv("RANSOMEYE_DB_HOST", "localhost"),
            port=int(os.getenv("RANSOMEYE_DB_PORT", "5432")),
            database=os.getenv("RANSOMEYE_DB_NAME", "ransomeye"),
            user=os.getenv("RANSOMEYE_DB_USER"),
            password=os.getenv("RANSOMEYE_DB_PASSWORD"),
        )
        cur = conn.cursor()
        try:
            cur.execute("SELECT incident_id FROM incidents ORDER BY created_at DESC LIMIT 1")
            row = cur.fetchone()
            if row:
                return row[0]
        finally:
            cur.close()
            conn.close()
        time.sleep(1)
    raise AssertionError("Incident not created in time")


def _wait_for_ui(base_url: str, timeout: int = 20) -> None:
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


def _wait_for_ingest(base_url: str, timeout: int = 20) -> None:
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(f"{base_url}/health", timeout=2)
            if response.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise AssertionError("Ingest did not become ready")


def test_pipeline_e2e_linux_agent_to_ui():
    _apply_migrations()
    users = _init_rbac_users()
    temp_dir = Path(tempfile.mkdtemp(prefix="ransomeye-e2e-"))
    service_key_dir = temp_dir / "service-keys"
    component_key_dir = temp_dir / "component-keys"
    policy_dir = temp_dir / "policy"
    policy_engine_key_dir = temp_dir / "policy-engine-keys"
    audit_key_dir = temp_dir / "audit-keys"
    model_storage_dir = temp_dir / "models"
    _generate_service_keys(service_key_dir)
    policy_engine_key_dir.mkdir(parents=True, exist_ok=True)
    audit_key_dir.mkdir(parents=True, exist_ok=True)
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
            "RANSOMEYE_ALLOW_UNAUTH_INGEST": "1",
            "RANSOMEYE_CORE_STATUS_PATH": str(temp_dir / "core_status.json"),
            "RANSOMEYE_RUN_DIR": str(temp_dir),
            "RANSOMEYE_LOG_DIR": str(temp_dir / "logs"),
            "RANSOMEYE_POLICY_DIR": str(policy_dir),
            "RANSOMEYE_POLICY_ENGINE_KEY_DIR": str(policy_engine_key_dir),
            "RANSOMEYE_SCHEMA_MIGRATIONS_DIR": str(PROJECT_ROOT / "schemas" / "migrations"),
            "RANSOMEYE_EVENT_ENVELOPE_SCHEMA_PATH": str(PROJECT_ROOT / "contracts" / "event-envelope.schema.json"),
            "RANSOMEYE_COMMAND_SIGNING_KEY": "core-signing-key-1234567890-abcdef",
            "RANSOMEYE_UI_JWT_SIGNING_KEY": "ui-signing-key-1234567890-abcdef",
            "RANSOMEYE_UI_HEALTH_TOKEN": _make_ui_health_token(
                users["admin"]["user_id"], "ui-signing-key-1234567890-abcdef"
            ),
            "RANSOMEYE_AUDIT_LEDGER_PATH": str(temp_dir / "audit_ledger.jsonl"),
            "RANSOMEYE_AUDIT_LEDGER_KEY_DIR": str(audit_key_dir),
            "RANSOMEYE_MODEL_STORAGE_DIR": str(model_storage_dir),
            "RANSOMEYE_UI_PORT": str(ui_port),
            "RANSOMEYE_INGEST_PORT": str(ingest_port),
            "RANSOMEYE_INGEST_URL": f"http://127.0.0.1:{ingest_port}/events",
            "RANSOMEYE_SERVICE_KEY_DIR": str(service_key_dir),
            "RANSOMEYE_COMPONENT_KEY_DIR": str(component_key_dir),
            "RANSOMEYE_COMPONENT_INSTANCE_ID": f"e2e-dpi-{uuid.uuid4()}",
            "RANSOMEYE_DPI_CAPTURE_BACKEND": "replay",
            "RANSOMEYE_DPI_REPLAY_PATH": str(PROJECT_ROOT / "validation" / "harness" / "fixtures" / "dpi_frames.jsonl"),
            "RANSOMEYE_DPI_INTERFACE": "lo",
            "RANSOMEYE_COMPONENT_CYCLE_SECONDS": "1",
        }
    )

    proc = _start_core(env)
    try:
        ingest_url = f"http://127.0.0.1:{ingest_port}/events"
        _wait_for_ingest(f"http://127.0.0.1:{ingest_port}")
        os.environ["RANSOMEYE_INGEST_URL"] = ingest_url
        os.environ["RANSOMEYE_SERVICE_KEY_DIR"] = str(service_key_dir)
        os.environ["RANSOMEYE_COMPONENT_KEY_DIR"] = str(component_key_dir)
        launch_linux_agent_and_wait_for_event(ingest_url=ingest_url, timeout_seconds=40)

        incident_id = _wait_for_incident(timeout=40)
        conn = psycopg2.connect(
            host=os.getenv("RANSOMEYE_DB_HOST", "localhost"),
            port=int(os.getenv("RANSOMEYE_DB_PORT", "5432")),
            database=os.getenv("RANSOMEYE_DB_NAME", "ransomeye"),
            user=os.getenv("RANSOMEYE_DB_USER"),
            password=os.getenv("RANSOMEYE_DB_PASSWORD"),
        )
        try:
            event_id = _wait_for_ai_metadata_event(conn, incident_id, timeout=40)
            ai_metadata = verify_ai_metadata_exists(conn, event_id, check_content=False)
            assert any(ai_metadata.values()) is True
        finally:
            conn.close()

        policy_file = policy_dir / f"policy_decision_{incident_id}.json"
        start = time.time()
        while time.time() - start < 30 and not policy_file.exists():
            time.sleep(1)
        assert policy_file.exists() is True

        base_url = f"http://127.0.0.1:{ui_port}"
        _wait_for_ui(base_url)
        login = requests.post(f"{base_url}/auth/login", json=users["admin"], timeout=5)
        assert login.status_code == 200
        token = login.json()["access_token"]

        unauthorized = requests.get(f"{base_url}/api/incidents", timeout=5)
        assert unauthorized.status_code == 401

        incidents = requests.get(
            f"{base_url}/api/incidents",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        assert incidents.status_code == 200

        detail = requests.get(
            f"{base_url}/api/incidents/{incident_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        assert detail.status_code == 200
        payload = detail.json()
        assert payload.get("ai_insights") is not None
        assert payload.get("policy_recommendations") is not None
    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
