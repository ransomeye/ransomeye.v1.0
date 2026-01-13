# Validation Step 6 — Ingest Pipeline & Event Integrity (End-to-End Entry Point)

**Component Identity:**
- **Name:** Ingest Pipeline (HTTP entry → validation → persistence)
- **Primary Paths:**
  - `/home/ransomeye/rebuild/services/ingest/app/main.py` - Main ingest service
  - `/home/ransomeye/rebuild/services/ingest/app/main_hardened.py` - Hardened variant
- **Entry Point:** HTTP POST `POST /events` - `services/ingest/app/main.py:504` - `@app.post("/events")`
- **Database Write:** Ingest service writes to `raw_events`, `machines`, `component_instances`, `event_validation_log`

**Spec Reference:**
- Event Envelope Contract (`contracts/event-envelope.schema.json`)
- Time Semantics Policy (`contracts/time-semantics.policy.json`)
- Phase 4 — Minimal Data Plane (Ingest Service)

---

## 1. COMPONENT IDENTITY & BOUNDARY

### Evidence

**How Events Enter:**
- ✅ HTTP POST endpoint: `services/ingest/app/main.py:504` - `@app.post("/events")`
- ✅ Protocol: HTTP/1.1 (FastAPI/uvicorn)
- ✅ Content-Type: JSON (implicit, FastAPI parses JSON)
- ✅ Endpoint path: `/events`
- ✅ FastAPI application: `services/ingest/app/main.py:280` - `app = FastAPI(...)`

**Authentication / Trust Assumptions:**
- ❌ **CRITICAL:** No authentication found:
  - `services/ingest/app/main.py:504-698` - `ingest_event()` does NOT verify authentication
  - No authentication middleware found
  - No API key verification found
  - No signature verification found (from previous validation)
- ⚠️ **ISSUE:** Ingest accepts events from any source (no authentication)

**Whether Ingest is the Only Write Path for Events:**
- ✅ **VERIFIED (in production code):** Ingest is the only write path:
  - `services/linux-agent/src/main.rs:293-332` - Agents use HTTP POST to ingest service
  - `dpi/probe/main.py` - DPI probe is stubbed, would use HTTP POST if implemented
  - No database connection code found in agents/DPI
- ⚠️ **ISSUE:** Test harness can write directly: `validation/harness/track_1_determinism.py:652-688` - Direct INSERT into `raw_events`
- ⚠️ **ISSUE:** Documentation says agents can write directly: `schemas/DATA_PLANE_HARDENING.md:29-31` - But code shows HTTP POST

**Any Component Bypasses Ingest to Write Events:**
- ✅ **PROVEN IMPOSSIBLE (in production code):** No component bypasses ingest:
  - Agents use HTTP POST (do not bypass)
  - DPI would use HTTP POST (does not bypass)
  - ⚠️ **ISSUE:** Test harness bypasses ingest (test code only)

**Multiple Ingestion Paths Exist:**
- ✅ **VERIFIED:** Only one ingestion path exists (HTTP POST to `/events`)
- ✅ No message bus found
- ✅ No direct database writes from agents/DPI (in production code)

**Ingest Mutates Events Beyond Normalization:**
- ⚠️ **ISSUE:** Ingest mutates `ingested_at`:
  - `services/ingest/app/main.py:587-589` - Updates `ingested_at` to current UTC time
  - `services/ingest/README.md:28-30` - "Updates ingested_at (contract compliance: time-semantics.md)"
  - ⚠️ **ISSUE:** Event envelope is mutated during processing (ingested_at is updated)
  - ✅ No other mutations found (no normalization, no field dropping)

### Verdict: **PARTIAL**

**Justification:**
- Ingest is clearly identified as the single HTTP entry point
- **CRITICAL:** No authentication (accepts events from any source)
- **ISSUE:** Ingest mutates `ingested_at` during processing (but this is documented)
- **ISSUE:** Test harness can bypass ingest (test code only)
- Production agents use HTTP POST (do not bypass ingest)

---

## 2. EVENT ENVELOPE VALIDATION (CRITICAL)

### Evidence

**Enforcement of `event-envelope.schema.json`:**
- ✅ Schema is loaded: `services/ingest/app/main.py:226-237` - Loads schema from file
- ✅ Schema validation occurs: `services/ingest/app/main.py:316-328` - `validate_schema()` uses `jsonschema.validate()`
- ✅ Schema validation is strict: `services/ingest/app/main.py:319` - Uses `jsonschema.validate()` which raises `ValidationError` on failure
- ✅ Schema validation order: `services/ingest/app/main.py:526` - Schema validation occurs FIRST (before hash, timestamps, duplicate)

