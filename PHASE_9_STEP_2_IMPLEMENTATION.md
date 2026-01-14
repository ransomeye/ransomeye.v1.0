# Phase-9 Step 2: Cryptographic Authority & Signing — Implementation Summary

**Implementation Date:** 2024-01-15  
**Status:** Complete  
**Scope:** Persistent vendor signing authority replacing ephemeral CI keys

---

## Changes Made

### 1. Key Registry & Persistent Signing Authority

#### 1.1 Key Registry (`supply-chain/crypto/key_registry.py`)

**Functionality:**
- Persistent key registry with lifecycle management
- Key status tracking (active, revoked, rotated, compromised)
- Revocation list (CRL) management
- Key metadata storage (fingerprints, generation dates, parent keys)

**Key Features:**
- Three-tier hierarchy support (Root → Signing → No Ephemeral)
- Status enumeration (ACTIVE, REVOKED, ROTATED, COMPROMISED)
- Audit trail for all key operations

#### 1.2 Persistent Signing Authority (`supply-chain/crypto/persistent_signing_authority.py`)

**Functionality:**
- Encrypted key vault (Option B: Software Vault)
- Private keys encrypted with ChaCha20Poly1305
- Passphrase-derived encryption keys (PBKDF2)
- Key retrieval with revocation checking
- Public key export for distribution

**Key Features:**
- No ephemeral key generation (raises `EphemeralKeyError` if attempted)
- Automatic revocation checking
- Status verification before signing
- Encrypted storage at rest

### 2. VendorKeyManager Update

**File:** `supply-chain/crypto/vendor_key_manager.py`

**Changes:**
- `get_or_create_keypair()` now raises error if key not found
- Ephemeral key generation explicitly forbidden
- Error message directs to key generation ceremony

**Evidence:**
- Method raises `VendorKeyManagerError` with message: "Ephemeral key generation is forbidden"

### 3. Signing CLI Updates

#### 3.1 Sign Artifacts CLI (`supply-chain/cli/sign_artifacts.py`)

**Changes:**
- Replaced `VendorKeyManager` with `PersistentSigningAuthority`
- Updated arguments: `--key-dir` → `--vault-dir` and `--registry-path`
- Uses persistent vault for key retrieval

**Evidence:**
- Imports `PersistentSigningAuthority` instead of `VendorKeyManager`
- Calls `authority.get_signing_key()` instead of `key_manager.get_or_create_keypair()`

#### 3.2 Verify Artifacts CLI (`supply-chain/cli/verify_artifacts.py`)

**Changes:**
- Added revocation checking (`--check-revocation` flag)
- Updated to use `PersistentSigningAuthority` for public key retrieval
- Verifies key is not revoked before verification

**Evidence:**
- Imports `KeyRegistry` and `PersistentSigningAuthority`
- Checks revocation list if `--check-revocation` flag set
- Fails verification if key is revoked

### 4. CI Workflow Updates

**File:** `.github/workflows/ci-build-and-sign.yml`

**Changes:**
- **REMOVED:** Ephemeral key generation step (`Generate signing keypair (CI)`)
- **ADDED:** Persistent key loading step (`Load persistent signing keys`)
- **UPDATED:** All signing steps to use `--vault-dir` and `--registry-path`
- **ADDED:** Revocation checking in verification steps
- **ADDED:** Public key export step

**Key Sections:**

**Removed:**
```yaml
- name: Generate signing keypair (CI)
  run: |
    mkdir -p /tmp/ci-signing-keys
    # Ephemeral key generation (FORBIDDEN)
```

**Added:**
```yaml
- name: Load persistent signing keys
  env:
    RANSOMEYE_KEY_VAULT_PASSPHRASE: ${{ secrets.RANSOMEYE_KEY_VAULT_PASSPHRASE }}
  run: |
    # Verify persistent keys are available
    # Fail if keys not found (no ephemeral generation)
```

**Updated:**
```yaml
- name: Sign all artifacts
  env:
    RANSOMEYE_KEY_VAULT_PASSPHRASE: ${{ secrets.RANSOMEYE_KEY_VAULT_PASSPHRASE }}
    RANSOMEYE_KEY_VAULT_DIR: ${{ secrets.RANSOMEYE_KEY_VAULT_DIR || 'keys/vault' }}
    RANSOMEYE_KEY_REGISTRY_PATH: ${{ secrets.RANSOMEYE_KEY_REGISTRY_PATH || 'keys/registry.json' }}
  run: |
    # Use persistent signing authority
    python3 supply-chain/cli/sign_artifacts.py \
      --vault-dir "$RANSOMEYE_KEY_VAULT_DIR" \
      --registry-path "$RANSOMEYE_KEY_REGISTRY_PATH" \
      ...
```

### 5. SBOM Generator Update

**File:** `release/generate_sbom.py`

**Changes:**
- Replaced `VendorKeyManager` with `PersistentSigningAuthority`
- Updated arguments: `--key-dir` → `--vault-dir` and `--registry-path`
- Uses persistent vault for SBOM signing

