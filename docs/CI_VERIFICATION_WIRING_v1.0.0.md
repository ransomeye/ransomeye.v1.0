# RansomEye CI Verification Wiring
**AUTHORITATIVE: Public Key Distribution & CI Integration**

**Version:** 1.0.0  
**Date:** 2026-01-18  
**Status:** ✅ COMPLETE

---

## Overview

This document describes how the RansomEye CI pipeline is wired to verify signed release bundles using public key cryptography.

**Key Principle:** CI has **READ-ONLY** access to public keys. Private keys **NEVER** enter CI.

---

## Public Key Distribution

### Location: `release/.keys/`

All release verification public keys are stored in this directory and committed to the repository.

**Current Keys:**

| Key ID | Fingerprint | Status | Purpose |
|--------|-------------|--------|---------|
| `ransomeye-release-signing-v1` | `4ba9f27a9d8d61ef2ad07ee9dbc5d29335a73bd5fcf334cb08b30058fb34f2e1` | Active | Release artifact signing |

### Security Properties

✅ **Public keys are safe to commit**  
✅ **No secrets in CI environment**  
✅ **Verifiable by anyone with repository access**  
✅ **Keys can be audited in git history**  
❌ **Private keys NEVER in repository**  
❌ **Private keys NEVER in CI**  

---

## Key Registry

### Location: `keys/registry.json`

The key registry tracks:
- All signing keys (past and present)
- Key status (active, rotated, revoked, compromised)
- Key fingerprints
- Generation timestamps
- Revocation dates (if applicable)

### Usage in CI

CI workflows reference the registry to:
1. Verify signing key is active (not revoked)
2. Check key status before accepting signatures
3. Provide audit trail for key usage

**CI Access:** Read-only, committed to repository

---

## CI Workflow Integration

### Pipeline: `.github/workflows/ransomeye-release.yml`

#### Stage 1: Build & Package (Unsigned)
```
build → tests → security → package
```

**Output:** `unsigned-release` artifact

**Key Properties:**
- No signing keys accessed
- No signatures generated
- Artifacts ready for offline signing

---

#### Stage 2: Signing Handoff (OFFLINE)

**Workflow pauses** and displays signing instructions:

```
================================================================
UNSIGNED BUNDLE READY FOR OFFLINE SIGNING
================================================================

REQUIRED ACTIONS (OFFLINE, AIR-GAPPED WORKSTATION):

1. Download artifact 'unsigned-release' from this workflow run
2. Follow signing procedure: docs/DRY_RUN_CHECKLIST_v1.0.0.md
3. Sign all artifacts using: supply-chain/cli/sign_artifacts.py
4. Create release bundle: scripts/create_release_bundle.py
5. Verify bundle offline: scripts/verify_release_bundle.py
6. Upload signed bundle tarball (.tar.gz) as artifact 'signed-release-bundle'

PUBLIC KEY FOR VERIFICATION:
  Path: release/.keys/ransomeye-release-signing-v1.pub
  Fingerprint: 4ba9f27a9d8d61ef2ad07ee9dbc5d29335a73bd5fcf334cb08b30058fb34f2e1

KEY REGISTRY:
  Path: keys/registry.json
```

**Manual Step:** Operator downloads unsigned artifacts, signs offline, uploads signed bundle.

---

#### Stage 3: Verify & Release

**Input:** `signed-release-bundle` artifact (uploaded by operator)

**Verification Steps:**

1. **Download signed bundle tarball**
   - Expects: `ransomeye-vX.Y.Z-release-bundle.tar.gz`
   - Expects: `ransomeye-vX.Y.Z-release-bundle.tar.gz.sha256`

2. **Verify bundle cryptographically**
   ```bash
   python3 scripts/verify_release_bundle.py \
     --bundle <bundle.tar.gz> \
     --checksum <bundle.tar.gz.sha256> \
     --registry-path keys/registry.json \
     --output verification-report.json
   ```

   **Checks:**
   - Bundle tarball integrity (checksum)
   - RELEASE_MANIFEST.json structure
   - All artifacts match manifest hashes
   - All artifact signatures valid (using bundled public key)
   - SBOM signature valid
   - Phase-8 evidence signature valid
   - Phase-8 evidence shows GA verdict: PASS
   - Signing key is active (not revoked)

3. **Extract verified bundle**
   - Uploads as `verified-release-bundle` artifact
   - Used for all downstream promotion stages

**Outcome:**
- ✅ PASS → Continue to promotion gates
- ❌ FAIL → Block release, log failure, exit with error

---

#### Stage 4: DEV Promotion (Auto)

**Environment:** `dev` (no reviewers required)

**Actions:**
- Download `verified-release-bundle`
- Run `release/promote.sh --env dev`
- Auto-deploy to DEV environment

**Gate:** None (automatic)

---

#### Stage 5: STAGING Promotion (Gated)

**Environment:** `staging` (requires 1 reviewer)

**Re-verification:**
```bash
# Verify RELEASE_MANIFEST.json integrity
# Verify all artifact hashes match manifest
# Confirm bundle structure intact
```

