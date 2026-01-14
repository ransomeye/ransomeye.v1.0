# Validation Step 4 — Ingest → Normalization → Database Write Validation

**Component Identity:**
- **Name:** Telemetry Ingest Service (Data Plane)
- **Primary Paths:**
  - `/home/ransomeye/rebuild/services/ingest/app/main.py` — Main ingest service
  - `/home/ransomeye/rebuild/services/ingest/app/main_hardened.py` — Hardened variant
- **Entry Points:**
  - HTTP POST: `POST /events` — `services/ingest/app/main.py:549` — `@app.post("/events")`
  - Health check: `GET /health` — `services/ingest/app/main.py:751` — `@app.get("/health")`
- **Database Write Access:** Ingest service writes to `raw_events`, `machines`, `component_instances`, `event_validation_log`

**Master Spec References:**
- Phase 4 — Minimal Data Plane (Ingest Service)
- Phase 10.1 — Core Runtime Hardening (data plane hardening)
- Event Envelope Contract (`contracts/event-envelope.schema.json`)
- Time Semantics Contract (`contracts/time-semantics.policy.json`)
- Master specification: Deterministic data plane requirements
- Master specification: Fail-closed data plane requirements

---

## PURPOSE

This validation proves that the data plane is correct, deterministic, credential-safe, and fail-closed from ingest entry to database persistence.

This file validates correctness and integrity, not trust (trust was validated in File 03). This validation focuses on:
- Event envelope validation correctness
- Normalization determinism
- Integrity and sequence guarantees
- Database write semantics
- Credential usage at DB layer
- Fail-closed guarantees

This validation does NOT validate inter-service trust, correlation engine, agents, or DPI.

---

## DATA PLANE DEFINITION

**Data Plane Requirements (Master Spec):**

1. **Ingest Entry Validation** — Event envelope validation is mandatory, schema enforcement blocks malformed events, missing required fields cause rejection
2. **Normalization Determinism** — Same raw event → same normalized output, field ordering/timestamps/IDs are deterministic, no environment- or time-based mutation
3. **Integrity & Sequence Guarantees** — Hash integrity checks, sequence monotonicity, duplicate detection behavior, replay handling
4. **Database Write Semantics** — DB writes are transactional, partial writes cannot occur, failed writes cause rollback
5. **Credential Usage at DB Layer** — DB credentials used are explicit, no fallback credentials exist, missing credentials block writes
6. **Fail-Closed Guarantees** — Any ingest/normalize/write failure stops processing, no "best effort" or "continue on error" logic

**Data Flow:**
1. **Ingest Entry:** HTTP POST `/events` → JSON parsing → Schema validation
2. **Normalization:** (No normalization in ingest per README)
3. **Integrity Checks:** Hash integrity → Sequence monotonicity → Hash chain continuity → Duplicate detection
4. **Database Write:** Transaction begin → Write to `machines`, `component_instances`, `raw_events`, `event_validation_log` → Transaction commit/rollback

---

## WHAT IS VALIDATED

### 1. Ingest Entry Validation
- Event envelope validation is mandatory
- Schema enforcement blocks malformed events
- Missing required fields cause rejection

### 2. Normalization Determinism
- Same raw event → same normalized output
- Field ordering, timestamps, IDs are deterministic
- No environment- or time-based mutation

### 3. Integrity & Sequence Guarantees
- Hash integrity checks
- Sequence monotonicity
- Duplicate detection behavior
- Replay handling

### 4. Database Write Semantics
- DB writes are transactional
- Partial writes cannot occur
- Failed writes cause rollback

### 5. Credential Usage at DB Layer
- DB credentials used are explicit
- No fallback credentials exist
- Missing credentials block writes

### 6. Fail-Closed Guarantees
- Any ingest/normalize/write failure stops processing
- No "best effort" or "continue on error" logic

---

## WHAT IS EXPLICITLY NOT ASSUMED

- **NOT ASSUMED:** That normalization happens in ingest (README confirms no normalization in ingest)
- **NOT ASSUMED:** That `ingested_at` is deterministic (it uses `datetime.now()` which is time-based)
- **NOT ASSUMED:** That SQL `NOW()` is deterministic (it uses database server time)
- **NOT ASSUMED:** That sequence gaps are acceptable (sequence monotonicity is enforced)
- **NOT ASSUMED:** That partial writes are acceptable (transactions ensure atomicity)

---

