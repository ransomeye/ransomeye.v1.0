# RansomEye v1.0 DPI Probe (Unified Runtime)

**AUTHORITATIVE**: Production-grade DPI pipeline (capture → flow → redaction → telemetry).

---

## What This Component Does

This component is the **single runtime entrypoint** for DPI:

1. **Captures packets** using AF_PACKET fastpath (C library)
2. **Assembles flows** deterministically from packet metadata
3. **Applies privacy redaction** before any storage/transmission
4. **Builds event envelopes** per `contracts/event-envelope.schema.json`
5. **Transmits telemetry** to Core Ingest (`/events`) with signatures

---

## Runtime Requirements

- **Core supervision required**: probe refuses to start without Core
- **AF_PACKET required**: missing capabilities or library → startup failure
- **Telemetry signing required**: PyNaCl and component keys required
- **Ingest required**: any telemetry failure causes probe exit

---

## Build Instructions

```bash
# Build AF_PACKET fastpath library
gcc -shared -fPIC -O2 -o /opt/ransomeye/lib/libransomeye_dpi_af_packet.so \
  dpi-advanced/fastpath/af_packet_capture.c
```

---

## Configuration

Required environment variables:

- `RANSOMEYE_INGEST_URL`
- `RANSOMEYE_COMPONENT_INSTANCE_ID`
- `RANSOMEYE_DPI_INTERFACE`
- `RANSOMEYE_DPI_FASTPATH_LIB`
- `RANSOMEYE_COMPONENT_KEY_DIR`

Optional:

- `RANSOMEYE_DPI_CAPTURE_BACKEND` (default: `af_packet_c`)
- `RANSOMEYE_DPI_FLOW_TIMEOUT` (default: `300`)
- `RANSOMEYE_DPI_HEARTBEAT_SECONDS` (default: `5`)
- `RANSOMEYE_DPI_PRIVACY_MODE` (default: `FORENSIC`)
- `RANSOMEYE_DPI_IP_REDACTION` (default: `none`)
- `RANSOMEYE_DPI_PORT_REDACTION` (default: `none`)

---

## Operational Guarantees

- **Fail-fast on misconfiguration**
- **No stub loops**
- **No telemetry buffering**
- **Heartbeat telemetry** emitted even if traffic is idle

---

**END OF README**
