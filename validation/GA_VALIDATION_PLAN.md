# RansomEye v1.0 GA Validation Plan

**AUTHORITATIVE:** Comprehensive validation plan for GA readiness determination

## Overview

This validation plan proves RansomEye is GA-ready through systematic testing across five mandatory validation tracks:
1. **Determinism Proof**: Same inputs → same outputs (bit-for-bit)
2. **Replay & Rehydration**: Rebuild all data from raw_events only
3. **Failure Injection**: Graceful degradation, no corruption
4. **Scale & Stress**: 1M+ events, mixed traffic, co-located deployment
5. **Security & Safety**: Enforcement authority, signed execution, RBAC

## Validation Tracks

### TRACK 1 — DETERMINISM PROOF

**Objective**: Prove that same inputs produce same outputs (bit-for-bit) across all processing stages.

#### Test Scenarios

**DET-001: Detection Determinism**
- **Input**: Deterministic agent telemetry (fixed seed, same order)
- **Process**: Agent → Ingest Service → raw_events
- **Output**: raw_events table (event_id, payload hash)
- **Validation**: Run twice, compare hashes (must match exactly)
- **Pass Criteria**: All event_id values match, all payload hashes match

**DET-002: Normalization Determinism**
- **Input**: Deterministic raw_events (from DET-001)
- **Process**: Normalization Service → normalized tables
- **Output**: process_activity, file_activity, persistence, network_intent (row hashes)
- **Validation**: Run twice, compare hashes (must match exactly)
- **Pass Criteria**: All normalized row hashes match, all event_id mappings match

**DET-003: Correlation Determinism**
- **Input**: Deterministic normalized events (from DET-002)
- **Process**: Correlation Engine → incidents, evidence
- **Output**: incidents table (incident_id, hash), evidence table (evidence_id, hash)
- **Validation**: Run twice, compare hashes (must match exactly)
- **Pass Criteria**: All incident_id values match, all confidence_score values match, all stage assignments match

**DET-004: Forensics Determinism**
- **Input**: Deterministic incidents (from DET-003)
- **Process**: Forensic Summarization → summaries
- **Output**: JSON summary (canonical hash), text summary (character hash), graph metadata (hash)
- **Validation**: Run twice, compare hashes (must match exactly)
- **Pass Criteria**: All JSON summary hashes match, all text summary hashes match, all graph metadata hashes match

**DET-005: LLM Summarization Determinism**
- **Input**: Deterministic incidents (from DET-003)
- **Process**: LLM Summarizer → summaries (SOC, Executive, Legal)
- **Output**: Summary JSON (canonical hash), PDF (hash), HTML (hash)
- **Validation**: Run twice, compare hashes (must match exactly)
- **Pass Criteria**: All summary hashes match (temperature=0.0, fixed seed)

#### Metrics Collected

- **Hash Comparison**: Total comparisons, matches, mismatches
- **Execution Time**: Per-run execution time (for performance baseline)
- **Memory Usage**: Per-run memory usage (for resource baseline)

#### Pass/Fail Criteria

**PASS**: All hashes match exactly (100% match rate)
**FAIL**: Any hash mismatch (0% tolerance)

#### Evidence Artifacts

- `determinism_proof_run1.json`: First run hashes
- `determinism_proof_run2.json`: Second run hashes
- `determinism_proof_log.json`: Comparison results
- `determinism_proof_report.md`: Human-readable report

---

### TRACK 2 — REPLAY & REHYDRATION

**Objective**: Prove that all downstream data can be rebuilt from raw_events only, with no divergence.

#### Test Scenarios

**REP-001: Normalized Events Replay**
- **Baseline**: Export raw_events and normalized tables from production/test DB
- **Clear**: Clear all normalized tables (keep raw_events)
- **Replay**: Replay raw_events through normalization service
- **Compare**: Compare baseline vs rebuilt (hashes must match exactly)
- **Pass Criteria**: All normalized row hashes match, all event_id mappings match

**REP-002: Incidents Replay**
- **Baseline**: Export normalized events and incidents from production/test DB
- **Clear**: Clear incidents table (keep normalized events)
- **Replay**: Replay normalized events through correlation engine
- **Compare**: Compare baseline vs rebuilt (hashes must match exactly)
- **Pass Criteria**: All incident_id values match, all confidence_score values match, all stage assignments match

**REP-003: Evidence Replay**
- **Baseline**: Export incidents and evidence from production/test DB
- **Clear**: Clear evidence table (keep incidents)
- **Replay**: Rebuild evidence links (if needed)
- **Compare**: Compare baseline vs rebuilt (hashes must match exactly)
- **Pass Criteria**: All evidence link hashes match, all event_id references match