## VALIDATION METHODOLOGY

### Evidence Collection Strategy

1. **Code Path Analysis:** Trace event flow from HTTP POST → validation → database write
2. **Determinism Analysis:** Search for `now()`, `datetime.now()`, `time.time()`, `random`, `uuid`, `UUID`, `generate`, `NOW()` in SQL
3. **Transaction Analysis:** Search for `begin`, `commit`, `rollback`, `transaction`, `atomic`, `partial`, `best.*effort`, `continue.*error`
4. **Credential Analysis:** Search for `RANSOMEYE_DB_PASSWORD`, `get_secret`, `fallback`, `default.*password`, `shared.*credential`
5. **Error Handling Analysis:** Search for `silent`, `data.*loss`, `continue.*error`, `best.*effort`, `partial.*write`

### Forbidden Patterns (Grep Validation)

- `now\(\)|datetime\.now|time\.time|random|uuid|UUID|generate|NOW\(\)` — Non-deterministic time/random generation (forbidden in normalization)
- `best.*effort|continue.*error|partial.*write|silent.*drop` — Best-effort or continue-on-error logic (forbidden)
- `fallback.*credential|default.*password|shared.*credential` — Fallback credentials (forbidden)

---

## 1. INGEST ENTRY VALIDATION

### Evidence

**Event Envelope Validation is Mandatory:**
- ✅ Schema validation occurs: `services/ingest/app/main.py:571` — `validate_schema(envelope)` called before processing
- ✅ Schema validation is mandatory: `services/ingest/app/main.py:571-602` — Returns HTTP 400 BAD REQUEST if validation fails
- ✅ Validation order: Schema → Hash → Timestamps → Duplicate → Storage
- ✅ No bypass: Schema validation cannot be bypassed (called before any processing)

**Schema Enforcement Blocks Malformed Events:**
- ✅ Strict schema exists: `contracts/event-envelope.schema.json` — Event envelope schema with `additionalProperties: false`
- ✅ Schema validation uses jsonschema: `services/ingest/app/main.py:341-353` — `validate_schema()` uses `jsonschema.validate()`
- ✅ Malformed events rejected: `services/ingest/app/main.py:571-602` — Returns HTTP 400 BAD REQUEST on schema violation
- ✅ Schema validation logs failure: `services/ingest/app/main.py:577-590` — Logs to `event_validation_log`
- ✅ Unknown fields rejected: `contracts/event-envelope.schema.json:19` — `additionalProperties: false` prevents unknown fields

**Missing Required Fields Cause Rejection:**
- ✅ Required fields enforced: `contracts/event-envelope.schema.json:7-18` — `required` array lists all required fields
- ✅ Missing fields rejected: `services/ingest/app/main.py:344` — `jsonschema.ValidationError` raised on missing required fields
- ✅ Missing fields cause HTTP 400: `services/ingest/app/main.py:599-602` — Returns HTTP 400 BAD REQUEST with error details

**Validation Errors Are Not Ignored or Logged Only:**
- ✅ Validation errors cause rejection: `services/ingest/app/main.py:571-602` — Returns HTTP 400 BAD REQUEST (not logged only)
- ✅ Validation errors are logged: `services/ingest/app/main.py:590` — Logs to `event_validation_log` (in addition to rejection)
- ✅ No "log and continue" logic: Validation failures cause immediate HTTP exception (no processing continues)

### Verdict: **PASS**

**Justification:**
- Event envelope validation is mandatory (cannot be bypassed)
- Schema enforcement blocks malformed events (strict schema, unknown fields rejected)
- Missing required fields cause rejection (HTTP 400 BAD REQUEST)
- Validation errors are not ignored or logged only (rejection + logging)

**PASS Conditions (Met):**
- Event envelope validation is mandatory — **CONFIRMED** (validation called before processing)
- Schema enforcement blocks malformed events — **CONFIRMED** (strict schema, HTTP 400 on violation)
- Missing required fields cause rejection — **CONFIRMED** (jsonschema validation, HTTP 400)

**Evidence Required:**
- File paths: `services/ingest/app/main.py:341-353,571-602`, `contracts/event-envelope.schema.json:7-19`
- Validation code: `validate_schema()` function, `jsonschema.validate()` call
- Error handling: HTTP 400 BAD REQUEST on validation failure

---

## 2. NORMALIZATION DETERMINISM

### Evidence

