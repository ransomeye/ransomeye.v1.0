# RansomEye Release Signing Public Keys

This directory contains **PUBLIC KEYS ONLY** for release signature verification.

## Security Model

**✅ SAFE TO COMMIT:** Public keys are non-sensitive and required for verification.  
**❌ NEVER COMMIT:** Private keys (stored in encrypted vault, offline only).

## Current Keys

### `ransomeye-release-signing-v1.pub`
- **Type:** ed25519 public key
- **Purpose:** Verify signatures on release artifacts
- **Fingerprint:** `4ba9f27a9d8d61ef2ad07ee9dbc5d29335a73bd5fcf334cb08b30058fb34f2e1`
- **Status:** Active
- **Generated:** 2026-01-18T07:30:26+00:00
- **Ceremony Log:** `keys/ceremony-logs/ransomeye-release-signing-v1-generation-20260118-073026.json`

## Usage

### CI Verification
```bash
python3 scripts/verify_release_bundle.py \
  --bundle ransomeye-v1.0.0-release-bundle.tar.gz \
  --registry-path keys/registry.json
```

### Manual Verification
```bash
# Public key is embedded in release bundle for offline verification
# No external key fetching required
```

## Key Rotation

When rotating keys:
1. Generate new key with `scripts/key_generation_ceremony.py`
2. Export public key to this directory
3. Update `keys/registry.json` to mark old key as rotated
4. Commit new public key and updated registry
5. Old public keys remain in this directory for historical verification

## Revocation

If a key is compromised:
1. Update `keys/registry.json` to mark key as revoked
2. **DO NOT DELETE** the public key from this directory (needed for historical verification)
3. Generate and deploy new signing key immediately
4. Re-sign all active releases with new key

## Verification

Verify public key fingerprint:
```bash
python3 -c "
from cryptography.hazmat.primitives import serialization
import hashlib

with open('release/.keys/ransomeye-release-signing-v1.pub', 'rb') as f:
    pub_key = f.read()
    fingerprint = hashlib.sha256(pub_key).hexdigest()
    print(f'Fingerprint: {fingerprint}')
"
```

Expected: `4ba9f27a9d8d61ef2ad07ee9dbc5d29335a73bd5fcf334cb08b30058fb34f2e1`
