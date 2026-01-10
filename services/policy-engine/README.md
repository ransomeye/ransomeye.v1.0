# RansomEye v1.0 Policy Engine (Phase 7 - Simulation-First)

**AUTHORITATIVE**: Minimal policy engine operating in simulation-first mode for Phase 7 proof-of-concept.

---

## What This Component Does

This component **ONLY** implements the minimal policy evaluation required for Phase 7 validation:

1. **Consumes Existing Incidents** (contract compliance: Phase 5 incidents):
   - Reads from `incidents` table (unresolved incidents only)
   - **Read-only**: Does NOT modify incidents, evidence, or any fact tables
   - **Non-blocking**: Operates in batch mode, does not block pipeline

2. **Evaluates Explicit Policy Rules** (contract compliance: Phase 7 requirements):
   - **Exactly ONE rule** defined: `evaluate_suspicious_incident_rule()`
   - Rule: IF `incident.stage == 'SUSPICIOUS'`, THEN recommend action: `ISOLATE_HOST`
   - Deterministic: No time windows, no probabilities, no heuristics

3. **Produces Policy Decisions and Simulations** (contract compliance: Phase 7 requirements):
   - **Policy decisions**: Records policy evaluation results (should_recommend_action, recommended_action, reason)
   - **Simulations**: All decisions are in simulation mode (no enforcement, no execution)
   - **Audit trail**: Policy decisions are stored for audit (file-based for Phase 7 minimal)

4. **Signs Commands Without Executing Them** (contract compliance: Phase 7 requirements):
   - **Command generation**: Creates command payload (command_id, command_type, target_machine_id, incident_id, issued_at)
   - **Cryptographic signing**: Signs command using HMAC-SHA256
   - **Storage**: Stores signed command (for audit trail)
   - **NO execution**: Commands are NOT sent to agents (simulation-first)

---

## Policy is Simulation-First

**CRITICAL PRINCIPLE**: Policy Engine operates in **SIMULATION MODE BY DEFAULT**.

**Simulation-First Properties**:
- ✅ **No execution**: Commands are generated and signed but NOT executed
- ✅ **No agent contact**: Agents are NEVER contacted by policy engine
- ✅ **No enforcement**: Policy decisions are recommendations only, not actions
- ✅ **Simulation by default**: Policy engine runs in simulation mode unless explicitly enabled (enforcement disabled by default)

**Simulation Mode Enforcement**:
- Policy decisions are marked with `simulation_mode: True` and `enforcement_disabled: True`
- Signed commands are stored but NOT sent to agents
- All policy decisions are labeled as "SIMULATION - NOT EXECUTED"
- System correctness is unaffected by policy engine (simulation mode)

---

## No Commands Are Executed

**CRITICAL PRINCIPLE**: Policy Engine **NEVER executes commands**.

**No Execution Enforcement**:
- ❌ **NO agent contact**: Policy engine does NOT contact agents
- ❌ **NO command transmission**: Signed commands are NOT sent to agents
- ❌ **NO enforcement**: Policy recommendations are NOT enforced automatically
- ❌ **NO incident modification**: Policy engine does NOT modify incident state
- ✅ **ONLY simulation**: Commands are generated, signed, and stored (simulation only)

**Execution Prevention**:
- Commands are stored in files (not sent to agents)
- Policy decisions are marked as simulation mode
- Enforcement is disabled by default (environment variable controls)
- All policy decisions include "SIMULATION - NOT EXECUTED" label

---

## Enforcement is Disabled by Default

**CRITICAL PRINCIPLE**: Enforcement is **DISABLED BY DEFAULT**.

**Default Configuration**:
- `RANSOMEYE_POLICY_ENFORCEMENT_ENABLED` environment variable defaults to `false`
- Policy engine runs in simulation mode unless explicitly enabled
- Enforcement must be explicitly enabled (not enabled by default)

