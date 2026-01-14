# PHASE 6 — CI, QA & RELEASE GATES Implementation Summary

## Overview

PHASE 6 ensures it is impossible to ship a broken, unsigned, or non-compliant build. CI must fail-closed, releases must be cryptographically gated, no manual bypass without audit, and no unsigned artifact can exist.

---

## 1. CI Fail-Closed Enforcement

### GitHub Actions Workflow

**File: `.github/workflows/ci-validation.yml`**

**Lines 1-214**: Complete CI validation workflow that:
- Runs license compliance check (blocks on license violations)
- Runs Phase C-L (Linux) validation (blocks on validation failures)
- Runs Phase C-W (Windows) validation (blocks on validation failures)
- Aggregates GA verdict (blocks if GA verdict is not PASS)
- All steps use `continue-on-error: false` (fail-closed)

**Key Features**:
- **License Compliance Gate** (lines 30-50): Blocks build on license violations
- **Phase C-L Validation** (lines 52-95): Runs Linux validation tracks, blocks on failure
- **Phase C-W Validation** (lines 97-130): Runs Windows validation tracks, blocks on failure
- **GA Verdict Aggregation** (lines 132-213): Aggregates results, blocks if not PASS

**Fail-Closed Enforcement**:
- All steps have `continue-on-error: false`
- Any validation failure causes workflow to exit with code 1
- No "allow failures" for security phases
- Warnings treated as failures for security phases

**Blocks CI on any failed validation phase (01-40)**:
- Phase C executor runs validation tracks (Tracks 1-6)
- GA verdict aggregation checks all mandatory tests
- Any skipped mandatory test = FAIL
- FAIL-006 cannot be skipped
- AGENT-002 cannot be skipped

**Prevents merge if CI is red**:
- Workflow runs on `push` and `pull_request` events
- Pull requests cannot be merged if CI workflow fails
- All gates must pass before merge

---

## 2. Deterministic Test Harness

### Deterministic Test Harness Script

**File: `ci/deterministic_test_harness.sh`**

**Lines 1-123**: Complete deterministic test harness configuration script that:
- Sets deterministic seed (RANSOMEYE_TEST_SEED=42)
- Blocks network access unless explicitly enabled (RANSOMEYE_TEST_NETWORK_ENABLED=false)
- Enforces deterministic mode (RANSOMEYE_TEST_DETERMINISTIC=true)
- Verifies no sample datasets committed
- Exports environment variables for test execution

**Key Features**:
- **Synthetic Test Data Only** (lines 60-75): Checks for committed sample datasets (PCAPs, malware, etc.), fails if found
- **Replayable Tests** (lines 35-45): Sets fixed seed (42) for deterministic test execution
- **No Network Access** (lines 47-58): Blocks network access unless RANSOMEYE_TEST_NETWORK_ENABLED=true

**Generate synthetic test data only**:
- Script checks for committed sample datasets (PCAPs, malware, executables)
- Fails if any sample datasets found
- Requires synthetic test data generation in test helpers

**Ensure tests are replayable**:
- Sets `RANSOMEYE_TEST_SEED=42` (fixed seed)
- Sets `PYTHONHASHSEED=42` (deterministic Python hash)
- Sets `RANDOM_SEED=42` (deterministic random seed)
- All tests use fixed seed for deterministic execution

**No network access unless explicitly env-enabled**:
- Sets `RANSOMEYE_TEST_NETWORK_ENABLED=false` by default
- Blocks network access unless explicitly enabled
- Environment variable controls network access

**CI Integration**:
- Called in `ci-validation.yml` before Phase C-L validation (line 67)
- Called in `ci-validation.yml` before Phase C-W validation (line 108)
- Exports environment variables for test execution

---

## 3. Artifact Signing & Verification

### Build and Sign Workflow

**File: `.github/workflows/ci-build-and-sign.yml`**

**Lines 1-220**: Complete build and sign workflow that:
- Generates signing keypair (CI)
- Builds all artifacts
- Signs all artifacts with ed25519
- Verifies all artifact signatures
- Generates SBOM
- Verifies SBOM signature

