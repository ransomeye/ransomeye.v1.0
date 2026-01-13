# RansomEye v1.0 GA Validation Test Matrix

**AUTHORITATIVE:** Complete test matrix for GA validation

## Test Matrix Overview

| Test Area | Test ID | Test Name | Priority | Status | Evidence Artifact |
|-----------|---------|-----------|----------|--------|-------------------|
| **Determinism** | DET-001 | Detection Determinism | P0 | PENDING | `determinism_proof_log.json` |
| **Determinism** | DET-002 | Normalization Determinism | P0 | PENDING | `determinism_proof_log.json` |
| **Determinism** | DET-003 | Correlation Determinism | P0 | PENDING | `determinism_proof_log.json` |
| **Determinism** | DET-004 | Forensics Determinism | P0 | PENDING | `determinism_proof_log.json` |
| **Replay** | REP-001 | Normalized Events Replay | P0 | PENDING | `replay_verification_log.json` |
| **Replay** | REP-002 | Incidents Replay | P0 | PENDING | `replay_verification_log.json` |
| **Replay** | REP-003 | Evidence Replay | P0 | PENDING | `replay_verification_log.json` |
| **Replay** | REP-004 | Forensic Summaries Replay | P0 | PENDING | `replay_verification_log.json` |
| **Failure** | FAIL-001 | DB Restart (Mid-Transaction) | P0 | PENDING | `failure_injection_results.json` |
| **Failure** | FAIL-002 | Queue Overflow | P0 | PENDING | `failure_injection_results.json` |
| **Failure** | FAIL-003 | Agent Disconnect | P0 | PENDING | `failure_injection_results.json` |
| **Failure** | FAIL-004 | Duplicate Events | P0 | PENDING | `failure_injection_results.json` |
| **Failure** | FAIL-005 | Partial Writes | P0 | PENDING | `failure_injection_results.json` |
| **Scale** | SCALE-001 | Burst Ingestion (10K/sec) | P0 | PENDING | `scale_validation_metrics.json` |
| **Scale** | SCALE-002 | Sustained Load (1K/sec) | P0 | PENDING | `scale_validation_metrics.json` |
| **Scale** | SCALE-003 | POC Single-Host Mode | P1 | PENDING | `scale_validation_metrics.json` |
| **Audit** | AUDIT-001 | Ledger Integrity | P0 | PENDING | `audit_integrity_verification.json` |
| **Audit** | AUDIT-002 | Coverage Analysis | P0 | PENDING | `audit_coverage_report.json` |
| **Audit** | AUDIT-003 | Compliance Verification | P0 | PENDING | `audit_compliance_report.json` |

## Test Details

### DET-001: Detection Determinism

**Objective**: Prove that same agent telemetry produces same `raw_events` (bit-for-bit).

**Test Steps**:
1. Generate deterministic test telemetry (fixed seed)
2. Ingest telemetry through agent → ingest service
3. Capture `raw_events` table (event_id, payload hash)
4. Clear `raw_events` table
5. Re-ingest same telemetry (same order)
6. Capture `raw_events` table (event_id, payload hash)
7. Compare hashes (must match exactly)

**Success Criteria**:
- All `event_id` values match
- All `payload` hashes match
- All `ingested_at` timestamps match (if deterministic)

**Evidence**: `determinism_proof_log.json`

---

### DET-002: Normalization Determinism

**Objective**: Prove that same `raw_events` produces same normalized events (bit-for-bit).

**Test Steps**:
1. Load deterministic `raw_events` (from DET-001)
2. Process through normalization service
3. Capture normalized tables (process_activity, file_activity, etc.) - row hashes
4. Clear normalized tables
5. Re-process same `raw_events` (same order)
6. Capture normalized tables (row hashes)
7. Compare hashes (must match exactly)

**Success Criteria**:
- All normalized row hashes match
- All `event_id` mappings match
- All field values match (no rounding, no truncation)

**Evidence**: `determinism_proof_log.json`

---

### DET-003: Correlation Determinism

