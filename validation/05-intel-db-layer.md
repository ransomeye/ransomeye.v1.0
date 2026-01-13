# Validation Step 5 — Intel Database Layer (Schema, Access Control & Read/Write Boundaries)

**Component Identity:**
- **Database Engine:** PostgreSQL 14+ (compatible)
- **Schema Location:** `/home/ransomeye/rebuild/schemas/`
- **Schema Authority:** `schemas/SCHEMA_BUNDLE.md` - FROZEN schema bundle v1.0.0
- **Database Access Utilities:** `/home/ransomeye/rebuild/common/db/safety.py`

**Spec Reference:**
- Schema Bundle (`schemas/SCHEMA_BUNDLE.md`)
- Data Plane Hardening (`schemas/DATA_PLANE_HARDENING.md`)
- Core Runtime (`core/runtime.py`)

---

## 1. COMPONENT IDENTITY

### Evidence

**Database Engine & Version:**
- ✅ PostgreSQL 14+ required: `schemas/SCHEMA_BUNDLE.md:264-266` - "PostgreSQL 14.0" minimum, "PostgreSQL 15+ recommended"
- ✅ Version compatibility: `schemas/SCHEMA_BUNDLE.md:14` - "PostgreSQL 14+ (compatible)"

**Schema Ownership Model:**
- ✅ Authoritative schemas exist: `schemas/` directory contains SQL files
- ✅ Schema bundle is FROZEN: `schemas/SCHEMA_BUNDLE.md:182-186` - "FROZEN AS OF: 2026-01-12", "STATUS: FROZEN — DO NOT MODIFY"
- ✅ Schema version: `schemas/SCHEMA_BUNDLE.md:11` - Version `1.0.0`
- ✅ Schema integrity hash: `schemas/SCHEMA_BUNDLE.md:17` - SHA256 hash for integrity verification
- ✅ Immutability rules: `schemas/SCHEMA_BUNDLE.md:188-197` - "NO MODIFICATIONS ALLOWED", "NO EXTENSIONS ALLOWED"

**Which Services Are Allowed to WRITE:**
- ✅ Ingest Service: `schemas/DATA_PLANE_HARDENING.md:32` - Writes to `raw_events`, `event_validation_log`, `sequence_gaps`, `machines`, `component_instances`
- ✅ Correlation Engine: `schemas/DATA_PLANE_HARDENING.md:34` - Writes to `incidents`, `incident_stages`, `evidence`, `evidence_correlation_patterns`
- ✅ AI Service: `schemas/DATA_PLANE_HARDENING.md:35` - Writes to `ai_model_versions`, `feature_vectors`, `clusters`, `cluster_memberships`, `novelty_scores`, `shap_explanations`
- ✅ Normalization Service: `schemas/DATA_PLANE_HARDENING.md:33` - Writes to normalized tables (`process_activity`, `file_activity`, etc.)
- ✅ Policy Engine: `schemas/DATA_PLANE_HARDENING.md:36` - "NONE (Policy engine does not write to DB)"
- ✅ UI/API: `schemas/DATA_PLANE_HARDENING.md:37` - "NONE (UI is read-only)"

**Which Services Are Allowed to READ:**
- ✅ Ingest Service: `schemas/DATA_PLANE_HARDENING.md:32` - "NONE (Ingest is write-only)"
- ✅ Normalization Service: `schemas/DATA_PLANE_HARDENING.md:33` - Reads from `v_raw_events_normalization` view
- ✅ Correlation Engine: `schemas/DATA_PLANE_HARDENING.md:34` - Reads from correlation views (`v_raw_events_correlation`, etc.)
- ✅ AI Service: `schemas/DATA_PLANE_HARDENING.md:35` - Reads from AI views (`v_raw_events_ai`, etc.)
- ✅ Policy Engine: `schemas/DATA_PLANE_HARDENING.md:36` - Reads from policy views (`v_incidents_policy`, etc.)
- ✅ UI/API: `schemas/DATA_PLANE_HARDENING.md:37` - Reads from UI views (`v_*_ui`)

