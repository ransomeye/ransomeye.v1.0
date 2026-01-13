# Phase C Build-Integrity and Validation Fixes

**AUTHORITATIVE**: Build-integrity fixes for Phase C validation execution

## Overview

Phase C execution has been hardened with embedded credentials, fail-fast DB connectivity, OS boundary enforcement, and GA aggregation fixes.

## Changes Implemented

### A. DB Connection Defaults Fixed

**Problem**: Default credentials were not embedded, causing execution failures.

**Solution**: Embedded default credentials (gagan/gagan) for POC + GA.

**Changes**:
- Updated `test_helpers.py`: `get_test_db_connection()` now defaults to `gagan`/`gagan`
- Environment variables may override but absence must never break execution
- Defaults: `RANSOMEYE_DB_USER=gagan`, `RANSOMEYE_DB_PASSWORD=gagan`

**Code**:
```python
def get_test_db_connection():
    return psycopg2.connect(
        host=os.getenv("RANSOMEYE_DB_HOST", "localhost"),
        port=int(os.getenv("RANSOMEYE_DB_PORT", "5432")),
        database=os.getenv("RANSOMEYE_DB_NAME", "ransomeye"),
        user=os.getenv("RANSOMEYE_DB_USER", "gagan"),  # Default: gagan
        password=os.getenv("RANSOMEYE_DB_PASSWORD", "gagan")  # Default: gagan
    )
```

### B. Phase C Executor Hardened

**Problem**: DB failures could result in partial verdicts or unclear errors.

**Solution**: Added startup DB connectivity assertion and fail-fast behavior.

**Changes**:
1. **Startup DB Connectivity Assertion**:
   - Added `_assert_db_connectivity()` method
   - Called in `__init__` before any tracks execute
   - If DB connection fails → immediate fatal exit
   - No tracks execute
   - No partial verdict
   - Clear error message with default credentials

2. **Verdict Structure Safety**:
   - Verdict structure always initialized in `__init__`
   - Prevents KeyError if tracks don't execute
   - Safe defaults for all verdict fields

3. **Track Execution State**:
   - Added `tracks_executed` flag
   - `generate_final_report()` aborts if tracks didn't execute
   - Prevents computing verdict when execution failed

**Error Messages**:
```
FATAL: Database connectivity check failed.
Phase C validation requires database connection.
Error: [connection error]

Default credentials: gagan / gagan
Override with environment variables:
  RANSOMEYE_DB_HOST (default: localhost)
  RANSOMEYE_DB_PORT (default: 5432)
  RANSOMEYE_DB_NAME (default: ransomeye)
  RANSOMEYE_DB_USER (default: gagan)
  RANSOMEYE_DB_PASSWORD (default: gagan)
```

### C. OS Execution Boundaries Enforced

**Problem**: Linux could run Windows mode, Windows could run Linux tracks.

**Solution**: Enforced OS execution boundaries with clear fatal errors.

**Changes**:
1. **OS Boundary Enforcement**:
   - Added `_enforce_os_boundaries()` method
   - Called in `__init__` after mode detection
   - Linux refuses `--mode windows`
   - Windows refuses `--mode linux`
   - Clear fatal errors when violated

2. **Track Execution Guards**:
   - `_run_linux_tracks()` checks execution_mode == 'linux'
   - `_run_windows_tracks()` checks execution_mode == 'windows'
   - Fatal exit if violated

**Error Messages**:
```
FATAL: Cannot run Phase C-W (Windows mode) on Linux host.
Windows Agent validation must be run on native Windows host.
Use --mode linux or omit --mode to auto-detect.
```

```
FATAL: Cannot run Phase C-L (Linux mode) on Windows host.
Linux tracks must be run on Linux host.
Use --mode windows or omit --mode to auto-detect.
```

### D. GA Aggregation Fixed

**Problem**: Aggregator imported from executor, creating dependency issues.

**Solution**: Aggregator reads result JSONs only, no imports from executor.

**Changes**:
1. **Removed Executor Import**:
   - Removed `from validation.harness.phase_c_executor import PhaseCExecutor, TestStatus`
   - Added string constants: `TEST_STATUS_PASSED`, `TEST_STATUS_FAILED`, `TEST_STATUS_SKIPPED`
   - Aggregator is now standalone and module-safe

2. **JSON-Only Reading**:
   - Aggregator only reads JSON files
   - No runtime dependencies on executor
   - Can run independently after both Phase C-L and Phase C-W complete

**Code**:
```python
# Test status values (string constants, no import needed)
TEST_STATUS_PASSED = "passed"
TEST_STATUS_FAILED = "failed"
TEST_STATUS_SKIPPED = "skipped"
```

## Execution Commands

