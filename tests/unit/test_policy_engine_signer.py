from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = PROJECT_ROOT / "services" / "policy-engine" / "app"
if str(POLICY_PATH) not in sys.path:
    sys.path.insert(0, str(POLICY_PATH))

import signer


def test_policy_signer_missing_key_dir(monkeypatch):
    monkeypatch.delenv("RANSOMEYE_POLICY_ENGINE_KEY_DIR", raising=False)
    signer._SIGNER = None
    with pytest.raises(SystemExit):
        signer.get_signer()


def test_policy_signer_valid_signature(tmp_path, monkeypatch):
    monkeypatch.setenv("RANSOMEYE_POLICY_ENGINE_KEY_DIR", str(tmp_path))
    signer._SIGNER = None
    s = signer.get_signer()
    payload = signer.create_command_payload(
        command_type="ISOLATE_HOST",
        target_machine_id="machine-1",
        incident_id="incident-1",
        policy_id="policy-1",
        policy_version="1.0.0",
        issuing_authority="policy-engine",
    )
    signature = s.sign_payload(payload)
    assert isinstance(signature, str)


def test_policy_signer_crypto_failure(monkeypatch, tmp_path):
    monkeypatch.setenv("RANSOMEYE_POLICY_ENGINE_KEY_DIR", str(tmp_path))
    signer._SIGNER = None

    class _Boom:
        def __init__(self, *_a, **_k): pass
        def get_or_create_keypair(self):
            raise RuntimeError("crypto failure")

    monkeypatch.setattr(signer, "PolicyEngineKeyManager", _Boom)
    with pytest.raises(SystemExit):
        signer.get_signer()
