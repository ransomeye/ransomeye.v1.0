# Phase 8.4 Independent Verification & Forensic Rehydration

## Overview

Independent verification provides a **read-only, third-party verification mechanism** that allows auditors, customers, regulators, and incident response teams to independently verify production readiness **without running RansomEye, without CI, and without trust in the build system**.

This is the **final technical gate** before customer delivery.

## Why Independent Verification Matters

### For Auditors

- **Zero Trust**: Verify evidence bundle without trusting the build system
- **Reproducible**: Same inputs always produce same verification results
- **Forensic**: Reconstruct validation state from frozen evidence
- **Defensible**: Cryptographically provable verification process

### For Customers

- **Pre-Delivery Verification**: Verify release readiness before accepting delivery
- **Compliance**: Meet regulatory requirements for software integrity
- **Risk Assessment**: Understand validation coverage and gaps
- **Transparency**: Independent verification of vendor claims

### For Regulators

- **Audit Trail**: Complete, tamper-evident audit trail
- **Reproducibility**: Verification can be repeated by any party
- **Accountability**: Cryptographic proof of validation state
- **Compliance**: Meets requirements for software supply chain security

### For IR Teams

- **Forensic Rehydration**: Reconstruct validation state from evidence
- **Incident Analysis**: Verify what was validated before deployment
- **Root Cause**: Understand validation gaps that may have contributed to incidents
- **Evidence Preservation**: Immutable evidence for post-incident analysis

## How Auditors/Customers Use This

### Step 1: Obtain Evidence Bundle

Obtain the following files from the vendor:

- `validation/evidence_bundle/evidence_bundle.json`
- `validation/evidence_bundle/evidence_bundle.json.sig`
- Public key for signature verification
- Release artifacts (if verifying artifact hashes)
- Phase 8.1 and 8.2 result files (if verifying hash integrity)

### Step 2: Run Verification

```bash
export RANSOMEYE_RELEASE_ROOT=/path/to/release/bundle
export RANSOMEYE_SIGNING_KEY_DIR=/path/to/public/keys  # or use public_key.pem in release root

python3 validation/evidence_verify/verify_evidence_bundle.py
```

### Step 3: Review Report

Review `verification_report.json`:

- `final_verdict`: `FOR-RELEASE` or `DO-NOT-RELEASE`
- `signature_valid`: Signature verification result
- `hash_integrity`: Hash recalculation results
- `artifact_integrity`: Artifact completeness results
- `sbom_integrity`: SBOM verification results
- `failures[]`: List of any failures

### Step 4: Make Decision

- **FOR-RELEASE**: All checks passed, release is ready
- **DO-NOT-RELEASE**: One or more checks failed, do not release

## Exact Commands to Run

### Basic Verification (Signature Only)

```bash
# Minimal verification (signature only)
export RANSOMEYE_SIGNING_KEY_DIR=/path/to/public/keys
python3 validation/evidence_verify/verify_evidence_bundle.py
```

### Full Verification (All Checks)

```bash
# Full verification (signature + hashes + artifacts + SBOM)
export RANSOMEYE_RELEASE_ROOT=/path/to/release/bundle
export RANSOMEYE_SIGNING_KEY_DIR=/path/to/public/keys
export RANSOMEYE_SIGNING_KEY_ID=vendor-release-key-1

python3 validation/evidence_verify/verify_evidence_bundle.py
```

### Using Public Key File

```bash
# If public key is in release root
export RANSOMEYE_RELEASE_ROOT=/path/to/release/bundle
# Script will automatically find public_key.pem in release root
python3 validation/evidence_verify/verify_evidence_bundle.py
```

## Offline Verification Guarantee

This script is **STRICTLY READ-ONLY** and **FULLY OFFLINE**:

- ✅ **No file modifications**: Never modifies any file
- ✅ **No network access**: No HTTP, DNS, or external calls
- ✅ **No re-execution**: Does not re-run validations
- ✅ **No regeneration**: Does not regenerate artifacts
- ✅ **Deterministic**: Same inputs always produce same results
- ✅ **Reproducible**: Can be run by any third party

## Verification Steps

The script performs the following verification steps:

### Step A: Signature Verification

- Loads evidence bundle JSON
- Loads signature from `evidence_bundle.json.sig`
- Loads public key (from key directory or release root)
- Verifies ed25519 signature
- **FAIL if signature invalid**

### Step B: Evidence Bundle Integrity

- Validates JSON schema
- Verifies `bundle_version == "1.0"`
- Verifies `overall_status == "FROZEN"`
- Checks all required fields present
- **FAIL if bundle structure invalid**

### Step C: Hash Recalculation

- Recomputes Phase 8.1 result file hash
- Recomputes Phase 8.2 result file hash
- Recomputes GA verdict hash (if present)
- Recomputes all artifact hashes
- Recomputes SBOM manifest hash
- Recomputes SBOM signature hash
- Compares with hashes in bundle
- **FAIL on any mismatch**

