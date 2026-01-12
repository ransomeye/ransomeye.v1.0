# RansomEye Global Validator

**AUTHORITATIVE:** Deterministic assurance engine for end-to-end system integrity validation

## Overview

The RansomEye Global Validator is a foundational assurance subsystem that provides **provable correctness** for the entire RansomEye platform. It serves as the **final authority** on whether a deployment is trustworthy, consuming the **Audit Ledger as the root of truth** and producing **signed, auditable compliance reports**.

## Assurance Model & Threat Assumptions

### Assurance Model

The Global Validator provides **deterministic assurance** through:

1. **Complete System Validation**: Validates all components (Core, Agents, DPI) and their interactions
2. **Chain-of-Custody Verification**: Ensures every security-relevant action has a corresponding ledger entry
3. **Integrity Verification**: Detects tampering, drift, or unauthorized changes
4. **Cryptographic Proof**: All validation reports are cryptographically signed
5. **Deterministic Execution**: Same inputs always produce same outputs (no randomness, no trust assumptions)

### Threat Assumptions

The validator protects against:

1. **Tampering**: Modification or deletion of system components or configuration
2. **Gaps in Chain-of-Custody**: Missing ledger entries for security-relevant actions
3. **Silent Failures**: Actions that occur without being recorded in the ledger
4. **Configuration Drift**: Unauthorized changes to system configuration
5. **Integrity Breaches**: Installed artifacts that don't match release checksums

## Relationship to Audit Ledger

The Global Validator **consumes the Audit Ledger as the root of truth**:

- **Ledger as Source**: All validation checks use the Audit Ledger as the authoritative source
- **Ledger Verification**: First validation step is to verify ledger integrity (hash chain, signatures)
- **Chain-of-Custody**: Validator verifies that all security-relevant actions have corresponding ledger entries
- **No Bypass**: Validation cannot be bypassed - all checks are mandatory and fail-fast

### Separate Signing Keys

**CRITICAL**: Validator uses **separate signing keys** from the Audit Ledger:

- **Ledger Keys**: Used for signing ledger entries (managed by Audit Ledger)
- **Validator Keys**: Used for signing validation reports (managed by Global Validator)
- **Never Reused**: Validator never reuses ledger signing keys
- **Verification**: Reports must be signed with validator keys, not ledger keys

## What PASS Means (Legally and Operationally)

### Legal Meaning

A **PASS** validation report means:

1. **Integrity Proven**: All system components match release checksums (no tampering)
2. **Chain-of-Custody Complete**: Every security-relevant action has a corresponding ledger entry
3. **Ledger Integrity**: Audit ledger hash chain and signatures are valid
4. **Configuration Valid**: All configuration changes are authorized and recorded
5. **Cryptographic Proof**: Report is cryptographically signed and verifiable

**Legal Admissibility**: A PASS report provides cryptographic proof that the system is trustworthy and can be presented to auditors, regulators, or courts as evidence of system integrity.

### Operational Meaning

A **PASS** validation report means:

1. **System Trustworthy**: Deployment can be trusted for production use
2. **Compliance Verified**: System meets compliance requirements (SOC 2, ISO 27001, etc.)
3. **Forensic Ready**: System is ready for forensic analysis if needed
4. **Audit Trail Complete**: Complete audit trail exists for all security-relevant actions
5. **No Action Required**: No remediation needed - system is in correct state

## What FAIL Means (and Required Actions)

### Failure Classifications

A **FAIL** validation report includes a **failure classification**:

1. **INTEGRITY_BREACH**: System integrity compromised (tampering, unauthorized changes)
2. **MISSING_LEDGER_ENTRY**: Security-relevant action missing from ledger
3. **TAMPERING_DETECTED**: Installed artifacts don't match release checksums
4. **CONFIGURATION_DRIFT**: Unauthorized configuration changes detected
5. **INCOMPLETE_CHAIN_OF_CUSTODY**: Gaps in chain-of-custody detected
6. **SIMULATION_FAILURE**: Attack simulation failed to produce expected results

