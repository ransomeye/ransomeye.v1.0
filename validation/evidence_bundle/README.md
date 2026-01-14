# Phase 8.3 Evidence Bundle Freezing & Attestation

## Overview

Evidence bundle freezing creates a **tamper-evident, immutable evidence bundle** that cryptographically freezes all validation results, artifact hashes, and SBOM information. This bundle serves as the **final authority** before production release and provides cryptographic proof that all validation checks passed.

**Phase 8.3 Requirement**: Create tamper-evident evidence bundle that can be independently verified offline.

## Purpose

The evidence bundle freezes:

- Phase 8.1 Runtime Smoke results
- Phase 8.2 Release Integrity results
- GA verdict (if present)
- Artifact + SBOM trust chain
- Hashes of all evidence files

This bundle is the **last checkpoint** before production release. Any tampering with evidence files will be detected through hash mismatches or signature verification failures.

## How to Run

### Basic Usage

```bash
cd /path/to/rebuild
export RANSOMEYE_SIGNING_KEY_DIR=/path/to/signing/keys
export RANSOMEYE_RELEASE_ROOT=/path/to/release/bundle  # optional, default: ./build/artifacts
export RANSOMEYE_SIGNING_KEY_ID=vendor-release-key-1   # optional, default: vendor-release-key-1

python3 validation/evidence_bundle/freeze_evidence_bundle.py
```

### Prerequisites

Before running, ensure:

1. **Phase 8.1 completed successfully**
   - `validation/runtime_smoke/runtime_smoke_result.json` exists
   - `overall_status` is `PASS`

2. **Phase 8.2 completed successfully**
   - `validation/release_integrity/release_integrity_result.json` exists
   - `overall_status` is `PASS`

3. **Signing keys available**
   - `RANSOMEYE_SIGNING_KEY_DIR` points to directory with signing keys
   - Key file `{signing_key_id}.pem` exists in key directory

4. **Release artifacts available** (optional)
   - `RANSOMEYE_RELEASE_ROOT` points to release bundle directory
   - Artifacts and SBOM files are present

### Environment Variables

- `RANSOMEYE_SIGNING_KEY_DIR` (required)
  - Directory containing vendor signing keys
  - Must contain `{signing_key_id}.pem` for signing

- `RANSOMEYE_RELEASE_ROOT` (optional, default: `./build/artifacts`)
  - Root directory containing release artifacts
  - Used to collect artifact hashes and SBOM information

- `RANSOMEYE_SIGNING_KEY_ID` (optional, default: `vendor-release-key-1`)
  - Signing key identifier
  - Used to locate key file: `{signing_key_id}.pem`

### Exit Codes

- `0`: Evidence bundle created and signed successfully
- `1`: Any failure (missing inputs, validation failure, signing error)

## Mandatory Checks (Fail-Closed)

The script **MUST FAIL** if:

1. **Phase 8.1 result missing or invalid**
   - File not found: `validation/runtime_smoke/runtime_smoke_result.json`
   - Invalid JSON
   - `overall_status != PASS`

2. **Phase 8.2 result missing or invalid**
   - File not found: `validation/release_integrity/release_integrity_result.json`
   - Invalid JSON
   - `overall_status != PASS`

3. **Signing key not available**
   - `RANSOMEYE_SIGNING_KEY_DIR` not set
   - Key directory not found
   - Key file not found

4. **Evidence file unreadable**
   - Any referenced file cannot be read
   - Any referenced file is malformed JSON

**Note**: GA verdict is optional. If not found, the bundle is still created (with `ga_verdict: null`).

## Evidence Bundle Structure

The script creates:

```
validation/evidence_bundle/
├── evidence_bundle.json      # Evidence bundle (immutable)
└── evidence_bundle.json.sig   # ed25519 signature
```

### Bundle JSON Format

```json
{
  "bundle_version": "1.0",
  "created_at": "2024-01-15T10:30:45.123456+00:00",
  "host": "build-host.example.com",
  "git": {
    "repo": "https://github.com/ransomeye/ransomeye.v1.0.git",
    "branch": "main",
    "commit": "abc123def456..."
  },
  "inputs": {
    "runtime_smoke": "sha256_hash_of_phase_8_1_result",
    "release_integrity": "sha256_hash_of_phase_8_2_result",
    "ga_verdict": "sha256_hash_of_ga_verdict_or_null"
  },
  "artifacts": [
    {
      "name": "core-installer-v1.0.0.tar.gz",
      "sha256": "abc123..."
    },
    {
      "name": "linux-agent-v1.0.0.tar.gz",
      "sha256": "def456..."
    }
  ],
  "sbom": {
    "sha256": "sha256_hash_of_manifest.json",
    "signature_sha256": "sha256_hash_of_manifest.json.sig"
  },
  "overall_status": "FROZEN"
}
```

### Fields

