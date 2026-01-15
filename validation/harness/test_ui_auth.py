#!/usr/bin/env python3
"""
RansomEye v1.0 Validation Harness - UI Auth + RBAC Tests
AUTHORITATIVE: Phase 4 UI authentication enforcement verification
"""

import os
import sys
import socket
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Tuple

import requests

from validation.harness.phase_c_executor import ValidationStatus
from validation.harness.test_helpers import get_test_db_connection


def _project_root() -> Path:
    return Path(__file__).parent.parent.parent


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    _, port = sock.getsockname()
    sock.close()
    return port


def _build_env(port: int, jwt_key: str, ledger_path: Path, ledger_key_dir: Path) -> Dict[str, str]:
    env = os.environ.copy()
    env["RANSOMEYE_SUPERVISED"] = "1"
    env["RANSOMEYE_CORE_PID"] = str(os.getpid())
    env["RANSOMEYE_CORE_TOKEN"] = str(uuid.uuid4())
    env["RANSOMEYE_UI_PORT"] = str(port)
    env["RANSOMEYE_UI_BIND_ADDRESS"] = "127.0.0.1"
    env["RANSOMEYE_UI_JWT_SIGNING_KEY"] = jwt_key
    env["RANSOMEYE_AUDIT_LEDGER_PATH"] = str(ledger_path)
    env["RANSOMEYE_AUDIT_LEDGER_KEY_DIR"] = str(ledger_key_dir)
    env["RANSOMEYE_UI_CORS_ALLOW_ORIGINS"] = "http://127.0.0.1:5173"
    env["RANSOMEYE_UI_CORS_ALLOW_METHODS"] = "GET,POST"
    env["RANSOMEYE_UI_COOKIE_SECURE"] = "false"
    env["RANSOMEYE_UI_COOKIE_SAMESITE"] = "lax"
    return env


def _wait_for_login(base_url: str, timeout: int = 10) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.post(
                f"{base_url}/auth/login",
                json={"username": "missing", "password": "missing"},
                timeout=1
            )
            if response.status_code in (401, 403):
                return True
        except Exception:
            time.sleep(0.5)
    return False


def _prepare_rbac_users() -> Dict[str, Dict[str, str]]:
    project_root = _project_root()
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from rbac.api.rbac_api import RBACAPI

    conn = get_test_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM rbac_refresh_tokens")
    cur.execute("DELETE FROM rbac_user_roles")
    cur.execute("DELETE FROM rbac_users WHERE username IN (%s, %s)", ("ui_admin", "ui_auditor"))
    conn.commit()
    cur.close()
    conn.close()

    rbac_api = RBACAPI({
        "host": os.getenv("RANSOMEYE_DB_HOST", "localhost"),
        "port": int(os.getenv("RANSOMEYE_DB_PORT", "5432")),
        "database": os.getenv("RANSOMEYE_DB_NAME", "ransomeye"),
        "user": os.getenv("RANSOMEYE_DB_USER"),
        "password": os.getenv("RANSOMEYE_DB_PASSWORD")
    })
    rbac_api.initialize_role_permissions()

    admin = rbac_api.create_user("ui_admin", "ui_admin_pass", created_by="system")
    auditor = rbac_api.create_user("ui_auditor", "ui_auditor_pass", created_by="system")
    rbac_api.assign_role(admin["user_id"], "SUPER_ADMIN", assigned_by="system")
    rbac_api.assign_role(auditor["user_id"], "AUDITOR", assigned_by="system")
    return {
        "admin": {"username": "ui_admin", "password": "ui_admin_pass"},
        "auditor": {"username": "ui_auditor", "password": "ui_auditor_pass"}
    }


def _start_ui_backend(env: Dict[str, str]) -> Tuple[subprocess.Popen, str]:
    project_root = _project_root()
    backend = project_root / "services" / "ui" / "backend" / "main.py"
    proc = subprocess.Popen([os.environ.get("PYTHON", "python3"), str(backend)], env=env)
    base_url = f"http://127.0.0.1:{env['RANSOMEYE_UI_PORT']}"
    return proc, base_url