### Required Actions on FAIL

When validation **FAILS**, the following actions are **mandatory**:

1. **Immediate Investigation**: Investigate first failure location and error
2. **System Isolation**: If integrity breach or tampering detected, isolate system immediately
3. **Ledger Review**: Review audit ledger for missing entries or gaps
4. **Remediation**: Fix identified issues and re-run validation
5. **Documentation**: Document failure and remediation in incident log
6. **Re-validation**: Re-run validation after remediation to confirm PASS

**No Production Use**: System **MUST NOT** be used in production until validation **PASSES**.

## Determinism Guarantees

The Global Validator provides **strict determinism guarantees**:

1. **No Randomness**: Validation uses no random number generation
2. **No Wall-Clock Trust**: Validation doesn't rely on system clock (uses ledger timestamps)
3. **No Sleeps**: Validation doesn't use sleep or delays
4. **Fixed Ordering**: Checks are always executed in the same order
5. **Same Input → Same Output**: Same inputs always produce same outputs

### Deterministic Execution

Validation execution is **fully deterministic**:

- **Inputs**: Ledger file, public keys, checksums, manifests, configs
- **Processing**: Fixed-order checks with no randomness
- **Outputs**: Signed validation report (deterministic JSON)

**Result**: Validation can be **reproduced** by anyone with the same inputs, providing cryptographic proof of system state.

## How to Present Reports to Auditors / Regulators

### Report Formats

Validation reports are available in three formats:

1. **JSON** (Authoritative): Machine-readable, cryptographically signed
2. **PDF** (Human/Compliance): Human-readable, suitable for compliance documentation
3. **CSV** (Regulatory Ingestion): Structured format for regulatory systems

### Verification Process

To verify a validation report:

1. **Load Public Key**: Load validator public key from key directory
2. **Verify Signature**: Verify report signature using validator public key
3. **Verify Hash**: Verify report hash matches calculated hash
4. **Review Results**: Review validation status and failure details

### Presenting to Auditors

When presenting validation reports to auditors:

1. **Provide All Formats**: Provide JSON (authoritative), PDF (human-readable), and CSV (if needed)
2. **Include Public Key**: Provide validator public key for signature verification
3. **Explain Process**: Explain validation process and what PASS/FAIL means
4. **Show Chain-of-Custody**: Show how validation verifies chain-of-custody from ledger
5. **Demonstrate Determinism**: Demonstrate that validation is deterministic and reproducible

### Legal Admissibility

Validation reports are **legally admissible** as evidence because:

1. **Cryptographic Proof**: Reports are cryptographically signed (non-repudiation)
2. **Deterministic**: Validation is deterministic and reproducible
3. **Complete**: Reports include all validation checks and results
4. **Auditable**: Reports can be verified independently by auditors

## Validation Checks

### 1. Audit Ledger Integrity

**Purpose**: Verify audit ledger integrity (hash chain, signatures, key continuity)

**Checks**:
- Full ledger replay
- Hash chain verification (prev_entry_hash matches previous entry_hash)
- Signature verification (all entries signed with valid keys)
- Key continuity (all entries use same key or documented rotation)

**Failure**: If ledger integrity fails, all other checks are skipped (fail-fast)

### 2. Installer & Binary Integrity

**Purpose**: Verify installed artifacts match release checksums

**Checks**:
- Hash verification of installed binaries, scripts, services
- Match against release SHA256SUMS
- Detection of drift or tampering

**Failure**: If integrity fails, tampering is detected and system is untrustworthy

### 3. Configuration Integrity

**Purpose**: Detect unauthorized configuration changes

**Checks**:
- Configuration file hash verification
- Comparison with ledger-recorded config hashes
- Detection of unauthorized changes

**Failure**: If config integrity fails, unauthorized changes detected

### 4. Chain-of-Custody

**Purpose**: Verify complete chain from ingest → correlation → AI → policy → response

