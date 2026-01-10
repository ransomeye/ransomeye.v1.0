# RansomEye v1.0 SOC UI (Phase 8 - Read-Only)

**AUTHORITATIVE**: Minimal read-only SOC UI for Phase 8 proof-of-concept.

---

## What This Component Does

This component **ONLY** implements the minimal read-only visibility required for Phase 8 validation:

1. **Read-Only Database Views** (contract compliance: Phase 8 requirements):
   - `v_active_incidents`: Active (unresolved) incidents
   - `v_incident_timeline`: Incident stage transitions (timeline)
   - `v_incident_evidence_summary`: Evidence summary per incident
   - `v_policy_recommendations`: Policy recommendations (placeholder for Phase 8 minimal)
   - `v_ai_insights`: AI insights (clusters, novelty scores, SHAP summaries)
   - `v_incident_detail`: Combined incident detail view

2. **Read-Only Backend API** (contract compliance: Phase 8 requirements):
   - `GET /api/incidents`: List active incidents (from `v_active_incidents` view)
   - `GET /api/incidents/{incident_id}`: Get incident detail (from views only)
   - `GET /api/incidents/{incident_id}/timeline`: Get incident timeline (from `v_incident_timeline` view)
   - **Read-only**: All endpoints are GET only (no POST, PUT, DELETE, PATCH)

3. **Read-Only Frontend** (contract compliance: Phase 8 requirements):
   - **Incident list**: Displays active incidents (read-only)
   - **Incident detail view**: Displays timeline, evidence count, AI insights, policy recommendations
   - **No edits**: No edit forms, no input fields, no save buttons
   - **No actions**: No "acknowledge", "resolve", or "close" buttons
   - **No action triggers**: No buttons that execute actions

---

## UI is Read-Only

**CRITICAL PRINCIPLE**: UI is **READ-ONLY** and **OBSERVATIONAL ONLY**.

**Read-Only Enforcement**:
- ❌ **NO database writes**: UI does NOT write to database (no INSERT, UPDATE, DELETE)
- ❌ **NO base table queries**: UI queries views only, not base tables
- ❌ **NO state inference**: UI does not infer or compute state (displays only)
- ❌ **NO action triggers**: UI does not trigger any actions or commands
- ❌ **NO edits**: UI does not allow editing of any data
- ✅ **ONLY display**: UI displays data from read-only views (observational only)

**Read-Only Proof**:
- All backend endpoints are GET only (no POST, PUT, DELETE, PATCH)
- All database queries are SELECT on views only (no INSERT, UPDATE, DELETE)
- Frontend has no edit forms, no save buttons, no action buttons
- UI cannot modify incidents, evidence, or any fact tables

---

## UI Does Not Affect Pipeline

**CRITICAL PRINCIPLE**: UI **does not affect** the data pipeline.

**Pipeline Independence**:
- ✅ **No pipeline dependency**: Data plane (ingest) works without UI
- ✅ **No pipeline blocking**: UI does not block data plane or correlation engine
- ✅ **No pipeline modification**: UI does not modify pipeline state
- ✅ **No pipeline triggers**: UI does not trigger pipeline operations

**Pipeline Independence Proof**:
- Phase 4 (Data Plane): Works without UI (validates and stores events)
- Phase 5 (Correlation Engine): Works without UI (deterministic rules create incidents)
- Phase 6 (AI Core): Works without UI (generates AI metadata)
- Phase 7 (Policy Engine): Works without UI (generates policy recommendations)
- Phase 8 (SOC UI): Optional visibility layer (does not affect pipeline)

---

## UI Reads from DB Views Only

**CRITICAL PRINCIPLE**: UI **reads from DB views only**, not base tables.

**View-Only Enforcement**:
- ✅ **All queries use views**: Backend queries `v_active_incidents`, `v_incident_timeline`, etc.
- ✅ **No base table queries**: Backend does NOT query `incidents`, `evidence`, `raw_events`, etc. directly
- ✅ **Views are read-only**: SQL views are SELECT only (no writes)
- ✅ **View definitions**: Views are defined in `views.sql` (read-only SQL)

**View-Only Proof**:
- Backend `query_view()` function only queries views (not base tables)
- All API endpoints query views only (no direct table queries)
- View definitions in `views.sql` are SELECT only (no INSERT, UPDATE, DELETE)
- UI cannot access base tables (views are the only interface)

---

## System Correctness is Independent of UI

**CRITICAL PRINCIPLE**: System **remains fully correct** if UI is disabled.