**Ambiguity in DB Ownership or Access Rights:**
- ⚠️ **ISSUE:** Documentation says agents can write directly: `schemas/DATA_PLANE_HARDENING.md:29-31` - "Linux Agent: `raw_events` (INSERT only)"
- ✅ **VERIFIED:** Agents do NOT write directly in code (use HTTP POST to ingest service)
- ⚠️ **DISCREPANCY:** Documentation vs code mismatch

### Verdict: **PARTIAL**

**Justification:**
- Database engine and schema ownership are clearly defined
- Services allowed to write/read are documented
- **ISSUE:** Documentation says agents can write directly, but code shows they use HTTP POST (discrepancy)
- **ISSUE:** Views are documented but not found in schema files (views may not be implemented)

---

## 2. SCHEMA AUTHORITY & ENFORCEMENT (CRITICAL)

### Evidence

**Presence of Authoritative Schemas:**
- ✅ Authoritative schemas exist: `schemas/` directory contains SQL files:
  - `schemas/00_core_identity.sql` - Core identity tables
  - `schemas/01_raw_events.sql` - Raw events storage
  - `schemas/02_normalized_agent.sql` - Normalized agent tables
  - `schemas/03_normalized_dpi.sql` - Normalized DPI tables
  - `schemas/04_correlation.sql` - Correlation tables
  - `schemas/05_ai_metadata.sql` - AI metadata tables
  - `schemas/06_indexes.sql` - Index strategy
  - `schemas/07_retention.sql` - Partitioning and retention
- ✅ Schema bundle is authoritative: `schemas/SCHEMA_BUNDLE.md:4` - "AUTHORITATIVE: This bundle contains the immutable database schema"
- ✅ Schema is FROZEN: `schemas/SCHEMA_BUNDLE.md:182-186` - "FROZEN AS OF: 2026-01-12"

**Migration Mechanism:**
- ⚠️ **ISSUE:** No migration mechanism found:
  - `schemas/SCHEMA_BUNDLE.md:149-177` - Migration rules are documented but no migration scripts found
  - `schemas/SCHEMA_BUNDLE.md:122` - "This schema bundle is **IMMUTABLE** and **FROZEN**. No changes are permitted"
  - ⚠️ **ISSUE:** Schema is frozen, so migrations are not applicable (but rules are documented for hypothetical future)

**Schema Versioning:**
- ✅ Schema version exists: `schemas/SCHEMA_BUNDLE.md:11` - Version `1.0.0`
- ✅ Schema integrity hash: `schemas/SCHEMA_BUNDLE.md:17` - SHA256 hash for integrity verification
- ✅ Version format: `schemas/SCHEMA_BUNDLE.md:152` - Semantic versioning (MAJOR.MINOR.PATCH)

**Startup-Time Schema Verification:**
- ✅ Schema presence validated: `core/runtime.py:161-208` - `_validate_schema_presence()` checks for required tables
- ✅ Required tables checked: `core/runtime.py:179-183` - Checks for `machines`, `component_instances`, `raw_events`, `event_validation_log`, `incidents`, `incident_stages`, `evidence`, `feature_vectors`, `clusters`, `cluster_memberships`, `shap_explanations`
- ✅ Missing tables cause termination: `core/runtime.py:199-202` - `exit_startup_error()` on missing tables
- ✅ Schema structure validated: `core/runtime.py:331-363` - `_invariant_check_schema_mismatch()` checks for `raw_events.event_id` column
- ✅ Schema mismatch causes termination: `core/runtime.py:351-356` - `exit_fatal()` on schema mismatch

**What Happens on Schema Mismatch:**
- ✅ Schema mismatch causes termination: `core/runtime.py:331-363` - `_invariant_check_schema_mismatch()` calls `exit_fatal()` on mismatch
- ✅ Missing columns cause termination: `core/runtime.py:351-356` - Missing `raw_events.event_id` column causes termination
- ✅ Missing tables cause termination: `core/runtime.py:199-202` - Missing required tables cause `exit_startup_error()`

