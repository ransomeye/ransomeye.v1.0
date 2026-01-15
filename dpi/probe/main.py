#!/usr/bin/env python3
"""
RansomEye v1.0 DPI Probe (Unified Runtime)
AUTHORITATIVE: Production-grade DPI pipeline (capture → flow → redaction → telemetry)
Python 3.10+ only
"""

import base64
import ctypes
import hashlib
import json
import os
import select
import socket
import struct
import sys
import threading
import time
import uuid
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.config import ConfigLoader, ConfigError
    from common.logging import setup_logging
    from common.shutdown import ShutdownHandler, ExitCode, exit_config_error, exit_startup_error
    from common.security.service_auth import ServiceAuthManager, ServiceAuthError
    _common_available = True
except ImportError:
    _common_available = False
    class ConfigLoader:
        def __init__(self, name): self.config = {}; self.required_vars = []
        def require(self, *args, **kwargs): return self
        def optional(self, *args, **kwargs): return self
        def load(self): return {}
    class ConfigError(Exception):
        pass
    class ServiceAuthManager:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("Service auth not available")
    class ServiceAuthError(Exception):
        pass
    def setup_logging(name):
        class Logger:
            def info(self, m, **k): print(m)
            def error(self, m, **k): print(m, file=sys.stderr)
            def warning(self, m, **k): print(m, file=sys.stderr)
            def fatal(self, m, **k): print(f"FATAL: {m}", file=sys.stderr)
            def startup(self, m, **k): print(f"STARTUP: {m}")
            def shutdown(self, m, **k): print(f"SHUTDOWN: {m}")
            def config_error(self, m, **k): print(f"CONFIG_ERROR: {m}", file=sys.stderr)
        return Logger()
    class ShutdownHandler:
        def __init__(self, *args, **kwargs): pass
        def is_shutdown_requested(self): return False
        def exit(self, code): sys.exit(code)
    class ExitCode:
        SUCCESS = 0
        CONFIG_ERROR = 1
        STARTUP_ERROR = 2
        FATAL_ERROR = 4
    def exit_config_error(m):
        print(f"CONFIG_ERROR: {m}", file=sys.stderr)
        sys.exit(1)
    def exit_startup_error(m):
        print(f"STARTUP_ERROR: {m}", file=sys.stderr)
        sys.exit(2)

try:
    import nacl.signing
    import nacl.encoding
    _nacl_available = True
except ImportError:
    _nacl_available = False

# Import DPI engine components
_dpi_engine_dir = Path(_project_root) / "dpi-advanced" / "engine"
if str(_dpi_engine_dir) not in sys.path:
    sys.path.insert(0, str(_dpi_engine_dir))

from flow_assembler import FlowAssembler
from privacy_redactor import PrivacyRedactor
from behavior_model import BehaviorModel


logger = setup_logging('dpi-probe')
shutdown_handler = ShutdownHandler('dpi-probe', cleanup_func=lambda: _cleanup())


def _cleanup():
    logger.shutdown("DPI Probe shutting down")


def _assert_supervised():
    if os.getenv("RANSOMEYE_SUPERVISED") != "1":
        error_msg = "DPI Probe must be started by Core orchestrator"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)
    core_pid = os.getenv("RANSOMEYE_CORE_PID")
    core_token = os.getenv("RANSOMEYE_CORE_TOKEN")
    if not core_pid or not core_token:
        error_msg = "DPI Probe missing Core supervision metadata"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)
    try:
        uuid.UUID(core_token)
    except Exception:
        error_msg = "DPI Probe invalid Core token"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)
    if os.getppid() != int(core_pid):
        error_msg = "DPI Probe parent PID mismatch"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)


def _get_machine_id() -> str:
    machine_id = socket.gethostname().strip()
    if not machine_id:
        raise RuntimeError("machine_id is empty")
    return machine_id


def _get_boot_id() -> str:
    boot_id_path = "/proc/sys/kernel/random/boot_id"
    try:
        boot_id = Path(boot_id_path).read_text(encoding="utf-8").strip()
    except Exception as exc:
        raise RuntimeError(f"Failed to read boot_id from {boot_id_path}: {exc}") from exc
    if not boot_id:
        raise RuntimeError("boot_id is empty")
    return boot_id


