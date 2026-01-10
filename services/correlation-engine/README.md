# RansomEye v1.0 Correlation Engine (Phase 5 - Deterministic)

**AUTHORITATIVE**: Minimal deterministic correlation engine implementing canonical correlation contract for Phase 5 proof-of-concept.

---

## What This Component Does

This component **ONLY** implements the minimal deterministic correlation required for Phase 5 validation:

1. **Consumes Validated Events** (contract compliance: Phase 4 validated events):
   - Reads from `raw_events` table (events with `validation_status = 'VALID'`)
   - Uses only persisted facts (no real-time data, no time-window dependency)
   - Processes events in deterministic order (by `ingested_at ASC`)

2. **Applies Explicit Contradiction Rules** (contract compliance: Phase 5 requirements):
   - **Exactly ONE rule** defined: `apply_linux_agent_rule()`
   - Rule: If `component == 'linux_agent'`, then create exactly one incident with:
     - `stage = 'SUSPICIOUS'` (deterministic constant)
     - `confidence_score = 0.3` (deterministic constant)
   - Rule is purely deterministic (no probabilistic logic, no time windows, no heuristics)

3. **Produces At Most One Incident Per Event** (contract compliance: Phase 5 requirements):
   - One event → ≤ 1 incident (explicit requirement)
   - Deterministic: Rule evaluation is deterministic (boolean logic only)
   - Idempotent: Restarting engine does NOT duplicate incidents (checks `evidence` table)

4. **Stores Incidents in Database** (contract compliance: Phase 2 schema):
   - **incidents**: Create incident record with deterministic properties
   - **incident_stages**: Create initial stage transition (from_stage=NULL, to_stage=SUSPICIOUS)
   - **evidence**: Link triggering event to incident (evidence_type=CORRELATION_PATTERN)
   - All writes are atomic (single transaction)

---

## What Rules Exist

**Exactly ONE rule** (Phase 5 requirement):

### Rule: `apply_linux_agent_rule()`

**Condition** (deterministic):
- `event.component == 'linux_agent'` (exact string match)

**Action** (deterministic):
- If condition is TRUE: Create exactly one incident with:
  - `stage = 'SUSPICIOUS'` (constant)
  - `confidence_score = 0.3` (constant)
- If condition is FALSE: Create zero incidents

**Deterministic Properties**:
- ✅ **No time-window logic**: Rule applies to single event only, no time-based conditions
- ✅ **No probabilistic logic**: Confidence score is constant (0.3), not computed
- ✅ **No heuristics**: Explicit boolean condition (component == 'linux_agent')
- ✅ **No ML/AI**: Pure boolean logic only (no machine learning, no inference)
- ✅ **No enrichment**: Uses only event data from `raw_events` table (no external data)

---

## Why Rules Are Deterministic

**Deterministic Definition**: Given the same input, the rule always produces the same output.

**This rule is deterministic because**:

1. **No Time-Window Dependency**: 
   - Rule does not depend on time windows or temporal relationships
   - Rule applies to single event only (no "wait for more data")
   - No time-based conditions (no "if event occurred within X hours")

2. **No Probabilistic Logic**:
   - Confidence score is constant (0.3), not computed from probabilities
   - No probability distributions, no statistical inference
   - No "confidence tuning" or "adaptive thresholds"

3. **No Heuristics**:
   - Rule uses explicit boolean conditions (component == 'linux_agent')
   - No fuzzy matching, no pattern matching, no heuristics
   - No "best guess" or "most likely" logic

4. **No ML/AI**:
   - Pure boolean logic only (if-then-else)
   - No machine learning models, no neural networks, no LLM
   - No training data, no model inference

5. **Deterministic Execution**:
   - Rule evaluation is deterministic (same input → same output)
   - No random numbers, no probabilistic sampling
   - No non-deterministic operations (no async, no threads, no race conditions)

**Proof of Determinism**:
- Given event with `component = 'linux_agent'`: Always creates incident with `stage='SUSPICIOUS'`, `confidence_score=0.3`
- Given event with `component != 'linux_agent'`: Always creates zero incidents
- Same input always produces same output (deterministic)

---

## What This Engine Does NOT Do

**Phase 5 Requirements - Forbidden Behaviors**:

- ❌ **NO AI/ML/LLM**: Does not use machine learning, neural networks, or large language models
- ❌ **NO time-window dependency**: Does not wait for time windows or temporal relationships
- ❌ **NO probabilistic logic**: Does not use probabilities, statistics, or probability distributions
- ❌ **NO heuristics**: Does not use heuristics, pattern matching, or fuzzy logic
- ❌ **NO enrichment**: Does not enrich events with external data or context
- ❌ **NO retries**: Does not retry failed operations
- ❌ **NO background threads**: Does not use background threads or async processing
- ❌ **NO async**: Does not use async/await (synchronous code only)

