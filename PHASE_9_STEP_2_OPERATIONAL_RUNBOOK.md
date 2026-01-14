# Phase-9 Step 2: Cryptographic Authority — Operational Runbook

**Document Classification:** Operational Procedure  
**Version:** 1.0  
**Date:** 2024-01-15  
**Status:** Production-Ready

---

## Overview

This runbook provides step-by-step procedures for managing the persistent vendor signing authority. All procedures must be followed exactly to maintain cryptographic integrity.

**Key Principles:**
- No ephemeral keys: All keys must be generated through ceremony
- Persistent storage: Keys stored in encrypted vault
- Lifecycle management: All key operations logged and auditable
- Fail-closed: Revoked keys fail verification automatically

---

## 1. Key Generation Ceremony

### 1.1 Prerequisites

**Required:**
- Air-gapped or secure system
- Key custodian (minimum 1 person)
- Witness (optional but recommended)
- Secure passphrase (minimum 32 characters, stored securely)

**Environment:**
- Python 3.10+
- RansomEye codebase checked out
- `RANSOMEYE_KEY_VAULT_PASSPHRASE` environment variable set (or will be prompted)

### 1.2 Procedure

**Step 1: Prepare Ceremony Environment**

```bash
# Set vault passphrase (or use environment variable)
export RANSOMEYE_KEY_VAULT_PASSPHRASE="<secure-passphrase>"

# Create key directories
mkdir -p keys/vault
mkdir -p keys/ceremony-logs
```

**Step 2: Generate Signing Key**

```bash
python3 scripts/key_generation_ceremony.py \
  --key-id vendor-signing-key-1 \
  --key-type signing \
  --vault-dir keys/vault \
  --registry-path keys/registry.json \
  --log-dir keys/ceremony-logs \
  --participants "Key Custodian Name" \
  --witness "Witness Name" \
  --passphrase "$RANSOMEYE_KEY_VAULT_PASSPHRASE"
```

**Step 3: Verify Key Generation**

```bash
# Check registry
python3 scripts/key_lifecycle_manage.py \
  --registry-path keys/registry.json \
  status --key-id vendor-signing-key-1

# Verify public key exists
ls -lh keys/vault/vendor-signing-key-1.pub
```

**Step 4: Backup Encrypted Vault**

```bash
# Create encrypted backup
tar czf keys-backup-$(date +%Y%m%d).tar.gz \
  keys/vault/ \
  keys/registry.json \
  keys/ceremony-logs/

# Store backup in secure location (offline, geographically separate)
```

**Step 5: Distribute Public Key**

```bash
# Export public key for distribution
python3 << 'EOF'
from pathlib import Path
import sys
sys.path.insert(0, 'supply-chain')
from crypto.persistent_signing_authority import PersistentSigningAuthority
import os

authority = PersistentSigningAuthority(
    vault_dir=Path('keys/vault'),
    registry_path=Path('keys/registry.json')
)

public_key_pem = authority.export_public_key_pem('vendor-signing-key-1')
Path('vendor-signing-key-1.pub').write_bytes(public_key_pem)
print("Public key exported to vendor-signing-key-1.pub")
EOF

# Distribute public key to:
# - CI/CD secrets (RANSOMEYE_KEY_VAULT_DIR, RANSOMEYE_KEY_REGISTRY_PATH)
# - Customer distribution channels
# - Public key registry
```

### 1.3 Evidence

**Required Evidence:**
- Ceremony log file: `keys/ceremony-logs/vendor-signing-key-1-generation-YYYYMMDD-HHMMSS.json`
- Registry entry: `keys/registry.json` contains key entry
- Encrypted vault: `keys/vault/vendor-signing-key-1.encrypted` exists
- Public key: `keys/vault/vendor-signing-key-1.pub` exists
- Backup: Encrypted backup stored in secure location

---

## 2. Key Rotation

### 2.1 Prerequisites

**Trigger Events:**
- Scheduled rotation (every 2 years)
- Key compromise suspected
- Regulatory requirement

**Required:**
- New key generated through ceremony
- Old key still active (for dual-signing period)

### 2.2 Procedure

**Step 1: Generate New Key**

```bash
# Generate new signing key
python3 scripts/key_generation_ceremony.py \
  --key-id vendor-signing-key-2 \
  --key-type signing \
  --vault-dir keys/vault \
  --registry-path keys/registry.json \
  --log-dir keys/ceremony-logs \
  --participants "Key Custodian Name" \
  --passphrase "$RANSOMEYE_KEY_VAULT_PASSPHRASE"
```

**Step 2: Dual-Signing Period (90 days)**

During dual-signing period, both old and new keys sign artifacts:

```bash
# Sign with old key (vendor-signing-key-1)
# Sign with new key (vendor-signing-key-2)
# Both signatures must verify
```

**Step 3: Mark Old Key as Rotated**

After dual-signing period:

```bash
python3 scripts/key_lifecycle_manage.py \
  --registry-path keys/registry.json \
  rotate \
  --old-key-id vendor-signing-key-1 \
  --new-key-id vendor-signing-key-2
```

