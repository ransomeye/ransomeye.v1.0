# Validation Step 11 — DPI Probe Network Truth (Unified Runtime)

**Component Identity:**
- **Name:** DPI Probe (Passive Network Sensor)
- **Primary Paths:**
  - `/home/ransomeye/rebuild/dpi/probe/main.py` - Unified DPI runtime entrypoint
  - `/home/ransomeye/rebuild/dpi-advanced/fastpath/af_packet_capture.c` - AF_PACKET capture backend
  - `/home/ransomeye/rebuild/dpi-advanced/engine/flow_assembler.py` - Flow assembly
  - `/home/ransomeye/rebuild/dpi-advanced/engine/privacy_redactor.py` - Privacy redaction
- **Entry Point:**
  - `dpi/probe/main.py` - Unified runtime (capture → flow → redaction → telemetry)

**Master Spec References:**
- Phase 15.20 — DPI Probe Advanced Engine (10G / eBPF / AF_PACKET Fast-Path)
- DPI Probe README (`dpi/probe/README.md`)
- DPI Advanced Engine README (`dpi-advanced/README.md`)

---

## PURPOSE

This validation proves that the unified DPI runtime captures accurate network truth, preserves privacy boundaries, and emits signed telemetry into Ingest.

This file validates:
- Packet/flow capture guarantees
- Time semantics (capture_time vs ingest_time)
- Privacy enforcement (no payload leakage if forbidden)
- Integrity & tamper resistance (event integrity chain)
- Credential & trust usage (telemetry signing)

---

## DPI PROBE DEFINITION

**DPI Probe Requirements (Unified Runtime):**

1. **Packet/Flow Capture Guarantees** — Accurate packet/flow capture, deterministic flow assembly
2. **Time Semantics** — capture_time (packet timestamp) vs ingest_time (ingested_at) separation
3. **Privacy Enforcement** — No payload leakage if forbidden, privacy redaction is enforced
4. **Integrity & Tamper Resistance** — Event integrity chain and signed telemetry
5. **Credential & Trust Usage** — DPI telemetry keys are enforced

**DPI Probe Structure:**
- **Entry Point:** Packet capture loop (AF_PACKET)
- **Processing Chain:** Capture packet → Assemble flow → Redact privacy → Emit telemetry

---

## WHAT IS VALIDATED

### 1. Packet/Flow Capture Guarantees
- Accurate packet/flow capture
- Deterministic flow assembly

### 2. Time Semantics
- capture_time (packet timestamp) vs ingest_time (ingested_at) separation

### 3. Privacy Enforcement
- No payload leakage if forbidden
- Privacy redaction is enforced before telemetry

### 4. Integrity & Tamper Resistance
- Event integrity chain is present
- Telemetry signatures validated by Ingest

### 5. Credential & Trust Usage
- Key material is stored and enforced correctly
- No hardcoded credentials