**General Forbidden Behaviors**:

- ❌ **NO time-window logic**: Does not use time windows (no "events within X hours")
- ❌ **NO waiting for more data**: Does not wait for additional events before creating incidents
- ❌ **NO confidence tuning**: Does not adjust confidence scores dynamically
- ❌ **NO pattern matching**: Does not match patterns or sequences
- ❌ **NO correlation with other events**: Does not correlate events with other events (single event only)
- ❌ **NO incident merging**: Does not merge incidents or link related incidents
- ❌ **NO state management**: Does not maintain state between runs (uses only persisted facts)

---

## Why Time is NOT Required for Correctness

**Time-Independent Determinism**:

1. **No Time-Window Logic**:
   - Rule does not depend on time windows (no "events within X hours")
   - Rule applies to single event only (no temporal relationships)
   - No time-based conditions (no "if event occurred at Y time")

2. **Deterministic Execution Order**:
   - Events are processed in deterministic order (by `ingested_at ASC`)
   - Order is deterministic (same events in same order → same results)
   - No time-based scheduling or timing dependencies

3. **Idempotency Without Time**:
   - Idempotency is achieved through database checks (not time-based)
   - Check if event already processed (in `evidence` table)
   - Restarting engine does NOT duplicate incidents (time-independent)

4. **Persisted Facts Only**:
   - Engine uses only persisted facts from database (not real-time data)
   - No time-dependent state (no "last seen" timestamps for correlation)
   - Facts are immutable (time of event is a fact, not a dependency)

**Proof of Time-Independence**:
- Rule evaluation depends only on event data (component, machine_id, etc.)
- Rule does not depend on current time, time windows, or temporal relationships
- Same events processed at different times produce same results (deterministic)
- Engine can be restarted at any time without affecting correctness (idempotent)

---

## How This Proves Phase 5 Correctness

### Validation Criteria (PASS / FAIL)

**PASS if**:
1. ✅ **One event → ≤ 1 incident**: Rule produces at most one incident per event
2. ✅ **Restarting engine does NOT duplicate incidents**: Idempotency check prevents duplicates
3. ✅ **No time-window logic exists**: Rule does not use time windows or temporal relationships
4. ✅ **No ML/AI imports exist**: No machine learning or AI libraries imported
5. ✅ **No retries or background jobs exist**: No retry logic or background processing

**FAIL if**:
1. ❌ **Engine waits for more data**: Engine should process events immediately (no waiting)
2. ❌ **Engine uses time windows**: Engine should not use time-based conditions
3. ❌ **Engine attempts "confidence tuning"**: Confidence score must be constant (0.3)
4. ❌ **Engine uses probabilistic logic**: Rule must be deterministic (no probabilities)
5. ❌ **Engine uses ML/AI**: Rule must use pure boolean logic only

### Contract Compliance

1. **Event Envelope Contract** (`event-envelope.schema.json`):
   - ✅ Reads events from `raw_events` table (validated events from Phase 4)
   - ✅ Uses event fields (component, machine_id, event_id, etc.)

2. **Database Schema Contract** (`schemas/04_correlation.sql`):
   - ✅ Writes to `incidents` table (immutable primary key, deterministic properties)
   - ✅ Writes to `incident_stages` table (auditable stage transitions)
   - ✅ Writes to `evidence` table (event-to-incident linkage)
   - ✅ All writes are atomic (single transaction)

3. **Failure Semantics Contract** (`failure-semantics.md`):
   - ✅ No retries (fails immediately on error)
   - ✅ Fail-closed (missing environment variables cause startup failure)

4. **Environment Variable Contract** (`env.contract.json`):
   - ✅ Reads database connection parameters from environment variables
   - ✅ No path computation (all configuration from environment)

---

## Environment Variables

**Required** (contract compliance: `env.contract.json`):
- `RANSOMEYE_DB_HOST`: PostgreSQL host (default: `localhost`)
- `RANSOMEYE_DB_PORT`: PostgreSQL port (default: `5432`)
- `RANSOMEYE_DB_NAME`: Database name (default: `ransomeye`)
- `RANSOMEYE_DB_USER`: Database user (default: `ransomeye`)
- `RANSOMEYE_DB_PASSWORD`: Database password (**required**, no default, fail-closed)

---

## Database Schema Requirements

**Phase 5 requires these tables** (from Phase 2 schema):
- `raw_events`: Source of validated events (from Phase 4)
- `incidents`: Incident registry (machine-first modeling)
- `incident_stages`: Incident stage transitions (auditable)
- `evidence`: Event-to-incident linkage (many-to-many)

**Phase 5 does NOT require**:
- Normalized tables (used only if required by rules, not used in Phase 5)
- AI metadata tables (no ML/AI in Phase 5)
- Time-window tables (no time-window logic in Phase 5)

