# RansomEye v1.0 Validation Harness (Phase 9 - Written First)

**AUTHORITATIVE**: Authoritative validation harness that proves end-to-end correctness of RansomEye v1.0.

---

## What This Component Does

This component **ONLY** implements the minimal validation required for Phase 9 proof-of-concept:

1. **Cold Start Correctness** (`test_cold_start.py`):
   - Validates system behavior with no prior state
   - Database is empty (cold start)
   - Services can start without errors
   - System is in correct initial state

2. **Zero-Event Correctness** (`test_zero_event.py`):
   - Validates system behavior with zero events processed
   - Correlation engine processes zero events (no incidents created)
   - System remains in correct state (no incidents, no evidence)

3. **One-Event Correctness** (`test_one_event.py`):
   - Validates system behavior with exactly one event
   - Ingest one valid event (linux_agent)
   - Run correlation engine
   - Assert exactly one incident created with correct properties

4. **Duplicate Event Handling** (`test_duplicates.py`):
   - Validates duplicate event rejection
   - Ingest same event twice
   - Assert duplicate rejected with 409 CONFLICT
   - Assert only one event stored

5. **Failure Semantics Enforcement** (`test_failure_semantics.py`):
   - Validates fail-closed behavior, no retries, no silent failures
   - Missing required environment variable causes startup failure
   - Invalid database connection causes failure
   - No retries on errors (fail-fast)
   - No silent failures (all errors logged/reported)

6. **Subsystem Disablement** (`test_subsystem_disablement.py`):
   - Validates system correctness when subsystems are disabled
   - AI Core disabled: System creates incidents correctly
   - Policy Engine disabled: System creates incidents correctly
   - UI disabled: System creates incidents correctly

---

## What This Component Explicitly Does NOT Do

**Phase 9 Requirements - Forbidden Behaviors**:

- ❌ **NO service logic**: Validation only, no service implementation
- ❌ **NO mocks of core logic**: Tests use real system behavior
- ❌ **NO sleeps / timing hacks**: Tests are deterministic (no time.sleep, no random delays)
- ❌ **NO randomness**: Tests are deterministic (no random data generation)
- ❌ **NO skipping failures**: Tests fail fast (no try-except that swallows errors)
- ❌ **NO schema changes**: Tests read from existing schema only
- ❌ **NO contract changes**: Tests validate against frozen contracts

---

## What Is Validated

**Phase 9 Objective**: Prove end-to-end correctness of RansomEye v1.0.

**Validation Scope**:
1. **Cold Start**: System starts correctly with empty database
2. **Zero Events**: System handles zero events correctly (no incidents created)
3. **One Event**: System processes one event correctly (one incident created with correct properties)
4. **Duplicates**: System rejects duplicate events correctly (409 CONFLICT)
5. **Failure Semantics**: System enforces fail-closed, fail-fast, no silent failures
6. **Subsystem Disablement**: System remains correct when AI, Policy, or UI subsystems are disabled

**What Is NOT Validated** (Out of Scope for Phase 9):
- Performance (latency, throughput)
- Scalability (large numbers of events/incidents)
- Security (authentication, authorization)
- High availability (failover, redundancy)
- Load testing (stress testing, capacity planning)

---

## Why Failures Block Release

**Phase 9 Requirement**: Validation failures MUST block release.

**Failures Block Release Because**:
1. **Correctness**: System must be correct before release (incidents created correctly, duplicates rejected, etc.)
2. **Reliability**: System must handle failures correctly (fail-closed, fail-fast, no silent failures)
3. **Observability**: System must be observable (logs, exit codes, no silent failures)
4. **Modularity**: System must work correctly when subsystems are disabled (AI, Policy, UI)

**If Validation Fails**:
- System is NOT correct (incidents not created, duplicates not rejected, etc.)
- System is NOT reliable (failures not handled correctly, silent failures exist)
- System is NOT observable (errors not logged, exit codes incorrect)
- System is NOT modular (subsystems required for correctness)

**Release Criteria**:
- ✅ All validation tests PASS
- ✅ Results are deterministic (same input → same output)
- ✅ System is left clean (no test data remaining)
- ✅ No silent failures exist (all errors logged/reported)

---

## How to Run Validation

### Prerequisites

