# RansomEye v1.0 Dry-Run Release Checklist
**AUTHORITATIVE: Copy-Paste-Safe Execution Guide**

**Version:** 1.0.0  
**Date:** 2026-01-18  
**Prerequisites:** CI/CD pipeline operational, GitHub environments configured

---

## ⚠️ CRITICAL: Execution Sequence

**DO NOT attempt Phase B until Phase A completes.**  
**DO NOT attempt Phase C until Phase B completes.**

---

## Phase A: GitHub Environment Setup (One-Time)

### A.1 Create GitHub Environments

Navigate to: `Settings → Environments`

```bash
# Create 'dev' environment
# - No protection rules
# - Auto-deployment enabled

# Create 'staging' environment  
# - Required reviewers: 1
# - Assign: [staging-approver-github-username]

# Create 'prod' environment
# - Required reviewers: 2
# - Assign: [prod-approver-1-github-username, prod-approver-2-github-username]
# - Prevent administrators from bypassing: ENABLED
```

**Verification:**
- [ ] All 3 environments exist
- [ ] Reviewer counts configured correctly
- [ ] Admin bypass disabled for PROD

---

## Phase B: Offline Key Generation (One-Time, Air-Gapped)

**⚠️ SECURITY REQUIREMENT:** Execute on air-gapped workstation with dual witnesses present.

### B.1 Generate Signing Key

**Location:** Air-gapped signing workstation  
**Participants:** [Name 1], [Name 2]  
**Witness:** [Name 3] (optional)

```bash
# Navigate to RansomEye repository (on air-gapped machine)
cd /path/to/ransomeye/repo

# Set vault passphrase (store in password manager, NEVER commit)
export RANSOMEYE_KEY_VAULT_PASSPHRASE="[GENERATE_STRONG_PASSPHRASE]"

# Generate signing key
python3 scripts/key_generation_ceremony.py \
  --key-id "ransomeye-release-signing-v1" \
  --key-type signing \
  --vault-dir keys/vault \
  --registry-path keys/registry.json \
  --log-dir keys/ceremony-logs \
  --participants "Participant1" "Participant2" \
  --witness "Witness1"
```

**Expected Output:**
```
✅ Keypair generated
   Public key fingerprint: [64-char-hex-hash]
✅ Key stored in vault: keys/vault
✅ Key registered in registry: keys/registry.json
✅ Ceremony log written to keys/ceremony-logs/ransomeye-release-signing-v1-generation-YYYYMMDD-HHMMSS.json
```

**Post-Generation Actions:**
- [ ] Record public key fingerprint in signing ceremony log
- [ ] Export public key: `keys/vault/ransomeye-release-signing-v1.pub`
- [ ] Store vault passphrase in secure password manager
- [ ] Backup encrypted vault offline (USB + safe deposit box)
- [ ] **COMMIT ONLY public key and registry to repository**

```bash
# On air-gapped machine: Export public key for repository
cp keys/vault/ransomeye-release-signing-v1.pub release/.keys/

# On development machine: Add public key to repository
git add release/.keys/ransomeye-release-signing-v1.pub
git add keys/registry.json
git commit -m "Add release signing public key and registry

- Public key fingerprint: [fingerprint-from-ceremony]
- Generated during signing ceremony: [date]
- Participants: [names]"
git push origin main
```

**Security Checklist:**
- [ ] Private key NEVER leaves air-gapped machine
- [ ] Vault passphrase stored securely (NOT in repository)
- [ ] Dual witnesses signed ceremony log
- [ ] Backup vault encrypted and offline
- [ ] Only public key committed to repository

---

## Phase C: Trigger CI Build

### C.1 Create and Push Test Tag

```bash
# Verify clean working directory
git status

# Create test tag
git tag v0.0.1-test -m "Dry-run test release"

# Push tag to trigger CI
git push origin v0.0.1-test
```

### C.2 Monitor CI Workflow

Navigate to: `Actions → ransomeye-release workflow`

**Expected Stages:**
1. ✅ Build (compile all components)
2. ✅ Test (unit + integration tests)
3. ✅ Package (create unsigned artifacts)
4. ⏸️ **WAIT FOR COMPLETION**

**Verification:**
- [ ] Workflow completes successfully
- [ ] Build artifacts generated
- [ ] No test failures

### C.3 Download Unsigned Artifacts

**⚠️ CRITICAL: Do NOT proceed until CI workflow shows "Completed"**

