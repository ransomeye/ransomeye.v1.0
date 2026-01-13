# Phase C Execution Prerequisites Hardening

**AUTHORITATIVE**: Prerequisites hardening for Phase C validation execution

## Overview

Phase C execution prerequisites have been hardened to ensure all 35 tests are actually runnable. Execution will **FAIL FAST** with explicit error messages if required prerequisites are missing.

## Changes Implemented

### 1. FAIL-006: Database Restart Authority

**Problem**: FAIL-006 requires database restart capability but had no explicit authority selection.

**Solution**: Added explicit execution authority selection with fail-fast validation.

**Environment Variables**:
- `RANSOMEYE_DB_RESTART_MODE` (required for FAIL-006)
  - Must be `docker` or `systemd`
  - If not set → FAIL-006 is **SKIPPED** with explicit warning

**Option A — Docker**:
- `RANSOMEYE_DB_RESTART_MODE=docker`
- `RANSOMEYE_DB_CONTAINER_NAME` (required) - Docker container name
- Validation: Checks container name is provided

**Option B — Systemd**:
- `RANSOMEYE_DB_RESTART_MODE=systemd`
- Requires sudo privileges
- Optional: `RANSOMEYE_DB_SERVICE_NAME` (default: postgresql)
- Validation: Checks sudo is available

**Failure Behavior**:
- Invalid mode → FAIL FAST with error
- Docker mode without container name → FAIL FAST with error
- Systemd mode without sudo → FAIL FAST with error
- Not configured → FAIL-006 SKIPPED (other tests continue)

**Implementation**: `test_fail_006_database_restart()` in `track_3_failure.py`

### 2. Agent Reality Check Binaries

**Problem**: AGENT-001 and AGENT-002 had no mandatory binary path requirements.

**Solution**: Added mandatory environment variables with fail-fast validation.

**Environment Variables**:
- `RANSOMEYE_AGENT_BIN_LINUX` (required for AGENT-001)
  - Full path to Linux agent binary
  - Must exist and be executable
  - No PATH lookup, no defaults

- `RANSOMEYE_AGENT_BIN_WINDOWS` (required for AGENT-002)
  - Full path to Windows agent binary
  - Must exist and be executable
  - No PATH lookup, no defaults

**Validation**:
- Harness verifies binaries exist (Path.exists())
- Harness verifies executability (os.access(path, os.X_OK))
- **FAIL FAST** if missing or not executable

**Failure Messages**:
- Not set → "RANSOMEYE_AGENT_BIN_LINUX is required for AGENT-001"
- Does not exist → "RANSOMEYE_AGENT_BIN_LINUX does not exist: {path}"
- Not executable → "RANSOMEYE_AGENT_BIN_LINUX is not executable: {path}"

**Implementation**: 
- Prerequisite validation in `PhaseCExecutor.validate_prerequisites()`
- Test validation in `test_agent_001_linux_real_vs_simulator()` and `test_agent_002_windows_real_vs_simulator()` in `track_6_agent.py`

### 3. SCALE-004 Topology Clarification

**Problem**: Unclear whether Phase C orchestrates deployment topology.

**Solution**: Updated documentation and harness logic to clarify responsibilities.

**Clarification**:
- **Phase C does not orchestrate deployment**
- **Topology (co-located vs distributed) is pre-configured**
- Harness only measures:
  - Latency (p50, p95, p99)
  - IO wait
  - Queue depth
  - Contention
- **No environment manipulation allowed**

**Implementation**: Updated `test_scale_004_colocated()` documentation and added note in metrics output.

### 4. Prerequisites Documentation

**Updated**: `PHASE_C_EXECUTION_SUMMARY.md`

**Added Sections**:
1. Database Restart Authority (FAIL-006 requirements)
2. Agent Binaries (AGENT-001 and AGENT-002 requirements)
3. Topology Configuration (SCALE-004 clarification)
4. Prerequisite validation output examples
5. Failure message examples

## Prerequisite Validation Flow

### Execution Start

1. **PhaseCExecutor.run_all_tracks()** is called
2. **validate_prerequisites()** is executed
3. If errors found → **FAIL FAST** with explicit error messages
4. If warnings found → Display warnings, continue execution
5. If valid → Continue to test execution

### Validation Checks

**Database Restart (FAIL-006)**:
- Check `RANSOMEYE_DB_RESTART_MODE` is valid (docker/systemd) or empty
- If docker: Check `RANSOMEYE_DB_CONTAINER_NAME` is set
- If systemd: Check sudo is available
- If not configured: Add warning (test will be skipped)

**Agent Binaries (AGENT-001, AGENT-002)**:
- Check `RANSOMEYE_AGENT_BIN_LINUX` is set
- Check `RANSOMEYE_AGENT_BIN_LINUX` exists
- Check `RANSOMEYE_AGENT_BIN_LINUX` is executable
- Same checks for `RANSOMEYE_AGENT_BIN_WINDOWS`
- If any check fails → Add error (execution blocked)

