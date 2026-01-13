# Validation Step 4 — Telemetry Ingest, Normalization & DB Write Path

**Component Identity:**
- **Name:** Telemetry Ingest Service
- **Primary Paths:**
  - `/home/ransomeye/rebuild/services/ingest/app/main.py` - Main ingest service
  - `/home/ransomeye/rebuild/services/ingest/app/main_hardened.py` - Hardened variant
- **Entry Points:**
  - HTTP POST: `POST /events` - `services/ingest/app/main.py:504` - `@app.post("/events")`
  - Health check: `GET /health` - `services/ingest/app/main.py:700` - `@app.get("/health")`
- **Database Write Access:** Ingest service writes to `raw_events`, `machines`, `component_instances`, `event_validation_log`

**Spec Reference:**
- Phase 4 — Minimal Data Plane (Ingest Service)
- Event Envelope Contract (`contracts/event-envelope.schema.json`)
- Time Semantics Contract (`contracts/time-semantics.policy.json`)
- Data Plane Hardening (`schemas/DATA_PLANE_HARDENING.md`)

---

## 1. COMPONENT IDENTITY

### Evidence

**Ingest Service Name:**
- ✅ Ingest service identified: `services/ingest/app/main.py:1-5` - "RansomEye v1.0 Ingest Service"
- ✅ Service name: "ingest" - `services/ingest/app/main.py:112` - `setup_logging('ingest')`

**Entry Points:**
- ✅ HTTP POST endpoint: `services/ingest/app/main.py:504` - `@app.post("/events")`
- ✅ Health check endpoint: `services/ingest/app/main.py:700` - `@app.get("/health")`
- ❌ **NO bus subscriptions** - No message bus found (uses HTTP POST)
- ✅ FastAPI application: `services/ingest/app/main.py:280` - `app = FastAPI(...)`

**Other Components Writing to DB:**
- ⚠️ **ISSUE:** `schemas/DATA_PLANE_HARDENING.md:29-31` - Documentation says agents CAN write directly to `raw_events`:
  - "Linux Agent: `raw_events` (INSERT only)"
  - "Windows Agent: `raw_events` (INSERT only)"
  - "DPI Probe: `raw_events` (INSERT only)"
- ✅ **VERIFIED:** Agents do NOT write directly in code:
  - `services/linux-agent/src/main.rs:293-332` - `transmit_event()` uses HTTP POST to ingest service
  - `dpi/probe/main.py` - DPI probe is stubbed, would use HTTP POST if implemented
  - No database connection code found in agents
- ⚠️ **DISCREPANCY:** Documentation says agents can write directly, but code shows they use HTTP POST

**Validation Harness Bypass:**
- ⚠️ **ISSUE:** `validation/harness/track_1_determinism.py:652-688` - `ingest_event()` function writes directly to `raw_events`:
  - `validation/harness/track_1_determinism.py:662-682` - Direct INSERT into `raw_events` table
  - This is a test harness, not production code, but shows direct write is possible

### Verdict: **PARTIAL**

**Justification:**
- Ingest service is clearly identified with proper entry points
- **ISSUE:** Documentation says agents can write directly, but code shows they use HTTP POST (discrepancy)
- **ISSUE:** Test harness can write directly (bypasses ingest), but this is test code
- Production agents use HTTP POST (do not bypass ingest)

---

## 2. AUTHENTICATED TELEMETRY INPUT

### Evidence

**Telemetry Origin Verification:**
- ❌ **CRITICAL:** Ingest service does NOT verify telemetry origin:
  - `services/ingest/app/main.py:504-698` - `ingest_event()` does NOT verify origin
  - No authentication middleware found
  - No origin verification found

**Signature Verification Before Processing:**
- ❌ **CRITICAL:** Ingest service does NOT verify signatures:
  - `services/ingest/app/main.py:504-698` - `ingest_event()` does NOT verify signatures
  - `services/ingest/app/main.py:376-384` - `validate_hash_integrity()` only verifies SHA256 hash, NOT cryptographic signature
  - No signature verification code found in ingest service
- ✅ Agents sign events: `agents/windows/agent/telemetry/signer.py:85-122` - Signs with ed25519
- ❌ **CRITICAL:** Ingest does NOT verify these signatures

