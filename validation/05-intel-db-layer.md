# Validation Step 5 — Database Layer & Intelligence Storage Validation

**Component Identity:**
- **Database Engine:** PostgreSQL 14+ (compatible)
- **Schema Location:** `/home/ransomeye/rebuild/schemas/`
- **Schema Authority:** `schemas/SCHEMA_BUNDLE.md` — FROZEN schema bundle v1.0.0
- **Database Access Utilities:** `/home/ransomeye/rebuild/common/db/safety.py`

**Master Spec References:**
- Phase 2 — Database First (Schema Bundle)
- Phase 10.1 — Core Runtime Hardening (database layer hardening)
- Schema Bundle (`schemas/SCHEMA_BUNDLE.md`)
- Data Plane Hardening (`schemas/DATA_PLANE_HARDENING.md`)
- Master specification: Database layer correctness requirements
- Master specification: Intelligence storage determinism requirements

---

## PURPOSE

This validation proves that the database layer enforces correctness, separation, credential safety, and determinism for intelligence data.

This file validates the storage substrate, not ingest or correlation logic. This validation focuses on:
- Schema correctness and integrity (foreign keys, referential integrity)
- Credential scoping and least privilege (per-service users, write restrictions)
- Determinism at storage layer (deterministic primary keys, no time-based defaults)
- Transactional guarantees (atomic multi-table writes, rollback behavior)
- Replayability and rebuild capability (intelligence can be rebuilt from raw_events)
- Fail-closed behavior (DB errors block processing)

This validation does NOT validate correlation engine logic, AI/ML, UI, or agents.

---

## DATABASE LAYER DEFINITION

**Database Layer Requirements (Master Spec):**

1. **Schema Correctness & Integrity** — Tables exist as defined, foreign keys are enforced, referential integrity is guaranteed, no orphaned records possible
2. **Credential Scoping & Least Privilege** — Per-service DB users exist, services cannot write to tables they do not own, read/write separation exists where required
3. **Determinism at Storage Layer** — Deterministic primary keys (where required), no time-based default values that affect reproducibility, no DB-side randomness
4. **Transactional Guarantees** — Multi-table writes are atomic, partial writes cannot persist, rollback behavior is correct
5. **Replayability & Rebuild Capability** — Intelligence can be rebuilt from raw_events, no hidden state exists only in memory, deterministic reprocessing is possible
6. **Fail-Closed Behavior** — DB errors block processing, no "continue on error" logic exists

**Database Schema Structure:**
- **Core Identity:** `machines`, `component_instances`, `component_identity_history`
- **Raw Events:** `raw_events`, `event_validation_log`, `sequence_gaps`
- **Normalized Agent:** `process_activity`, `file_activity`, `persistence`, `network_intent`, `health_heartbeat`
- **Normalized DPI:** `dpi_flows`, `dns`, `deception`
- **Correlation:** `incidents`, `incident_stages`, `evidence`, `evidence_correlation_patterns`
- **AI Metadata:** `ai_model_versions`, `feature_vectors`, `clusters`, `cluster_memberships`, `novelty_scores`, `shap_explanations`

---

## WHAT IS VALIDATED

### 1. Schema Correctness & Integrity
- Tables exist as defined in Master Spec
- Foreign keys are enforced
- Referential integrity is guaranteed
- No orphaned records possible

### 2. Credential Scoping & Least Privilege
- Per-service DB users exist
- Services cannot write to tables they do not own
- Read/write separation exists where required

### 3. Determinism at Storage Layer
- Deterministic primary keys (where required)
- No time-based default values that affect reproducibility
- No DB-side randomness

### 4. Transactional Guarantees
- Multi-table writes are atomic
- Partial writes cannot persist
- Rollback behavior is correct

### 5. Replayability & Rebuild Capability
- Intelligence can be rebuilt from raw_events
- No hidden state exists only in memory
- Deterministic reprocessing is possible

### 6. Fail-Closed Behavior
- DB errors block processing
- No "continue on error" logic exists

---

## WHAT IS EXPLICITLY NOT ASSUMED

- **NOT ASSUMED:** That credential scoping is implemented (schema file exists but is disabled)
- **NOT ASSUMED:** That `created_at` timestamps are deterministic (they use `NOW()`)
- **NOT ASSUMED:** That BIGSERIAL IDs are deterministic (auto-increment is non-deterministic)
- **NOT ASSUMED:** That intelligence can be rebuilt deterministically (NOW() timestamps are non-deterministic)
- **NOT ASSUMED:** That services cannot write to tables they do not own (no enforcement mechanism)

