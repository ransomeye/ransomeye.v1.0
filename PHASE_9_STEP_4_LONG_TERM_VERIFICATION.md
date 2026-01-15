# Phase-9 Step 4: Long-Term Verification Procedure

**Document Classification:** Operational Procedure  
**Version:** 1.0  
**Date:** 2024-01-15  
**Retention Period:** 7+ years (SOX compliance)

---

## Overview

This procedure enables verification of release bundles **years after creation**, meeting regulatory requirements for long-term auditability (SOX 7-year retention, ISO 27001, etc.).

---

## Long-Term Storage Requirements

### Storage Media

**Recommended:**
- **WORM Storage:** Write-Once-Read-Many (AWS S3 Glacier, Azure Blob Archive, on-premises WORM)
- **Versioned Storage:** Object versioning enabled (AWS S3 versioning, Azure Blob versioning)
- **Geographic Distribution:** Multiple geographically separate copies
- **Encryption:** At-rest encryption (AES-256)

**Storage Locations:**
1. **Primary:** Production storage (S3/Blob with versioning)
2. **Secondary:** Geographically separate backup
3. **Tertiary:** Offline media (encrypted USB drives, tapes) in secure vault

### Storage Structure

```
release-archive/
├── ransomeye-v1.0.0/
│   ├── ransomeye-v1.0.0-release-bundle.tar.gz
│   ├── ransomeye-v1.0.0-release-bundle.tar.gz.sha256
│   └── metadata/
│       ├── release-notes.md
│       ├── build-info.json
│       └── build-environment.json
├── ransomeye-v1.0.1/
│   └── ...
└── public-keys/
    ├── vendor-signing-key-1.pub
    ├── vendor-signing-key-2.pub
    └── revocation-list.json
```

---

## 5+ Year Verification Procedure

### Scenario: Verifying a 5-Year-Old Release Bundle

**Date:** 2029-01-15  
**Bundle:** `ransomeye-v1.0.0-release-bundle.tar.gz` (created 2024-01-15)  
**Context:** Regulatory audit requiring verification of historical release

---

### Step 1: Retrieve Bundle from Long-Term Storage

```bash
# Retrieve bundle from archive storage
# (Example: AWS S3 Glacier retrieval, or restore from backup)

# Verify bundle integrity after retrieval
sha256sum ransomeye-v1.0.0-release-bundle.tar.gz > retrieved-bundle.sha256

# Compare with stored checksum
if ! diff ransomeye-v1.0.0-release-bundle.tar.gz.sha256 retrieved-bundle.sha256; then
    echo "❌ FAIL: Bundle integrity compromised during storage"
    exit 1
fi
echo "✅ Bundle integrity verified after 5-year storage"
```

**Evidence:** Bundle retrieved, checksum matches stored value

---

### Step 2: Extract Bundle

```bash
# Extract bundle (same as current procedure)
mkdir -p verification-2029
tar xzf ransomeye-v1.0.0-release-bundle.tar.gz -C verification-2029

BUNDLE_DIR="verification-2029/ransomeye-v1.0.0-release-bundle"
```

**Evidence:** Bundle extracted successfully

---

### Step 3: Verify RELEASE_MANIFEST.json

```bash
# Verify manifest exists and is valid
python3 << 'EOF'
import json
from pathlib import Path

bundle_dir = Path('$BUNDLE_DIR')
manifest_path = bundle_dir / 'RELEASE_MANIFEST.json'

with open(manifest_path) as f:
    manifest = json.load(f)

print(f"Release version: {manifest['release_version']}")
print(f"Created: {manifest['created_at']}")
print(f"Age: 5 years (created 2024-01-15)")
print(f"Artifacts: {len(manifest['artifacts'])}")
print(f"GA verdict: {manifest['evidence']['ga_verdict']}")
EOF
```

**Evidence:** Manifest valid, contains all required information

---

### Step 4: Verify Public Keys (Check Revocation)

