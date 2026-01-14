# Phase 8.2 Release Artifact Integrity (Offline)

## Overview

Release artifact integrity validation performs offline verification of all release artifacts and SBOM before distribution. This validation ensures that all artifacts are properly signed, their hashes match their manifests, and the SBOM correctly references all artifacts.

**Phase 8.2 Requirement**: Run fully offline (no HTTP, no DNS, no external calls), exit 0 only if ALL checks pass, else exit 1.

## How to Run

### Basic Usage

```bash
cd /path/to/rebuild
python3 validation/release_integrity/release_integrity_check.py
```

### Environment Variables

The script uses the following environment variables:

- `RANSOMEYE_RELEASE_ROOT` (default: `./build/artifacts`)
  - Root directory containing release artifacts
  - Must contain artifact files and their manifests/signatures

- `RANSOMEYE_SIGNING_KEY_DIR` (optional)
  - Directory containing vendor signing keys
  - Keys should be named `{signing_key_id}.pub` for public keys

- `RANSOMEYE_SIGNING_KEY_ID` (default: `vendor-release-key-1`)
  - Signing key identifier to use for verification
  - Used when `RANSOMEYE_SIGNING_KEY_DIR` is set

### Example

```bash
export RANSOMEYE_RELEASE_ROOT=/path/to/release/bundle
export RANSOMEYE_SIGNING_KEY_DIR=/path/to/signing/keys
export RANSOMEYE_SIGNING_KEY_ID=vendor-release-key-1

python3 validation/release_integrity/release_integrity_check.py
```

### Exit Codes

- `0`: All checks passed
- `1`: One or more checks failed

## Expected Artifacts

The script expects the following artifacts:

1. **Core Installer** (`core-installer*.tar.gz` or `core-installer*.zip`)
2. **Linux Agent** (`linux-agent*.tar.gz` or `linux-agent*.zip`)
3. **Windows Agent** (`windows-agent*.tar.gz` or `windows-agent*.zip`)
4. **DPI Probe** (`dpi-probe*.tar.gz` or `dpi-probe*.zip`)

## Checks Performed

### For Each Artifact

The script performs the following checks for each artifact:

1. **Artifact Exists**
   - Verifies the artifact file is present in the release root

2. **Manifest Exists**
   - Looks for manifest file: `{artifact_name}.manifest.json`
   - Searches in: `signed/` subdirectory, artifact directory, or release root

3. **Signature Exists**
   - Looks for signature file: `{artifact_name}.manifest.sig`
   - Searches in: `signed/` subdirectory or alongside manifest

4. **SHA256 Matches Manifest**
   - Computes SHA256 hash of artifact file
   - Compares with hash in manifest
   - Must match exactly (case-insensitive)

5. **ed25519 Signature Verifies**
   - Verifies ed25519 signature using provided public key
   - Signature can be in separate `.sig` file or embedded in manifest

### SBOM Verification

The script performs the following SBOM checks:

1. **SBOM Exists**
   - Verifies `manifest.json` exists in release root

2. **SBOM Signature Exists**
   - Verifies `manifest.json.sig` exists in release root

3. **SBOM Signature Verifies**
   - Verifies ed25519 signature of SBOM manifest
   - Uses same public key as artifact verification

4. **SBOM References All Artifacts Exactly Once**
   - Verifies SBOM references each expected artifact exactly once
   - Checks for: `core-installer`, `linux-agent`, `windows-agent`, `dpi-probe`
   - Maps artifact types (`core`, `linux_agent`, `windows_agent`, `dpi_probe`) to expected names

## Expected Output

### Console Output (stderr)

The script writes human-readable output to stderr:

