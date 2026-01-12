# RansomEye DPI Advanced Engine (10G / eBPF / AF_PACKET Fast-Path)

**AUTHORITATIVE:** Carrier-grade, high-performance network intelligence engine

## Overview

The RansomEye DPI Advanced Engine upgrades the DPI Probe from a **functional sensor** to a **carrier-grade, high-performance network intelligence engine** capable of sustaining **10G+ traffic** with **provable performance and privacy guarantees**. It provides line-rate traffic observation, flow-level behavioral ML (local, bounded, explainable), asset classification, privacy-preserving redaction, and deterministic chunked upload with cryptographic enforcement.

## Core Principles

### Observation Only, At Scale

**CRITICAL**: DPI is observation only, at scale:

- ✅ **No payload storage**: No payload is ever persisted
- ✅ **No packet replay**: No packet replay capability
- ✅ **No MITM**: No man-in-the-middle
- ✅ **No active traffic modification**: No traffic modification
- ✅ **No credential extraction**: No credential extraction
- ✅ **No decryption**: No decryption of encrypted payloads
- ✅ **No cloud dependency**: No cloud dependency
- ✅ **No kernel patching**: No kernel patching

### Performance Targets (Mandatory)

**CRITICAL**: Performance must be proven, not claimed:

- ✅ **10 Gbps sustained throughput**: Proven with reproducible benchmarks
- ✅ **<5% CPU per 1 Gbps**: CPU efficiency target
- ✅ **Zero packet drops at 64-byte packets**: AF_PACKET requirement
- ✅ **Bounded memory**: Ring buffers only
- ✅ **Backpressure under congestion**: No OOM

## Fast-Path Implementation

### AF_PACKET

- **PACKET_MMAP (TPACKET_V3)**: Zero-copy packet capture
- **RX ring only**: Receive ring buffer
- **Zero-copy**: Direct memory mapping
- **CPU affinity pinning**: Core pinning for performance

### eBPF

- **Flow tuple extraction**: Extract 5-tuple from packets
- **L7 protocol fingerprinting**: Metadata-only protocol detection
- **Per-flow counters**: Flow statistics
- **No loops**: Verifier-safe code
- **Verifier-safe**: All eBPF code passes verifier

## Flow-Level ML (Strictly Local)

### Allowed

- **Sequence models on flow metadata only**: Packet size, timing, flags, protocol hints
- **Local processing**: All processing is local
- **Bounded computation**: Bounded computation time

### Forbidden

- **Payload inspection**: No payload inspection
- **Cross-host learning**: No cross-host learning
- **Cloud inference**: No cloud inference

### Outputs

- **Behavioral profile IDs**: Deterministic profile identifiers
- **Confidence bands**: Confidence levels
- **Feature vectors only**: Stored in HNMP-compatible form

## Asset Classification

### Inference

- **Device type**: server, workstation, IoT, network device
- **Role**: database, domain_controller, proxy, printer, web_server, mail_server, dns_server

### Based On

- **Port behavior**: Port usage patterns
- **Protocol mix**: Protocol combinations
- **Flow directionality**: Inbound vs outbound flows

### Requirements

- ✅ **Deterministic**: Same flows → same classification
- ✅ **Explainable**: All classifications are explainable
- ✅ **Replayable**: Classifications can be replayed

## Privacy Modes (Mandatory)

### STRICT

- **Hash IPs**: IP addresses are hashed
- **Truncate ports**: Ports are truncated
- **No DNS labels**: DNS labels are removed

### BALANCED

- **Partial IP retention**: First two octets retained
- **Domain second-level only**: Only second-level domain retained

### FORENSIC

- **Full metadata**: Full metadata (no payload)

**Redaction happens before storage and upload.**

## Upload Pipeline

- **Chunked uploads**: Uploads are chunked
- **Per-chunk SHA256**: Each chunk has SHA256 hash
- **Signed chunk manifests**: Manifests are signed (Ed25519)
- **Backpressure-aware**: Handles backpressure
- **Resume-safe**: Uploads can be resumed
- **Offline buffering**: Bounded offline buffering

**No silent drops.**

## Required Integrations

DPI Advanced Engine integrates with:

- **HNMP Engine**: Flow → network facts
- **Threat Graph**: Asset & flow edges
- **KillChain & Forensics**: Evidence references
- **Risk Index**: Signals only
- **Alert Engine**: Context only
- **Audit Ledger**: All actions
- **Global Validator**: Full replay

## Determinism Rules