**REP-004: Forensic Summaries Replay**
- **Baseline**: Export incidents and forensic summaries from production/test DB
- **Clear**: Clear forensic summaries (keep incidents)
- **Replay**: Re-generate forensic summaries
- **Compare**: Compare baseline vs rebuilt (hashes must match exactly)
- **Pass Criteria**: All JSON summary hashes match, all text summary hashes match, all graph metadata hashes match

**REP-005: Killchain Replay**
- **Baseline**: Export incidents and killchain data from production/test DB
- **Clear**: Clear killchain data (keep incidents)
- **Replay**: Rebuild killchain from incidents
- **Compare**: Compare baseline vs rebuilt (hashes must match exactly)
- **Pass Criteria**: All killchain stage hashes match, all evidence links match

#### Metrics Collected

- **Replay Time**: Time to replay all data
- **Hash Comparison**: Total comparisons, matches, mismatches
- **Data Volume**: Number of rows replayed, total data size

#### Pass/Fail Criteria

**PASS**: All hashes match exactly (100% match rate, 0% divergence)
**FAIL**: Any hash mismatch (0% tolerance)

#### Evidence Artifacts

- `replay_baseline.json`: Baseline data hashes
- `replay_rebuilt.json`: Rebuilt data hashes
- `replay_verification_log.json`: Comparison results
- `replay_verification_report.md`: Human-readable report

---

### TRACK 3 — FAILURE INJECTION

**Objective**: Prove that system handles failures gracefully without corruption or silent loss.

#### Test Scenarios

**FAIL-001: DB Connection Loss (Mid-Transaction)**
- **Inject**: Kill database connection during transaction (insert into raw_events)
- **Verify**: Transaction rolled back, no partial writes
- **Verify**: Event can be re-ingested (idempotent)
- **Verify**: Audit log entry for connection loss
- **Pass Criteria**: No corruption, no orphaned rows, idempotent re-ingestion

**FAIL-002: Agent Disconnect (Sequence Gaps)**
- **Inject**: Agent sends events with sequence numbers, disconnect mid-sequence
- **Verify**: Sequence gap detected and logged in sequence_gaps table
- **Verify**: Audit ledger entry created
- **Verify**: Processing continues (fail-open)
- **Pass Criteria**: Gap detected, gap logged, processing continues

**FAIL-003: Queue Overflow (Backpressure)**
- **Inject**: Ingest events at rate exceeding processing capacity (fill queue to capacity)
- **Verify**: Backpressure mechanism activates
- **Verify**: Events buffered (not dropped silently)
- **Verify**: Audit log entry for queue overflow
- **Pass Criteria**: Backpressure activated, events buffered, no silent loss

**FAIL-004: Duplicate Events (Idempotency)**
- **Inject**: Ingest same event twice (same event_id)
- **Verify**: First ingestion succeeds
- **Verify**: Second ingestion skipped (idempotent)
- **Verify**: No duplicate rows in raw_events
- **Verify**: Audit log entry for duplicate detection
- **Pass Criteria**: Idempotent handling, no duplicates, duplicate logged

**FAIL-005: Partial Writes (Atomicity)**
- **Inject**: Simulate partial write (network failure mid-write)
- **Verify**: Transaction rolled back
- **Verify**: No partial writes
- **Verify**: Event can be re-ingested
- **Verify**: Audit log entry for rollback
- **Pass Criteria**: Atomicity maintained, no partial writes, re-ingestion possible

**FAIL-006: Database Restart (Mid-Processing)**
- **Inject**: Kill database process during active processing
- **Verify**: Database restarts cleanly
- **Verify**: No corruption in any table
- **Verify**: Processing resumes correctly
- **Verify**: Audit log entry for restart
- **Pass Criteria**: Clean restart, no corruption, processing resumes

#### Metrics Collected

- **Corruption Check**: Number of corrupted rows, orphaned rows
- **Silent Loss Check**: Number of events lost, number of events buffered
- **Degradation Check**: Processing time, error rate, recovery time

#### Pass/Fail Criteria

**PASS**: No corruption, no silent loss, correct degradation (graceful failure)
**FAIL**: Any corruption, any silent loss, incorrect degradation (catastrophic failure)

#### Evidence Artifacts

- `failure_injection_scenarios.json`: Scenario definitions
- `failure_injection_results.json`: Test results
- `failure_injection_report.md`: Human-readable report

---

### TRACK 4 — SCALE & STRESS

**Objective**: Prove that system handles 1M+ events with acceptable latency, no deadlocks, no data loss.

#### Test Scenarios

**SCALE-001: Burst Ingestion (10K events/sec)**
- **Load**: Generate 100K events, ingest at 10K events/sec (burst)
- **Measure**: Latency (p50, p95, p99), backpressure (queue depth), CPU/memory (per service), DB stability (lock contention, WAL growth)
- **Pass Criteria**: p99 latency < 1s, queue depth < 10K, CPU < 80%, memory < 2GB, no lock contention

