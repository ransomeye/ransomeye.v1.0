# RansomEye v1.0 GA Validation Architecture

**AUTHORITATIVE:** Global GA validation and determinism proof framework

## Overview

This document defines the comprehensive validation framework for proving RansomEye is GA-ready through:
- **Determinism guarantees**: Same input → same output (bit-for-bit)
- **Replay validation**: Full system replay from raw events
- **Failure injection**: Corruption resistance and graceful degradation
- **Scale validation**: 1M+ events, burst traffic, sustained load
- **Audit proof**: Complete audit trail and compliance artifacts

## Validation Architecture

### Component Structure

```
validation/
├── GA_VALIDATION_ARCHITECTURE.md          # This document
├── TEST_MATRIX.md                         # Complete test matrix
├── GA_READINESS_CHECKLIST.md              # GA readiness checklist
├── VALIDATION_REPORT_TEMPLATE.md          # Validation report template
├── harness/
│   ├── test_determinism.py                # Determinism proof tests
│   ├── test_replay.py                     # Replay validation tests
│   ├── test_failure_injection.py          # Failure injection tests
│   ├── test_scale.py                      # Scale validation tests
│   └── test_audit_proof.py                # Audit proof tests
├── fixtures/
│   ├── raw_events/                        # Test event datasets
│   ├── expected_outputs/                  # Expected deterministic outputs
│   └── failure_scenarios/                 # Failure scenario definitions
├── tools/
│   ├── event_generator.py                 # Synthetic event generator
│   ├── hash_comparator.py                 # Hash comparison tool
│   ├── replay_engine.py                   # Replay execution engine
│   ├── failure_injector.py                # Failure injection tool
│   ├── scale_simulator.py                 # Scale simulation tool
│   └── audit_verifier.py                  # Audit verification tool
└── reports/
    ├── determinism_proof/                 # Determinism proof logs
    ├── replay_verification/                # Replay verification logs
    ├── failure_reports/                   # Failure injection reports
    ├── scale_metrics/                     # Scale validation metrics
    └── ga_readiness/                      # GA readiness artifacts
```

### Validation Pipeline

```
1. Determinism Proof
   ├── Generate test events
   ├── Process through detection → correlation → forensics
   ├── Capture all outputs (hashes)
   ├── Re-run with same inputs
   ├── Compare hashes (must match bit-for-bit)
   └── Generate determinism proof log

2. Replay Validation
   ├── Export raw_events from production/test DB
   ├── Clear all downstream tables (normalized, incidents, summaries)
   ├── Replay raw_events through full pipeline
   ├── Rebuild normalized events
   ├── Rebuild incidents
   ├── Rebuild forensic summaries
   ├── Compare hashes (must match original)
   └── Generate replay verification log

3. Failure Injection
   ├── Simulate DB restart (mid-transaction)
   ├── Simulate queue overflow (backpressure)
   ├── Simulate agent disconnect (sequence gaps)
   ├── Simulate duplicate events (idempotency)
   ├── Simulate partial writes (atomicity)
   ├── Verify no corruption
   ├── Verify no silent loss
   ├── Verify correct degradation
   └── Generate failure report

4. Scale Validation
   ├── Generate 1M+ synthetic events
   ├── Ingest at burst rate (10K events/sec)
   ├── Ingest at sustained rate (1K events/sec)
   ├── Measure latency (p50, p95, p99)
   ├── Measure backpressure (queue depth)
   ├── Measure CPU/memory (per service)
   ├── Measure DB stability (lock contention, WAL growth)
   └── Generate scale metrics report

5. Audit Proof
   ├── Verify audit ledger integrity (hash chain)
   ├── Verify all actions logged (coverage)
   ├── Verify signature validity (ed25519)
   ├── Verify chronological ordering
   ├── Generate audit compliance report
   └── Generate signed validation report (PDF/JSON)
```

## Determinism Proof

### Scope

**CRITICAL**: Prove that same inputs produce same outputs (bit-for-bit) across:
- **Detection**: Agent telemetry → raw_events
- **Normalization**: raw_events → normalized tables
- **Correlation**: normalized events → incidents
- **Forensics**: incidents → forensic summaries

### Test Methodology

1. **Input Generation**
   - Generate deterministic test events (fixed seed)
   - Store input events with SHA256 hash
   - Ensure no randomness in event generation

2. **First Run**
   - Process events through full pipeline
   - Capture all outputs:
     - `raw_events` table (event_id, payload hash)
     - `process_activity` table (row hash)
     - `file_activity` table (row hash)
     - `incidents` table (incident_id, hash)
     - `forensic_summarization` JSON (summary hash)
   - Store all hashes in `determinism_proof_run1.json`

3. **Second Run**
   - Clear all downstream tables
   - Re-run with same inputs (same event order)
   - Capture all outputs (same format)
   - Store all hashes in `determinism_proof_run2.json`

4. **Hash Comparison**
   - Compare hashes from run1 and run2
   - **REQUIREMENT**: All hashes must match exactly
   - Generate `determinism_proof_log.json` with:
     - Total comparisons
     - Matches
     - Mismatches (if any)
     - Mismatch details

