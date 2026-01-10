# RansomEye v1.0 Linux Agent (Phase 4 - Minimal)

**AUTHORITATIVE**: Minimal Linux agent implementing canonical event envelope contract for Phase 4 proof-of-concept.

---

## What This Component Does

This component **ONLY** implements the minimal event envelope construction and transmission required for Phase 4 validation:

1. **Reads Environment Variables** (contract compliance: `env.contract.json`):
   - `RANSOMEYE_COMPONENT_INSTANCE_ID` (required)
   - `RANSOMEYE_VERSION` (required)
   - `RANSOMEYE_INGEST_URL` (optional, defaults to `http://localhost:8000/events`)

2. **Constructs Canonical Event Envelope** (contract compliance: `event-envelope.schema.json`):
   - `event_id`: UUID v4 (generated)
   - `machine_id`: System hostname
   - `component`: Exactly `"linux_agent"` (contract enum value)
   - `component_instance_id`: From environment variable
   - `observed_at`: RFC3339 UTC timestamp (current time)
   - `ingested_at`: RFC3339 UTC timestamp (same as observed_at, ingest service will update)
   - `sequence`: `0` (first event, per schema constraint)
   - `payload`: Minimal JSON object with `{"phase": "phase4_minimal"}` (explicitly allowed for Phase 4)
   - `identity.hostname`: System hostname
   - `identity.boot_id`: From `/proc/sys/kernel/random/boot_id`
   - `identity.agent_version`: From environment variable
   - `integrity.hash_sha256`: SHA256 hash of envelope (computed with hash_sha256 set to empty string)
   - `integrity.prev_hash_sha256`: `null` (first event, sequence=0)

3. **Transmits Event via HTTP** (contract compliance: No retries, no batching):
   - Single HTTP POST request to ingest service
   - JSON payload (event envelope)
   - No retry logic (Phase 4 requirement)
   - No buffering (Phase 4 requirement)
   - Fails immediately if transmission fails

---

## What This Component Explicitly Does NOT Do

**Phase 4 Requirements - Forbidden Behaviors**:

- ❌ **NO local persistence**: Does not store events locally
- ❌ **NO retries**: Does not retry failed transmissions
- ❌ **NO batching**: Does not batch multiple events
- ❌ **NO enrichment**: Does not enrich events with additional data
- ❌ **NO inference**: Does not perform any analysis or inference
- ❌ **NO filesystem/process monitoring**: Does not monitor filesystem or processes
- ❌ **NO background threads**: Does not use background threads or async processing

**General Forbidden Behaviors**:

- ❌ **NO path computation**: All paths come from environment variables (contract compliance)
- ❌ **NO hardcoded values**: All configuration comes from environment variables
- ❌ **NO correlation**: Does not correlate events with other events
- ❌ **NO heuristics**: Does not use heuristics or machine learning
- ❌ **NO enrichment**: Does not enrich events with external data

---

## How This Proves Phase 4 Correctness

### Validation Criteria (PASS / FAIL)

**PASS if**:
1. ✅ **One event is accepted**: Agent constructs exactly one event envelope
2. ✅ **Event envelope is canonical**: All fields match `event-envelope.schema.json` exactly
3. ✅ **Hash integrity is valid**: `hash_sha256` is computed correctly (ingest service verifies)
4. ✅ **Sequence is correct**: `sequence=0` with `prev_hash_sha256=null` (first event, per schema)
5. ✅ **Timestamps are valid**: RFC3339 UTC format (ingest service validates)
6. ✅ **Transmission is successful**: HTTP POST succeeds, ingest service accepts event

**FAIL if**:
1. ❌ **Anything "helpful" is added**: Any additional logic beyond minimal event construction
2. ❌ **Future logic leaks in**: Any enrichment, correlation, or inference logic
3. ❌ **Contract violations**: Any deviation from `event-envelope.schema.json` or `env.contract.json`
4. ❌ **Forbidden behaviors**: Any retry, batching, persistence, or background processing

### Contract Compliance

