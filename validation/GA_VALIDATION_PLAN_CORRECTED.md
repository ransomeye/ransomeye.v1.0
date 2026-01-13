# RansomEye v1.0 GA Validation Plan (Corrected)

**AUTHORITATIVE:** Corrected validation plan for GA readiness determination

## Overview

This corrected validation plan proves RansomEye is GA-ready through systematic testing across six mandatory validation tracks:
1. **Determinism (Corrected)**: Hash equality for non-LLM, semantic equivalence for LLM
2. **Replay & Rehydration (Split Modes)**: Identity replay (bit-exact) and Evolution replay (semantic)
3. **Failure Injection**: Graceful degradation, no corruption
4. **Scale & Stress (Realistic)**: 1M+ events with locked latency targets
5. **Security & Safety**: Enforcement authority, RBAC, access control
6. **Agent Reality Check (New)**: Real agent vs simulator equivalence

## Validation Tracks

### TRACK 1 — DETERMINISM (CORRECTED)

**Objective**: Prove that same inputs produce same outputs, with correct validation for LLM vs non-LLM paths.

#### Test Scenarios

**DET-001: Detection Determinism**
- **Input**: Deterministic agent telemetry (fixed seed, same order)
- **Process**: Agent → Ingest Service → raw_events
- **Output**: raw_events table (event_id, payload hash)
- **Validation**: Run twice, compare hashes (must match exactly)
- **Pass Criteria**: All event_id values match, all payload hashes match (bit-exact)
- **Type**: Non-LLM path → hash equality required

**DET-002: Normalization Determinism**
- **Input**: Deterministic raw_events (from DET-001)
- **Process**: Normalization Service → normalized tables
- **Output**: process_activity, file_activity, persistence, network_intent (row hashes)
- **Validation**: Run twice, compare hashes (must match exactly)
- **Pass Criteria**: All normalized row hashes match, all event_id mappings match (bit-exact)
- **Type**: Non-LLM path → hash equality required

**DET-003: Correlation Determinism**
- **Input**: Deterministic normalized events (from DET-002)
- **Process**: Correlation Engine → incidents, evidence
- **Output**: incidents table (incident_id, hash), evidence table (evidence_id, hash)
- **Validation**: Run twice, compare hashes (must match exactly)
- **Pass Criteria**: All incident_id values match, all confidence_score values match, all stage assignments match (bit-exact)
- **Type**: Non-LLM path → hash equality required

**DET-004: Forensic Summarization Determinism**
- **Input**: Deterministic incidents (from DET-003)
- **Process**: Forensic Summarization → summaries
- **Output**: JSON summary (canonical hash), text summary (character hash), graph metadata (hash)
- **Validation**: Run twice, compare hashes (must match exactly)
- **Pass Criteria**: All JSON summary hashes match, all text summary hashes match, all graph metadata hashes match (bit-exact)
- **Type**: Non-LLM path → hash equality required

**DET-005: LLM Semantic Determinism**
- **Input**: Deterministic incidents (from DET-003)
- **Process**: LLM Summarizer → summaries (SOC, Executive, Legal)
- **Output**: Summary JSON (schema validation), PDF (structure validation), HTML (structure validation)
- **Validation**: Run twice, compare schema + semantic equivalence (NOT hash equality)
- **Pass Criteria**:
  - Schema equivalence: All required fields present, all field types match
  - Semantic equivalence: Same facts, same evidence references, same structure
  - Forbidden language checks: No speculation, no adjectives, no mitigation advice
  - Structure/ordering: Same section order, same claim ordering
  - Exclusions: No hallucinated content, no unsupported claims
- **Type**: LLM path → schema + semantic equivalence only (hash equality NOT required)

#### Metrics Collected

- **Non-LLM Paths**: Hash comparison (matches/mismatches), execution time, memory usage
- **LLM Paths**: Schema validation (pass/fail), semantic equivalence score, forbidden language violations, structure/ordering match

#### Pass/Fail Criteria

**Non-LLM Paths (DET-001 through DET-004)**:
- **PASS**: All hashes match exactly (100% match rate, 0% tolerance)
- **FAIL**: Any hash mismatch

**LLM Paths (DET-005)**:
- **PASS**: Schema equivalence + semantic equivalence + no forbidden language + structure/ordering match
- **FAIL**: Schema mismatch OR semantic mismatch OR forbidden language detected OR structure/ordering mismatch

#### Evidence Artifacts