### Determinism Guarantees

**Detection (Agent → raw_events)**
- Same telemetry → same `raw_events` row
- Same `event_id`, same `payload` hash
- Same `ingested_at` timestamp (if deterministic)

**Normalization (raw_events → normalized)**
- Same `raw_events` → same normalized rows
- Same `event_id` mapping
- Same field values (no rounding, no truncation)

**Correlation (normalized → incidents)**
- Same normalized events → same `incident_id`
- Same `confidence_score` (if deterministic)
- Same `stage` assignment

**Forensics (incidents → summaries)**
- Same incident → same `summary_id`
- Same JSON summary (canonical JSON hash)
- Same text summary (character-for-character)
- Same graph metadata

### Evidence Artifacts

- `determinism_proof_run1.json`: First run hashes
- `determinism_proof_run2.json`: Second run hashes
- `determinism_proof_log.json`: Comparison results
- `determinism_proof_report.md`: Human-readable report

## Replay Validation

### Scope

**CRITICAL**: Prove that system can replay from `raw_events` and rebuild all downstream data identically.

### Test Methodology

1. **Baseline Export**
   - Export `raw_events` from production/test DB
   - Export all downstream data:
     - Normalized tables (process_activity, file_activity, etc.)
     - Incidents table
     - Evidence table
     - Forensic summaries (if any)
   - Calculate hashes for all exported data
   - Store in `replay_baseline.json`

2. **Replay Execution**
   - Clear all downstream tables (keep `raw_events`)
   - Replay `raw_events` through full pipeline:
     - Normalization service
     - Correlation engine
     - Forensic summarization
   - Export all rebuilt data
   - Calculate hashes for all rebuilt data
   - Store in `replay_rebuilt.json`

3. **Hash Comparison**
   - Compare baseline hashes vs rebuilt hashes
   - **REQUIREMENT**: All hashes must match exactly
   - Generate `replay_verification_log.json` with:
     - Total comparisons
     - Matches
     - Mismatches (if any)
     - Mismatch details

### Replay Guarantees

**Normalized Events**
- Same `raw_events` → same normalized rows
- Same `event_id` mapping
- Same field values

**Incidents**
- Same normalized events → same `incident_id`
- Same `confidence_score`
- Same `stage` progression

**Evidence**
- Same incidents → same evidence links
- Same `event_id` references

**Forensic Summaries**
- Same incidents → same summaries
- Same JSON (canonical hash)
- Same text (character-for-character)

### Evidence Artifacts

- `replay_baseline.json`: Baseline data hashes
- `replay_rebuilt.json`: Rebuilt data hashes
- `replay_verification_log.json`: Comparison results
- `replay_verification_report.md`: Human-readable report

## Failure Injection

### Scope

**CRITICAL**: Prove that system handles failures gracefully without corruption or silent loss.

### Failure Scenarios

#### 1. Database Restart (Mid-Transaction)

**Test**:
- Start transaction (insert into `raw_events`)
- Kill database process mid-transaction
- Restart database
- Verify: Transaction rolled back, no partial writes

**Expected Behavior**:
- No corruption in `raw_events` table
- No orphaned rows
- Event can be re-ingested (idempotent)

**Validation**:
- Check `raw_events` table integrity (PRIMARY KEY constraints)
- Verify no partial writes (all-or-nothing)
- Verify replay capability (event can be re-ingested)

#### 2. Queue Overflow (Backpressure)

**Test**:
- Ingest events at rate exceeding processing capacity
- Fill queue to capacity
- Verify: Backpressure mechanism activates

**Expected Behavior**:
- Queue depth monitored
- Backpressure signal sent to agents
- Events buffered (not dropped silently)
- Audit log entry for queue overflow

**Validation**:
- Check queue depth metrics
- Check backpressure signals
- Check audit ledger entries
- Verify no silent event loss

#### 3. Agent Disconnect (Sequence Gaps)

**Test**:
- Agent sends events with sequence numbers
- Simulate agent disconnect (mid-sequence)
- Agent reconnects with gap in sequence
- Verify: Sequence gap detected and logged

**Expected Behavior**:
- Sequence gap detected
- Gap logged in `sequence_gaps` table
- Audit ledger entry created
- Processing continues (fail-open)

**Validation**:
- Check `sequence_gaps` table
- Check audit ledger entries
- Verify processing continues

#### 4. Duplicate Events (Idempotency)

**Test**:
- Ingest same event twice (same `event_id`)
- Verify: Second ingestion is idempotent

**Expected Behavior**:
- First ingestion succeeds
- Second ingestion skipped (idempotent)
- No duplicate rows in `raw_events`
- Audit log entry for duplicate detection

**Validation**:
- Check `raw_events` table (no duplicates)
- Check idempotency logic
- Check audit ledger entries

#### 5. Partial Writes (Atomicity)

**Test**:
- Simulate partial write (network failure mid-write)
- Verify: Transaction rolled back, no partial state

**Expected Behavior**:
- Transaction rolled back
- No partial writes
- Event can be re-ingested

**Validation**:
- Check database integrity
- Check transaction logs
- Verify replay capability

### Failure Validation Matrix