```
RansomEye v1.0 Phase 8.2 Release Artifact Integrity Check
======================================================================
Release root: /path/to/release/bundle
Using public key from key_dir: /path/to/keys (key_id: vendor-release-key-1)

Finding artifacts...
Verifying artifacts...
  Verifying core-installer...
  Verifying linux-agent...
  Verifying windows-agent...
  Verifying dpi-probe...

Verifying SBOM...

✓ All checks PASSED

Artifact Summary:
  ✓ core-installer: PASS
    ✓ artifact_exists: PASS
    ✓ manifest_exists: PASS
    ✓ signature_exists: PASS
    ✓ sha256_match: PASS
    ✓ signature_verify: PASS
  ✓ linux-agent: PASS
    ✓ artifact_exists: PASS
    ✓ manifest_exists: PASS
    ✓ signature_exists: PASS
    ✓ sha256_match: PASS
    ✓ signature_verify: PASS
  ✓ windows-agent: PASS
    ✓ artifact_exists: PASS
    ✓ manifest_exists: PASS
    ✓ signature_exists: PASS
    ✓ sha256_match: PASS
    ✓ signature_verify: PASS
  ✓ dpi-probe: PASS
    ✓ artifact_exists: PASS
    ✓ manifest_exists: PASS
    ✓ signature_exists: PASS
    ✓ sha256_match: PASS
    ✓ signature_verify: PASS

SBOM Status: PASS
  ✓ sbom_exists: PASS
  ✓ sbom_signature_exists: PASS
  ✓ sbom_signature_verify: PASS
  ✓ sbom_references_core-installer: PASS
  ✓ sbom_references_linux-agent: PASS
  ✓ sbom_references_windows-agent: PASS
  ✓ sbom_references_dpi-probe: PASS

Results written to: /path/to/rebuild/validation/release_integrity/release_integrity_result.json
```

### JSON Output (machine-readable)

Results are written to `release_integrity_result.json` in the same directory:

```json
{
  "timestamp": "2024-01-15T10:30:45.123456+00:00",
  "artifacts": [
    {
      "name": "core-installer",
      "checks": [
        {
          "name": "artifact_exists",
          "status": "PASS",
          "message": "Artifact file found: core-installer-v1.0.0.tar.gz",
          "error": ""
        },
        {
          "name": "manifest_exists",
          "status": "PASS",
          "message": "Manifest file found: /path/to/signed/core-installer-v1.0.0.tar.gz.manifest.json",
          "error": ""
        },
        {
          "name": "signature_exists",
          "status": "PASS",
          "message": "Signature file found: /path/to/signed/core-installer-v1.0.0.tar.gz.manifest.sig",
          "error": ""
        },
        {
          "name": "sha256_match",
          "status": "PASS",
          "message": "SHA256 matches manifest: abc123...",
          "error": ""
        },
        {
          "name": "signature_verify",
          "status": "PASS",
          "message": "ed25519 signature verified",
          "error": ""
        }
      ],
      "status": "PASS"
    },
    {
      "name": "linux-agent",
      "checks": [...],
      "status": "PASS"
    },
    {
      "name": "windows-agent",
      "checks": [...],
      "status": "PASS"
    },
    {
      "name": "dpi-probe",
      "checks": [...],
      "status": "PASS"
    }
  ],
  "sbom_status": {
    "status": "PASS",
    "checks": [
      {
        "name": "sbom_exists",
        "status": "PASS",
        "message": "SBOM manifest found: /path/to/manifest.json",
        "error": ""
      },
      {
        "name": "sbom_signature_exists",
        "status": "PASS",
        "message": "SBOM signature found: /path/to/manifest.json.sig",
        "error": ""
      },
      {
        "name": "sbom_signature_verify",
        "status": "PASS",
        "message": "SBOM signature verified successfully",
        "error": ""
      },
      {
        "name": "sbom_references_core-installer",
        "status": "PASS",
        "message": "SBOM references core-installer exactly once",
        "error": ""
      },
      {
        "name": "sbom_references_linux-agent",
        "status": "PASS",
        "message": "SBOM references linux-agent exactly once",
        "error": ""
      },
      {
        "name": "sbom_references_windows-agent",
        "status": "PASS",
        "message": "SBOM references windows-agent exactly once",
        "error": ""
      },
      {
        "name": "sbom_references_dpi-probe",
        "status": "PASS",
        "message": "SBOM references dpi-probe exactly once",
        "error": ""
      }
    ]
  },
  "overall_status": "PASS"
}
```

## Failure Semantics

### Overall Status

- **PASS**: All artifact checks passed AND SBOM checks passed AND all expected artifacts found
- **FAIL**: Any artifact check failed OR SBOM check failed OR any expected artifact missing

### Individual Check Status

Each check has:
- **status**: `PASS` or `FAIL`
- **message**: Human-readable description of the result
- **error**: Error message (if status is `FAIL`)

### Exit Behavior