---

## VALIDATION METHODOLOGY

### Evidence Collection Strategy

1. **Schema Analysis:** Examine SQL schema files for foreign keys, constraints, defaults
2. **Credential Analysis:** Check for role-based access control, GRANT/REVOKE statements
3. **Determinism Analysis:** Search for `NOW()`, `random()`, `uuid_generate()`, `DEFAULT` in schemas
4. **Transaction Analysis:** Check for transaction usage, rollback behavior
5. **Replayability Analysis:** Check if all intelligence tables have foreign keys to `raw_events`
6. **Error Handling Analysis:** Check for fail-closed behavior, no "continue on error" logic

### Forbidden Patterns (Grep Validation)

- `NOW\(\)|random\(\)|uuid_generate|gen_random_uuid` — Non-deterministic defaults (forbidden in intelligence tables)
- `ON DELETE CASCADE|ON DELETE SET NULL` — Soft integrity (forbidden, must use RESTRICT)
- `GRANT.*TO PUBLIC|REVOKE.*FROM PUBLIC` — Public access (forbidden)

---

## 1. SCHEMA CORRECTNESS & INTEGRITY

### Evidence

**Tables Exist as Defined in Master Spec:**
- ✅ Authoritative schemas exist: `schemas/` directory contains SQL files
- ✅ Schema bundle is FROZEN: `schemas/SCHEMA_BUNDLE.md:182-186` — "FROZEN AS OF: 2026-01-12"
- ✅ Schema version: `schemas/SCHEMA_BUNDLE.md:11` — Version `1.0.0`
- ✅ Required tables exist: `00_core_identity.sql`, `01_raw_events.sql`, `02_normalized_agent.sql`, `03_normalized_dpi.sql`, `04_correlation.sql`, `05_ai_metadata.sql`
- ✅ Schema validation at startup: `core/runtime.py:161-208` — `_validate_schema_presence()` checks for required tables

**Foreign Keys Are Enforced:**
- ✅ Foreign keys exist: All normalized/correlation/AI tables have foreign keys to `raw_events`
- ✅ Foreign key enforcement: `schemas/01_raw_events.sql:30` — `REFERENCES machines(machine_id) ON DELETE RESTRICT`
- ✅ Foreign key enforcement: `schemas/04_correlation.sql:45` — `REFERENCES machines(machine_id) ON DELETE RESTRICT`
- ✅ Foreign key enforcement: `schemas/04_correlation.sql:189` — `REFERENCES raw_events(event_id) ON DELETE RESTRICT`
- ✅ Foreign key enforcement: `schemas/05_ai_metadata.sql:88` — `REFERENCES raw_events(event_id) ON DELETE RESTRICT`
- ✅ All foreign keys use `ON DELETE RESTRICT`: No `CASCADE` or `SET NULL` found

**Referential Integrity Is Guaranteed:**
- ✅ Referential integrity enforced: All foreign keys use `ON DELETE RESTRICT` (prevents deletion of referenced rows)
- ✅ No orphaned records possible: `ON DELETE RESTRICT` prevents deletion of parent rows with child references
- ✅ Foreign key constraints: All foreign keys are enforced at database level (not application-level)

**No Orphaned Records Possible:**
- ✅ `ON DELETE RESTRICT` prevents orphaned records: Cannot delete parent row if child rows exist
- ✅ All normalized tables reference `raw_events`: `schemas/02_normalized_agent.sql:53` — `REFERENCES raw_events(event_id) ON DELETE RESTRICT`
- ✅ All correlation tables reference `raw_events`: `schemas/04_correlation.sql:189` — `REFERENCES raw_events(event_id) ON DELETE RESTRICT`
- ✅ All AI metadata tables reference `raw_events`: `schemas/05_ai_metadata.sql:88` — `REFERENCES raw_events(event_id) ON DELETE RESTRICT`

**FK Constraints Missing:**
- ❌ **CONFIRMED:** FK constraints are NOT missing: All foreign keys are defined with `ON DELETE RESTRICT`
- ✅ Foreign keys are present: All normalized/correlation/AI tables have foreign keys