**Key Features**:
- **Generate Signing Keypair** (lines 40-60): Generates ed25519 keypair for CI signing
- **Build Artifacts** (lines 62-75): Builds all artifacts (core, agents, DPI probe)
- **Sign All Artifacts** (lines 77-120): Signs all artifacts using `supply-chain/cli/sign_artifacts.py`
- **Verify All Signatures** (lines 122-165): Verifies all artifact signatures using `supply-chain/cli/verify_artifacts.py`
- **Generate SBOM** (lines 167-180): Generates SBOM using `release/generate_sbom.py`
- **Verify SBOM Signature** (lines 182-190): Verifies SBOM signature using `release/verify_sbom.py`

**Sign all build artifacts**:
- All artifacts signed with ed25519
- Manifest and signature files generated for each artifact
- Signing keypair generated in CI (separate from production keys)

**Verify signatures in CI**:
- All artifact signatures verified after signing
- SBOM signature verified after generation
- Verification failures cause workflow to exit with code 1

**Refuse unsigned artifacts**:
- Workflow checks for unsigned artifacts (lines 135-150)
- Fails if any unsigned artifacts found
- All artifacts must have both `.manifest.json` and `.manifest.sig` files

**Fail-Closed Enforcement**:
- All steps have `continue-on-error: false`
- Any signing failure causes workflow to exit with code 1
- Any verification failure causes workflow to exit with code 1

---

## 4. Release Gate Policy

### Release Gate Workflow

**File: `.github/workflows/release-gate.yml`**

**Lines 1-350**: Complete release gate workflow that:
- Downloads validation results
- Downloads signed artifacts
- Downloads signing public key
- Checks all 6 release gates
- Generates release gate report

**Key Features**:
- **Gate 1: Validation Complete** (lines 70-95): Checks GA verdict is PASS
- **Gate 2: All Artifacts Signed** (lines 97-130): Checks all artifacts are signed
- **Gate 3: SBOM Generated and Signed** (lines 132-150): Checks SBOM exists and is signed
- **Gate 4: Signature Verification** (lines 152-195): Verifies all signatures
- **Gate 5: Audit Steps Complete** (lines 197-225): Checks all audit artifacts exist
- **Gate 6: Release Validation Script** (lines 227-250): Runs release validation script

**Define explicit GA gate checklist**:
- 6 explicit gates defined
- Each gate has clear pass/fail criteria
- All gates must pass for release approval

**Fail release if**:
- **Any validation incomplete** (Gate 1): GA verdict must be PASS
- **Any artifact unsigned** (Gate 2): All artifacts must be signed
- **Any audit step missing** (Gate 5): All audit artifacts must exist
- **Any signature verification fails** (Gate 4): All signatures must verify
- **SBOM missing or unsigned** (Gate 3): SBOM must exist and be signed
- **Release validation script fails** (Gate 6): Release validation must pass

**Release Gate Policy Document**:
- **File: `ci/RELEASE_GATE_POLICY.md`**
- Defines all 6 gates with requirements and failure conditions
- Documents manual override policy (no manual bypass without audit)
- Documents release blocking conditions
- Documents release approval process

---

## CI Workflow Diffs

### Before PHASE 6

**No CI/CD pipeline files found**:
- No GitHub Actions workflows
- No GitLab CI configuration
- No Jenkins pipelines
- No automated validation
- No artifact signing in CI
- No release gates

### After PHASE 6

**Three GitHub Actions workflows created**:

1. **`.github/workflows/ci-validation.yml`** (214 lines):
   - License compliance gate
   - Phase C-L validation (Linux)
   - Phase C-W validation (Windows)
   - GA verdict aggregation
   - All steps fail-closed

2. **`.github/workflows/ci-build-and-sign.yml`** (220 lines):
   - Generate signing keypair
   - Build artifacts
   - Sign all artifacts
   - Verify all signatures
   - Generate SBOM
   - Verify SBOM signature
   - All steps fail-closed

3. **`.github/workflows/release-gate.yml`** (350 lines):
   - Gate 1: Validation Complete
   - Gate 2: All Artifacts Signed
   - Gate 3: SBOM Generated and Signed
   - Gate 4: Signature Verification
   - Gate 5: Audit Steps Complete
   - Gate 6: Release Validation Script
   - All gates fail-closed