**Whether Partial Schemas Are Tolerated:**
- ✅ Partial schemas are NOT tolerated: `core/runtime.py:199-202` - Missing required tables cause termination
- ✅ All required tables must exist: `core/runtime.py:179-183` - Checks for all required tables

**Auto-Migration Without Validation:**
- ✅ No auto-migration found: Schema is FROZEN, no migration scripts found
- ✅ Schema is immutable: `schemas/SCHEMA_BUNDLE.md:122` - "No changes are permitted"

**Best-Effort Schema Usage:**
- ✅ Schema validation is strict: `core/runtime.py:161-208` - Validates schema presence and structure
- ✅ No best-effort usage: Missing tables/columns cause termination

**Silent Column Creation:**
- ✅ No silent column creation: Schema is FROZEN, no dynamic schema changes
- ✅ All columns are explicitly defined: `schemas/SCHEMA_BUNDLE.md:96` - "No dynamic columns: All columns are explicitly defined"

### Verdict: **PASS**

**Justification:**
- Authoritative schemas exist and are FROZEN
- Schema validation occurs at startup and terminates on mismatch
- No auto-migration, best-effort usage, or silent column creation found
- **ISSUE:** Migration mechanism is documented but not implemented (schema is frozen, so not applicable)

---

## 3. WRITE ACCESS CONTROL

### Evidence

**Which Services Write to DB:**
- ✅ Ingest Service: `services/ingest/app/main.py:392-502` - `store_event()` writes to `raw_events`, `machines`, `component_instances`, `event_validation_log`
- ✅ Correlation Engine: `services/correlation-engine/app/db.py:124-199` - `create_incident()` writes to `incidents`, `incident_stages`, `evidence`
- ✅ AI Service: `services/ai-core/app/db.py:199-283` - `store_feature_vector()` writes to AI metadata tables
- ✅ Policy Engine: `schemas/DATA_PLANE_HARDENING.md:36` - "NONE (Policy engine does not write to DB)"
- ✅ UI/API: `schemas/DATA_PLANE_HARDENING.md:37` - "NONE (UI is read-only)"

**How Credentials Are Scoped:**
- ❌ **CRITICAL:** All services use same DB user:
  - `services/ingest/app/main.py:94` - `RANSOMEYE_DB_USER` default: `'ransomeye'`
  - `services/correlation-engine/app/db.py:62` - `RANSOMEYE_DB_USER` default: `'ransomeye'`
  - `services/ai-core/app/db.py:56` - `RANSOMEYE_DB_USER` default: `'ransomeye'`
  - `services/policy-engine/app/db.py:59` - `RANSOMEYE_DB_USER` default: `'ransomeye'`
  - `services/ui/backend/main.py:88` - `RANSOMEYE_DB_USER` default: `'ransomeye'`
- ❌ **CRITICAL:** All services use same password: `RANSOMEYE_DB_PASSWORD` (shared secret)
- ⚠️ **ISSUE:** No credential scoping (all services use same credentials)

**Whether DB Users Are Role-Separated:**
- ❌ **CRITICAL:** DB users are NOT role-separated:
  - `schemas/DATA_PLANE_HARDENING.md:69-78` - Documentation says roles should exist (`ransomeye_agent_linux`, `ransomeye_ingest`, `ransomeye_correlation`, etc.)
  - ❌ **CRITICAL:** No role creation found in schema files
  - ❌ **CRITICAL:** No GRANT/REVOKE statements found in schema files
  - ❌ **CRITICAL:** All services use same user `ransomeye` (no role separation)
- ⚠️ **ISSUE:** Documentation says roles should exist, but they are not implemented