**Required Fields (No Optional Tolerance):**
- ✅ Required fields enforced: `contracts/event-envelope.schema.json:7-18` - `required` array lists all required fields
- ✅ Missing fields rejected: `services/ingest/app/main.py:526-557` - Returns HTTP 400 BAD REQUEST on schema violation
- ✅ Schema validation logs failure: `services/ingest/app/main.py:532-543` - Logs to `event_validation_log`

**Type Correctness:**
- ✅ Type validation enforced: `contracts/event-envelope.schema.json:20-114` - Type definitions for all fields
- ✅ Type mismatches rejected: `services/ingest/app/main.py:321-328` - `jsonschema.ValidationError` raised on type mismatch
- ✅ Type validation logs failure: `services/ingest/app/main.py:532-543` - Logs to `event_validation_log`

**Enum Correctness (`component`):**
- ✅ Enum validation enforced: `contracts/event-envelope.schema.json:31-34` - `component` field is enum: `["linux_agent", "windows_agent", "dpi", "core"]`
- ✅ Invalid enum values rejected: `services/ingest/app/main.py:319` - `jsonschema.validate()` rejects invalid enum values
- ✅ Enum validation logs failure: `services/ingest/app/main.py:532-543` - Logs to `event_validation_log`

**What Happens on Missing Field:**
- ✅ Missing field causes rejection: `services/ingest/app/main.py:526-557` - Returns HTTP 400 BAD REQUEST
- ✅ Missing field is logged: `services/ingest/app/main.py:532-543` - Logs to `event_validation_log` with error details
- ✅ Missing field does NOT cause silent acceptance: Schema validation rejects before processing

**What Happens on Extra/Unknown Field:**
- ✅ Unknown fields forbidden: `contracts/event-envelope.schema.json:19` - `additionalProperties: false`
- ✅ Unknown fields rejected: `services/ingest/app/main.py:319` - `jsonschema.validate()` rejects unknown fields
- ✅ Unknown fields cause schema violation: `services/ingest/app/main.py:322-326` - Returns "SCHEMA_VIOLATION" error

**What Happens on Type Mismatch:**
- ✅ Type mismatch causes rejection: `services/ingest/app/main.py:526-557` - Returns HTTP 400 BAD REQUEST
- ✅ Type mismatch is logged: `services/ingest/app/main.py:532-543` - Logs to `event_validation_log` with error details
- ✅ Type mismatch does NOT cause silent acceptance: Schema validation rejects before processing

**Best-Effort Parsing:**
- ✅ Schema validation is strict: `services/ingest/app/main.py:316-328` - Raises `ValidationError` on failure
- ✅ No best-effort parsing: `services/ingest/app/main.py:554-557` - Rejects invalid messages
- ✅ All validation failures cause rejection: `services/ingest/app/main.py:526-622` - Multiple validation checks

**Silent Field Dropping:**
- ✅ No field dropping: Schema validation rejects messages with missing/extra fields
- ✅ All required fields must be present: `contracts/event-envelope.schema.json:7-18` - Required fields enforced

**Acceptance of Partially Valid Envelopes:**
- ✅ Partially valid envelopes rejected: `services/ingest/app/main.py:526-557` - Schema validation rejects partial messages
- ✅ All required fields must be valid: Schema validation checks all fields

### Verdict: **PASS**

**Justification:**
- Strict schema validation is present and enforced
- Missing required fields, type mismatches, and unknown fields are all rejected
- No best-effort parsing or silent field dropping found
- Schema validation occurs before any processing

---

## 3. TIME SEMANTICS ENFORCEMENT

### Evidence

**Enforcement of `observed_at`:**
- ✅ `observed_at` is required: `contracts/event-envelope.schema.json:41-44` - Required field, RFC3339 format
- ✅ `observed_at` is validated: `services/ingest/app/main.py:330-374` - `validate_timestamps()` parses and validates `observed_at`
- ✅ `observed_at` format validated: `services/ingest/app/main.py:336` - Uses `parser.isoparse()` to parse RFC3339
- ✅ `observed_at` timezone normalized: `services/ingest/app/main.py:339-342` - Normalizes to UTC

**Enforcement of `ingested_at`:**
- ✅ `ingested_at` is required: `contracts/event-envelope.schema.json:46-49` - Required field, RFC3339 format
- ⚠️ **ISSUE:** `ingested_at` is mutated: `services/ingest/app/main.py:587-589` - Updates `ingested_at` to current UTC time
- ✅ `ingested_at` is validated: `services/ingest/app/main.py:330-374` - `validate_timestamps()` validates `ingested_at` AFTER mutation
- ✅ `ingested_at` format validated: `services/ingest/app/main.py:337` - Uses `parser.isoparse()` to parse RFC3339
- ✅ `ingested_at` timezone normalized: `services/ingest/app/main.py:344-347` - Normalizes to UTC