| Failure Scenario | Corruption Check | Silent Loss Check | Degradation Check | Audit Check |
|-----------------|------------------|-------------------|-------------------|-------------|
| DB Restart | ✅ No partial writes | ✅ No events lost | ✅ Graceful restart | ✅ Restart logged |
| Queue Overflow | ✅ Queue integrity | ✅ Events buffered | ✅ Backpressure | ✅ Overflow logged |
| Agent Disconnect | ✅ No corruption | ✅ Gaps detected | ✅ Processing continues | ✅ Gaps logged |
| Duplicate Events | ✅ No duplicates | ✅ No loss | ✅ Idempotent | ✅ Duplicates logged |
| Partial Writes | ✅ Atomicity | ✅ No loss | ✅ Rollback | ✅ Rollback logged |

### Evidence Artifacts

- `failure_injection_scenarios.json`: Scenario definitions
- `failure_injection_results.json`: Test results
- `failure_injection_report.md`: Human-readable report

## Scale Validation

### Scope

**CRITICAL**: Prove that system handles 1M+ events with acceptable latency, backpressure, and resource usage.

### Test Scenarios

#### 1. Burst Ingestion (10K events/sec)

**Test**:
- Generate 100K events
- Ingest at 10K events/sec (burst)
- Measure latency, backpressure, CPU/memory

**Metrics**:
- **Latency**: p50, p95, p99 (target: p99 < 1s)
- **Backpressure**: Queue depth (target: < 10K)
- **CPU**: Per-service CPU usage (target: < 80%)
- **Memory**: Per-service memory usage (target: < 2GB)
- **DB**: Lock contention, WAL growth

#### 2. Sustained Load (1K events/sec)

**Test**:
- Generate 1M events
- Ingest at 1K events/sec (sustained)
- Measure latency, backpressure, CPU/memory over 1 hour

**Metrics**:
- **Latency**: p50, p95, p99 (target: p99 < 5s)
- **Backpressure**: Queue depth (target: < 1K)
- **CPU**: Per-service CPU usage (target: < 50%)
- **Memory**: Per-service memory usage (target: < 2GB)
- **DB**: Lock contention, WAL growth, table bloat

#### 3. POC Single-Host Mode

**Test**:
- Run Core + DPI + Linux Agent on same host
- Ingest 100K events
- Measure resource isolation, port conflicts

**Metrics**:
- **CPU Isolation**: Per-service CPU usage (no starvation)
- **Memory Isolation**: Per-service memory usage (no OOM)
- **IO Isolation**: Per-service IO usage (no starvation)
- **Port Conflicts**: No port conflicts
- **Performance**: Acceptable latency despite co-location

### Scale Validation Matrix

| Scenario | Event Count | Rate | Latency Target | Backpressure Target | CPU Target | Memory Target |
|----------|-------------|-----|----------------|---------------------|------------|---------------|
| Burst | 100K | 10K/sec | p99 < 1s | < 10K | < 80% | < 2GB |
| Sustained | 1M | 1K/sec | p99 < 5s | < 1K | < 50% | < 2GB |
| POC | 100K | 1K/sec | p99 < 5s | < 1K | < 80% | < 2GB |

### Evidence Artifacts

- `scale_validation_metrics.json`: All metrics
- `scale_validation_report.md`: Human-readable report
- `scale_validation_charts/`: Performance charts (if applicable)

## Audit Proof

### Scope

**CRITICAL**: Prove that audit ledger provides complete, tamper-evident audit trail.

### Audit Validation

#### 1. Ledger Integrity

**Test**:
- Verify hash chain integrity (prev_entry_hash matches previous entry_hash)
- Verify signature validity (ed25519 signatures)
- Verify chronological ordering (timestamp monotonic)

**Expected Behavior**:
- All hash chains valid
- All signatures valid
- All timestamps monotonic

#### 2. Coverage

**Test**:
- Verify all security-relevant actions are logged:
  - Installer actions
  - Service lifecycle events
  - Policy decisions
  - AI model lifecycle actions
  - Playbook execution
  - Forensic access
  - Administrative actions

**Expected Behavior**:
- 100% coverage of security-relevant actions
- No silent actions

#### 3. Compliance

**Test**:
- Verify audit ledger meets compliance requirements:
  - SOC 2: Access control and audit requirements
  - ISO 27001: Audit logging requirements
  - HIPAA: Audit trail requirements
  - PCI DSS: Audit logging requirements
  - GDPR: Audit trail requirements

**Expected Behavior**:
- All compliance requirements met
- Audit trail exportable
- Audit trail immutable

### Evidence Artifacts

- `audit_integrity_verification.json`: Integrity check results
- `audit_coverage_report.json`: Coverage analysis
- `audit_compliance_report.json`: Compliance verification
- `audit_proof_report.md`: Human-readable report

## GA Readiness Checklist

See `GA_READINESS_CHECKLIST.md` for complete checklist.

## Validation Report

See `VALIDATION_REPORT_TEMPLATE.md` for validation report template.

---

**AUTHORITATIVE**: This validation architecture is the single authoritative source for GA validation.

**STATUS**: Validation architecture defined. Ready for test implementation.