**Normalization in Ingest:**
- ❌ **CRITICAL FAILURE:** No normalization occurs in ingest service:
  - `services/ingest/README.md:50` — "NO normalization: Does not write to normalized tables"
  - `services/ingest/README.md:97` — "Does NOT write to normalized tables"
  - No normalization code found in ingest service
- ⚠️ **ISSUE:** Normalization is deferred to downstream (not in ingest)

**Same Raw Event → Same Normalized Output:**
- ⚠️ **N/A:** No normalization in ingest (cannot validate normalization determinism)
- ⚠️ **ISSUE:** Event data is stored as-is from envelope (no normalization)

**Field Ordering, Timestamps, IDs Are Deterministic:**
- ✅ Field ordering is deterministic: `services/ingest/app/main.py:464-503` — Database INSERT uses explicit field order
- ✅ Event ID is deterministic: `contracts/event-envelope.schema.json:21-24` — `event_id` is UUID from envelope (not generated)
- ❌ **CRITICAL FAILURE:** `ingested_at` is NOT deterministic: `services/ingest/app/main.py:633` — `datetime.now(timezone.utc)` uses current time
- ❌ **CRITICAL FAILURE:** SQL `NOW()` is NOT deterministic: `services/ingest/app/main.py:507` — `VALUES (%s, %s, NOW())` uses database server time
- ⚠️ **ISSUE:** Same event ingested at different times will have different `ingested_at` values

**No Environment- or Time-Based Mutation:**
- ❌ **CRITICAL FAILURE:** `ingested_at` is time-based: `services/ingest/app/main.py:633` — `datetime.now(timezone.utc)` mutates based on ingestion time
- ❌ **CRITICAL FAILURE:** SQL `NOW()` is time-based: `services/ingest/app/main.py:507` — `NOW()` mutates based on database server time
- ✅ No environment-based mutation: No environment variables used for field mutation
- ✅ No random generation: No `random`, `uuid`, `UUID` generation found in normalization path

**Normalization Depends on `now()`:**
- ❌ **CRITICAL FAILURE:** `ingested_at` depends on `now()`: `services/ingest/app/main.py:633` — `datetime.now(timezone.utc).isoformat()`
- ❌ **CRITICAL FAILURE:** SQL `NOW()` depends on database server time: `services/ingest/app/main.py:507` — `NOW()` in SQL

**Random IDs Generated During Normalization:**
- ✅ No random IDs generated: No `random`, `uuid`, `UUID` generation found in normalization path
- ✅ Event ID comes from envelope: `services/ingest/app/main.py:429` — `event_id = envelope["event_id"]` (not generated)

### Verdict: **FAIL**

**Justification:**
- **CRITICAL FAILURE:** No normalization occurs in ingest (deferred to downstream)
- **CRITICAL FAILURE:** `ingested_at` is NOT deterministic (uses `datetime.now()` which is time-based)
- **CRITICAL FAILURE:** SQL `NOW()` is NOT deterministic (uses database server time)
- Same event ingested at different times will have different `ingested_at` values (non-deterministic)

**FAIL Conditions (Met):**
- Normalization depends on `now()` — **CONFIRMED** (`datetime.now()` and SQL `NOW()`)
- Random IDs are generated during normalization — **NOT CONFIRMED** (no random IDs, but timestamps are non-deterministic)

**Evidence Required:**
- File paths: `services/ingest/app/main.py:633,507`, `services/ingest/README.md:50,97`
- Non-deterministic code: `datetime.now(timezone.utc)`, SQL `NOW()`
- Missing normalization: No normalization code in ingest service

---

## 3. INTEGRITY & SEQUENCE GUARANTEES

### Evidence

**Hash Integrity Checks:**
- ✅ Hash integrity validation exists: `services/ingest/app/main.py:401-409` — `validate_hash_integrity()` function
- ✅ Hash integrity is checked: `services/ingest/app/main.py:604-630` — Called before storage
- ✅ Hash mismatch causes rejection: `services/ingest/app/main.py:604-630` — Returns HTTP 400 BAD REQUEST on hash mismatch
- ✅ Hash computation is deterministic: `services/ingest/app/main.py:329-339` — `compute_hash()` uses `sort_keys=True` for deterministic JSON serialization