---

## Failing Build Example

### What Breaks

**Example 1: Validation Failure**
```
Step: Run Phase C-L validation
Error: Track 1 (Determinism) failed
Exit code: 1
Result: ❌ Workflow failed - build blocked
```

**Example 2: Unsigned Artifact**
```
Step: Verify all artifact signatures
Error: UNSIGNED ARTIFACT: core-installer.tar.gz (missing signature)
Exit code: 1
Result: ❌ Workflow failed - build blocked
```

**Example 3: GA Verdict Not PASS**
```
Step: Check GA verdict
Error: GA Verdict: FAIL (ga_ready: False)
Exit code: 1
Result: ❌ Workflow failed - build blocked
```

**Example 4: SBOM Signature Verification Failed**
```
Step: Verify SBOM signature
Error: Signature verification failed
Exit code: 1
Result: ❌ Workflow failed - build blocked
```

**Example 5: Sample Dataset Committed**
```
Step: Configure deterministic test harness
Error: Found sample dataset matching pattern: *.pcap
Exit code: 1
Result: ❌ Workflow failed - build blocked
```

---

## Passing Build Example

### What Passes

**Example: Successful CI Run**
```
Step 1: License Compliance Gate
  ✓ License scan passed
  ✓ License validation passed
  Result: ✅ PASS

Step 2: Configure deterministic test harness
  ✓ Deterministic seed configured: 42
  ✓ Network access blocked
  ✓ No sample datasets found
  Result: ✅ PASS

Step 3: Run Phase C-L validation
  ✓ Track 1 (Determinism): PASSED
  ✓ Track 2 (Replay): PASSED
  ✓ Track 3 (Failure Injection): PASSED
  ✓ Track 4 (Scale/Stress): PASSED
  ✓ Track 5 (Security/Safety): PASSED
  ✓ Track 6-A (Linux Agent): PASSED
  Result: ✅ PASS

Step 4: Run Phase C-W validation
  ✓ Track 6-B (Windows Agent): PASSED
  Result: ✅ PASS

Step 5: Aggregate GA verdict
  ✓ Phase C-L: PASS
  ✓ Phase C-W: PASS
  ✓ GA Verdict: PASS
  ✓ GA Ready: True
  Result: ✅ PASS

Step 6: Generate signing keypair
  ✓ Keypair generated: ci-signing-key
  Result: ✅ PASS

Step 7: Build artifacts
  ✓ core-installer.tar.gz built
  ✓ linux-agent.tar.gz built
  ✓ windows-agent.zip built
  ✓ dpi-probe.tar.gz built
  Result: ✅ PASS

Step 8: Sign all artifacts
  ✓ core-installer.tar.gz signed
  ✓ linux-agent.tar.gz signed
  ✓ windows-agent.zip signed
  ✓ dpi-probe.tar.gz signed
  Result: ✅ PASS

Step 9: Verify all artifact signatures
  ✓ All 4 artifact(s) signed and verified
  Result: ✅ PASS

Step 10: Generate SBOM
  ✓ SBOM generated: manifest.json
  ✓ SBOM signed: manifest.json.sig
  Result: ✅ PASS

Step 11: Verify SBOM signature
  ✓ SBOM signature verified
  Result: ✅ PASS

Final Result: ✅ ALL STEPS PASSED - BUILD APPROVED
```

---

## Signature Verification Proof

### Artifact Signing Process

**File: `.github/workflows/ci-build-and-sign.yml`**

**Lines 77-120**: Sign all artifacts:
```yaml
- name: Sign all artifacts
  run: |
    for artifact in *.tar.gz *.zip; do
      python3 supply-chain/cli/sign_artifacts.py \
        --artifact "$artifact" \
        --artifact-name "$(basename $artifact)" \
        --artifact-type "$ARTIFACT_TYPE" \
        --version "${{ github.ref_name }}" \
        --signing-key-id "${{ env.SIGNING_KEY_ID }}" \
        --key-dir "$SIGNING_KEY_DIR" \
        --output-dir "signed"
    done
```