- `bundle_version`: Bundle format version (currently "1.0")
- `created_at`: ISO 8601 UTC timestamp when bundle was created
- `host`: Hostname of machine that created the bundle
- `git.repo`: Git remote URL (origin)
- `git.branch`: Current git branch
- `git.commit`: Current git commit hash
- `inputs.runtime_smoke`: SHA256 hash of Phase 8.1 result file
- `inputs.release_integrity`: SHA256 hash of Phase 8.2 result file
- `inputs.ga_verdict`: SHA256 hash of GA verdict file (or `null` if not found)
- `artifacts[]`: Array of artifact hashes (name, sha256)
- `sbom.sha256`: SHA256 hash of SBOM manifest.json
- `sbom.signature_sha256`: SHA256 hash of SBOM signature file
- `overall_status`: Always "FROZEN" on successful creation

## Cryptographic Attestation

The evidence bundle is signed using **ed25519**:

1. **Signature Creation**
   - Bundle JSON is serialized to canonical JSON (sorted keys, no whitespace)
   - Canonical JSON is hashed with SHA256
   - Hash is signed with ed25519 private key
   - Signature is base64-encoded and written to `evidence_bundle.json.sig`

2. **Signature Verification**
   - Load public key from `{signing_key_id}.pub`
   - Recreate canonical JSON from bundle
   - Hash canonical JSON with SHA256
   - Verify signature against hash

3. **Tamper Detection**
   - Any modification to bundle JSON will cause hash mismatch
   - Signature verification will fail if bundle is tampered
   - Hash mismatches in referenced files will be detected

## Offline Verification Steps

### Step 1: Verify Bundle Hash

```bash
# Compute hash of bundle
sha256sum validation/evidence_bundle/evidence_bundle.json

# Compare with expected hash (if known)
```

### Step 2: Verify Signature

```bash
# Using supply-chain verification tools
python3 supply-chain/cli/verify_artifacts.py \
    --artifact validation/evidence_bundle/evidence_bundle.json \
    --manifest validation/evidence_bundle/evidence_bundle.json \
    --public-key /path/to/public_key.pem
```

Or using Python:

```python
from supply_chain.crypto.artifact_verifier import ArtifactVerifier
from pathlib import Path
import json

# Load bundle
bundle_path = Path('validation/evidence_bundle/evidence_bundle.json')
signature_path = Path('validation/evidence_bundle/evidence_bundle.json.sig')
public_key_path = Path('/path/to/public_key.pem')

# Load bundle
with open(bundle_path, 'r') as f:
    bundle = json.load(f)

# Load signature
with open(signature_path, 'r') as f:
    signature = f.read().strip()

# Add signature to bundle for verification
bundle['signature'] = signature

# Verify
verifier = ArtifactVerifier(public_key_path=public_key_path)
if verifier.verify_manifest_signature(bundle):
    print("✓ Signature verified")
else:
    print("✗ Signature verification failed")
```

### Step 3: Verify Referenced Files

```bash
# Verify Phase 8.1 hash
sha256sum validation/runtime_smoke/runtime_smoke_result.json
# Compare with bundle['inputs']['runtime_smoke']

# Verify Phase 8.2 hash
sha256sum validation/release_integrity/release_integrity_result.json
# Compare with bundle['inputs']['release_integrity']

# Verify artifact hashes
for artifact in bundle['artifacts']:
    sha256sum "$RANSOMEYE_RELEASE_ROOT/${artifact['name']}"
    # Compare with artifact['sha256']
```

## Expected Output

### Console Output (stderr)

The script writes human-readable output to stderr:

```
RansomEye v1.0 Phase 8.3 Evidence Bundle Freezing & Attestation
======================================================================
Project root: /path/to/rebuild
Release root: /path/to/release/bundle
Key directory: /path/to/signing/keys
Signing key ID: vendor-release-key-1

Loading Phase 8.1 results...
  ✓ Phase 8.1: abc123def4567890...
Loading Phase 8.2 results...
  ✓ Phase 8.2: def456abc1237890...
Loading GA verdict (optional)...
  ✓ GA verdict: 7890abc123def456...

Collecting artifact hashes...
  ✓ Found 4 artifacts
Collecting SBOM info...
  ✓ SBOM manifest: 1234567890abcdef...
  ✓ SBOM signature: abcdef1234567890...

Signing evidence bundle...
  ✓ Signature created

Writing evidence bundle...
  ✓ Bundle written: /path/to/rebuild/validation/evidence_bundle/evidence_bundle.json
  ✓ Signature written: /path/to/rebuild/validation/evidence_bundle/evidence_bundle.json.sig

Evidence Bundle Summary:
  Bundle version: 1.0
  Created at: 2024-01-15T10:30:45.123456+00:00
  Host: build-host.example.com
  Git repo: https://github.com/ransomeye/ransomeye.v1.0.git
  Git branch: main
  Git commit: abc123def456...
  Artifacts: 4
  Overall status: FROZEN

✓ Evidence bundle frozen and attested
```