**Clock Skew Tolerance:**
- ✅ Clock skew tolerance enforced: `services/ingest/app/main.py:350-356` - Rejects if `ingested_at - observed_at < -5` seconds (future beyond tolerance)
- ✅ Clock skew tolerance matches policy: `contracts/time-semantics.policy.json:53-56` - `max_future_seconds: 5`
- ✅ Clock skew violation rejected: `services/ingest/app/main.py:350-356` - Returns HTTP 400 BAD REQUEST

**Out-of-Order Arrival Handling:**
- ⚠️ **ISSUE:** Out-of-order arrival is NOT explicitly handled in timestamp validation:
  - `services/ingest/app/main.py:330-374` - `validate_timestamps()` does NOT check for out-of-order arrival
  - `contracts/time-semantics.policy.json:179-186` - Policy says out-of-order should be "ACCEPT_WITH_WARNING"
  - ⚠️ **ISSUE:** Out-of-order events are accepted (no explicit rejection, but no explicit handling)

**Late Arrival Handling:**
- ✅ Late arrival detected: `services/ingest/app/main.py:366` - `late_arrival = time_diff > 3600` (1 hour)
- ✅ Late arrival threshold matches policy: `contracts/time-semantics.policy.json:69-72` - `threshold_hours: 1`
- ✅ Late arrival is marked: `services/ingest/app/main.py:366-367` - Sets `late_arrival` flag and `arrival_latency_seconds`
- ✅ Late arrival is stored: `services/ingest/app/main.py:469` - `late_arrival` and `arrival_latency_seconds` stored in `raw_events`
- ✅ Late arrival is accepted: `services/ingest/app/main.py:366` - Late arrival does NOT cause rejection (only marking)

**Exact Rejection vs Acceptance Rules:**
- ✅ Future beyond tolerance rejected: `services/ingest/app/main.py:350-356` - `ingested_at - observed_at < -5` seconds → REJECT
- ✅ Too old rejected: `services/ingest/app/main.py:358-364` - `ingested_at - observed_at > 30 days` → REJECT
- ✅ Late arrival accepted: `services/ingest/app/main.py:366` - `ingested_at - observed_at > 1 hour` → ACCEPT (with marking)
- ✅ Clock skew within tolerance accepted: `services/ingest/app/main.py:350` - `ingested_at - observed_at >= -5` seconds → ACCEPT

**Whether Time Violations Are Logged and Rejected:**
- ✅ Time violations are logged: `services/ingest/app/main.py:592-622` - Logs to `event_validation_log` on timestamp validation failure
- ✅ Time violations are rejected: `services/ingest/app/main.py:619-622` - Returns HTTP 400 BAD REQUEST on timestamp validation failure

**Ingest Accepts Events with Invalid Timestamps:**
- ✅ Invalid timestamps rejected: `services/ingest/app/main.py:591-622` - Returns HTTP 400 BAD REQUEST on timestamp validation failure
- ✅ Invalid timestamps logged: `services/ingest/app/main.py:592-622` - Logs to `event_validation_log`

**Ingest Rewrites Timestamps Silently:**
- ⚠️ **ISSUE:** Ingest rewrites `ingested_at`:
  - `services/ingest/app/main.py:587-589` - Updates `ingested_at` to current UTC time
  - `services/ingest/README.md:28-30` - "Updates ingested_at (contract compliance: time-semantics.md)"
  - ⚠️ **ISSUE:** `ingested_at` is rewritten (but this is documented and expected behavior)

**Late Events Are Accepted Without Explicit Marking:**
- ✅ Late events are explicitly marked: `services/ingest/app/main.py:366-367` - Sets `late_arrival` flag and `arrival_latency_seconds`
- ✅ Late events are stored with marking: `services/ingest/app/main.py:469` - `late_arrival` and `arrival_latency_seconds` stored in `raw_events`

### Verdict: **PARTIAL**

**Justification:**
- Time semantics are enforced (clock skew, age limits, late arrival detection)
- Time violations are logged and rejected
- **ISSUE:** `ingested_at` is rewritten during processing (but this is documented)
- **ISSUE:** Out-of-order arrival is not explicitly handled (but events are accepted)

---

## 4. INTEGRITY & ORDERING GUARANTEES

### Evidence