### Step D: Artifact Completeness

- Verifies all artifacts referenced in bundle exist
- Verifies artifact hashes match bundle
- Verifies one-to-one mapping with SBOM entries
- **FAIL if artifacts missing or hashes mismatch**

### SBOM Integrity

- Verifies SBOM manifest exists
- Verifies SBOM signature exists
- Verifies SBOM hashes match bundle
- **FAIL if SBOM missing or hashes mismatch**

## Verification Report Structure

The script generates `verification_report.json`:

```json
{
  "verified_at": "2024-01-15T10:30:45.123456+00:00",
  "signature_valid": true,
  "hash_integrity": "PASS",
  "artifact_integrity": "PASS",
  "sbom_integrity": "PASS",
  "ga_verdict": "PASS",
  "final_verdict": "FOR-RELEASE",
  "failures": []
}
```

### Fields

- `verified_at`: ISO 8601 timestamp when verification was performed
- `signature_valid`: `true` if signature verified, `false` otherwise
- `hash_integrity`: `"PASS"` if all hashes match, `"FAIL"` otherwise
- `artifact_integrity`: `"PASS"` if all artifacts verified, `"FAIL"` otherwise
- `sbom_integrity`: `"PASS"` if SBOM verified, `"FAIL"` otherwise
- `ga_verdict`: `"PASS"` if GA verdict verified, `"FAIL"` if present but invalid, `"NOT_PRESENT"` if not found
- `final_verdict`: `"FOR-RELEASE"` or `"DO-NOT-RELEASE"`
- `failures[]`: Array of failure messages (empty if all checks pass)

## Interpretation of FOR-RELEASE vs DO-NOT-RELEASE

### FOR-RELEASE

**Meaning**: All verification checks passed. The release is ready for customer delivery.

**Conditions**:
- ✅ Signature verified successfully
- ✅ Bundle integrity validated
- ✅ All hashes match (Phase 8.1, 8.2, GA verdict, artifacts, SBOM)
- ✅ All artifacts exist and are complete
- ✅ SBOM integrity verified
- ✅ No failures reported

**Action**: Proceed with release delivery.

### DO-NOT-RELEASE

**Meaning**: One or more verification checks failed. The release is **NOT** ready for customer delivery.

**Possible Causes**:
- ❌ Signature verification failed (bundle may be tampered)
- ❌ Bundle structure invalid (bundle may be corrupted)
- ❌ Hash mismatch (evidence files may have been modified)
- ❌ Artifacts missing or incomplete (release bundle incomplete)
- ❌ SBOM integrity failure (SBOM may be tampered)

**Action**: **DO NOT RELEASE**. Investigate failures and fix issues before re-verification.

## Example PASS Report

```json
{
  "verified_at": "2024-01-15T10:30:45.123456+00:00",
  "signature_valid": true,
  "hash_integrity": "PASS",
  "artifact_integrity": "PASS",
  "sbom_integrity": "PASS",
  "ga_verdict": "PASS",
  "final_verdict": "FOR-RELEASE",
  "failures": []
}
```

**Console Output**:
```
RansomEye v1.0 Phase 8.4 Independent Verification & Forensic Rehydration
======================================================================
Project root: /path/to/rebuild
Release root: /path/to/release/bundle
Key directory: /path/to/public/keys
Signing key ID: vendor-release-key-1

Loading evidence bundle...
  ✓ Bundle loaded

Step A: Verifying signature...
  ✓ Signature verified

Step B: Verifying bundle integrity...
  ✓ Bundle integrity verified

Step C: Recomputing and verifying hashes...
  ✓ Hash integrity verified

Step D: Verifying artifact completeness...
  ✓ Artifact integrity verified

Verifying SBOM integrity...
  ✓ SBOM integrity verified

Determining final verdict...
  ✓ FOR-RELEASE

Verification Summary:
  Signature valid: True
  Hash integrity: PASS
  Artifact integrity: PASS
  SBOM integrity: PASS
  GA verdict: PASS
  Final verdict: FOR-RELEASE
```

## Example FAIL Report

```json
{
  "verified_at": "2024-01-15T10:30:45.123456+00:00",
  "signature_valid": false,
  "hash_integrity": "FAIL",
  "artifact_integrity": "PASS",
  "sbom_integrity": "PASS",
  "ga_verdict": "NOT_PRESENT",
  "final_verdict": "DO-NOT-RELEASE",
  "failures": [
    "Signature verification failed",
    "Phase 8.1 hash mismatch: expected abc123..., computed def456..."
  ]
}
```

