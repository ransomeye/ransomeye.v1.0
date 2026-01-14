# Validation Step 6 — Ingest Pipeline Validation

**Component Identity:**
- **Service:** Ingest Service (HTTP entry point)
- **Location:** `/home/ransomeye/rebuild/services/ingest/app/main.py`
- **Entry Point:** HTTP POST `POST /events` — `services/ingest/app/main.py:549` — `@app.post("/events")`
- **Database Write:** Ingest service writes to `raw_events`, `machines`, `component_instances`, `event_validation_log`

**Master Spec References:**
- Phase 4 — Minimal Data Plane (Ingest Service)
- Event Envelope Contract (`contracts/event-envelope.schema.json`)
- Time Semantics Policy (`contracts/time-semantics.policy.json`)
- Master specification: Ingest pipeline correctness requirements
- Master specification: Event integrity and replay requirements

---

## PURPOSE

This validation proves that the ingest pipeline enforces event envelope correctness, time semantics, sequence handling, replay behavior, integrity chain, and fail-closed behavior.

This file validates the ingest service entry point, not correlation or AI logic. This validation focuses on:
- Event envelope enforcement (schema validation, type correctness, required fields)
- Time semantics (event_time vs ingest_time, clock skew tolerance, late arrival)
- Sequence handling & monotonicity (per component_instance_id)
- Replay behavior (duplicate detection, idempotency)
- Integrity chain (hash propagation, hash chain continuity)
- Fail-closed behavior (DB errors block processing)

This validation does NOT validate correlation engine logic, AI/ML, UI, or agents.

---

## INGEST PIPELINE DEFINITION

**Ingest Pipeline Requirements (Master Spec):**

1. **Event Envelope Enforcement** — Events conform to schema, required fields present, type correctness enforced, unknown fields rejected
2. **Time Semantics** — event_time (observed_at) vs ingest_time (ingested_at) separation, clock skew tolerance, late arrival detection
3. **Sequence Handling & Monotonicity** — Sequence numbers monotonically increasing per component_instance_id, gaps detected
4. **Replay Behavior** — Replay of same events produces same raw_events records, duplicate detection, idempotency
5. **Integrity Chain** — Hash verification, hash chain continuity, hash propagation to storage
6. **Fail-Closed Behavior** — DB errors block processing, no "continue on error" logic exists

**Ingest Pipeline Structure:**
- **Entry Point:** HTTP POST `/events` endpoint
- **Validation Chain:** Schema → Hash → Timestamp → Duplicate → Storage
- **Storage Tables:** `machines`, `component_instances`, `raw_events`, `event_validation_log`

---

## WHAT IS VALIDATED

### 1. Event Envelope Enforcement
- Schema validation is strict and enforced
- Required fields are present and validated
- Type correctness is enforced
- Unknown fields are rejected

### 2. Time Semantics (event_time vs ingest_time)
- observed_at (event_time) is preserved from envelope
- ingested_at (ingest_time) handling is correct
- Clock skew tolerance is enforced
- Late arrival is detected and marked
- ingest_time does NOT affect downstream intelligence

### 3. Sequence Handling & Monotonicity
- Sequence numbers are monotonically increasing per component_instance_id
- Sequence gaps are detected
- Sequence violations cause rejection

### 4. Replay Behavior
- Replay of same events produces same raw_events records
- Duplicate detection is enforced
- Idempotency is guaranteed

### 5. Integrity Chain (Hash Propagation)
- Hash verification is enforced
- Hash chain continuity is verified
- Hash propagation to storage is correct

### 6. Fail-Closed Behavior
- DB errors block processing
- No "continue on error" logic exists

---

## WHAT IS EXPLICITLY NOT ASSUMED

- **NOT ASSUMED:** That ingest_time (ingested_at) does not affect downstream intelligence (ingested_at is stored in raw_events, may be used by correlation/AI)
- **NOT ASSUMED:** That replay produces identical raw_events records (ingested_at is mutated during processing)
- **NOT ASSUMED:** That pipeline does not mutate events (ingested_at is rewritten)
- **NOT ASSUMED:** That sequence gaps are rejected (small gaps are tolerated, large gaps rejected)

---

## VALIDATION METHODOLOGY

### Evidence Collection Strategy