**Correctness Without UI**:
- ✅ **Correctness without UI**: All fact tables (incidents, evidence, raw_events) remain correct
- ✅ **Detection without UI**: Correlation engine creates incidents without UI (Phase 5)
- ✅ **Pipeline without UI**: Data plane (ingest) and correlation engine work without UI
- ✅ **Visibility without UI**: UI is optional visibility layer, not required for correctness

**Correctness Without UI Proof**:
- Phase 4 (Data Plane): Works without UI (validates and stores events)
- Phase 5 (Correlation Engine): Works without UI (deterministic rules create incidents)
- Phase 6 (AI Core): Works without UI (generates AI metadata)
- Phase 7 (Policy Engine): Works without UI (generates policy recommendations)
- Phase 8 (SOC UI): Optional visibility (does not affect correctness)

**System Correctness Proof**:
- If UI is disabled: Incidents are still created by correlation engine (Phase 5)
- If UI is disabled: Events are still validated and stored (Phase 4)
- If UI is disabled: System correctness is unaffected (UI is observational only)

---

## What This Component Explicitly Does NOT Do

**Phase 8 Requirements - Forbidden Behaviors**:

- ❌ **UI must NOT write to DB**: UI does not write to database (no INSERT, UPDATE, DELETE)
- ❌ **UI must NOT query base tables**: UI queries views only, not base tables
- ❌ **UI must NOT infer state**: UI displays data only, does not infer or compute state
- ❌ **UI must NOT trigger actions**: UI does not trigger any actions or commands
- ❌ **UI must NOT contain policy logic**: UI displays policy recommendations only, does not evaluate policy
- ❌ **UI must NOT contain AI logic**: UI displays AI insights only, does not perform AI operations

**General Forbidden Behaviors**:

- ❌ **NO edits**: UI does not allow editing of incidents, evidence, or any data
- ❌ **NO action buttons**: UI does not have "acknowledge", "resolve", "close", or any action buttons
- ❌ **NO forms**: UI does not have edit forms or input fields
- ❌ **NO writes**: UI does not write to database (read-only)
- ❌ **NO base table queries**: UI does not query base tables (views only)
- ❌ **NO state computation**: UI does not compute or infer state (displays only)

---

## Database Views (Read-Only)

**Phase 8 requirement**: UI reads from DB views only, not base tables.

### v_active_incidents
- **Columns**: incident_id, machine_id, stage, confidence, created_at, last_observed_at, total_evidence_count, title, description
- **Source**: `incidents` table (WHERE resolved = FALSE)
- **Purpose**: List active (unresolved) incidents

### v_incident_timeline
- **Columns**: incident_id, stage, transitioned_at, from_stage, transitioned_by, transition_reason, evidence_count_at_transition, confidence_score_at_transition
- **Source**: `incident_stages` table
- **Purpose**: Incident stage transitions (timeline)

### v_incident_evidence_summary
- **Columns**: incident_id, evidence_count, evidence_type_count, last_evidence_at, first_evidence_at
- **Source**: `evidence` table (aggregated)
- **Purpose**: Evidence summary per incident

### v_policy_recommendations
- **Columns**: incident_id, recommended_action, simulation_mode, created_at
- **Source**: Empty view (Phase 8 minimal: policy decisions are file-based, not in DB)
- **Purpose**: Policy recommendations (placeholder for Phase 8 minimal)

### v_ai_insights
- **Columns**: incident_id, cluster_id, novelty_score, shap_summary
- **Source**: `cluster_memberships`, `novelty_scores`, `shap_explanations` tables (joined)
- **Purpose**: AI insights (clusters, novelty scores, SHAP summaries)

### v_incident_detail
- **Columns**: Combined view of incident details with evidence and AI insights
- **Source**: `incidents` table joined with `v_incident_evidence_summary` and `v_ai_insights`
- **Purpose**: Complete incident detail view (for incident detail page)

---

## How This Proves Phase 8 Correctness

### Validation Criteria (PASS / FAIL)

**PASS if**:
1. ✅ **UI reads ONLY from views**: All backend queries use views, not base tables
2. ✅ **UI cannot modify data**: All endpoints are GET only (no POST, PUT, DELETE, PATCH)
3. ✅ **UI can be disabled without impact**: System works correctly without UI
4. ✅ **No table writes exist**: No INSERT, UPDATE, DELETE queries in backend
5. ✅ **No base table queries**: All queries use views only