### Failure Output

If any check fails:

```
ERROR: Phase 8.1 overall_status is not PASS: FAIL
```

Or:

```
ERROR: Phase 8.2 result not found: /path/to/validation/release_integrity/release_integrity_result.json
```

## Failure Semantics

### Exit Behavior

- Script exits with code `0` only if bundle and signature are created successfully
- Script exits with code `1` on ANY failure
- JSON outputs are NOT written on failure (fail-closed)

### Common Failure Scenarios

1. **Phase 8.1 Not Passed**
   - Phase 8.1 result missing
   - Phase 8.1 `overall_status != PASS`
   - Phase 8.1 result is invalid JSON

2. **Phase 8.2 Not Passed**
   - Phase 8.2 result missing
   - Phase 8.2 `overall_status != PASS`
   - Phase 8.2 result is invalid JSON

3. **Signing Key Not Found**
   - `RANSOMEYE_SIGNING_KEY_DIR` not set
   - Key directory doesn't exist
   - Key file `{signing_key_id}.pem` not found

4. **File Read Errors**
   - Evidence files unreadable
   - Evidence files are malformed JSON
   - Permission errors

## Dependencies

### Required

- Python 3.10+
- `cryptography` library (for ed25519 signing)
- Supply-chain signing modules:
  - `supply-chain/crypto/artifact_signer.py`
  - `supply-chain/crypto/vendor_key_manager.py`
- Git (for repository information)

### Installation

The `cryptography` library is typically available in most Python environments. If not:

```bash
pip install cryptography
```

## Offline Operation

This script is designed to run **fully offline** (no network calls):

- All file operations are local filesystem
- Git commands are local (no network access)
- No HTTP/HTTPS requests
- No DNS lookups
- No external API calls
- All signing uses local keys

## Integration

This script is intended for:

- Pre-release evidence freezing
- Production readiness certification
- Audit trail creation
- Compliance documentation

**Note**: This script does NOT modify CI workflows. It is a standalone validation tool.

## Troubleshooting

### Phase 8.1/8.2 Not Passed

If Phase 8.1 or 8.2 did not pass:

1. Run Phase 8.1 validation:
   ```bash
   python3 validation/runtime_smoke/runtime_smoke_check.py
   ```

2. Run Phase 8.2 validation:
   ```bash
   python3 validation/release_integrity/release_integrity_check.py
   ```

3. Fix any failures before freezing evidence bundle

### Signing Key Not Found

If signing key is not found:

1. Verify `RANSOMEYE_SIGNING_KEY_DIR` is set correctly
2. Check that key directory exists
3. Verify key file exists: `{signing_key_id}.pem`
4. Check file permissions (must be readable)

### Git Information Missing

If git information is missing:

1. Verify you're in a git repository
2. Check that git is installed and in PATH
3. Verify git remote is configured: `git remote get-url origin`
4. Git information is optional - bundle will still be created with empty strings

### Artifact Hashes Not Collected

If artifact hashes are not collected:

1. Verify `RANSOMEYE_RELEASE_ROOT` points to correct directory
2. Check that artifact files exist in release root
3. Verify artifact file names match expected patterns (`*.tar.gz`, `*.zip`)
4. Artifact collection is optional - bundle will still be created with empty array

## Security Considerations

1. **Private Key Protection**
   - Signing keys must be stored securely
   - Private keys should never be committed to repository
   - Use secure key management practices

2. **Bundle Immutability**
   - Once created, bundle should not be modified
   - Any modification will break signature verification
   - Store bundles in tamper-evident storage

3. **Verification**
   - Always verify bundle signature before trusting
   - Verify all referenced file hashes
   - Use independent verification tools

## Example Verification Script

```bash
#!/bin/bash
# Verify evidence bundle

BUNDLE_PATH="validation/evidence_bundle/evidence_bundle.json"
SIGNATURE_PATH="validation/evidence_bundle/evidence_bundle.json.sig"
PUBLIC_KEY_PATH="/path/to/public_key.pem"

# Verify signature
python3 -c "
from supply_chain.crypto.artifact_verifier import ArtifactVerifier
from pathlib import Path
import json

bundle_path = Path('$BUNDLE_PATH')
signature_path = Path('$SIGNATURE_PATH')
public_key_path = Path('$PUBLIC_KEY_PATH')

with open(bundle_path, 'r') as f:
    bundle = json.load(f)

with open(signature_path, 'r') as f:
    signature = f.read().strip()

bundle['signature'] = signature

verifier = ArtifactVerifier(public_key_path=public_key_path)
if verifier.verify_manifest_signature(bundle):
    print('✓ Signature verified')
    exit(0)
else:
    print('✗ Signature verification failed')
    exit(1)
"

if [ $? -eq 0 ]; then
    echo "✓ Evidence bundle verified"
else
    echo "✗ Evidence bundle verification failed"
    exit 1
fi
```