- ✅ **Same packets → same flows**: Deterministic flow assembly
- ✅ **Same flows → same features**: Deterministic feature extraction
- ✅ **Same policies → same redaction**: Deterministic redaction
- ✅ **Same input → same output hashes**: Deterministic hashing

**No entropy.**

## Usage

### Run Probe

```bash
python3 dpi-advanced/cli/run_probe.py \
    --interface eth0 \
    --privacy-policy /path/to/privacy_policy.json \
    --flows-store /var/lib/ransomeye/dpi/flows.jsonl \
    --asset-profiles-store /var/lib/ransomeye/dpi/asset_profiles.jsonl \
    --upload-chunks-store /var/lib/ransomeye/dpi/upload_chunks.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --flow-timeout 300 \
    --chunk-size 1000
```

### Benchmark Probe

```bash
python3 dpi-advanced/cli/benchmark_probe.py \
    --benchmark-type both \
    --duration 60 \
    --packet-size 64 \
    --num-packets 100000 \
    --output benchmark_results.json
```

### Programmatic API

```python
from api.dpi_api import DPIAPI

api = DPIAPI(
    flows_store_path=Path('/var/lib/ransomeye/dpi/flows.jsonl'),
    asset_profiles_store_path=Path('/var/lib/ransomeye/dpi/asset_profiles.jsonl'),
    upload_chunks_store_path=Path('/var/lib/ransomeye/dpi/upload_chunks.jsonl'),
    privacy_policy={
        'privacy_mode': 'BALANCED',
        'ip_redaction': 'partial',
        'port_redaction': 'none',
        'dns_redaction': 'second_level_only'
    },
    ledger_path=Path('/var/lib/ransomeye/audit/ledger.jsonl'),
    ledger_key_dir=Path('/var/lib/ransomeye/audit/keys')
)

# Process packet
flow = api.process_packet(
    src_ip='192.168.1.10',
    dst_ip='192.168.1.20',
    src_port=12345,
    dst_port=80,
    protocol='tcp',
    packet_size=1500,
    timestamp=datetime.now(timezone.utc)
)
```

## File Structure

```
dpi-advanced/
├── schema/
│   ├── flow-record.schema.json          # Frozen JSON schema for flow records
│   ├── asset-profile.schema.json        # Frozen JSON schema for asset profiles
│   ├── upload-chunk.schema.json        # Frozen JSON schema for upload chunks
│   └── privacy-policy.schema.json      # Frozen JSON schema for privacy policies
├── fastpath/
│   ├── af_packet_capture.c             # AF_PACKET fast-path (C)
│   └── ebpf_flow_tracker.c             # eBPF flow tracker (C)
├── engine/
│   ├── __init__.py
│   ├── flow_assembler.py               # Deterministic flow assembly
│   ├── behavior_model.py              # Flow-level behavioral ML
│   ├── asset_classifier.py            # Asset classification
│   ├── privacy_redactor.py            # Privacy-preserving redaction
│   └── uploader.py                    # Chunked upload with crypto
├── performance/
│   ├── throughput_benchmark.py        # Throughput benchmark
│   ├── latency_benchmark.py          # Latency benchmark
│   └── cpu_profile.md                 # CPU profile documentation
├── api/
│   ├── __init__.py
│   └── dpi_api.py                     # DPI API with audit integration
├── cli/
│   ├── __init__.py
│   ├── run_probe.py                   # Run probe CLI
│   └── benchmark_probe.py             # Benchmark probe CLI
└── README.md                          # This file
```

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **C compiler**: Required for fast-path C code (gcc)
- **eBPF tools**: Required for eBPF compilation (clang, llvm)
- **libpcap**: Required for packet capture (optional, for fallback)
- **Audit Ledger**: Required for audit trail (separate subsystem)

## Security Considerations

1. **No Payload Storage**: No payload is ever persisted
2. **Privacy-First**: Privacy redaction before storage
3. **Cryptographic Integrity**: Upload chunks are cryptographically signed
4. **Deterministic**: Same inputs always produce same outputs
5. **Replayable**: All outputs can be replayed

## Limitations

1. **No Payload Inspection**: No payload inspection
2. **No Decryption**: No decryption of encrypted payloads
3. **No Cloud Dependency**: No cloud dependency
4. **Observation Only**: No active traffic modification
5. **Local ML Only**: All ML is local and bounded

## Future Enhancements

- Advanced eBPF programs
- Enhanced behavioral models
- Advanced asset classification
- Performance optimizations
- Hardware offload support

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye DPI Advanced Engine documentation.