**Enforcement Control**:
- Enforcement is controlled by environment variable (not code)
- Default is simulation mode (no enforcement)
- Enforcement can be enabled for testing/debugging (but should remain disabled in production for Phase 7)

**Enforcement Status**:
- Default: `RANSOMEYE_POLICY_ENFORCEMENT_ENABLED=false` (simulation mode)
- If enabled: `RANSOMEYE_POLICY_ENFORCEMENT_ENABLED=true` (but still does not execute commands in Phase 7)
- Phase 7 requirement: No automatic enforcement (even if enabled, commands are NOT executed)

---

## All Commands Are Signed and Auditable

**CRITICAL PRINCIPLE**: All commands are **cryptographically signed** and **auditable**.

**Command Signing**:
- ✅ **Cryptographic signing**: Commands are signed using HMAC-SHA256
- ✅ **Signing key**: Signing key comes from environment variable (configurable)
- ✅ **Deterministic**: Same command payload + same key → same signature
- ✅ **Auditable**: All signed commands are stored (for audit trail)

**Audit Trail**:
- Policy decisions are stored (with timestamp, reason, recommended action)
- Signed commands are stored (with payload, signature, signing algorithm, signed_at)
- All policy decisions and commands are immutable (never updated, never deleted)
- File-based storage for Phase 7 minimal (no schema changes allowed)

**Command Structure**:
```json
{
  "payload": {
    "command_id": "uuid",
    "command_type": "ISOLATE_HOST",
    "target_machine_id": "machine_id",
    "incident_id": "incident_id",
    "issued_at": "RFC3339 UTC timestamp"
  },
  "signature": "HMAC-SHA256 signature (64 hex chars)",
  "signing_algorithm": "HMAC-SHA256",
  "signed_at": "RFC3339 UTC timestamp"
}
```

---

## System Correctness Does Not Depend on Policy Engine

**CRITICAL PRINCIPLE**: System **remains fully correct** if policy engine is disabled.

**Correctness Without Policy Engine**:
- ✅ **Correctness without policy**: All fact tables (incidents, evidence, raw_events) remain correct
- ✅ **Detection without policy**: Correlation engine creates incidents without policy engine (Phase 5)
- ✅ **Pipeline without policy**: Data plane (ingest) and correlation engine work without policy engine
- ✅ **Enforcement without policy**: Policy recommendations are optional enrichment, not required for correctness

**Correctness Without Policy Proof**:
- Phase 4 (Data Plane): Works without policy engine (validates and stores events)
- Phase 5 (Correlation Engine): Works without policy engine (deterministic rules create incidents)
- Phase 7 (Policy Engine): Optional enrichment (recommendations only, does not affect correctness)

**System Correctness Proof**:
- If policy engine is disabled: Incidents are still created by correlation engine (Phase 5)
- If policy engine is disabled: Events are still validated and stored (Phase 4)
- If policy engine is disabled: System correctness is unaffected (policy is advisory only)

---

## What This Component Explicitly Does NOT Do

**Phase 7 Requirements - Forbidden Behaviors**:

- ❌ **NO automatic enforcement**: Policy engine does NOT enforce policy decisions automatically
- ❌ **NO agent execution**: Policy engine does NOT execute commands on agents
- ❌ **NO incident modification**: Policy engine does NOT modify incident state, stage, or confidence
- ❌ **NO AI/ML/LLM**: Policy engine uses only deterministic boolean rules (no machine learning)
- ❌ **NO background schedulers**: Policy engine does not use background threads or schedulers
- ❌ **NO async**: Policy engine uses synchronous batch processing only
- ❌ **NO command transmission**: Signed commands are NOT sent to agents (simulation-first)

**General Forbidden Behaviors**:

- ❌ **NO incident creation**: Policy engine does not create incidents (correlation engine creates incidents)
- ❌ **NO incident modification**: Policy engine does not modify incident stage, confidence, or any incident fields
- ❌ **NO evidence creation**: Policy engine does not create evidence (correlation engine creates evidence)
- ❌ **NO fact modification**: Policy engine does not modify any fact tables
- ❌ **NO agent communication**: Policy engine does not contact agents (no HTTP, no RPC, no messaging)
- ❌ **NO real-time processing**: Policy engine processes incidents in batch (not real-time)
- ❌ **NO pipeline blocking**: Policy engine does not block data plane or correlation engine

---

## What Rules Exist

**Exactly ONE rule** (Phase 7 requirement):

### Rule: `evaluate_suspicious_incident_rule()`

**Condition** (deterministic):
- `incident.current_stage == 'SUSPICIOUS'` (exact string match)

**Action** (deterministic):
- If condition is TRUE: Recommend action `ISOLATE_HOST`
- If condition is FALSE: Recommend `NO_ACTION`

**Deterministic Properties**:
- ✅ **No time-window logic**: Rule applies to single incident only, no time-based conditions
- ✅ **No probabilistic logic**: Deterministic boolean condition (current_stage == 'SUSPICIOUS')
- ✅ **No heuristics**: Explicit boolean condition, no fuzzy logic
- ✅ **Recommendation only**: Returns action recommendation, does not execute

**Why Rules Are Deterministic**:
- Rule uses explicit boolean condition (component == 'linux_agent' for comparison)
- Rule does not depend on time windows or temporal relationships
- Rule does not use probabilities, statistics, or probability distributions
- Rule does not use heuristics, pattern matching, or fuzzy logic
- Rule does not use ML/AI (pure boolean logic only)

---

## Why Time is NOT Required for Correctness

**Time-Independent Determinism**:

1. **No Time-Window Logic**:
   - Rule does not depend on time windows (no "incidents within X hours")
   - Rule applies to single incident only (no temporal relationships)
   - No time-based conditions (no "if incident occurred at Y time")

2. **Deterministic Execution Order**:
   - Incidents are processed in deterministic order (by `first_observed_at ASC`)
   - Order is deterministic (same incidents in same order → same results)
   - No time-based scheduling or timing dependencies

3. **Idempotency Without Time**:
   - Idempotency is achieved through file existence checks (not time-based)
   - Check if incident already evaluated (policy decision file exists)
   - Restarting engine does NOT duplicate policy decisions (time-independent)

4. **Persisted Facts Only**:
   - Policy engine uses only persisted facts from database (not real-time data)
   - No time-dependent state (no "last seen" timestamps for policy evaluation)
   - Facts are immutable (time of incident is a fact, not a dependency)

**Proof of Time-Independence**:
- Rule evaluation depends only on incident data (current_stage, machine_id, etc.)
- Rule does not depend on current time, time windows, or temporal relationships
- Same incidents processed at different times produce same results (deterministic)
- Policy engine can be restarted at any time without affecting correctness (idempotent)

---

## How This Proves Phase 7 Correctness

### Validation Criteria (PASS / FAIL)

**PASS if**:
1. ✅ **Incidents are unchanged**: Policy engine does not modify incidents table
2. ✅ **Policy decisions are recorded**: Policy decisions are stored (file-based for Phase 7 minimal)
3. ✅ **Signed commands are generated**: Signed commands are created and stored (file-based for Phase 7 minimal)
4. ✅ **No enforcement occurs**: Commands are NOT executed, agents are NOT contacted
5. ✅ **Disabling policy engine has zero impact**: System works correctly without policy engine

**FAIL if**:
1. ❌ **Any command is executed**: Commands must NOT be executed (simulation-first)
2. ❌ **Any agent is contacted**: Policy engine must NOT contact agents
3. ❌ **Incident state is modified**: Policy engine must NOT modify incidents
4. ❌ **Enforcement occurs implicitly**: Enforcement must be explicitly disabled (simulation mode by default)

### Contract Compliance

1. **Event Envelope Contract** (`event-envelope.schema.json`):
   - ✅ Reads incidents (created by correlation engine from validated events)
   - ✅ Does not modify events or incidents (read-only)