**Identity Binding:**
- ✅ Event envelopes include identity: `contracts/event-envelope.schema.json:61-85` - `identity` object with `hostname`, `boot_id`, `agent_version`
- ✅ Event envelopes include component: `contracts/event-envelope.schema.json:31-34` - `component` field
- ✅ Event envelopes include machine_id: `contracts/event-envelope.schema.json:26-29` - `machine_id` field
- ⚠️ **ISSUE:** Identity is NOT cryptographically bound - can be spoofed
- ⚠️ **ISSUE:** Component identity is NOT verified - can be spoofed

**Where Verification Occurs:**
- ❌ **CRITICAL:** Verification does NOT occur in ingest service
- ❌ **CRITICAL:** No signature verification before processing
- ❌ **CRITICAL:** No origin verification before processing

**What Happens if Verification Fails:**
- ❌ **CRITICAL:** Verification does NOT exist, so cannot fail
- ⚠️ Unsigned events are accepted (no verification = no failure)

### Verdict: **FAIL**

**Justification:**
- **CRITICAL FAILURE:** Ingest service does NOT verify telemetry origin
- **CRITICAL FAILURE:** Ingest service does NOT verify cryptographic signatures
- **CRITICAL FAILURE:** Identity is NOT cryptographically bound (can be spoofed)
- **CRITICAL FAILURE:** Component identity is NOT verified (can be spoofed)
- This violates authenticated telemetry input requirements

---

## 3. SCHEMA VALIDATION (CRITICAL)

### Evidence

**Presence of Strict Schemas:**
- ✅ Strict schema exists: `contracts/event-envelope.schema.json` - Event envelope schema
- ✅ Schema is loaded: `services/ingest/app/main.py:226-237` - Loads schema from file
- ✅ Schema uses jsonschema: `services/ingest/app/main.py:319` - Uses `jsonschema.validate()`

**Validation Before Normalization:**
- ✅ Schema validation occurs: `services/ingest/app/main.py:526-557` - `validate_schema()` called before storage
- ⚠️ **ISSUE:** No normalization occurs in ingest (README says "NO normalization")
- ✅ Validation order: Schema → Hash → Timestamps → Duplicate → Storage

**Rejection of Missing Required Fields:**
- ✅ Required fields enforced: `contracts/event-envelope.schema.json:7-18` - `required` array lists all required fields
- ✅ Missing fields rejected: `services/ingest/app/main.py:526-557` - Returns HTTP 400 BAD REQUEST on schema violation
- ✅ Schema validation logs failure: `services/ingest/app/main.py:532-543` - Logs to `event_validation_log`

**Rejection of Type Mismatches:**
- ✅ Type validation enforced: `contracts/event-envelope.schema.json:20-114` - Type definitions for all fields
- ✅ Type mismatches rejected: `services/ingest/app/main.py:321-328` - `jsonschema.ValidationError` raised on type mismatch
- ✅ Type validation logs failure: `services/ingest/app/main.py:532-543` - Logs to `event_validation_log`

**Rejection of Unknown Fields:**
- ✅ Unknown fields forbidden: `contracts/event-envelope.schema.json:19` - `additionalProperties: false`
- ✅ Unknown fields rejected: `services/ingest/app/main.py:319` - `jsonschema.validate()` rejects unknown fields
- ✅ Unknown fields cause schema violation: `services/ingest/app/main.py:322-326` - Returns "SCHEMA_VIOLATION" error

**Best-Effort Parsing:**
- ✅ Schema validation is strict: `services/ingest/app/main.py:316-328` - Raises `ValidationError` on failure
- ✅ No best-effort parsing: `services/ingest/app/main.py:554-557` - Rejects invalid messages
- ✅ All validation failures cause rejection: `services/ingest/app/main.py:526-622` - Multiple validation checks

**Silent Field Dropping:**
- ✅ No field dropping: Schema validation rejects messages with missing/extra fields
- ✅ All required fields must be present: `contracts/event-envelope.schema.json:7-18` - Required fields enforced

**Schema Mismatch Allowed Through:**
- ✅ Schema mismatches rejected: `services/ingest/app/main.py:526-557` - Returns HTTP 400 BAD REQUEST
- ✅ Schema validation logs failure: `services/ingest/app/main.py:532-543` - Logs to `event_validation_log`

