#!/usr/bin/env python3
"""
RansomEye v1.0 Validation Harness - DPI Unified Pipeline Test
AUTHORITATIVE: Validates DPI capture replay and telemetry ingest
"""

import json
import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

import requests

from validation.harness.phase_c_executor import ValidationStatus
from validation.harness.test_helpers import get_test_db_connection, clean_database


def _generate_service_keys(key_dir: Path) -> None:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization

    key_dir.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    (key_dir / "ingest.key").write_bytes(private_key_bytes)
    (key_dir / "ingest.pub").write_bytes(public_key_bytes)


def _wait_for_ingest(url: str, timeout: int = 10) -> None:
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("Ingest service did not become healthy")


def _run_dpi_pipeline_replay() -> dict:
    """
    DPI-001: Replay capture emits telemetry and ingest accepts it.
    """
    clean_database()
    temp_dir = Path(tempfile.mkdtemp(prefix="ransomeye-dpi-test-"))
    component_key_dir = temp_dir / "component-keys"
    service_key_dir = temp_dir / "service-keys"
    replay_path = Path(__file__).parent / "fixtures" / "dpi_frames.jsonl"

    _generate_service_keys(service_key_dir)

    core_token = str(uuid.uuid4())
    ingest_port = 18080
    ingest_url = f"http://127.0.0.1:{ingest_port}"

    env = os.environ.copy()
    env["RANSOMEYE_SUPERVISED"] = "1"
    env["RANSOMEYE_CORE_PID"] = str(os.getpid())
    env["RANSOMEYE_CORE_TOKEN"] = core_token
    env["RANSOMEYE_COMPONENT_KEY_DIR"] = str(component_key_dir)
    env["RANSOMEYE_SERVICE_KEY_DIR"] = str(service_key_dir)
    env["RANSOMEYE_INGEST_PORT"] = str(ingest_port)
    env["RANSOMEYE_ALLOW_WEAK_SECRETS"] = "1"
    env["PYTHONWARNINGS"] = "ignore::DeprecationWarning"
    env["RANSOMEYE_EVENT_ENVELOPE_SCHEMA_PATH"] = str(
        Path(__file__).parent.parent.parent / "contracts" / "event-envelope.schema.json"
    )

    ingest_proc = subprocess.Popen(
        [os.environ.get("PYTHON", "python3"), str(Path(__file__).parent.parent.parent / "services" / "ingest" / "app" / "main.py")],
        env=env
    )
    try:
        _wait_for_ingest(f"{ingest_url}/health", timeout=15)

        dpi_env = env.copy()
        dpi_env["RANSOMEYE_INGEST_URL"] = f"{ingest_url}/events"
        dpi_env["RANSOMEYE_COMPONENT_INSTANCE_ID"] = f"dpi-test-{uuid.uuid4()}"
        dpi_env["RANSOMEYE_DPI_INTERFACE"] = "lo"
        dpi_env["RANSOMEYE_DPI_CAPTURE_BACKEND"] = "replay"
        dpi_env["RANSOMEYE_DPI_REPLAY_PATH"] = str(replay_path)
        dpi_env["RANSOMEYE_DPI_FLOW_TIMEOUT"] = "1"
        dpi_env["RANSOMEYE_DPI_HEARTBEAT_SECONDS"] = "2"
        dpi_env["RANSOMEYE_ENV"] = "ci"
        dpi_env["CI"] = "true"

        dpi_proc = subprocess.Popen(
            [os.environ.get("PYTHON", "python3"), str(Path(__file__).parent.parent.parent / "dpi" / "probe" / "main.py")],
            env=dpi_env
        )

        event_id = None
        payload = None
        start = time.time()
        while time.time() - start < 15:
            conn = get_test_db_connection()
            cur = conn.cursor()
            try:
                cur.execute("""
                    SELECT event_id, payload
                    FROM raw_events
                    WHERE component = 'dpi'
                    ORDER BY ingested_at DESC
                    LIMIT 1
                """)
                row = cur.fetchone()
                if row:
                    event_id, payload = row
                    break
            finally:
                cur.close()
                conn.close()
            time.sleep(0.5)

        if dpi_proc.poll() is None:
            dpi_proc.terminate()
            dpi_proc.wait(timeout=5)

        if not event_id or not payload:
            raise RuntimeError("DPI telemetry not observed in ingest database")

        if not isinstance(payload, dict):
            raise RuntimeError("DPI payload is not JSON")

        event_type = payload.get("event_type")
        if event_type not in ("dpi.flow", "dpi.heartbeat"):
            raise RuntimeError(f"Unexpected DPI event_type: {event_type}")

        capture = payload.get("capture", {})
        if capture.get("backend") != "replay":
            raise RuntimeError("DPI capture backend not recorded as replay")

        return {"status": ValidationStatus.PASSED.value, "event_id": event_id}
    finally:
        ingest_proc.terminate()
        ingest_proc.wait(timeout=5)


def test_dpi_pipeline_replay() -> None:
    result = _run_dpi_pipeline_replay()
    assert result["status"] == ValidationStatus.PASSED.value


if __name__ == "__main__":
    try:
        result = _run_dpi_pipeline_replay()
        print(json.dumps(result, indent=2))
        exit(0 if result["status"] == ValidationStatus.PASSED.value else 1)
    except Exception as exc:
        print(f"FAIL: {exc}")
        exit(1)
