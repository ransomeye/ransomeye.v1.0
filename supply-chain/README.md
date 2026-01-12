# RansomEye Supply-Chain Signing & Verification Framework

**AUTHORITATIVE:** Cryptographic supply-chain integrity for installers and artifacts

## Purpose Statement

The Supply-Chain Signing & Verification Framework provides **cryptographic supply-chain integrity** for RansomEye installers and artifacts. This framework ensures that artifacts have not been tampered with between build and deployment.

**This is integrity proof, not trust assertion. Customers may replace trust roots.**

> **"RansomEye self-signs for integrity, not authority. Final trust always belongs to the operator."**

## Why Self-Signing Exists

RansomEye self-signs artifacts to:

- **Prove integrity**: Cryptographic proof that artifacts have not been modified
- **Enable verification**: Allow customers to verify artifact integrity offline
- **Support air-gapped environments**: No internet or external dependencies required
- **Provide chain-of-custody**: Full traceability from build to deployment

**Self-signing does NOT assert trust or authority.** Customers may replace trust roots with their own keys.

## Difference Between Integrity vs Trust

- **Integrity**: Cryptographic proof that artifact has not been modified (what this framework provides)
- **Trust**: Belief that artifact comes from trusted source (customer decision)

This framework provides **integrity**, not **trust**. Customers must make their own trust decisions.

## How Customers Replace Trust Roots

Customers can replace RansomEye's vendor signing keys with their own keys:

1. **Generate customer keypair**: Use ed25519 key generation
2. **Re-sign artifacts**: Use customer private key to sign artifacts
3. **Deploy customer public key**: Deploy customer public key to verification systems
4. **Verify with customer key**: Use customer public key for verification

**Example:**
```bash
# Generate customer keypair
openssl genpkey -algorithm Ed25519 -out customer_private_key.pem
openssl pkey -in customer_private_key.pem -pubout -out customer_public_key.pem

# Re-sign artifact with customer key
python3 supply-chain/cli/sign_artifacts.py \
    --artifact ransomeye-installer.bin \
    --artifact-name ransomeye-core-installer \
    --artifact-type CORE_INSTALLER \
    --version 1.0.0 \
    --signing-key-id customer-key-1 \
    --key-dir /path/to/customer/keys \
    --output-dir /path/to/output

# Verify with customer key
python3 supply-chain/cli/verify_artifacts.py \
    --artifact ransomeye-installer.bin \
    --manifest ransomeye-installer.bin.manifest.json \
    --public-key customer_public_key.pem
```

## Air-Gapped Verification

Verification can be performed **completely offline**:

- **No internet calls**: All verification is local
- **No external dependencies**: Only requires artifact, manifest, and public key
- **Deterministic**: Same inputs always produce same results
- **Reproducible**: Verification can be repeated indefinitely

**Example:**
```bash
# Copy artifact, manifest, and public key to air-gapped system
# Verify offline
python3 supply-chain/cli/verify_artifacts.py \
    --artifact ransomeye-installer.bin \
    --manifest ransomeye-installer.bin.manifest.json \
    --public-key vendor_public_key.pem
```

## Legal / Regulatory Positioning

### Court Admissibility

- **Cryptographic proof**: SHA256 hash provides integrity proof
- **Signature verification**: ed25519 signature provides authenticity proof
- **Chain-of-custody**: Full manifest provides build-to-deployment traceability
- **Reproducible**: Verification can be repeated by third parties

### Regulatory Compliance

- **SOX / SOC2**: Supply-chain integrity is auditable
- **ISO 27001**: Cryptographic controls for artifact integrity
- **NIST**: Supply-chain risk management (SP 800-161)
- **FIPS 140-2**: Cryptographic module compliance (ed25519)

## Architecture

### Signing Flow (Deterministic)

1. **Hash artifact** (SHA256)
2. **Build canonical manifest** (sorted JSON)
3. **Hash manifest**
4. **Sign manifest hash** (ed25519)
5. **Store outputs**:
   - `<artifact>.sha256`
   - `<artifact>.manifest.json`
   - `<artifact>.manifest.sig`