### Verdict: **PASS**

**Justification:**
- Strict schema validation is present and enforced
- Missing required fields, type mismatches, and unknown fields are all rejected
- No best-effort parsing or silent field dropping found
- Schema validation occurs before any processing

---

## 4. NORMALIZATION LOGIC

### Evidence

**Agent vs DPI Normalization Paths:**
- ❌ **CRITICAL:** No normalization occurs in ingest service:
  - `services/ingest/README.md:50` - "NO normalization: Does not write to normalized tables"
  - `services/ingest/README.md:97` - "Does NOT write to normalized tables"
  - No normalization code found in ingest service
- ✅ Normalization exists elsewhere: `hnmp/engine/*_normalizer.py` - Normalizers exist in HNMP engine
- ⚠️ **ISSUE:** Normalization does NOT occur in ingest (happens downstream)

**Field Canonicalization:**
- ✅ Timestamps canonicalized: `services/ingest/app/main.py:330-374` - `validate_timestamps()` normalizes to UTC
- ✅ Timestamps are RFC3339: `contracts/event-envelope.schema.json:42-48` - Format validation
- ⚠️ **ISSUE:** Host IDs, IPs are NOT canonicalized in ingest (stored as-is from envelope)
- ⚠️ **ISSUE:** No canonicalization of machine_id, component_instance_id

**Explicit Mapping Rules:**
- ❌ **CRITICAL:** No mapping rules in ingest service (no normalization)
- ✅ Mapping rules exist in HNMP: `hnmp/engine/*_normalizer.py` - Normalizers have mapping rules
- ⚠️ **ISSUE:** Mapping rules are NOT in ingest (deferred to downstream)

**Handling of Malformed-but-Authenticated Events:**
- ✅ Malformed events rejected: `services/ingest/app/main.py:526-557` - Schema validation rejects malformed events
- ✅ Malformed events logged: `services/ingest/app/main.py:532-543` - Logs to `event_validation_log`
- ⚠️ **ISSUE:** "Authenticated" is not verified (no signature verification)

**Ambiguous Mappings:**
- ⚠️ **N/A:** No mappings in ingest (no normalization)
- ⚠️ **ISSUE:** No canonicalization means ambiguous host identity resolution possible

**Inconsistent Host Identity Resolution:**
- ⚠️ **ISSUE:** Host identity is NOT resolved in ingest:
  - `services/ingest/app/main.py:439-445` - `machines` table uses `machine_id` as-is from envelope
  - No host identity resolution logic found
  - Multiple `machine_id` values for same host possible

**DPI and Agent Events Treated Interchangeably:**
- ✅ Events stored in same table: `services/ingest/app/main.py:463-478` - All events go to `raw_events`
- ✅ Component field distinguishes: `contracts/event-envelope.schema.json:31-34` - `component` field (enum)
- ⚠️ **ISSUE:** No special handling for DPI vs agent events in ingest (treated the same)

### Verdict: **PARTIAL**

**Justification:**
- **CRITICAL ISSUE:** No normalization occurs in ingest service (deferred to downstream)
- Timestamps are canonicalized, but host IDs and IPs are not
- No explicit mapping rules in ingest
- Host identity resolution is inconsistent (no resolution logic)
- DPI and agent events are treated the same (no differentiation)

---

## 5. DEDUPLICATION & FLOOD PROTECTION

### Evidence

**Deduplication Keys:**
- ✅ Deduplication by event_id: `services/ingest/app/main.py:386-390` - `check_duplicate()` checks `event_id`
- ✅ event_id is UUID: `contracts/event-envelope.schema.json:21-24` - UUID v4 format
- ✅ event_id is PRIMARY KEY: `schemas/01_raw_events.sql:26` - `event_id UUID NOT NULL PRIMARY KEY`
- ⚠️ **ISSUE:** Only `event_id` is used for deduplication (no other keys)

**Time Windows:**
- ❌ **CRITICAL:** No time windows for deduplication:
  - `services/ingest/app/main.py:386-390` - `check_duplicate()` checks all-time (no time window)
  - No time-based deduplication found
  - Duplicate check is global (not time-bounded)