```bash
# Retrieve public key registry from long-term storage
# (Public keys and revocation lists stored separately for long-term access)

# Check if signing key is still valid (not revoked)
python3 << 'EOF'
import json
import sys
from pathlib import Path

bundle_dir = Path('$BUNDLE_DIR')
manifest_path = bundle_dir / 'RELEASE_MANIFEST.json'

# Load manifest
with open(manifest_path) as f:
    manifest = json.load(f)

key_id = manifest['public_keys'][0]['key_id']
print(f"Signing key ID: {key_id}")

# Load revocation list from long-term storage
revocation_list_path = Path('public-keys/revocation-list.json')
if revocation_list_path.exists():
    with open(revocation_list_path) as f:
        revocation_list = json.load(f)
    
    # Check if key is revoked
    is_revoked = any(entry['key_id'] == key_id for entry in revocation_list.get('revoked_keys', []))
    
    if is_revoked:
        print(f"⚠️  WARNING: Signing key {key_id} was revoked after bundle creation")
        print("   Bundle signatures are still valid for historical verification")
        print("   But key should not be used for new signatures")
    else:
        print(f"✅ Signing key {key_id} is not in revocation list")
else:
    print("⚠️  WARNING: Revocation list not available")
    print("   Proceeding with signature verification (key may have been revoked)")
EOF
```

**Evidence:** Key revocation status checked (if registry available)

---

### Step 5: Verify Signatures (Using Bundled Public Key)

```bash
# Use public key from bundle (no external key retrieval needed)
PUBLIC_KEY_PATH="$BUNDLE_DIR/keys/vendor-signing-key-1.pub"

# Verify SBOM signature
python3 release/verify_sbom.py \
  --release-root "$BUNDLE_DIR/artifacts" \
  --manifest "$BUNDLE_DIR/sbom/manifest.json" \
  --signature "$BUNDLE_DIR/sbom/manifest.json.sig" \
  --public-key "$PUBLIC_KEY_PATH"

# Verify artifact signatures
cd "$BUNDLE_DIR/signatures"
for manifest in *.manifest.json; do
    ARTIFACT_NAME="${manifest%.manifest.json}"
    ARTIFACT_FILE="../artifacts/${ARTIFACT_NAME}"
    
    python3 ../../../../supply-chain/cli/verify_artifacts.py \
      --artifact "$ARTIFACT_FILE" \
      --manifest "$manifest" \
      --public-key "$PUBLIC_KEY_PATH"
done
```

**Evidence:** All signatures verified using bundled public key (no external key retrieval)

---

### Step 6: Verify Phase-8 Evidence Bundle

```bash
# Verify evidence bundle signature
EVIDENCE_BUNDLE="$BUNDLE_DIR/evidence/evidence_bundle.json"
EVIDENCE_SIG="$BUNDLE_DIR/evidence/evidence_bundle.json.sig"

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

# Verify GA verdict
ga_verdict = evidence_bundle.get('overall_status', 'UNKNOWN')
if ga_verdict != 'PASS':
    print(f"❌ FAIL: GA verdict is {ga_verdict} (must be PASS)")
    sys.exit(1)
print(f"✅ GA verdict: {ga_verdict}")

# Load signature
signature = evidence_sig_path.read_text(encoding='utf-8').strip()
evidence_bundle['signature'] = signature

# Verify signature
sys.path.insert(0, 'supply-chain')
from crypto.artifact_verifier import ArtifactVerifier

verifier = ArtifactVerifier(public_key_path=public_key_path)
if verifier.verify_manifest_signature(evidence_bundle):
    print("✅ Evidence bundle signature verified (5-year-old bundle)")
else:
    print("❌ FAIL: Evidence bundle signature verification failed")
    sys.exit(1)
EOF
```

**Evidence:** Evidence bundle verified, GA verdict confirmed, signature valid

---

### Step 7: Verify Artifact Hashes Match Manifest

```bash
# Verify all artifacts match manifest hashes
python3 << 'EOF'
import json
import hashlib
from pathlib import Path

bundle_dir = Path('$BUNDLE_DIR')
manifest_path = bundle_dir / 'RELEASE_MANIFEST.json'

with open(manifest_path) as f:
    manifest = json.load(f)

all_match = True
for artifact in manifest['artifacts']:
    artifact_path = bundle_dir / artifact['path']
    
    if not artifact_path.exists():
        print(f"❌ FAIL: Artifact not found: {artifact['path']}")
        all_match = False
        continue
    
    # Compute hash
    hash_obj = hashlib.sha256()
    with open(artifact_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_obj.update(chunk)
    actual_hash = hash_obj.hexdigest()
    
    if actual_hash != artifact['sha256']:
        print(f"❌ FAIL: Hash mismatch for {artifact['name']}")
        all_match = False
    else:
        print(f"✅ {artifact['name']}: hash verified (5-year-old artifact)")

if not all_match:
    sys.exit(1)
print("✅ All artifacts match manifest (5-year verification)")
EOF
```