**Soft Integrity Is Relied Upon:**
- ❌ **CONFIRMED:** Soft integrity is NOT relied upon: All foreign keys use `ON DELETE RESTRICT` (hard integrity)
- ✅ No `ON DELETE CASCADE` or `ON DELETE SET NULL` found: All foreign keys use `RESTRICT`

### Verdict: **PASS**

**Justification:**
- Tables exist as defined in Master Spec (authoritative schemas, FROZEN)
- Foreign keys are enforced (all foreign keys use `ON DELETE RESTRICT`)
- Referential integrity is guaranteed (database-level enforcement)
- No orphaned records possible (`ON DELETE RESTRICT` prevents deletion of parent rows)

**PASS Conditions (Met):**
- Tables exist as defined in Master Spec — **CONFIRMED** (authoritative schemas, FROZEN)
- Foreign keys are enforced — **CONFIRMED** (all foreign keys use `ON DELETE RESTRICT`)
- Referential integrity is guaranteed — **CONFIRMED** (database-level enforcement)
- No orphaned records possible — **CONFIRMED** (`ON DELETE RESTRICT`)

**Evidence Required:**
- File paths: `schemas/SCHEMA_BUNDLE.md:182-186`, `schemas/01_raw_events.sql:30`, `schemas/04_correlation.sql:45,189`, `schemas/05_ai_metadata.sql:88`
- Foreign key definitions: All foreign keys use `ON DELETE RESTRICT`
- Schema validation: `core/runtime.py:161-208` — `_validate_schema_presence()`

---

## 2. CREDENTIAL SCOPING & LEAST PRIVILEGE

### Evidence

**Per-Service DB Users Exist:**
- ❌ **CRITICAL FAILURE:** Per-service DB users do NOT exist:
  - `schemas/08_db_users_roles.sql:5-7` — "PHASE A2 REVERTED: v1.0 GA uses single DB user per credential constraint"
  - `schemas/08_db_users_roles.sql:6` — "This schema is DISABLED for v1.0 GA - all services use gagan/gagan"
  - `schemas/08_db_users_roles.sql:7` — "DO NOT EXECUTE THIS SCHEMA IN v1.0 GA"
- ❌ **CRITICAL FAILURE:** All services use same DB user: `services/ingest/app/main.py:95` — `RANSOMEYE_DB_USER` default: `'gagan'`
- ❌ **CRITICAL FAILURE:** All services use same password: `RANSOMEYE_DB_PASSWORD` (shared secret)

**Services Cannot Write to Tables They Do Not Own:**
- ❌ **CRITICAL FAILURE:** No enforcement mechanism exists:
  - `schemas/08_db_users_roles.sql` is disabled (not executed)
  - No GRANT/REVOKE statements executed
  - All services use same user `gagan` with full access
- ⚠️ **ISSUE:** Services write to correct tables (by convention), but no enforcement mechanism exists

**Read/Write Separation Exists Where Required:**
- ❌ **CRITICAL FAILURE:** Read/write separation does NOT exist:
  - `schemas/08_db_users_roles.sql` is disabled (not executed)
  - No role-based access control implemented
  - All services use same user `gagan` with full access
- ⚠️ **ISSUE:** Policy Engine uses read-only connection in code: `services/policy-engine/app/db.py:36-64` — `create_readonly_connection()`
- ⚠️ **ISSUE:** UI backend uses write connection: `services/ui/backend/main.py:114-176` — `_init_db_pool()` creates write connection pool

**Shared Superuser Logic Exists:**
- ❌ **CRITICAL FAILURE:** Shared superuser logic exists:
  - All services use same user `gagan` (not superuser, but shared)
  - No role separation implemented
  - No GRANT/REVOKE statements executed

**Any Service Has Unnecessary Privileges:**
- ❌ **CRITICAL FAILURE:** All services have unnecessary privileges:
  - All services use same user `gagan` with full access
  - No role-based access control implemented
  - Services can write to any table (no enforcement)

**Role-Based Access Control:**
- ❌ **CRITICAL FAILURE:** Role-based access control is NOT implemented:
  - `schemas/08_db_users_roles.sql` defines roles but is disabled
  - No GRANT/REVOKE statements executed
  - All services use same user `gagan`

### Verdict: **FAIL**