**Memory Bounds:**
- ❌ **CRITICAL:** No in-memory deduplication state:
  - `services/ingest/app/main.py:386-390` - `check_duplicate()` queries database (not in-memory)
  - No memory bounds needed (no in-memory state)
  - ⚠️ **ISSUE:** Database query for every event (no caching)

**Flood Handling Behavior:**
- ❌ **CRITICAL:** No flood protection found:
  - `services/ingest/app/main.py:504-698` - No rate limiting found
  - `services/ingest/app/main.py:504-698` - No throttling found
  - `services/ingest/app/main.py:504-698` - No backpressure found
  - No flood protection mechanisms found

**Unlimited In-Memory Dedupe State:**
- ✅ No in-memory dedupe state: `services/ingest/app/main.py:386-390` - Uses database query
- ✅ No memory bounds needed: No in-memory state to bound

**No Protection Against Event Storms:**
- ❌ **CRITICAL:** No protection against event storms:
  - No rate limiting
  - No throttling
  - No backpressure
  - No queue limits
  - ⚠️ **ISSUE:** Event storms can overwhelm ingest service

**DB Write Amplification Possible:**
- ⚠️ **PARTIAL:** Write amplification possible:
  - `services/ingest/app/main.py:439-483` - Writes to `machines`, `component_instances`, `raw_events`, `event_validation_log` (4 tables per event)
  - `services/ingest/app/main.py:439-445` - `machines` table uses `ON CONFLICT` (UPSERT)
  - `services/ingest/app/main.py:447-461` - `component_instances` table uses `ON CONFLICT` (UPSERT)
  - ⚠️ **ISSUE:** Multiple writes per event (write amplification)

### Verdict: **FAIL**

**Justification:**
- Deduplication exists but only by `event_id` (no time windows)
- **CRITICAL FAILURE:** No flood protection (no rate limiting, throttling, or backpressure)
- **CRITICAL FAILURE:** Event storms can overwhelm ingest service
- **ISSUE:** Write amplification (4 tables per event)
- **ISSUE:** Database query for every duplicate check (no caching)

---

## 6. DATABASE WRITE SAFETY (CRITICAL)

### Evidence

**Single DB Writer Model:**
- ✅ Ingest is single writer: `services/ingest/app/main.py:392-502` - `store_event()` is the write function
- ⚠️ **ISSUE:** Multiple components can write (agents via ingest, but also test harness can write directly)
- ⚠️ **ISSUE:** Documentation says agents can write directly, but code shows they use HTTP POST

**Use of Prepared Statements / Parameterized Queries:**
- ✅ Parameterized queries used: `services/ingest/app/main.py:439-483` - All queries use `%s` placeholders
- ✅ Prepared statements: `services/ingest/app/main.py:439` - `cur.execute()` with parameterized values
- ✅ No SQL injection risk: All values are parameterized

**Transaction Handling:**
- ✅ Explicit transactions: `services/ingest/app/main.py:489-502` - Uses `execute_write_operation()` with explicit begin/commit/rollback
- ✅ Transaction management: `common/db/safety.py:280-318` - `execute_write_operation()` manages transactions
- ✅ Rollback on failure: `services/ingest/app/main.py:499-502` - `rollback_transaction()` on exception
- ✅ Commit on success: `common/db/safety.py:308` - `commit_transaction()` on success

**Failure Behavior on DB Errors:**
- ✅ Deadlock detection: `common/db/safety.py:75-97` - `_detect_and_fail_on_db_error()` detects deadlocks
- ✅ Deadlock termination: `common/db/safety.py:80-84` - Calls `exit_fatal()` on deadlock
- ✅ Integrity violation detection: `common/db/safety.py:56-72` - `_is_integrity_violation()` detects violations
- ✅ Integrity violation termination: `common/db/safety.py:92-96` - Calls `exit_fatal()` on integrity violation
- ✅ No retries: `services/ingest/README.md:40` - "NO retry logic: Does not retry failed database operations"