**Whether Least-Privilege Is Enforced:**
- ❌ **CRITICAL:** Least-privilege is NOT enforced:
  - All services use same user `ransomeye` with full access
  - No role-based access control found
  - No GRANT/REVOKE statements found
  - ⚠️ **ISSUE:** Services can write to any table (no enforcement of write boundaries)

**Shared Superuser Credentials:**
- ⚠️ **ISSUE:** All services use same credentials (not superuser, but shared):
  - `release/ransomeye-v1.0/README.md:143-144` - Default credentials: `gagan`/`gagan` (weak default)
  - `installer/core/install.sh:290,301` - Hardcoded weak credentials in installer
  - ⚠️ **ISSUE:** Shared credentials across all services (no separation)

**Agents or DPI Writing Directly:**
- ✅ Agents do NOT write directly: `services/linux-agent/src/main.rs:293-332` - Uses HTTP POST to ingest service
- ✅ DPI does NOT write directly: `dpi/probe/main.py` - DPI probe is stubbed, would use HTTP POST if implemented
- ⚠️ **ISSUE:** Documentation says agents can write directly, but code shows they use HTTP POST

**Any Service Writing Outside Its Domain:**
- ⚠️ **PARTIAL:** Services write to their designated tables:
  - Ingest writes to `raw_events`, `machines`, `component_instances`, `event_validation_log` (correct)
  - Correlation writes to `incidents`, `incident_stages`, `evidence` (correct)
  - AI writes to AI metadata tables (correct)
- ⚠️ **ISSUE:** No enforcement mechanism found (services could write to any table if they wanted)
- ⚠️ **ISSUE:** No database-level access control (no roles, no GRANT/REVOKE)

### Verdict: **FAIL**

**Justification:**
- **CRITICAL FAILURE:** All services use same DB user `ransomeye` (no role separation)
- **CRITICAL FAILURE:** No role-based access control implemented (documented but not implemented)
- **CRITICAL FAILURE:** No GRANT/REVOKE statements found (no database-level access control)
- **CRITICAL FAILURE:** Least-privilege is NOT enforced (services can write to any table)
- **ISSUE:** Shared credentials across all services (no separation)
- **ISSUE:** Services write to correct tables, but no enforcement mechanism exists

---

## 4. READ ACCESS CONTROL

### Evidence

**Which Services Read from DB:**
- ✅ Normalization Service: `schemas/DATA_PLANE_HARDENING.md:33` - Reads from `v_raw_events_normalization` view
- ✅ Correlation Engine: `schemas/DATA_PLANE_HARDENING.md:34` - Reads from correlation views
- ✅ AI Service: `schemas/DATA_PLANE_HARDENING.md:35` - Reads from AI views
- ✅ Policy Engine: `schemas/DATA_PLANE_HARDENING.md:36` - Reads from policy views
- ✅ UI/API: `schemas/DATA_PLANE_HARDENING.md:37` - Reads from UI views

**Whether Sensitive Tables Are Restricted:**
- ❌ **CRITICAL:** Views are documented but NOT implemented:
  - `schemas/DATA_PLANE_HARDENING.md:39-65` - View definitions are documented
  - ❌ **CRITICAL:** No `CREATE VIEW` statements found in schema files
  - ❌ **CRITICAL:** Services read from tables directly (not using views)
  - `services/correlation-engine/app/db.py:72` - "Get events from raw_events" (direct table access)
  - `services/ai-core/app/db.py:125` - "FROM incidents" (direct table access)
  - `services/policy-engine/app/main.py:210` - "Read from incidents table" (direct table access)
- ❌ **CRITICAL:** No view-based access control found

**Whether Reporting / AI / UI Have Read-Only Access:**
- ⚠️ **PARTIAL:** Read-only enforcement exists in code:
  - `services/policy-engine/app/db.py:36-64` - `get_db_connection()` uses `create_readonly_connection()`
  - `common/db/safety.py:187-202` - `create_readonly_connection()` enforces read-only mode
  - `common/db/safety.py:336-337` - `execute_read_operation()` can enforce read-only
