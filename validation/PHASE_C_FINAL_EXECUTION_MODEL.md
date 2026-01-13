# Phase C Final Execution Model

**AUTHORITATIVE**: Final, locked execution model for Phase C Global GA Validation

## Build-Integrity Constraints

### Default Database Credentials

**Embedded defaults**: `gagan` / `gagan`

- Defaults exist in code, never break execution
- May be overridden by environment variables
- If defaults are used, emits RuntimeWarning:
  ```
  "Default POC credentials (gagan/gagan) in use — NOT production safe."
  ```
- Do NOT remove defaults
- Do NOT require env vars

### No Constructor Side-Effects

`__init__()` must never:
- Open DB connections
- Call network resources
- Call `sys.exit`

All validation moved to explicit:
```python
executor.preflight_check()
```

### Fail-Fast, Explicit Errors Only

- No Python tracebacks for operator errors
- All fatal errors print clear messages and exit cleanly
- Error messages are actionable and specific

## Phase C Execution Model (Final & Locked)

### Two-Host, One-Verdict Model

#### Phase C-L (Linux Host)

**Runs only**:
- Track 1 — Determinism (DET-001 → DET-006)
- Track 2 — Replay (REP-A & REP-B)
- Track 3 — Failure Injection (FAIL-001 → FAIL-006)
- Track 4 — Scale & Stress
- Track 5 — Security & Safety
- Track 6-A — Linux Agent Reality Check

**Explicitly forbidden on Linux**:
- AGENT-002 (Windows ETW)
- Must be skipped with reason, not silently ignored

**Produces**: `phase_c_linux_results.json`

#### Phase C-W (Windows Host)

**Runs only**:
- Track 6-B — Windows Agent / ETW Reality Check

**Produces**: `phase_c_windows_results.json`

### GA Verdict Aggregation

GA verdict computed only by aggregating:
- `phase_c_linux_results.json`
- `phase_c_windows_results.json`

**Both must PASS**

**Rules**:
- No skipped mandatory tests allowed
- FAIL-006 and AGENT-002 are mandatory for GA

## Determinism & Replay Rules (Fixed)

### Non-LLM Paths

**Bit-exact hash match required**

- DET-001 through DET-004: Hash equality (100% match)
- REP-A (Identity Replay): Hash exact

### LLM Paths

❌ **Bit-for-bit matching is impossible**

✅ **Enforce**:
- Schema equivalence
- Semantic equivalence
- Identical structure & ordering
- Forbidden-language checks

**Tests**:
- DET-005: LLM Semantic Determinism
- REP-B (Evolution Replay): Backward-compatible superset allowed

## Agent Reality Check (Corrected)

**No simulator input injection**

**Functional parity testing only**:
- Same actions → same facts → same schema

**PID reuse disambiguation**:
- Must be disambiguated by `(PID, start_time)` OR generated `ProcessGUID`
- DET-006 validates this

## Database & Data-Plane Rules

### All DB Reads Via Views Only

- No direct table access fallback
- Views must not contain parameters
- RBAC enforcement via views

### Duplicate Event IDs

- Must be log & drop, not fatal
- Idempotent handling required

### PostgreSQL Assumptions

- High concurrency (1M+ events)
- Partitioned tables
- BRIN for time, BTREE for keys

### Disk I/O Metrics

**Must be collected for co-located tests**:
- Disk I/O wait
- Queue depth
- Included in SCALE-004 metrics

## Failure Injection (FAIL-006) — Hard Rule

**FAIL-006 cannot be skipped for GA**

**Supported restart modes**:
- Docker (requires `RANSOMEYE_DB_CONTAINER_NAME`)
- systemd (requires sudo privileges)

**If restart authority is missing**:
- Phase C must fail fast
- No partial GA
- Clear error message

**Implementation**:
- Checks `RANSOMEYE_DB_RESTART_MODE` in `test_fail_006_database_restart()`
- If missing → `sys.exit(1)` with clear error
- If invalid → `sys.exit(1)` with clear error
- Validates Docker/systemd prerequisites

## Result Artifact Hardening

**Each results JSON must include**:

```json
{
  "schema_version": "1.0",
  "phase": "Phase C-L | Phase C-W",
  "status": "PASS | FAIL",
  "execution_start": "...",
  "execution_end": "...",
  "execution_mode": "linux | windows",
  "platform": "...",
  "platform_release": "...",
  "tracks": {...},
  "tests": {...},
  "verdict": {...}
}
```

**Required fields**:
- `schema_version`: Must be "1.0"
- `phase`: Must be "Phase C-L" or "Phase C-W"
- `status`: Must be "PASS" or "FAIL"
- `verdict`: Contains detailed verdict information

## Aggregator Hardening

**Aggregator must**:
- Validate both result files exist
- Validate `schema_version == "1.0"`
- Validate `phase` matches expected value
- Fail explicitly if missing/corrupt
- No imports from executor code
- JSON-only parsing
- Clear GA verdict: `GA-READY` or `GA-BLOCKED`

**Validation checks**:
1. File existence
2. JSON validity
3. Schema version
4. Phase name
5. Verdict structure

**Error messages**:
- Clear, actionable
- No tracebacks
- Explicit file paths

## Execution Flow

### Phase C-L Execution

```python
executor = PhaseCExecutor(execution_mode='linux')
executor.preflight_check()  # Explicit, not in __init__
executor.run_all_tracks()
# Produces: phase_c_linux_results.json
```

### Phase C-W Execution

```python
executor = PhaseCExecutor(execution_mode='windows')
executor.preflight_check()  # Explicit, not in __init__
executor.run_all_tracks()
# Produces: phase_c_windows_results.json
```

### GA Verdict Aggregation

```python
verdict = aggregate_ga_verdict(
    'phase_c_linux_results.json',
    'phase_c_windows_results.json'
)
# Returns: GA-READY or GA-BLOCKED
```

## GA Verdict Logic

**GA_READY = Phase C-L PASS AND Phase C-W PASS**

**Checks**:
1. ✅ `linux_results.status == "PASS"`
2. ✅ `windows_results.status == "PASS"`
3. ✅ FAIL-006 not skipped
4. ✅ AGENT-002 not in Linux results (must be skipped)
5. ✅ AGENT-002 in Windows results and passed
6. ✅ No skipped mandatory tests

**Final Verdict**:
- ✅ **GA-READY**: All checks pass
- ❌ **GA-BLOCKED**: Any check fails

## Status

**Phase C execution is now architecturally correct, deterministic, explicit, auditable, and GA-reliable.**

---

**AUTHORITATIVE**: This document defines the final, locked execution model for Phase C validation.