**FAIL if**:
1. ❌ **Any DB write exists**: Backend must NOT write to database
2. ❌ **Any base table is queried**: Backend must query views only, not base tables
3. ❌ **Any action can be triggered**: Frontend must NOT have action buttons or forms

### Contract Compliance

1. **Database Schema Contract** (`schemas/04_correlation.sql`, `schemas/05_ai_metadata.sql`):
   - ✅ Reads from views only (not base tables)
   - ✅ Does NOT write to fact tables (incidents, evidence, raw_events, etc.)
   - ✅ Does NOT write to AI metadata tables (read-only display)

2. **Failure Semantics Contract** (`failure-semantics.md`):
   - ✅ No retries (fails immediately on error)
   - ✅ Fail-closed (missing environment variables cause startup failure)
   - ✅ System correctness unaffected by UI failures (UI is observational only)

3. **Environment Variable Contract** (`env.contract.json`):
   - ✅ Reads database connection parameters from environment variables
   - ✅ Reads API configuration from environment variables
   - ✅ No path computation (all configuration from environment)

---

## Environment Variables

**Required** (contract compliance: `env.contract.json`):
- `RANSOMEYE_DB_HOST`: PostgreSQL host (default: `localhost`)
- `RANSOMEYE_DB_PORT`: PostgreSQL port (default: `5432`)
- `RANSOMEYE_DB_NAME`: Database name (default: `ransomeye`)
- `RANSOMEYE_DB_USER`: Database user (default: `ransomeye`)
- `RANSOMEYE_DB_PASSWORD`: Database password (**required**, no default, fail-closed)

**Optional**:
- `RANSOMEYE_UI_PORT`: Backend API port (default: `8080`)
- `RANSOMEYE_POLICY_DIR`: Policy decisions directory (default: `/tmp/ransomeye/policy`)

**Frontend**:
- `VITE_API_BASE_URL`: Backend API URL (default: `http://localhost:8080`)

---

## Database Views Setup

**Phase 8 requirement**: Views must be created in database before UI can be used.

```bash
# Connect to database
psql -h localhost -U ransomeye -d ransomeye

# Create views
\i services/ui/backend/views.sql
```

**View Creation**:
- Views are defined in `services/ui/backend/views.sql`
- Views are read-only (SELECT only, no writes)
- Views can be created/dropped without affecting base tables
- Views are the only interface UI uses to access data

---

## Run Instructions

### Backend

```bash
# Install dependencies
cd services/ui/backend
pip install -r requirements.txt

# Set required environment variables
export RANSOMEYE_DB_HOST="localhost"
export RANSOMEYE_DB_PORT="5432"
export RANSOMEYE_DB_NAME="ransomeye"
export RANSOMEYE_DB_USER="ransomeye"
export RANSOMEYE_DB_PASSWORD="your_password"

# Create database views (one-time setup)
psql -h localhost -U ransomeye -d ransomeye -f views.sql

# Run backend API
uvicorn main:app --host 0.0.0.0 --port 8080
```

### Frontend

```bash
# Install dependencies
cd services/ui/frontend
npm install

# Set environment variable (optional)
export VITE_API_BASE_URL="http://localhost:8080"

# Run frontend (development)
npm run dev

# Build frontend (production)
npm run build
```

---

## API Endpoints

### `GET /api/incidents`

**Response**:
```json
{
  "incidents": [
    {
      "incident_id": "uuid",
      "machine_id": "machine_id",
      "stage": "SUSPICIOUS",
      "confidence": 30.0,
      "created_at": "RFC3339 UTC timestamp",
      "last_observed_at": "RFC3339 UTC timestamp",
      "total_evidence_count": 1,
      "title": null,
      "description": null
    }
  ]
}
```

### `GET /api/incidents/{incident_id}`