2. **Database Schema Contract** (`schemas/04_correlation.sql`):
   - ✅ Reads from `incidents` table (read-only, does not modify)
   - ✅ Does NOT write to fact tables (incidents, evidence, raw_events, etc.)
   - ✅ Phase 7 minimal: Uses file-based storage for policy decisions and commands (no schema changes allowed)

3. **Failure Semantics Contract** (`failure-semantics.md`):
   - ✅ No retries (fails immediately on error)
   - ✅ Fail-closed (missing environment variables cause startup failure)
   - ✅ System correctness unaffected by policy engine failures (policy is advisory only)

4. **Environment Variable Contract** (`env.contract.json`):
   - ✅ Reads database connection parameters from environment variables
   - ✅ Reads policy configuration from environment variables
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
- `RANSOMEYE_POLICY_DIR`: Directory for policy decisions and signed commands (default: `/tmp/ransomeye/policy`)
- `RANSOMEYE_COMMAND_SIGNING_KEY`: Command signing key (default: phase7_minimal_default_key, NOT SECURE FOR PRODUCTION)
- `RANSOMEYE_POLICY_ENFORCEMENT_ENABLED`: Enable enforcement (default: `false`, simulation mode)

---

## Database Schema Requirements

**Phase 7 requires these tables** (from Phase 2 schema):
- `incidents`: Source of incidents (from Phase 5 correlation engine)

**Phase 7 does NOT require**:
- Policy decision tables (Phase 7 minimal: uses file-based storage, no schema changes allowed)
- Command tables (Phase 7 minimal: uses file-based storage, no schema changes allowed)

**Note**: Phase 7 minimal implementation uses file-based storage for policy decisions and signed commands because schema changes are not allowed. In production, these would be stored in database tables (`policy_decisions`, `signed_commands`).

---

## Run Instructions

```bash
# Install dependencies
cd services/policy-engine
pip install -r requirements.txt

# Set required environment variables
export RANSOMEYE_DB_HOST="localhost"
export RANSOMEYE_DB_PORT="5432"
export RANSOMEYE_DB_NAME="ransomeye"
export RANSOMEYE_DB_USER="ransomeye"
export RANSOMEYE_DB_PASSWORD="your_password"

# Optional: Set policy directory (default: /tmp/ransomeye/policy)
export RANSOMEYE_POLICY_DIR="/opt/ransomeye/policy"

# Optional: Set command signing key (default: phase7_minimal_default_key)
export RANSOMEYE_COMMAND_SIGNING_KEY="your_signing_key"

# Optional: Enable enforcement (default: false, simulation mode)
# WARNING: Even if enabled, commands are NOT executed in Phase 7
export RANSOMEYE_POLICY_ENFORCEMENT_ENABLED="false"

# Run policy engine (batch processing, simulation mode)
python3 app/main.py
```

---

## Policy Decision Format

**Policy Decision Structure**:
```json
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
```

**Signed Command Structure**:
```json
{
  "payload": {
    "command_id": "uuid",
    "command_type": "ISOLATE_HOST",
    "target_machine_id": "machine_id",
    "incident_id": "incident_id",
    "issued_at": "RFC3339 UTC timestamp"
  },
  "signature": "HMAC-SHA256 signature (64 hex chars)",
  "signing_algorithm": "HMAC-SHA256",
  "signed_at": "RFC3339 UTC timestamp"
}
```

---

## Proof of Phase 7 Correctness

**Phase 7 Objective**: Prove that policy engine operates in simulation-first mode without affecting system correctness.

**This component proves**:
- ✅ **Policy is simulation-first**: Commands are generated and signed but NOT executed
- ✅ **No commands are executed**: Agents are NEVER contacted, commands are NOT sent
- ✅ **Enforcement is disabled by default**: Simulation mode by default, enforcement must be explicitly enabled
- ✅ **All commands are signed and auditable**: Commands are cryptographically signed and stored (for audit trail)
- ✅ **System correctness does not depend on policy engine**: Disabling policy engine has zero impact on detection
- ✅ **Contract compliance**: Aligns with frozen contracts from Phases 1-6