**Objective**: Prove that same normalized events produce same incidents (bit-for-bit).

**Test Steps**:
1. Load deterministic normalized events (from DET-002)
2. Process through correlation engine
3. Capture `incidents` table (incident_id, hash)
4. Capture `evidence` table (evidence_id, hash)
5. Clear `incidents` and `evidence` tables
6. Re-process same normalized events (same order)
7. Capture `incidents` and `evidence` tables (hashes)
8. Compare hashes (must match exactly)

**Success Criteria**:
- All `incident_id` values match
- All `confidence_score` values match (if deterministic)
- All `stage` assignments match
- All evidence links match

**Evidence**: `determinism_proof_log.json`

---

### DET-004: Forensics Determinism

**Objective**: Prove that same incidents produce same forensic summaries (bit-for-bit).

**Test Steps**:
1. Load deterministic incidents (from DET-003)
2. Generate forensic summaries
3. Capture summary hashes (JSON, text, graph)
4. Clear forensic summaries
5. Re-generate summaries for same incidents
6. Capture summary hashes
7. Compare hashes (must match exactly)

**Success Criteria**:
- All JSON summary hashes match (canonical JSON)
- All text summary hashes match (character-for-character)
- All graph metadata hashes match

**Evidence**: `determinism_proof_log.json`

---

### REP-001: Normalized Events Replay

**Objective**: Prove that `raw_events` can be replayed to rebuild normalized events identically.

**Test Steps**:
1. Export `raw_events` from production/test DB
2. Export normalized tables (process_activity, file_activity, etc.)
3. Calculate baseline hashes
4. Clear normalized tables (keep `raw_events`)
5. Replay `raw_events` through normalization service
6. Export rebuilt normalized tables
7. Calculate rebuilt hashes
8. Compare hashes (must match exactly)

**Success Criteria**:
- All normalized row hashes match
- All `event_id` mappings match
- All field values match

**Evidence**: `replay_verification_log.json`

---

### REP-002: Incidents Replay

**Objective**: Prove that normalized events can be replayed to rebuild incidents identically.

**Test Steps**:
1. Export normalized events (from REP-001)
2. Export `incidents` table
3. Calculate baseline hashes
4. Clear `incidents` table (keep normalized events)
5. Replay normalized events through correlation engine
6. Export rebuilt `incidents` table
7. Calculate rebuilt hashes
8. Compare hashes (must match exactly)

**Success Criteria**:
- All `incident_id` values match
- All `confidence_score` values match
- All `stage` assignments match

**Evidence**: `replay_verification_log.json`

---

### REP-003: Evidence Replay

**Objective**: Prove that incidents can be replayed to rebuild evidence identically.

**Test Steps**:
1. Export `incidents` table (from REP-002)
2. Export `evidence` table
3. Calculate baseline hashes
4. Clear `evidence` table (keep `incidents`)
5. Rebuild evidence links (if needed)
6. Export rebuilt `evidence` table
7. Calculate rebuilt hashes
8. Compare hashes (must match exactly)

**Success Criteria**:
- All evidence link hashes match
- All `event_id` references match

**Evidence**: `replay_verification_log.json`

---

### REP-004: Forensic Summaries Replay

**Objective**: Prove that incidents can be replayed to rebuild forensic summaries identically.

**Test Steps**:
1. Export `incidents` table (from REP-002)
2. Export forensic summaries (if any)
3. Calculate baseline hashes
4. Clear forensic summaries (keep `incidents`)
5. Re-generate forensic summaries
6. Export rebuilt summaries
7. Calculate rebuilt hashes
8. Compare hashes (must match exactly)

**Success Criteria**:
- All JSON summary hashes match
- All text summary hashes match
- All graph metadata hashes match

**Evidence**: `replay_verification_log.json`

---

### FAIL-001: DB Restart (Mid-Transaction)

**Objective**: Prove that DB restart during transaction does not cause corruption.

