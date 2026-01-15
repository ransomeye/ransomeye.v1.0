import os
import struct
from datetime import datetime, timezone

from dpi.probe import main as dpi_main
from dpi.probe.main import _parse_frame, EventEnvelopeBuilder, _build_flow_payload


def _build_ipv4_tcp_frame():
    dst_mac = b"\xaa\xbb\xcc\xdd\xee\xff"
    src_mac = b"\x11\x22\x33\x44\x55\x66"
    ethertype = struct.pack("!H", 0x0800)
    eth_header = dst_mac + src_mac + ethertype

    version_ihl = 0x45
    tos = 0
    total_length = 20 + 4
    identification = 0
    flags_fragment = 0
    ttl = 64
    protocol = 6
    checksum = 0
    src_ip = struct.pack("!4B", 192, 168, 1, 10)
    dst_ip = struct.pack("!4B", 192, 168, 1, 20)
    ip_header = struct.pack(
        "!BBHHHBBH4s4s",
        version_ihl,
        tos,
        total_length,
        identification,
        flags_fragment,
        ttl,
        protocol,
        checksum,
        src_ip,
        dst_ip,
    )

    tcp_header = struct.pack("!HH", 443, 51515)
    return eth_header + ip_header + tcp_header


def test_parse_frame_extracts_flow_fields():
    frame = _build_ipv4_tcp_frame()
    parsed = _parse_frame(frame, datetime.now(timezone.utc))
    assert parsed is not None
    assert parsed["src_ip"] == "192.168.1.10"
    assert parsed["dst_ip"] == "192.168.1.20"
    assert parsed["src_port"] == 443
    assert parsed["dst_port"] == 51515
    assert parsed["protocol"] == "tcp"


def test_event_envelope_builder_tracks_sequence():
    builder = EventEnvelopeBuilder(
        machine_id="machine-a",
        component_instance_id="component-1",
        hostname="host-a",
        boot_id="boot-1",
        agent_version="1.0.0",
    )
    first = builder.build({"event_type": "dpi.heartbeat"}, observed_at=datetime.now(timezone.utc))
    second = builder.build({"event_type": "dpi.heartbeat"}, observed_at=datetime.now(timezone.utc))
    assert first["sequence"] == 0
    assert second["sequence"] == 1
    builder.update_prev_hash("abc123")
    third = builder.build({"event_type": "dpi.heartbeat"}, observed_at=datetime.now(timezone.utc))
    assert third["integrity"]["prev_hash_sha256"] == "abc123"


def test_build_flow_payload_shape():
    payload = _build_flow_payload(
        {
            "flow_id": "flow-1",
            "src_ip": "10.0.0.1",
            "dst_ip": "10.0.0.2",
            "src_port": 1111,
            "dst_port": 2222,
            "protocol": "tcp",
            "packet_count": 5,
            "byte_count": 100,
            "flow_start": "start",
            "flow_end": "end",
            "immutable_hash": "hash",
        },
        {"backend": "replay", "interface": "lo"},
    )
    assert payload["event_type"] == "dpi.flow"
    assert payload["flow"]["src_ip"] == "10.0.0.1"


def test_run_dpi_probe_emits_events(monkeypatch, tmp_path):
    events = []

    class _FakeCapture:
        def __init__(self, replay_path):
            self._calls = 0

        def read(self, timeout_seconds):
            self._calls += 1
            if self._calls == 1:
                return b"frame", datetime.now(timezone.utc)
            return None

        def close(self):
            return None

    class _FakeFlowAssembler:
        def __init__(self, flow_timeout):
            return None

        def process_packet(self, **kwargs):
            return {
                "flow_id": "flow-1",
                "src_ip": "10.0.0.1",
                "dst_ip": "10.0.0.2",
                "src_port": 1111,
                "dst_port": 2222,
                "protocol": "tcp",
                "packet_count": 1,
                "byte_count": 10,
                "flow_start": "start",
                "flow_end": "end",
                "immutable_hash": "hash",
            }

        def flush_expired(self, now):
            return []

    class _FakeBehaviorModel:
        def analyze_flow(self, flow):
            return {"profile_id": "profile-1"}

    class _FakePrivacyRedactor:
        def __init__(self, config):
            return None

        def redact_flow(self, flow):
            return flow

    class _FakeSigner:
        def __init__(self, key_dir, private_key_path=None):
            return None

        def sign_envelope(self, envelope):
            envelope["integrity"]["hash_sha256"] = "hash"
            return envelope

    class _FakeAuthManager:
        def __init__(self, service_name):
            return None

        def get_auth_token(self, target_service):
            return "token"

    class _FakeShutdown:
        def __init__(self):
            self._called = 0

        def is_shutdown_requested(self):
            self._called += 1
            return self._called > 2

    monkeypatch.setattr(dpi_main, "ReplayCapture", _FakeCapture)
    monkeypatch.setattr(dpi_main, "FlowAssembler", _FakeFlowAssembler)
    monkeypatch.setattr(dpi_main, "BehaviorModel", _FakeBehaviorModel)
    monkeypatch.setattr(dpi_main, "PrivacyRedactor", _FakePrivacyRedactor)
    monkeypatch.setattr(dpi_main, "TelemetrySigner", _FakeSigner)
    monkeypatch.setattr(dpi_main, "ServiceAuthManager", _FakeAuthManager)
    monkeypatch.setattr(dpi_main, "_parse_frame", lambda frame, ts: {"src_ip": "10.0.0.1", "dst_ip": "10.0.0.2", "src_port": 1, "dst_port": 2, "protocol": "tcp", "packet_size": 10, "timestamp": ts})
    monkeypatch.setattr(dpi_main, "_send_event", lambda ingest_url, envelope, auth_manager: events.append(envelope))
    monkeypatch.setattr(dpi_main, "shutdown_handler", _FakeShutdown())
    monkeypatch.setattr(dpi_main, "_get_machine_id", lambda: "machine-1")
    monkeypatch.setattr(dpi_main, "_get_boot_id", lambda: "boot-1")

    os.environ["CI"] = "true"
    os.environ["RANSOMEYE_ENV"] = "ci"

    config = {
        "RANSOMEYE_INGEST_URL": "http://127.0.0.1:8000/events",
        "RANSOMEYE_DPI_INTERFACE": "lo",
        "RANSOMEYE_COMPONENT_INSTANCE_ID": "component-1",
        "RANSOMEYE_DPI_CAPTURE_BACKEND": "replay",
        "RANSOMEYE_DPI_FLOW_TIMEOUT": "1",
        "RANSOMEYE_DPI_HEARTBEAT_SECONDS": "1",
        "RANSOMEYE_DPI_REPLAY_PATH": str(tmp_path / "frames.jsonl"),
        "RANSOMEYE_DPI_PRIVACY_MODE": "FORENSIC",
        "RANSOMEYE_DPI_IP_REDACTION": "none",
        "RANSOMEYE_DPI_PORT_REDACTION": "none",
    }

    dpi_main.run_dpi_probe(config)
    assert len(events) >= 1
