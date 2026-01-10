# RansomEye v1.0 Ingest Service (Phase 4 - Minimal)

**AUTHORITATIVE**: Minimal ingest service implementing canonical event validation and storage for Phase 4 proof-of-concept.

---

## What This Component Does

This component **ONLY** implements the minimal event validation and storage required for Phase 4 validation:

1. **Accepts Event via HTTP** (contract compliance: Single HTTP POST endpoint):
   - Endpoint: `POST /events`
   - Content-Type: `application/json`
   - Payload: Event envelope (JSON)

2. **Validates Event** (contract compliance: `event-envelope.schema.json`, `time-semantics.policy.json`):
   - **Schema Validation**: Validates against `event-envelope.schema.json` using `jsonschema`
   - **Timestamp Validation**: Validates RFC3339 UTC format, clock skew tolerance (5 seconds), age limit (30 days)
   - **Hash Integrity**: Verifies `hash_sha256` matches computed hash (excludes hash_sha256 field itself)
   - **Duplicate Detection**: Checks if `event_id` already exists in `raw_events` table

3. **Stores Event in Database** (contract compliance: Phase 4 requirements):
   - **machines**: Store or update machine record (machine-first modeling)
   - **component_instances**: Store or update component instance record
   - **raw_events**: Insert event envelope (immutable, never updated)
   - **event_validation_log**: Log validation result (success or failure)

4. **Updates ingested_at** (contract compliance: `time-semantics.md`):
   - Sets `ingested_at` to current UTC time (ingest service responsibility)
   - Validates timestamp semantics after update

---

## What This Component Explicitly Does NOT Do

**Phase 4 Requirements - Forbidden Behaviors**:

- ❌ **NO correlation**: Does not correlate events with other events or incidents
- ❌ **NO enrichment**: Does not enrich events with additional data or context
- ❌ **NO retry logic**: Does not retry failed database operations
- ❌ **NO background jobs**: Does not use background threads or async processing
- ❌ **NO AI/ML**: Does not perform any machine learning or AI operations
- ❌ **NO heuristics**: Does not use heuristics or pattern matching
- ❌ **NO inference**: Does not infer or deduce additional information

**General Forbidden Behaviors**:

- ❌ **NO path computation**: Database connection parameters come from environment variables
- ❌ **NO hardcoded values**: All configuration comes from environment variables
- ❌ **NO normalization**: Does not write to normalized tables (Phase 4 requirement: raw_events only)
- ❌ **NO sequence gap handling**: Does not handle sequence gaps (only detects duplicates)
- ❌ **NO integrity chain validation**: Does not validate `prev_hash_sha256` against previous event (Phase 4 minimal)

---

## How This Proves Phase 4 Correctness

### Validation Criteria (PASS / FAIL)

**PASS if**:
1. ✅ **One event is accepted**: HTTP POST `/events` accepts exactly one event
2. ✅ **One row exists in raw_events**: Event is stored in `raw_events` table exactly once
3. ✅ **Hash chain is valid**: `hash_sha256` verification passes
4. ✅ **No other tables are touched**: Only writes to `machines`, `component_instances`, `raw_events`, `event_validation_log` (Phase 4 requirement)
5. ✅ **Restarting ingest does NOT duplicate data**: Duplicate detection prevents duplicate events

**FAIL if**:
1. ❌ **Anything "helpful" is added**: Any additional logic beyond minimal validation and storage
2. ❌ **Future logic leaks in**: Any correlation, enrichment, retry, or background processing
3. ❌ **Schema violations**: Any deviation from `event-envelope.schema.json` or database schema
4. ❌ **Additional table writes**: Writing to normalized tables or other tables beyond Phase 4 requirement

### Contract Compliance

1. **Event Envelope Contract** (`event-envelope.schema.json`):
   - ✅ Validates all required fields present
   - ✅ Validates all field types and formats match schema exactly
   - ✅ Rejects events that do not conform to schema

2. **Time Semantics Contract** (`time-semantics.policy.json`):
   - ✅ Validates RFC3339 UTC format for timestamps
   - ✅ Validates clock skew tolerance (5 seconds future, 30 days past)
   - ✅ Detects late arrival (ingested_at - observed_at > 1 hour)
   - ✅ Sets `ingested_at` to current UTC time (ingest service responsibility)

3. **Failure Semantics Contract** (`failure-semantics.md`):
   - ✅ Rejects invalid events with explicit error codes
   - ✅ Logs all validation operations (success and failure) to `event_validation_log`
   - ✅ Detects duplicates (event_id already exists)
   - ✅ Fail-closed: Missing environment variables cause startup failure

