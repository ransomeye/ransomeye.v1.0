# RansomEye v1.0 GA Readiness Checklist

**AUTHORITATIVE:** GA readiness verification checklist

## Checklist Overview

This checklist verifies that RansomEye is GA-ready across all critical dimensions:
- **Determinism**: Same input → same output (bit-for-bit)
- **Replay**: Full system replay capability
- **Failure Handling**: Graceful degradation, no corruption
- **Scale**: 1M+ events, acceptable latency
- **Audit**: Complete, tamper-evident audit trail

## Determinism Checklist

### DET-001: Detection Determinism
- [ ] Same agent telemetry → same `raw_events` (bit-for-bit)
- [ ] All `event_id` values match
- [ ] All `payload` hashes match
- [ ] Evidence: `determinism_proof_log.json`

### DET-002: Normalization Determinism
- [ ] Same `raw_events` → same normalized events (bit-for-bit)
- [ ] All normalized row hashes match
- [ ] All `event_id` mappings match
- [ ] All field values match (no rounding, no truncation)
- [ ] Evidence: `determinism_proof_log.json`

### DET-003: Correlation Determinism
- [ ] Same normalized events → same incidents (bit-for-bit)
- [ ] All `incident_id` values match
- [ ] All `confidence_score` values match (if deterministic)
- [ ] All `stage` assignments match
- [ ] All evidence links match
- [ ] Evidence: `determinism_proof_log.json`

### DET-004: Forensics Determinism
- [ ] Same incidents → same forensic summaries (bit-for-bit)
- [ ] All JSON summary hashes match (canonical JSON)
- [ ] All text summary hashes match (character-for-character)
- [ ] All graph metadata hashes match
- [ ] Evidence: `determinism_proof_log.json`

**Determinism Status**: ⬜ PASS / ⬜ FAIL

---

## Replay Checklist

### REP-001: Normalized Events Replay
- [ ] `raw_events` can be replayed to rebuild normalized events identically
- [ ] All normalized row hashes match
- [ ] All `event_id` mappings match
- [ ] All field values match
- [ ] Evidence: `replay_verification_log.json`

### REP-002: Incidents Replay
- [ ] Normalized events can be replayed to rebuild incidents identically
- [ ] All `incident_id` values match
- [ ] All `confidence_score` values match
- [ ] All `stage` assignments match
- [ ] Evidence: `replay_verification_log.json`

### REP-003: Evidence Replay
- [ ] Incidents can be replayed to rebuild evidence identically
- [ ] All evidence link hashes match
- [ ] All `event_id` references match
- [ ] Evidence: `replay_verification_log.json`

### REP-004: Forensic Summaries Replay
- [ ] Incidents can be replayed to rebuild forensic summaries identically
- [ ] All JSON summary hashes match
- [ ] All text summary hashes match
- [ ] All graph metadata hashes match
- [ ] Evidence: `replay_verification_log.json`

**Replay Status**: ⬜ PASS / ⬜ FAIL

---

## Failure Handling Checklist

### FAIL-001: DB Restart (Mid-Transaction)
- [ ] DB restart during transaction does not cause corruption
- [ ] Transaction rolled back correctly
- [ ] No partial writes
- [ ] Event can be re-ingested (idempotent)
- [ ] Audit log entry for restart
- [ ] Evidence: `failure_injection_results.json`

### FAIL-002: Queue Overflow
- [ ] Queue overflow triggers backpressure without silent loss
- [ ] Queue depth monitored
- [ ] Backpressure signal sent to agents
- [ ] Events buffered (not dropped silently)
- [ ] Audit log entry for queue overflow
- [ ] Evidence: `failure_injection_results.json`

### FAIL-003: Agent Disconnect
- [ ] Agent disconnect detected and logged without corruption
- [ ] Sequence gap detected
- [ ] Gap logged in `sequence_gaps` table
- [ ] Audit ledger entry created
- [ ] Processing continues (fail-open)
- [ ] Evidence: `failure_injection_results.json`

### FAIL-004: Duplicate Events
- [ ] Duplicate events handled idempotently
- [ ] First ingestion succeeds
- [ ] Second ingestion skipped (idempotent)
- [ ] No duplicate rows in `raw_events`
- [ ] Audit log entry for duplicate detection
- [ ] Evidence: `failure_injection_results.json`