**Phase 5 (Correlation Engine) provides**:
- ✅ **Incidents**: Incidents created by deterministic rules (without policy engine)

**Together, they prove**:
- ✅ **Incidents created without policy**: Correlation engine creates incidents independently (Phase 5)
- ✅ **Policy recommends without modifying**: Policy engine adds recommendations without modifying incidents (Phase 7)
- ✅ **System correctness without policy**: System works correctly even if policy engine is disabled

---

## Phase 7 Limitation

**Storage Limitation**:
- Phase 7 minimal uses file-based storage for policy decisions and signed commands
- This is because schema changes are not allowed in Phase 7
- **For Phase 7 minimal**: Policy decisions and commands are stored in JSON files
- **Proper implementation**: Would have `policy_decisions` and `signed_commands` database tables

This limitation does not affect Phase 7 correctness (policy is simulation-first, metadata only).

---

## Operational Hardening Guarantees

**Phase 10.1 Requirement**: Core runtime hardening for startup and shutdown.

### Startup Validation

- ✅ **Environment Variable Validation**: All required environment variables validated at Core startup. Missing variables cause immediate exit (non-zero).
- ✅ **Database Connectivity Validation**: DB connection validated at Core startup. Connection failure causes immediate exit.
- ✅ **Schema Presence Validation**: Required database tables validated at Core startup. Missing tables cause immediate exit.
- ✅ **Write Permissions Validation**: Policy directory validated for write permissions at Core startup. Permission failures cause immediate exit.

### Fail-Fast Invariants

- ✅ **Missing Environment Variable**: Terminates Core immediately (no recovery, no retry).
- ✅ **Database Connection Failure**: Terminates Core immediately (no recovery, no retry).
- ✅ **Schema Mismatch**: Terminates Core immediately (no recovery, no retry).

### Graceful Shutdown

- ✅ **SIGTERM/SIGINT Handling**: Core stops accepting new work, finishes in-flight DB transactions, closes DB connections cleanly, exits cleanly with log confirmation.
- ✅ **Transaction Cleanup**: All in-flight transactions committed or rolled back on shutdown.
- ✅ **Connection Cleanup**: All database connections closed cleanly on shutdown.

---

## Database Safety & Transaction Guarantees

**Isolation Level Enforcement**:
- ✅ **Explicit Isolation Level**: All connections use READ_COMMITTED isolation level, enforced at connection creation.
- ✅ **Isolation Level Logged**: Isolation level logged at startup with actual PostgreSQL setting.

**Explicit Transaction Behavior**:
- ✅ **Read-Only Operations**: Policy Engine uses read-only connections exclusively. Connection health validated before each read operation.

**Read-Only Enforcement**:
- ✅ **Read-Only Connections**: All database connections are read-only. Policy Engine must never write to DB.
- ✅ **Abort on Write Attempt**: Any write attempt terminates Core immediately with security-grade error logging.
- ✅ **Connection-Level Enforcement**: Read-only mode enforced at connection level. Cannot be bypassed.

**Fail-Fast Semantics**:
- ✅ **Deadlock Detection**: Deadlocks detected, logged, and Core terminates immediately (no retries).
- ✅ **Serialization Failures**: Serialization failures detected, logged, and Core terminates immediately (no retries).
- ✅ **Connection Health**: Connection health validated before each read operation. Broken connections cause immediate Core termination.
- ✅ **Write Attempt Detection**: Any write operation (INSERT, UPDATE, DELETE, CREATE, ALTER, DROP) terminates Core immediately.

**No Retries, No Partial State**:
- ✅ **No Retries**: All database failures terminate Core immediately. No retry loops, no best-effort fallbacks.
- ✅ **Read-Only Guarantee**: Policy Engine is read-only by construction. No write code paths exist.