4. **Database Schema Contract** (`schemas/01_raw_events.sql`):
   - ✅ Writes to `machines` table (machine-first modeling)
   - ✅ Writes to `component_instances` table (component instance tracking)
   - ✅ Writes to `raw_events` table (immutable event storage)
   - ✅ Writes to `event_validation_log` table (validation audit trail)
   - ✅ Does NOT write to normalized tables (Phase 4 requirement: raw_events only)

---

## Environment Variables

**Required** (contract compliance: `env.contract.json`):
- `RANSOMEYE_DB_HOST`: PostgreSQL host (default: `localhost`)
- `RANSOMEYE_DB_PORT`: PostgreSQL port (default: `5432`)
- `RANSOMEYE_DB_NAME`: Database name (default: `ransomeye`)
- `RANSOMEYE_DB_USER`: Database user (default: `ransomeye`)
- `RANSOMEYE_DB_PASSWORD`: Database password (**required**, no default)

**Optional**:
- `RANSOMEYE_EVENT_ENVELOPE_SCHEMA_PATH`: Path to `event-envelope.schema.json` (default: `/opt/ransomeye/etc/contracts/event-envelope.schema.json`)

---

## Database Schema Requirements

**Phase 4 requires these tables** (from Phase 2 schema):
- `machines`: Machine registry (machine-first modeling)
- `component_instances`: Component instance registry
- `raw_events`: Immutable event storage
- `event_validation_log`: Validation audit trail

**Phase 4 does NOT require**:
- Normalized tables (process_activity, file_activity, etc.)
- Correlation tables (incidents, evidence, etc.)
- AI metadata tables (feature_vectors, clusters, etc.)

---

## Run Instructions