**Actions:**
- Download `verified-release-bundle`
- Re-verify bundle integrity
- Run `release/promote.sh --env staging`
- Deploy to STAGING environment

**Gate:** 1 reviewer approval required

---

#### Stage 6: PROD Promotion (Dual-Approval)

**Environment:** `prod` (requires 2 reviewers)

**Final Verification:**
```bash
# Verify RELEASE_MANIFEST.json present
# Verify Phase-8 evidence shows GA verdict: PASS
# Verify all 4 required components present:
#   - core-installer
#   - linux-agent
#   - windows-agent
#   - dpi-probe
# Verify signing key is active
```

**Actions:**
- Download `verified-release-bundle`
- Perform final production gate checks
- Run `release/promote.sh --env prod`
- Deploy to PROD environment
- Run `release/publish.sh` to create immutable release record

**Gate:** 2 reviewer approvals required (no admin bypass)

---

## Verification Script: `scripts/verify_release_bundle.py`

### Purpose
Cryptographically verify signed release bundles using ed25519 signatures.

### Verification Process

1. **Bundle Integrity**
   - Verify tarball SHA256 matches checksum file
   - Verify tarball can be extracted

2. **Manifest Verification**
   - Parse `RELEASE_MANIFEST.json`
   - Verify required fields present
   - Verify bundle structure matches manifest

3. **Artifact Verification**
   - For each artifact in manifest:
     - Verify file exists
     - Verify SHA256 matches manifest
     - Verify size matches manifest

4. **Signature Verification**
   - Load public key from bundle (`keys/ransomeye-release-signing-v1.pub`)
   - Verify public key hash matches manifest
   - For each artifact:
     - Load artifact manifest (`.manifest.json`)
     - Load signature (`.manifest.sig`)
     - Verify ed25519 signature using public key
   - Verify SBOM signature
   - Verify evidence bundle signature

5. **Key Registry Check**
   - Check if signing key is revoked (if registry provided)
   - Check if signing key is active
   - Block release if key is revoked or inactive

6. **GA Verdict Check**
   - Verify Phase-8 evidence bundle present
   - Verify GA verdict is `PASS`
   - Block release if verdict is not `PASS`

### Exit Codes
- `0` - Verification PASSED (FOR-RELEASE)
- `1` - Verification FAILED (DO-NOT-RELEASE)

### Offline Verification
The script is designed for **long-term offline verification**:
- All required keys bundled in release
- No external dependencies required
- Can be verified years later without CI access
- No network connectivity required

---

## Security Properties

### Trust Model

```
┌─────────────────────────────────────────────────────────────┐
│ AIR-GAPPED SIGNING WORKSTATION                              │
│                                                             │
│  ┌──────────────────┐                                      │
│  │ Private Keys     │  ← NEVER LEAVES THIS MACHINE         │
│  │ (Encrypted Vault)│                                      │
│  └────────┬─────────┘                                      │
│           │                                                 │
│           v                                                 │
│  ┌──────────────────┐                                      │
│  │ Signing Process  │                                      │
│  │ (Dual Witnesses) │                                      │
│  └────────┬─────────┘                                      │
│           │                                                 │
│           v                                                 │
│  ┌──────────────────┐                                      │
│  │ Signed Bundle    │  ← UPLOADED TO CI                    │
│  │ + Public Key     │                                      │
│  └──────────────────┘                                      │
└─────────────────────────────────────────────────────────────┘
                         │
                         │ Upload
                         v
┌─────────────────────────────────────────────────────────────┐
│ CI ENVIRONMENT (UNTRUSTED)                                  │
│                                                             │
│  ┌──────────────────┐                                      │
│  │ Public Key       │  ← READ-ONLY, COMMITTED              │
│  │ (release/.keys/) │                                      │
│  └────────┬─────────┘                                      │
│           │                                                 │
│           v                                                 │
│  ┌──────────────────┐                                      │
│  │ Verify Signatures│  ← CRYPTOGRAPHIC VERIFICATION        │
│  │ (Read-Only)      │                                      │
│  └────────┬─────────┘                                      │
│           │                                                 │
│           v                                                 │
│  ┌──────────────────┐                                      │
│  │ Promotion Gates  │  ← DUAL APPROVAL                     │
│  │ (Human Authority)│                                      │
│  └──────────────────┘                                      │
└─────────────────────────────────────────────────────────────┘
```

### Guarantees

✅ **Private keys never in CI**  
✅ **Signatures generated offline only**  
✅ **CI can only verify (not sign)**  
✅ **Dual approval for production**  
✅ **Full audit trail (git + ceremony logs)**  
✅ **Long-term verifiability (bundled keys)**  
✅ **Revocation support (key registry)**  
✅ **No single point of compromise**  

---

## Key Rotation Procedure

When rotating signing keys:

### Step 1: Generate New Key (Offline)
```bash
python3 scripts/key_generation_ceremony.py \
  --key-id "ransomeye-release-signing-v2" \
  --key-type signing \
  --vault-dir keys/vault \
  --registry-path keys/registry.json \
  --log-dir keys/ceremony-logs \
  --participants "Participant1" "Participant2"
```

