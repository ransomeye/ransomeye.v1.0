# RansomEye v1.0 DPI Probe (Phase 10 - Stub Runtime)

**AUTHORITATIVE**: Stubbed DPI probe runtime with capture disabled for Phase 10.

---

## What This Component Does

This component is a **stub runtime** for the DPI Probe:

1. **Validates Configuration** (contract compliance: `env.contract.json`):
   - Validates required environment variables
   - Validates optional configuration (ports, paths, etc.)
   - Fails immediately if required configuration is missing

2. **Logs Startup and Shutdown**:
   - Explicit startup logging
   - Explicit shutdown logging
   - No capture or processing (disabled for Phase 10)

3. **Handles Shutdown Gracefully**:
   - Handles SIGTERM and SIGINT signals
   - Exits cleanly with appropriate exit codes

---

## What This Component Explicitly Does NOT Do

**Phase 10 Requirements - Forbidden Behaviors**:

- ❌ **NO packet capture**: Packet capture is disabled (stub runtime)
- ❌ **NO network analysis**: No network analysis performed
- ❌ **NO event generation**: No events are generated or transmitted
- ❌ **NO background threads**: No background threads or async processing
- ❌ **NO retries**: No retry logic (fail-fast only)

---

## Build Instructions

```bash
# No build required - Python script only
cd dpi/probe
```

## Run Instructions

```bash
# Set required environment variables (if any)
# (Currently no required variables for stub runtime)

# Run DPI probe stub
python3 main.py
```

---

## Operational Hardening Guarantees

**Phase 10.1 requirement**: Startup validation, fail-fast invariants, and graceful shutdown.

### Startup Validation

- ✅ **Environment Variables**: All required environment variables are validated at startup. Missing variables cause immediate failure (non-zero exit code).
- ✅ **Configuration Validation**: All configuration values are validated before use. Invalid values cause immediate failure.
- ✅ **Fail-Fast on Misconfiguration**: If any required configuration is missing or invalid, the probe exits immediately with a clear error message.

### Fail-Fast Invariants

- ✅ **Missing Environment Variables**: If any required environment variable is missing, the probe terminates immediately with exit code `CONFIG_ERROR` (1).
- ✅ **Invalid Configuration**: If any configuration value is invalid, the probe terminates immediately with exit code `CONFIG_ERROR` (1).
- ✅ **Fatal Errors**: If any fatal error occurs during execution, the probe exits immediately with exit code `FATAL_ERROR` (4). No retries, no recovery.

### Graceful Shutdown

- ✅ **Signal Handling**: The probe handles SIGTERM and SIGINT gracefully:
  - Stops accepting new work (no new capture operations).
  - Completes any in-flight operations if possible.
  - Exits cleanly with exit code `SUCCESS` (0).
- ✅ **Clean Exit**: All errors are logged explicitly before exit. No silent crashes.

### Exit Codes

- `SUCCESS` (0): Normal completion or graceful shutdown
- `CONFIG_ERROR` (1): Missing or invalid configuration (environment variables)
- `STARTUP_ERROR` (2): Startup validation failure
- `FATAL_ERROR` (4): Fatal error during execution

### Logging

- ✅ **Structured Logging**: All startup, shutdown, and failure events are logged explicitly.
- ✅ **Error Context**: All errors include context (what failed, why it failed, what the probe was doing).

---

**END OF README**