**What Happens if DB is Slow:**
- ⚠️ **ISSUE:** No timeout handling found:
  - `services/ingest/app/main.py:192-213` - `get_db_connection()` gets connection from pool
  - `services/ingest/app/main.py:212-213` - Pool exhaustion raises `RuntimeError`
  - ⚠️ **ISSUE:** No timeout on slow queries (can hang indefinitely)
  - ⚠️ **ISSUE:** Pool exhaustion causes HTTP 500 (no graceful degradation)

**What Happens if DB is Unavailable:**
- ✅ Connection failure causes error: `services/ingest/app/main.py:198-209` - `get_db_connection()` raises `RuntimeError` on failure
- ✅ Error causes HTTP 500: `services/ingest/app/main.py:681-695` - Exception handler returns HTTP 500 INTERNAL ERROR
- ✅ Error is logged: `services/ingest/app/main.py:690` - Logs error
- ⚠️ **ISSUE:** No graceful degradation (returns HTTP 500)

**Partial Writes:**
- ✅ Atomic transactions: `common/db/safety.py:280-318` - `execute_write_operation()` uses transactions
- ✅ Rollback on failure: `common/db/safety.py:316` - `rollback_transaction()` on exception
- ✅ No partial writes: Transactions ensure atomicity

**Silent Drops Without Audit:**
- ✅ Drops are audited: `services/ingest/app/main.py:532-543` - Logs to `event_validation_log`
- ✅ All validation failures are logged: `services/ingest/app/main.py:526-622` - Multiple validation checks log failures
- ✅ All DB errors are logged: `services/ingest/app/main.py:501` - `logger.db_error()` on exception

**Retry Loops Without Cap:**
- ✅ No retries: `services/ingest/README.md:40` - "NO retry logic"
- ✅ No retry loops found: `services/ingest/app/main.py:504-698` - No retry code found
- ✅ Failures cause immediate rejection: `services/ingest/app/main.py:554-557` - Returns HTTP error codes

### Verdict: **PARTIAL**

**Justification:**
- Parameterized queries, transactions, and failure handling are proper
- **ISSUE:** No timeout handling on slow queries (can hang)
- **ISSUE:** No graceful degradation on DB unavailability (returns HTTP 500)
- **ISSUE:** Pool exhaustion causes HTTP 500 (no backpressure)
- No retries and proper audit logging are good

---

## 7. NEGATIVE VALIDATION (MANDATORY)

### Evidence

**Agent Writes Directly to DB:**
- ✅ **PROVEN IMPOSSIBLE (in production code):** Agents do NOT write directly:
  - `services/linux-agent/src/main.rs:293-332` - `transmit_event()` uses HTTP POST
  - No database connection code found in agents
  - ✅ **VERIFIED:** Production agents cannot write directly (use HTTP POST)
- ⚠️ **ISSUE:** Test harness can write directly: `validation/harness/track_1_determinism.py:652-688` - Direct INSERT
- ⚠️ **ISSUE:** Documentation says agents can write directly: `schemas/DATA_PLANE_HARDENING.md:29-31`

**DPI Writes Directly to DB:**
- ✅ **PROVEN IMPOSSIBLE (in production code):** DPI does NOT write directly:
  - `dpi/probe/main.py` - DPI probe is stubbed, would use HTTP POST if implemented
  - No database connection code found in DPI
  - ✅ **VERIFIED:** Production DPI cannot write directly (would use HTTP POST)

**Malformed Telemetry is Persisted:**
- ✅ **PROVEN IMPOSSIBLE:** Malformed telemetry is NOT persisted:
  - `services/ingest/app/main.py:526-557` - Schema validation rejects malformed messages
  - `services/ingest/app/main.py:554-557` - Returns HTTP 400 BAD REQUEST
  - ✅ **VERIFIED:** Malformed telemetry is rejected (not persisted)

**Duplicate Events Flood DB:**
- ⚠️ **PARTIAL:** Duplicate events are detected, but:
  - `services/ingest/app/main.py:632-647` - Duplicate `event_id` is rejected
  - ⚠️ **ISSUE:** If attacker can generate unique `event_id` for each duplicate, flooding is possible
  - ⚠️ **ISSUE:** No rate limiting prevents flooding
  - ⚠️ **VERIFIED:** Duplicate events CAN flood DB if attacker generates unique `event_id` values