**Response**:
```json
{
  "incident": {
    "incident_id": "uuid",
    "machine_id": "machine_id",
    "stage": "SUSPICIOUS",
    "confidence": 30.0,
    "created_at": "RFC3339 UTC timestamp",
    "last_observed_at": "RFC3339 UTC timestamp",
    "total_evidence_count": 1,
    "evidence_count": 1,
    "cluster_id": "uuid",
    "novelty_score": null,
    "shap_summary": null
  },
  "timeline": [
    {
      "incident_id": "uuid",
      "stage": "SUSPICIOUS",
      "transitioned_at": "RFC3339 UTC timestamp",
      "from_stage": null,
      "transitioned_by": null,
      "transition_reason": null,
      "evidence_count_at_transition": 1,
      "confidence_score_at_transition": 30.0
    }
  ],
  "evidence_summary": {
    "incident_id": "uuid",
    "evidence_count": 1,
    "evidence_type_count": 1,
    "last_evidence_at": "RFC3339 UTC timestamp",
    "first_evidence_at": "RFC3339 UTC timestamp"
  },
  "ai_insights": {
    "incident_id": "uuid",
    "cluster_id": "uuid",
    "novelty_score": null,
    "shap_summary": null
  },
  "policy_recommendations": [
    {
      "incident_id": "uuid",
      "machine_id": "machine_id",
      "evaluated_at": "RFC3339 UTC timestamp",
      "should_recommend_action": true,
      "recommended_action": "ISOLATE_HOST",
      "reason": "Policy rule matched: incident.stage == 'SUSPICIOUS', recommended action: ISOLATE_HOST",
      "simulation_mode": true,
      "enforcement_disabled": true
    }
  ]
}
```

### `GET /api/incidents/{incident_id}/timeline`

**Response**:
```json
{
  "timeline": [
    {
      "incident_id": "uuid",
      "stage": "SUSPICIOUS",
      "transitioned_at": "RFC3339 UTC timestamp",
      "from_stage": null,
      "transitioned_by": null,
      "transition_reason": null,
      "evidence_count_at_transition": 1,
      "confidence_score_at_transition": 30.0
    }
  ]
}
```

---

## Proof of Phase 8 Correctness

**Phase 8 Objective**: Prove that SOC UI provides read-only visibility without affecting system correctness.

**This component proves**:
- ✅ **UI is read-only**: All endpoints are GET only, no database writes
- ✅ **UI reads from views only**: All queries use views, not base tables
- ✅ **UI does not affect pipeline**: Pipeline works correctly without UI
- ✅ **System correctness independent of UI**: Disabling UI has zero impact on detection
- ✅ **No edits, no actions**: Frontend has no edit forms, no action buttons
- ✅ **Contract compliance**: Aligns with frozen contracts from Phases 1-7

**Phase 5 (Correlation Engine) provides**:
- ✅ **Incidents**: Incidents created by deterministic rules

**Phase 6 (AI Core) provides**:
- ✅ **AI Insights**: AI metadata (clusters, novelty scores, SHAP explanations)

**Phase 7 (Policy Engine) provides**:
- ✅ **Policy Recommendations**: Policy decisions and signed commands

**Together, they prove**:
- ✅ **Incidents created without UI**: Correlation engine creates incidents independently (Phase 5)
- ✅ **UI displays without modifying**: UI displays data without modifying incidents (Phase 8)
- ✅ **System correctness without UI**: System works correctly even if UI is disabled

---

## Phase 8 Limitations

**View Limitations**:
- Phase 8 minimal uses `event_id` as `incident_id` in `v_ai_insights` view (limitation of Phase 6)
- `v_policy_recommendations` is empty (Phase 8 minimal: policy decisions are file-based, not in DB)
- Policy recommendations are read from files (not from database view)

**Storage Limitations**:
- Policy recommendations are stored in files (not in database)
- This is because schema changes are not allowed in Phase 8
- **For Phase 8 minimal**: Policy recommendations are read from JSON files
- **Proper implementation**: Would have `policy_decisions` database table and view

These limitations do not affect Phase 8 correctness (UI is read-only, observational only).

---

## Operational Hardening Guarantees

**Phase 10.1 Requirement**: Core runtime hardening for startup and shutdown.

### Startup Validation

- ✅ **Environment Variable Validation**: All required environment variables validated at Core startup. Missing variables cause immediate exit (non-zero).
- ✅ **Database Connectivity Validation**: DB connection validated at Core startup. Connection failure causes immediate exit.
- ✅ **Schema Presence Validation**: Required database tables validated at Core startup. Missing tables cause immediate exit.
- ✅ **Read-Only Enforcement Validation**: UI views validated at Core startup. Missing views cause immediate exit.

### Fail-Fast Invariants

- ✅ **Missing Environment Variable**: Terminates Core immediately (no recovery, no retry).
- ✅ **Database Connection Failure**: Terminates Core immediately (no recovery, no retry).
- ✅ **Schema Mismatch**: Terminates Core immediately (no recovery, no retry).
- ✅ **Unauthorized Write Attempt**: Terminates Core immediately when UI attempts to write to database (read-only module enforcement, no recovery, no retry).