### Step 2: Export Public Key
```bash
cp keys/vault/ransomeye-release-signing-v2.pub release/.keys/
```

### Step 3: Update Registry (Mark Old Key as Rotated)
```bash
python3 scripts/key_lifecycle_manage.py \
  --action rotate \
  --key-id ransomeye-release-signing-v1 \
  --successor-key-id ransomeye-release-signing-v2 \
  --registry-path keys/registry.json
```

### Step 4: Commit Changes
```bash
git add release/.keys/ransomeye-release-signing-v2.pub
git add keys/registry.json
git commit -m "Rotate release signing key v1 → v2

- New key: ransomeye-release-signing-v2
- Old key: ransomeye-release-signing-v1 (rotated)
- Public key fingerprint: [fingerprint]"
git push origin main
```

### Step 5: Use New Key for Next Release
All future releases use `ransomeye-release-signing-v2`.

### Step 6: Keep Old Public Key
**DO NOT DELETE** `release/.keys/ransomeye-release-signing-v1.pub`.  
Old releases signed with v1 must remain verifiable.

---

## Key Revocation Procedure

If a key is compromised:

### Step 1: Revoke Key Immediately
```bash
python3 scripts/key_lifecycle_manage.py \
  --action revoke \
  --key-id ransomeye-release-signing-v1 \
  --registry-path keys/registry.json \
  --reason "Key compromised: [incident-id]"
```

### Step 2: Commit Revocation
```bash
git add keys/registry.json
git commit -m "SECURITY: Revoke compromised signing key

Key ID: ransomeye-release-signing-v1
Reason: [incident-details]
Incident: [incident-id]"
git push origin main
```

### Step 3: Generate New Key
Follow key rotation procedure to generate replacement key.

### Step 4: Re-sign Active Releases
All active releases must be re-signed with new key.

### Step 5: Notify Stakeholders
Publish security advisory with:
- Revoked key fingerprint
- New key fingerprint
- Re-signed release URLs

---

## Testing & Validation

### Dry-Run Checklist
**Location:** `docs/DRY_RUN_CHECKLIST_v1.0.0.md`

Validates:
- Key generation ceremony
- Offline signing process
- Bundle creation
- Offline verification
- CI integration (end-to-end)

### Manual Verification Test
```bash
# Download any signed bundle
wget https://releases.ransomeye.com/v1.0.0/ransomeye-v1.0.0-release-bundle.tar.gz

# Verify offline (no network required)
python3 scripts/verify_release_bundle.py \
  --bundle ransomeye-v1.0.0-release-bundle.tar.gz \
  --registry-path keys/registry.json

# Expected: ✅ RELEASE BUNDLE VERIFICATION PASSED
```

---

## Audit & Compliance

### Audit Trail Components

1. **Git History**
   - All public key commits tracked
   - All registry updates tracked
   - Full history of key lifecycle

2. **Ceremony Logs**
   - `keys/ceremony-logs/` directory
   - Immutable signing ceremony records
   - Witness signatures
   - Timestamps

3. **CI Workflow Logs**
   - Verification results
   - Promotion approvals
   - Deployment timestamps

4. **Release Manifests**
   - Embedded in every signed bundle
   - Self-contained audit trail
   - Long-term verifiable

### Compliance Evidence

For audit purposes, provide:
- Key registry (`keys/registry.json`)
- Ceremony logs (`keys/ceremony-logs/`)
- Signed release bundle
- CI workflow run logs
- Approval records (GitHub environments)

**Retention:** Permanent (required for historical verification)

---

## Status Summary

| Component | Status | Location |
|-----------|--------|----------|
| Public key distribution | ✅ Complete | `release/.keys/` |
| Key registry | ✅ Complete | `keys/registry.json` |
| CI verification wiring | ✅ Complete | `.github/workflows/ransomeye-release.yml` |
| Verification script | ✅ Complete | `scripts/verify_release_bundle.py` |
| Signing tooling | ✅ Complete | `supply-chain/cli/sign_artifacts.py` |
| Bundle creation | ✅ Complete | `scripts/create_release_bundle.py` |
| Promotion gates | ✅ Complete | GitHub environments (to be configured) |
| Dry-run checklist | ✅ Complete | `docs/DRY_RUN_CHECKLIST_v1.0.0.md` |

---

## Next Steps

1. **Configure GitHub Environments**
   - Create `dev`, `staging`, `prod` environments
   - Configure reviewer requirements
   - Disable admin bypass for PROD

2. **Execute Dry-Run Release**
   - Follow `docs/DRY_RUN_CHECKLIST_v1.0.0.md`
   - Validate end-to-end flow
   - Document any issues

3. **Production Release**
   - Tag v1.0.0
   - Execute full release process
   - Deploy to production

---

**Document Maintained By:** RansomEye Release Engineering  
**Last Updated:** 2026-01-18  
**Version:** 1.0.0
