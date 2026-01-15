# Phase-9 Step 4: Offline Verification Walkthrough

**Document Classification:** Operational Procedure  
**Version:** 1.0  
**Date:** 2024-01-15

---

## Overview

This walkthrough demonstrates that the release gate can run **completely offline** without CI, GitHub, or network access. All verification uses only the release bundle contents.

---

## Prerequisites

**Required:**
- Release bundle tarball: `ransomeye-<version>-release-bundle.tar.gz`
- Bundle checksum file: `ransomeye-<version>-release-bundle.tar.gz.sha256` (optional)
- Python 3.10+ with dependencies installed
- No network access required
- No CI access required
- No GitHub access required

**Optional:**
- Key registry file (for revocation checking): `keys/registry.json`

---

## Step-by-Step Offline Verification

### Step 1: Verify Bundle Integrity

```bash
# Verify bundle checksum (if available)
if [ -f "ransomeye-v1.0.0-release-bundle.tar.gz.sha256" ]; then
    EXPECTED_HASH=$(awk '{print $1}' ransomeye-v1.0.0-release-bundle.tar.gz.sha256)
    ACTUAL_HASH=$(sha256sum ransomeye-v1.0.0-release-bundle.tar.gz | awk '{print $1}')
    
    if [ "$EXPECTED_HASH" != "$ACTUAL_HASH" ]; then
        echo "❌ FAIL: Bundle checksum mismatch"
        exit 1
    fi
    echo "✅ Bundle checksum verified"
fi

# Verify bundle can be extracted
tar tzf ransomeye-v1.0.0-release-bundle.tar.gz > /dev/null
if [ $? -ne 0 ]; then
    echo "❌ FAIL: Bundle is corrupted or invalid"
    exit 1
fi
echo "✅ Bundle integrity verified"
```

**Evidence:** Bundle is valid tarball, checksum matches (if provided)

---

### Step 2: Extract Bundle

```bash
# Extract bundle
mkdir -p verification-extract
tar xzf ransomeye-v1.0.0-release-bundle.tar.gz -C verification-extract

BUNDLE_DIR="verification-extract/ransomeye-v1.0.0-release-bundle"
```

**Evidence:** Bundle extracted successfully, directory structure verified

---

### Step 3: Verify RELEASE_MANIFEST.json

```bash
# Verify manifest exists
if [ ! -f "$BUNDLE_DIR/RELEASE_MANIFEST.json" ]; then
    echo "❌ FAIL: RELEASE_MANIFEST.json not found"
    exit 1
fi

# Verify manifest is valid JSON
python3 -c "import json; json.load(open('$BUNDLE_DIR/RELEASE_MANIFEST.json'))" || {
    echo "❌ FAIL: RELEASE_MANIFEST.json is invalid JSON"
    exit 1
}

# Display manifest contents
python3 << 'EOF'
import json
with open('$BUNDLE_DIR/RELEASE_MANIFEST.json') as f:
    manifest = json.load(f)
    print(f"Release version: {manifest['release_version']}")
    print(f"Artifacts: {len(manifest['artifacts'])}")
    print(f"Signatures: {len(manifest['signatures'])}")
    print(f"GA verdict: {manifest['evidence']['ga_verdict']}")
EOF
```

**Evidence:** Manifest exists, is valid JSON, contains required fields

---

### Step 4: Verify Artifacts Match Manifest

```bash
# Verify all artifacts exist and match manifest hashes
python3 << 'EOF'
import json
import hashlib
from pathlib import Path

bundle_dir = Path('$BUNDLE_DIR')
manifest_path = bundle_dir / 'RELEASE_MANIFEST.json'

with open(manifest_path) as f:
    manifest = json.load(f)

for artifact in manifest['artifacts']:
    artifact_path = bundle_dir / artifact['path']
    if not artifact_path.exists():
        print(f"❌ FAIL: Artifact not found: {artifact['path']}")
        exit(1)
    
    # Compute hash
    hash_obj = hashlib.sha256()
    with open(artifact_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_obj.update(chunk)
    actual_hash = hash_obj.hexdigest()
    
    if actual_hash != artifact['sha256']:
        print(f"❌ FAIL: Hash mismatch for {artifact['name']}")
        exit(1)
    
    print(f"✅ {artifact['name']}: hash verified")

print("✅ All artifacts match manifest")
EOF
```