**Justification:**
- **CRITICAL FAILURE:** Per-service DB users do NOT exist (all services use same user `gagan`)
- **CRITICAL FAILURE:** Services cannot write to tables they do not own (no enforcement mechanism)
- **CRITICAL FAILURE:** Read/write separation does NOT exist (no role-based access control)
- **CRITICAL FAILURE:** Shared superuser logic exists (all services use same user `gagan`)
- **CRITICAL FAILURE:** All services have unnecessary privileges (full access to all tables)

**FAIL Conditions (Met):**
- Shared superuser logic exists — **CONFIRMED** (all services use same user `gagan`)
- Any service has unnecessary privileges — **CONFIRMED** (all services have full access)

**Evidence Required:**
- File paths: `schemas/08_db_users_roles.sql:5-7`, `services/ingest/app/main.py:95`, `services/ui/backend/main.py:114-176`
- Disabled schema: `schemas/08_db_users_roles.sql` is disabled for v1.0 GA
- Shared credentials: All services use same user `gagan` with full access

---

## 3. DETERMINISM AT STORAGE LAYER

### Evidence

**Deterministic Primary Keys (Where Required):**
- ✅ Primary keys are deterministic: Most primary keys are UUIDs from application (deterministic if provided)
- ✅ Primary keys are deterministic: `schemas/01_raw_events.sql:26` — `event_id UUID NOT NULL PRIMARY KEY` (from envelope)
- ✅ Primary keys are deterministic: `schemas/04_correlation.sql:42` — `incident_id UUID NOT NULL PRIMARY KEY` (from application)
- ⚠️ **ISSUE:** Some primary keys use BIGSERIAL: `schemas/04_correlation.sql:128` — `id BIGSERIAL NOT NULL PRIMARY KEY` (auto-increment, non-deterministic)
- ⚠️ **ISSUE:** BIGSERIAL is non-deterministic: Auto-increment depends on insertion order (not deterministic)

**No Time-Based Default Values That Affect Reproducibility:**
- ❌ **CRITICAL FAILURE:** Time-based defaults exist: `schemas/01_raw_events.sql:89` — `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- ❌ **CRITICAL FAILURE:** Time-based defaults exist: `schemas/04_correlation.sql:98` — `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- ❌ **CRITICAL FAILURE:** Time-based defaults exist: `schemas/05_ai_metadata.sql:64` — `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- ⚠️ **ISSUE:** `created_at` timestamps are non-deterministic (use `NOW()` which is database server time)

**No DB-Side Randomness:**
- ✅ No `random()` found: No `random()` function calls in schemas
- ✅ No `uuid_generate()` found: No `uuid_generate()` function calls in schemas
- ✅ No `gen_random_uuid()` found: No `gen_random_uuid()` function calls in schemas
- ✅ Primary keys are from application: Most primary keys are UUIDs from application (not generated by database)

**NOW(), random(), or Implicit Defaults Are Used in Intelligence Tables:**
- ❌ **CONFIRMED:** `NOW()` is used in intelligence tables: `schemas/04_correlation.sql:98` — `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- ❌ **CONFIRMED:** `NOW()` is used in intelligence tables: `schemas/05_ai_metadata.sql:64` — `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- ❌ **CONFIRMED:** `NOW()` is used in intelligence tables: `schemas/04_correlation.sql:141` — `transitioned_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- ✅ No `random()` or `uuid_generate()` found: No randomness in schemas

### Verdict: **FAIL**

**Justification:**
- **CRITICAL FAILURE:** Time-based defaults exist (`NOW()` used in `created_at` columns)
- **CRITICAL FAILURE:** `NOW()` is used in intelligence tables (non-deterministic)
- **ISSUE:** BIGSERIAL is non-deterministic (auto-increment depends on insertion order)
- Primary keys are mostly deterministic (UUIDs from application), but `created_at` timestamps are non-deterministic

**FAIL Conditions (Met):**
- NOW(), random(), or implicit defaults are used in intelligence tables — **CONFIRMED** (`NOW()` used in `created_at` columns)

**Evidence Required:**
- File paths: `schemas/01_raw_events.sql:89`, `schemas/04_correlation.sql:98,141`, `schemas/05_ai_metadata.sql:64`
- Non-deterministic defaults: `NOW()` used in `created_at` columns
- BIGSERIAL usage: Auto-increment IDs are non-deterministic

---

## 4. TRANSACTIONAL GUARANTEES

### Evidence