**`hash_sha256` Verification:**
- ✅ Hash verification occurs: `services/ingest/app/main.py:376-384` - `validate_hash_integrity()` verifies hash
- ✅ Hash computation: `services/ingest/app/main.py:304-314` - `compute_hash()` computes SHA256 hash (excludes hash_sha256 field)
- ✅ Hash mismatch causes rejection: `services/ingest/app/main.py:559-585` - Returns HTTP 400 BAD REQUEST on hash mismatch
- ✅ Hash mismatch is logged: `services/ingest/app/main.py:561-580` - Logs to `event_validation_log`

**`prev_hash_sha256` Chain Enforcement:**
- ✅ Hash chain verification occurs: `services/ingest/app/main.py:418-423` - `verify_hash_chain_continuity()` verifies chain
- ✅ Hash chain verification in storage: `services/ingest/app/main.py:419-423` - Verifies hash chain during `store_event()`
- ✅ Hash chain violation causes rejection: `services/ingest/app/main.py:420-423` - Raises `ValueError` on hash chain violation
- ✅ Hash chain violation is logged: `services/ingest/app/main.py:422` - Logs error, then raises exception
- ✅ Hash chain violation returns HTTP 400: `services/ingest/app/main.py:652-671` - Returns HTTP 400 BAD REQUEST on integrity violation

**`sequence` Monotonicity per `component_instance_id`:**
- ✅ Sequence monotonicity verification occurs: `services/ingest/app/main.py:425-431` - `verify_sequence_monotonicity()` verifies monotonicity
- ✅ Sequence monotonicity verification in storage: `services/ingest/app/main.py:426-431` - Verifies sequence monotonicity during `store_event()`
- ✅ Sequence monotonicity violation causes rejection: `services/ingest/app/main.py:427-431` - Raises `ValueError` on sequence violation
- ✅ Sequence monotonicity violation is logged: `services/ingest/app/main.py:429-430` - Logs error, then raises exception
- ✅ Sequence monotonicity violation returns HTTP 400: `services/ingest/app/main.py:652-671` - Returns HTTP 400 BAD REQUEST on integrity violation

**What Happens on Hash Mismatch:**
- ✅ Hash mismatch causes rejection: `services/ingest/app/main.py:559-585` - Returns HTTP 400 BAD REQUEST
- ✅ Hash mismatch is logged: `services/ingest/app/main.py:561-580` - Logs to `event_validation_log`
- ✅ Hash mismatch does NOT cause silent acceptance: Event is rejected before storage

**What Happens on Broken Hash Chain:**
- ✅ Broken hash chain causes rejection: `services/ingest/app/main.py:420-423` - Raises `ValueError` on hash chain violation
- ✅ Broken hash chain is logged: `services/ingest/app/main.py:422` - Logs error
- ✅ Broken hash chain returns HTTP 400: `services/ingest/app/main.py:652-671` - Returns HTTP 400 BAD REQUEST
- ✅ Broken hash chain does NOT cause silent acceptance: Event is rejected before storage

**What Happens on Sequence Gap or Rollback:**
- ✅ Sequence gap causes rejection: `services/ingest/app/main.py:427-431` - Raises `ValueError` on sequence violation
- ✅ Sequence gap is logged: `services/ingest/app/main.py:429-430` - Logs error
- ✅ Sequence gap returns HTTP 400: `services/ingest/app/main.py:652-671` - Returns HTTP 400 BAD REQUEST
- ⚠️ **ISSUE:** Large gaps (>1000) are rejected, but small gaps are not explicitly handled:
  - `common/integrity/verification.py:116-118` - Large gaps (>1000) are rejected
  - ⚠️ **ISSUE:** Small gaps (1-1000) are accepted (no explicit rejection)

**Hash Mismatch Logged but Event Accepted:**
- ✅ Hash mismatch causes rejection: `services/ingest/app/main.py:559-585` - Returns HTTP 400 BAD REQUEST
- ✅ Hash mismatch does NOT cause silent acceptance: Event is rejected before storage

**Sequence Gaps Tolerated Silently:**
- ⚠️ **PARTIAL:** Small sequence gaps are tolerated:
  - `common/integrity/verification.py:102-114` - Sequence must be > max_sequence (monotonically increasing)
  - `common/integrity/verification.py:116-118` - Large gaps (>1000) are rejected
  - ⚠️ **ISSUE:** Small gaps (1-1000) are accepted (no explicit rejection, but sequence must be > max_sequence)