```bash
# In GitHub UI:
# Actions → ransomeye-release → [your workflow run] → Artifacts

# Download: release-artifacts-unsigned.zip
# Save to: ~/downloads/release-artifacts-unsigned.zip
```

**Verification:**
- [ ] ZIP file downloaded successfully
- [ ] File size > 0 bytes
- [ ] ZIP file can be extracted

```bash
# Verify downloaded artifacts
unzip -l ~/downloads/release-artifacts-unsigned.zip
```

**Expected Contents:**
```
build/artifacts/core-installer.tar.gz
build/artifacts/linux-agent.tar.gz
build/artifacts/windows-agent.zip
build/artifacts/dpi-probe.tar.gz
build/artifacts/build-info.json
build/artifacts/build-environment.json
```

**⏸️ CHECKPOINT: Do NOT proceed until artifacts are downloaded and verified**

---

## Phase D: Offline Signing Ceremony

**⚠️ SECURITY REQUIREMENT:** Execute on air-gapped workstation with dual witnesses present.

### D.1 Transfer Unsigned Artifacts to Air-Gapped Machine

**Method:** USB drive (virus scan before transfer)

```bash
# On air-gapped machine: Extract artifacts
cd /path/to/ransomeye/repo
mkdir -p build/artifacts
cd build/artifacts
unzip ~/usb/release-artifacts-unsigned.zip

# Verify extraction
ls -lh
```

**Expected files:**
- `core-installer.tar.gz`
- `linux-agent.tar.gz`
- `windows-agent.zip`
- `dpi-probe.tar.gz`
- `build-info.json`
- `build-environment.json`

### D.2 Sign Each Artifact

**⚠️ IMPORTANT:** Vault passphrase must be set before signing

```bash
# Set vault passphrase (from password manager)
export RANSOMEYE_KEY_VAULT_PASSPHRASE="[YOUR_VAULT_PASSPHRASE]"

# Create output directory for signed artifacts
mkdir -p build/artifacts/signed

# Sign Core Installer
python3 supply-chain/cli/sign_artifacts.py \
  --artifact build/artifacts/core-installer.tar.gz \
  --artifact-name core-installer.tar.gz \
  --artifact-type CORE_INSTALLER \
  --version v0.0.1-test \
  --signing-key-id ransomeye-release-signing-v1 \
  --vault-dir keys/vault \
  --registry-path keys/registry.json \
  --output-dir build/artifacts/signed

# Sign Linux Agent
python3 supply-chain/cli/sign_artifacts.py \
  --artifact build/artifacts/linux-agent.tar.gz \
  --artifact-name linux-agent.tar.gz \
  --artifact-type LINUX_AGENT \
  --version v0.0.1-test \
  --signing-key-id ransomeye-release-signing-v1 \
  --vault-dir keys/vault \
  --registry-path keys/registry.json \
  --output-dir build/artifacts/signed

# Sign Windows Agent
python3 supply-chain/cli/sign_artifacts.py \
  --artifact build/artifacts/windows-agent.zip \
  --artifact-name windows-agent.zip \
  --artifact-type WINDOWS_AGENT \
  --version v0.0.1-test \
  --signing-key-id ransomeye-release-signing-v1 \
  --vault-dir keys/vault \
  --registry-path keys/registry.json \
  --output-dir build/artifacts/signed

# Sign DPI Probe
python3 supply-chain/cli/sign_artifacts.py \
  --artifact build/artifacts/dpi-probe.tar.gz \
  --artifact-name dpi-probe.tar.gz \
  --artifact-type DPI_PROBE \
  --version v0.0.1-test \
  --signing-key-id ransomeye-release-signing-v1 \
  --vault-dir keys/vault \
  --registry-path keys/registry.json \
  --output-dir build/artifacts/signed
```

**Expected Output (per artifact):**
```
Artifact signed successfully:
  Artifact: build/artifacts/[artifact-name]
  Artifact ID: [uuid]
  SHA256: [64-char-hex]
  Signing Key ID: ransomeye-release-signing-v1
  Output files:
    - build/artifacts/signed/[artifact-name].sha256
    - build/artifacts/signed/[artifact-name].manifest.json
    - build/artifacts/signed/[artifact-name].manifest.sig
```

**Verification:**
```bash
# Verify all signatures created
ls -lh build/artifacts/signed/

# Expected: 12 files (3 per artifact × 4 artifacts)
# - core-installer.tar.gz.sha256
# - core-installer.tar.gz.manifest.json
# - core-installer.tar.gz.manifest.sig
# (repeated for all 4 artifacts)
```