- `determinism_proof_run1.json`: First run outputs (hashes for non-LLM, schemas for LLM)
- `determinism_proof_run2.json`: Second run outputs
- `determinism_proof_log.json`: Comparison results
- `determinism_proof_report.md`: Human-readable report

---

### TRACK 2 — REPLAY & REHYDRATION (SPLIT MODES)

**Objective**: Prove that all downstream data can be rebuilt from raw_events, with two distinct replay modes.

#### Test Scenarios

**REP-A: Identity Replay (Bit-Exact)**
- **Mode**: Same code, same schemas
- **Baseline**: Export raw_events and all downstream data from production/test DB
- **Clear**: Clear all downstream tables (keep raw_events)
- **Replay**: Replay raw_events through full pipeline (same code version)
- **Compare**: Compare baseline vs rebuilt (hashes must match exactly)
- **Pass Criteria**: All hashes match exactly (bit-exact, 100% match rate)
- **Tests**:
  - REP-A-001: Normalized Events Replay
  - REP-A-002: Incidents Replay
  - REP-A-003: Evidence Replay
  - REP-A-004: Forensic Summaries Replay
  - REP-A-005: Killchain Replay

**REP-B: Evolution Replay (Semantic Equivalence)**
- **Mode**: New code version, same inputs
- **Baseline**: Export raw_events and all downstream data from production/test DB
- **Clear**: Clear all downstream tables (keep raw_events)
- **Replay**: Replay raw_events through full pipeline (new code version)
- **Compare**: Compare baseline vs rebuilt (semantic equivalence required, hash equality NOT required)
- **Pass Criteria**:
  - Schema equivalence: All required fields present, all field types match
  - Semantic equivalence: Same facts, same evidence references, same structure
  - Forbidden language checks: No speculation, no adjectives, no mitigation advice
  - Structure/ordering: Same section order, same claim ordering
- **Tests**:
  - REP-B-001: Normalized Events Replay (semantic)
  - REP-B-002: Incidents Replay (semantic)
  - REP-B-003: Evidence Replay (semantic)
  - REP-B-004: Forensic Summaries Replay (semantic)
  - REP-B-005: LLM Summaries Replay (semantic)

#### Metrics Collected

- **REP-A (Identity)**: Replay time, hash comparison (matches/mismatches), data volume
- **REP-B (Evolution)**: Replay time, schema validation, semantic equivalence score, forbidden language violations

#### Pass/Fail Criteria

**REP-A (Identity Replay)**:
- **PASS**: All hashes match exactly (bit-exact, 100% match rate)
- **FAIL**: Any hash mismatch

**REP-B (Evolution Replay)**:
- **PASS**: Schema equivalence + semantic equivalence + no forbidden language + structure/ordering match
- **FAIL**: Schema mismatch OR semantic mismatch OR forbidden language detected OR structure/ordering mismatch

#### Evidence Artifacts

- `replay_identity_baseline.json`: Baseline data hashes (REP-A)
- `replay_identity_rebuilt.json`: Rebuilt data hashes (REP-A)
- `replay_evolution_baseline.json`: Baseline data schemas (REP-B)
- `replay_evolution_rebuilt.json`: Rebuilt data schemas (REP-B)
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
- **Pass Criteria**: No corruption, no orphaned rows, idempotent re-ingestion, explicit degradation logged

**FAIL-002: Agent Disconnect (Sequence Gaps)**
- **Inject**: Agent sends events with sequence numbers, disconnect mid-sequence
- **Verify**: Sequence gap detected and logged in sequence_gaps table
- **Verify**: Audit ledger entry created
- **Verify**: Processing continues (fail-open)
- **Pass Criteria**: Gap detected, gap logged, processing continues, explicit degradation logged

**FAIL-003: Queue Overflow (Backpressure)**
- **Inject**: Ingest events at rate exceeding processing capacity (fill queue to capacity)
- **Verify**: Backpressure mechanism activates
- **Verify**: Events buffered (not dropped silently)
- **Verify**: Audit log entry for queue overflow
- **Pass Criteria**: Backpressure activated, events buffered, no silent loss, explicit degradation logged

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
- **Pass Criteria**: Atomicity maintained, no partial writes, re-ingestion possible, explicit degradation logged

**FAIL-006: Database Restart (Mid-Processing)**
- **Inject**: Kill database process during active processing
- **Verify**: Database restarts cleanly
- **Verify**: No corruption in any table
- **Verify**: Processing resumes correctly
- **Verify**: Audit log entry for restart
- **Pass Criteria**: Clean restart, no corruption, processing resumes, explicit degradation logged

#### Metrics Collected