1. **Schema Validation Analysis:** Examine schema validation code, error handling, rejection behavior
2. **Time Semantics Analysis:** Check observed_at vs ingested_at handling, clock skew tolerance, late arrival detection
3. **Sequence Analysis:** Check sequence monotonicity verification, gap detection, violation handling
4. **Replay Analysis:** Check duplicate detection, idempotency guarantees, replay behavior
5. **Integrity Analysis:** Check hash verification, hash chain continuity, hash propagation
6. **Error Handling Analysis:** Check fail-closed behavior, error blocking, "continue on error" logic

### Forbidden Patterns (Grep Validation)

- `ingested_at.*NOW|created_at.*NOW` — Non-deterministic timestamps (affects replay)
- `continue.*except|pass.*except` — Silent error handling (forbidden, must fail-closed)
- `retry|Retry` — Retry logic (forbidden, must fail-fast)

---

## 1. EVENT ENVELOPE ENFORCEMENT

### Evidence

**Schema Validation Is Strict and Enforced:**
- ✅ Schema is loaded: `services/ingest/app/main.py:226-237` — Loads schema from file
- ✅ Schema validation occurs: `services/ingest/app/main.py:341-354` — `validate_schema()` uses `jsonschema.validate()`
- ✅ Schema validation is strict: `services/ingest/app/main.py:344` — Uses `jsonschema.validate()` which raises `ValidationError` on failure
- ✅ Schema validation order: `services/ingest/app/main.py:571` — Schema validation occurs FIRST (before hash, timestamps, duplicate)

**Required Fields Are Present and Validated:**
- ✅ Required fields enforced: `contracts/event-envelope.schema.json:7-18` — `required` array lists all required fields
- ✅ Missing fields rejected: `services/ingest/app/main.py:571-602` — Returns HTTP 400 BAD REQUEST on schema violation
- ✅ Schema validation logs failure: `services/ingest/app/main.py:576-590` — Logs to `event_validation_log`

**Type Correctness Is Enforced:**
- ✅ Type validation enforced: `contracts/event-envelope.schema.json:20-114` — Type definitions for all fields
- ✅ Type mismatches rejected: `services/ingest/app/main.py:346-353` — `jsonschema.ValidationError` raised on type mismatch
- ✅ Type validation logs failure: `services/ingest/app/main.py:576-590` — Logs to `event_validation_log`

**Unknown Fields Are Rejected:**
- ✅ Unknown fields forbidden: `contracts/event-envelope.schema.json:19` — `additionalProperties: false`
- ✅ Unknown fields rejected: `services/ingest/app/main.py:344` — `jsonschema.validate()` rejects unknown fields
- ✅ Unknown fields cause schema violation: `services/ingest/app/main.py:347-351` — Returns "SCHEMA_VIOLATION" error

### Verdict: **PASS**

**Justification:**
- Schema validation is strict and enforced (jsonschema.validate raises ValidationError)
- Required fields are present and validated (required array enforced)
- Type correctness is enforced (type definitions validated)
- Unknown fields are rejected (additionalProperties: false)

**PASS Conditions (Met):**
- Schema validation is strict and enforced — **CONFIRMED** (jsonschema.validate raises ValidationError)
- Required fields are present and validated — **CONFIRMED** (required array enforced)
- Type correctness is enforced — **CONFIRMED** (type definitions validated)
- Unknown fields are rejected — **CONFIRMED** (additionalProperties: false)

**Evidence Required:**
- File paths: `services/ingest/app/main.py:226-237,341-354,571-602`, `contracts/event-envelope.schema.json:7-19,20-114`
- Schema validation: `validate_schema()`, `jsonschema.validate()`, error handling

---

## 2. TIME SEMANTICS (EVENT_TIME VS INGEST_TIME)

### Evidence

**observed_at (event_time) Is Preserved from Envelope:**
- ✅ observed_at is preserved: `services/ingest/app/main.py:433` — `observed_at = parser.isoparse(envelope["observed_at"])`
- ✅ observed_at stored in raw_events: `services/ingest/app/main.py:477-495` — INSERT INTO raw_events includes observed_at
- ✅ observed_at not mutated: observed_at value from envelope is stored directly (not rewritten)