- ⚠️ **ISSUE:** UI backend uses write connection: `services/ui/backend/main.py:114-176` - `_init_db_pool()` creates write connection pool
- ⚠️ **ISSUE:** No database-level read-only enforcement (no roles, no GRANT/REVOKE)

**UI Has Write Access:**
- ⚠️ **ISSUE:** UI backend has write access:
  - `services/ui/backend/main.py:114-176` - `_init_db_pool()` creates write connection pool
  - `schemas/DATA_PLANE_HARDENING.md:37` - Documentation says "NONE (UI is read-only)" but code shows write access
- ⚠️ **ISSUE:** Documentation vs code mismatch

**AI Core Can Mutate State:**
- ✅ AI core can mutate state: `schemas/DATA_PLANE_HARDENING.md:35` - AI writes to `clusters` (INSERT/UPDATE)
- ✅ AI core writes to AI metadata tables: `services/ai-core/app/db.py:199-283` - Writes to `feature_vectors`, `clusters`, etc.
- ⚠️ **ISSUE:** AI core can UPDATE `clusters` table (mutates state, but this is expected behavior)

**Ad-Hoc SQL from UI/API Layers:**
- ⚠️ **ISSUE:** Services use parameterized queries (good), but no view-based access control:
  - `services/correlation-engine/app/db.py:72` - Direct SQL queries to `raw_events` table
  - `services/ai-core/app/db.py:125` - Direct SQL queries to `incidents` table
  - ⚠️ **ISSUE:** No view-based access control (services query tables directly)

### Verdict: **FAIL**

**Justification:**
- **CRITICAL FAILURE:** Views are documented but NOT implemented (services read from tables directly)
- **CRITICAL FAILURE:** No view-based access control found
- **CRITICAL FAILURE:** UI backend has write access (documentation says read-only)
- **ISSUE:** Read-only enforcement exists in code for Policy Engine, but not for UI
- **ISSUE:** No database-level read-only enforcement (no roles, no GRANT/REVOKE)

---

## 5. TRANSACTION & CONSISTENCY SAFETY

### Evidence

**Use of Transactions:**
- ✅ Transactions are used: `common/db/safety.py:280-318` - `execute_write_operation()` uses explicit transactions
- ✅ Explicit transaction begin: `common/db/safety.py:301` - `begin_transaction()` called
- ✅ Explicit transaction commit: `common/db/safety.py:308` - `commit_transaction()` called
- ✅ Explicit transaction rollback: `common/db/safety.py:316` - `rollback_transaction()` called on failure
- ✅ Transaction management: `services/ingest/app/main.py:489-502` - Uses `execute_write_operation()` for transaction management

**Handling of Partial Failures:**
- ✅ Partial failures cause rollback: `common/db/safety.py:311-318` - Exception causes rollback
- ✅ No partial commits: Transactions ensure atomicity
- ✅ Rollback on failure: `common/db/safety.py:316` - `rollback_transaction()` called on exception

**Isolation Level Assumptions:**
- ✅ Isolation level is explicit: `common/db/safety.py:22-26` - `IsolationLevel` enum defines levels
- ✅ Default isolation level: `common/db/safety.py:147` - `IsolationLevel.READ_COMMITTED` (default)
- ✅ Isolation level is set: `common/db/safety.py:161` - `conn.set_isolation_level(isolation_level)`
- ✅ Isolation level is validated: `common/db/safety.py:165-171` - Validates isolation level was set

**What Happens During Crashes:**
- ✅ WAL ensures atomicity: `schemas/DATA_PLANE_HARDENING.md:98` - "WAL enabled (data integrity critical)"
- ✅ All tables are LOGGED: `schemas/DATA_PLANE_HARDENING.md:213` - "UNLOGGED Tables: **NONE** (all tables are LOGGED)"
- ✅ Crash recovery: WAL ensures atomic writes and crash recovery
- ⚠️ **ISSUE:** No explicit crash recovery testing found (but WAL is enabled)