- **Corruption Check**: Number of corrupted rows, orphaned rows
- **Silent Loss Check**: Number of events lost, number of events buffered
- **Degradation Check**: Processing time, error rate, recovery time, explicit degradation logs

#### Pass/Fail Criteria

**PASS**: No corruption, no silent loss, explicit degradation only (all failures logged)
**FAIL**: Any corruption, any silent loss, incorrect degradation (catastrophic failure)

#### Evidence Artifacts

- `failure_injection_scenarios.json`: Scenario definitions
- `failure_injection_results.json`: Test results
- `failure_injection_report.md`: Human-readable report

---

### TRACK 4 — SCALE & STRESS (REALISTIC)

**Objective**: Prove that system handles 1M+ events with acceptable latency (locked targets), no deadlocks, no data loss.

#### Test Scenarios

**SCALE-001: Burst Ingestion**
- **Load**: Generate 100K events, ingest at 10K events/sec (burst)
- **Measure**: Latency (p50, p95, p99), backpressure (queue depth), CPU/memory (per service), DB stability (lock contention, WAL growth)
- **Pass Criteria**: 
  - Latency: p50 < 1s, p95 < 3s, p99 < 5s (LOCKED)
  - Backpressure: Queue depth < 10K
  - CPU: Per-service < 80%
  - Memory: Per-service < 2GB
  - DB: No lock contention, WAL growth acceptable

**SCALE-002: Sustained Load (1M+ Events)**
- **Load**: Generate 1,000,000 events, ingest at 1K events/sec (sustained, 1 hour)
- **Measure**: Latency (p50, p95, p99), backpressure (queue depth), CPU/memory (per service), DB stability (lock contention, WAL growth, table bloat)
- **Pass Criteria**:
  - Latency: p50 < 1s, p95 < 3s, p99 < 5s (LOCKED)
  - Backpressure: Queue depth < 1K
  - CPU: Per-service < 50%
  - Memory: Per-service < 2GB
  - DB: No lock contention, WAL growth acceptable, no table bloat
  - Data Loss: 0 events lost

**SCALE-003: Mixed Traffic (ETW + DPI + Agent)**
- **Load**: Generate 100K events (33K ETW, 33K DPI, 34K Agent), ingest concurrently
- **Measure**: Latency (p50, p95, p99), backpressure (queue depth), CPU/memory (per service), DB stability (lock contention)
- **Pass Criteria**:
  - Latency: p50 < 1s, p95 < 3s, p99 < 5s (LOCKED)
  - Backpressure: Queue depth < 5K
  - CPU: Per-service < 70%
  - Memory: Per-service < 2GB
  - DB: No lock contention

**SCALE-004: Co-located Deployment (POC Single-Host)**
- **Load**: Run Core + DPI + Linux Agent on same host, ingest 100K events
- **Measure**: Resource isolation (CPU, memory, IO), port conflicts, performance (latency, throughput)
- **Pass Criteria**:
  - Latency: p50 < 1s, p95 < 3s, p99 < 5s (LOCKED)
  - CPU isolation: Per-service CPU usage (no starvation)
  - Memory isolation: Per-service memory usage (no OOM)
  - IO isolation: Per-service IO usage (no starvation)
  - Port conflicts: None

**SCALE-005: Backpressure Recovery**
- **Load**: Ingest events at rate exceeding capacity, trigger backpressure, reduce rate, verify recovery
- **Measure**: Backpressure activation time, recovery time, data loss (must be 0)
- **Pass Criteria**:
  - Backpressure activates correctly
  - Recovery time < 30 seconds
  - Data loss: 0 events lost
  - Latency returns to targets: p50 < 1s, p95 < 3s, p99 < 5s (LOCKED)

#### Metrics Collected

- **Latency**: p50, p95, p99 (milliseconds) - LOCKED TARGETS
- **Backpressure**: Queue depth (events), activation time, recovery time
- **CPU**: Per-service CPU usage (percentage)
- **Memory**: Per-service memory usage (GB)
- **DB Stability**: Lock contention (count), WAL growth (MB), table bloat (percentage)
- **Data Loss**: Number of events lost (must be 0)

#### Pass/Fail Criteria

**PASS**: All latency targets met (LOCKED), all metrics within targets, no deadlocks, no unbounded latency, no data loss
**FAIL**: Any latency target missed (LOCKED), any metric exceeds target, any deadlock, unbounded latency, any data loss

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

**SEC-003: No Direct Table Access Verification**
- **Test**: Attempt direct table reads (bypass views)
- **Verify**: Direct table access blocked (RBAC enforcement)
- **Verify**: Only approved views accessible
- **Pass Criteria**: No direct table reads, all access via views