**Multi-Table Writes Are Atomic:**
- ✅ Transactions are used: `common/db/safety.py:280-318` — `execute_write_operation()` uses explicit transactions
- ✅ Explicit transaction begin: `common/db/safety.py:301` — `begin_transaction()` called
- ✅ Explicit transaction commit: `common/db/safety.py:308` — `commit_transaction()` called
- ✅ Explicit transaction rollback: `common/db/safety.py:316` — `rollback_transaction()` called on failure
- ✅ Multi-table writes are atomic: `services/ingest/app/main.py:464-508` — All INSERT statements within single transaction

**Partial Writes Cannot Persist:**
- ✅ Partial writes cannot persist: Transactions ensure atomicity (all writes succeed or all fail)
- ✅ Rollback on failure: `common/db/safety.py:316` — `rollback_transaction()` called on exception
- ✅ No partial commits: Transaction ensures atomicity

**Rollback Behavior Is Correct:**
- ✅ Rollback on exception: `common/db/safety.py:311-318` — Exception causes rollback
- ✅ Rollback in error handler: `services/ingest/app/main.py:733-734` — `conn.rollback()` in exception handler
- ✅ No commit on failure: Transaction rollback prevents partial state

**Isolation Level:**
- ✅ Isolation level is explicit: `common/db/safety.py:22-26` — `IsolationLevel` enum defines levels
- ✅ Default isolation level: `common/db/safety.py:147` — `IsolationLevel.READ_COMMITTED` (default)
- ✅ Isolation level is set: `common/db/safety.py:161` — `conn.set_isolation_level(isolation_level)`

**Deadlock/Serialization Failure Detection:**
- ✅ Deadlock detection: `common/db/safety.py:38-44` — `_is_deadlock_error()` detects deadlocks
- ✅ Deadlock termination: `common/db/safety.py:80-84` — `exit_fatal()` on deadlock
- ✅ Serialization failure detection: `common/db/safety.py:47-53` — `_is_serialization_error()` detects serialization failures
- ✅ Serialization failure termination: `common/db/safety.py:86-90` — `exit_fatal()` on serialization failure

### Verdict: **PASS**

**Justification:**
- Multi-table writes are atomic (transactions ensure atomicity)
- Partial writes cannot persist (rollback on failure)
- Rollback behavior is correct (explicit rollback on exception)
- Isolation level is explicit (READ_COMMITTED)
- Deadlock/serialization failure detection and termination

**PASS Conditions (Met):**
- Multi-table writes are atomic — **CONFIRMED** (transactions ensure atomicity)
- Partial writes cannot persist — **CONFIRMED** (rollback on failure)
- Rollback behavior is correct — **CONFIRMED** (explicit rollback on exception)

**Evidence Required:**
- File paths: `common/db/safety.py:280-318,38-44,47-53`, `services/ingest/app/main.py:464-508,733-734`
- Transaction code: `execute_write_operation()`, `begin_transaction()`, `commit_transaction()`, `rollback_transaction()`
- Error handling: Rollback on exception, deadlock/serialization failure detection

---

## 5. REPLAYABILITY & REBUILD CAPABILITY

### Evidence

**Intelligence Can Be Rebuilt from raw_events:**
- ✅ All normalized tables reference `raw_events`: `schemas/02_normalized_agent.sql:53` — `REFERENCES raw_events(event_id) ON DELETE RESTRICT`
- ✅ All correlation tables reference `raw_events`: `schemas/04_correlation.sql:189` — `REFERENCES raw_events(event_id) ON DELETE RESTRICT`
- ✅ All AI metadata tables reference `raw_events`: `schemas/05_ai_metadata.sql:88` — `REFERENCES raw_events(event_id) ON DELETE RESTRICT`
- ✅ Foreign keys enable rebuild: All intelligence tables have foreign keys to `raw_events` (can be rebuilt from `raw_events`)

**No Hidden State Exists Only in Memory:**
- ✅ All state is in database: No in-memory state found (all state persisted to database)
- ✅ No hidden state: All intelligence state is stored in database tables
- ✅ State is queryable: All state can be queried from database

**Deterministic Reprocessing Is Possible:**
- ⚠️ **PARTIAL:** Deterministic reprocessing is possible, but:
  - `created_at` timestamps use `NOW()` (non-deterministic)
  - BIGSERIAL IDs are non-deterministic (auto-increment)
  - Reprocessing will produce different `created_at` timestamps and BIGSERIAL IDs