**ingested_at (ingest_time) Handling Is Correct:**
- ⚠️ **ISSUE:** ingested_at is mutated: `services/ingest/app/main.py:632-634` — Updates `ingested_at` to current UTC time
- ✅ ingested_at is validated: `services/ingest/app/main.py:636` — `validate_timestamps()` validates `ingested_at` AFTER mutation
- ✅ ingested_at stored in raw_events: `services/ingest/app/main.py:477-495` — INSERT INTO raw_events includes ingested_at

**Clock Skew Tolerance Is Enforced:**
- ✅ Clock skew tolerance enforced: `services/ingest/app/main.py:374-381` — Rejects if `ingested_at - observed_at < -5` seconds (future beyond tolerance)
- ✅ Clock skew tolerance matches policy: `contracts/time-semantics.policy.json:53-56` — `max_future_seconds: 5`
- ✅ Clock skew violation rejected: `services/ingest/app/main.py:374-381` — Returns HTTP 400 BAD REQUEST

**Late Arrival Is Detected and Marked:**
- ✅ Late arrival detected: `services/ingest/app/main.py:391` — `late_arrival = time_diff > 3600` (1 hour)
- ✅ Late arrival threshold matches policy: `contracts/time-semantics.policy.json:69-72` — `threshold_hours: 1`
- ✅ Late arrival is marked: `services/ingest/app/main.py:391-392` — Sets `late_arrival` flag and `arrival_latency_seconds`
- ✅ Late arrival is stored: `services/ingest/app/main.py:469` — `late_arrival` and `arrival_latency_seconds` stored in `raw_events`

**ingest_time Does NOT Affect Downstream Intelligence:**
- ❌ **CRITICAL FAILURE:** ingested_at is stored in raw_events: `services/ingest/app/main.py:477-495` — INSERT INTO raw_events includes ingested_at
- ❌ **CRITICAL FAILURE:** ingested_at may be used by correlation: Correlation engine reads from raw_events table (may use ingested_at)
- ⚠️ **ISSUE:** ingested_at affects replay determinism (same event replayed has different ingested_at)

### Verdict: **FAIL**

**Justification:**
- observed_at (event_time) is preserved from envelope
- Clock skew tolerance is enforced
- Late arrival is detected and marked
- **CRITICAL FAILURE:** ingested_at (ingest_time) is mutated during processing (non-deterministic)
- **CRITICAL FAILURE:** ingested_at is stored in raw_events (may affect downstream intelligence)

**FAIL Conditions (Met):**
- ingest_time affects downstream intelligence — **CONFIRMED** (ingested_at stored in raw_events, may be used by correlation/AI)

**Evidence Required:**
- File paths: `services/ingest/app/main.py:632-634,477-495,374-391`, `contracts/time-semantics.policy.json:53-56,69-72`
- Timestamp mutation: `ingested_at` updated to current UTC time
- Storage: `ingested_at` stored in `raw_events` table

---

## 3. SEQUENCE HANDLING & MONOTONICITY

### Evidence

**Sequence Numbers Are Monotonically Increasing per component_instance_id:**
- ✅ Sequence monotonicity verification occurs: `services/ingest/app/main.py:450-456` — `verify_sequence_monotonicity()` verifies monotonicity
- ✅ Sequence monotonicity verification in storage: `services/ingest/app/main.py:452-456` — Verifies sequence monotonicity during `store_event()`
- ✅ Sequence monotonicity violation causes rejection: `services/ingest/app/main.py:454-456` — Raises `ValueError` on sequence violation
- ✅ Sequence monotonicity violation is logged: `services/ingest/app/main.py:454-455` — Logs error, then raises exception
- ✅ Sequence monotonicity violation returns HTTP 400: `services/ingest/app/main.py:719-722` — Returns HTTP 400 BAD REQUEST on integrity violation

**Sequence Gaps Are Detected:**
- ✅ Large gaps rejected: `common/integrity/verification.py:116-118` — Large gaps (>1000) are rejected
- ⚠️ **ISSUE:** Small gaps tolerated: `common/integrity/verification.py:102-114` — Small gaps (1-1000) are accepted (no explicit rejection)
- ✅ Sequence must be > max_sequence: `common/integrity/verification.py:103` — Sequence must be > max_sequence (monotonically increasing)