## Updated Prerequisites List

### Required for All Tests

1. **Database Connection**:
   - `RANSOMEYE_DB_PASSWORD` (required)
   - `RANSOMEYE_DB_HOST` (default: localhost)
   - `RANSOMEYE_DB_PORT` (default: 5432)
   - `RANSOMEYE_DB_NAME` (default: ransomeye)
   - `RANSOMEYE_DB_USER` (default: ransomeye)

2. **Database Schema**: All required tables must exist

### Required for Specific Tests

3. **FAIL-006 (Database Restart)**:
   - `RANSOMEYE_DB_RESTART_MODE` (docker or systemd, or empty to skip)
   - If docker: `RANSOMEYE_DB_CONTAINER_NAME` (required)
   - If systemd: sudo privileges required

4. **AGENT-001 (Linux Agent)**:
   - `RANSOMEYE_AGENT_BIN_LINUX` (required, full path, must exist and be executable)

5. **AGENT-002 (Windows Agent)**:
   - `RANSOMEYE_AGENT_BIN_WINDOWS` (required, full path, must exist and be executable)

### Pre-Configured (Not Orchestrated by Phase C)

6. **SCALE-004 (Topology)**: Deployment topology must be pre-configured. Harness only measures metrics.

## Execution-Blocking Checks

### Fail Fast Conditions

Execution will **FAIL FAST** (exit with error) if:

1. **Agent Binaries Missing**:
   - `RANSOMEYE_AGENT_BIN_LINUX` not set
   - `RANSOMEYE_AGENT_BIN_LINUX` does not exist
   - `RANSOMEYE_AGENT_BIN_LINUX` not executable
   - Same for `RANSOMEYE_AGENT_BIN_WINDOWS`

2. **Invalid DB Restart Mode**:
   - `RANSOMEYE_DB_RESTART_MODE` set to invalid value (not docker/systemd/empty)
   - Docker mode without `RANSOMEYE_DB_CONTAINER_NAME`
   - Systemd mode without sudo

### Skip Conditions (Non-Blocking)

Tests will be **SKIPPED** (with explicit message) if:

1. **FAIL-006**: `RANSOMEYE_DB_RESTART_MODE` not configured
   - Test status: SKIPPED
   - Skip reason: "RANSOMEYE_DB_RESTART_MODE not configured. Set to 'docker' or 'systemd' to enable FAIL-006."

## Test Runnability Status

### All 35 Tests Status

✅ **All 35 tests are now runnable** with proper prerequisites:

- **Track 1 (6 tests)**: DET-001 through DET-006 - ✅ Runnable
- **Track 2 (10 tests)**: REP-A-001 through REP-A-005, REP-B-001 through REP-B-005 - ✅ Runnable
- **Track 3 (6 tests)**: 
  - FAIL-001 through FAIL-005 - ✅ Runnable
  - FAIL-006 - ✅ Runnable (with DB restart mode) or ⚠️ Skipped (without)
- **Track 4 (5 tests)**: SCALE-001 through SCALE-005 - ✅ Runnable
- **Track 5 (6 tests)**: SEC-001 through SEC-006 - ✅ Runnable
- **Track 6 (2 tests)**: 
  - AGENT-001 - ✅ Runnable (with Linux binary)
  - AGENT-002 - ✅ Runnable (with Windows binary)

## Files Modified

1. **`validation/harness/phase_c_executor.py`**:
   - Added `validate_prerequisites()` method
   - Added prerequisite validation to `run_all_tracks()`
   - Added prerequisites storage in executor

2. **`validation/harness/track_3_failure.py`**:
   - Updated `test_fail_006_database_restart()` with DB restart mode validation
   - Added Docker and systemd restart logic
   - Added skip logic when not configured

3. **`validation/harness/track_6_agent.py`**:
   - Updated `test_agent_001_linux_real_vs_simulator()` with binary validation
   - Updated `test_agent_002_windows_real_vs_simulator()` with binary validation
   - Added fail-fast checks for missing/invalid binaries

4. **`validation/harness/track_4_scale.py`**:
   - Updated `test_scale_004_colocated()` documentation
   - Added topology responsibility clarification

5. **`validation/PHASE_C_EXECUTION_SUMMARY.md`**:
   - Added comprehensive prerequisites section
   - Added DB restart authority requirements
   - Added agent binary requirements
   - Added topology clarification
   - Added failure message examples

## Verification

✅ Prerequisite validation tested and working
✅ Fail-fast behavior verified
✅ Skip behavior verified (FAIL-006)
✅ Error messages explicit and actionable

## Status

**Phase C execution prerequisites hardened. Validation can now run.**

All 35 tests are runnable with proper prerequisites. Execution will fail fast with explicit error messages if required prerequisites are missing, ensuring clear feedback for operators.

---

**AUTHORITATIVE**: This document describes the hardened prerequisites for Phase C validation execution.