### Phase C-L (Linux)

```bash
# Auto-detect (Linux)
python3 -m validation.harness.phase_c_executor

# Explicit Linux mode
python3 -m validation.harness.phase_c_executor --mode linux

# With custom output directory
python3 -m validation.harness.phase_c_executor --mode linux --output-dir /path/to/output
```

**Default Credentials**: `gagan` / `gagan` (embedded)

**Override** (optional):
```bash
export RANSOMEYE_DB_USER="custom_user"
export RANSOMEYE_DB_PASSWORD="custom_password"
```

### Phase C-W (Windows)

```bash
# Auto-detect (Windows)
python validation\harness\phase_c_executor.py

# Explicit Windows mode
python validation\harness\phase_c_executor.py --mode windows
```

**Default Credentials**: `gagan` / `gagan` (embedded)

### GA Verdict Aggregation

```bash
# Standalone aggregator (no executor import)
python3 -m validation.harness.aggregate_ga_verdict \
  validation/reports/phase_c/phase_c_linux_results.json \
  validation/reports/phase_c/phase_c_windows_results.json
```

**Or directly**:
```bash
python3 validation/harness/aggregate_ga_verdict.py \
  phase_c_linux_results.json \
  phase_c_windows_results.json
```

## Fail-Fast Behavior

### DB Connectivity Failure

**Before any tracks execute**:
1. `PhaseCExecutor.__init__()` calls `_assert_db_connectivity()`
2. If DB connection fails → immediate `sys.exit(1)`
3. No tracks execute
4. No partial verdict
5. Clear error message

### OS Boundary Violation

**Before any tracks execute**:
1. `PhaseCExecutor.__init__()` calls `_enforce_os_boundaries()`
2. If Linux tries `--mode windows` → immediate `sys.exit(1)`
3. If Windows tries `--mode linux` → immediate `sys.exit(1)`
4. Clear error message

### Track Execution Failure

**During track execution**:
1. Exception caught in `run_all_tracks()`
2. Fatal error message printed
3. Immediate `sys.exit(1)`
4. No verdict computed

### Verdict Generation Safety

**After track execution**:
1. `generate_final_report()` checks `tracks_executed` flag
2. If `False` → immediate `sys.exit(1)`
3. Prevents computing verdict when execution failed
4. Clear error message

## Module-Safe Execution

### All Tools Run Via `python3 -m`

**Phase C-L**:
```bash
python3 -m validation.harness.phase_c_executor --mode linux
```

**Phase C-W**:
```bash
python3 -m validation.harness.phase_c_executor --mode windows
```

**GA Aggregation**:
```bash
python3 -m validation.harness.aggregate_ga_verdict linux.json windows.json
```

### Direct Script Execution

Direct script execution also works (imports are module-safe):
```bash
python3 validation/harness/phase_c_executor.py --mode linux
python3 validation/harness/aggregate_ga_verdict.py linux.json windows.json
```

## GA Verdict Logic

**GA_READY = Phase C-L PASS AND Phase C-W PASS**

**Rules Enforced**:
1. ✅ Any skipped mandatory test = FAIL
2. ✅ FAIL-006 cannot be skipped
3. ✅ AGENT-002 cannot be skipped
4. ✅ No partial or provisional GA allowed

**Aggregation Checks**:
- `linux_results.verdict == "PASS"`
- `windows_results.verdict == "PASS"`
- FAIL-006 not skipped in Linux results
- AGENT-002 not in Linux results (must be skipped)
- AGENT-002 in Windows results and passed
- No skipped mandatory tests

## Files Modified

1. **`validation/harness/test_helpers.py`**:
   - Updated `get_test_db_connection()` with default credentials (gagan/gagan)

2. **`validation/harness/phase_c_executor.py`**:
   - Added `_assert_db_connectivity()` method
   - Added `_enforce_os_boundaries()` method
   - Added `tracks_executed` flag
   - Added verdict structure initialization in `__init__`
   - Updated `generate_final_report()` to abort if tracks didn't execute
   - Updated `_run_linux_tracks()` and `_run_windows_tracks()` with OS guards

3. **`validation/harness/aggregate_ga_verdict.py`**:
   - Removed executor import
   - Added string constants for test status
   - Made aggregator standalone and module-safe

## Verification

✅ DB credentials embedded (gagan/gagan)
✅ Startup DB connectivity assertion working
✅ OS boundary enforcement working
✅ GA aggregation standalone (no executor import)
✅ Module-safe execution verified
✅ Fail-fast behavior verified

## Status

**Phase C execution is now credential-safe, OS-correct, fail-fast, and GA-reliable.**

---

**AUTHORITATIVE**: This document describes the build-integrity fixes for Phase C validation execution.