1. **Database**: PostgreSQL 14+ must be running and accessible
2. **Environment Variables**: Database connection parameters must be set
3. **Services**: Ingest service must be running (for HTTP-based tests)

### Environment Variables

**Required**:
- `RANSOMEYE_DB_HOST`: PostgreSQL host (default: `localhost`)
- `RANSOMEYE_DB_PORT`: PostgreSQL port (default: `5432`)
- `RANSOMEYE_DB_NAME`: Database name (default: `ransomeye`)
- `RANSOMEYE_DB_USER`: Database user (default: `ransomeye`)
- `RANSOMEYE_DB_PASSWORD`: Database password (**required**, no default, fail-closed)

**Optional**:
- `RANSOMEYE_INGEST_URL`: Ingest service URL (default: `http://localhost:8000/events`)

### Run Individual Tests

```bash
# Test cold start correctness
python3 validation/harness/test_cold_start.py

# Test zero-event correctness
python3 validation/harness/test_zero_event.py

# Test one-event correctness
python3 validation/harness/test_one_event.py

# Test duplicate event handling
python3 validation/harness/test_duplicates.py

# Test failure semantics enforcement
python3 validation/harness/test_failure_semantics.py

# Test subsystem disablement
python3 validation/harness/test_subsystem_disablement.py
```

### Run All Tests

```bash
# Run all validation tests
python3 -m pytest validation/harness/ -v

# Or run sequentially (no pytest required)
for test in validation/harness/test_*.py; do
    python3 "$test" || exit 1
done
```

### Start Ingest Service (Required for HTTP Tests)

```bash
# Start ingest service (required for test_one_event.py, test_duplicates.py)
cd services/ingest
export RANSOMEYE_DB_HOST="localhost"
export RANSOMEYE_DB_PORT="5432"
export RANSOMEYE_DB_NAME="ransomeye"
export RANSOMEYE_DB_USER="ransomeye"
export RANSOMEYE_DB_PASSWORD="your_password"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Determinism Guarantees

**Phase 9 Requirement**: Tests must be deterministic (no randomness, no sleeps, no timing hacks).

**Determinism Guarantees**:
1. **No Randomness**: Tests use fixed event IDs, machine IDs, timestamps (no UUID.random(), no random data)
2. **No Sleeps**: Tests do not use `time.sleep()` or timing hacks (no waiting, no delays)
3. **No Timing**: Tests do not depend on wall-clock time (no time-dependent assertions)
4. **Deterministic Ordering**: Tests process events in deterministic order (by ingested_at ASC)

**Deterministic Inputs**:
- Event IDs: Fixed UUIDs (not randomly generated)
- Machine IDs: Fixed strings (e.g., "test-machine-001")
- Timestamps: Fixed RFC3339 UTC timestamps (not `datetime.now()`)
- Sequence numbers: Fixed integers (0, 1, 2, ...)

**Deterministic Outputs**:
- Same input → same output (same event → same incident, same properties)
- Same database state → same results (deterministic queries)
- Same environment → same behavior (no environment-dependent randomness)

**Non-Deterministic Behaviors** (Forbidden):
- ❌ `uuid.uuid4()` for test data (use fixed UUIDs)
- ❌ `datetime.now()` for test data (use fixed timestamps)
- ❌ `time.sleep()` for synchronization (no timing hacks)
- ❌ Random data generation (use fixed test data)

---

## PASS / FAIL Criteria

### PASS Criteria

**Phase 9 Requirement**: Tests PASS only if:
1. ✅ **All tests pass consistently**: All validation tests complete without errors
2. ✅ **Results are deterministic**: Same input → same output (no flaky tests)
3. ✅ **System is left clean**: No test data remaining after tests complete
4. ✅ **No silent failures exist**: All errors are logged/reported (no swallowed exceptions)

**PASS Example**:
```
TEST: Cold Start Correctness
PASS: Cold Start Correctness

TEST: Zero-Event Correctness
PASS: Zero-Event Correctness

TEST: One-Event Correctness
PASS: One-Event Correctness

TEST: Duplicate Event Handling
PASS: Duplicate Event Handling

TEST: Failure Semantics Enforcement
PASS: Failure Semantics Enforcement

TEST: Subsystem Disablement
PASS: Subsystem Disablement