**Step 4: Update CI/CD Configuration**

Update GitHub Secrets:
- `RANSOMEYE_SIGNING_KEY_ID`: `vendor-signing-key-2`
- Verify vault and registry paths still correct

**Step 5: Re-Sign All Artifacts**

All artifacts signed with old key must be re-signed with new key:

```bash
# Re-sign all artifacts with new key
# Update SBOM with new signatures
# Update Phase-8 evidence bundles
```

### 2.3 Evidence

**Required Evidence:**
- New key generation log
- Rotation log entry in registry
- Dual-signing period documentation
- Re-signed artifacts with new key signatures

---

## 3. Key Revocation

### 3.1 Prerequisites

**Trigger Events:**
- Key compromise confirmed
- Key rotation completed
- Regulatory requirement

### 3.2 Procedure

**Step 1: Immediate Revocation**

```bash
python3 scripts/key_lifecycle_manage.py \
  --registry-path keys/registry.json \
  revoke \
  --key-id vendor-signing-key-1 \
  --reason "Key rotation completed - replaced by vendor-signing-key-2"
```

**Step 2: Verify Revocation**

```bash
# Check revocation list
python3 scripts/key_lifecycle_manage.py \
  --registry-path keys/registry.json \
  list-revoked

# Verify key status
python3 scripts/key_lifecycle_manage.py \
  --registry-path keys/registry.json \
  status --key-id vendor-signing-key-1
```

**Step 3: Notify Stakeholders**

- Update public key registry with revocation
- Notify customers of key revocation
- Update documentation

**Step 4: Re-Sign Artifacts (if required)**

If revocation is due to compromise (not rotation):
- Generate new key
- Re-sign all artifacts
- Distribute new public key

### 3.3 Evidence

**Required Evidence:**
- Revocation log entry in registry
- Revocation list updated
- Stakeholder notification log
- Re-signed artifacts (if compromise)

---

## 4. Key Compromise Recovery

### 4.1 Prerequisites

**Trigger Events:**
- Key compromise detected
- Unauthorized access to vault
- Security incident

### 4.2 Procedure

**Step 1: Immediate Actions**

```bash
# Mark key as compromised (automatically revokes)
python3 scripts/key_lifecycle_manage.py \
  --registry-path keys/registry.json \
  compromise \
  --key-id vendor-signing-key-1
```

**Step 2: Generate New Key**

```bash
# Generate replacement key immediately
python3 scripts/key_generation_ceremony.py \
  --key-id vendor-signing-key-emergency-1 \
  --key-type signing \
  --vault-dir keys/vault \
  --registry-path keys/registry.json \
  --log-dir keys/ceremony-logs \
  --participants "Key Custodian Name" "Security Officer Name" \
  --passphrase "$RANSOMEYE_KEY_VAULT_PASSPHRASE"
```

**Step 3: Incident Investigation**

- Document compromise details
- Identify root cause
- Implement remediation measures
- Update security procedures

**Step 4: Re-Sign All Artifacts**

```bash
# Re-sign all artifacts with new key
# Update SBOM
# Update Phase-8 evidence bundles
```

**Step 5: Notify Stakeholders**

- Immediate notification of compromise
- Distribution of new public key
- Instructions for artifact re-verification

### 4.3 Evidence

**Required Evidence:**
- Compromise detection log
- Incident investigation report
- New key generation log
- Re-signed artifacts
- Stakeholder notification log

---

## 5. Key Escrow / Backup

### 5.1 Prerequisites

**Required:**
- Encrypted vault backup
- Registry backup
- Ceremony logs backup
- Secure storage location (geographically separate)

### 5.2 Procedure

**Step 1: Create Encrypted Backup**

```bash
# Create backup package
tar czf keys-backup-$(date +%Y%m%d).tar.gz \
  keys/vault/ \
  keys/registry.json \
  keys/ceremony-logs/

# Encrypt backup (optional additional encryption)
# gpg --symmetric keys-backup-YYYYMMDD.tar.gz
```

**Step 2: Store Backup**

- Primary backup: Secure on-premises vault
- Secondary backup: Geographically separate location
- Tertiary backup: Offline media in secure location

**Step 3: Verify Backup Integrity**

```bash
# Verify backup can be restored
tar xzf keys-backup-YYYYMMDD.tar.gz
# Verify files exist and are readable
```

**Step 4: Document Backup Location**

- Record backup location in secure documentation
- Update backup schedule (quarterly recommended)
- Test restoration procedure annually

### 5.3 Evidence

**Required Evidence:**
- Backup creation log
- Backup location documentation
- Restoration test results
- Backup schedule documentation

---

## 6. CI/CD Integration

### 6.1 GitHub Secrets Configuration

**Required Secrets:**

1. `RANSOMEYE_KEY_VAULT_PASSPHRASE`
   - Vault decryption passphrase
   - Mark as "Secret" (masked in logs)