**Console Output**:
```
RansomEye v1.0 Phase 8.4 Independent Verification & Forensic Rehydration
======================================================================
Project root: /path/to/rebuild
Release root: /path/to/release/bundle
Key directory: /path/to/public/keys
Signing key ID: vendor-release-key-1

Loading evidence bundle...
  ✓ Bundle loaded

Step A: Verifying signature...
  ✗ Signature verification failed

Step B: Verifying bundle integrity...
  ✓ Bundle integrity verified

Step C: Recomputing and verifying hashes...
  ✗ Hash integrity check failed

Step D: Verifying artifact completeness...
  ✓ Artifact integrity verified

Verifying SBOM integrity...
  ✓ SBOM integrity verified

Determining final verdict...
  ✗ DO-NOT-RELEASE

Failures:
  - Signature verification failed
  - Phase 8.1 hash mismatch: expected abc123..., computed def456...

Verification Summary:
  Signature valid: False
  Hash integrity: FAIL
  Artifact integrity: PASS
  SBOM integrity: PASS
  GA verdict: NOT_PRESENT
  Final verdict: DO-NOT-RELEASE
```

## Exit Codes

- `0`: `final_verdict == FOR-RELEASE` (all checks passed)
- `1`: `final_verdict == DO-NOT-RELEASE` (one or more checks failed)

**Note**: Verification report is **always written**, even on failure.

## Environment Variables

- `RANSOMEYE_RELEASE_ROOT` (optional, default: `./build/artifacts`)
  - Root directory containing release artifacts
  - Required for artifact and SBOM verification

- `RANSOMEYE_SIGNING_KEY_DIR` (optional)
  - Directory containing public keys
  - Keys should be named `{signing_key_id}.pub`

- `RANSOMEYE_SIGNING_KEY_ID` (optional, default: `vendor-release-key-1`)
  - Signing key identifier
  - Used to locate public key file

**Note**: If `public_key.pem` exists in release root, it will be used automatically.

## Dependencies

### Required

- Python 3.10+
- `cryptography` library (for ed25519 signature verification)
- Supply-chain verification modules:
  - `supply-chain/crypto/artifact_verifier.py`
  - `supply-chain/crypto/vendor_key_manager.py`

### Installation

The `cryptography` library is typically available in most Python environments. If not:

```bash
pip install cryptography
```

## Troubleshooting

### Signature Verification Failed

**Possible Causes**:
- Wrong public key used
- Bundle has been tampered
- Signature file corrupted

**Solutions**:
1. Verify public key matches signing key
2. Re-obtain evidence bundle from vendor
3. Check signature file is not corrupted

### Hash Mismatch

**Possible Causes**:
- Evidence files have been modified
- Files were corrupted during transfer
- Wrong files being verified

**Solutions**:
1. Re-obtain evidence files from vendor
2. Verify file integrity (checksums)
3. Ensure correct files are being verified

### Artifacts Not Found

**Possible Causes**:
- Release root path incorrect
- Artifacts not included in release bundle
- Artifact names don't match

**Solutions**:
1. Verify `RANSOMEYE_RELEASE_ROOT` points to correct directory
2. Check artifact files exist in release root
3. Verify artifact names match bundle entries

### Public Key Not Found

**Possible Causes**:
- Key directory not set
- Key file not in expected location
- Key file name incorrect

**Solutions**:
1. Set `RANSOMEYE_SIGNING_KEY_DIR` environment variable
2. Place `public_key.pem` in release root
3. Verify key file name matches `{signing_key_id}.pub`

## Security Considerations

1. **Public Key Trust**
   - Public keys must be obtained through trusted channels
   - Verify public key authenticity before use
   - Use key fingerprints for verification

2. **Evidence Bundle Integrity**
   - Always verify signature before trusting bundle
   - Store bundles in tamper-evident storage
   - Never modify evidence bundles

3. **Verification Environment**
   - Run verification on clean, isolated systems
   - Use read-only filesystems when possible
   - Log all verification activities

4. **Report Preservation**
   - Store verification reports securely
   - Use tamper-evident storage
   - Maintain audit trail of all verifications

## Use Cases

### Pre-Delivery Verification

Customer verifies release readiness before accepting delivery:

```bash
# Customer receives evidence bundle and release artifacts
# Runs independent verification
python3 validation/evidence_verify/verify_evidence_bundle.py

# Reviews verification_report.json
# Makes go/no-go decision based on final_verdict
```

### Regulatory Compliance

Regulator verifies software supply chain security:

```bash
# Regulator receives evidence bundle
# Runs independent verification
python3 validation/evidence_verify/verify_evidence_bundle.py

# Reviews verification report
# Verifies compliance with regulations
```

### Post-Incident Forensics

IR team rehydrates validation state for incident analysis:

```bash
# IR team receives evidence bundle from pre-incident state
# Runs independent verification
python3 validation/evidence_verify/verify_evidence_bundle.py

# Reviews verification report
# Reconstructs validation state
# Identifies validation gaps
```

## Integration

This script is intended for:

- **Third-party verification**: Auditors, customers, regulators
- **Pre-delivery checks**: Customer acceptance testing
- **Compliance verification**: Regulatory compliance checks
- **Forensic analysis**: Post-incident investigation
- **Supply chain security**: Software supply chain verification

**Note**: This script does NOT modify CI workflows. It is a standalone, read-only verification tool.