**Sequence Monotonicity:**
- ✅ Sequence monotonicity validation exists: `services/ingest/app/main.py:451-456` — `verify_sequence_monotonicity()` called
- ✅ Sequence monotonicity is checked: `common/integrity/verification.py:76-105` — `verify_sequence_monotonicity()` function
- ✅ Sequence gaps cause rejection: `services/ingest/app/main.py:451-456` — Raises `ValueError` on sequence violation
- ✅ Sequence violations cause HTTP 400: `services/ingest/app/main.py:703-722` — Returns HTTP 400 BAD REQUEST on integrity violation

**Duplicate Detection Behavior:**
- ✅ Duplicate detection exists: `services/ingest/app/main.py:411-415` — `check_duplicate()` function
- ✅ Duplicate detection is checked: `services/ingest/app/main.py:677-692` — Called before storage
- ✅ Duplicate events cause rejection: `services/ingest/app/main.py:677-692` — Returns HTTP 409 CONFLICT on duplicate
- ✅ Duplicate detection uses `event_id`: `services/ingest/app/main.py:414` — `SELECT 1 FROM raw_events WHERE event_id = %s`

**Replay Handling:**
- ✅ Duplicate detection prevents exact replays: `services/ingest/app/main.py:677-692` — Duplicate `event_id` rejected
- ✅ Sequence monotonicity prevents out-of-order replays: `services/ingest/app/main.py:451-456` — Sequence gaps rejected
- ✅ Hash chain continuity prevents hash chain breaks: `services/ingest/app/main.py:443-448` — Hash chain violations rejected
- ⚠️ **ISSUE:** No cryptographic nonces prevent replay of valid events (only duplicate detection and sequence monotonicity)

**Sequence Gaps Are Silently Accepted:**
- ❌ **CONFIRMED:** Sequence gaps are NOT silently accepted: `services/ingest/app/main.py:451-456` — `verify_sequence_monotonicity()` raises `ValueError` on gaps
- ✅ Sequence gaps cause rejection: `common/integrity/verification.py:76-105` — Sequence gaps detected and rejected

**Hash Mismatches Are Logged But Not Blocked:**
- ❌ **CONFIRMED:** Hash mismatches are NOT logged but not blocked: `services/ingest/app/main.py:604-630` — Returns HTTP 400 BAD REQUEST (blocked, not just logged)
- ✅ Hash mismatches cause rejection: `services/ingest/app/main.py:604-630` — HTTP 400 BAD REQUEST + logging

### Verdict: **PASS**

**Justification:**
- Hash integrity checks are present and enforced (HTTP 400 on mismatch)
- Sequence monotonicity is present and enforced (ValueError on violation)
- Duplicate detection is present and enforced (HTTP 409 on duplicate)
- Replay handling is present (duplicate detection, sequence monotonicity, hash chain continuity)
- Sequence gaps are NOT silently accepted (rejected with ValueError)
- Hash mismatches are NOT logged but not blocked (rejected with HTTP 400)

**PASS Conditions (Met):**
- Hash integrity checks — **CONFIRMED** (validation exists, HTTP 400 on mismatch)
- Sequence monotonicity — **CONFIRMED** (validation exists, ValueError on violation)
- Duplicate detection behavior — **CONFIRMED** (validation exists, HTTP 409 on duplicate)
- Replay handling — **CONFIRMED** (duplicate detection, sequence monotonicity, hash chain continuity)

**Evidence Required:**
- File paths: `services/ingest/app/main.py:401-409,411-415,443-456,604-630,677-692`, `common/integrity/verification.py:76-105`
- Validation functions: `validate_hash_integrity()`, `verify_sequence_monotonicity()`, `check_duplicate()`, `verify_hash_chain_continuity()`
- Error handling: HTTP 400/409 on violations, ValueError on sequence violations

---

## 4. DATABASE WRITE SEMANTICS

### Evidence

**DB Writes Are Transactional:**
- ✅ Explicit transactions: `services/ingest/app/main.py:517-530` — Uses `execute_write_operation()` with explicit transaction management
- ✅ Transaction management: `common/db/safety.py:280-318` — `execute_write_operation()` manages transactions
- ✅ Transaction begin: `services/ingest/app/main.py:523` — `begin_transaction(conn, logger)` (fallback path)
- ✅ Transaction commit: `services/ingest/app/main.py:526` — `commit_transaction(conn, logger, "store_event")` (fallback path)
- ✅ Transaction rollback: `services/ingest/app/main.py:528` — `rollback_transaction(conn, logger, "store_event")` (fallback path)