---

## Resource & Disk Safety Guarantees

**Disk Safety**:
- ✅ **Disk Full Detection**: Policy decision and signed command file writes detect disk full conditions (ENOSPC, EDQUOT). Core terminates immediately on detection.
- ✅ **Permission Denied Detection**: File operations detect permission denied errors (EACCES, EPERM). Core terminates immediately on detection.
- ✅ **Read-Only Filesystem Detection**: File write operations detect read-only filesystem errors (EROFS). Core terminates immediately on detection.
- ✅ **Directory Creation Safety**: Policy directory creation uses safe operations with disk space checks. Core terminates immediately on failure.
- ✅ **File Write Safety**: All file writes (policy decisions, signed commands) use safe write operations with explicit error detection. Core terminates immediately on write failure.
- ✅ **No Silent Failures**: All disk operations use explicit error detection. No retries, no degradation.

**Log Safety**:
- ✅ **Log Size Limits**: Log messages are limited to 1MB per message to prevent unbounded log growth.
- ✅ **Logging Failure Handling**: If logging fails (disk full, permission denied, memory error), Core terminates immediately (fail-fast).
- ✅ **No Silent Logging Failures**: All logging operations detect and handle failures explicitly.

**File Descriptor & Resource Limits**:
- ✅ **File Descriptor Check**: File descriptor usage checked at startup. Core terminates if >90% of soft limit in use.
- ✅ **File Descriptor Exhaustion Detection**: All file open operations detect file descriptor exhaustion (EMFILE, ENFILE). Core terminates immediately on detection.

**Memory Safety**:
- ✅ **Memory Allocation Failure Detection**: Policy evaluation and file write operations detect MemoryError. Core terminates immediately on detection.
- ✅ **No Swap-Based Survival**: Core does not attempt to continue with swap-based memory. Memory allocation failures cause immediate termination.

**Fail-Fast Semantics**:
- ✅ **No Retries**: All resource failures terminate Core immediately. No retry loops, no best-effort fallbacks.
- ✅ **Explicit Error Messages**: All resource failures log explicit error messages before termination.
- ✅ **Deterministic Behavior**: Core behavior is deterministic under resource failure - immediate termination with explicit error.

---

## Security & Secrets Handling Guarantees

**Secrets Handling**:
- ✅ **Environment Variables Only**: All secrets (database password, signing key) come from environment variables only. No secrets in code, config files, logs, or exceptions.
- ✅ **Secret Validation**: All required secrets validated at startup. Missing or weak secrets terminate Core immediately.
- ✅ **No Secret Logging**: Secrets never appear in logs. Config logging uses redacted versions.

**Signing Discipline**:
- ✅ **Key Loaded Once**: Signing key read once at startup, never reloaded. Key cached in module-level variable (_SIGNING_KEY).
- ✅ **Key Never Logged**: Signing key never logged. Any attempt to log key terminates Core immediately.
- ✅ **Key Strength Validation**: Signing key validated for strength (minimum 32 characters, sufficient entropy, not default value). Weak keys terminate Core immediately.
- ✅ **Fail-Fast on Invalid Key**: Missing, weak, or default signing keys terminate Core immediately at startup. No fallback to default keys.

**Log Redaction**:
- ✅ **Automatic Redaction**: All log messages and exceptions automatically sanitized for secrets.
- ✅ **Stack Trace Sanitization**: Exception messages sanitized before logging.
- ✅ **Secret Pattern Detection**: Logging detects common secret patterns and redacts values.

**Fail-Fast Semantics**:
- ✅ **No Retries**: All security failures terminate Core immediately.
- ✅ **Explicit Error Messages**: All security failures log explicit error messages (sanitized) before termination.
- ✅ **Deterministic Behavior**: Core behavior is deterministic under security failure - immediate termination with sanitized error.

**END OF README**
