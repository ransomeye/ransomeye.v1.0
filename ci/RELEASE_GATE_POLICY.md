# PHASE 6 — Release Gate Policy

**AUTHORITATIVE**: Explicit GA gate checklist for RansomEye releases

**GA-BLOCKING**: No release, no installer, no package may exist without this phase being PASS.

---

## Release Gate Checklist

### Gate 1: Validation Complete

**Requirement**: All validation phases (01-40) must be complete and PASS.

**Check**:
- Phase C-L (Linux) validation results exist
- Phase C-W (Windows) validation results exist
- GA verdict is PASS
- No validation phases skipped

**Failure Condition**: If any validation phase is incomplete or FAIL, release is blocked.

**Evidence**:
- `validation/reports/phase_c/phase_c_linux_results.json` exists
- `validation/reports/phase_c/phase_c_windows_results.json` exists
- `validation/reports/phase_c/phase_c_aggregate_verdict.json` exists
- `ga_verdict` field in aggregate verdict is "PASS"

---

### Gate 2: All Artifacts Signed

**Requirement**: All build artifacts must be cryptographically signed with ed25519.

**Check**:
- Every artifact has a corresponding `.manifest.json` file
- Every manifest has a corresponding `.manifest.sig` file
- No unsigned artifacts exist

**Failure Condition**: If any artifact is unsigned, release is blocked.

**Evidence**:
- All artifacts in `build/artifacts/signed/` have both `.manifest.json` and `.manifest.sig` files
- No artifacts exist without signatures

---

### Gate 3: SBOM Generated and Signed

**Requirement**: SBOM (Software Bill of Materials) must be generated and signed.

**Check**:
- `build/artifacts/sbom/manifest.json` exists
- `build/artifacts/sbom/manifest.json.sig` exists
- SBOM includes all artifacts with SHA256 hashes

**Failure Condition**: If SBOM is missing or unsigned, release is blocked.

**Evidence**:
- `build/artifacts/sbom/manifest.json` exists
- `build/artifacts/sbom/manifest.json.sig` exists
- SBOM manifest includes all artifacts

---

### Gate 4: Signature Verification

**Requirement**: All signatures must be cryptographically verified.

**Check**:
- SBOM signature verifies successfully
- All artifact signatures verify successfully
- Public key is available for verification

**Failure Condition**: If any signature verification fails, release is blocked.

**Evidence**:
- `release/verify_sbom.py` exits with code 0
- `supply-chain/cli/verify_artifacts.py` exits with code 0 for all artifacts
- All signature verifications succeed

---

### Gate 5: Audit Steps Complete

**Requirement**: All audit steps must be complete.

**Check**:
- Validation reports exist
- SBOM exists
- All required audit artifacts are present

**Failure Condition**: If any audit step is missing, release is blocked.

**Evidence**:
- `validation/reports/phase_c/phase_c_linux_results.json` exists
- `validation/reports/phase_c/phase_c_windows_results.json` exists
- `validation/reports/phase_c/phase_c_aggregate_verdict.json` exists
- `build/artifacts/sbom/manifest.json` exists

---

### Gate 6: Release Validation Script

**Requirement**: Release validation script must pass.

**Check**:
- `release/ransomeye-v1.0/validate-release.sh` executes successfully
- All checksums verify
- All files present

**Failure Condition**: If release validation script fails, release is blocked.

**Evidence**:
- `release/ransomeye-v1.0/validate-release.sh` exits with code 0
- All checksums match
- All files present

---

## Manual Override Policy

**PHASE 6 Requirement**: No manual bypass without audit.

**Manual Override Process**:
1. Manual override requires explicit approval from release manager
2. Manual override must be logged to audit ledger
3. Manual override reason must be documented
4. Manual override must be reviewed by security team

**Forbidden**:
- No manual override for validation failures
- No manual override for unsigned artifacts
- No manual override for signature verification failures
- No manual override for missing audit steps

---

## Release Blocking Conditions

Release is **BLOCKED** if:

1. **Any validation incomplete**: Validation phases 01-40 not complete
2. **Any artifact unsigned**: Any build artifact missing signature
3. **Any audit step missing**: Required audit artifacts not present
4. **Any signature verification fails**: Any signature fails cryptographic verification
5. **GA verdict is not PASS**: GA verdict is FAIL or PARTIAL
6. **Release validation script fails**: Release validation script exits with non-zero code

---

## Release Approval Process

Release is **APPROVED** only if:

1. ✅ Gate 1: Validation Complete - PASS
2. ✅ Gate 2: All Artifacts Signed - PASS
3. ✅ Gate 3: SBOM Generated and Signed - PASS
4. ✅ Gate 4: Signature Verification - PASS
5. ✅ Gate 5: Audit Steps Complete - PASS
6. ✅ Gate 6: Release Validation Script - PASS

**All gates must pass. No exceptions.**

---

## CI/CD Integration

**GitHub Actions Workflow**: `.github/workflows/release-gate.yml`

**Automated Enforcement**:
- All gates are checked automatically in CI
- Release workflow blocks on any gate failure
- No manual intervention possible for gate failures

**Evidence**:
- CI workflow logs show all gates passing
- Release gate report uploaded as artifact
- All gate checks documented in workflow

---

## Fail-Closed Behavior

**PHASE 6 Requirement**: CI must fail-closed.

**Enforcement**:
- All CI steps use `continue-on-error: false`
- Any gate failure causes workflow to exit with code 1
- No "allow failures" for security gates
- No manual override without audit

**Evidence**:
- `.github/workflows/ci-validation.yml` - All steps have `continue-on-error: false`
- `.github/workflows/ci-build-and-sign.yml` - All steps have `continue-on-error: false`
- `.github/workflows/release-gate.yml` - All steps have `continue-on-error: false`

---

## Mapping to Validation Files

### Validation File 15 (CI/QA/Release Gates)

**Evidence**:
- CI workflows enforce validation phases (`.github/workflows/ci-validation.yml`)
- Artifact signing enforced in CI (`.github/workflows/ci-build-and-sign.yml`)
- Release gates enforced (`.github/workflows/release-gate.yml`)
- Fail-closed behavior enforced (all workflows use `continue-on-error: false`)

### Validation File 21 (Final Synthesis and Recommendations)

**Evidence**:
- Release gate policy documented (`ci/RELEASE_GATE_POLICY.md`)
- GA gate checklist defined (6 gates, all must pass)
- Manual override policy defined (requires audit)
- Release blocking conditions defined

---

## Summary

PHASE 6 — CI, QA & RELEASE GATES ensures:

✅ **CI Fail-Closed Enforcement**: CI blocks on any failed validation phase
✅ **Deterministic Test Harness**: Tests use synthetic data, are replayable, no network access
✅ **Artifact Signing & Verification**: All artifacts signed, signatures verified in CI
✅ **Release Gate Policy**: Explicit GA gate checklist, all gates must pass

**No broken build can ship. No unsigned artifact can exist. No release without validation.**