- ✅ Event data is deterministic: Event data from `raw_events` is deterministic (can be reprocessed)
- ⚠️ **ISSUE:** Reprocessing will produce different metadata timestamps (non-deterministic)

**Any Intelligence State Cannot Be Reconstructed:**
- ❌ **CONFIRMED:** Intelligence state CAN be reconstructed: All intelligence tables have foreign keys to `raw_events`
- ✅ Rebuild capability exists: All normalized/correlation/AI tables reference `raw_events` (can be rebuilt)

### Verdict: **PARTIAL**

**Justification:**
- Intelligence can be rebuilt from `raw_events` (all intelligence tables have foreign keys to `raw_events`)
- No hidden state exists only in memory (all state is in database)
- **ISSUE:** Deterministic reprocessing is partially possible (event data is deterministic, but `created_at` timestamps and BIGSERIAL IDs are non-deterministic)

**PASS Conditions (Met):**
- Intelligence can be rebuilt from raw_events — **CONFIRMED** (all intelligence tables have foreign keys to `raw_events`)
- No hidden state exists only in memory — **CONFIRMED** (all state is in database)

**Evidence Required:**
- File paths: `schemas/02_normalized_agent.sql:53`, `schemas/04_correlation.sql:189`, `schemas/05_ai_metadata.sql:88`
- Foreign key definitions: All intelligence tables have foreign keys to `raw_events`
- Rebuild capability: All normalized/correlation/AI tables reference `raw_events`

---

## 6. FAIL-CLOSED BEHAVIOR

### Evidence

**DB Errors Block Processing:**
- ✅ DB unavailability causes termination: `core/runtime.py:136-159` — `_validate_db_connectivity()` calls `exit_startup_error()` on connection failure
- ✅ Connection failure causes error: `services/ingest/app/main.py:198-209` — `get_db_connection()` raises `RuntimeError` on failure
- ✅ Error causes HTTP 500: `services/ingest/app/main.py:732-746` — Exception handler returns HTTP 500 INTERNAL ERROR
- ✅ No retries: `services/ingest/README.md:40` — "NO retry logic: Does not retry failed database operations"

**No "Continue on Error" Logic Exists:**
- ✅ No continue-on-error logic: All DB errors cause immediate termination or HTTP exception
- ✅ Failures cause immediate rejection: `services/ingest/app/main.py:554-557` — Returns HTTP error codes
- ✅ No fallback processing: No fallback paths found in database operations

**Deadlock/Integrity Violation Detection:**
- ✅ Deadlock detection: `common/db/safety.py:38-44` — `_is_deadlock_error()` detects deadlocks
- ✅ Deadlock termination: `common/db/safety.py:80-84` — `exit_fatal()` on deadlock
- ✅ Integrity violation detection: `common/db/safety.py:56-72` — `_is_integrity_violation()` detects violations
- ✅ Integrity violation termination: `common/db/safety.py:92-96` — `exit_fatal()` on integrity violation

**Silent Data Corruption:**
- ❌ **CONFIRMED:** No silent data corruption: All DB errors are logged and cause termination/HTTP exception
- ✅ All failures are logged: `services/ingest/app/main.py:501` — `logger.db_error()` on exception
- ✅ All failures cause HTTP exception: HTTP 500 INTERNAL ERROR on DB errors

### Verdict: **PASS**

**Justification:**
- DB errors block processing (fail-fast, no retries)
- No "continue on error" logic exists (all DB errors cause immediate termination or HTTP exception)
- Deadlock/integrity violation detection and termination
- No silent data corruption (all failures are logged and cause termination/HTTP exception)

**PASS Conditions (Met):**
- DB errors block processing — **CONFIRMED** (fail-fast, no retries)
- No "continue on error" logic exists — **CONFIRMED** (all DB errors cause immediate termination or HTTP exception)

**Evidence Required:**
- File paths: `core/runtime.py:136-159`, `services/ingest/app/main.py:198-209,732-746`, `common/db/safety.py:38-44,56-72,80-84,92-96`
- Error handling: Fail-fast, no retries, deadlock/integrity violation detection and termination
- Logging: All failures are logged before termination/HTTP exception

---

## CREDENTIAL TYPES VALIDATED