**Partial Writes Cannot Occur:**
- ✅ Atomic transactions: `services/ingest/app/main.py:517-530` — All writes within single transaction
- ✅ All-or-nothing: `services/ingest/app/main.py:464-508` — All INSERT statements within `_do_store_event()` function (single transaction)
- ✅ Rollback on failure: `services/ingest/app/main.py:528` — `rollback_transaction()` on exception
- ✅ No partial commits: Transaction ensures atomicity (all writes succeed or all fail)

**Failed Writes Cause Rollback:**
- ✅ Rollback on exception: `services/ingest/app/main.py:528` — `rollback_transaction(conn, logger, "store_event")` on exception
- ✅ Rollback in error handler: `services/ingest/app/main.py:733-734` — `conn.rollback()` in exception handler
- ✅ No commit on failure: Transaction rollback prevents partial state

**Parameterized Queries:**
- ✅ Parameterized queries used: `services/ingest/app/main.py:464-508` — All queries use `%s` placeholders
- ✅ No SQL injection risk: All values are parameterized
- ✅ Prepared statements: `services/ingest/app/main.py:464` — `cur.execute()` with parameterized values

**Deadlock/Integrity Violation Detection:**
- ✅ Deadlock detection: `common/db/safety.py:75-97` — `_detect_and_fail_on_db_error()` detects deadlocks
- ✅ Deadlock termination: `common/db/safety.py:80-84` — Calls `exit_fatal()` on deadlock
- ✅ Integrity violation detection: `common/db/safety.py:56-72` — `_is_integrity_violation()` detects violations
- ✅ Integrity violation termination: `common/db/safety.py:92-96` — Calls `exit_fatal()` on integrity violation

### Verdict: **PASS**

**Justification:**
- DB writes are transactional (explicit transaction management)
- Partial writes cannot occur (atomic transactions, all-or-nothing)
- Failed writes cause rollback (rollback on exception)
- Parameterized queries prevent SQL injection
- Deadlock/integrity violation detection and termination

**PASS Conditions (Met):**
- DB writes are transactional — **CONFIRMED** (explicit transaction management)
- Partial writes cannot occur — **CONFIRMED** (atomic transactions)
- Failed writes cause rollback — **CONFIRMED** (rollback on exception)

**Evidence Required:**
- File paths: `services/ingest/app/main.py:517-530,464-508,733-734`, `common/db/safety.py:280-318,75-97`
- Transaction code: `execute_write_operation()`, `begin_transaction()`, `commit_transaction()`, `rollback_transaction()`
- Error handling: Rollback on exception, deadlock/integrity violation detection

---

## 5. CREDENTIAL USAGE AT DB LAYER

### Evidence

**DB Credentials Used Are Explicit:**
- ✅ Credentials loaded from environment: `services/ingest/app/main.py:91` — `config_loader.require('RANSOMEYE_DB_PASSWORD')`
- ✅ Credentials retrieved explicitly: `services/ingest/app/main.py:137` — `db_password = config_loader.get_secret('RANSOMEYE_DB_PASSWORD')`
- ✅ Credentials used explicitly: `services/ingest/app/main.py:147` — `password=db_password` (explicit parameter)
- ✅ No hardcoded credentials: No hardcoded passwords found in ingest service code

**No Fallback Credentials Exist:**
- ✅ No fallback credentials: `services/ingest/app/main.py:91` — `config_loader.require()` (required, no default)
- ✅ No default password: `services/ingest/app/main.py:91` — No default value for `RANSOMEYE_DB_PASSWORD`
- ✅ Missing credentials cause failure: `services/ingest/app/main.py:109-110` — `ConfigError` causes `exit_config_error()` (fail-fast)

**Missing Credentials Block Writes:**
- ✅ Missing credentials block startup: `services/ingest/app/main.py:109-110` — `ConfigError` causes `exit_config_error()` (service cannot start)
- ✅ Missing credentials block DB connection: `services/ingest/app/main.py:129-173` — `_init_db_pool()` requires password (cannot create pool without password)
- ✅ No writes without credentials: Service cannot start without credentials (fail-fast)

**Shared Superuser Logic:**
- ✅ No shared superuser logic: Each service uses its own credentials from environment
- ✅ Credentials are service-specific: `services/ingest/app/main.py:91` — Ingest service uses `RANSOMEYE_DB_PASSWORD`
- ⚠️ **ISSUE:** All services may use same password (shared credential, but not "superuser logic")