ALL TESTS PASS
```

### FAIL Criteria

**Phase 9 Requirement**: Tests FAIL if:
1. ❌ **Any nondeterminism**: Tests produce different results on different runs (flaky tests)
2. ❌ **Any skipped test**: Tests skip validation steps (no `skip`, no `TODO`, no `FIXME`)
3. ❌ **Any silent error**: Errors are swallowed or not logged (no `except: pass`, no silent failures)

**FAIL Example**:
```
TEST: One-Event Correctness
FAIL: One-Event Correctness - Expected 1 incident, found 0
Traceback (most recent call last):
  ...
AssertionError: Expected 1 incident, found 0

ALL TESTS FAIL
```

### Exit Codes

**Phase 9 Requirement**: Tests must exit with correct codes:
- **Exit Code 0**: All tests PASS
- **Exit Code 1**: Any test FAILS (fail-fast, no silent failures)

**Usage**:
```bash
python3 validation/harness/test_one_event.py
if [ $? -eq 0 ]; then
    echo "Test passed"
else
    echo "Test failed"
    exit 1
fi
```

---

## Test Structure

**Phase 9 Requirement**: Each test must:
1. **Set up environment**: Clean database, set environment variables
2. **Execute scenario**: Ingest events, run correlation engine, etc.
3. **Assert DB state**: Validate database state (correct number of incidents, evidence, etc.)
4. **Assert logs / exit codes**: Validate logs and exit codes (no errors, correct exit codes)
5. **Clean up**: Clean database after test (no test data remaining)

**Test Template**:
```python
def test_example():
    """Test description."""
    # Phase 9 requirement: Set up environment
    clean_database()
    
    # Phase 9 requirement: Execute scenario
    # ... test logic ...
    
    # Phase 9 requirement: Assert DB state
    assert_database_state()
    
    # Phase 9 requirement: Assert logs / exit codes
    assert_no_errors()
    
    # Phase 9 requirement: Clean up
    clean_database()
```

---

## Contract Compliance

**Phase 9 Requirement**: Tests must validate against frozen contracts.

**Contracts Validated**:
1. **Database Schema Contract** (`schemas/*.sql`):
   - Tests read from existing schema only (no schema changes)
   - Tests validate against schema constraints (incidents, evidence, etc.)

2. **Event Envelope Contract** (`contracts/event-envelope.schema.json`):
   - Tests create valid event envelopes (match schema)
   - Tests validate event envelope properties (event_id, machine_id, etc.)

3. **Failure Semantics Contract** (`failure-semantics.md`):
   - Tests validate fail-closed behavior (missing env vars cause failure)
   - Tests validate fail-fast behavior (no retries on errors)
   - Tests validate no silent failures (errors logged/reported)

4. **Environment Variable Contract** (`env.contract.json`):
   - Tests use environment variables for configuration (no hardcoded values)
   - Tests validate fail-closed behavior (missing required vars cause failure)

---

## Phase 9 Limitations

**Phase 9 Minimal Implementation**:
- Tests require ingest service to be running (for HTTP-based tests)
- Tests use real database (no database mocking)
- Tests use real system behavior (no service logic mocking)
- Tests are sequential (no parallel execution)

**Limitations Do Not Affect Correctness**:
- Tests validate real system behavior (not mocked behavior)
- Tests validate end-to-end correctness (not unit test correctness)
- Tests validate deterministic behavior (not performance)

---

## Proof of Phase 9 Correctness

**Phase 9 Objective**: Prove end-to-end correctness of RansomEye v1.0.

**This component proves**:
- ✅ **Cold Start Correctness**: System starts correctly with empty database
- ✅ **Zero-Event Correctness**: System handles zero events correctly
- ✅ **One-Event Correctness**: System processes one event correctly
- ✅ **Duplicate Handling**: System rejects duplicate events correctly
- ✅ **Failure Semantics**: System enforces fail-closed, fail-fast, no silent failures
- ✅ **Subsystem Disablement**: System remains correct when subsystems are disabled

**Together, they prove**:
- ✅ **System Correctness**: System creates incidents correctly, rejects duplicates, handles failures
- ✅ **System Reliability**: System handles failures correctly, no silent failures
- ✅ **System Modularity**: System works correctly when subsystems are disabled

---

**END OF README**