1. **Event Envelope Contract** (`event-envelope.schema.json`):
   - ✅ All required fields present
   - ✅ All fields match schema exactly (types, formats, constraints)
   - ✅ `component` enum value matches exactly (`"linux_agent"`)
   - ✅ `sequence` is uint64 (0 for first event)
   - ✅ `prev_hash_sha256` is null for first event
   - ✅ Hash computation follows standard practice (hash with hash_sha256 empty, then set)

2. **Environment Variable Contract** (`env.contract.json`):
   - ✅ All required environment variables read
   - ✅ No path computation (no paths used in this component)
   - ✅ Fail-closed: Missing required variables cause immediate failure

3. **Time Semantics Contract** (`time-semantics.md`):
   - ✅ `observed_at` is RFC3339 UTC format
   - ✅ `ingested_at` is RFC3339 UTC format (set by ingest service, but we provide initial value)

4. **Failure Semantics Contract** (`failure-semantics.md`):
   - ✅ No silent failures: All errors are explicit
   - ✅ Fail-closed: Missing environment variables or transmission failure causes immediate exit

---

## Build Instructions

```bash
cd services/linux-agent
cargo build --release
```

## Run Instructions

```bash
# Set required environment variables
export RANSOMEYE_COMPONENT_INSTANCE_ID="550e8400-e29b-41d4-a716-446655440000"
export RANSOMEYE_VERSION="1.0.0"
export RANSOMEYE_INGEST_URL="http://localhost:8000/events"  # Optional

# Run agent
./target/release/ransomeye-linux-agent
```

---

## Proof of Phase 4 Correctness

**Phase 4 Objective**: Prove that one valid event can be created, transmitted, validated, and stored.

**This component proves**:
- ✅ **Event creation**: Constructs canonical event envelope matching all contract requirements
- ✅ **Event transmission**: Transmits event to ingest service via HTTP (no retries, no batching)
- ✅ **Contract compliance**: All fields match frozen contracts from Phase 1 exactly

**Ingest service proves**:
- ✅ **Event validation**: Validates event against schema and time semantics
- ✅ **Event storage**: Stores event in database (machines, component_instances, raw_events, event_validation_log)
- ✅ **Duplicate detection**: Detects duplicate events (event_id + sequence)
- ✅ **Hash integrity**: Verifies hash_sha256 integrity

**Together, they prove**:
- ✅ **One valid event → validated → stored → queryable**: Complete Phase 4 objective

---

## Operational Hardening Guarantees

**Phase 10.1 requirement**: Startup validation, fail-fast invariants, and graceful shutdown.

### Startup Validation

- ✅ **Environment Variables**: All required environment variables are validated at startup (`RANSOMEYE_COMPONENT_INSTANCE_ID`, `RANSOMEYE_VERSION`). Missing variables cause immediate failure (non-zero exit code).
- ✅ **Configuration Validation**: All configuration values are validated before use. Invalid values cause immediate failure.
- ✅ **Fail-Fast on Misconfiguration**: If any required configuration is missing or invalid, the agent exits immediately with a clear error message.

### Fail-Fast Invariants

- ✅ **Missing Environment Variables**: If any required environment variable is missing, the agent terminates immediately with exit code `CONFIG_ERROR` (1).
- ✅ **Invalid Configuration**: If any configuration value is invalid (e.g., invalid URL format), the agent terminates immediately with exit code `CONFIG_ERROR` (1).
- ✅ **Transmission Failure**: If event transmission fails, the agent exits immediately with exit code `FATAL_ERROR` (4). No retries, no recovery.

### Graceful Shutdown

- ✅ **Signal Handling**: The agent handles SIGTERM and SIGINT gracefully:
  - Stops accepting new work (no new events generated).
  - Completes in-flight transmissions if possible.
  - Exits cleanly with exit code `SUCCESS` (0).
- ✅ **Clean Exit**: All errors are logged explicitly before exit. No silent crashes.

### Exit Codes

- `SUCCESS` (0): Normal completion or graceful shutdown
- `CONFIG_ERROR` (1): Missing or invalid configuration (environment variables)
- `FATAL_ERROR` (4): Fatal error during execution (transmission failure, etc.)

### Logging

- ✅ **Structured Logging**: All startup, shutdown, and failure events are logged explicitly.
- ✅ **Error Context**: All errors include context (what failed, why it failed, what the agent was doing).

---

**END OF README**