---

## Run Instructions

```bash
# Install dependencies
cd services/correlation-engine
pip install -r requirements.txt

# Set required environment variables
export RANSOMEYE_DB_HOST="localhost"
export RANSOMEYE_DB_PORT="5432"
export RANSOMEYE_DB_NAME="ransomeye"
export RANSOMEYE_DB_USER="ransomeye"
export RANSOMEYE_DB_PASSWORD="your_password"

# Run correlation engine
python3 app/main.py
```

---

## Proof of Phase 5 Correctness

**Phase 5 Objective**: Prove that deterministic correlation engine can consume validated events, apply explicit rules, and produce incidents deterministically.

**This component proves**:
- ✅ **Deterministic rule evaluation**: Rule is purely deterministic (no time windows, no probabilities, no heuristics)
- ✅ **At most one incident per event**: Rule produces ≤ 1 incident per event (explicit requirement)
- ✅ **Idempotent operation**: Restarting engine does NOT duplicate incidents (idempotency check)
- ✅ **Time-independent correctness**: Time is NOT required for correctness (no time-window logic)
- ✅ **Atomic writes**: All database writes are atomic (single transaction)
- ✅ **Contract compliance**: Aligns with frozen contracts from Phases 1-4

**Phase 4 (Ingest Service) provides**:
- ✅ **Validated events**: Events in `raw_events` table with `validation_status = 'VALID'`

**Together, they prove**:
- ✅ **Validated events → deterministic correlation → incidents**: Complete Phase 5 objective

---

## Operational Hardening Guarantees

**Phase 10.1 Requirement**: Core runtime hardening for startup and shutdown.

### Startup Validation

- ✅ **Environment Variable Validation**: All required environment variables validated at Core startup. Missing variables cause immediate exit (non-zero).
- ✅ **Database Connectivity Validation**: DB connection validated at Core startup. Connection failure causes immediate exit.
- ✅ **Schema Presence Validation**: Required database tables validated at Core startup. Missing tables cause immediate exit.

### Fail-Fast Invariants

- ✅ **Missing Environment Variable**: Terminates Core immediately (no recovery, no retry).
- ✅ **Database Connection Failure**: Terminates Core immediately (no recovery, no retry).
- ✅ **Schema Mismatch**: Terminates Core immediately (no recovery, no retry).
- ✅ **Duplicate Incident Creation Attempt**: Terminates Core immediately when attempting to create duplicate incident for same event_id (no recovery, no retry).

### Graceful Shutdown

- ✅ **SIGTERM/SIGINT Handling**: Core stops accepting new work, finishes in-flight DB transactions, closes DB connections cleanly, exits cleanly with log confirmation.
- ✅ **Transaction Cleanup**: All in-flight transactions committed or rolled back on shutdown.
- ✅ **Connection Cleanup**: All database connections closed cleanly on shutdown.

---

## Resource & Disk Safety Guarantees

**Disk Safety**:
- ✅ **No Disk Writes**: Correlation Engine does not write to disk. All data persisted via database only.
- ✅ **Database Disk Failures**: Database write failures (including disk full) detected and handled by database safety utilities. Core terminates immediately on database disk failures.

**Log Safety**:
- ✅ **Log Size Limits**: Log messages are limited to 1MB per message to prevent unbounded log growth.
- ✅ **Logging Failure Handling**: If logging fails (disk full, permission denied, memory error), Core terminates immediately (fail-fast).
- ✅ **No Silent Logging Failures**: All logging operations detect and handle failures explicitly.

**File Descriptor & Resource Limits**:
- ✅ **File Descriptor Check**: File descriptor usage checked at startup. Core terminates if >90% of soft limit in use.
- ✅ **File Descriptor Exhaustion Detection**: Database connection operations detect file descriptor exhaustion. Core terminates immediately on detection.

**Memory Safety**:
- ✅ **Memory Allocation Failure Detection**: Event processing operations detect MemoryError. Core terminates immediately on detection.
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
- ✅ **No Secret Logging**: Database password never appears in logs. Config logging uses redacted versions.

**Log Redaction**:
- ✅ **Automatic Redaction**: All log messages and exceptions automatically sanitized for secrets.
- ✅ **Stack Trace Sanitization**: Exception messages sanitized before logging.
- ✅ **Secret Pattern Detection**: Logging detects common secret patterns and redacts values.

**Fail-Fast Semantics**:
- ✅ **No Retries**: All security failures terminate Core immediately.
- ✅ **Explicit Error Messages**: All security failures log explicit error messages (sanitized) before termination.
- ✅ **Deterministic Behavior**: Core behavior is deterministic under security failure - immediate termination with sanitized error.

**END OF README**
