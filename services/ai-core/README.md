# RansomEye v1.0 AI Core (Phase 6 - Read-Only, Non-Blocking)

**AUTHORITATIVE**: Minimal AI Core operating in read-only advisory mode for Phase 6 proof-of-concept.

---

## What This Component Does

This component **ONLY** implements the minimal AI analysis required for Phase 6 validation:

1. **Consumes Existing Incidents** (contract compliance: Phase 5 incidents):
   - Reads from `incidents` table (unresolved incidents only)
   - **Read-only**: Does NOT modify incidents, evidence, or any fact tables
   - **Non-blocking**: Operates in batch mode, does not block pipeline

2. **Performs Offline, Batch Analysis** (contract compliance: Phase 6 requirements):
   - **Offline**: Processes incidents in batch, not real-time
   - **Batch**: Reads all unresolved incidents, processes them together
   - **Non-blocking**: Does not interfere with data plane or correlation engine

3. **Produces Metadata Only** (contract compliance: Phase 6 requirements):
   - **Feature Vectors**: Extracts numeric features from incidents (references only, not blobs)
   - **Clusters**: Groups similar incidents using unsupervised clustering (metadata only)
   - **SHAP Explanations**: Explains incident confidence contributions (references only, not blobs)

4. **Stores AI Metadata in Database** (contract compliance: Phase 2 schema):
   - **ai_model_versions**: Registry of model versions (versioned and reproducible)
   - **feature_vectors**: Feature vector references (not blobs)
   - **clusters**: Cluster metadata (versioned)
   - **cluster_memberships**: Incident ↔ cluster mapping (metadata only)
   - **shap_explanations**: SHAP explanation references (not blobs)

---

## AI is Read-Only

**CRITICAL PRINCIPLE**: AI Core is **read-only** with respect to facts. It **NEVER** modifies:

- ❌ **NO incident modification**: Does not create, update, or delete incidents
- ❌ **NO evidence modification**: Does not create, update, or delete evidence
- ❌ **NO fact modification**: Does not modify any fact tables (incidents, evidence, raw_events, etc.)
- ✅ **ONLY metadata**: Writes ONLY to AI metadata tables (feature_vectors, clusters, shap_explanations, etc.)

**Read-Only Enforcement**:
- AI Core reads from `incidents` table (SELECT only)
- AI Core writes ONLY to AI metadata tables (feature_vectors, clusters, cluster_memberships, shap_explanations)
- AI Core NEVER writes to incidents, evidence, raw_events, or any fact tables
- If AI Core fails, incidents remain unchanged (system correctness unaffected)

---

## AI Cannot Block or Decide

**CRITICAL PRINCIPLE**: AI Core **cannot block** the pipeline and **cannot decide** anything:

- ❌ **NO blocking**: Does not block data plane or correlation engine
- ❌ **NO decision-making**: Does not create incidents or modify incident state
- ❌ **NO real-time inference**: Operates in batch mode, not real-time
- ❌ **NO pipeline dependency**: Pipeline works correctly even if AI Core is disabled

**Non-Blocking Enforcement**:
- AI Core operates in batch mode (offline, not real-time)
- AI Core does not block data plane (ingest service) or correlation engine
- AI Core can be disabled without affecting system correctness
- If AI Core fails, system continues normally (incidents unchanged)

---

## AI Output is Advisory Only

**CRITICAL PRINCIPLE**: AI Core output is **advisory only**, not actionable:

- ✅ **Metadata only**: Feature vectors, clusters, SHAP explanations are metadata
- ✅ **References only**: Feature vectors and SHAP explanations stored as references (hashes), not blobs
- ✅ **No action triggers**: AI output does not trigger any actions or decisions
- ✅ **Human review required**: AI output is for human review, not automated action

**Advisory-Only Enforcement**:
- AI Core does not create incidents (correlation engine creates incidents)
- AI Core does not modify incident stage or confidence (correlation engine manages incidents)
- AI Core does not trigger alerts or actions (other systems may use AI metadata for analysis)
- AI Core output is informational only (for SOC analysts, not for automation)

---

## System Remains Correct Without AI

**CRITICAL PRINCIPLE**: System **remains fully correct** if AI is disabled:

- ✅ **Correctness without AI**: All fact tables (incidents, evidence, raw_events) remain correct
- ✅ **Detection without AI**: Correlation engine creates incidents without AI (deterministic rules)
- ✅ **Pipeline without AI**: Data plane (ingest) and correlation engine work without AI
- ✅ **Metadata without AI**: AI metadata is optional enrichment, not required for correctness

**Correctness Without AI**:
- Phase 4 (Data Plane): Works without AI (validates and stores events)
- Phase 5 (Correlation Engine): Works without AI (deterministic rules create incidents)
- Phase 6 (AI Core): Optional enrichment (metadata only, does not affect correctness)

**System Correctness Proof**:
- If AI Core is disabled: Incidents are still created by correlation engine (Phase 5)
- If AI Core is disabled: Events are still validated and stored (Phase 4)
- If AI Core is disabled: System correctness is unaffected (AI is advisory only)

---

## What This Component Explicitly Does NOT Do

**Phase 6 Requirements - Forbidden Behaviors**:

- ❌ **AI does NOT create incidents**: Correlation engine creates incidents (Phase 5), not AI
- ❌ **AI does NOT modify incidents**: AI reads incidents only, never modifies
- ❌ **AI does NOT block pipeline**: AI operates in batch mode, does not block data plane
- ❌ **AI does NOT require real-time inference**: AI operates offline, batch processing only
- ❌ **AI is NOT in data plane**: AI is separate from data plane (ingest) and correlation engine
- ❌ **NO deep learning**: Uses only scikit-learn (KMeans) and SHAP, no deep learning models
- ❌ **NO retries**: Does not retry failed operations
- ❌ **NO background schedulers**: Does not use background threads or schedulers

**General Forbidden Behaviors**:

- ❌ **NO incident creation**: Does not create incidents (correlation engine creates incidents)
- ❌ **NO incident modification**: Does not modify incident stage, confidence, or any incident fields
- ❌ **NO evidence creation**: Does not create evidence (correlation engine creates evidence)
- ❌ **NO fact modification**: Does not modify any fact tables
- ❌ **NO real-time processing**: Does not process events in real-time (batch only)
- ❌ **NO pipeline blocking**: Does not block data plane or correlation engine

---

## How This Proves Phase 6 Correctness

### Validation Criteria (PASS / FAIL)

**PASS if**:
1. ✅ **Incidents are unchanged**: AI Core does not modify incidents table
2. ✅ **Only AI metadata tables are written**: AI Core writes ONLY to ai_model_versions, feature_vectors, clusters, cluster_memberships, shap_explanations
3. ✅ **Disabling AI has zero impact on detection**: Correlation engine creates incidents without AI
4. ✅ **SHAP output is generated per run**: SHAP explanations are generated for each batch run
5. ✅ **Models are versioned and reproducible**: Model versions are stored in ai_model_versions table with version strings

**FAIL if**:
1. ❌ **AI touches facts**: AI modifies incidents, evidence, or any fact tables
2. ❌ **AI alters incident state**: AI modifies incident stage, confidence, or any incident fields
3. ❌ **AI introduces timing dependency**: AI blocks pipeline or requires real-time inference
4. ❌ **AI blocks pipeline**: AI interferes with data plane or correlation engine

### Contract Compliance

1. **Event Envelope Contract** (`event-envelope.schema.json`):
   - ✅ Reads incidents (created by correlation engine from validated events)
   - ✅ Does not modify events or incidents (read-only)

2. **Database Schema Contract** (`schemas/05_ai_metadata.sql`):
   - ✅ Writes to `ai_model_versions` table (model version registry)
   - ✅ Writes to `feature_vectors` table (feature vector references, not blobs)
   - ✅ Writes to `clusters` table (cluster metadata)
   - ✅ Writes to `cluster_memberships` table (incident ↔ cluster mapping)
   - ✅ Writes to `shap_explanations` table (SHAP explanation references, not blobs)
   - ✅ Does NOT write to fact tables (incidents, evidence, raw_events, etc.)

3. **Failure Semantics Contract** (`failure-semantics.md`):
   - ✅ No retries (fails immediately on error)
   - ✅ Fail-closed (missing environment variables cause startup failure)
   - ✅ System correctness unaffected by AI failures (AI is advisory only)

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