### Database Credentials
- **Type:** PostgreSQL user/password (`RANSOMEYE_DB_USER`/`RANSOMEYE_DB_PASSWORD`)
- **Source:** Environment variable (required, no default)
- **Validation:** ❌ **NOT VALIDATED** (all services use same user `gagan`, no role separation)
- **Usage:** Shared credentials across all services (no role-based access control)
- **Status:** ❌ **FAIL** (shared superuser logic, no credential scoping)

---

## PASS CONDITIONS

### Section 1: Schema Correctness & Integrity
- ✅ Tables exist as defined in Master Spec — **PASS**
- ✅ Foreign keys are enforced — **PASS**
- ✅ Referential integrity is guaranteed — **PASS**
- ✅ No orphaned records possible — **PASS**

### Section 2: Credential Scoping & Least Privilege
- ❌ Per-service DB users exist — **FAIL** (all services use same user `gagan`)
- ❌ Services cannot write to tables they do not own — **FAIL** (no enforcement mechanism)
- ❌ Read/write separation exists where required — **FAIL** (no role-based access control)

### Section 3: Determinism at Storage Layer
- ⚠️ Deterministic primary keys (where required) — **PARTIAL** (UUIDs are deterministic, BIGSERIAL is not)
- ❌ No time-based default values that affect reproducibility — **FAIL** (`NOW()` used in `created_at` columns)
- ✅ No DB-side randomness — **PASS** (no `random()`, `uuid_generate()` found)

### Section 4: Transactional Guarantees
- ✅ Multi-table writes are atomic — **PASS**
- ✅ Partial writes cannot persist — **PASS**
- ✅ Rollback behavior is correct — **PASS**

### Section 5: Replayability & Rebuild Capability
- ✅ Intelligence can be rebuilt from raw_events — **PASS**
- ✅ No hidden state exists only in memory — **PASS**
- ⚠️ Deterministic reprocessing is possible — **PARTIAL** (event data is deterministic, but `created_at` timestamps are not)

### Section 6: Fail-Closed Behavior
- ✅ DB errors block processing — **PASS**
- ✅ No "continue on error" logic exists — **PASS**

---

## FAIL CONDITIONS

### Section 1: Schema Correctness & Integrity
- ❌ FK constraints missing — **NOT CONFIRMED** (all foreign keys are defined)
- ❌ Soft integrity is relied upon — **NOT CONFIRMED** (all foreign keys use `ON DELETE RESTRICT`)

### Section 2: Credential Scoping & Least Privilege
- ❌ **CONFIRMED:** Shared superuser logic exists — **All services use same user `gagan`**
- ❌ **CONFIRMED:** Any service has unnecessary privileges — **All services have full access**

### Section 3: Determinism at Storage Layer
- ❌ **CONFIRMED:** NOW(), random(), or implicit defaults are used in intelligence tables — **`NOW()` used in `created_at` columns**

### Section 4: Transactional Guarantees
- ❌ Partial or inconsistent state can be persisted — **NOT CONFIRMED** (atomic transactions prevent partial writes)
- ❌ Errors do not abort processing — **NOT CONFIRMED** (errors cause rollback and HTTP exception)

### Section 5: Replayability & Rebuild Capability
- ❌ Any intelligence state cannot be reconstructed — **NOT CONFIRMED** (all intelligence tables have foreign keys to `raw_events`)

### Section 6: Fail-Closed Behavior
- ❌ Silent data corruption — **NOT CONFIRMED** (all failures are logged and cause termination/HTTP exception)

---

## EVIDENCE REQUIRED

### Schema Correctness & Integrity
- File paths: `schemas/SCHEMA_BUNDLE.md:182-186`, `schemas/01_raw_events.sql:30`, `schemas/04_correlation.sql:45,189`, `schemas/05_ai_metadata.sql:88`
- Foreign key definitions: All foreign keys use `ON DELETE RESTRICT`
- Schema validation: `core/runtime.py:161-208` — `_validate_schema_presence()`

### Credential Scoping & Least Privilege
- File paths: `schemas/08_db_users_roles.sql:5-7`, `services/ingest/app/main.py:95`, `services/ui/backend/main.py:114-176`
- Disabled schema: `schemas/08_db_users_roles.sql` is disabled for v1.0 GA
- Shared credentials: All services use same user `gagan` with full access