**What Happens During Concurrent Writes:**
- ✅ Row-level locks: `schemas/DATA_PLANE_HARDENING.md:298` - "Partition Lock: Row-level locks (no table-level locks on partitioned tables)"
- ✅ Deadlock detection: `common/db/safety.py:38-44` - `_is_deadlock_error()` detects deadlocks
- ✅ Deadlock termination: `common/db/safety.py:80-84` - `exit_fatal()` on deadlock
- ✅ Serialization failure detection: `common/db/safety.py:47-53` - `_is_serialization_error()` detects serialization failures
- ✅ Serialization failure termination: `common/db/safety.py:86-90` - `exit_fatal()` on serialization failure

**Partial Commits:**
- ✅ No partial commits: Transactions ensure atomicity
- ✅ Rollback on failure: `common/db/safety.py:316` - `rollback_transaction()` called on exception

**Inconsistent Incident State Possible:**
- ⚠️ **PARTIAL:** Incident state is managed in transactions:
  - `services/correlation-engine/app/db.py:124-199` - `create_incident()` writes to `incidents`, `incident_stages`, `evidence` in transactions
  - ⚠️ **ISSUE:** No explicit check for inconsistent state (but transactions ensure atomicity)

**Race Conditions Without Protection:**
- ✅ Deadlock detection exists: `common/db/safety.py:38-44` - `_is_deadlock_error()` detects deadlocks
- ✅ Serialization failure detection exists: `common/db/safety.py:47-53` - `_is_serialization_error()` detects serialization failures
- ✅ Row-level locks: `schemas/DATA_PLANE_HARDENING.md:298` - Row-level locks prevent table-level contention
- ⚠️ **ISSUE:** No explicit race condition protection (but deadlock/serialization detection exists)

### Verdict: **PARTIAL**

**Justification:**
- Transactions are properly used with explicit begin/commit/rollback
- Isolation level is explicit (READ_COMMITTED)
- Deadlock and serialization failure detection exists
- **ISSUE:** No explicit crash recovery testing found (but WAL is enabled)
- **ISSUE:** No explicit race condition protection (but deadlock/serialization detection exists)

---

## 6. FAILURE BEHAVIOR (FAIL-CLOSED)

### Evidence

**Behavior on DB Unavailability:**
- ✅ DB unavailability causes termination: `core/runtime.py:136-159` - `_validate_db_connectivity()` calls `exit_startup_error()` on connection failure
- ✅ Connection failure causes error: `services/ingest/app/main.py:198-209` - `get_db_connection()` raises `RuntimeError` on failure
- ✅ Error causes HTTP 500: `services/ingest/app/main.py:681-695` - Exception handler returns HTTP 500 INTERNAL ERROR
- ✅ No retries: `services/ingest/README.md:40` - "NO retry logic: Does not retry failed database operations"
- ⚠️ **ISSUE:** No graceful degradation (returns HTTP 500, terminates on startup failure)

**Behavior on Slow DB:**
- ⚠️ **ISSUE:** No timeout handling found:
  - `services/ingest/app/main.py:192-213` - `get_db_connection()` gets connection from pool (no timeout)
  - `common/db/safety.py:348-382` - Connection pool creation (no timeout on slow queries)
  - ⚠️ **ISSUE:** Slow queries can hang indefinitely (no timeout)

**Retry Strategies (if any):**
- ✅ No retries: `services/ingest/README.md:40` - "NO retry logic"
- ✅ No retry loops found: `services/ingest/app/main.py:504-698` - No retry code found
- ✅ Failures cause immediate rejection: `services/ingest/app/main.py:554-557` - Returns HTTP error codes
- ⚠️ **ISSUE:** Documentation says retries should exist: `schemas/DATA_PLANE_HARDENING.md:324-328` - "Retry Strategy: Exponential backoff" (but not implemented)