**Sequence Violations Cause Rejection:**
- ✅ Sequence violations cause rejection: `services/ingest/app/main.py:454-456` — Raises `ValueError` on sequence violation
- ✅ Sequence violations return HTTP 400: `services/ingest/app/main.py:719-722` — Returns HTTP 400 BAD REQUEST

### Verdict: **PASS**

**Justification:**
- Sequence numbers are monotonically increasing per component_instance_id (verify_sequence_monotonicity enforces)
- Sequence violations cause rejection (ValueError raised, HTTP 400 returned)
- Large gaps are rejected (>1000)
- Small gaps are tolerated (1-1000), but sequence must still be > max_sequence

**PASS Conditions (Met):**
- Sequence numbers are monotonically increasing per component_instance_id — **CONFIRMED** (verify_sequence_monotonicity enforces)
- Sequence violations cause rejection — **CONFIRMED** (ValueError raised, HTTP 400 returned)

**Evidence Required:**
- File paths: `services/ingest/app/main.py:450-456,719-722`, `common/integrity/verification.py:76-120`
- Sequence verification: `verify_sequence_monotonicity()`, gap detection, violation handling

---

## 4. REPLAY BEHAVIOR

### Evidence

**Replay of Same Events Produces Same raw_events Records:**
- ❌ **CRITICAL FAILURE:** Replay does NOT produce same raw_events records:
  - `services/ingest/app/main.py:632-634` — `ingested_at` is mutated to current UTC time (non-deterministic)
  - Same event replayed at different times has different `ingested_at` values
  - `services/ingest/app/main.py:477-495` — INSERT INTO raw_events includes ingested_at (non-deterministic)
- ⚠️ **ISSUE:** Replay produces different raw_events records (ingested_at differs, other fields identical)

**Duplicate Detection Is Enforced:**
- ✅ Duplicate detection by `event_id`: `services/ingest/app/main.py:411-415` — `check_duplicate()` checks `event_id`
- ✅ `event_id` is UUID: `contracts/event-envelope.schema.json:21-24` — UUID v4 format
- ✅ `event_id` is PRIMARY KEY: `schemas/01_raw_events.sql:26` — `event_id UUID NOT NULL PRIMARY KEY`
- ✅ Duplicate `event_id` causes rejection: `services/ingest/app/main.py:677-692` — Returns HTTP 409 CONFLICT on duplicate
- ✅ Duplicate `event_id` is logged: `services/ingest/app/main.py:679-687` — Logs to `event_validation_log`

**Idempotency Is Guaranteed:**
- ✅ Idempotency verification occurs: `services/ingest/app/main.py:458-462` — `verify_idempotency()` checks for duplicate `event_id`
- ✅ Idempotency verification in storage: `services/ingest/app/main.py:459-462` — Verifies idempotency during `store_event()`
- ✅ Idempotency violation causes rejection: `services/ingest/app/main.py:460-462` — Raises `ValueError` on idempotency violation
- ✅ Database PRIMARY KEY constraint: `schemas/01_raw_events.sql:26` — PRIMARY KEY constraint prevents duplicate `event_id`

### Verdict: **FAIL**

**Justification:**
- Duplicate detection is enforced (duplicate event_id rejected)
- Idempotency is guaranteed (idempotency verification, PRIMARY KEY constraint)
- **CRITICAL FAILURE:** Replay does NOT produce same raw_events records (ingested_at is mutated, non-deterministic)

**FAIL Conditions (Met):**
- Replay does not reproduce same raw_events — **CONFIRMED** (ingested_at is mutated to current UTC time, non-deterministic)

**Evidence Required:**
- File paths: `services/ingest/app/main.py:632-634,477-495,677-692,458-462`, `schemas/01_raw_events.sql:26`
- Replay non-determinism: `ingested_at` mutated to current UTC time
- Duplicate detection: `check_duplicate()`, `verify_idempotency()`, PRIMARY KEY constraint

---

## 5. INTEGRITY CHAIN (HASH PROPAGATION)

### Evidence

**Hash Verification Is Enforced:**
- ✅ Hash verification occurs: `services/ingest/app/main.py:401-409` — `validate_hash_integrity()` verifies hash
- ✅ Hash computation: `services/ingest/app/main.py:329-339` — `compute_hash()` computes SHA256 hash (excludes hash_sha256 field)
- ✅ Hash mismatch causes rejection: `services/ingest/app/main.py:604-630` — Returns HTTP 400 BAD REQUEST on hash mismatch
- ✅ Hash mismatch is logged: `services/ingest/app/main.py:610-625` — Logs to `event_validation_log`