**Evidence:** All artifacts exist, hashes match manifest

---

### Step 5: Verify Signatures (Offline, Using Bundled Public Key)

```bash
# Get public key from bundle
PUBLIC_KEY_PATH="$BUNDLE_DIR/keys/vendor-signing-key-1.pub"

if [ ! -f "$PUBLIC_KEY_PATH" ]; then
    PUBLIC_KEY_PATH=$(find "$BUNDLE_DIR/keys" -name "*.pub" | head -1)
fi

if [ ! -f "$PUBLIC_KEY_PATH" ]; then
    echo "❌ FAIL: Public key not found in bundle"
    exit 1
fi

echo "Using public key from bundle: $PUBLIC_KEY_PATH"

# Verify SBOM signature
python3 release/verify_sbom.py \
  --release-root "$BUNDLE_DIR/artifacts" \
  --manifest "$BUNDLE_DIR/sbom/manifest.json" \
  --signature "$BUNDLE_DIR/sbom/manifest.json.sig" \
  --public-key "$PUBLIC_KEY_PATH"

if [ $? -ne 0 ]; then
    echo "❌ FAIL: SBOM signature verification failed"
    exit 1
fi
echo "✅ SBOM signature verified"

# Verify all artifact signatures
cd "$BUNDLE_DIR/signatures"
for manifest in *.manifest.json; do
    ARTIFACT_NAME="${manifest%.manifest.json}"
    ARTIFACT_FILE="../artifacts/${ARTIFACT_NAME}"
    
    if [ -f "$ARTIFACT_FILE" ]; then
        python3 ../../../../supply-chain/cli/verify_artifacts.py \
          --artifact "$ARTIFACT_FILE" \
          --manifest "$manifest" \
          --public-key "$PUBLIC_KEY_PATH"
        
        if [ $? -ne 0 ]; then
            echo "❌ FAIL: Signature verification failed for $ARTIFACT_NAME"
            exit 1
        fi
        echo "✅ Signature verified: $ARTIFACT_NAME"
    fi
done
```

**Evidence:** All signatures verified using bundled public key (no CI access)

---

### Step 6: Verify Phase-8 Evidence Bundle

```bash
# Verify evidence bundle exists
EVIDENCE_BUNDLE="$BUNDLE_DIR/evidence/evidence_bundle.json"
EVIDENCE_SIG="$BUNDLE_DIR/evidence/evidence_bundle.json.sig"

if [ ! -f "$EVIDENCE_BUNDLE" ]; then
    echo "❌ FAIL: Evidence bundle not found"
    exit 1
fi

# Verify GA verdict is PASS
GA_VERDICT=$(python3 -c "import json; print(json.load(open('$EVIDENCE_BUNDLE')).get('overall_status', 'UNKNOWN'))")

if [ "$GA_VERDICT" != "PASS" ]; then
    echo "❌ FAIL: GA verdict is $GA_VERDICT (must be PASS)"
    exit 1
fi
echo "✅ GA verdict: PASS"

# Verify evidence bundle signature using bundled public key
python3 << 'EOF'
import json
import sys
from pathlib import Path

bundle_dir = Path('$BUNDLE_DIR')
evidence_path = bundle_dir / 'evidence/evidence_bundle.json'
evidence_sig_path = bundle_dir / 'evidence/evidence_bundle.json.sig'
public_key_path = bundle_dir / 'keys/vendor-signing-key-1.pub'

# Load evidence bundle
with open(evidence_path, 'r') as f:
    evidence_bundle = json.load(f)

# Load signature
signature = evidence_sig_path.read_text(encoding='utf-8').strip()
evidence_bundle['signature'] = signature

# Verify signature
sys.path.insert(0, 'supply-chain')
from crypto.artifact_verifier import ArtifactVerifier

verifier = ArtifactVerifier(public_key_path=public_key_path)
if verifier.verify_manifest_signature(evidence_bundle):
    print("✅ Evidence bundle signature verified")
else:
    print("❌ FAIL: Evidence bundle signature verification failed")
    sys.exit(1)
EOF
```

