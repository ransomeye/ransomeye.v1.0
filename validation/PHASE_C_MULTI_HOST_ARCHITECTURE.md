# Phase C Multi-Host Validation Architecture

**AUTHORITATIVE**: Multi-host execution model for Phase C Global GA Validation

## Overview

RansomEye is a multi-OS system. Linux and Windows agents cannot be validated on the same host. ETW is Windows-only and cannot run on Linux. GA certification must be technically defensible.

Phase C validation is implemented as a **two-run, multi-host validation process** with a single authoritative GA verdict.

## Execution Model

### Phase C-L (Linux Execution)

**Runs on**: Linux host

**Mandatory Tracks**:
- **Track 1**: Determinism (DET-001 → DET-006)
- **Track 2**: Replay (REP-A Identity, REP-B Evolution)
- **Track 3**: Failure Injection (FAIL-001 → FAIL-006)
- **Track 4**: Scale & Stress (with Disk I/O wait, Queue depth)
- **Track 5**: Security & Safety
- **Track 6-A**: Agent Reality Check — Linux Agent only

**Output Artifact (MANDATORY)**:
- `phase_c_linux_results.json`

**Execution**:
```bash
python3 validation/harness/phase_c_executor.py --mode linux
```

### Phase C-W (Windows Execution)

**Runs on**: Native Windows host

**Mandatory Tracks**:
- **Track 6-B**: Agent Reality Check — Windows Agent (ETW)

**What must be validated**:
- ETW event capture
- Normalization correctness
- PID reuse disambiguation
- Functional parity with simulator
- Deterministic schema output

**Output Artifact (MANDATORY)**:
- `phase_c_windows_results.json`

**Execution**:
```bash
python validation\harness\phase_c_executor.py --mode windows
```

## GA Verdict Logic (Non-Negotiable)

**GA verdict must be computed as:**

```
GA_READY = 
  phase_c_linux_results.PASS == true
  AND
  phase_c_windows_results.PASS == true
```

### Rules

1. **Any skipped mandatory test = FAIL**
   - All mandatory tests must execute and pass
   - No skipped tests allowed

2. **FAIL-006 cannot be skipped**
   - Database restart test must execute on Linux
   - Skipping FAIL-006 = GA blocked

3. **AGENT-002 cannot be skipped**
   - Windows Agent test must execute on Windows
   - Skipping AGENT-002 = GA blocked

4. **No partial or provisional GA allowed**
   - Both Phase C-L and Phase C-W must pass
   - No exceptions, no partial certifications

## Harness Requirements

### Linux Harness Behavior

**Must**:
- Execute Tracks 1-5 + Track 6-A (Linux Agent)
- Refuse to run AGENT-002
- Explicitly state: "Windows Agent validation must be run on Windows host"
- Skip AGENT-002 with explicit skip reason
- Produce `phase_c_linux_results.json`

**Implementation**:
- `track_6_agent_linux.py` executes only AGENT-001
- AGENT-002 is explicitly skipped with message
- Skip reason: "Windows Agent validation must be run on Windows host. Phase C-W execution required for AGENT-002."

### Windows Harness Behavior

**Must**:
- Run only Track 6-B (Windows Agent/ETW)
- Validate ETW via real agent execution
- Produce standalone results file
- Produce `phase_c_windows_results.json`

**Implementation**:
- `track_6_agent_windows.py` executes only AGENT-002
- Validates ETW event capture, normalization, PID reuse disambiguation
- Functional parity with simulator
- Deterministic schema output

## GA Verdict Aggregation

### Aggregation Process

1. **Run Phase C-L on Linux host**
   - Produces `phase_c_linux_results.json`

2. **Run Phase C-W on Windows host**
   - Produces `phase_c_windows_results.json`

3. **Aggregate verdict**
   ```bash
   python3 validation/harness/aggregate_ga_verdict.py \
     phase_c_linux_results.json \
     phase_c_windows_results.json
   ```

### Aggregation Logic

The aggregator checks:

1. **Phase C-L passed**: `linux_results.verdict == "PASS"`
2. **Phase C-W passed**: `windows_results.verdict == "PASS"`
3. **FAIL-006 not skipped**: Check Linux results for FAIL-006 status
4. **AGENT-002 not in Linux**: AGENT-002 must be skipped in Linux results
5. **AGENT-002 in Windows**: AGENT-002 must exist and pass in Windows results
6. **No skipped mandatory tests**: Both results must have 0 skipped tests