- Script exits with code `0` if `overall_status` is `PASS`
- Script exits with code `1` if `overall_status` is `FAIL`
- JSON output is always written, regardless of pass/fail status

### Common Failure Scenarios

1. **Artifact Not Found**
   - Artifact file missing from release root
   - Artifact name doesn't match expected pattern

2. **Manifest Not Found**
   - Manifest file missing for artifact
   - Manifest in unexpected location

3. **Signature Not Found**
   - Signature file missing for artifact
   - Signature in unexpected location

4. **SHA256 Mismatch**
   - Artifact file has been modified
   - Manifest contains incorrect hash

5. **Signature Verification Failed**
   - Signature is invalid or corrupted
   - Wrong public key used for verification
   - Artifact or manifest has been tampered with

6. **SBOM Verification Failed**
   - SBOM manifest missing or invalid
   - SBOM signature invalid
   - SBOM doesn't reference all artifacts
   - SBOM references artifacts multiple times

## Dependencies

### Required

- Python 3.10+
- `cryptography` library (for ed25519 signature verification)
- Supply-chain verification modules:
  - `supply-chain/crypto/artifact_verifier.py`
  - `supply-chain/crypto/vendor_key_manager.py`
  - `supply-chain/engine/verification_engine.py`
- Release verification module:
  - `release/verify_sbom.py`

### Installation

The `cryptography` library is typically available in most Python environments. If not:

```bash
pip install cryptography
```

## Offline Operation

This script is designed to run **fully offline** (no network calls):

- All file operations are local filesystem
- No HTTP/HTTPS requests
- No DNS lookups
- No external API calls
- All verification uses local files and keys

## File Structure

Expected release root structure:

```
release_root/
├── core-installer-v1.0.0.tar.gz
├── linux-agent-v1.0.0.tar.gz
├── windows-agent-v1.0.0.tar.gz
├── dpi-probe-v1.0.0.tar.gz
├── signed/
│   ├── core-installer-v1.0.0.tar.gz.manifest.json
│   ├── core-installer-v1.0.0.tar.gz.manifest.sig
│   ├── linux-agent-v1.0.0.tar.gz.manifest.json
│   ├── linux-agent-v1.0.0.tar.gz.manifest.sig
│   ├── windows-agent-v1.0.0.tar.gz.manifest.json
│   ├── windows-agent-v1.0.0.tar.gz.manifest.sig
│   ├── dpi-probe-v1.0.0.tar.gz.manifest.json
│   └── dpi-probe-v1.0.0.tar.gz.manifest.sig
├── manifest.json (SBOM)
├── manifest.json.sig (SBOM signature)
└── keys/ (optional)
    └── vendor-release-key-1.pub
```

## Integration

This script is intended for:

- Pre-release validation
- Release bundle verification
- CI/CD pipeline integration (deterministic checks)
- Customer acceptance testing

**Note**: This script does NOT modify CI workflows. It is a standalone validation tool.

## Troubleshooting

### Public Key Not Found

If public key is not found:

1. Verify `RANSOMEYE_SIGNING_KEY_DIR` is set correctly
2. Check that public key file exists: `{signing_key_id}.pub`
3. Alternatively, place `public_key.pem` in release root
4. Or place public key in `release_root/keys/{signing_key_id}.pub`

### Artifact Not Found

If artifacts are not found:

1. Verify `RANSOMEYE_RELEASE_ROOT` points to correct directory
2. Check artifact file names match expected patterns:
   - `*core*installer*.tar.gz` or `*core*installer*.zip`
   - `*linux-agent*.tar.gz` or `*linux-agent*.zip`
   - `*windows-agent*.tar.gz` or `*windows-agent*.zip`
   - `*dpi-probe*.tar.gz` or `*dpi-probe*.zip`

### Manifest/Signature Not Found

If manifest or signature files are not found:

1. Check `signed/` subdirectory in release root
2. Check same directory as artifact file
3. Check release root directory
4. Verify file naming matches: `{artifact_name}.manifest.json` and `{artifact_name}.manifest.sig`

### SBOM Verification Failed

If SBOM verification fails:

1. Verify `manifest.json` exists in release root
2. Verify `manifest.json.sig` exists in release root
3. Check SBOM contains all expected artifacts
4. Verify each artifact is referenced exactly once
5. Check artifact types match expected values (`core`, `linux_agent`, `windows_agent`, `dpi_probe`)