### FAIL-005: Partial Writes
- [ ] Partial writes rolled back atomically
- [ ] Transaction rolled back correctly
- [ ] No partial writes
- [ ] Event can be re-ingested
- [ ] Audit log entry for rollback
- [ ] Evidence: `failure_injection_results.json`

**Failure Handling Status**: ⬜ PASS / ⬜ FAIL

---

## Scale Checklist

### SCALE-001: Burst Ingestion (10K/sec)
- [ ] System handles burst ingestion (10K events/sec)
- [ ] Latency: p99 < 1s
- [ ] Backpressure: Queue depth < 10K
- [ ] CPU: Per-service < 80%
- [ ] Memory: Per-service < 2GB
- [ ] DB: No lock contention, WAL growth acceptable
- [ ] Evidence: `scale_validation_metrics.json`

### SCALE-002: Sustained Load (1K/sec)
- [ ] System handles sustained load (1K events/sec) over 1 hour
- [ ] Latency: p99 < 5s
- [ ] Backpressure: Queue depth < 1K
- [ ] CPU: Per-service < 50%
- [ ] Memory: Per-service < 2GB
- [ ] DB: No lock contention, WAL growth acceptable, no table bloat
- [ ] Evidence: `scale_validation_metrics.json`

### SCALE-003: POC Single-Host Mode
- [ ] Core + DPI + Linux Agent can run on same host without conflicts
- [ ] CPU isolation: Per-service CPU usage (no starvation)
- [ ] Memory isolation: Per-service memory usage (no OOM)
- [ ] IO isolation: Per-service IO usage (no starvation)
- [ ] Port conflicts: None
- [ ] Performance: Acceptable latency despite co-location
- [ ] Evidence: `scale_validation_metrics.json`

**Scale Status**: ⬜ PASS / ⬜ FAIL

---

## Audit Checklist

### AUDIT-001: Ledger Integrity
- [ ] Audit ledger maintains hash chain integrity
- [ ] All hash chains valid (prev_entry_hash matches previous entry_hash)
- [ ] All signatures valid (ed25519 signatures)
- [ ] All timestamps monotonic
- [ ] Evidence: `audit_integrity_verification.json`

### AUDIT-002: Coverage Analysis
- [ ] All security-relevant actions are logged
- [ ] Installer actions logged
- [ ] Service lifecycle events logged
- [ ] Policy decisions logged
- [ ] AI model lifecycle actions logged
- [ ] Playbook execution logged
- [ ] Forensic access logged
- [ ] Administrative actions logged
- [ ] No silent actions
- [ ] Evidence: `audit_coverage_report.json`

### AUDIT-003: Compliance Verification
- [ ] SOC 2 requirements met (access control and audit)
- [ ] ISO 27001 requirements met (audit logging)
- [ ] HIPAA requirements met (audit trail)
- [ ] PCI DSS requirements met (audit logging)
- [ ] GDPR requirements met (audit trail)
- [ ] Audit trail exportable
- [ ] Audit trail immutable
- [ ] Evidence: `audit_compliance_report.json`

**Audit Status**: ⬜ PASS / ⬜ FAIL

---

## Overall GA Readiness

### Summary

| Category | Status | Evidence |
|----------|--------|----------|
| **Determinism** | ⬜ PASS / ⬜ FAIL | `determinism_proof_log.json` |
| **Replay** | ⬜ PASS / ⬜ FAIL | `replay_verification_log.json` |
| **Failure Handling** | ⬜ PASS / ⬜ FAIL | `failure_injection_results.json` |
| **Scale** | ⬜ PASS / ⬜ FAIL | `scale_validation_metrics.json` |
| **Audit** | ⬜ PASS / ⬜ FAIL | `audit_integrity_verification.json`, `audit_coverage_report.json`, `audit_compliance_report.json` |

### GA Readiness Verdict

**Overall Status**: ⬜ GA-READY / ⬜ NOT GA-READY

**Rationale**:
- [ ] All P0 tests pass
- [ ] All evidence artifacts generated
- [ ] All validation reports complete
- [ ] Signed validation report generated (PDF/JSON)

### Residual Risks

List any residual risks that do not block GA but should be documented:

1. **Risk**: [Description]
   - **Mitigation**: [Mitigation strategy]
   - **Acceptable**: Yes/No

2. **Risk**: [Description]
   - **Mitigation**: [Mitigation strategy]
   - **Acceptable**: Yes/No

---

**AUTHORITATIVE**: This checklist is the single authoritative source for GA readiness verification.

**STATUS**: Checklist defined. Ready for validation execution.