All steps are **reproducible** and **deterministic**.

### Verification Flow

1. **Load manifest**
2. **Verify artifact SHA256** (compare computed hash with manifest hash)
3. **Verify manifest hash** (recompute canonical manifest hash)
4. **Verify signature** (verify ed25519 signature against manifest hash)

**No silent failures.** All failures are explicit with detailed reasons.

## Schema

### Artifact Manifest

All fields are **mandatory** (zero optional fields):

- `artifact_id` (UUID): Unique identifier
- `artifact_name` (string): Artifact name
- `artifact_type` (enum): Artifact type (CORE_INSTALLER, LINUX_AGENT, WINDOWS_AGENT, DPI_PROBE, RELEASE_BUNDLE)
- `version` (string): Artifact version (semver)
- `build_timestamp` (RFC3339 UTC): Build timestamp
- `sha256` (SHA256): Artifact content hash
- `signing_key_id` (string): Signing key identifier
- `signature` (Base64): ed25519 signature of manifest hash
- `toolchain_fingerprint` (SHA256): Toolchain configuration hash
- `build_host_fingerprint` (SHA256): Build host identity hash

## Cryptographic Choice

**Algorithm**: ed25519

**Justification**:
- Fast signing and verification
- Small signature size (64 bytes)
- Strong security (128-bit security level)
- Deterministic (RFC 8032)
- Widely supported in regulatory contexts
- Separate from Audit Ledger, Global Validator, Reporting, Model Registry keys

**Never reuse keys across subsystems.**

## Installer Integration

Each installer **must**:

1. **Verify its own manifest** before execution
2. **Abort installation** on failure
3. **Emit Audit Ledger entry**:
   - `SUPPLY_CHAIN_VERIFICATION_PASSED`
   - `SUPPLY_CHAIN_VERIFICATION_FAILED`

**No bypass flags. No "continue anyway".**

### Example Installer Integration

```python
from supply_chain.engine.verification_engine import VerificationEngine
from supply_chain.crypto.artifact_verifier import ArtifactVerifier
from pathlib import Path

# Initialize verifier
verifier = ArtifactVerifier(public_key_path=Path('/path/to/public_key.pem'))
verification_engine = VerificationEngine(verifier)

# Verify installer
installer_path = Path(__file__)  # Current installer
manifest_path = Path(__file__).with_suffix('.manifest.json')

result = verification_engine.verify_artifact(installer_path, manifest_path)

if not result.passed:
    print(f"Installation aborted: {result.reason}", file=sys.stderr)
    sys.exit(1)

# Emit audit ledger entry
# ... (emit SUPPLY_CHAIN_VERIFICATION_PASSED)
```

## Global Validator Integration

Global Validator must add checks:

- **Installer integrity**: Verify installer manifest
- **Binary integrity**: Verify binary SHA256 hashes
- **Manifest continuity**: Verify manifest chain-of-custody

Validator must be able to:

- **Re-verify artifacts offline**: No network required
- **Use alternate trusted public keys**: Support customer trust roots

## Usage

### Sign Artifact

```bash
python3 supply-chain/cli/sign_artifacts.py \
    --artifact ransomeye-installer.bin \
    --artifact-name ransomeye-core-installer \
    --artifact-type CORE_INSTALLER \
    --version 1.0.0 \
    --signing-key-id vendor-release-key-1 \
    --key-dir /var/lib/ransomeye/supply-chain/keys \
    --output-dir /var/lib/ransomeye/supply-chain/manifests
```

### Verify Artifact (Vendor Key)

```bash
python3 supply-chain/cli/verify_artifacts.py \
    --artifact ransomeye-installer.bin \
    --manifest ransomeye-installer.bin.manifest.json \
    --key-dir /var/lib/ransomeye/supply-chain/keys \
    --signing-key-id vendor-release-key-1
```