**Ceremony Log:**
- [ ] Record signing timestamp
- [ ] Record all artifact IDs
- [ ] Record signing key ID used
- [ ] Dual witnesses sign ceremony log

### D.3 Create Signed Release Bundle

**⚠️ NOTE:** This requires Phase-8 evidence bundle (skip for dry-run if unavailable)

```bash
# Create SBOM directory (mock for dry-run)
mkdir -p build/artifacts/sbom
echo '{"components": [], "version": "1.0"}' > build/artifacts/sbom/manifest.json
echo "mock-signature" > build/artifacts/sbom/manifest.json.sig

# Create evidence directory (mock for dry-run)
mkdir -p validation/evidence_bundle
echo '{"overall_status": "PASS", "timestamp": "'$(date -Iseconds)'"}' > validation/evidence_bundle/evidence_bundle.json
echo "mock-signature" > validation/evidence_bundle/evidence_bundle.json.sig

# Create public keys directory
mkdir -p build/artifacts/public-keys
cp keys/vault/ransomeye-release-signing-v1.pub build/artifacts/public-keys/

# Create release bundle
python3 scripts/create_release_bundle.py \
  --version v0.0.1-test \
  --build-artifacts-dir build/artifacts \
  --signed-artifacts-dir build/artifacts/signed \
  --sbom-dir build/artifacts/sbom \
  --public-keys-dir build/artifacts/public-keys \
  --evidence-dir validation/evidence_bundle \
  --metadata-dir build/artifacts \
  --signing-key-id ransomeye-release-signing-v1 \
  --output-dir release/bundles \
  --project-root .
```

**Expected Output:**
```
Collecting artifacts...
  ✅ core-installer.tar.gz
  ✅ linux-agent.tar.gz
  ✅ windows-agent.zip
  ✅ dpi-probe.tar.gz
Collecting signatures...
  ✅ core-installer.tar.gz
  ✅ linux-agent.tar.gz
  ✅ windows-agent.zip
  ✅ dpi-probe.tar.gz
Collecting SBOM...
  ✅ SBOM manifest and signature
Collecting public keys...
  ✅ ransomeye-release-signing-v1.pub
Collecting Phase-8 evidence...
  ✅ Evidence bundle and signature
Collecting metadata...
  ✅ Build metadata
Creating RELEASE_MANIFEST.json...
  ✅ RELEASE_MANIFEST.json (SHA256: [hash]...)
Creating release bundle tarball...
✅ Release bundle created: ransomeye-v0.0.1-test-release-bundle.tar.gz
   Size: [size] bytes
   SHA256: [64-char-hex]
   Manifest SHA256: [64-char-hex]
   Checksum: ransomeye-v0.0.1-test-release-bundle.tar.gz.sha256
```

**Verification:**
```bash
# Verify bundle created
ls -lh release/bundles/

# Expected files:
# - ransomeye-v0.0.1-test-release-bundle.tar.gz
# - ransomeye-v0.0.1-test-release-bundle.tar.gz.sha256
```

### D.4 Verify Signed Bundle (Offline Verification Test)

```bash
# Verify bundle on air-gapped machine
python3 scripts/verify_release_bundle.py \
  --bundle release/bundles/ransomeye-v0.0.1-test-release-bundle.tar.gz \
  --checksum release/bundles/ransomeye-v0.0.1-test-release-bundle.tar.gz.sha256 \
  --registry-path keys/registry.json
```

**Expected Output:**
```
Extracting release bundle...
Verifying bundle integrity...
  ✅ Bundle integrity verified
Verifying RELEASE_MANIFEST.json...
  ✅ Release version: v0.0.1-test
Verifying artifacts match manifest...
  ✅ 4 artifacts verified
Verifying artifact signatures...
  ✅ 4 signatures verified
Verifying SBOM...
  ✅ SBOM verified
Verifying Phase-8 evidence...
  ✅ Evidence bundle verified (GA verdict: PASS)

✅ RELEASE BUNDLE VERIFICATION PASSED

All verification checks passed:
  ✅ Bundle integrity
  ✅ Release manifest
  ✅ Artifacts match manifest
  ✅ All signatures verified
  ✅ SBOM verified
  ✅ Phase-8 evidence verified (GA verdict: PASS)

FOR-RELEASE: This bundle is approved for release.
```

**⚠️ CRITICAL: If verification fails, DO NOT proceed. Investigate and re-sign.**

---

## Phase E: Upload Signed Bundle to CI