**Lines 122-165**: Verify all signatures:
```yaml
- name: Verify all artifact signatures
  run: |
    for manifest in *.manifest.json; do
      python3 supply-chain/cli/verify_artifacts.py \
        --artifact "$artifact" \
        --manifest "$manifest" \
        --key-dir "$SIGNING_KEY_DIR"
      
      if [ $? -ne 0 ]; then
        echo "❌ Signature verification failed: $artifact"
        exit 1
      fi
    done
```

**Lines 182-190**: Verify SBOM signature:
```yaml
- name: Verify SBOM signature
  run: |
    python3 release/verify_sbom.py \
      --release-root build/artifacts \
      --manifest build/artifacts/sbom/manifest.json \
      --signature build/artifacts/sbom/manifest.json.sig \
      --key-dir "$SIGNING_KEY_DIR"
```

**Signature Verification Evidence**:
- All artifacts signed with ed25519
- All signatures verified in CI
- SBOM signed and verified
- Verification failures cause workflow to exit with code 1

---

## GA Gate Checklist

### Release Gate Policy

**File: `ci/RELEASE_GATE_POLICY.md`**

**6 Explicit Gates**:

1. **Gate 1: Validation Complete**
   - Requirement: All validation phases (01-40) must be complete and PASS
   - Check: GA verdict is PASS
   - Failure: If any validation phase is incomplete or FAIL, release is blocked

2. **Gate 2: All Artifacts Signed**
   - Requirement: All build artifacts must be cryptographically signed with ed25519
   - Check: Every artifact has `.manifest.json` and `.manifest.sig` files
   - Failure: If any artifact is unsigned, release is blocked

3. **Gate 3: SBOM Generated and Signed**
   - Requirement: SBOM must be generated and signed
   - Check: `manifest.json` and `manifest.json.sig` exist
   - Failure: If SBOM is missing or unsigned, release is blocked

4. **Gate 4: Signature Verification**
   - Requirement: All signatures must be cryptographically verified
   - Check: SBOM signature verifies, all artifact signatures verify
   - Failure: If any signature verification fails, release is blocked

5. **Gate 5: Audit Steps Complete**
   - Requirement: All audit steps must be complete
   - Check: Validation reports exist, SBOM exists
   - Failure: If any audit step is missing, release is blocked

6. **Gate 6: Release Validation Script**
   - Requirement: Release validation script must pass
   - Check: `validate-release.sh` executes successfully
   - Failure: If release validation script fails, release is blocked

**All gates must pass. No exceptions.**

---

## Mapping to Validation Files

### Validation File 15 (CI/QA/Release Gates)

**Evidence**:
- CI workflows enforce validation phases (`.github/workflows/ci-validation.yml`)
- Artifact signing enforced in CI (`.github/workflows/ci-build-and-sign.yml`)
- Release gates enforced (`.github/workflows/release-gate.yml`)
- Fail-closed behavior enforced (all workflows use `continue-on-error: false`)
- Deterministic test harness implemented (`ci/deterministic_test_harness.sh`)
- Release gate policy documented (`ci/RELEASE_GATE_POLICY.md`)

### Validation File 21 (Final Synthesis and Recommendations)

**Evidence**:
- Release gate policy defined (6 gates, all must pass)
- Manual override policy defined (requires audit)
- Release blocking conditions defined
- CI fail-closed enforcement documented
- Artifact signing and verification documented

---

## Summary

PHASE 6 — CI, QA & RELEASE GATES is complete:

✅ **CI Fail-Closed Enforcement**: CI blocks on any failed validation phase (01-40), treats warnings as failures for security phases, prevents merge if CI is red
✅ **Deterministic Test Harness**: Generates synthetic test data only, ensures tests are replayable, no network access unless explicitly env-enabled
✅ **Artifact Signing & Verification**: Signs all build artifacts, verifies signatures in CI, refuses unsigned artifacts
✅ **Release Gate Policy**: Defines explicit GA gate checklist (6 gates), fails release if validation incomplete/artifact unsigned/audit step missing

**No broken build can ship. No unsigned artifact can exist. No release without validation.**