**Final GA Verdict**:
- ✅ **GA-READY**: All checks pass
- ❌ **NOT GA-READY**: Any check fails

## Execution Flow

### Phase C-L Execution (Linux)

```
1. Detect OS (Linux)
2. Execute Track 1: Determinism
3. Execute Track 2: Replay
4. Execute Track 3: Failure Injection
5. Execute Track 4: Scale & Stress
6. Execute Track 5: Security & Safety
7. Execute Track 6-A: Linux Agent (AGENT-001)
8. Skip AGENT-002 (explicit message)
9. Generate phase_c_linux_results.json
```

### Phase C-W Execution (Windows)

```
1. Detect OS (Windows)
2. Execute Track 6-B: Windows Agent (AGENT-002)
3. Validate ETW event capture
4. Validate normalization correctness
5. Validate PID reuse disambiguation
6. Validate functional parity
7. Validate deterministic schema
8. Generate phase_c_windows_results.json
```

### GA Verdict Aggregation

```
1. Load phase_c_linux_results.json
2. Load phase_c_windows_results.json
3. Check Phase C-L passed
4. Check Phase C-W passed
5. Check FAIL-006 not skipped
6. Check AGENT-002 not in Linux
7. Check AGENT-002 in Windows and passed
8. Compute final GA verdict
9. Generate phase_c_aggregate_verdict.json
```

## Output Artifacts

### Phase C-L Artifacts

- `phase_c_linux_results.json` (MANDATORY)
- `phase_c_linux_report.md`
- Track-specific artifacts (determinism, replay, failure, scale, security, agent)

### Phase C-W Artifacts

- `phase_c_windows_results.json` (MANDATORY)
- `phase_c_windows_report.md`
- `agent_reality_check_windows_results.json`

### Aggregate Verdict

- `phase_c_aggregate_verdict.json`
- Final GA verdict (GA-READY or NOT GA-READY)

## OS Detection

The harness automatically detects the OS:

- **Linux**: `platform.system() == 'Linux'` → Phase C-L mode
- **Windows**: `platform.system() == 'Windows'` → Phase C-W mode
- **Other**: Raises error (unsupported platform)

Manual override available:
```bash
python3 validation/harness/phase_c_executor.py --mode linux
python3 validation/harness/phase_c_executor.py --mode windows
```

## Validation Matrix

| Test | Phase C-L (Linux) | Phase C-W (Windows) | Mandatory |
|------|-------------------|---------------------|-----------|
| DET-001 to DET-006 | ✅ Execute | ❌ N/A | ✅ Yes |
| REP-A-001 to REP-A-005 | ✅ Execute | ❌ N/A | ✅ Yes |
| REP-B-001 to REP-B-005 | ✅ Execute | ❌ N/A | ✅ Yes |
| FAIL-001 to FAIL-005 | ✅ Execute | ❌ N/A | ✅ Yes |
| FAIL-006 | ✅ Execute (cannot skip) | ❌ N/A | ✅ Yes |
| SCALE-001 to SCALE-005 | ✅ Execute | ❌ N/A | ✅ Yes |
| SEC-001 to SEC-006 | ✅ Execute | ❌ N/A | ✅ Yes |
| AGENT-001 | ✅ Execute | ❌ N/A | ✅ Yes |
| AGENT-002 | ⚠️ Skip (explicit) | ✅ Execute (cannot skip) | ✅ Yes |

## Error Handling

### Linux Harness

- **AGENT-002 attempted**: Explicitly skipped with message
- **Windows OS detected**: Error (should run Phase C-W on Windows)

### Windows Harness

- **Tracks 1-5 attempted**: Error (should run Phase C-L on Linux)
- **AGENT-001 attempted**: Error (should run Phase C-L on Linux)
- **AGENT-002 missing**: FAIL (mandatory test)

### Aggregation

- **Missing Linux results**: Error
- **Missing Windows results**: Error
- **FAIL-006 skipped**: GA blocked
- **AGENT-002 skipped**: GA blocked
- **AGENT-002 in Linux**: GA blocked (should be skipped)

## Status

**Phase C execution model corrected. GA validation is now OS-correct and audit-safe.**

---

**AUTHORITATIVE**: This architecture defines the multi-host execution model for Phase C validation.