**SCALE-002: Sustained Load (1K events/sec)**
- **Load**: Generate 1M events, ingest at 1K events/sec (sustained, 1 hour)
- **Measure**: Latency (p50, p95, p99), backpressure (queue depth), CPU/memory (per service), DB stability (lock contention, WAL growth, table bloat)
- **Pass Criteria**: p99 latency < 5s, queue depth < 1K, CPU < 50%, memory < 2GB, no lock contention, no table bloat

**SCALE-003: Mixed Traffic (ETW + DPI + Agent)**
- **Load**: Generate 100K events (33K ETW, 33K DPI, 34K Agent), ingest concurrently
- **Measure**: Latency (p50, p95, p99), backpressure (queue depth), CPU/memory (per service), DB stability (lock contention)
- **Pass Criteria**: p99 latency < 2s, queue depth < 5K, CPU < 70%, memory < 2GB, no lock contention

**SCALE-004: Co-located Deployment (POC Single-Host)**
- **Load**: Run Core + DPI + Linux Agent on same host, ingest 100K events
- **Measure**: Resource isolation (CPU, memory, IO), port conflicts, performance (latency, throughput)
- **Pass Criteria**: CPU isolation (no starvation), memory isolation (no OOM), IO isolation (no starvation), no port conflicts, acceptable latency

**SCALE-005: 1M+ Event Ingestion**
- **Load**: Generate 1,000,000 events, ingest at sustained rate (1K/sec)
- **Measure**: Total ingestion time, latency (p50, p95, p99), data loss (if any), DB stability (lock contention, WAL growth, table bloat)
- **Pass Criteria**: All events ingested, p99 latency < 5s, no data loss, no lock contention, acceptable WAL growth, no table bloat

#### Metrics Collected

- **Latency**: p50, p95, p99 (milliseconds)
- **Backpressure**: Queue depth (events)
- **CPU**: Per-service CPU usage (percentage)
- **Memory**: Per-service memory usage (GB)
- **DB Stability**: Lock contention (count), WAL growth (MB), table bloat (percentage)
- **Data Loss**: Number of events lost (must be 0)

#### Pass/Fail Criteria

**PASS**: All metrics within targets, no deadlocks, no unbounded latency, no data loss
**FAIL**: Any metric exceeds target, any deadlock, unbounded latency, any data loss

#### Evidence Artifacts

- `scale_validation_metrics.json`: All metrics
- `scale_validation_report.md`: Human-readable report
- `scale_validation_charts/`: Performance charts (if applicable)

---

### TRACK 5 — SECURITY & SAFETY

**Objective**: Prove that system enforces security and safety requirements (no enforcement without authority, no unsigned execution, no cross-module DB access, RBAC enforcement).

#### Test Scenarios

**SEC-001: Enforcement Authority Verification**
- **Test**: Attempt enforcement action without human authority approval
- **Verify**: Enforcement blocked, audit log entry created
- **Verify**: Only authorized actions execute
- **Pass Criteria**: No enforcement without authority, all enforcement actions logged

**SEC-002: Signed Execution Verification**
- **Test**: Attempt execution of unsigned command/action
- **Verify**: Unsigned execution blocked, audit log entry created
- **Verify**: Only signed executions allowed
- **Pass Criteria**: No unsigned execution, all executions signed

**SEC-003: Cross-Module DB Access Verification**
- **Test**: Attempt direct table reads (bypass views)
- **Verify**: Direct table access blocked (RBAC enforcement)
- **Verify**: Only approved views accessible
- **Pass Criteria**: No direct table reads, all access via views

**SEC-004: RBAC Enforcement Verification**
- **Test**: Attempt unauthorized DB operations (wrong role)
- **Verify**: Unauthorized operations blocked (RBAC enforcement)
- **Verify**: Only authorized operations allowed
- **Pass Criteria**: RBAC enforced, no unauthorized operations

**SEC-005: Data-Plane Access Control Verification**
- **Test**: Verify write/read ownership matrix compliance
- **Verify**: Agents never read DB (write-only)
- **Verify**: DPI never reads agent tables
- **Verify**: Core reads via views only
- **Pass Criteria**: All access control rules enforced

**SEC-006: Audit Ledger Integrity Verification**
- **Test**: Verify audit ledger hash chain integrity
- **Verify**: All entries signed (ed25519)
- **Verify**: All entries chronologically ordered
- **Verify**: No tampering (hash chain intact)
- **Pass Criteria**: Hash chain intact, all entries signed, chronological order maintained

#### Metrics Collected