**Integrity Failures Downgraded to Warnings:**
- ✅ Integrity failures cause rejection: `services/ingest/app/main.py:420-423,427-431` - Raises `ValueError` on integrity violation
- ✅ Integrity failures return HTTP 400: `services/ingest/app/main.py:652-671` - Returns HTTP 400 BAD REQUEST
- ✅ Integrity failures do NOT cause silent acceptance: Event is rejected before storage

### Verdict: **PARTIAL**

**Justification:**
- Hash verification, hash chain enforcement, and sequence monotonicity are present
- Integrity violations cause rejection (not silent acceptance)
- **ISSUE:** Small sequence gaps (1-1000) are accepted (no explicit rejection, but sequence must be > max_sequence)
- **ISSUE:** Large gaps (>1000) are rejected, but small gaps are tolerated

---

## 5. DE-DUPLICATION & REPLAY PROTECTION

### Evidence

**Duplicate Detection Keys:**
- ✅ Duplicate detection by `event_id`: `services/ingest/app/main.py:386-390` - `check_duplicate()` checks `event_id`
- ✅ `event_id` is UUID: `contracts/event-envelope.schema.json:21-24` - UUID v4 format
- ✅ `event_id` is PRIMARY KEY: `schemas/01_raw_events.sql:26` - `event_id UUID NOT NULL PRIMARY KEY`
- ⚠️ **ISSUE:** Only `event_id` is used for duplicate detection (no sequence/hash-based duplicate detection)

**Replay Handling:**
- ✅ Duplicate `event_id` causes rejection: `services/ingest/app/main.py:632-647` - Returns HTTP 409 CONFLICT on duplicate
- ✅ Duplicate `event_id` is logged: `services/ingest/app/main.py:633-641` - Logs to `event_validation_log`
- ⚠️ **ISSUE:** Replay with same `event_id` is detected, but replay with different `event_id` is not detected

**Idempotency Guarantees on Restart:**
- ✅ Idempotency verification occurs: `services/ingest/app/main.py:433-437` - `verify_idempotency()` checks for duplicate `event_id`
- ✅ Idempotency verification in storage: `services/ingest/app/main.py:434-437` - Verifies idempotency during `store_event()`
- ✅ Idempotency violation causes rejection: `services/ingest/app/main.py:435-437` - Raises `ValueError` on idempotency violation
- ✅ Idempotency violation is logged: `services/ingest/app/main.py:436` - Logs warning, then raises exception
- ✅ Idempotency violation returns HTTP 400: `services/ingest/app/main.py:652-671` - Returns HTTP 400 BAD REQUEST on integrity violation

**Duplicate Events Create Multiple DB Rows:**
- ✅ Duplicate events rejected: `services/ingest/app/main.py:632-647` - Returns HTTP 409 CONFLICT on duplicate `event_id`
- ✅ Database PRIMARY KEY constraint: `schemas/01_raw_events.sql:26` - `event_id UUID NOT NULL PRIMARY KEY` prevents duplicates at database level
- ✅ Duplicate events do NOT create multiple rows: Duplicate detection + PRIMARY KEY constraint prevent multiple rows

**Restarting Ingest Causes Re-Insertion:**
- ✅ Idempotency verification prevents re-insertion: `services/ingest/app/main.py:433-437` - `verify_idempotency()` checks for duplicate `event_id`
- ✅ Database PRIMARY KEY constraint prevents re-insertion: `schemas/01_raw_events.sql:26` - PRIMARY KEY constraint prevents duplicate `event_id`
- ✅ Restarting ingest does NOT cause re-insertion: Duplicate detection + PRIMARY KEY constraint prevent re-insertion

**Replay Cannot Be Detected Deterministically:**
- ⚠️ **PARTIAL:** Replay with same `event_id` is detected:
  - `services/ingest/app/main.py:632-647` - Duplicate `event_id` is detected and rejected
  - ✅ **VERIFIED:** Replay with same `event_id` CAN be detected deterministically
- ⚠️ **ISSUE:** Replay with different `event_id` is NOT detected:
  - If attacker generates unique `event_id` for each replay, replay cannot be detected
  - ⚠️ **VERIFIED:** Replay with different `event_id` CANNOT be detected deterministically

### Verdict: **PARTIAL**

**Justification:**
- Duplicate detection by `event_id` is present and enforced
- Idempotency guarantees on restart are present
- **ISSUE:** Only `event_id` is used for duplicate detection (no sequence/hash-based duplicate detection)
- **ISSUE:** Replay with different `event_id` cannot be detected deterministically

---

## 6. PERSISTENCE BEHAVIOR (ATOMICITY)

### Evidence