2. `RANSOMEYE_KEY_VAULT_DIR`
   - Path to encrypted key vault
   - Default: `keys/vault`

3. `RANSOMEYE_KEY_REGISTRY_PATH`
   - Path to key registry JSON file
   - Default: `keys/registry.json`

4. `RANSOMEYE_SIGNING_KEY_ID`
   - Active signing key identifier
   - Example: `vendor-signing-key-1`

### 6.2 Vault Deployment Options

**Option A: Repository-Based (Not Recommended for Production)**
- Vault stored in repository (encrypted)
- Requires passphrase in secrets
- Suitable for development only

**Option B: External Secret Store (Recommended)**
- Vault stored in external secret store (HashiCorp Vault, AWS Secrets Manager)
- CI retrieves vault at build time
- More secure for production

**Option C: Pre-Mounted Vault (Most Secure)**
- Vault pre-mounted in CI environment
- No network access required during build
- Requires secure CI environment

### 6.3 Verification

**CI Verification Steps:**

1. Vault accessibility check
2. Registry validation
3. Key status verification (active, not revoked)
4. Signing operation test
5. Revocation list check

---

## 7. Offline Verification

### 7.1 Public Key Distribution

**Distribution Channels:**
- Release bundles (included in `keys/` directory)
- Public key registry (vendor website)
- Customer distribution channels

### 7.2 Verification Procedure

**Step 1: Obtain Public Key**

```bash
# From release bundle
cp release-bundle/keys/vendor-signing-key-1.pub .

# Or download from public registry
curl -O https://vendor.example.com/keys/vendor-signing-key-1.pub
```

**Step 2: Verify Artifact**

```bash
python3 supply-chain/cli/verify_artifacts.py \
  --artifact artifact.tar.gz \
  --manifest artifact.tar.gz.manifest.json \
  --public-key vendor-signing-key-1.pub
```

**Step 3: Check Revocation (Optional)**

```bash
# Download revocation list
curl -O https://vendor.example.com/keys/revocation-list.json

# Check if key is revoked
python3 scripts/key_lifecycle_manage.py \
  --registry-path revocation-list.json \
  list-revoked
```

### 7.3 Evidence

**Required Evidence:**
- Public key availability verification
- Offline verification test results
- Revocation list availability

---

## 8. Troubleshooting

### 8.1 Common Issues

**Issue: "Key not found in registry"**

**Solution:**
- Verify key was generated through ceremony
- Check registry path is correct
- Verify key ID matches registry entry

**Issue: "Key is not active"**

**Solution:**
- Check key status: `key_lifecycle_manage.py status --key-id <key-id>`
- If revoked/rotated, use new key
- If compromised, follow compromise recovery procedure

**Issue: "Failed to decrypt private key"**

**Solution:**
- Verify `RANSOMEYE_KEY_VAULT_PASSPHRASE` is correct
- Check vault files exist and are readable
- Verify salt file exists

**Issue: "Ephemeral key generation attempted"**

**Solution:**
- This error indicates code is trying to generate keys in CI
- Verify all signing code uses `PersistentSigningAuthority`
- Check `VendorKeyManager.get_or_create_keypair()` is not called

### 8.2 Emergency Procedures

**Emergency: Vault Lost**

1. Restore from backup
2. Verify key integrity
3. Test signing operations
4. Document incident

**Emergency: Passphrase Lost**

1. Restore from backup (if available)
2. If backup unavailable, keys are unrecoverable
3. Generate new keys through ceremony
4. Re-sign all artifacts

---

## 9. Compliance & Auditing

### 9.1 Audit Requirements

**Required Audit Logs:**
- Key generation ceremonies
- Key rotations
- Key revocations
- Key compromise incidents
- Backup creation/restoration

**Audit Trail:**
- All operations logged in registry
- Ceremony logs stored permanently
- Incident reports documented

### 9.2 Compliance Verification

**Quarterly Review:**
- Review key status
- Verify backup integrity
- Test restoration procedures
- Update documentation

**Annual Review:**
- Complete key lifecycle audit
- Review security procedures
- Update operational runbook
- Compliance certification

---

## 10. Evidence Checklist

### Key Generation
- [ ] Ceremony log created
- [ ] Key registered in registry
- [ ] Encrypted vault created
- [ ] Public key exported
- [ ] Backup created
- [ ] Public key distributed

### Key Rotation
- [ ] New key generated
- [ ] Dual-signing period documented
- [ ] Old key marked as rotated
- [ ] CI/CD updated
- [ ] Artifacts re-signed

### Key Revocation
- [ ] Key revoked in registry
- [ ] Revocation list updated
- [ ] Stakeholders notified
- [ ] Public registry updated

### Key Compromise
- [ ] Key marked as compromised
- [ ] New key generated
- [ ] Incident investigated
- [ ] Artifacts re-signed
- [ ] Stakeholders notified

### Backup
- [ ] Backup created
- [ ] Backup stored securely
- [ ] Backup integrity verified
- [ ] Restoration tested
- [ ] Backup location documented

---

**End of Operational Runbook**