class TelemetrySigner:
    """Signs event envelopes with ed25519."""

    def __init__(self, key_dir: Path, private_key_path: Optional[Path] = None):
        if not _nacl_available:
            raise RuntimeError("PyNaCl not available - telemetry signing required")
        self.key_dir = key_dir
        self.key_dir.mkdir(parents=True, exist_ok=True)
        self.private_key_path = private_key_path or (self.key_dir / "dpi.key")
        self.signer = None
        self.key_id = None
        self._load_or_create_key()

    def _load_or_create_key(self) -> None:
        if self.private_key_path.exists():
            key_data = self.private_key_path.read_bytes()
            self.signer = nacl.signing.SigningKey(key_data)
        else:
            self.signer = nacl.signing.SigningKey.generate()
            self.private_key_path.write_bytes(self.signer.encode())
            os.chmod(self.private_key_path, 0o600)

        public_key = self.signer.verify_key.encode()
        self.key_id = hashlib.sha256(public_key).hexdigest()
        public_key_path = self.key_dir / f"{self.key_id}.pub"
        if not public_key_path.exists():
            public_key_path.write_bytes(public_key)
            os.chmod(public_key_path, 0o644)

    def sign_envelope(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        envelope_copy = envelope.copy()
        envelope_copy['integrity'] = envelope_copy['integrity'].copy()
        envelope_copy['integrity']['hash_sha256'] = ''

        envelope_json = json.dumps(envelope_copy, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        envelope_hash = hashlib.sha256(envelope_json.encode('utf-8')).hexdigest()

        signature_bytes = self.signer.sign(envelope_hash.encode('utf-8')).signature
        envelope['integrity']['hash_sha256'] = envelope_hash
        envelope['signature'] = base64.b64encode(signature_bytes).decode('ascii')
        envelope['signing_key_id'] = self.key_id
        return envelope


class EventEnvelopeBuilder:
    """Build canonical DPI event envelopes."""

    def __init__(self, machine_id: str, component_instance_id: str, hostname: str, boot_id: str, agent_version: str):
        self.machine_id = machine_id
        self.component_instance_id = component_instance_id
        self.hostname = hostname
        self.boot_id = boot_id
        self.agent_version = agent_version
        self._sequence = 0
        self._sequence_lock = threading.Lock()
        self._prev_hash: Optional[str] = None

    def build(self, payload: Dict[str, Any], observed_at: datetime) -> Dict[str, Any]:
        with self._sequence_lock:
            sequence = self._sequence
            self._sequence += 1

        envelope = {
            'event_id': str(uuid.uuid4()),
            'machine_id': self.machine_id,
            'component': 'dpi',
            'component_instance_id': self.component_instance_id,
            'observed_at': observed_at.isoformat().replace('+00:00', 'Z'),
            'ingested_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'sequence': sequence,
            'payload': payload,
            'identity': {
                'hostname': self.hostname,
                'boot_id': self.boot_id,
                'agent_version': self.agent_version
            },
            'integrity': {
                'hash_sha256': '',
                'prev_hash_sha256': self._prev_hash
            }
        }
        return envelope

    def update_prev_hash(self, hash_value: str) -> None:
        self._prev_hash = hash_value


class AFPacketCLibrary:
    def __init__(self, lib_path: Path):
        if not lib_path.exists():
            raise RuntimeError(f"AF_PACKET library not found: {lib_path}")
        self.lib = ctypes.CDLL(str(lib_path))
        self.lib.af_packet_open.argtypes = [ctypes.c_char_p]
        self.lib.af_packet_open.restype = ctypes.c_int
        self.lib.af_packet_read.argtypes = [
            ctypes.c_int, ctypes.c_void_p, ctypes.c_int,
            ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_long), ctypes.POINTER(ctypes.c_long)
        ]
        self.lib.af_packet_read.restype = ctypes.c_int
        self.lib.af_packet_close.argtypes = [ctypes.c_int]
        self.lib.af_packet_close.restype = None


class AFPacketCapture:
    def __init__(self, interface: str, lib_path: Path, buffer_size: int = 65535):
        self.interface = interface
        self.buffer_size = buffer_size
        self.library = AFPacketCLibrary(lib_path)
        self.fd = self.library.lib.af_packet_open(interface.encode('utf-8'))
        if self.fd < 0:
            raise RuntimeError(f"AF_PACKET open failed for interface {interface}")
        self.buffer = (ctypes.c_ubyte * self.buffer_size)()

    def read(self, timeout_seconds: float) -> Optional[Tuple[bytes, datetime]]:
        ready, _, _ = select.select([self.fd], [], [], timeout_seconds)
        if not ready:
            return None
        out_len = ctypes.c_int(0)
        out_sec = ctypes.c_long(0)
        out_nsec = ctypes.c_long(0)
        result = self.library.lib.af_packet_read(
            self.fd,
            ctypes.byref(self.buffer),
            self.buffer_size,
            ctypes.byref(out_len),
            ctypes.byref(out_sec),
            ctypes.byref(out_nsec)
        )
        if result != 0 or out_len.value <= 0:
            raise RuntimeError("AF_PACKET read failed")
        timestamp = datetime.fromtimestamp(out_sec.value + (out_nsec.value / 1e9), tz=timezone.utc)
        frame = bytes(self.buffer[:out_len.value])
        return frame, timestamp

    def close(self) -> None:
        self.library.lib.af_packet_close(self.fd)


class ReplayCapture:
    def __init__(self, replay_path: Path):
        if not replay_path.exists():
            raise RuntimeError(f"Replay file not found: {replay_path}")
        self.frames = []
        for line in replay_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            frame = base64.b64decode(record['frame_b64'])
            ts = record.get('timestamp')
            if ts:
                timestamp = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            else:
                timestamp = datetime.now(timezone.utc)
            self.frames.append((frame, timestamp))
        self.index = 0

    def read(self, timeout_seconds: float) -> Optional[Tuple[bytes, datetime]]:
        if self.index >= len(self.frames):
            time.sleep(timeout_seconds)
            return None
        frame = self.frames[self.index]
        self.index += 1
        return frame

    def close(self) -> None:
        return None


def _parse_frame(frame: bytes, timestamp: datetime) -> Optional[Dict[str, Any]]:
    if len(frame) < 14:
        return None
    ethertype = struct.unpack("!H", frame[12:14])[0]
    if ethertype != 0x0800:
        return None
    ip_offset = 14
    if len(frame) < ip_offset + 20:
        return None
    version_ihl = frame[ip_offset]
    ihl = (version_ihl & 0x0F) * 4
    if ihl < 20:
        return None
    if len(frame) < ip_offset + ihl:
        return None
    protocol = frame[ip_offset + 9]
    src_ip = socket.inet_ntoa(frame[ip_offset + 12:ip_offset + 16])
    dst_ip = socket.inet_ntoa(frame[ip_offset + 16:ip_offset + 20])
    payload_offset = ip_offset + ihl
    src_port = 0
    dst_port = 0
    if protocol in (6, 17) and len(frame) >= payload_offset + 4:
        src_port, dst_port = struct.unpack("!HH", frame[payload_offset:payload_offset + 4])
    protocol_name = {6: 'tcp', 17: 'udp'}.get(protocol, 'other')

    return {
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "src_port": src_port,
        "dst_port": dst_port,
        "protocol": protocol_name,
        "packet_size": len(frame),
        "timestamp": timestamp
    }


def _send_event(ingest_url: str, envelope: Dict[str, Any], auth_manager: ServiceAuthManager) -> None:
    payload = json.dumps(envelope, separators=(",", ":"), ensure_ascii=False).encode('utf-8')
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_manager.get_auth_token('ingest')}"
    }
    request = urllib.request.Request(ingest_url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            if response.status != 200:
                raise RuntimeError(f"Ingest rejected telemetry (status {response.status})")
    except Exception as exc:
        raise RuntimeError(f"Telemetry transmission failed: {exc}") from exc


def _build_flow_payload(flow: Dict[str, Any], capture_meta: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "event_type": "dpi.flow",
        "capture": capture_meta,
        "flow": {
            "flow_id": flow.get("flow_id"),
            "src_ip": flow.get("src_ip"),
            "dst_ip": flow.get("dst_ip"),
            "src_port": flow.get("src_port"),
            "dst_port": flow.get("dst_port"),
            "protocol": flow.get("protocol"),
            "packet_count": flow.get("packet_count"),
            "byte_count": flow.get("byte_count"),
            "flow_start": flow.get("flow_start"),
            "flow_end": flow.get("flow_end"),
            "behavioral_profile_id": flow.get("behavioral_profile_id", ""),
            "immutable_hash": flow.get("immutable_hash")
        }
    }


def _build_heartbeat_payload(capture_meta: Dict[str, Any], counters: Dict[str, int]) -> Dict[str, Any]:
    return {
        "event_type": "dpi.heartbeat",
        "capture": capture_meta,
        "counters": counters
    }


def run_dpi_probe(config: Dict[str, Any]) -> None:
    ingest_url = config["RANSOMEYE_INGEST_URL"]
    interface = config["RANSOMEYE_DPI_INTERFACE"]
    component_instance_id = config["RANSOMEYE_COMPONENT_INSTANCE_ID"]
    capture_backend = config["RANSOMEYE_DPI_CAPTURE_BACKEND"]
    flow_timeout = int(config["RANSOMEYE_DPI_FLOW_TIMEOUT"])
    heartbeat_seconds = int(config["RANSOMEYE_DPI_HEARTBEAT_SECONDS"])
    replay_path = config.get("RANSOMEYE_DPI_REPLAY_PATH")

    if capture_backend == "replay":
        if os.getenv("CI") != "true" or os.getenv("RANSOMEYE_ENV") != "ci":
            raise RuntimeError("Replay backend is only allowed in CI with RANSOMEYE_ENV=ci")
        if not replay_path:
            raise RuntimeError("Replay backend requires RANSOMEYE_DPI_REPLAY_PATH")

    machine_id = _get_machine_id()
    boot_id = _get_boot_id()
    hostname = machine_id
    agent_version = os.getenv("RANSOMEYE_VERSION", "1.0.0")

    key_dir = Path(os.getenv("RANSOMEYE_COMPONENT_KEY_DIR", os.path.join(os.getenv("RANSOMEYE_INSTALL_ROOT", "/opt/ransomeye"), "config", "component-keys")))
    signer = TelemetrySigner(key_dir=key_dir)
    envelope_builder = EventEnvelopeBuilder(
        machine_id=machine_id,
        component_instance_id=component_instance_id,
        hostname=hostname,
        boot_id=boot_id,
        agent_version=agent_version
    )

    try:
        auth_manager = ServiceAuthManager(service_name="ingest")
    except ServiceAuthError as exc:
        raise RuntimeError(f"Service auth initialization failed: {exc}") from exc

    if capture_backend == "af_packet_c":
        if sys.platform != "linux":
            raise RuntimeError("AF_PACKET capture requires Linux kernel")
        lib_path = Path(os.getenv(
            "RANSOMEYE_DPI_FASTPATH_LIB",
            os.path.join(os.getenv("RANSOMEYE_INSTALL_ROOT", "/opt/ransomeye"), "lib", "libransomeye_dpi_af_packet.so")
        ))
        capture = AFPacketCapture(interface=interface, lib_path=lib_path)
    elif capture_backend == "replay":
        capture = ReplayCapture(Path(replay_path))
    else:
        raise RuntimeError(f"Unsupported capture backend: {capture_backend}")

    flow_assembler = FlowAssembler(flow_timeout=flow_timeout)
    behavior_model = BehaviorModel()
    privacy_redactor = PrivacyRedactor({
        "privacy_mode": config["RANSOMEYE_DPI_PRIVACY_MODE"],
        "ip_redaction": config["RANSOMEYE_DPI_IP_REDACTION"],
        "port_redaction": config["RANSOMEYE_DPI_PORT_REDACTION"],
        "dns_redaction": "none"
    })

    capture_meta = {
        "backend": capture_backend,
        "interface": interface
    }
    counters = {"packets_seen": 0, "flows_emitted": 0, "heartbeats_sent": 0}
    last_heartbeat = time.time()

    logger.startup("DPI Probe starting", backend=capture_backend, interface=interface)

    try:
        while not shutdown_handler.is_shutdown_requested():
            now = datetime.now(timezone.utc)
            frame_result = capture.read(timeout_seconds=1.0)
            if frame_result:
                frame, timestamp = frame_result
                parsed = _parse_frame(frame, timestamp)
                if parsed:
                    counters["packets_seen"] += 1
                    completed_flow = flow_assembler.process_packet(
                        src_ip=parsed["src_ip"],
                        dst_ip=parsed["dst_ip"],
                        src_port=parsed["src_port"],
                        dst_port=parsed["dst_port"],
                        protocol=parsed["protocol"],
                        packet_size=parsed["packet_size"],
                        timestamp=parsed["timestamp"]
                    )
                    if completed_flow:
                        behavior = behavior_model.analyze_flow(completed_flow)
                        completed_flow["behavioral_profile_id"] = behavior.get("profile_id", "")
                        redacted_flow = privacy_redactor.redact_flow(completed_flow)
                        payload = _build_flow_payload(redacted_flow, capture_meta)
                        envelope = envelope_builder.build(payload, observed_at=timestamp)
                        signed = signer.sign_envelope(envelope)
                        _send_event(ingest_url, signed, auth_manager)
                        envelope_builder.update_prev_hash(signed["integrity"]["hash_sha256"])
                        counters["flows_emitted"] += 1

            expired_flows = flow_assembler.flush_expired(now)
            for expired_flow in expired_flows:
                behavior = behavior_model.analyze_flow(expired_flow)
                expired_flow["behavioral_profile_id"] = behavior.get("profile_id", "")
                redacted_flow = privacy_redactor.redact_flow(expired_flow)
                payload = _build_flow_payload(redacted_flow, capture_meta)
                envelope = envelope_builder.build(payload, observed_at=now)
                signed = signer.sign_envelope(envelope)
                _send_event(ingest_url, signed, auth_manager)
                envelope_builder.update_prev_hash(signed["integrity"]["hash_sha256"])
                counters["flows_emitted"] += 1

            if time.time() - last_heartbeat >= heartbeat_seconds:
                heartbeat_payload = _build_heartbeat_payload(capture_meta, counters)
                envelope = envelope_builder.build(heartbeat_payload, observed_at=now)
                signed = signer.sign_envelope(envelope)
                _send_event(ingest_url, signed, auth_manager)
                envelope_builder.update_prev_hash(signed["integrity"]["hash_sha256"])
                counters["heartbeats_sent"] += 1
                last_heartbeat = time.time()
    finally:
        capture.close()


if __name__ == "__main__":
    try:
        _assert_supervised()
        if not _nacl_available:
            raise RuntimeError("PyNaCl is required for telemetry signing")

        config_loader = ConfigLoader('dpi-probe')
        config_loader.require('RANSOMEYE_INGEST_URL')
        config_loader.require('RANSOMEYE_COMPONENT_INSTANCE_ID')
        config_loader.require('RANSOMEYE_DPI_INTERFACE')
        config_loader.optional('RANSOMEYE_DPI_CAPTURE_BACKEND', default='af_packet_c')
        config_loader.optional('RANSOMEYE_DPI_FLOW_TIMEOUT', default='300')
        config_loader.optional('RANSOMEYE_DPI_HEARTBEAT_SECONDS', default='5')
        config_loader.optional('RANSOMEYE_DPI_REPLAY_PATH', default='')
        config_loader.optional('RANSOMEYE_DPI_PRIVACY_MODE', default='FORENSIC')
        config_loader.optional('RANSOMEYE_DPI_IP_REDACTION', default='none')
        config_loader.optional('RANSOMEYE_DPI_PORT_REDACTION', default='none')
        config = config_loader.load()

        run_dpi_probe(config)
        logger.shutdown("DPI Probe completed successfully")
        sys.exit(ExitCode.SUCCESS)
    except KeyboardInterrupt:
        logger.shutdown("Received interrupt, shutting down")
        shutdown_handler.exit(ExitCode.SUCCESS)
    except ConfigError as e:
        logger.config_error(str(e))
        sys.exit(ExitCode.CONFIG_ERROR)
    except Exception as e:
        logger.fatal(f"Fatal error: {e}")
        shutdown_handler.exit(ExitCode.FATAL_ERROR)