**Hash Chain Continuity Is Verified:**
- ✅ Hash chain verification occurs: `services/ingest/app/main.py:443-448` — `verify_hash_chain_continuity()` verifies chain
- ✅ Hash chain verification in storage: `services/ingest/app/main.py:445-448` — Verifies hash chain during `store_event()`
- ✅ Hash chain violation causes rejection: `services/ingest/app/main.py:447-448` — Raises `ValueError` on hash chain violation
- ✅ Hash chain violation is logged: `services/ingest/app/main.py:447` — Logs error, then raises exception
- ✅ Hash chain violation returns HTTP 400: `services/ingest/app/main.py:719-722` — Returns HTTP 400 BAD REQUEST on integrity violation

**Hash Propagation to Storage Is Correct:**
- ✅ Hash stored in raw_events: `services/ingest/app/main.py:477-495` — INSERT INTO raw_events includes hash_sha256
- ✅ prev_hash_sha256 stored: `services/ingest/app/main.py:477-495` — INSERT INTO raw_events includes prev_hash_sha256
- ✅ Hash propagation is correct: Hash values from envelope are stored directly (not recomputed)

### Verdict: **PASS**

**Justification:**
- Hash verification is enforced (validate_hash_integrity verifies hash)
- Hash chain continuity is verified (verify_hash_chain_continuity enforces chain)
- Hash propagation to storage is correct (hash values stored directly)

**PASS Conditions (Met):**
- Hash verification is enforced — **CONFIRMED** (validate_hash_integrity verifies hash)
- Hash chain continuity is verified — **CONFIRMED** (verify_hash_chain_continuity enforces chain)
- Hash propagation to storage is correct — **CONFIRMED** (hash values stored directly)

**Evidence Required:**
- File paths: `services/ingest/app/main.py:329-339,401-409,443-448,477-495,604-630,719-722`
- Hash verification: `validate_hash_integrity()`, `compute_hash()`, hash mismatch handling
- Hash chain: `verify_hash_chain_continuity()`, hash chain violation handling

---

## 6. FAIL-CLOSED BEHAVIOR

### Evidence

**DB Errors Block Processing:**
- ✅ DB unavailability causes error: `services/ingest/app/main.py:198-209` — `get_db_connection()` raises `RuntimeError` on failure
- ✅ Error causes HTTP 500: `services/ingest/app/main.py:732-746` — Returns HTTP 500 INTERNAL ERROR on exception
- ✅ Error is logged: `services/ingest/app/main.py:741` — Logs error
- ✅ No retries: `services/ingest/README.md:40` — "NO retry logic: Does not retry failed database operations"

**No "Continue on Error" Logic Exists:**
- ✅ No continue-on-error logic: All DB errors cause immediate HTTP exception
- ✅ Failures cause immediate rejection: `services/ingest/app/main.py:571-602` — Returns HTTP error codes
- ✅ No fallback processing: No fallback paths found in database operations

**Service Continues After Error:**
- ⚠️ **ISSUE:** Service continues after error:
  - `services/ingest/app/main.py:549-748` — `ingest_event()` handles exceptions but does NOT terminate service
  - `services/ingest/app/main.py:732-746` — Returns HTTP 500 but service continues
  - ⚠️ **ISSUE:** Ingest service continues running after failures (no fail-closed behavior for service termination)

### Verdict: **PARTIAL**

**Justification:**
- DB errors block processing (fail-fast, no retries)
- No "continue on error" logic exists (all DB errors cause immediate HTTP exception)
- **ISSUE:** Service continues after error (service continues running, returns HTTP 500 but does not terminate)

**PASS Conditions (Met):**
- DB errors block processing — **CONFIRMED** (fail-fast, no retries)
- No "continue on error" logic exists — **CONFIRMED** (all DB errors cause immediate HTTP exception)

**Evidence Required:**
- File paths: `services/ingest/app/main.py:198-209,732-746,571-602`, `services/ingest/README.md:40`
- Error handling: Fail-fast, no retries, HTTP error codes
- Service behavior: Service continues after error (not fail-closed for service termination)