def _stop_process(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


def test_ui_auth_001_requires_auth(executor=None, conn=None) -> Dict[str, Any]:
    """
    UI-AUTH-001: All endpoints return 401 without auth.
    """
    port = _free_port()
    jwt_key = f"ui_test_key_{uuid.uuid4()}_{uuid.uuid4()}"
    temp_dir = Path(tempfile.mkdtemp(prefix="ransomeye-ui-auth-"))
    env = _build_env(port, jwt_key, temp_dir / "ledger.jsonl", temp_dir / "keys")
    env["RANSOMEYE_AUDIT_LEDGER_KEY_DIR"] = str(temp_dir / "keys")
    os.makedirs(env["RANSOMEYE_AUDIT_LEDGER_KEY_DIR"], exist_ok=True)

    _prepare_rbac_users()
    proc, base_url = _start_ui_backend(env)
    try:
        if not _wait_for_login(base_url):
            return {"status": ValidationStatus.FAILED.value, "error": "UI backend did not start"}

        incidents = requests.get(f"{base_url}/api/incidents", timeout=2)
        health = requests.get(f"{base_url}/health", timeout=2)
        passed = incidents.status_code == 401 and health.status_code == 401
        return {
            "status": ValidationStatus.PASSED.value if passed else ValidationStatus.FAILED.value,
            "incidents_status": incidents.status_code,
            "health_status": health.status_code
        }
    finally:
        _stop_process(proc)


def test_ui_auth_002_permission_denied(executor=None, conn=None) -> Dict[str, Any]:
    """
    UI-AUTH-002: Valid token + missing permission returns 403.
    """
    port = _free_port()
    jwt_key = f"ui_test_key_{uuid.uuid4()}_{uuid.uuid4()}"
    temp_dir = Path(tempfile.mkdtemp(prefix="ransomeye-ui-auth-"))
    env = _build_env(port, jwt_key, temp_dir / "ledger.jsonl", temp_dir / "keys")
    os.makedirs(env["RANSOMEYE_AUDIT_LEDGER_KEY_DIR"], exist_ok=True)

    users = _prepare_rbac_users()
    proc, base_url = _start_ui_backend(env)
    try:
        if not _wait_for_login(base_url):
            return {"status": ValidationStatus.FAILED.value, "error": "UI backend did not start"}

        response = requests.post(
            f"{base_url}/auth/login",
            json=users["auditor"],
            timeout=2
        )
        token = response.json().get("access_token")
        health = requests.get(
            f"{base_url}/health",
            headers={"Authorization": f"Bearer {token}"},
            timeout=2
        )
        passed = health.status_code == 403
        return {
            "status": ValidationStatus.PASSED.value if passed else ValidationStatus.FAILED.value,
            "health_status": health.status_code
        }
    finally:
        _stop_process(proc)


def test_ui_auth_003_permission_allowed(executor=None, conn=None) -> Dict[str, Any]:
    """
    UI-AUTH-003: Valid token + permission returns 200.
    """
    port = _free_port()
    jwt_key = f"ui_test_key_{uuid.uuid4()}_{uuid.uuid4()}"
    temp_dir = Path(tempfile.mkdtemp(prefix="ransomeye-ui-auth-"))
    env = _build_env(port, jwt_key, temp_dir / "ledger.jsonl", temp_dir / "keys")
    os.makedirs(env["RANSOMEYE_AUDIT_LEDGER_KEY_DIR"], exist_ok=True)

    users = _prepare_rbac_users()
    proc, base_url = _start_ui_backend(env)
    try:
        if not _wait_for_login(base_url):
            return {"status": ValidationStatus.FAILED.value, "error": "UI backend did not start"}

        response = requests.post(
            f"{base_url}/auth/login",
            json=users["admin"],
            timeout=2
        )
        token = response.json().get("access_token")
        health = requests.get(
            f"{base_url}/health",
            headers={"Authorization": f"Bearer {token}"},
            timeout=2
        )
        passed = health.status_code == 200
        return {
            "status": ValidationStatus.PASSED.value if passed else ValidationStatus.FAILED.value,
            "health_status": health.status_code
        }
    finally:
        _stop_process(proc)


def test_ui_auth_004_rbac_missing_startup(executor=None, conn=None) -> Dict[str, Any]:
    """
    UI-AUTH-004: UI fails startup if RBAC backend missing.
    """
    port = _free_port()
    jwt_key = f"ui_test_key_{uuid.uuid4()}_{uuid.uuid4()}"
    temp_dir = Path(tempfile.mkdtemp(prefix="ransomeye-ui-auth-"))
    env = _build_env(port, jwt_key, temp_dir / "ledger.jsonl", temp_dir / "keys")
    env["RANSOMEYE_RBAC_FORCE_UNAVAILABLE"] = "1"
    os.makedirs(env["RANSOMEYE_AUDIT_LEDGER_KEY_DIR"], exist_ok=True)

    proc, _ = _start_ui_backend(env)
    try:
        proc.wait(timeout=5)
        passed = proc.returncode not in (0, None)
        return {
            "status": ValidationStatus.PASSED.value if passed else ValidationStatus.FAILED.value,
            "exit_code": proc.returncode
        }
    finally:
        _stop_process(proc)


def test_ui_auth_005_cors_rejects_non_allowlisted(executor=None, conn=None) -> Dict[str, Any]:
    """
    UI-AUTH-005: CORS rejects non-allowlisted origins.
    """
    port = _free_port()
    jwt_key = f"ui_test_key_{uuid.uuid4()}_{uuid.uuid4()}"
    temp_dir = Path(tempfile.mkdtemp(prefix="ransomeye-ui-auth-"))
    env = _build_env(port, jwt_key, temp_dir / "ledger.jsonl", temp_dir / "keys")
    os.makedirs(env["RANSOMEYE_AUDIT_LEDGER_KEY_DIR"], exist_ok=True)

    users = _prepare_rbac_users()
    proc, base_url = _start_ui_backend(env)
    try:
        if not _wait_for_login(base_url):
            return {"status": ValidationStatus.FAILED.value, "error": "UI backend did not start"}

        response = requests.post(
            f"{base_url}/auth/login",
            json=users["admin"],
            timeout=2
        )
        token = response.json().get("access_token")
        incidents = requests.get(
            f"{base_url}/api/incidents",
            headers={
                "Authorization": f"Bearer {token}",
                "Origin": "http://evil.example"
            },
            timeout=2
        )
        allow_origin = incidents.headers.get("access-control-allow-origin")
        passed = allow_origin is None
        return {
            "status": ValidationStatus.PASSED.value if passed else ValidationStatus.FAILED.value,
            "allow_origin": allow_origin
        }
    finally:
        _stop_process(proc)


def test_ui_auth_006_frontend_login_flow(executor=None, conn=None) -> Dict[str, Any]:
    """
    UI-AUTH-006: Frontend-style login/refresh/logout flow works.
    """
    port = _free_port()
    jwt_key = f"ui_test_key_{uuid.uuid4()}_{uuid.uuid4()}"
    temp_dir = Path(tempfile.mkdtemp(prefix="ransomeye-ui-auth-"))
    env = _build_env(port, jwt_key, temp_dir / "ledger.jsonl", temp_dir / "keys")
    os.makedirs(env["RANSOMEYE_AUDIT_LEDGER_KEY_DIR"], exist_ok=True)

    users = _prepare_rbac_users()
    proc, base_url = _start_ui_backend(env)
    session = requests.Session()
    try:
        if not _wait_for_login(base_url):
            return {"status": ValidationStatus.FAILED.value, "error": "UI backend did not start"}

        login_resp = session.post(f"{base_url}/auth/login", json=users["admin"], timeout=2)
        token = login_resp.json().get("access_token")
        incidents = session.get(
            f"{base_url}/api/incidents",
            headers={"Authorization": f"Bearer {token}"},
            timeout=2
        )
        refresh_resp = session.post(f"{base_url}/auth/refresh", timeout=2)
        refresh_token = refresh_resp.json().get("access_token")
        logout_resp = session.post(
            f"{base_url}/auth/logout",
            headers={"Authorization": f"Bearer {refresh_token}"},
            timeout=2
        )
        refresh_after_logout = session.post(f"{base_url}/auth/refresh", timeout=2)

        passed = (
            login_resp.status_code == 200 and
            incidents.status_code == 200 and
            refresh_resp.status_code == 200 and
            logout_resp.status_code == 200 and
            refresh_after_logout.status_code == 401
        )
        return {
            "status": ValidationStatus.PASSED.value if passed else ValidationStatus.FAILED.value,
            "login_status": login_resp.status_code,
            "incidents_status": incidents.status_code,
            "refresh_status": refresh_resp.status_code,
            "logout_status": logout_resp.status_code,
            "refresh_after_logout_status": refresh_after_logout.status_code
        }
    finally:
        _stop_process(proc)