**Transaction Boundaries:**
- ✅ Transactions are used: `services/ingest/app/main.py:489-502` - Uses `execute_write_operation()` with explicit transactions
- ✅ Explicit transaction begin: `common/db/safety.py:301` - `begin_transaction()` called
- ✅ Explicit transaction commit: `common/db/safety.py:308` - `commit_transaction()` called
- ✅ Explicit transaction rollback: `common/db/safety.py:316` - `rollback_transaction()` called on failure

**All-or-Nothing Writes:**
- ✅ Atomic transactions: `common/db/safety.py:280-318` - `execute_write_operation()` uses transactions
- ✅ Rollback on failure: `common/db/safety.py:316` - `rollback_transaction()` called on exception
- ✅ No partial writes: Transactions ensure atomicity

**Tables Touched per Accepted Event:**
- ✅ Tables written per event: `services/ingest/app/main.py:439-483` - Writes to:
  - `machines` (UPSERT)
  - `component_instances` (UPSERT)
  - `raw_events` (INSERT)
  - `event_validation_log` (INSERT)
- ✅ All writes in single transaction: `services/ingest/app/main.py:489-502` - All writes in `store_event()` are in single transaction

**What Happens if Any Write Fails:**
- ✅ Write failure causes rollback: `common/db/safety.py:316` - `rollback_transaction()` called on exception
- ✅ Write failure causes HTTP 500: `services/ingest/app/main.py:681-695` - Returns HTTP 500 INTERNAL ERROR on exception
- ✅ Write failure is logged: `services/ingest/app/main.py:501` - `logger.db_error()` on exception
- ✅ Write failure does NOT cause silent acceptance: Event is rejected, transaction is rolled back

**Partial Writes Possible:**
- ✅ No partial writes: Transactions ensure atomicity
- ✅ Rollback on failure: `common/db/safety.py:316` - `rollback_transaction()` called on exception

**Event Accepted but Not Fully Persisted:**
- ✅ Event acceptance requires full persistence: `services/ingest/app/main.py:651` - `store_event()` must succeed for event to be accepted
- ✅ Event acceptance returns HTTP 201: `services/ingest/app/main.py:675-678` - Returns HTTP 201 CREATED only after successful storage
- ✅ Event acceptance does NOT occur without full persistence: Transaction ensures all-or-nothing

**Side-Tables Written Before Validation Completes:**
- ✅ Validation occurs before storage: `services/ingest/app/main.py:526-648` - Schema, hash, timestamp, duplicate validation occurs BEFORE `store_event()`
- ✅ Side-tables written in transaction: `services/ingest/app/main.py:439-483` - All tables written in single transaction
- ✅ Side-tables written after validation: `services/ingest/app/main.py:651` - `store_event()` is called only after all validation passes

### Verdict: **PASS**

**Justification:**
- Transaction boundaries are explicit and proper
- All-or-nothing writes are enforced (transactions ensure atomicity)
- Tables touched per event are documented and all writes are in single transaction
- Write failures cause rollback and rejection (no partial writes)

---

## 7. FAILURE SEMANTICS (FAIL-CLOSED)

### Evidence

**Behavior on DB Unavailable:**
- ✅ DB unavailability causes error: `services/ingest/app/main.py:198-209` - `get_db_connection()` raises `RuntimeError` on failure
- ✅ Error causes HTTP 500: `services/ingest/app/main.py:681-695` - Returns HTTP 500 INTERNAL ERROR on exception
- ✅ Error is logged: `services/ingest/app/main.py:690` - Logs error
- ✅ No retries: `services/ingest/README.md:40` - "NO retry logic: Does not retry failed database operations"

**Behavior on Schema Mismatch:**
- ✅ Schema mismatch causes termination: `core/runtime.py:331-363` - `_invariant_check_schema_mismatch()` calls `exit_fatal()` on schema mismatch
- ✅ Schema mismatch prevents startup: `core/runtime.py:199-202` - Missing required tables cause `exit_startup_error()`
- ⚠️ **ISSUE:** Schema mismatch at runtime (during event processing) causes HTTP 500, not termination:
  - `services/ingest/app/main.py:681-695` - Returns HTTP 500 INTERNAL ERROR on exception
  - ⚠️ **ISSUE:** Ingest continues accepting events after schema mismatch (returns HTTP 500 but service continues)

**Behavior on Integrity Violation:**
- ✅ Integrity violation causes rejection: `services/ingest/app/main.py:420-423,427-431` - Raises `ValueError` on integrity violation
- ✅ Integrity violation returns HTTP 400: `services/ingest/app/main.py:652-671` - Returns HTTP 400 BAD REQUEST
- ✅ Integrity violation is logged: `services/ingest/app/main.py:422,429-430` - Logs error
- ✅ Integrity violation does NOT cause silent acceptance: Event is rejected

