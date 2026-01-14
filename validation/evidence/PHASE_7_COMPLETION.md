# PHASE 7 — Post-CI Production Readiness Verification

**Status**: Evidence structure created, awaiting CI run evidence

**Date**: 2026-01-13

---

## Evidence Structure Created

### Files Created

1. **`validation/evidence/PHASE_6_GA_PROOF.md`**
   - Main certification document (template)
   - Contains sections for CI run info, GA verdict, artifact trust chain
   - Includes offline verification commands
   - **Status**: Template ready, awaiting CI evidence

2. **`validation/evidence/phase_6/README.md`**
   - Evidence directory documentation
   - Collection instructions
   - Directory structure reference
   - **Status**: Complete

3. **`validation/evidence/phase_6/verify_offline.sh`**
   - Offline verification script
   - Verifies GA verdict, artifact signatures, SBOM
   - Deterministic verification (no network access)
   - **Status**: Complete and executable

4. **`validation/evidence/phase_6/collect_evidence.sh`**
   - Evidence collection helper script
   - Uses GitHub CLI to download CI artifacts
   - Validates collected files
   - **Status**: Complete and executable

5. **`validation/evidence/phase_6/.gitkeep`**
   - Ensures directory is tracked in git
   - **Status**: Complete

---

## Next Steps to Complete Phase 7

### Step 1: Trigger CI Run

Trigger a successful CI run:

```bash
# Option 1: Empty commit
git commit --allow-empty -m "chore: Phase-7 evidence collection"
git push origin main

# Option 2: Manual workflow dispatch via GitHub UI
# Actions → CI Build and Sign - PHASE 6 → Run workflow
```

### Step 2: Collect Evidence

After CI run completes successfully:

```bash
cd validation/evidence/phase_6

# Option A: Using GitHub CLI
./collect_evidence.sh <workflow_run_id>

# Option B: Manual download from GitHub Actions UI
# 1. Go to successful workflow run
# 2. Download artifacts:
#    - phase-c-linux-results
#    - phase-c-windows-results
#    - ga-verdict
#    - signed-artifacts
#    - signing-public-key
# 3. Extract to validation/evidence/phase_6/
```

### Step 3: Verify Evidence Offline

Run offline verification:

```bash
cd validation/evidence/phase_6
./verify_offline.sh
```

Expected output:
```
==========================================
PHASE 6: Offline Verification
==========================================
=== Step 1: Verifying GA Verdict ===
✅ GA Verdict: GA-READY
=== Step 2: Verifying Artifact Signatures ===
✅ Verified: core-installer.tar.gz
✅ Verified: linux-agent.tar.gz
✅ Verified: windows-agent.zip
✅ Verified: dpi-probe.tar.gz
✅ All 4 artifact(s) verified
=== Step 3: Verifying SBOM ===
✅ SBOM verified
=== Step 4: Computing Evidence Hashes ===
✅ Evidence hashes computed: evidence_hashes.txt
==========================================
✅ ALL VERIFICATIONS PASSED
==========================================
```

### Step 4: Populate GA Proof Document

Update `validation/evidence/PHASE_6_GA_PROOF.md`:

1. **CI Run Information**:
   - Workflow run ID
   - Commit SHA
   - Branch
   - Execution date
   - Workflow URL

2. **GA Verdict Fields**:
   - Extract from `phase_c_aggregate_verdict.json`
   - Verify: `verdict == "GA-READY"`, `ga_ready == true`

3. **Artifact Hashes**:
   - Compute SHA256 hashes
   - Populate artifact table
   - Document verification results

4. **Certification**:
   - Certification date
   - Certified by
   - Certification status: CERTIFIED

### Step 5: Commit Evidence

```bash
git add validation/evidence/
git commit -m "chore: Phase-7 evidence - GA readiness certified"
git push origin main
```

---

## Verification Checklist

Before marking Phase-7 complete:

- [ ] CI run completed successfully
- [ ] All evidence files collected from CI (not regenerated locally)
- [ ] `phase_c_aggregate_verdict.json` shows `GA-READY`
- [ ] Offline verification script passes
- [ ] All artifact signatures verified
- [ ] SBOM signature verified
- [ ] Evidence hashes computed
- [ ] `PHASE_6_GA_PROOF.md` populated with all evidence
- [ ] Evidence files committed to repository

---

## Evidence Directory Structure (After Collection)

```
validation/evidence/
├── PHASE_6_GA_PROOF.md          # Main certification (populated)
├── PHASE_7_COMPLETION.md        # This file
└── phase_6/
    ├── README.md
    ├── verify_offline.sh
    ├── collect_evidence.sh
    ├── phase_c_linux_results.json      # From CI
    ├── phase_c_windows_results.json    # From CI
    ├── phase_c_aggregate_verdict.json  # From CI
    ├── artifacts/
    │   ├── core-installer.tar.gz
    │   ├── linux-agent.tar.gz
    │   ├── windows-agent.zip
    │   ├── dpi-probe.tar.gz
    │   ├── signed/
    │   │   ├── *.manifest.json
    │   │   └── *.manifest.sig
    │   └── sbom/
    │       ├── manifest.json
    │       └── manifest.json.sig
    ├── keys/
    │   └── vendor-signing-key-ci-signing-key.pub
    └── evidence_hashes.txt
```

---

## Production Readiness Criteria

Phase-7 is complete when:

1. ✅ Evidence structure exists
2. ✅ CI evidence collected (from actual CI run)
3. ✅ GA verdict proven (`GA-READY`)
4. ✅ Trust chain verified offline
5. ✅ Evidence committed and immutable

---

## Notes

- **Evidence must come from CI runs only** - no local regeneration
- **Offline verification is mandatory** - proves deterministic trust
- **Evidence is immutable** - once certified, cannot be modified
- **New evidence requires new certification** - previous certifications remain valid

---

**Phase-7 Status**: Structure ready, awaiting CI evidence collection