**SEC-004: RBAC Enforcement Verification**
- **Test**: Attempt unauthorized DB operations (wrong role)
- **Verify**: Unauthorized operations blocked (RBAC enforcement)
- **Verify**: Only authorized operations allowed
- **Pass Criteria**: RBAC enforced, no unauthorized operations

**SEC-005: Data-Plane Ownership Enforcement Verification**
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

### TRACK 6 — AGENT REALITY CHECK (NEW)

**Objective**: Prove that real agents (Linux, Windows) produce structurally and semantically equivalent output to simulators, with no simulator-only assumptions.

#### Test Scenarios

**AGENT-001: Linux Real Agent vs Simulator**
- **Test**: Run real Linux agent and simulator with same inputs
- **Compare**: Structural equivalence (same event schema, same field types)
- **Compare**: Semantic equivalence (same facts, same evidence references)
- **Verify**: No simulator-only assumptions (real agent must work identically)
- **Pass Criteria**: Structural equivalence + semantic equivalence + no simulator-only assumptions

**AGENT-002: Windows Real Agent vs Simulator**
- **Test**: Run real Windows agent (ETW) and simulator with same inputs
- **Compare**: Structural equivalence (same event schema, same field types)
- **Compare**: Semantic equivalence (same facts, same evidence references)
- **Verify**: No simulator-only assumptions (real agent must work identically)
- **Pass Criteria**: Structural equivalence + semantic equivalence + no simulator-only assumptions

#### Metrics Collected

- **Structural Equivalence**: Schema match rate, field type match rate
- **Semantic Equivalence**: Fact match rate, evidence reference match rate
- **Simulator Assumptions**: Number of simulator-only assumptions detected

#### Pass/Fail Criteria

**PASS**: Structural equivalence + semantic equivalence + no simulator-only assumptions
**FAIL**: Structural mismatch OR semantic mismatch OR simulator-only assumptions detected

#### Evidence Artifacts

- `agent_reality_check_results.json`: Test results
- `agent_reality_check_report.md`: Human-readable report
- `agent_structural_comparison.json`: Structural comparison results
- `agent_semantic_comparison.json`: Semantic comparison results

---

## Overall GA Readiness Verdict

### Validation Summary

| Track | Tests | Status | Evidence |
|-------|-------|--------|----------|
| **TRACK 1: Determinism (Corrected)** | 5 tests | ⬜ PASS / ⬜ FAIL | `determinism_proof_log.json` |
| **TRACK 2: Replay (Split Modes)** | 10 tests (5 REP-A + 5 REP-B) | ⬜ PASS / ⬜ FAIL | `replay_verification_log.json` |
| **TRACK 3: Failure Injection** | 6 tests | ⬜ PASS / ⬜ FAIL | `failure_injection_results.json` |
| **TRACK 4: Scale & Stress (Realistic)** | 5 tests | ⬜ PASS / ⬜ FAIL | `scale_validation_metrics.json` |
| **TRACK 5: Security & Safety** | 6 tests | ⬜ PASS / ⬜ FAIL | `security_verification_results.json` |
| **TRACK 6: Agent Reality Check** | 2 tests | ⬜ PASS / ⬜ FAIL | `agent_reality_check_results.json` |

**Total Tests**: 34 tests (all P0)

### GA Readiness Criteria

**GA-READY** if:
- ✅ All 34 tests PASS
- ✅ All evidence artifacts generated
- ✅ All validation reports complete
- ✅ No critical failures
- ✅ All security requirements met
- ✅ All performance targets met (LOCKED latency targets)
- ✅ LLM semantic determinism validated (not hash equality)
- ✅ Both replay modes pass (Identity + Evolution)
- ✅ Agent reality check passes (no simulator-only assumptions)

**NOT GA-READY** if:
- ❌ Any test FAILS
- ❌ Any evidence artifact missing
- ❌ Any critical failure
- ❌ Any security violation
- ❌ Any performance target missed (LOCKED latency targets)
- ❌ LLM semantic determinism fails
- ❌ Either replay mode fails
- ❌ Agent reality check fails

### Explicit GA Verdict

**Status**: ⬜ GA-READY / ⬜ NOT GA-READY

**Rationale**:
- [ ] All 34 tests pass
- [ ] All evidence artifacts generated
- [ ] All validation reports complete
- [ ] No critical failures
- [ ] All security requirements met
- [ ] All performance targets met (LOCKED: p50 < 1s, p95 < 3s, p99 < 5s)
- [ ] LLM semantic determinism validated (schema + semantic equivalence)
- [ ] Identity replay passes (bit-exact hashes)
- [ ] Evolution replay passes (semantic equivalence)
- [ ] Agent reality check passes (no simulator-only assumptions)