**Phase 6 requires these tables** (from Phase 2 schema):
- `incidents`: Source of incidents (from Phase 5 correlation engine)
- `ai_model_versions`: AI model version registry (versioned and reproducible)
- `feature_vectors`: Feature vector references (not blobs)
- `clusters`: Cluster metadata (versioned)
- `cluster_memberships`: Incident ↔ cluster mapping (metadata only)
- `shap_explanations`: SHAP explanation references (not blobs)

**Phase 6 does NOT require**:
- Normalized tables (used only if required by feature extraction, not used in Phase 6)
- Raw events (used indirectly via incidents, not directly read by AI Core)

**Note**: Phase 6 minimal implementation uses incident_id as event_id in feature_vectors and cluster_memberships tables (limitation of Phase 6 minimal). Proper implementation would have incident-level feature vectors and cluster memberships.

---

## Run Instructions

```bash
# Install dependencies
cd services/ai-core
pip install -r requirements.txt

# Set required environment variables
export RANSOMEYE_DB_HOST="localhost"
export RANSOMEYE_DB_PORT="5432"
export RANSOMEYE_DB_NAME="ransomeye"
export RANSOMEYE_DB_USER="ransomeye"
export RANSOMEYE_DB_PASSWORD="your_password"

# Run AI Core (batch processing)
python3 app/main.py
```

---

## AI Functions (Minimal, Required)

**Phase 6 requirement**: Exactly THREE capabilities

### 1. Feature Extraction (Deterministic)

**Module**: `feature_extraction.py`

**Function**: `extract_incident_features(incident: Dict[str, Any]) -> List[float]`

**Features Extracted** (Phase 6 requirement):
- `confidence_score`: Incident confidence (0.0 to 100.0)
- `current_stage`: Incident stage encoded as numeric (CLEAN=0.0, SUSPICIOUS=1.0, PROBABLE=2.0, CONFIRMED=3.0)
- `total_evidence_count`: Number of evidence entries (0.0 to inf)

**Deterministic Properties**:
- ✅ No probabilistic logic: Features are deterministic functions of incident data
- ✅ No time-window dependency: Features depend only on incident state
- ✅ No heuristics: Explicit feature extraction rules only

### 2. Unsupervised Clustering

**Module**: `clustering.py`

**Function**: `cluster_incidents(feature_vectors: np.ndarray, n_clusters: int = 3, random_state: int = 42)`

**Algorithm**: KMeans (scikit-learn)

**Reproducibility**:
- ✅ `random_state=42`: Ensures same input → same output (reproducible)
- ✅ `n_clusters=3`: Fixed number of clusters (deterministic)

**Deterministic Properties**:
- ✅ Reproducible: random_state ensures same input → same output
- ✅ No time-window dependency: Clustering depends only on feature vectors
- ✅ No probabilistic logic: KMeans is deterministic with fixed random_state

### 3. Explainability (SHAP)

**Module**: `shap_explainer.py`

**Function**: `explain_incident_confidence(incident: Dict[str, Any], feature_vector: List[float]) -> List[Dict[str, Any]]`

**Explanations Generated**:
- Confidence contribution: How confidence_score contributes to itself
- Stage contribution: How current_stage contributes to confidence
- Evidence contribution: How total_evidence_count contributes to confidence

**Storage**:
- ✅ References only: SHAP explanations stored as hashes, not blobs
- ✅ Top N features: Only top N feature contributions stored as JSONB (for quick access)
- ✅ Per run: SHAP output is generated per batch run (Phase 6 requirement)

---

## Proof of Phase 6 Correctness

**Phase 6 Objective**: Prove that AI Core operates in read-only advisory mode without affecting system correctness.

**This component proves**:
- ✅ **AI is read-only**: Does not modify incidents, evidence, or any fact tables
- ✅ **AI is non-blocking**: Operates in batch mode, does not block pipeline
- ✅ **AI is advisory only**: Output is metadata only, not actionable
- ✅ **System remains correct without AI**: Disabling AI has zero impact on detection
- ✅ **Models are versioned**: Model versions stored in ai_model_versions table
- ✅ **SHAP output per run**: SHAP explanations generated for each batch run

**Phase 5 (Correlation Engine) provides**:
- ✅ **Incidents**: Incidents created by deterministic rules (without AI)

**Together, they prove**:
- ✅ **Incidents created without AI**: Correlation engine creates incidents independently (Phase 5)
- ✅ **AI enriches without modifying**: AI Core adds metadata without modifying incidents (Phase 6)
- ✅ **System correctness without AI**: System works correctly even if AI is disabled