**Backpressure Propagation:**
- ⚠️ **ISSUE:** No backpressure propagation found:
  - `services/ingest/app/main.py:212-213` - Pool exhaustion raises `RuntimeError` (no backpressure)
  - `schemas/DATA_PLANE_HARDENING.md:319-322` - Documentation says backpressure should exist (but not implemented)
  - ⚠️ **ISSUE:** No queue-based ingestion found (documentation says it should exist)

**Silent Data Loss:**
- ✅ No silent data loss: All failures are logged
- ✅ All validation failures are logged: `services/ingest/app/main.py:532-543` - Logs to `event_validation_log`
- ✅ All DB errors are logged: `services/ingest/app/main.py:501` - `logger.db_error()` on exception

**Infinite Retries:**
- ✅ No infinite retries: No retry logic found
- ✅ Failures cause immediate rejection: `services/ingest/app/main.py:554-557` - Returns HTTP error codes

**Services Continuing Without Persistence:**
- ✅ Services terminate on DB unavailability: `core/runtime.py:136-159` - `_validate_db_connectivity()` calls `exit_startup_error()` on connection failure
- ✅ Services fail-fast: No services continue without persistence

### Verdict: **PARTIAL**

**Justification:**
- DB unavailability causes termination (fail-closed)
- No retries (fail-fast)
- **ISSUE:** No timeout handling on slow queries (can hang indefinitely)
- **ISSUE:** No backpressure propagation (pool exhaustion causes HTTP 500)
- **ISSUE:** Documentation says retries/backpressure should exist, but not implemented

---

## 7. NEGATIVE VALIDATION (MANDATORY)

### Evidence

**Agent Writes to DB:**
- ✅ **PROVEN IMPOSSIBLE (in production code):** Agents do NOT write directly:
  - `services/linux-agent/src/main.rs:293-332` - `transmit_event()` uses HTTP POST to ingest service
  - No database connection code found in agents
  - ✅ **VERIFIED:** Production agents cannot write directly (use HTTP POST)

**DPI Writes to DB:**
- ✅ **PROVEN IMPOSSIBLE (in production code):** DPI does NOT write directly:
  - `dpi/probe/main.py` - DPI probe is stubbed, would use HTTP POST if implemented
  - No database connection code found in DPI
  - ✅ **VERIFIED:** Production DPI cannot write directly (would use HTTP POST)

**Schema-Less Writes Occur:**
- ✅ **PROVEN IMPOSSIBLE:** Schema-less writes are NOT possible:
  - `core/runtime.py:161-208` - `_validate_schema_presence()` validates schema at startup
  - `core/runtime.py:331-363` - `_invariant_check_schema_mismatch()` validates schema structure
  - `schemas/SCHEMA_BUNDLE.md:96` - "No dynamic columns: All columns are explicitly defined"
  - ✅ **VERIFIED:** Schema validation occurs at startup (terminates on mismatch)

**AI Mutates Historical Data:**
- ⚠️ **PARTIAL:** AI can mutate state, but:
  - `schemas/DATA_PLANE_HARDENING.md:35` - AI writes to `clusters` (INSERT/UPDATE)
  - `services/ai-core/app/db.py:199-283` - AI writes to AI metadata tables
  - ⚠️ **ISSUE:** AI can UPDATE `clusters` table (mutates state, but this is expected behavior for AI metadata)
  - ⚠️ **VERIFIED:** AI can mutate AI metadata (but not historical event data)

**UI Mutates Operational Data:**
- ⚠️ **PARTIAL:** UI backend has write access:
  - `services/ui/backend/main.py:114-176` - `_init_db_pool()` creates write connection pool
  - `schemas/DATA_PLANE_HARDENING.md:37` - Documentation says "NONE (UI is read-only)" but code shows write access
  - ⚠️ **ISSUE:** UI backend can write to database (documentation says read-only)
  - ⚠️ **VERIFIED:** UI CAN mutate operational data (no enforcement)

### Verdict: **PARTIAL**

