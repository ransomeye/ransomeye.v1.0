# Phase C Validation - Execution Framework Summary

**AUTHORITATIVE**: Phase C validation test execution framework for Global GA Validation

## Overview

This document summarizes the Phase C validation test execution framework that has been created to execute all 35 tests across 6 validation tracks as defined in `GA_VALIDATION_PLAN_CORRECTED.md`.

## Framework Structure

### Main Components

1. **`phase_c_executor.py`**: Main test execution orchestrator
   - Coordinates execution of all 6 tracks
   - Collects evidence artifacts
   - Generates final GA verdict

2. **Track Executors**:
   - `track_1_determinism.py`: Determinism tests (DET-001 to DET-005)
   - `track_2_replay.py`: Replay tests (REP-A-001 to REP-A-005, REP-B-001 to REP-B-005)
   - `track_3_failure.py`: Failure injection tests (FAIL-001 to FAIL-006)
   - `track_4_scale.py`: Scale & stress tests (SCALE-001 to SCALE-005)
   - `track_5_security.py`: Security & safety tests (SEC-001 to SEC-006)
   - `track_6_agent.py`: Agent reality check tests (AGENT-001, AGENT-002)

## Test Coverage

### TRACK 1: Determinism (6 tests)
- DET-001: Detection Determinism (bit-exact hash comparison)
- DET-002: Normalization Determinism (bit-exact hash comparison)
- DET-003: Correlation Determinism (bit-exact hash comparison)
- DET-004: Forensic Summarization Determinism (bit-exact hash comparison)
- DET-005: LLM Semantic Determinism (schema + semantic equivalence)
- DET-006: Identity Disambiguation Determinism (bit-exact hash comparison)

### TRACK 2: Replay & Rehydration (10 tests)
- REP-A-001 to REP-A-005: Identity Replay (bit-exact)
- REP-B-001 to REP-B-005: Evolution Replay (semantic equivalence)

### TRACK 3: Failure Injection (6 tests)
- FAIL-001: DB Connection Loss (Mid-Transaction)
- FAIL-002: Agent Disconnect (Sequence Gaps)
- FAIL-003: Queue Overflow (Backpressure)
- FAIL-004: Duplicate Events (Idempotency)
- FAIL-005: Partial Writes (Atomicity)
- FAIL-006: Database Restart (Mid-Processing)

### TRACK 4: Scale & Stress (5 tests)
- SCALE-001: Burst Ingestion (100K events at 10K/sec)
- SCALE-002: Sustained Load (1M events at 1K/sec)
- SCALE-003: Mixed Traffic (ETW + DPI + Agent)
- SCALE-004: Co-located Deployment
- SCALE-005: Backpressure Recovery

### TRACK 5: Security & Safety (6 tests)
- SEC-001: Enforcement Authority Verification
- SEC-002: Signed Execution Verification
- SEC-003: No Direct Table Access Verification
- SEC-004: RBAC Enforcement Verification
- SEC-005: Data-Plane Ownership Enforcement Verification
- SEC-006: Audit Ledger Integrity Verification

### TRACK 6: Agent Reality Check (2 tests)
- AGENT-001: Linux Real Agent vs Simulator
- AGENT-002: Windows Real Agent vs Simulator

**Total: 35 tests**

## Execution Requirements

### Prerequisites

## **DATABASE BOOTSTRAP REQUIREMENT (MANDATORY)**

**Phase C assumes PostgreSQL is pre-provisioned with:**

- **User**: `gagan`
- **Password**: `gagan`
- **Database**: `ransomeye`
- **Owner**: `gagan`

**Phase C WILL FAIL if this is not true.**
**This is intentional and correct.**

**Bootstrap PostgreSQL (run once, as postgres superuser):**

```sql
CREATE ROLE gagan LOGIN PASSWORD 'gagan';
CREATE DATABASE ransomeye OWNER gagan;
GRANT ALL PRIVILEGES ON DATABASE ransomeye TO gagan;
```

**Phase C verifies:**
- Role exists with LOGIN privilege
- Database exists and is owned by role
- Authentication works with credentials
- Basic queries work

**If bootstrap verification fails:**
- Phase C aborts immediately
- Clear, actionable error message displayed
- No tracks execute
- No partial verdict

**This is NOT a code issue.**
**This is infrastructure correctness enforcement.**

**Environment variables (optional overrides):**
- `RANSOMEYE_DB_HOST` (default: localhost)
- `RANSOMEYE_DB_PORT` (default: 5432)
- `RANSOMEYE_DB_NAME` (default: ransomeye)
- `RANSOMEYE_DB_USER` (default: gagan)
- `RANSOMEYE_DB_PASSWORD` (default: gagan)

1. **Database Connection**:
   - PostgreSQL database must be running
   - **Database must be bootstrapped (see above)**
   - Environment variables may override defaults (see above)

2. **Database Schema**:
   - All required tables must exist (raw_events, incidents, evidence, etc.)
   - Schema must match Phase 2+ schema definitions

3. **Services** (for full execution):
   - Ingest service
   - Normalization service
   - Correlation engine
   - Forensic summarization
   - LLM summarizer

### Execution

```bash
cd /home/ransomeye/rebuild
python3 -m validation.harness.phase_c_executor
```

Or directly:

```bash
python3 validation/harness/phase_c_executor.py
```

## Evidence Artifacts

All evidence artifacts are saved to `validation/reports/phase_c/`:

### Track-Specific Artifacts

1. **TRACK 1 - Determinism**:
   - `determinism_proof_log.json`
   - `determinism_proof_report.md`

2. **TRACK 2 - Replay**:
   - `replay_verification_log.json`
   - `replay_verification_report.md`

3. **TRACK 3 - Failure Injection**:
   - `failure_injection_results.json`
   - `failure_injection_report.md`

4. **TRACK 4 - Scale & Stress**:
   - `scale_validation_metrics.json`
   - `scale_validation_report.md`

5. **TRACK 5 - Security & Safety**:
   - `security_verification_results.json`
   - `security_verification_report.md`

6. **TRACK 6 - Agent Reality Check**:
   - `agent_reality_check_results.json`
   - `agent_reality_check_report.md`

### Final Artifacts

- `phase_c_validation_results.json`: Complete test results (machine-readable)
- `phase_c_validation_report.md`: Human-readable summary report

## Pass/Fail Criteria

### Non-LLM Paths (DET-001 to DET-004, DET-006, REP-A)
- **PASS**: All hashes match exactly (100% match rate, 0% tolerance)
- **FAIL**: Any hash mismatch

### LLM Paths (DET-005, REP-B)
- **PASS**: Schema equivalence + semantic equivalence + no forbidden language + structure/ordering match
- **FAIL**: Schema mismatch OR semantic mismatch OR forbidden language detected OR structure/ordering mismatch

### Scale Tests (SCALE-001 to SCALE-005)
- **PASS**: All latency targets met (LOCKED: p50 < 1s, p95 < 3s, p99 < 5s), no data loss
- **FAIL**: Any latency target missed OR any data loss

### Failure Injection (FAIL-001 to FAIL-006)
- **PASS**: No corruption, no silent loss, explicit degradation only
- **FAIL**: Any corruption OR any silent loss OR incorrect degradation

### Security & Safety (SEC-001 to SEC-006)
- **PASS**: All security requirements enforced, no violations, all actions logged
- **FAIL**: Any security violation OR any unauthorized action OR any missing audit log

### Agent Reality Check (AGENT-001, AGENT-002)
- **PASS**: Structural equivalence + semantic equivalence + no simulator-only assumptions
- **FAIL**: Structural mismatch OR semantic mismatch OR simulator-only assumptions detected

## Final GA Verdict

The framework generates a final GA verdict based on:

1. **All 35 tests must PASS**
2. **All evidence artifacts must be generated**
3. **No critical failures**
4. **All security requirements met**
5. **All performance targets met (LOCKED latency targets)**

### Verdict Output

The framework will output one of:

- **"Phase C validation PASSED. RansomEye is GA-READY."**
- **"Phase C validation FAILED. GA is BLOCKED."**

## Implementation Notes

### Current Implementation Status

The framework has been created with:

1. ✅ Complete test structure for all 35 tests
2. ✅ Evidence artifact collection
3. ✅ Pass/fail logic implementation
4. ✅ Final GA verdict generation
5. ⚠️ Simplified implementations for some tests (require integration with actual services)

### Integration Requirements

For full execution, the following integrations are needed:

1. **Service Integration**:
   - Connect to actual ingest service
   - Connect to normalization service
   - Connect to correlation engine
   - Connect to forensic summarization API
   - Connect to LLM summarizer API

2. **Agent Integration**:
   - Launch real Linux agent binary
   - Launch real Windows agent (ETW)
   - Compare with simulator outputs

3. **Failure Injection**:
   - Actual database connection loss simulation
   - Actual queue overflow testing
   - Actual agent disconnect simulation

4. **Scale Testing**:
   - Actual high-volume event generation
   - Actual latency measurement
   - Actual backpressure testing

### Next Steps

1. **Service Integration**: Connect track executors to actual services
2. **Agent Testing**: Implement real agent vs simulator comparison
3. **Failure Injection**: Implement actual failure scenarios
4. **Scale Testing**: Implement actual high-volume testing
5. **LLM Validation**: Implement semantic equivalence validation for LLM outputs

## Execution Summary

To execute Phase C validation:

```bash
# Set environment variables
export RANSOMEYE_DB_PASSWORD="your_password"
export RANSOMEYE_DB_HOST="localhost"
export RANSOMEYE_DB_PORT="5432"
export RANSOMEYE_DB_NAME="ransomeye"
export RANSOMEYE_DB_USER="ransomeye"

# Run Phase C validation
python3 validation/harness/phase_c_executor.py
```

The framework will:
1. Execute all 6 tracks sequentially
2. Collect evidence artifacts for each track
3. Generate final GA verdict
4. Save all results to `validation/reports/phase_c/`

## Status

**Framework Status**: ✅ Created and ready for execution

**Integration Status**: ⚠️ Requires service integration for full execution

**Test Coverage**: ✅ All 35 tests defined and structured

**Evidence Collection**: ✅ All artifact formats defined

**GA Verdict Logic**: ✅ Implemented according to validation plan

---

**AUTHORITATIVE**: This execution framework implements the Phase C validation plan as defined in `GA_VALIDATION_PLAN_CORRECTED.md`.
