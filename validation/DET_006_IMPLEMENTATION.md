# DET-006: Identity Disambiguation Determinism - Implementation Summary

**AUTHORITATIVE**: Implementation of DET-006 test for Phase C validation

## Overview

DET-006 has been added to Track 1 — Determinism to test identity disambiguation when the same PID is reused with different process start times or process GUIDs.

## Test Definition

### DET-006: Identity Disambiguation Determinism

**Objective**: Prove that same PID reused with different process start times/GUIDs produces distinct process identities across all pipeline stages, with deterministic behavior.

**Test Scenario**:
- Same PID reused (e.g., PID 1234)
- Different process start times (or process GUID)
- Appears across: raw_events, normalized events, correlation, forensic summarization

**Assertions**:
1. **Distinct process identities created** (no merge)
   - Same PID with different start times/GUIDs must be treated as distinct identities
   - No merging of process lineages

2. **No lineage merge**
   - Processes with same PID but different start times must maintain separate lineages
   - Parent-child relationships must not be incorrectly merged

3. **Deterministic behavior across runs**
   - Same inputs must produce same outputs (bit-exact hash match)
   - Non-LLM path → bit-exact hash match required

4. **Replay-safe (Identity Replay compatible)**
   - Process identities must be consistent across replay runs
   - Identity Replay (REP-A) must produce bit-exact matches

## Implementation Details

### Test Logic

The test (`test_det_006`) performs the following:

1. **Generate PID Reuse Events**:
   - Creates events where PID 1234 is reused 3 times
   - Each reuse has different process start time and process GUID
   - Uses deterministic seed for reproducibility

2. **Run 1 - Baseline**:
   - Ingests events with PID reuse
   - Captures event hashes
   - Extracts process identities (PID:start_time:guid)
   - Records normalized and correlation identities

3. **Run 2 - Verification**:
   - Ingests same events (same seed, same order)
   - Captures event hashes
   - Extracts process identities
   - Records normalized and correlation identities

4. **Assertions**:
   - **Distinct identities**: Verify unique identity count matches between runs
   - **No lineage merge**: Verify same PID has multiple distinct identities
   - **Deterministic**: Verify all hashes match exactly between runs
   - **Replay-safe**: Verify identities match between runs

### Helper Functions

- `generate_pid_reuse_events(seed)`: Generates events with PID reuse scenario
- `get_process_identities_from_normalized(conn)`: Gets process identities from normalized tables
- `get_process_identities_from_correlation(conn)`: Gets process identities from correlation data

## Integration

### Track 1 Updates

- ✅ DET-006 test added to `execute_track_1_determinism()`
- ✅ Test count updated from 5 to 6 tests
- ✅ Documentation updated

### Framework Updates

- ✅ Execution summary updated (35 tests total)
- ✅ Pass/fail criteria updated (DET-006 is non-LLM path)
- ✅ Evidence artifacts include DET-006 results

## Pass/Fail Criteria

**PASS**: 
- Distinct process identities created (no merge)
- No lineage merge detected
- Deterministic behavior (all hashes match exactly)
- Replay-safe (identities match across runs)

**FAIL**: 
- Process identities merged incorrectly
- Lineage merge detected
- Hash mismatches between runs
- Identity inconsistencies

## Evidence Artifacts

DET-006 results are included in:
- `determinism_proof_log.json`: Complete test results
- `determinism_proof_report.md`: Human-readable report

## Status

✅ **DET-006 implemented and integrated**

- Test logic implemented
- Framework integration complete
- Documentation updated
- Phase C execution unblocked

---

**AUTHORITATIVE**: This implementation satisfies the DET-006 requirement for Phase C validation.