**DB Writes Succeed Without Credentials:**
- ❌ **CONFIRMED:** DB writes do NOT succeed without credentials: `services/ingest/app/main.py:109-110` — Service cannot start without credentials
- ✅ Credentials required at startup: `services/ingest/app/main.py:91` — `config_loader.require()` (required)

### Verdict: **PASS**

**Justification:**
- DB credentials used are explicit (loaded from environment, retrieved via `get_secret()`)
- No fallback credentials exist (required, no default)
- Missing credentials block writes (service cannot start without credentials)
- No shared superuser logic (each service uses its own credentials)

**PASS Conditions (Met):**
- DB credentials used are explicit — **CONFIRMED** (loaded from environment, explicit retrieval)
- No fallback credentials exist — **CONFIRMED** (required, no default)
- Missing credentials block writes — **CONFIRMED** (service cannot start without credentials)

**Evidence Required:**
- File paths: `services/ingest/app/main.py:91,109-110,137,147,129-173`
- Credential code: `config_loader.require('RANSOMEYE_DB_PASSWORD')`, `config_loader.get_secret()`, `_init_db_pool()`
- Error handling: `ConfigError` causes `exit_config_error()` (fail-fast)

---

## 6. FAIL-CLOSED GUARANTEES

### Evidence

**Any Ingest/Normalize/Write Failure Stops Processing:**
- ✅ Schema validation failure stops processing: `services/ingest/app/main.py:571-602` — Returns HTTP 400 BAD REQUEST (stops processing)
- ✅ Hash integrity failure stops processing: `services/ingest/app/main.py:604-630` — Returns HTTP 400 BAD REQUEST (stops processing)
- ✅ Timestamp validation failure stops processing: `services/ingest/app/main.py:636-667` — Returns HTTP 400 BAD REQUEST (stops processing)
- ✅ Duplicate detection failure stops processing: `services/ingest/app/main.py:677-692` — Returns HTTP 409 CONFLICT (stops processing)
- ✅ Integrity violation stops processing: `services/ingest/app/main.py:703-722` — Returns HTTP 400 BAD REQUEST (stops processing)
- ✅ Database write failure stops processing: `services/ingest/app/main.py:732-746` — Returns HTTP 500 INTERNAL ERROR (stops processing)

**No "Best Effort" or "Continue on Error" Logic:**
- ✅ No best-effort logic: All validation failures cause HTTP exception (no "try to process anyway")
- ✅ No continue-on-error logic: All failures cause immediate rejection (no "log and continue")
- ✅ No fallback processing: No fallback paths found in ingest service
- ✅ Failures cause immediate termination: HTTP exceptions terminate request processing

**Silent Data Loss:**
- ❌ **CONFIRMED:** No silent data loss: All failures are logged and cause HTTP exception (not silent)
- ✅ All failures are logged: `services/ingest/app/main.py:590,618,655,687,706` — Logs all validation failures
- ✅ All failures cause HTTP exception: HTTP 400/409/500 on failures (not silent)

**Non-Deterministic Writes:**
- ❌ **CONFIRMED:** Writes are NOT non-deterministic: Database writes use deterministic field order and values
- ⚠️ **ISSUE:** `ingested_at` is non-deterministic (uses `datetime.now()`), but this is intentional (ingestion timestamp)
- ✅ Field ordering is deterministic: `services/ingest/app/main.py:464-508` — Explicit field order in INSERT statements

**Error Handling:**
- ✅ Explicit error handling: All validation failures have explicit error handling (HTTP exceptions)
- ✅ Error logging: All failures are logged before rejection
- ✅ No silent failures: All failures cause HTTP exception (not silent)

### Verdict: **PASS**

**Justification:**
- Any ingest/normalize/write failure stops processing (HTTP exceptions terminate request)
- No "best effort" or "continue on error" logic (all failures cause immediate rejection)
- No silent data loss (all failures are logged and cause HTTP exception)
- Writes are deterministic (field ordering and values are deterministic, except `ingested_at` which is intentionally time-based)

**PASS Conditions (Met):**
- Any ingest/normalize/write failure stops processing — **CONFIRMED** (HTTP exceptions terminate request)
- No "best effort" or "continue on error" logic — **CONFIRMED** (all failures cause immediate rejection)

**Evidence Required:**
- File paths: `services/ingest/app/main.py:571-602,604-630,636-667,677-692,703-722,732-746`
- Error handling: HTTP 400/409/500 on failures, no "best effort" or "continue on error" logic
- Logging: All failures are logged before rejection