**Behavior on Internal Exception:**
- ✅ Internal exception causes HTTP 500: `services/ingest/app/main.py:681-695` - Returns HTTP 500 INTERNAL ERROR on exception
- ✅ Internal exception is logged: `services/ingest/app/main.py:690` - Logs error
- ✅ Internal exception causes rollback: `services/ingest/app/main.py:682-683` - Rolls back transaction on exception
- ✅ Internal exception does NOT cause silent acceptance: Event is rejected

**Ingest Continues Accepting Events After Failure:**
- ⚠️ **ISSUE:** Ingest continues accepting events after failure:
  - `services/ingest/app/main.py:504-698` - `ingest_event()` handles exceptions but does NOT terminate service
  - `services/ingest/app/main.py:681-695` - Returns HTTP 500 but service continues
  - ⚠️ **ISSUE:** Ingest service continues running after failures (no fail-closed behavior)

**Errors Logged but HTTP Returns Success:**
- ✅ Errors cause HTTP error codes: `services/ingest/app/main.py:554-557,582-585,619-622,644-647,668-671` - Returns HTTP 400/409/500 on errors
- ✅ Errors do NOT cause HTTP success: All error paths return HTTP error codes

**Retry Loops Hide Failure:**
- ✅ No retries: `services/ingest/README.md:40` - "NO retry logic"
- ✅ No retry loops found: `services/ingest/app/main.py:504-698` - No retry code found
- ✅ Failures cause immediate rejection: `services/ingest/app/main.py:554-557` - Returns HTTP error codes immediately

### Verdict: **PARTIAL**

**Justification:**
- DB unavailability, integrity violations, and internal exceptions cause rejection (not silent acceptance)
- No retries (fail-fast)
- **ISSUE:** Ingest continues accepting events after failure (service continues running, returns HTTP 500 but does not terminate)
- **ISSUE:** Schema mismatch at runtime causes HTTP 500 but service continues (not fail-closed)

---

## 8. NEGATIVE VALIDATION (MANDATORY)

### Evidence

**Invalid Envelope Reaches DB:**
- ✅ **PROVEN IMPOSSIBLE:** Invalid envelopes are NOT persisted:
  - `services/ingest/app/main.py:526-557` - Schema validation rejects invalid messages
  - `services/ingest/app/main.py:554-557` - Returns HTTP 400 BAD REQUEST
  - `services/ingest/app/main.py:559-585` - Hash integrity validation rejects invalid messages
  - `services/ingest/app/main.py:591-622` - Timestamp validation rejects invalid messages
  - ✅ **VERIFIED:** Invalid envelopes are rejected before storage (not persisted)

**Event Bypasses Integrity Checks:**
- ✅ **PROVEN IMPOSSIBLE:** Events cannot bypass integrity checks:
  - `services/ingest/app/main.py:526-557` - Schema validation occurs FIRST
  - `services/ingest/app/main.py:559-585` - Hash integrity validation occurs SECOND
  - `services/ingest/app/main.py:591-622` - Timestamp validation occurs THIRD
  - `services/ingest/app/main.py:632-647` - Duplicate check occurs FOURTH
  - `services/ingest/app/main.py:418-437` - Hash chain, sequence, idempotency verification occurs in `store_event()`
  - ✅ **VERIFIED:** All integrity checks must pass before storage (cannot bypass)

**Agent/DPI Can Inject Events Without Full Contract:**
- ✅ **PROVEN IMPOSSIBLE:** Agents/DPI cannot inject events without full contract:
  - `services/ingest/app/main.py:526-557` - Schema validation rejects incomplete messages
  - `contracts/event-envelope.schema.json:7-18` - All required fields must be present
  - `services/ingest/app/main.py:554-557` - Returns HTTP 400 BAD REQUEST on schema violation
  - ✅ **VERIFIED:** Events without full contract are rejected (not persisted)

**Ingest Mutates Event Identity or Ordering:**
- ⚠️ **PARTIAL:** Ingest mutates `ingested_at`:
  - `services/ingest/app/main.py:587-589` - Updates `ingested_at` to current UTC time
  - `services/ingest/README.md:28-30` - "Updates ingested_at (contract compliance: time-semantics.md)"
  - ⚠️ **ISSUE:** `ingested_at` is mutated (but this is documented and expected behavior)