```bash
# Install dependencies
cd services/ingest
pip install -r requirements.txt

# Set required environment variables
export RANSOMEYE_DB_HOST="localhost"
export RANSOMEYE_DB_PORT="5432"
export RANSOMEYE_DB_NAME="ransomeye"
export RANSOMEYE_DB_USER="ransomeye"
export RANSOMEYE_DB_PASSWORD="your_password"

# Run ingest service
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## API Endpoints

### `POST /events`

**Request**:
- Content-Type: `application/json`
- Body: Event envelope (JSON matching `event-envelope.schema.json`)

**Response** (Success):
- Status Code: `201 Created`
- Body: `{"event_id": "...", "status": "accepted"}`

**Response** (Validation Failure):
- Status Code: `400 Bad Request`
- Body: `{"error_code": "...", "validation_details": {...}}`

**Response** (Duplicate):
- Status Code: `409 Conflict`
- Body: `{"error_code": "DUPLICATE_EVENT_ID"}`

---

## Proof of Phase 4 Correctness

**Phase 4 Objective**: Prove that one valid event can be created, transmitted, validated, and stored.

**This component proves**:
- ✅ **Event validation**: Validates event against frozen contracts from Phase 1
- ✅ **Event storage**: Stores event in database matching frozen schema from Phase 2
- ✅ **Duplicate detection**: Prevents duplicate events (restarting ingest does NOT duplicate data)
- ✅ **Hash integrity**: Verifies hash_sha256 integrity
- ✅ **Minimal implementation**: Only writes to required tables (no normalized tables, no correlation)

**Linux agent proves**:
- ✅ **Event creation**: Constructs canonical event envelope
- ✅ **Event transmission**: Transmits event via HTTP

**Together, they prove**:
- ✅ **One valid event → validated → stored → queryable**: Complete Phase 4 objective

---

## Operational Hardening Guarantees

**Phase 10.1 Requirement**: Core runtime hardening for startup and shutdown.

### Startup Validation

- ✅ **Environment Variable Validation**: All required environment variables validated at Core startup. Missing variables cause immediate exit (non-zero).
- ✅ **Database Connectivity Validation**: DB connection validated at Core startup. Connection failure causes immediate exit.
- ✅ **Schema Presence Validation**: Required database tables validated at Core startup. Missing tables cause immediate exit.
- ✅ **Write Permissions Validation**: Required directories validated for write permissions at Core startup. Permission failures cause immediate exit.

### Fail-Fast Invariants

- ✅ **Missing Environment Variable**: Terminates Core immediately (no recovery, no retry).
- ✅ **Database Connection Failure**: Terminates Core immediately (no recovery, no retry).
- ✅ **Schema Mismatch**: Terminates Core immediately (no recovery, no retry).

### Graceful Shutdown

- ✅ **SIGTERM/SIGINT Handling**: Core stops accepting new work, finishes in-flight DB transactions, closes DB connections cleanly, exits cleanly with log confirmation.
- ✅ **Transaction Cleanup**: All in-flight transactions committed or rolled back on shutdown.
- ✅ **Connection Cleanup**: All database connections closed cleanly on shutdown.

---

## Resource & Disk Safety Guarantees

**Disk Safety**:
- ✅ **Disk Full Detection**: All disk write operations detect disk full conditions (ENOSPC, EDQUOT). Core terminates immediately on detection.
- ✅ **Permission Denied Detection**: All file operations detect permission denied errors (EACCES, EPERM). Core terminates immediately on detection.
- ✅ **Read-Only Filesystem Detection**: All file write operations detect read-only filesystem errors (EROFS). Core terminates immediately on detection.
- ✅ **No Silent Failures**: All disk operations use explicit error detection. No retries, no degradation.

**Log Safety**:
- ✅ **Log Size Limits**: Log messages are limited to 1MB per message to prevent unbounded log growth.
- ✅ **Logging Failure Handling**: If logging fails (disk full, permission denied, memory error), Core terminates immediately (fail-fast).
- ✅ **No Silent Logging Failures**: All logging operations detect and handle failures explicitly.

**File Descriptor & Resource Limits**:
- ✅ **File Descriptor Check**: File descriptor usage checked at startup. Core terminates if >90% of soft limit in use.
- ✅ **File Descriptor Exhaustion Detection**: All file open operations detect file descriptor exhaustion (EMFILE, ENFILE). Core terminates immediately on detection.

**Memory Safety**:
- ✅ **Memory Allocation Failure Detection**: All memory-intensive operations (schema loading, feature extraction, clustering, SHAP) detect MemoryError. Core terminates immediately on detection.
- ✅ **No Swap-Based Survival**: Core does not attempt to continue with swap-based memory. Memory allocation failures cause immediate termination.

**Fail-Fast Semantics**:
- ✅ **No Retries**: All resource failures terminate Core immediately. No retry loops, no best-effort fallbacks.
- ✅ **Explicit Error Messages**: All resource failures log explicit error messages before termination.
- ✅ **Deterministic Behavior**: Core behavior is deterministic under resource failure - immediate termination with explicit error.

---

## Security & Secrets Handling Guarantees

**Secrets Handling**:
- ✅ **Environment Variables Only**: Database password comes from environment variables only. No secrets in code, config files, logs, or exceptions.
- ✅ **Secret Validation**: Database password validated at startup. Missing or weak password terminates Core immediately.
- ✅ **Secret Storage**: Password stored in secure storage (ConfigLoader._secret_values) separate from config dict. Config dict contains "[REDACTED]".
- ✅ **No Secret Logging**: Database password never appears in logs. Config logging uses redacted versions. Password retrieved via config_loader.get_secret() for database connections.

**Log Redaction**:
- ✅ **Automatic Redaction**: All log messages and exceptions automatically sanitized for secrets (passwords, keys, tokens, credentials).
- ✅ **Stack Trace Sanitization**: Exception messages sanitized before logging. Stack traces do not contain secrets.
- ✅ **Secret Pattern Detection**: Logging detects common secret patterns (password, key, token, auth, etc.) and redacts values.
- ✅ **Fail-Fast on Secret Logging**: If a secret is detected in a log attempt, Core terminates immediately (no silent acceptance).
- ✅ **API Response Sanitization**: API error responses never expose full error details (avoid secret leakage in error messages).

**Input Validation**:
- ✅ **Schema Validation**: All incoming event envelopes validated against schema. Malformed JSON terminates Core immediately.
- ✅ **Type Validation**: All database inputs validated for types and bounds. Invalid types terminate Core immediately.
- ✅ **Bounds Checking**: All numeric inputs validated for bounds. Out-of-bounds values terminate Core immediately.

**Fail-Fast Semantics**:
- ✅ **No Retries**: All security failures terminate Core immediately. No retry loops, no best-effort fallbacks.
- ✅ **Explicit Error Messages**: All security failures log explicit error messages (sanitized) before termination.
- ✅ **Deterministic Behavior**: Core behavior is deterministic under security failure - immediate termination with sanitized error.

**END OF README**