---

## CREDENTIAL TYPES VALIDATED

### Database Credentials
- **Type:** PostgreSQL password (`RANSOMEYE_DB_PASSWORD`)
- **Source:** Environment variable (required, no default)
- **Validation:** ✅ **VALIDATED** (required at startup, fail-fast on missing)
- **Usage:** Explicit retrieval via `config_loader.get_secret()`, used in database connection pool
- **Status:** ✅ **PASS** (explicit, no fallback, missing credentials block writes)

---

## PASS CONDITIONS

### Section 1: Ingest Entry Validation
- ✅ Event envelope validation is mandatory — **PASS**
- ✅ Schema enforcement blocks malformed events — **PASS**
- ✅ Missing required fields cause rejection — **PASS**

### Section 2: Normalization Determinism
- ❌ Same raw event → same normalized output — **FAIL** (no normalization in ingest, `ingested_at` is non-deterministic)
- ❌ Field ordering, timestamps, IDs are deterministic — **FAIL** (`ingested_at` uses `datetime.now()`, SQL `NOW()`)
- ❌ No environment- or time-based mutation — **FAIL** (`ingested_at` is time-based)

### Section 3: Integrity & Sequence Guarantees
- ✅ Hash integrity checks — **PASS**
- ✅ Sequence monotonicity — **PASS**
- ✅ Duplicate detection behavior — **PASS**
- ✅ Replay handling — **PASS**

### Section 4: Database Write Semantics
- ✅ DB writes are transactional — **PASS**
- ✅ Partial writes cannot occur — **PASS**
- ✅ Failed writes cause rollback — **PASS**

### Section 5: Credential Usage at DB Layer
- ✅ DB credentials used are explicit — **PASS**
- ✅ No fallback credentials exist — **PASS**
- ✅ Missing credentials block writes — **PASS**

### Section 6: Fail-Closed Guarantees
- ✅ Any ingest/normalize/write failure stops processing — **PASS**
- ✅ No "best effort" or "continue on error" logic — **PASS**

---

## FAIL CONDITIONS

### Section 1: Ingest Entry Validation
- ❌ Any malformed event reaches normalization — **NOT CONFIRMED** (schema validation blocks malformed events)
- ❌ Validation errors are ignored or logged only — **NOT CONFIRMED** (validation errors cause HTTP 400)

### Section 2: Normalization Determinism
- ❌ **CONFIRMED:** Normalization depends on `now()` — **`ingested_at` uses `datetime.now()`, SQL `NOW()`**
- ❌ **CONFIRMED:** Random IDs are generated during normalization — **NOT CONFIRMED** (no random IDs, but timestamps are non-deterministic)

### Section 3: Integrity & Sequence Guarantees
- ❌ Sequence gaps are silently accepted — **NOT CONFIRMED** (sequence gaps cause rejection)
- ❌ Hash mismatches are logged but not blocked — **NOT CONFIRMED** (hash mismatches cause HTTP 400)

### Section 4: Database Write Semantics
- ❌ Partial or inconsistent state can be persisted — **NOT CONFIRMED** (atomic transactions prevent partial writes)
- ❌ Errors do not abort processing — **NOT CONFIRMED** (errors cause rollback and HTTP exception)

### Section 5: Credential Usage at DB Layer
- ❌ DB writes succeed without credentials — **NOT CONFIRMED** (service cannot start without credentials)
- ❌ Shared superuser logic exists — **NOT CONFIRMED** (each service uses its own credentials)

### Section 6: Fail-Closed Guarantees
- ❌ Silent data loss — **NOT CONFIRMED** (all failures are logged and cause HTTP exception)
- ❌ Non-deterministic writes — **PARTIAL** (`ingested_at` is non-deterministic, but intentional)

---

## EVIDENCE REQUIRED

### Ingest Entry Validation
- File paths: `services/ingest/app/main.py:341-353,571-602`, `contracts/event-envelope.schema.json:7-19`
- Validation code: `validate_schema()` function, `jsonschema.validate()` call
- Error handling: HTTP 400 BAD REQUEST on validation failure

### Normalization Determinism
- File paths: `services/ingest/app/main.py:633,507`, `services/ingest/README.md:50,97`
- Non-deterministic code: `datetime.now(timezone.utc)`, SQL `NOW()`
- Missing normalization: No normalization code in ingest service