**Blockers**:
- [List any blockers preventing GA]

**Non-Blockers**:
- [List any non-blockers (acceptable risks)]

---

## Test Execution Plan

### Phase 1: Determinism Proof (TRACK 1)
1. Generate deterministic test events
2. Run first pass (capture hashes for non-LLM, schemas for LLM)
3. Run second pass (capture hashes for non-LLM, schemas for LLM)
4. Compare:
   - Non-LLM: Hash equality (bit-exact)
   - LLM: Schema + semantic equivalence (NOT hash equality)
5. Generate determinism proof log

### Phase 2: Replay & Rehydration (TRACK 2)
1. **REP-A (Identity Replay)**:
   - Export baseline data (raw_events, normalized, incidents, summaries)
   - Clear downstream tables
   - Replay raw_events through full pipeline (same code)
   - Compare baseline vs rebuilt (bit-exact hashes)
2. **REP-B (Evolution Replay)**:
   - Export baseline data (raw_events, normalized, incidents, summaries)
   - Clear downstream tables
   - Replay raw_events through full pipeline (new code version)
   - Compare baseline vs rebuilt (semantic equivalence, NOT hash equality)
3. Generate replay verification log

### Phase 3: Failure Injection (TRACK 3)
1. Execute each failure scenario
2. Verify no corruption, no silent loss, explicit degradation only
3. Generate failure injection results
4. Generate failure injection report

### Phase 4: Scale & Stress (TRACK 4)
1. Execute each scale scenario
2. Measure latency (p50, p95, p99) - LOCKED TARGETS
3. Measure backpressure, CPU/memory, DB stability
4. Verify all latency targets met (LOCKED: p50 < 1s, p95 < 3s, p99 < 5s)
5. Generate scale validation metrics
6. Generate scale validation report

### Phase 5: Security & Safety (TRACK 5)
1. Execute each security test
2. Verify enforcement authority, signed execution, RBAC, access control
3. Generate security verification results
4. Generate security verification report

### Phase 6: Agent Reality Check (TRACK 6)
1. Run real Linux agent and simulator (same inputs)
2. Run real Windows agent and simulator (same inputs)
3. Compare structural and semantic equivalence
4. Verify no simulator-only assumptions
5. Generate agent reality check results
6. Generate agent reality check report

### Phase 7: GA Readiness Assessment
1. Review all test results
2. Generate overall GA readiness verdict
3. Generate signed validation report (PDF/JSON)
4. Document residual risks (if any)

---

## Evidence Artifacts Summary

### Determinism Proof
- `determinism_proof_run1.json`: First run outputs (hashes for non-LLM, schemas for LLM)
- `determinism_proof_run2.json`: Second run outputs
- `determinism_proof_log.json`: Comparison results
- `determinism_proof_report.md`: Human-readable report

### Replay & Rehydration
- `replay_identity_baseline.json`: Baseline data hashes (REP-A)
- `replay_identity_rebuilt.json`: Rebuilt data hashes (REP-A)
- `replay_evolution_baseline.json`: Baseline data schemas (REP-B)
- `replay_evolution_rebuilt.json`: Rebuilt data schemas (REP-B)
- `replay_verification_log.json`: Comparison results
- `replay_verification_report.md`: Human-readable report

### Failure Injection
- `failure_injection_scenarios.json`: Scenario definitions
- `failure_injection_results.json`: Test results
- `failure_injection_report.md`: Human-readable report

### Scale & Stress
- `scale_validation_metrics.json`: All metrics (with LOCKED latency targets)
- `scale_validation_report.md`: Human-readable report
- `scale_validation_charts/`: Performance charts (if applicable)

### Security & Safety
- `security_verification_results.json`: Test results
- `security_verification_report.md`: Human-readable report
- `rbac_enforcement_log.json`: RBAC enforcement log
- `audit_integrity_verification.json`: Audit integrity verification

### Agent Reality Check
- `agent_reality_check_results.json`: Test results
- `agent_reality_check_report.md`: Human-readable report
- `agent_structural_comparison.json`: Structural comparison results
- `agent_semantic_comparison.json`: Semantic comparison results

---

**AUTHORITATIVE**: This corrected validation plan is the single authoritative source for GA validation.

**STATUS**: Corrected validation plan defined. Ready for test execution.