**Telemetry Without Identity is Stored:**
- ✅ **PROVEN IMPOSSIBLE:** Telemetry without identity is NOT stored:
  - `contracts/event-envelope.schema.json:61-85` - `identity` object is required
  - `services/ingest/app/main.py:316-328` - Schema validation checks for required fields
  - `services/ingest/app/main.py:412-414` - Identity fields are extracted and stored
  - ✅ **VERIFIED:** Telemetry without identity is rejected (schema validation)

### Verdict: **PARTIAL**

**Justification:**
- Agents and DPI cannot write directly in production code (use HTTP POST)
- Malformed telemetry is not persisted (schema validation)
- Telemetry without identity is not stored (schema validation)
- **CRITICAL:** Duplicate events CAN flood DB if attacker generates unique `event_id` values (no rate limiting)
- **ISSUE:** Test harness can write directly (bypasses ingest)

---

## 8. VERDICT & IMPACT

### Section-by-Section Verdicts

1. **Component Identity:** PARTIAL
   - Ingest service is clearly identified, but documentation discrepancy exists

2. **Authenticated Telemetry Input:** FAIL
   - No signature verification, no origin verification, identity not cryptographically bound

3. **Schema Validation:** PASS
   - Strict schema validation is present and enforced

4. **Normalization Logic:** PARTIAL
   - No normalization in ingest (deferred to downstream), no host identity resolution

5. **Deduplication & Flood Protection:** FAIL
   - No flood protection, event storms can overwhelm service

6. **Database Write Safety:** PARTIAL
   - Proper transactions and parameterized queries, but no timeout handling or graceful degradation

7. **Negative Validation:** PARTIAL
   - Agents/DPI cannot write directly, but duplicate events can flood DB

### Overall Verdict: **FAIL**

**Justification:**
- **CRITICAL FAILURE:** Ingest service does NOT verify telemetry origin or signatures
- **CRITICAL FAILURE:** No flood protection (event storms can overwhelm service)
- **CRITICAL FAILURE:** Duplicate events can flood DB if attacker generates unique `event_id` values
- **CRITICAL FAILURE:** Identity is NOT cryptographically bound (can be spoofed)
- **ISSUE:** No normalization in ingest (deferred to downstream)
- **ISSUE:** No timeout handling on slow queries
- **ISSUE:** No graceful degradation on DB unavailability
- Schema validation is proper, but authentication/authorization are missing

**Impact if Ingest Layer is Compromised:**
- **CRITICAL:** If ingest is compromised, all telemetry can be injected (no signature verification)
- **CRITICAL:** If ingest is compromised, all identity can be spoofed (no identity verification)
- **CRITICAL:** If ingest is compromised, event storms can be injected (no flood protection)
- **CRITICAL:** If ingest is compromised, duplicate events can flood DB (no rate limiting)
- **HIGH:** If ingest is compromised, all downstream engines receive untrusted data
- **HIGH:** If ingest is compromised, correlation and AI results are untrustworthy

**Whether Correlation & AI Validations Remain Trustworthy:**
- ❌ **NO** - Correlation and AI validations cannot be trusted if ingest is compromised
- ❌ If unsigned telemetry can reach database, then correlation results are untrustworthy
- ❌ If identity can be spoofed, then all event attribution is untrustworthy
- ❌ If event storms can flood DB, then system availability is compromised
- ⚠️ Schema validation is trustworthy, but authentication/authorization are not

**Recommendations:**
1. **CRITICAL:** Implement cryptographic signature verification in ingest service
2. **CRITICAL:** Implement telemetry origin verification (who can publish what)
3. **CRITICAL:** Implement flood protection (rate limiting, throttling, backpressure)
4. **CRITICAL:** Implement component identity verification (cryptographic proof of component identity)
5. **HIGH:** Implement timeout handling on slow database queries
6. **HIGH:** Implement graceful degradation on database unavailability
7. **MEDIUM:** Consider implementing normalization in ingest (or document why it's deferred)
8. **MEDIUM:** Resolve documentation discrepancy (agents can write directly vs use HTTP POST)

---

**Validation Date:** 2025-01-13
**Validator:** Lead Validator & Compliance Auditor
**Next Step:** Validation Step 5 — Intel DB Layer (if applicable) or Validation Step 6 — Correlation Engine