### Verify Artifact (Customer Key)

```bash
python3 supply-chain/cli/verify_artifacts.py \
    --artifact ransomeye-installer.bin \
    --manifest ransomeye-installer.bin.manifest.json \
    --public-key /path/to/customer_public_key.pem
```

## File Structure

```
supply-chain/
├── schema/
│   └── artifact-manifest.schema.json    # Frozen JSON schema
├── crypto/
│   ├── __init__.py
│   ├── vendor_key_manager.py          # Vendor key management
│   ├── artifact_signer.py             # ed25519 signing
│   └── artifact_verifier.py           # Offline verification
├── engine/
│   ├── __init__.py
│   ├── manifest_builder.py            # Deterministic manifest building
│   └── verification_engine.py        # Comprehensive verification
├── cli/
│   ├── __init__.py
│   ├── sign_artifacts.py              # Sign artifact CLI
│   └── verify_artifacts.py           # Verify artifact CLI
└── README.md                          # This file
```

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **cryptography**: Required for ed25519 signing/verification

## Security Considerations

1. **Separate keys**: Never reuse keys across subsystems
2. **Offline storage**: Vendor keys stored offline (documented)
3. **External key support**: Customers can replace trust roots
4. **No bypass flags**: Installers must verify before execution
5. **Explicit failures**: No silent failures, all failures are explicit

## Explicit Non-Features

This framework **MUST NOT**:

- ❌ Assume PKI infrastructure
- ❌ Make internet calls
- ❌ Hardcode paths
- ❌ Include optional fields
- ❌ Skip verification
- ❌ Share keys with other subsystems

## Branding vs Integrity Boundary

### Why Branding is Excluded from Cryptographic Scope

Branding (logo, visual identity, evidence notices) is **presentation-only** and is **excluded from cryptographic scope** for the following reasons:

1. **Integrity vs Identity**: Cryptographic hashes and signatures prove **integrity** (artifact has not been modified). Branding asserts **identity** (origin and visual recognition). These are separate concerns.

2. **Deterministic Content**: Signed manifests must be **deterministic** and **reproducible**. Branding elements (logos, visual styling) may change for legal or operational reasons without affecting artifact integrity.

3. **Legal Clarity**: Visual identity helps establish **legal clarity** and **chain-of-custody** in court/regulatory contexts, but does not affect the **cryptographic proof** of artifact integrity.

4. **Customer Trust**: Customers may need to replace or modify branding for their own legal/operational requirements without invalidating cryptographic proofs.

### Why Visual Identity Still Matters Legally

Visual identity (logo, product name, evidence notices) matters legally because:

- **Origin Assertion**: Visual identity asserts the origin of the artifact (RansomEye)
- **Chain-of-Custody**: Visual markings help establish chain-of-custody in court
- **Regulatory Compliance**: Visual identity helps meet regulatory requirements for evidence presentation
- **Professional Standards**: Visual identity meets professional standards for evidence-grade artifacts

### Court / Regulator Interpretation

Courts and regulators interpret branding and integrity as follows:

- **Cryptographic Proof**: SHA256 hashes and ed25519 signatures provide **cryptographic proof** of artifact integrity
- **Visual Identity**: Logos and product names provide **visual proof** of origin and identity
- **Separation**: The separation of branding from cryptographic scope is **intentional** and **documented**, allowing both to serve their respective purposes without interference

### Implementation

In RansomEye Supply-Chain Signing & Verification Framework:

- **Manifest Signing**: Only manifest content (not branding) is signed
- **Installer Display**: Branding is displayed **before** verification, not embedded in signed content
- **Verification Output**: Branding in verification output is **presentation-only**, not part of verification logic

**Manifest signature must NOT change if logo file is replaced.**

> **"Branding asserts origin; cryptography asserts integrity. RansomEye separates both by design."**

## Final Statement

> **"RansomEye self-signs for integrity, not authority. Final trust always belongs to the operator."**

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye Supply-Chain Signing & Verification Framework documentation.