**Evidence:** All artifact hashes match manifest (no corruption after 5 years)

---

### Step 8: Complete Verification

```bash
# Run complete verification
python3 scripts/verify_release_bundle.py \
  --bundle ransomeye-v1.0.0-release-bundle.tar.gz \
  --checksum ransomeye-v1.0.0-release-bundle.tar.gz.sha256 \
  --extract-dir verification-2029

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ 5-YEAR VERIFICATION PASSED"
    echo "=========================================="
    echo ""
    echo "Bundle verified successfully after 5 years in storage."
    echo "All signatures valid, all hashes match, GA verdict confirmed."
    echo ""
    echo "This demonstrates long-term verifiability for regulatory compliance."
else
    echo ""
    echo "=========================================="
    echo "❌ 5-YEAR VERIFICATION FAILED"
    echo "=========================================="
    exit 1
fi
```

**Evidence:** Complete verification passed after 5-year storage

---

## Storage Guidance

### WORM Storage Configuration

**AWS S3:**
```bash
# Create S3 bucket with versioning and WORM
aws s3api create-bucket --bucket ransomeye-release-archive
aws s3api put-bucket-versioning \
  --bucket ransomeye-release-archive \
  --versioning-configuration Status=Enabled
aws s3api put-object-lock-configuration \
  --bucket ransomeye-release-archive \
  --object-lock-configuration '{
    "ObjectLockEnabled": "Enabled",
    "Rule": {
      "DefaultRetention": {
        "Mode": "COMPLIANCE",
        "Days": 2555
      }
    }
  }'
```

**Azure Blob:**
```bash
# Create storage account with versioning and immutability
az storage account create \
  --name ransomeyereleasearchive \
  --resource-group ransomeye-rg \
  --enable-hierarchical-namespace true \
  --enable-versioning true

# Enable immutability policy
az storage container immutability-policy create \
  --account-name ransomeyereleasearchive \
  --container-name releases \
  --period 2555 \
  --allow-protected-append-writes true
```

### Backup Strategy

1. **Primary Storage:** Cloud WORM storage (S3/Blob)
2. **Secondary Backup:** Geographically separate cloud storage
3. **Tertiary Backup:** Encrypted offline media in secure vault

**Backup Schedule:**
- **Primary:** Real-time (immediate upload after bundle creation)
- **Secondary:** Daily backup
- **Tertiary:** Quarterly backup to offline media

---

## Verification Tools Availability

### Long-Term Tool Compatibility

**Verification scripts are designed for long-term compatibility:**

1. **Minimal Dependencies:** Only standard Python libraries and cryptography
2. **No External APIs:** No network calls, no external services
3. **Self-Contained:** All verification logic in bundle or scripts
4. **Documentation:** Complete procedures documented for future use

**Tool Preservation:**
- Verification scripts stored with bundles
- Tool versions documented in bundle metadata
- Alternative verification methods documented

---

## Regulatory Compliance

### SOX Compliance (7-Year Retention)

**Requirement:** Financial records must be retained for 7 years

**Compliance:**
- ✅ Release bundles stored for 7+ years
- ✅ Verification possible after 7 years
- ✅ Complete audit trail preserved
- ✅ Immutable storage (WORM)

### ISO 27001 Compliance

**Requirement:** Information security management

**Compliance:**
- ✅ Cryptographic verification
- ✅ Immutable audit trail
- ✅ Secure storage
- ✅ Access controls

### NIST Compliance

**Requirement:** Software supply chain security

**Compliance:**
- ✅ SBOM included and verified
- ✅ Artifact signatures verified
- ✅ Evidence bundle preserved
- ✅ Long-term verifiability

---

## Evidence

**Long-Term Verification Evidence:**

1. **Bundle Integrity:** Checksum verification after 5-year storage
2. **Signature Validity:** All signatures verify using bundled keys
3. **Hash Consistency:** All artifact hashes match manifest
4. **Evidence Validity:** Phase-8 evidence bundle verified
5. **GA Verdict:** Historical GA verdict confirmed

**Storage Evidence:**

1. **WORM Configuration:** Storage configured with immutability
2. **Versioning:** Object versioning enabled
3. **Backup Strategy:** Multiple geographically distributed backups
4. **Retention Policy:** 7+ year retention documented

---

**End of Long-Term Verification Procedure**