**Test Steps**:
1. Start transaction (insert into `raw_events`)
2. Kill database process mid-transaction
3. Restart database
4. Verify transaction rolled back
5. Verify no partial writes
6. Verify event can be re-ingested

**Success Criteria**:
- No corruption in `raw_events` table
- No orphaned rows
- Event can be re-ingested (idempotent)
- Audit log entry for restart

**Evidence**: `failure_injection_results.json`

---

### FAIL-002: Queue Overflow

**Objective**: Prove that queue overflow triggers backpressure without silent loss.

**Test Steps**:
1. Ingest events at rate exceeding processing capacity
2. Fill queue to capacity
3. Verify backpressure mechanism activates
4. Verify events buffered (not dropped silently)
5. Verify audit log entry for queue overflow

**Success Criteria**:
- Queue depth monitored
- Backpressure signal sent to agents
- Events buffered (not dropped)
- Audit log entry created

**Evidence**: `failure_injection_results.json`

---

### FAIL-003: Agent Disconnect

**Objective**: Prove that agent disconnect is detected and logged without corruption.

**Test Steps**:
1. Agent sends events with sequence numbers
2. Simulate agent disconnect (mid-sequence)
3. Agent reconnects with gap in sequence
4. Verify sequence gap detected
5. Verify gap logged in `sequence_gaps` table
6. Verify audit ledger entry created
7. Verify processing continues (fail-open)

**Success Criteria**:
- Sequence gap detected
- Gap logged in `sequence_gaps` table
- Audit ledger entry created
- Processing continues

**Evidence**: `failure_injection_results.json`

---

### FAIL-004: Duplicate Events

**Objective**: Prove that duplicate events are handled idempotently.

**Test Steps**:
1. Ingest event with `event_id` = "test-001"
2. Verify event ingested successfully
3. Ingest same event again (same `event_id`)
4. Verify second ingestion skipped (idempotent)
5. Verify no duplicate rows in `raw_events`
6. Verify audit log entry for duplicate detection

**Success Criteria**:
- First ingestion succeeds
- Second ingestion skipped (idempotent)
- No duplicate rows in `raw_events`
- Audit log entry created

**Evidence**: `failure_injection_results.json`

---

### FAIL-005: Partial Writes

**Objective**: Prove that partial writes are rolled back atomically.

**Test Steps**:
1. Start transaction (insert into `raw_events`)
2. Simulate network failure mid-write
3. Verify transaction rolled back
4. Verify no partial writes
5. Verify event can be re-ingested

**Success Criteria**:
- Transaction rolled back
- No partial writes
- Event can be re-ingested
- Audit log entry for rollback

**Evidence**: `failure_injection_results.json`

---

### SCALE-001: Burst Ingestion (10K/sec)

**Objective**: Prove that system handles burst ingestion (10K events/sec) with acceptable latency.

**Test Steps**:
1. Generate 100K events
2. Ingest at 10K events/sec (burst)
3. Measure latency (p50, p95, p99)
4. Measure backpressure (queue depth)
5. Measure CPU/memory (per service)
6. Measure DB stability (lock contention, WAL growth)

**Success Criteria**:
- Latency: p99 < 1s
- Backpressure: Queue depth < 10K
- CPU: Per-service < 80%
- Memory: Per-service < 2GB
- DB: No lock contention, WAL growth acceptable

**Evidence**: `scale_validation_metrics.json`

---

### SCALE-002: Sustained Load (1K/sec)

**Objective**: Prove that system handles sustained load (1K events/sec) over 1 hour.

**Test Steps**:
1. Generate 1M events
2. Ingest at 1K events/sec (sustained)
3. Measure latency (p50, p95, p99) over 1 hour
4. Measure backpressure (queue depth) over 1 hour
5. Measure CPU/memory (per service) over 1 hour
6. Measure DB stability (lock contention, WAL growth, table bloat)

**Success Criteria**:
- Latency: p99 < 5s
- Backpressure: Queue depth < 1K
- CPU: Per-service < 50%
- Memory: Per-service < 2GB
- DB: No lock contention, WAL growth acceptable, no table bloat