### Integrity & Sequence Guarantees
- File paths: `services/ingest/app/main.py:401-409,411-415,443-456,604-630,677-692`, `common/integrity/verification.py:76-105`
- Validation functions: `validate_hash_integrity()`, `verify_sequence_monotonicity()`, `check_duplicate()`, `verify_hash_chain_continuity()`
- Error handling: HTTP 400/409 on violations, ValueError on sequence violations

### Database Write Semantics
- File paths: `services/ingest/app/main.py:517-530,464-508,733-734`, `common/db/safety.py:280-318,75-97`
- Transaction code: `execute_write_operation()`, `begin_transaction()`, `commit_transaction()`, `rollback_transaction()`
- Error handling: Rollback on exception, deadlock/integrity violation detection

### Credential Usage at DB Layer
- File paths: `services/ingest/app/main.py:91,109-110,137,147,129-173`
- Credential code: `config_loader.require('RANSOMEYE_DB_PASSWORD')`, `config_loader.get_secret()`, `_init_db_pool()`
- Error handling: `ConfigError` causes `exit_config_error()` (fail-fast)

### Fail-Closed Guarantees
- File paths: `services/ingest/app/main.py:571-602,604-630,636-667,677-692,703-722,732-746`
- Error handling: HTTP 400/409/500 on failures, no "best effort" or "continue on error" logic
- Logging: All failures are logged before rejection

---

## GA VERDICT

### Overall: **FAIL**

**Critical Blockers:**
1. **FAIL:** No normalization occurs in ingest (deferred to downstream)
   - **Impact:** Normalization determinism cannot be validated in ingest service
   - **Location:** `services/ingest/README.md:50,97` — "NO normalization: Does not write to normalized tables"
   - **Severity:** **HIGH** (normalization is deferred, but determinism requirements still apply)
   - **Master Spec Violation:** Normalization determinism requirements cannot be validated if normalization doesn't exist

2. **FAIL:** `ingested_at` is NOT deterministic (uses `datetime.now()`)
   - **Impact:** Same event ingested at different times will have different `ingested_at` values
   - **Location:** `services/ingest/app/main.py:633` — `datetime.now(timezone.utc).isoformat()`
   - **Severity:** **HIGH** (violates determinism requirements for normalization)
   - **Master Spec Violation:** Normalization must be deterministic; time-based mutation violates this

3. **FAIL:** SQL `NOW()` is NOT deterministic (uses database server time)
   - **Impact:** `event_validation_log.validation_timestamp` is non-deterministic
   - **Location:** `services/ingest/app/main.py:507` — `VALUES (%s, %s, NOW())`
   - **Severity:** **HIGH** (violates determinism requirements)
   - **Master Spec Violation:** Normalization must be deterministic; database server time is non-deterministic

**Non-Blocking Issues:**
1. Ingest entry validation is correct (schema enforcement, required fields)
2. Integrity and sequence guarantees are correct (hash integrity, sequence monotonicity, duplicate detection)
3. Database write semantics are correct (transactional, atomic, rollback on failure)
4. Credential usage is correct (explicit, no fallback, missing credentials block writes)
5. Fail-closed guarantees are correct (failures stop processing, no "best effort" logic)

**Strengths:**
1. ✅ Schema validation is present and enforced
2. ✅ Hash integrity validation is present and enforced
3. ✅ Sequence monotonicity validation is present and enforced
4. ✅ Duplicate detection is present and enforced
5. ✅ Database writes are transactional and atomic
6. ✅ Credential usage is explicit and fail-fast
7. ✅ Fail-closed behavior is correct (failures stop processing)

**Recommendations:**
1. **CRITICAL:** Implement normalization in ingest service (or document why it's deferred and validate determinism in downstream)
2. **CRITICAL:** Make `ingested_at` deterministic (use timestamp from envelope, not `datetime.now()`)
3. **CRITICAL:** Make SQL `NOW()` deterministic (use explicit timestamp parameter, not `NOW()`)
4. **HIGH:** Document normalization determinism requirements for downstream components
5. **MEDIUM:** Consider adding cryptographic nonces to event envelopes for replay protection

---

**Validation Date:** 2025-01-13  
**Validator:** Independent System Validator  
**Next Step:** Validation Step 5 — Correlation Engine  
**GA Status:** **BLOCKED** (Critical failures in normalization determinism)