- ✅ Event identity is NOT mutated: `event_id`, `machine_id`, `component`, `component_instance_id` are not mutated
- ✅ Event ordering is NOT mutated: `sequence` is not mutated
- ⚠️ **VERIFIED:** Ingest mutates `ingested_at` (but this is documented)

### Verdict: **PARTIAL**

**Justification:**
- Invalid envelopes cannot reach DB (schema validation rejects them)
- Events cannot bypass integrity checks (all checks must pass)
- Agents/DPI cannot inject events without full contract (schema validation enforces contract)
- **ISSUE:** Ingest mutates `ingested_at` (but this is documented and expected behavior)

---

## 9. VERDICT & IMPACT

### Section-by-Section Verdicts

1. **Component Identity & Boundary:** PARTIAL
   - Ingest is clearly identified as single HTTP entry point
   - No authentication (accepts events from any source)
   - Ingest mutates `ingested_at` during processing (but documented)

2. **Event Envelope Validation:** PASS
   - Strict schema validation is present and enforced
   - Missing required fields, type mismatches, and unknown fields are all rejected

3. **Time Semantics Enforcement:** PARTIAL
   - Time semantics are enforced (clock skew, age limits, late arrival detection)
   - `ingested_at` is rewritten during processing (but documented)
   - Out-of-order arrival is not explicitly handled

4. **Integrity & Ordering Guarantees:** PARTIAL
   - Hash verification, hash chain enforcement, and sequence monotonicity are present
   - Small sequence gaps (1-1000) are accepted (no explicit rejection)

5. **De-Duplication & Replay Protection:** PARTIAL
   - Duplicate detection by `event_id` is present and enforced
   - Replay with different `event_id` cannot be detected deterministically

6. **Persistence Behavior:** PASS
   - Transaction boundaries are explicit and proper
   - All-or-nothing writes are enforced

7. **Failure Semantics:** PARTIAL
   - Failures cause rejection (not silent acceptance)
   - Ingest continues accepting events after failure (service continues running)

8. **Negative Validation:** PARTIAL
   - Invalid envelopes cannot reach DB
   - Events cannot bypass integrity checks
   - Ingest mutates `ingested_at` (but documented)

### Overall Verdict: **PARTIAL**

**Justification:**
- **CRITICAL:** No authentication (accepts events from any source)
- **CRITICAL:** Ingest continues accepting events after failure (not fail-closed)
- **ISSUE:** Ingest mutates `ingested_at` during processing (but documented)
- **ISSUE:** Small sequence gaps (1-1000) are accepted (no explicit rejection)
- **ISSUE:** Replay with different `event_id` cannot be detected deterministically
- Schema validation, integrity checks, and persistence behavior are proper

**Blast Radius if Ingest is Compromised:**
- **CRITICAL:** If ingest is compromised, any source can inject events (no authentication)
- **CRITICAL:** If ingest is compromised, malformed events can be injected (if validation is bypassed)
- **CRITICAL:** If ingest is compromised, replay attacks are possible (if duplicate detection is bypassed)
- **CRITICAL:** If ingest is compromised, all downstream engines receive untrusted data
- **HIGH:** If ingest is compromised, correlation and AI results are untrustworthy
- **HIGH:** If ingest is compromised, system availability is compromised (no fail-closed behavior)

**Whether Downstream Components Remain Trustworthy:**
- ⚠️ **PARTIAL** - Downstream components can be trusted IF ingest validation is working:
  - ✅ If schema validation works, then downstream receives contract-valid events
  - ✅ If integrity checks work, then downstream receives integrity-verified events
  - ❌ If authentication is missing, then downstream receives events from untrusted sources
  - ❌ If ingest continues after failure, then downstream may receive inconsistent data
  - ⚠️ Schema validation and integrity checks are trustworthy, but authentication and fail-closed behavior are missing

**Recommendations:**
1. **CRITICAL:** Implement authentication (API keys, signatures, or other authentication mechanism)
2. **CRITICAL:** Implement fail-closed behavior (terminate service on critical failures)
3. **HIGH:** Implement explicit handling for out-of-order arrival (accept with warning, as per policy)
4. **HIGH:** Implement explicit handling for small sequence gaps (accept with warning, as per policy)
5. **HIGH:** Implement replay detection beyond `event_id` (sequence/hash-based duplicate detection)
6. **MEDIUM:** Document `ingested_at` mutation behavior more explicitly (why it's necessary)
7. **MEDIUM:** Resolve documentation vs code discrepancies (agents can write directly vs use HTTP POST)

---

**Validation Date:** 2025-01-13
**Validator:** Lead Validator & Compliance Auditor
**Next Step:** Validation Step 7 — Correlation Engine (if applicable)