### Graceful Shutdown

- ✅ **SIGTERM/SIGINT Handling**: Core stops accepting new work, finishes in-flight DB transactions, closes DB connections cleanly, exits cleanly with log confirmation.
- ✅ **Transaction Cleanup**: All in-flight transactions committed or rolled back on shutdown.
- ✅ **Connection Cleanup**: All database connections closed cleanly on shutdown.

---

## Database Safety & Transaction Guarantees

**Isolation Level Enforcement**:
- ✅ **Explicit Isolation Level**: Connection pool uses READ_COMMITTED isolation level, enforced on each connection from pool.
- ✅ **Isolation Level Logged**: Isolation level logged at pool creation with actual PostgreSQL setting.

**Explicit Transaction Behavior**:
- ✅ **Read-Only Operations**: UI Backend uses read-only connection pool. All connections from pool are read-only.
- ✅ **Connection Health Validation**: Connection health validated before each query. Broken connections cause immediate Core termination.

**Read-Only Enforcement**:
- ✅ **Read-Only Pool**: Database connection pool enforces read-only mode on every connection.
- ✅ **View-Only Queries**: `query_view()` function verifies that only database views (not base tables) can be queried.
- ✅ **Abort on Write Attempt**: Any write attempt (including queries to base tables) terminates Core immediately with security-grade error logging.
- ✅ **Transaction-Level Enforcement**: Read-only mode enforced at transaction level. Cannot be bypassed.

**Fail-Fast Semantics**:
- ✅ **Deadlock Detection**: Deadlocks detected, logged, and Core terminates immediately (no retries).
- ✅ **Serialization Failures**: Serialization failures detected, logged, and Core terminates immediately (no retries).
- ✅ **Connection Health**: Connection health validated before each query operation. Broken connections cause immediate Core termination.
- ✅ **Unauthorized Table Access**: Queries to base tables (non-view objects) terminate Core immediately.

**No Retries, No Partial State**:
- ✅ **No Retries**: All database failures terminate Core immediately. No retry loops, no best-effort fallbacks.
- ✅ **Read-Only Guarantee**: UI Backend is read-only by construction. No write code paths exist.
- ✅ **View Enforcement**: Only database views can be queried. Base table queries are rejected with immediate Core termination.

---

## Resource & Disk Safety Guarantees

**Disk Safety**:
- ✅ **No Disk Writes**: UI Backend does not write to disk. All data persisted via database only.
- ✅ **Database Disk Failures**: Database read failures (including disk full on database server) detected and handled by database safety utilities. Core terminates immediately on database disk failures.

**Log Safety**:
- ✅ **Log Size Limits**: Log messages are limited to 1MB per message to prevent unbounded log growth.
- ✅ **Logging Failure Handling**: If logging fails (disk full, permission denied, memory error), Core terminates immediately (fail-fast).
- ✅ **No Silent Logging Failures**: All logging operations detect and handle failures explicitly.

**File Descriptor & Resource Limits**:
- ✅ **File Descriptor Check**: File descriptor usage checked at startup. Core terminates if >90% of soft limit in use.
- ✅ **File Descriptor Exhaustion Detection**: Database connection pool operations detect file descriptor exhaustion. Core terminates immediately on detection.

**Memory Safety**:
- ✅ **Memory Allocation Failure Detection**: Query result processing detects MemoryError. Core terminates immediately on detection.
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
- ✅ **API Response Sanitization**: API error responses never expose full error details (avoid secret leakage in error messages).

**Untrusted Input Handling**:
- ✅ **Incident ID Validation**: All incident_id parameters from URL paths validated for format (UUID), length, and injection patterns before processing.
- ✅ **Injection Prevention**: Incident IDs checked for SQL injection patterns (quotes, semicolons, comments). Malformed IDs return 400 Bad Request, Core continues.
- ✅ **Length Limits**: Incident IDs limited to 100 characters. Exceeding limit returns 400 Bad Request.
- ✅ **Type Validation**: All query results validated for structure and types before returning to client.

**Fail-Fast Semantics**:
- ✅ **No Retries**: All security failures terminate Core immediately (except input validation which returns HTTP 400).
- ✅ **Explicit Error Messages**: All security failures log explicit error messages (sanitized) before termination or HTTP error.
- ✅ **Deterministic Behavior**: Core behavior is deterministic under security failure - immediate termination with sanitized error or HTTP 400 for input validation.

**END OF README**