- **Enforcement Authority**: Number of unauthorized enforcement attempts, number of authorized enforcement actions
- **Signed Execution**: Number of unsigned execution attempts, number of signed executions
- **Cross-Module Access**: Number of direct table access attempts, number of view accesses
- **RBAC Enforcement**: Number of unauthorized operation attempts, number of authorized operations
- **Audit Integrity**: Number of hash chain violations, number of signature failures

#### Pass/Fail Criteria

**PASS**: All security requirements enforced, no violations, all actions logged
**FAIL**: Any security violation, any unauthorized action, any missing audit log

#### Evidence Artifacts

- `security_verification_results.json`: Test results
- `security_verification_report.md`: Human-readable report
- `rbac_enforcement_log.json`: RBAC enforcement log
- `audit_integrity_verification.json`: Audit integrity verification

---

## Overall GA Readiness Verdict

### Validation Summary

| Track | Tests | Status | Evidence |
|-------|-------|--------|----------|
| **TRACK 1: Determinism** | 5 tests | ⬜ PASS / ⬜ FAIL | `determinism_proof_log.json` |
| **TRACK 2: Replay** | 5 tests | ⬜ PASS / ⬜ FAIL | `replay_verification_log.json` |
| **TRACK 3: Failure Injection** | 6 tests | ⬜ PASS / ⬜ FAIL | `failure_injection_results.json` |
| **TRACK 4: Scale & Stress** | 5 tests | ⬜ PASS / ⬜ FAIL | `scale_validation_metrics.json` |
| **TRACK 5: Security & Safety** | 6 tests | ⬜ PASS / ⬜ FAIL | `security_verification_results.json` |

**Total Tests**: 27 tests (all P0)

### GA Readiness Criteria

**GA-READY** if:
- ✅ All 27 tests PASS
- ✅ All evidence artifacts generated
- ✅ All validation reports complete
- ✅ No critical failures
- ✅ All security requirements met
- ✅ All performance targets met

**NOT GA-READY** if:
- ❌ Any test FAILS
- ❌ Any evidence artifact missing
- ❌ Any critical failure
- ❌ Any security violation
- ❌ Any performance target missed

### Explicit GA Verdict

**Status**: ⬜ GA-READY / ⬜ NOT GA-READY

**Rationale**:
- [ ] All 27 tests pass
- [ ] All evidence artifacts generated
- [ ] All validation reports complete
- [ ] No critical failures
- [ ] All security requirements met
- [ ] All performance targets met

**Blockers**:
- [List any blockers preventing GA]

**Non-Blockers**:
- [List any non-blockers (acceptable risks)]

---

## Test Execution Plan

### Phase 1: Determinism Proof (TRACK 1)
1. Generate deterministic test events
2. Run first pass (capture hashes)
3. Run second pass (capture hashes)
4. Compare hashes (must match exactly)
5. Generate determinism proof log

### Phase 2: Replay & Rehydration (TRACK 2)
1. Export baseline data (raw_events, normalized, incidents, summaries)
2. Clear downstream tables
3. Replay raw_events through full pipeline
4. Compare baseline vs rebuilt (must match exactly)
5. Generate replay verification log

### Phase 3: Failure Injection (TRACK 3)
1. Execute each failure scenario
2. Verify no corruption, no silent loss, correct degradation
3. Generate failure injection results
4. Generate failure injection report

### Phase 4: Scale & Stress (TRACK 4)
1. Execute each scale scenario
2. Measure latency, backpressure, CPU/memory, DB stability
3. Generate scale validation metrics
4. Generate scale validation report

### Phase 5: Security & Safety (TRACK 5)
1. Execute each security test
2. Verify enforcement authority, signed execution, RBAC, access control
3. Generate security verification results
4. Generate security verification report

### Phase 6: GA Readiness Assessment
1. Review all test results
2. Generate overall GA readiness verdict
3. Generate signed validation report (PDF/JSON)
4. Document residual risks (if any)

---

## Evidence Artifacts Summary

### Determinism Proof
- `determinism_proof_run1.json`
- `determinism_proof_run2.json`
- `determinism_proof_log.json`
- `determinism_proof_report.md`

### Replay & Rehydration
- `replay_baseline.json`
- `replay_rebuilt.json`
- `replay_verification_log.json`
- `replay_verification_report.md`

### Failure Injection
- `failure_injection_scenarios.json`
- `failure_injection_results.json`
- `failure_injection_report.md`

### Scale & Stress
- `scale_validation_metrics.json`
- `scale_validation_report.md`
- `scale_validation_charts/`

### Security & Safety
- `security_verification_results.json`
- `security_verification_report.md`
- `rbac_enforcement_log.json`
- `audit_integrity_verification.json`

---

**AUTHORITATIVE**: This validation plan is the single authoritative source for GA validation.

**STATUS**: Validation plan defined. Ready for test execution.