---

## Phase 6 Limitation

**Schema Limitation**:
- Phase 6 schema expects `event_id` in `feature_vectors`, `cluster_memberships`, and `shap_explanations` tables
- Phase 6 works with incidents, not events
- **For Phase 6 minimal**: We use `incident_id` as `event_id` (limitation of Phase 6 minimal implementation)
- **Proper implementation**: Would have incident-level feature vectors and cluster memberships

This limitation does not affect Phase 6 correctness (AI is read-only, metadata only).

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
- ✅ **Read Operations**: Use read-only connections with explicit read-only mode enforcement. Connection health validated before each read.
- ✅ **Write Operations**: All metadata writes (model versions, feature vectors, clusters, cluster memberships, SHAP explanations) use explicit transaction management:
  - Explicit transaction begin
  - Explicit commit on success
  - Explicit rollback on failure
  - If rollback fails, Core terminates immediately

**Read-Only Enforcement**:
- ✅ **Read Connections**: All incident reads use read-only connections. Abort process if write attempted.
- ✅ **Write Connections**: Separate write connections used only for metadata writes. Read operations never use write connections.

**Fail-Fast Semantics**:
- ✅ **Deadlock Detection**: Deadlocks detected, logged, and Core terminates immediately (no retries).
- ✅ **Integrity Violations**: Unique constraint violations, foreign key violations, and check violations detected, logged, and Core terminates immediately (no retries).
- ✅ **Serialization Failures**: Serialization failures detected, logged, and Core terminates immediately (no retries).
- ✅ **Connection Health**: Connection health validated before each critical operation. Broken connections cause immediate Core termination.

**No Retries, No Partial State**:
- ✅ **No Retries**: All database failures terminate Core immediately. No retry loops, no best-effort fallbacks.
- ✅ **Atomic Transactions**: All metadata writes are atomic. Either all writes succeed or all are rolled back.
- ✅ **No Partial State**: Failed transactions are completely rolled back. No partial metadata stored.

---

## Resource & Disk Safety Guarantees

**Disk Safety**:
- ✅ **No Disk Writes**: AI Core does not write to disk. All data persisted via database only.
- ✅ **Database Disk Failures**: Database write failures (including disk full) detected and handled by database safety utilities. Core terminates immediately on database disk failures.

**Log Safety**:
- ✅ **Log Size Limits**: Log messages are limited to 1MB per message to prevent unbounded log growth.
- ✅ **Logging Failure Handling**: If logging fails (disk full, permission denied, memory error), Core terminates immediately (fail-fast).
- ✅ **No Silent Logging Failures**: All logging operations detect and handle failures explicitly.

**File Descriptor & Resource Limits**:
- ✅ **File Descriptor Check**: File descriptor usage checked at startup. Core terminates if >90% of soft limit in use.
- ✅ **File Descriptor Exhaustion Detection**: Database connection operations detect file descriptor exhaustion. Core terminates immediately on detection.

**Memory Safety**:
- ✅ **Memory Allocation Failure Detection**: All memory-intensive operations (feature extraction, clustering, SHAP explanations) detect MemoryError. Core terminates immediately on detection.
- ✅ **NumPy Array Operations**: All NumPy array allocations (feature vectors, cluster computations) detect memory failures. Core terminates immediately on allocation failure.
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

**Untrusted Input Handling**:
- ✅ **Incident Validation**: All incidents from database validated for structure, types, and bounds before processing.
- ✅ **Structure Validation**: Incidents must have required fields (incident_id, machine_id, current_stage, confidence_score). Missing fields terminate Core immediately.
- ✅ **Type Validation**: All incident fields validated for types (strings, numbers, booleans). Invalid types terminate Core immediately.
- ✅ **Bounds Checking**: Confidence scores validated for bounds (0.0-100.0). Stage values validated against allowed values. Out-of-bounds values terminate Core immediately.
- ✅ **List Size Limits**: Incident lists limited to 10,000 entries to prevent DoS. Exceeding limit terminates Core immediately.

**Fail-Fast Semantics**:
- ✅ **No Retries**: All security failures terminate Core immediately.
- ✅ **Explicit Error Messages**: All security failures log explicit error messages (sanitized) before termination.
- ✅ **Deterministic Behavior**: Core behavior is deterministic under security failure - immediate termination with sanitized error.

**END OF README**