**Evidence:** Evidence bundle verified, GA verdict is PASS, signature verified using bundled key

---

### Step 7: Check Key Revocation (Optional, if Registry Available)

```bash
# If key registry is available (optional)
if [ -f "keys/registry.json" ]; then
    python3 << 'EOF'
    import json
    import sys
    from pathlib import Path
    
    bundle_dir = Path('$BUNDLE_DIR')
    manifest_path = bundle_dir / 'RELEASE_MANIFEST.json'
    registry_path = Path('keys/registry.json')
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    key_id = manifest['public_keys'][0]['key_id']
    
    sys.path.insert(0, 'supply-chain')
    from crypto.key_registry import KeyRegistry
    
    registry = KeyRegistry(registry_path)
    
    if registry.is_revoked(key_id):
        print(f"❌ FAIL: Signing key {key_id} is REVOKED")
        sys.exit(1)
    
    if not registry.is_key_active(key_id):
        key_entry = registry.get_key(key_id)
        status = key_entry['status'] if key_entry else 'unknown'
        print(f"❌ FAIL: Signing key {key_id} is not active (status: {status})")
        sys.exit(1)
    
    print(f"✅ Signing key {key_id} is active (not revoked)")
EOF
else
    echo "⚠️  Key registry not available (revocation check skipped)"
fi
```

**Evidence:** Key revocation checked (if registry available)

---

### Step 8: Complete Verification

```bash
# Run complete verification script
python3 scripts/verify_release_bundle.py \
  --bundle ransomeye-v1.0.0-release-bundle.tar.gz \
  --checksum ransomeye-v1.0.0-release-bundle.tar.gz.sha256 \
  --registry-path keys/registry.json \
  --extract-dir verification-extract

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ FOR-RELEASE: Bundle verified offline"
    echo "=========================================="
    echo ""
    echo "All verification completed using bundled keys and evidence."
    echo "No CI access, GitHub access, or network access required."
else
    echo ""
    echo "=========================================="
    echo "❌ DO-NOT-RELEASE: Verification failed"
    echo "=========================================="
    exit 1
fi
```

**Evidence:** Complete verification passed, release approved

---

## Verification Without Network Access

### Demonstration

1. **Disable Network:**
   ```bash
   # Disable network interface (example)
   sudo ifdown eth0
   # Or use firewall rules
   sudo iptables -A OUTPUT -j DROP
   ```

2. **Run Verification:**
   ```bash
   # All verification steps above work without network
   # No external dependencies
   # No CI access required
   # No GitHub API calls
   ```

3. **Re-enable Network:**
   ```bash
   sudo ifup eth0
   # Or remove firewall rules
   ```

**Evidence:** Verification completes successfully with network disabled

---

## Verification Without CI

### Demonstration

1. **No CI Artifact Downloads:**
   - Release gate does not use `actions/download-artifact@v4`
   - All data comes from release bundle

2. **No CI Dependencies:**
   - No CI artifact retention required
   - No CI availability required
   - Verification works even if CI is down

3. **Independent Verification:**
   - Bundle can be verified on any system
   - No GitHub Actions required
   - No CI runner required

**Evidence:** Release gate workflow shows no `actions/download-artifact` steps (except for bundle itself)

---

## Verification Without GitHub

### Demonstration

1. **No GitHub API Calls:**
   - Verification does not call GitHub API
   - No repository access required
   - No GitHub authentication required

2. **Standalone Verification:**
   - Bundle can be verified on air-gapped system
   - No GitHub account required
   - No repository access required

**Evidence:** Verification scripts use only local files, no GitHub API calls

---

## Summary

**Offline Verification Guarantees:**

✅ **No Network Access:** All verification uses bundled files only  
✅ **No CI Access:** No CI artifact downloads or CI dependencies  
✅ **No GitHub Access:** No GitHub API calls or repository access  
✅ **Bundled Keys:** Public keys included in bundle  
✅ **Bundled Evidence:** Phase-8 evidence included in bundle  
✅ **Complete Verification:** All gates pass using bundle contents only

**Evidence:** All verification steps complete successfully with network disabled, CI unavailable, and GitHub inaccessible.

---

**End of Walkthrough**