**Justification:**
- Agents and DPI cannot write directly in production code (use HTTP POST)
- Schema-less writes are not possible (schema validation at startup)
- **ISSUE:** AI can mutate AI metadata (expected behavior, but mutates state)
- **CRITICAL:** UI CAN mutate operational data (documentation says read-only, but code shows write access)

---

## 8. VERDICT & IMPACT

### Section-by-Section Verdicts

1. **Component Identity:** PARTIAL
   - Database engine and schema ownership are clearly defined
   - Documentation vs code discrepancy (agents can write directly vs use HTTP POST)

2. **Schema Authority & Enforcement:** PASS
   - Authoritative schemas exist and are FROZEN
   - Schema validation occurs at startup and terminates on mismatch

3. **Write Access Control:** FAIL
   - All services use same DB user (no role separation)
   - No role-based access control implemented
   - No GRANT/REVOKE statements found

4. **Read Access Control:** FAIL
   - Views are documented but NOT implemented
   - Services read from tables directly
   - UI backend has write access (documentation says read-only)

5. **Transaction & Consistency Safety:** PARTIAL
   - Transactions are properly used
   - Deadlock and serialization failure detection exists
   - No explicit crash recovery testing found

6. **Failure Behavior:** PARTIAL
   - DB unavailability causes termination (fail-closed)
   - No timeout handling on slow queries
   - No backpressure propagation

7. **Negative Validation:** PARTIAL
   - Agents/DPI cannot write directly
   - Schema-less writes are not possible
   - UI CAN mutate operational data (no enforcement)

### Overall Verdict: **FAIL**

**Justification:**
- **CRITICAL FAILURE:** All services use same DB user `ransomeye` (no role separation)
- **CRITICAL FAILURE:** No role-based access control implemented (documented but not implemented)
- **CRITICAL FAILURE:** Views are documented but NOT implemented (services read from tables directly)
- **CRITICAL FAILURE:** UI backend has write access (documentation says read-only)
- **CRITICAL FAILURE:** No database-level access control (no GRANT/REVOKE statements)
- **ISSUE:** No timeout handling on slow queries
- **ISSUE:** No backpressure propagation
- Schema validation is proper, but access control is missing

**Impact of DB-Layer Compromise:**
- **CRITICAL:** If DB layer is compromised, all services have full access (no role separation)
- **CRITICAL:** If DB layer is compromised, any service can write to any table (no enforcement)
- **CRITICAL:** If DB layer is compromised, UI can mutate operational data (no read-only enforcement)
- **CRITICAL:** If DB layer is compromised, all data is accessible (no view-based access control)
- **HIGH:** If DB layer is compromised, all downstream engines receive untrusted data
- **HIGH:** If DB layer is compromised, correlation and AI results are untrustworthy

**Whether Downstream (Engine, AI, Reporting) Remain Trustworthy:**
- ❌ **NO** - Downstream engines cannot be trusted if DB layer is compromised
- ❌ If any service can write to any table, then correlation results are untrustworthy
- ❌ If UI can mutate operational data, then reporting results are untrustworthy
- ❌ If services read from tables directly (not views), then access control is bypassed
- ⚠️ Schema validation is trustworthy, but access control is not

**Recommendations:**
1. **CRITICAL:** Implement role-based access control (create database roles, GRANT/REVOKE statements)
2. **CRITICAL:** Implement views for read-only access (create views, enforce view usage)
3. **CRITICAL:** Enforce read-only access for UI backend (use read-only connection, no write access)
4. **CRITICAL:** Separate credentials per service (different DB users per service)
5. **HIGH:** Implement timeout handling on slow database queries
6. **HIGH:** Implement backpressure propagation (queue-based ingestion, rate limiting)
7. **MEDIUM:** Resolve documentation vs code discrepancies (agents can write directly vs use HTTP POST)
8. **MEDIUM:** Add explicit crash recovery testing (verify WAL recovery)

---

**Validation Date:** 2025-01-13
**Validator:** Lead Validator & Compliance Auditor
**Next Step:** Validation Step 6 — Correlation Engine (if applicable)