**Evidence:**
- Imports `PersistentSigningAuthority`
- Calls `authority.get_signing_key()` for SBOM signing

### 6. Phase-8 Evidence Bundle Update

**File:** `validation/evidence_bundle/freeze_evidence_bundle.py`

**Changes:**
- Updated `sign_bundle()` function to use `PersistentSigningAuthority`
- Removed `VendorKeyManager` import
- Uses persistent vault for evidence bundle signing

**Evidence:**
- Imports `PersistentSigningAuthority`
- Calls `authority.get_signing_key()` for evidence bundle signing
- Error message indicates persistent keys required

### 7. Key Lifecycle Management Scripts

#### 7.1 Key Generation Ceremony (`scripts/key_generation_ceremony.py`)

**Functionality:**
- Generates ed25519 keypairs
- Stores keys in encrypted vault
- Registers keys in registry
- Logs ceremony with participants and witness
- Exports public key for distribution

**Evidence:**
- Script executable and functional
- Creates ceremony logs
- Registers keys in registry

#### 7.2 Key Lifecycle Management (`scripts/key_lifecycle_manage.py`)

**Functionality:**
- Key revocation (`revoke` command)
- Key rotation (`rotate` command)
- Key compromise marking (`compromise` command)
- Key status display (`status` command)
- Revocation list display (`list-revoked` command)

**Evidence:**
- Script executable and functional
- All commands tested and working

### 8. Operational Runbook

**File:** `PHASE_9_STEP_2_OPERATIONAL_RUNBOOK.md`

**Content:**
- Key generation ceremony procedures
- Key rotation procedures
- Key revocation procedures
- Key compromise recovery procedures
- Key escrow/backup procedures
- CI/CD integration guide
- Offline verification procedures
- Troubleshooting guide
- Compliance & auditing requirements

**Evidence:**
- Complete operational procedures documented
- Step-by-step instructions with commands
- Evidence checklists for each procedure

---

## Key Hierarchy Implementation

### Three-Tier Hierarchy

1. **Root Key (Offline, Air-Gapped)**
   - **Status:** Designed, not yet implemented (future work)
   - **Purpose:** Attest signing keys (not used for artifact signing)
   - **Storage:** Offline, air-gapped system

2. **Vendor Signing Key (Persistent)**
   - **Status:** ✅ Implemented
   - **Purpose:** Signs artifacts, SBOM, Phase-8 evidence
   - **Storage:** Encrypted vault (Option B: Software Vault)
   - **Lifecycle:** Full lifecycle management implemented

3. **Ephemeral Keys**
   - **Status:** ✅ Explicitly Forbidden
   - **Enforcement:** Code raises errors if ephemeral generation attempted
   - **Evidence:** `VendorKeyManager.get_or_create_keypair()` raises error

---

## Key Storage Model: Option B (Encrypted Software Vault)

### Implementation Details

**Encryption:**
- Algorithm: ChaCha20Poly1305 (AEAD)
- Key Derivation: PBKDF2-HMAC-SHA256 (100,000 iterations)
- Salt: 16 bytes (random, stored separately)

**Storage:**
- Private keys: `{key_id}.encrypted` (encrypted)
- Salt: `{key_id}.salt` (unencrypted, required for decryption)
- Public keys: `{key_id}.pub` (unencrypted, safe to distribute)

**Access Control:**
- Passphrase required: `RANSOMEYE_KEY_VAULT_PASSPHRASE`
- Manual unlock ceremony documented
- No automatic key generation in CI

### Alternative: HSM Integration (Future)

**Note:** HSM integration (Option A) can be added by:
1. Implementing HSM client library integration
2. Updating `PersistentSigningAuthority` to support HSM backend
3. Configuring HSM endpoint and credentials
4. No changes to signing API required (abstraction layer)

---

## Revocation & Lifecycle Management

### Revocation List (CRL)

**Implementation:**
- Stored in key registry JSON file
- Contains: key_id, revocation_date, reason, public_key_fingerprint
- Checked automatically during verification if `--check-revocation` flag set

**Enforcement:**
- Revoked keys fail verification
- Revoked keys cannot be used for signing
- Revocation list exported for public distribution

### Key Status Tracking

**Statuses:**
- `ACTIVE`: Key can be used for signing
- `REVOKED`: Key is revoked, signatures invalid
- `ROTATED`: Key replaced by newer key
- `COMPROMISED`: Key compromised, automatically revoked

**Enforcement:**
- Only `ACTIVE` keys can be used for signing
- Status checked before every signing operation
- Status changes logged in registry

---

## Phase-8 Evidence Binding

### Real Artifact Protection

**Implementation:**
- Phase-8 evidence bundles reference real artifact hashes (from Step 1 builds)
- Evidence bundles signed with persistent signing keys
- Public keys available for offline verification