---

## CREDENTIAL TYPES VALIDATED

### Database Credentials
- **Type:** PostgreSQL user/password (`RANSOMEYE_DB_USER`/`RANSOMEYE_DB_PASSWORD`)
- **Source:** Environment variable (required, no default)
- **Validation:** ❌ **NOT VALIDATED** (validation file 05 covers database credentials)
- **Usage:** Database connection for storage operations
- **Status:** ❌ **NOT VALIDATED** (outside scope of this validation)

---

## PASS CONDITIONS

### Section 1: Event Envelope Enforcement
- ✅ Schema validation is strict and enforced — **PASS**
- ✅ Required fields are present and validated — **PASS**
- ✅ Type correctness is enforced — **PASS**
- ✅ Unknown fields are rejected — **PASS**

### Section 2: Time Semantics (event_time vs ingest_time)
- ✅ observed_at (event_time) is preserved from envelope — **PASS**
- ✅ Clock skew tolerance is enforced — **PASS**
- ✅ Late arrival is detected and marked — **PASS**
- ❌ ingest_time does NOT affect downstream intelligence — **FAIL**

### Section 3: Sequence Handling & Monotonicity
- ✅ Sequence numbers are monotonically increasing per component_instance_id — **PASS**
- ✅ Sequence violations cause rejection — **PASS**

### Section 4: Replay Behavior
- ❌ Replay of same events produces same raw_events records — **FAIL**
- ✅ Duplicate detection is enforced — **PASS**
- ✅ Idempotency is guaranteed — **PASS**

### Section 5: Integrity Chain (Hash Propagation)
- ✅ Hash verification is enforced — **PASS**
- ✅ Hash chain continuity is verified — **PASS**
- ✅ Hash propagation to storage is correct — **PASS**

### Section 6: Fail-Closed Behavior
- ✅ DB errors block processing — **PASS**
- ✅ No "continue on error" logic exists — **PASS**

---

## FAIL CONDITIONS

### Section 1: Event Envelope Enforcement
- ❌ Schema validation is not strict — **NOT CONFIRMED** (schema validation is strict)
- ❌ Required fields are not validated — **NOT CONFIRMED** (required fields are validated)
- ❌ Type correctness is not enforced — **NOT CONFIRMED** (type correctness is enforced)
- ❌ Unknown fields are accepted — **NOT CONFIRMED** (unknown fields are rejected)

### Section 2: Time Semantics (event_time vs ingest_time)
- ❌ **CONFIRMED:** ingest_time affects downstream intelligence — **ingested_at stored in raw_events, may be used by correlation/AI**

### Section 3: Sequence Handling & Monotonicity
- ❌ Sequence numbers are not monotonically increasing — **NOT CONFIRMED** (sequence monotonicity is enforced)
- ❌ Sequence violations are not rejected — **NOT CONFIRMED** (sequence violations cause rejection)

### Section 4: Replay Behavior
- ❌ **CONFIRMED:** Replay does not reproduce same raw_events — **ingested_at is mutated to current UTC time (non-deterministic)**

### Section 5: Integrity Chain (Hash Propagation)
- ❌ Hash verification is not enforced — **NOT CONFIRMED** (hash verification is enforced)
- ❌ Hash chain continuity is not verified — **NOT CONFIRMED** (hash chain continuity is verified)
- ❌ Hash propagation to storage is incorrect — **NOT CONFIRMED** (hash propagation is correct)

### Section 6: Fail-Closed Behavior
- ❌ DB errors do not block processing — **NOT CONFIRMED** (DB errors block processing)
- ❌ "Continue on error" logic exists — **NOT CONFIRMED** (no "continue on error" logic)

---

## EVIDENCE REQUIRED

### Event Envelope Enforcement
- File paths: `services/ingest/app/main.py:226-237,341-354,571-602`, `contracts/event-envelope.schema.json:7-19,20-114`
- Schema validation: `validate_schema()`, `jsonschema.validate()`, error handling

### Time Semantics (event_time vs ingest_time)
- File paths: `services/ingest/app/main.py:632-634,477-495,374-391`, `contracts/time-semantics.policy.json:53-56,69-72`
- Timestamp mutation: `ingested_at` updated to current UTC time
- Storage: `ingested_at` stored in `raw_events` table

