# RansomEye DPI Engine (Unified Runtime Backend)

**AUTHORITATIVE:** Carrier-grade, high-performance network intelligence engine

## Overview

The RansomEye DPI Engine provides the internal pipeline used by the unified DPI runtime. It provides line-rate traffic observation, flow-level behavioral modeling, asset classification, privacy-preserving redaction, and deterministic hashing for evidence integrity.

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

## Telemetry

Telemetry emission is handled by the unified DPI runtime (`dpi/probe/main.py`).

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

This engine is invoked by `dpi/probe/main.py` and is not a standalone runtime.

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
│   └── privacy_redactor.py            # Privacy-preserving redaction
├── performance/
│   ├── throughput_benchmark.py        # Throughput benchmark
│   ├── latency_benchmark.py          # Latency benchmark
│   └── cpu_profile.md                 # CPU profile documentation
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