**Evidence:**
- `freeze_evidence_bundle.py` uses `PersistentSigningAuthority`
- Evidence bundles contain real artifact SHA256 hashes
- Signatures verify against persistent public keys

### Offline Verification

**Implementation:**
- Public keys exported from vault
- Public keys included in release bundles
- Verification scripts accept public key as parameter
- No CI dependency for verification

**Evidence:**
- `verify_artifacts.py` accepts `--public-key` parameter
- Public keys exported in CI workflow
- Verification works offline (no network required)

---

## Evidence Mapping Table

| Requirement | Implementation | Evidence Location |
|------------|---------------|-------------------|
| **No ephemeral keys** | `VendorKeyManager.get_or_create_keypair()` raises error | `supply-chain/crypto/vendor_key_manager.py:41-59` |
| **Persistent key storage** | Encrypted vault with passphrase | `supply-chain/crypto/persistent_signing_authority.py` |
| **Key registry** | JSON registry with lifecycle tracking | `supply-chain/crypto/key_registry.py` |
| **Revocation support** | Revocation list in registry, checked during verification | `supply-chain/crypto/key_registry.py:get_revocation_list()`, `supply-chain/cli/verify_artifacts.py:--check-revocation` |
| **Key generation ceremony** | Script with logging and witness | `scripts/key_generation_ceremony.py` |
| **Key rotation** | Rotation command with dual-signing support | `scripts/key_lifecycle_manage.py:rotate` |
| **Key revocation** | Revocation command with CRL update | `scripts/key_lifecycle_manage.py:revoke` |
| **Compromise recovery** | Compromise command with automatic revocation | `scripts/key_lifecycle_manage.py:compromise` |
| **CI uses persistent keys** | CI workflow loads keys from vault, no generation | `.github/workflows/ci-build-and-sign.yml:Load persistent signing keys` |
| **Phase-8 uses persistent keys** | Evidence bundle signing uses persistent authority | `validation/evidence_bundle/freeze_evidence_bundle.py:sign_bundle()` |
| **Offline verification** | Public keys exported, verification accepts public key | `supply-chain/cli/verify_artifacts.py:--public-key`, CI workflow exports public key |
| **Operational procedures** | Complete runbook with step-by-step procedures | `PHASE_9_STEP_2_OPERATIONAL_RUNBOOK.md` |

---

## Files Created

1. `supply-chain/crypto/key_registry.py` - Key registry with lifecycle management
2. `supply-chain/crypto/persistent_signing_authority.py` - Persistent signing authority
3. `scripts/key_generation_ceremony.py` - Key generation ceremony script
4. `scripts/key_lifecycle_manage.py` - Key lifecycle management script
5. `PHASE_9_STEP_2_OPERATIONAL_RUNBOOK.md` - Operational runbook

## Files Modified

1. `supply-chain/crypto/vendor_key_manager.py` - Forbid ephemeral key generation
2. `supply-chain/cli/sign_artifacts.py` - Use persistent signing authority
3. `supply-chain/cli/verify_artifacts.py` - Add revocation checking
4. `release/generate_sbom.py` - Use persistent signing authority
5. `validation/evidence_bundle/freeze_evidence_bundle.py` - Use persistent signing authority
6. `.github/workflows/ci-build-and-sign.yml` - Remove ephemeral key generation, use persistent keys

---

## Verification Commands

### Verify No Ephemeral Key Generation

```bash
# Attempt ephemeral key generation (should fail)
python3 << 'EOF'
from supply_chain.crypto.vendor_key_manager import VendorKeyManager
from pathlib import Path

key_manager = VendorKeyManager(Path('/tmp/test'))
try:
    key_manager.get_or_create_keypair('test-key')
    print("❌ ERROR: Ephemeral key generation succeeded (should fail)")
except Exception as e:
    print(f"✅ Ephemeral key generation correctly forbidden: {e}")
EOF
```

### Verify Persistent Key Storage

```bash
# Generate key through ceremony
python3 scripts/key_generation_ceremony.py \
  --key-id test-key-1 \
  --participants "Test User" \
  --passphrase "test-passphrase"

# Verify key in registry
python3 scripts/key_lifecycle_manage.py \
  --registry-path keys/registry.json \
  status --key-id test-key-1
```

### Verify Revocation

```bash
# Revoke key
python3 scripts/key_lifecycle_manage.py \
  --registry-path keys/registry.json \
  revoke --key-id test-key-1 --reason "Test revocation"

# Verify revocation list
python3 scripts/key_lifecycle_manage.py \
  --registry-path keys/registry.json \
  list-revoked
```

---

## Next Steps (Not Implemented)

The following are **NOT** implemented in this step (per scope constraints):

- ❌ Credential remediation (Phase-9 Step 3)
- ❌ Release gate independence (Phase-9 Step 4)
- ❌ Root key implementation (future enhancement)
- ❌ HSM integration (Option A, can be added later)

These will be addressed in subsequent implementation steps.

---

**Implementation Status:** ✅ Complete  
**Ready for:** Operational deployment and testing