### Sequence Handling & Monotonicity
- File paths: `services/ingest/app/main.py:450-456,719-722`, `common/integrity/verification.py:76-120`
- Sequence verification: `verify_sequence_monotonicity()`, gap detection, violation handling

### Replay Behavior
- File paths: `services/ingest/app/main.py:632-634,477-495,677-692,458-462`, `schemas/01_raw_events.sql:26`
- Replay non-determinism: `ingested_at` mutated to current UTC time
- Duplicate detection: `check_duplicate()`, `verify_idempotency()`, PRIMARY KEY constraint

### Integrity Chain (Hash Propagation)
- File paths: `services/ingest/app/main.py:329-339,401-409,443-448,477-495,604-630,719-722`
- Hash verification: `validate_hash_integrity()`, `compute_hash()`, hash mismatch handling
- Hash chain: `verify_hash_chain_continuity()`, hash chain violation handling

### Fail-Closed Behavior
- File paths: `services/ingest/app/main.py:198-209,732-746,571-602`, `services/ingest/README.md:40`
- Error handling: Fail-fast, no retries, HTTP error codes
- Service behavior: Service continues after error (not fail-closed for service termination)

---

## GA VERDICT

### Overall: **FAIL**

**Critical Blockers:**
1. **FAIL:** ingest_time affects downstream intelligence (ingested_at stored in raw_events, may be used by correlation/AI)
   - **Impact:** ingested_at is stored in raw_events table, may be used by correlation engine or AI
   - **Location:** `services/ingest/app/main.py:632-634,477-495` — ingested_at mutated and stored
   - **Severity:** **CRITICAL** (violates requirement that ingest_time does not affect downstream intelligence)
   - **Master Spec Violation:** ingest_time must not affect downstream intelligence

2. **FAIL:** Replay does not reproduce same raw_events records (ingested_at is mutated, non-deterministic)
   - **Impact:** Same event replayed at different times produces different raw_events records (ingested_at differs)
   - **Location:** `services/ingest/app/main.py:632-634` — ingested_at updated to current UTC time
   - **Severity:** **CRITICAL** (violates replay determinism requirement)
   - **Master Spec Violation:** Replay must produce same raw_events records

3. **PARTIAL:** Pipeline mutates events nondeterministically (ingested_at is mutated)
   - **Impact:** ingested_at is rewritten during processing (non-deterministic)
   - **Location:** `services/ingest/app/main.py:632-634` — ingested_at updated to current UTC time
   - **Severity:** **HIGH** (affects replay determinism)
   - **Master Spec Violation:** Pipeline must not mutate events nondeterministically

**Non-Blocking Issues:**
1. Event envelope enforcement is correct (schema validation, type correctness, unknown fields rejected)
2. Sequence handling & monotonicity is correct (monotonicity enforced, violations rejected)
3. Integrity chain is correct (hash verification, hash chain continuity, hash propagation)
4. Fail-closed behavior is correct (DB errors block processing, no "continue on error" logic)

**Strengths:**
1. ✅ Schema validation is strict and enforced
2. ✅ Required fields are present and validated
3. ✅ Type correctness is enforced
4. ✅ Sequence numbers are monotonically increasing per component_instance_id
5. ✅ Hash verification is enforced
6. ✅ Hash chain continuity is verified
7. ✅ Duplicate detection is enforced
8. ✅ Idempotency is guaranteed

**Recommendations:**
1. **CRITICAL:** Make ingested_at deterministic (use observed_at or fixed timestamp, not current UTC time)
2. **CRITICAL:** Ensure ingested_at does not affect downstream intelligence (document that ingested_at is metadata only, not used by correlation/AI)
3. **CRITICAL:** Fix replay determinism (ensure replay produces same raw_events records)
4. **HIGH:** Document ingested_at mutation behavior (why it's necessary, if it is)
5. **MEDIUM:** Consider fail-closed behavior for service termination (terminate service on critical failures)

---

**Validation Date:** 2025-01-13  
**Validator:** Independent System Validator  
**Next Step:** Validation Step 7 — Correlation Engine  
**GA Status:** **BLOCKED** (Critical failures in time semantics and replay determinism)