**Evidence**: `scale_validation_metrics.json`

---

### SCALE-003: POC Single-Host Mode

**Objective**: Prove that Core + DPI + Linux Agent can run on same host without conflicts.

**Test Steps**:
1. Deploy Core + DPI + Linux Agent on same host
2. Ingest 100K events
3. Measure resource isolation (CPU, memory, IO)
4. Measure port conflicts
5. Measure performance (latency, throughput)

**Success Criteria**:
- CPU isolation: Per-service CPU usage (no starvation)
- Memory isolation: Per-service memory usage (no OOM)
- IO isolation: Per-service IO usage (no starvation)
- Port conflicts: None
- Performance: Acceptable latency despite co-location

**Evidence**: `scale_validation_metrics.json`

---

### AUDIT-001: Ledger Integrity

**Objective**: Prove that audit ledger maintains hash chain integrity and signature validity.

**Test Steps**:
1. Load audit ledger entries
2. Verify hash chain integrity (prev_entry_hash matches previous entry_hash)
3. Verify signature validity (ed25519 signatures)
4. Verify chronological ordering (timestamp monotonic)

**Success Criteria**:
- All hash chains valid
- All signatures valid
- All timestamps monotonic

**Evidence**: `audit_integrity_verification.json`

---

### AUDIT-002: Coverage Analysis

**Objective**: Prove that all security-relevant actions are logged in audit ledger.

**Test Steps**:
1. Identify all security-relevant actions:
   - Installer actions
   - Service lifecycle events
   - Policy decisions
   - AI model lifecycle actions
   - Playbook execution
   - Forensic access
   - Administrative actions
2. Verify all actions are logged in audit ledger
3. Verify no silent actions

**Success Criteria**:
- 100% coverage of security-relevant actions
- No silent actions

**Evidence**: `audit_coverage_report.json`

---

### AUDIT-003: Compliance Verification

**Objective**: Prove that audit ledger meets compliance requirements (SOC 2, ISO 27001, HIPAA, PCI DSS, GDPR).

**Test Steps**:
1. Verify SOC 2 requirements (access control and audit)
2. Verify ISO 27001 requirements (audit logging)
3. Verify HIPAA requirements (audit trail)
4. Verify PCI DSS requirements (audit logging)
5. Verify GDPR requirements (audit trail)

**Success Criteria**:
- All compliance requirements met
- Audit trail exportable
- Audit trail immutable

**Evidence**: `audit_compliance_report.json`

---

## Test Execution Order

1. **Determinism Tests** (DET-001 through DET-004)
2. **Replay Tests** (REP-001 through REP-004)
3. **Failure Injection Tests** (FAIL-001 through FAIL-005)
4. **Scale Tests** (SCALE-001 through SCALE-003)
5. **Audit Tests** (AUDIT-001 through AUDIT-003)

## Test Status Tracking

| Test ID | Status | Pass/Fail | Notes |
|---------|--------|-----------|-------|
| DET-001 | PENDING | - | - |
| DET-002 | PENDING | - | - |
| DET-003 | PENDING | - | - |
| DET-004 | PENDING | - | - |
| REP-001 | PENDING | - | - |
| REP-002 | PENDING | - | - |
| REP-003 | PENDING | - | - |
| REP-004 | PENDING | - | - |
| FAIL-001 | PENDING | - | - |
| FAIL-002 | PENDING | - | - |
| FAIL-003 | PENDING | - | - |
| FAIL-004 | PENDING | - | - |
| FAIL-005 | PENDING | - | - |
| SCALE-001 | PENDING | - | - |
| SCALE-002 | PENDING | - | - |
| SCALE-003 | PENDING | - | - |
| AUDIT-001 | PENDING | - | - |
| AUDIT-002 | PENDING | - | - |
| AUDIT-003 | PENDING | - | - |

---

**AUTHORITATIVE**: This test matrix is the single authoritative source for GA validation tests.

**STATUS**: Test matrix defined. Ready for test implementation.