**Checks**:
- Verify all security-relevant actions have ledger entries
- Detect gaps in chain-of-custody
- Detect silent transitions (actions without ledger entries)

**Failure**: If chain-of-custody fails, gaps or silent transitions detected

### 5. Subsystem Disablement Correctness

**Purpose**: Prove system correctness when subsystems are disabled

**Checks**:
- Verify system correctness when AI disabled
- Verify system correctness when Policy disabled
- Verify system correctness when UI disabled
- Evidence must exist in ledger

**Failure**: If disablement correctness fails, system state is invalid

### 6. Synthetic Attack Simulation (Non-Destructive)

**Purpose**: Simulate ransomware attack without altering production state

**Checks**:
- Deterministic simulated ransomware scenario
- Verify detection path (ingest → correlation → AI)
- Verify response path (policy → enforcement)
- All simulation actions recorded in ledger

**Failure**: If simulation fails, detection or response paths are broken

## Usage

### Basic Validation

Run validation with minimal inputs:

```bash
python3 global-validator/cli/run_validation.py \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --validator-key-dir /var/lib/ransomeye/validator/keys \
    --output validation-report.json
```

### Full Validation

Run validation with all checks:

```bash
python3 global-validator/cli/run_validation.py \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --validator-key-dir /var/lib/ransomeye/validator/keys \
    --release-checksums /opt/ransomeye/release/checksums/SHA256SUMS \
    --component-manifests /opt/ransomeye/core/installer.manifest.json /opt/ransomeye/linux-agent/installer.manifest.json \
    --config-snapshots /opt/ransomeye/core/config/environment /opt/ransomeye/linux-agent/config/environment \
    --run-simulation \
    --output validation-report.json
```

### Generate PDF Report

```python
from reports.render_pdf import render_pdf
import json

report = json.loads(open('validation-report.json').read())
render_pdf(report, Path('validation-report.pdf'))
```

### Generate CSV Report

```python
from reports.render_csv import render_csv
import json

report = json.loads(open('validation-report.json').read())
render_csv(report, Path('validation-report.csv'))
```

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **cryptography**: Required for ed25519 signing/verification
  - Install: `pip install cryptography`
- **reportlab**: Optional, for PDF rendering
  - Install: `pip install reportlab`

## File Structure

```
global-validator/
├── schema/
│   └── validation-report.schema.json    # Frozen JSON schema
├── crypto/
│   ├── __init__.py
│   ├── validator_key_manager.py         # Validator keypair management
│   ├── signer.py                         # Report signing
│   └── verifier.py                       # Report verification
├── checks/
│   ├── __init__.py
│   ├── ledger_checks.py                  # Ledger integrity checks
│   ├── integrity_checks.py               # Installer/binary integrity checks
│   ├── custody_checks.py                 # Chain-of-custody checks
│   ├── config_checks.py                  # Configuration integrity checks
│   └── simulation_checks.py             # Attack simulation checks
├── cli/
│   ├── __init__.py
│   └── run_validation.py                # Validation runner CLI
├── reports/
│   ├── __init__.py
│   ├── render_pdf.py                     # PDF report renderer
│   └── render_csv.py                     # CSV report renderer
└── README.md                             # This file
```

## Security Considerations

1. **Separate Keys**: Validator uses separate signing keys from Audit Ledger
2. **Key Protection**: Validator private keys must be protected (0o600 permissions)
3. **Report Verification**: Always verify report signatures before trusting results
4. **Fail-Fast**: Validation stops on first failure (fail-fast semantics)
5. **Deterministic**: Validation is deterministic and reproducible

## Limitations

1. **File-Based**: Phase A2 uses file-based inputs (ledger, checksums, manifests)
2. **Offline-Capable**: Validation requires no network or database (offline-capable)
3. **Deterministic**: Validation is fully deterministic (no randomness, no trust assumptions)

## Future Enhancements

- Real-time validation monitoring
- Automated validation scheduling
- Integration with compliance frameworks
- Advanced attack simulation scenarios
- Distributed validation support

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye Global Validator documentation.
