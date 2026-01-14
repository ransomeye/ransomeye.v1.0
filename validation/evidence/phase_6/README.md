# Phase-6 Evidence Directory

This directory contains **immutable evidence** from Phase-6 CI execution proving GA readiness.

## Directory Structure

```
validation/evidence/phase_6/
├── README.md                    # This file
├── verify_offline.sh            # Offline verification script
├── phase_c_linux_results.json   # Phase C-L validation results (from CI)
├── phase_c_windows_results.json # Phase C-W validation results (from CI)
├── phase_c_aggregate_verdict.json # Final GA verdict (from CI)
├── artifacts/                   # Signed artifacts from CI
│   ├── core-installer.tar.gz
│   ├── linux-agent.tar.gz
│   ├── windows-agent.zip
│   ├── dpi-probe.tar.gz
│   ├── signed/                 # Artifact manifests and signatures
│   │   ├── *.manifest.json
│   │   └── *.manifest.sig
│   └── sbom/                   # SBOM and signature
│       ├── manifest.json
│       └── manifest.json.sig
├── keys/                       # Signing public key
│   └── vendor-signing-key-ci-signing-key.pub
└── evidence_hashes.txt         # SHA256 hashes of all evidence files
```

## Evidence Collection

### From GitHub Actions

1. Navigate to successful `CI Build and Sign - PHASE 6` workflow run
2. Download artifacts:
   - `phase-c-linux-results` → extract here
   - `phase-c-windows-results` → extract here (merge with linux results)
   - `ga-verdict` → extract here (contains `phase_c_aggregate_verdict.json`)
   - `signed-artifacts` → extract to `artifacts/`
   - `signing-public-key` → extract to `keys/`

### File Naming

After extraction, ensure files are named:
- `phase_c_linux_results.json`
- `phase_c_windows_results.json`
- `phase_c_aggregate_verdict.json`

## Offline Verification

Run the verification script in a clean environment (no network access):

```bash
cd validation/evidence/phase_6
chmod +x verify_offline.sh
./verify_offline.sh
```

The script verifies:
1. GA verdict is `GA-READY`
2. All artifact signatures are valid
3. SBOM signature is valid
4. All hashes are computed

## Evidence Immutability

**Once populated, these files must not be modified.**

- Evidence files are from CI runs only
- No local regeneration allowed
- Modifications invalidate certification
- New evidence requires new certification

## Hash Verification

After collecting evidence, compute hashes:

```bash
cd validation/evidence/phase_6
find . -type f -exec sha256sum {} \; | sort > evidence_hashes.txt
```

Include these hashes in `PHASE_6_GA_PROOF.md`.

## Related Documentation

- `validation/evidence/PHASE_6_GA_PROOF.md` - Main certification document
- `.github/workflows/ci-validation.yml` - CI validation workflow
- `.github/workflows/ci-build-and-sign.yml` - Build and sign workflow