### Determinism at Storage Layer
- File paths: `schemas/01_raw_events.sql:89`, `schemas/04_correlation.sql:98,141`, `schemas/05_ai_metadata.sql:64`
- Non-deterministic defaults: `NOW()` used in `created_at` columns
- BIGSERIAL usage: Auto-increment IDs are non-deterministic

### Transactional Guarantees
- File paths: `common/db/safety.py:280-318,38-44,47-53`, `services/ingest/app/main.py:464-508,733-734`
- Transaction code: `execute_write_operation()`, `begin_transaction()`, `commit_transaction()`, `rollback_transaction()`
- Error handling: Rollback on exception, deadlock/serialization failure detection

### Replayability & Rebuild Capability
- File paths: `schemas/02_normalized_agent.sql:53`, `schemas/04_correlation.sql:189`, `schemas/05_ai_metadata.sql:88`
- Foreign key definitions: All intelligence tables have foreign keys to `raw_events`
- Rebuild capability: All normalized/correlation/AI tables reference `raw_events`

### Fail-Closed Behavior
- File paths: `core/runtime.py:136-159`, `services/ingest/app/main.py:198-209,732-746`, `common/db/safety.py:38-44,56-72,80-84,92-96`
- Error handling: Fail-fast, no retries, deadlock/integrity violation detection and termination
- Logging: All failures are logged before termination/HTTP exception

---

## GA VERDICT

### Overall: **FAIL**

**Critical Blockers:**
1. **FAIL:** Per-service DB users do NOT exist (all services use same user `gagan`)
   - **Impact:** No credential scoping, no least-privilege enforcement
   - **Location:** `schemas/08_db_users_roles.sql:5-7` — Schema is disabled for v1.0 GA
   - **Severity:** **CRITICAL** (violates Master Spec credential scoping requirements)
   - **Master Spec Violation:** Per-service DB users must exist for least-privilege enforcement

2. **FAIL:** Services cannot write to tables they do not own (no enforcement mechanism)
   - **Impact:** Services can write to any table (no database-level access control)
   - **Location:** `schemas/08_db_users_roles.sql` — Schema is disabled, no GRANT/REVOKE statements executed
   - **Severity:** **CRITICAL** (violates least-privilege requirements)
   - **Master Spec Violation:** Services must be restricted to their designated tables

3. **FAIL:** `NOW()` is used in intelligence tables (non-deterministic)
   - **Impact:** `created_at` timestamps are non-deterministic, affecting reproducibility
   - **Location:** `schemas/04_correlation.sql:98`, `schemas/05_ai_metadata.sql:64` — `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
   - **Severity:** **HIGH** (violates determinism requirements)
   - **Master Spec Violation:** No time-based default values that affect reproducibility

**Non-Blocking Issues:**
1. Schema correctness and integrity are correct (foreign keys enforced, referential integrity guaranteed)
2. Transactional guarantees are correct (atomic multi-table writes, rollback on failure)
3. Replayability and rebuild capability are correct (intelligence can be rebuilt from `raw_events`)
4. Fail-closed behavior is correct (DB errors block processing, no "continue on error" logic)

**Strengths:**
1. ✅ Foreign keys are enforced (all foreign keys use `ON DELETE RESTRICT`)
2. ✅ Referential integrity is guaranteed (database-level enforcement)
3. ✅ No orphaned records possible (`ON DELETE RESTRICT` prevents deletion of parent rows)
4. ✅ Multi-table writes are atomic (transactions ensure atomicity)
5. ✅ Intelligence can be rebuilt from `raw_events` (all intelligence tables have foreign keys to `raw_events`)
6. ✅ Fail-closed behavior is correct (DB errors block processing)

**Recommendations:**
1. **CRITICAL:** Implement role-based access control (execute `schemas/08_db_users_roles.sql`, create per-service users)
2. **CRITICAL:** Enforce write restrictions (GRANT/REVOKE statements, restrict services to their designated tables)
3. **CRITICAL:** Make `created_at` timestamps deterministic (use explicit timestamp parameter, not `NOW()`)
4. **HIGH:** Document deterministic reprocessing requirements (event data is deterministic, but metadata timestamps are not)
5. **MEDIUM:** Consider making BIGSERIAL IDs deterministic (use UUIDs instead of auto-increment)

---

**Validation Date:** 2025-01-13  
**Validator:** Independent System Validator  
**Next Step:** Validation Step 6 — Correlation Engine  
**GA Status:** **BLOCKED** (Critical failures in credential scoping and determinism)