**⚠️ TODO:** CI workflow must support signed bundle upload mechanism

```bash
# Transfer signed bundle from air-gapped machine to development machine
# Method: USB drive (virus scan)

# Expected file on development machine:
# ~/signed-bundles/ransomeye-v0.0.1-test-release-bundle.tar.gz
```

**Current Limitation:** CI workflow does not yet have artifact re-upload mechanism.

**Workaround for Dry-Run:**
- Manually verify bundle on air-gapped machine (Phase D.4) ✅
- Skip CI re-verification for this dry-run
- Document requirement for CI artifact upload workflow enhancement

---

## Phase F: Promotion Gate Testing

**⚠️ NOTE:** This phase requires CI workflow enhancement to accept signed bundles.

**Expected Flow (once implemented):**

### F.1 DEV Auto-Promotion
- [ ] CI automatically promotes to `dev` environment
- [ ] No manual approval required
- [ ] Deployment logs captured

### F.2 STAGING Gated Promotion
- [ ] CI pauses for approval
- [ ] Designated reviewer receives notification
- [ ] Reviewer approves deployment
- [ ] CI promotes to `staging`
- [ ] Deployment logs captured

### F.3 PROD Dual-Approval Gate
- [ ] CI pauses for approval
- [ ] Two designated approvers required
- [ ] **DO NOT APPROVE** (this is a test)
- [ ] Verify gate holds without bypass option

**For Dry-Run:** Verify GitHub environment protection rules are configured correctly (Phase A.1)

---

## Phase G: Dry-Run Completion

### G.1 Dry-Run Report

**Document:**
- [ ] Key generation ceremony completed
- [ ] Signing ceremony completed with dual witnesses
- [ ] All 4 artifacts signed successfully
- [ ] Release bundle created and verified offline
- [ ] Offline verification passed
- [ ] GitHub environments configured

**Blockers Identified:**
- [ ] CI workflow missing signed bundle re-upload mechanism
- [ ] CI workflow missing promotion gate integration

**Timing Metrics:**
- Key generation: [X minutes]
- Artifact signing: [Y minutes]
- Bundle creation: [Z minutes]
- Offline verification: [W minutes]

### G.2 Clean Up Test Artifacts

```bash
# Delete test tag
git tag -d v0.0.1-test
git push origin :refs/tags/v0.0.1-test

# Remove test artifacts from air-gapped machine
rm -rf build/artifacts/*
rm -rf release/bundles/*

# Preserve:
# - keys/vault/* (encrypted, keep offline)
# - keys/registry.json (committed)
# - keys/ceremony-logs/* (audit trail)
# - release/.keys/*.pub (committed)
```

### G.3 Stakeholder Sign-Off

**Required Approvals:**
- [ ] Security Team: Signing ceremony validated
- [ ] Operations Team: Process feasible for production
- [ ] Engineering Team: CI/CD enhancements identified

---

## Success Criteria

✅ **CI build produces unsigned artifacts**  
✅ **Offline signing ceremony completes with dual witnesses**  
✅ **All artifacts signed using persistent keys**  
✅ **Release bundle created and includes all components**  
✅ **Offline verification passes**  
✅ **Keys never exposed to CI**  
✅ **Full audit trail captured**  

---

## Failure Handling

### If Key Generation Fails
- Review vault passphrase requirements
- Verify filesystem permissions on keys/vault
- Check Python cryptography library installed

### If Artifact Signing Fails
- Verify vault passphrase correct
- Verify signing key is active in registry
- Check artifact file exists and is readable

### If Bundle Creation Fails
- Verify all signed artifacts present
- Check SBOM and evidence bundles exist
- Verify directory structure matches expected layout

### If Verification Fails
- Review verification error message
- Check signature integrity
- Verify public key matches signing key

---

## Next Steps After Successful Dry-Run

1. **Enhance CI Workflow**
   - Add signed bundle upload mechanism
   - Integrate promotion gates
   - Add verification stage

2. **Production Key Generation**
   - Generate production signing key (not test key)
   - Use hardware security module (HSM) if available
   - Update key custody procedures

3. **v1.0.0 Release**
   - Create v1.0.0 tag
   - Execute full release process
   - Deploy to production

---

## Emergency Contacts

**Security Team:** [contact]  
**Operations Team:** [contact]  
**Key Custodian:** [contact]  
**Incident Response:** [contact]

---

**Document Version:** 1.0.0  
**Last Updated:** 2026-01-18  
**Maintained By:** RansomEye Release Engineering
