# Phase-9: Production Enablement — Design Document

**Document Classification:** Production Architecture Specification  
**Version:** 1.0  
**Date:** 2024-01-15  
**Author:** Lead Production Architect for RansomEye v1.0  
**Status:** Design Phase (Implementation Pending)

---

## Executive Summary

Phase-9 transforms RansomEye v1.0 from an architecturally complete but operationally incomplete system into a production-ready platform. This phase addresses three critical blockers identified in the Production Readiness Assessment:

1. **Build System**: Replace placeholder builds with deterministic, reproducible builds
2. **Cryptographic Authority**: Establish persistent, auditable signing key management
3. **Credential Remediation**: Remove all hardcoded credentials and establish secure secret management
4. **Release Gate Independence**: Enable offline release verification without CI artifact dependencies

**Scope:** Phase-9 focuses exclusively on production enablement. Phase-8 logic remains unchanged except where required to bind evidence to real artifacts.

---

## 1. Build System Architecture

### 1.1 Component Inventory

RansomEye v1.0 consists of four production components requiring distinct build strategies:

#### Component 1: Core
- **Language:** Python 3.10+
- **Structure:** Multi-service Python application
- **Components:**
  - Ingest Service (`services/ingest/`)
  - Correlation Engine (`services/correlation-engine/`)
  - AI Core (`services/ai-core/`)
  - Policy Engine (`services/policy-engine/`)
  - UI Backend (`services/ui/backend/`)
  - UI Frontend (`services/ui/frontend/`)
  - Common utilities (`common/`)
- **Dependencies:** PostgreSQL, Python packages (requirements.txt files)
- **Packaging Format:** `core-installer.tar.gz` (tarball with Python code, installers, configs)

#### Component 2: Linux Agent
- **Language:** Rust (edition 2021)
- **Source:** `services/linux-agent/`
- **Build Tool:** Cargo
- **Target:** `x86_64-unknown-linux-gnu`
- **Dependencies:** reqwest, uuid, serde, serde_json, sha2, chrono, anyhow, hostname
- **Packaging Format:** `linux-agent.tar.gz` (binary + installer scripts)

#### Component 3: Windows Agent
- **Language:** Rust (edition 2021)
- **Source:** `agents/windows/agent/` (Python) + `services/windows-agent/` (Rust, if exists)
- **Build Tool:** Cargo (for Rust) or Python packaging (if Python-only)
- **Target:** `x86_64-pc-windows-msvc`
- **Dependencies:** Rust toolchain for Windows cross-compilation
- **Packaging Format:** `windows-agent.zip` (binary + installer scripts)

#### Component 4: DPI Probe
- **Language:** Python 3.10+
- **Source:** `dpi/probe/`
- **Dependencies:** Python packages (requirements.txt)
- **Packaging Format:** `dpi-probe.tar.gz` (Python code + installer scripts)

### 1.2 Build Environment Requirements

#### Deterministic Build Controls

**1.2.1 Source Code Versioning**
- **Requirement:** All builds must reference exact git commit SHA
- **Enforcement:** Build scripts must capture `git rev-parse HEAD` and embed in build metadata
- **Evidence:** `build/artifacts/build-info.json` must contain:
  ```json
  {
    "git_commit": "exact_sha256_hash",
    "git_tag": "v1.0.0",
    "build_timestamp": "RFC3339_UTC",
    "build_runner": "github-actions",
    "build_id": "github_run_id"
  }
  ```

**1.2.2 Dependency Pinning**
- **Python:** All `requirements.txt` files must use exact version pins (no `>=`, `~=`, or ranges)
- **Rust:** `Cargo.lock` must be committed to version control
- **Node.js:** `package-lock.json` must be committed (if UI frontend uses npm)
- **Enforcement:** Build fails if any dependency specification is unpinned

**1.2.3 Build Environment Isolation**
- **Requirement:** Builds must run in isolated, reproducible environments
- **Implementation:**
  - Python: Use virtual environments with `--no-deps` flag to prevent contamination
  - Rust: Use `cargo build --locked` to enforce Cargo.lock
  - Node.js: Use `npm ci` (not `npm install`) for deterministic installs
- **Evidence:** Build logs must show exact versions of all toolchain components

**1.2.4 Timestamp Control**
- **Requirement:** Build timestamps must be deterministic or explicitly controlled
- **Implementation:**
  - Set `SOURCE_DATE_EPOCH` environment variable to fixed value for reproducible builds
  - Use `--reproducible` flag for Rust builds (if available)
  - Python: Set `PYTHONHASHSEED=0` for deterministic hash ordering
- **Evidence:** Build metadata must record `SOURCE_DATE_EPOCH` value used

### 1.3 Per-Component Build Strategy

#### 1.3.1 Core Build Process

**Build Steps:**
1. **Environment Setup**
   ```bash
   python3 -m venv build/venv-core
   source build/venv-core/bin/activate
   pip install --upgrade pip==<exact_version>
   ```

2. **Dependency Installation**
   ```bash
   # Install all requirements.txt files with exact pins
   find . -name "requirements.txt" -exec pip install --no-deps -r {} \;
   # Verify no unpinned dependencies
   pip check
   ```

3. **Code Validation**
   ```bash
   # Type checking (if mypy configured)
   mypy --strict common/ services/
   # Linting
   flake8 common/ services/
   ```

4. **Package Assembly**
   ```bash
   mkdir -p build/artifacts/core-installer
   # Copy Python code
   cp -r common/ build/artifacts/core-installer/
   cp -r core/ build/artifacts/core-installer/
   cp -r services/ build/artifacts/core-installer/
   cp -r contracts/ build/artifacts/core-installer/
   cp -r schemas/ build/artifacts/core-installer/
   # Copy installer
   cp -r installer/core/ build/artifacts/core-installer/installer/
   # Generate build metadata
   python3 scripts/generate_build_info.py --output build/artifacts/core-installer/build-info.json
   ```

5. **Tarball Creation**
   ```bash
   cd build/artifacts
   tar czf core-installer.tar.gz \
     --owner=0 --group=0 \
     --mtime="@${SOURCE_DATE_EPOCH}" \
     core-installer/
   ```

**Artifact Output:**
- `build/artifacts/core-installer.tar.gz` (SHA256 hash recorded in build-info.json)

#### 1.3.2 Linux Agent Build Process

**Build Steps:**
1. **Rust Toolchain Setup**
   ```bash
   rustup toolchain install stable
   rustup target add x86_64-unknown-linux-gnu
   ```

2. **Deterministic Build**
   ```bash
   cd services/linux-agent
   export SOURCE_DATE_EPOCH=$(date +%s)
   export RUSTFLAGS="-C link-arg=-fuse-ld=gold"
   cargo build --release --locked --target x86_64-unknown-linux-gnu
   ```

3. **Binary Verification**
   ```bash
   # Verify binary exists and is executable
   test -f target/x86_64-unknown-linux-gnu/release/ransomeye-linux-agent
   # Record binary hash
   sha256sum target/x86_64-unknown-linux-gnu/release/ransomeye-linux-agent > binary.sha256
   ```

4. **Package Assembly**
   ```bash
   mkdir -p build/artifacts/linux-agent
   cp target/x86_64-unknown-linux-gnu/release/ransomeye-linux-agent build/artifacts/linux-agent/
   cp -r installer/linux-agent/* build/artifacts/linux-agent/installer/
   cp binary.sha256 build/artifacts/linux-agent/
   ```

5. **Tarball Creation**
   ```bash
   cd build/artifacts
   tar czf linux-agent.tar.gz \
     --owner=0 --group=0 \
     --mtime="@${SOURCE_DATE_EPOCH}" \
     linux-agent/
   ```

**Artifact Output:**
- `build/artifacts/linux-agent.tar.gz` (SHA256 hash recorded in build-info.json)

#### 1.3.3 Windows Agent Build Process

**Build Steps:**
1. **Rust Toolchain Setup (Cross-Compilation)**
   ```bash
   rustup toolchain install stable-x86_64-pc-windows-msvc
   # Or use cross-compilation toolchain
   rustup target add x86_64-pc-windows-msvc
   ```

2. **Deterministic Build**
   ```bash
   cd services/windows-agent  # or agents/windows/agent if Python-based
   export SOURCE_DATE_EPOCH=$(date +%s)
   # If Rust:
   cargo build --release --locked --target x86_64-pc-windows-msvc
   # If Python:
   python3 -m PyInstaller --onefile --name ransomeye-windows-agent agent_main.py
   ```

3. **Binary Verification**
   ```bash
   # Verify binary exists
   test -f target/x86_64-pc-windows-msvc/release/ransomeye-windows-agent.exe
   # Record binary hash
   sha256sum target/x86_64-pc-windows-msvc/release/ransomeye-windows-agent.exe > binary.sha256
   ```

4. **Package Assembly**
   ```bash
   mkdir -p build/artifacts/windows-agent
   cp target/x86_64-pc-windows-msvc/release/ransomeye-windows-agent.exe build/artifacts/windows-agent/
   cp -r installer/windows-agent/* build/artifacts/windows-agent/installer/
   cp binary.sha256 build/artifacts/windows-agent/
   ```

5. **ZIP Creation**
   ```bash
   cd build/artifacts
   zip -r windows-agent.zip \
     -x "*.git*" \
     windows-agent/
   ```

**Artifact Output:**
- `build/artifacts/windows-agent.zip` (SHA256 hash recorded in build-info.json)

#### 1.3.4 DPI Probe Build Process

**Build Steps:**
1. **Environment Setup**
   ```bash
   python3 -m venv build/venv-dpi
   source build/venv-dpi/bin/activate
   pip install --upgrade pip==<exact_version>
   ```

2. **Dependency Installation**
   ```bash
   cd dpi/probe
   pip install --no-deps -r requirements.txt
   ```

3. **Package Assembly**
   ```bash
   mkdir -p build/artifacts/dpi-probe
   cp -r dpi/probe/* build/artifacts/dpi-probe/
   cp -r installer/dpi-probe/* build/artifacts/dpi-probe/installer/
   ```

4. **Tarball Creation**
   ```bash
   cd build/artifacts
   tar czf dpi-probe.tar.gz \
     --owner=0 --group=0 \
     --mtime="@${SOURCE_DATE_EPOCH}" \
     dpi-probe/
   ```

**Artifact Output:**
- `build/artifacts/dpi-probe.tar.gz` (SHA256 hash recorded in build-info.json)

### 1.4 Reproducibility Guarantees

**1.4.1 Build Reproducibility Verification**
- **Requirement:** Same source code + same dependencies + same build environment = identical binaries
- **Verification Process:**
  1. Build artifact A at time T1 with commit SHA1
  2. Build artifact B at time T2 with same commit SHA1
  3. Compare SHA256 hashes: `sha256sum artifactA == sha256sum artifactB`
- **Evidence:** Reproducibility test results stored in `build/artifacts/reproducibility-test.json`

**1.4.2 Build Environment Documentation**
- **Requirement:** Complete documentation of build environment
- **Content:**
  - OS version and kernel
  - Toolchain versions (Python, Rust, Node.js, etc.)
  - Environment variables
  - Build flags and options
- **Evidence:** `build/artifacts/build-environment.json`

### 1.5 Artifact Layout

**Exact Paths and Names:**
```
build/artifacts/
├── core-installer.tar.gz
├── linux-agent.tar.gz
├── windows-agent.zip
├── dpi-probe.tar.gz
├── build-info.json
├── build-environment.json
├── reproducibility-test.json
└── signed/
    ├── core-installer.tar.gz.manifest.json
    ├── core-installer.tar.gz.manifest.sig
    ├── linux-agent.tar.gz.manifest.json
    ├── linux-agent.tar.gz.manifest.sig
    ├── windows-agent.zip.manifest.json
    ├── windows-agent.zip.manifest.sig
    ├── dpi-probe.tar.gz.manifest.json
    └── dpi-probe.tar.gz.manifest.sig
```

---

## 2. Cryptographic Authority Design

### 2.1 Persistent Vendor Signing Key Architecture

#### 2.1.1 Key Hierarchy

**Three-Tier Key Hierarchy:**

1. **Root Key (Offline, Air-Gapped)**
   - **Purpose:** Signs intermediate CA certificates
   - **Storage:** Hardware Security Module (HSM) or offline air-gapped system
   - **Access:** Physical access required, multi-person authorization
   - **Rotation:** Every 5 years or on compromise
   - **Location:** `keys/root/vendor-root-key-1.pem` (encrypted, offline storage)

2. **Signing Key (Online, HSM-Protected)**
   - **Purpose:** Signs release artifacts and SBOMs
   - **Storage:** HSM (preferred) or encrypted key vault with access controls
   - **Access:** Automated CI/CD access via HSM API (no key material exposed)
   - **Rotation:** Every 2 years or on compromise
   - **Location:** HSM key slot or `keys/signing/vendor-signing-key-1.pem` (HSM-encrypted)

3. **Ephemeral Session Keys (CI-Generated, Short-Lived)**
   - **Purpose:** NOT USED. All signing uses persistent signing keys.
   - **Rationale:** Eliminates ephemeral key generation in CI

#### 2.1.2 Key Naming Convention

**Format:** `vendor-{key-type}-{key-id}-{generation-date}`

**Examples:**
- `vendor-root-key-1-20240115`
- `vendor-signing-key-1-20240115`
- `vendor-signing-key-2-20240201` (rotated key)

**Metadata File:** Each key has associated metadata:
```json
{
  "key_id": "vendor-signing-key-1",
  "key_type": "signing",
  "generation_date": "2024-01-15T00:00:00Z",
  "algorithm": "ed25519",
  "public_key_fingerprint": "sha256:...",
  "status": "active",
  "rotation_date": null,
  "revocation_date": null
}
```

### 2.2 HSM / Offline Vault Model

#### 2.2.1 HSM Integration Architecture

**Option A: Cloud HSM (Preferred for CI/CD)**
- **Service:** AWS CloudHSM, Azure Dedicated HSM, or Google Cloud HSM
- **Integration:** HSM client library in CI/CD pipeline
- **Access Control:** IAM roles with least-privilege access
- **Key Operations:** Sign operations performed on HSM, private key never leaves HSM
- **Evidence:** HSM audit logs for all signing operations

**Option B: On-Premises HSM (For Air-Gapped Environments)**
- **Hardware:** FIPS 140-2 Level 3+ HSM (e.g., Thales Luna, SafeNet)
- **Integration:** HSM client library with network access to HSM
- **Access Control:** Certificate-based authentication, role-based access
- **Key Operations:** Sign operations performed on HSM
- **Evidence:** HSM audit logs exported to secure logging system

**Option C: Software Key Vault (Interim Solution)**
- **Service:** HashiCorp Vault, AWS Secrets Manager, or Azure Key Vault
- **Integration:** API-based key retrieval and signing
- **Access Control:** IAM/AD authentication, encryption at rest
- **Key Operations:** Private key retrieved, signing performed in CI (less secure than HSM)
- **Evidence:** Vault audit logs for all key access

#### 2.2.2 Offline Root Key Storage

**Physical Security Requirements:**
- **Location:** Secure physical vault or safe
- **Access:** Multi-person authorization (2-of-3 or 3-of-5)
- **Media:** Encrypted USB drive or smart card
- **Backup:** Multiple geographically distributed backups
- **Documentation:** Key generation ceremony documented and witnessed

**Key Generation Ceremony:**
1. **Participants:** Key custodian, security officer, witness
2. **Environment:** Air-gapped system, verified clean OS
3. **Process:**
   - Generate keypair on air-gapped system
   - Verify keypair integrity
   - Export public key (for distribution)
   - Encrypt private key with passphrase
   - Store encrypted private key on encrypted media
   - Destroy all temporary files
   - Document ceremony in key generation log
4. **Evidence:** `keys/root/vendor-root-key-1-generation-log.json`

### 2.3 Key Lifecycle Management

#### 2.3.1 Key Generation

**Signing Key Generation (HSM):**
1. **Request:** Key custodian initiates key generation request
2. **Authorization:** Multi-person approval (2-of-3)
3. **Generation:** HSM generates keypair (private key never leaves HSM)
4. **Verification:** Public key exported and verified
5. **Registration:** Key registered in key registry with metadata
6. **Evidence:** `keys/signing/vendor-signing-key-{id}-generation-log.json`

**Root Key Generation (Offline):**
1. **Ceremony:** Physical key generation ceremony (see 2.2.2)
2. **Documentation:** Complete ceremony log
3. **Distribution:** Public key distributed to all stakeholders
4. **Storage:** Encrypted private key stored in secure vault
5. **Evidence:** `keys/root/vendor-root-key-{id}-generation-log.json`

#### 2.3.2 Key Storage

**Signing Key Storage (HSM):**
- **Primary:** HSM key slot (private key never exported)
- **Backup:** Encrypted key export stored in secure backup system
- **Access:** HSM API with certificate-based authentication
- **Evidence:** HSM audit logs showing key creation and access

**Root Key Storage (Offline):**
- **Primary:** Encrypted USB drive in physical vault
- **Backup:** Encrypted backup in geographically separate vault
- **Access:** Physical access + multi-person authorization
- **Evidence:** Vault access logs, key retrieval logs

#### 2.3.3 Key Rotation

**Rotation Trigger Events:**
- **Scheduled:** Every 2 years (signing keys), every 5 years (root keys)
- **Compromise:** Immediate rotation on suspected or confirmed compromise
- **Regulatory:** Rotation required by compliance requirements

**Rotation Process (Signing Keys):**
1. **Planning:** Key rotation plan documented 30 days before rotation
2. **Generation:** New key generated (see 2.3.1)
3. **Dual-Signing Period:** Both old and new keys sign artifacts for 90 days
4. **Migration:** All new artifacts signed with new key only
5. **Revocation:** Old key marked as revoked (not deleted, for historical verification)
6. **Evidence:** `keys/signing/vendor-signing-key-{id}-rotation-log.json`

**Rotation Process (Root Keys):**
1. **Ceremony:** Physical key rotation ceremony (similar to generation)
2. **Certificate Chain:** New root key signs new intermediate certificates
3. **Migration:** Gradual migration of signing keys to new root
4. **Revocation:** Old root key marked as revoked
5. **Evidence:** `keys/root/vendor-root-key-{id}-rotation-log.json`

#### 2.3.4 Key Escrow / Backup

**Escrow Requirements:**
- **Purpose:** Disaster recovery, key loss prevention
- **Storage:** Encrypted backups in geographically distributed secure locations
- **Access:** Multi-person authorization required
- **Verification:** Periodic restoration tests to verify escrow integrity

**Backup Process:**
1. **Encryption:** Private key encrypted with strong passphrase
2. **Distribution:** Encrypted backup stored in 3+ geographically separate locations
3. **Verification:** Periodic restoration tests (annually)
4. **Evidence:** `keys/{type}/vendor-{type}-key-{id}-escrow-log.json`

#### 2.3.5 Key Revocation & Compromise Recovery

**Revocation Triggers:**
- **Compromise:** Suspected or confirmed key compromise
- **Rotation:** Key replaced by newer key
- **Regulatory:** Revocation required by compliance

**Revocation Process:**
1. **Immediate Action:** Key marked as revoked in key registry
2. **Notification:** All stakeholders notified of revocation
3. **Certificate Revocation List (CRL):** Revoked key added to CRL
4. **Artifact Re-Signing:** All artifacts signed with revoked key must be re-signed with new key
5. **Evidence:** `keys/{type}/vendor-{type}-key-{id}-revocation-log.json`

**Compromise Recovery:**
1. **Detection:** Compromise detected through monitoring or audit
2. **Immediate Revocation:** Key revoked immediately
3. **Investigation:** Forensic investigation of compromise
4. **Key Rotation:** New key generated and activated
5. **Artifact Re-Signing:** All artifacts re-signed with new key
6. **Notification:** Customers and stakeholders notified
7. **Evidence:** `keys/{type}/vendor-{type}-key-{id}-compromise-recovery-log.json`

### 2.4 Phase-8 Integration Without Trusting CI

#### 2.4.1 Key Access in CI/CD

**HSM-Based Signing (Preferred):**
```yaml
- name: Sign artifacts with HSM
  env:
    HSM_ENDPOINT: ${{ secrets.HSM_ENDPOINT }}
    HSM_KEY_SLOT: vendor-signing-key-1
    HSM_CERT_PATH: ${{ secrets.HSM_CLIENT_CERT }}
  run: |
    python3 supply-chain/cli/sign_artifacts.py \
      --artifact "$artifact" \
      --hsm-endpoint "$HSM_ENDPOINT" \
      --hsm-key-slot "$HSM_KEY_SLOT" \
      --hsm-cert "$HSM_CERT_PATH"
```

**Key Material Never Exposed:**
- Private key never leaves HSM
- CI only has access to HSM API (not key material)
- Signing operations logged in HSM audit trail

#### 2.4.2 Offline Verification

**Public Key Distribution:**
- Public keys published in public key registry
- Public keys embedded in release bundles
- Public keys available for download from vendor website

**Verification Process:**
1. **Obtain Public Key:** Download from public registry or release bundle
2. **Verify Signature:** Use public key to verify artifact signatures
3. **No CI Dependency:** Verification requires only public key (not CI access)

**Evidence:** Phase-8 verification scripts updated to accept public key as parameter (not retrieve from CI)

---

## 3. Credential & Secret Remediation Plan

### 3.1 Hardcoded Credential Inventory

#### 3.1.1 Identified Hardcoded Credentials

**Location 1: CI Validation Workflow**
- **File:** `.github/workflows/ci-validation-reusable.yml:47-50`
- **Credentials:**
  ```yaml
  RANSOMEYE_DB_NAME: 'ransomeye_test'
  RANSOMEYE_DB_USER: 'ransomeye_test'
  RANSOMEYE_DB_PASSWORD: 'test_password_change_in_production'
  ```
- **Risk:** Credentials exposed in version control, accessible to anyone with repository access

**Location 2: Installer Scripts (Historical)**
- **Files:**
  - `installer/core/install.sh:424-425`
  - `installer/linux-agent/install.sh:228-229`
  - `installer/dpi-probe/install.sh:276-277`
- **Credentials:** Default database credentials (`gagan`/`gagan`)
- **Risk:** Default credentials in installer scripts

**Location 3: Test Signing Keys**
- **File:** `installer/core/install.sh:436`
- **Credential:** `RANSOMEYE_COMMAND_SIGNING_KEY="test_signing_key_minimum_32_characters_long_for_validation_long_enough"`
- **Risk:** Test signing key hardcoded in installer

### 3.2 Remediation Steps

#### 3.2.1 Step 1: Move CI Credentials to GitHub Secrets

**Action:**
1. **Create GitHub Secrets:**
   - `RANSOMEYE_DB_NAME` → GitHub Secret: `TEST_DB_NAME`
   - `RANSOMEYE_DB_USER` → GitHub Secret: `TEST_DB_USER`
   - `RANSOMEYE_DB_PASSWORD` → GitHub Secret: `TEST_DB_PASSWORD`

2. **Update Workflow:**
   ```yaml
   env:
     RANSOMEYE_DB_NAME: ${{ secrets.TEST_DB_NAME }}
     RANSOMEYE_DB_USER: ${{ secrets.TEST_DB_USER }}
     RANSOMEYE_DB_PASSWORD: ${{ secrets.TEST_DB_PASSWORD }}
   ```

3. **Remove Hardcoded Values:**
   - Delete hardcoded credentials from workflow file
   - Commit change with message: "SECURITY: Remove hardcoded test credentials"

**Evidence:** 
- GitHub Secrets configured (screenshot or API verification)
- Workflow file updated (git commit)
- CI validation still passes with secrets

#### 3.2.2 Step 2: Remove Default Credentials from Installers

**Action:**
1. **Update Installer Scripts:**
   - Remove default database credentials
   - Require environment variables or user input
   - Fail-fast if credentials not provided

2. **Example Change:**
   ```bash
   # BEFORE:
   RANSOMEYE_DB_USER="gagan"
   RANSOMEYE_DB_PASSWORD="gagan"
   
   # AFTER:
   if [ -z "$RANSOMEYE_DB_USER" ] || [ -z "$RANSOMEYE_DB_PASSWORD" ]; then
     echo "ERROR: RANSOMEYE_DB_USER and RANSOMEYE_DB_PASSWORD must be set"
     exit 1
   fi
   ```

3. **Update Documentation:**
   - Installer READMEs updated to document required environment variables
   - Examples show secure credential provisioning

**Evidence:**
- Installer scripts updated (git commits)
- Installer documentation updated
- Installer tests verify fail-fast behavior

#### 3.2.3 Step 3: Remove Test Signing Keys

**Action:**
1. **Update Installer Scripts:**
   - Remove hardcoded test signing key
   - Require `RANSOMEYE_COMMAND_SIGNING_KEY` environment variable
   - Fail-fast if not provided

2. **Update Documentation:**
   - Document signing key generation process
   - Provide examples of secure key generation

**Evidence:**
- Installer scripts updated
- Documentation updated
- Tests verify fail-fast behavior

#### 3.2.4 Step 4: Rotate Exposed Credentials

**Action:**
1. **Database Credentials:**
   - Rotate `ransomeye_test` database password
   - Update GitHub Secret with new password
   - Verify CI validation still passes

2. **Signing Keys:**
   - Generate new test signing keys
   - Update test environments
   - Verify tests still pass

**Evidence:**
- Credential rotation log
- CI validation passes with new credentials
- Old credentials invalidated

#### 3.2.5 Step 5: Audit Git History

**Action:**
1. **Scan Git History:**
   ```bash
   git log --all --full-history --source -- "*" | \
     grep -i -E "(password|secret|key|credential|token)" > git-history-audit.txt
   ```

2. **Identify Exposed Credentials:**
   - Review audit output
   - Identify commits containing credentials
   - Document all exposed credentials

3. **Rotate All Exposed Credentials:**
   - Rotate all credentials found in git history
   - Update all systems using exposed credentials
   - Document rotation in credential rotation log

4. **Consider Git History Rewrite (If Necessary):**
   - **Warning:** Rewriting git history is destructive
   - **Alternative:** Document exposed credentials and rotate
   - **Decision:** Based on risk assessment and organizational policy

**Evidence:**
- Git history audit report (`security/git-history-audit-YYYY-MM-DD.txt`)
- Credential rotation log (`security/credential-rotation-log.json`)
- Risk assessment document

### 3.3 Enforcement Mechanisms

#### 3.3.1 Pre-Commit Hooks

**Implementation:**
```bash
#!/bin/bash
# .git/hooks/pre-commit

# Check for hardcoded credentials
if git diff --cached | grep -i -E "(password|secret|key|credential|token)\s*=\s*['\"][^'\"]+['\"]"; then
  echo "ERROR: Potential hardcoded credential detected"
  echo "Please use environment variables or secrets management"
  exit 1
fi
```

**Evidence:** Pre-commit hook installed and tested

#### 3.3.2 CI Credential Scanning

**Implementation:**
- **Tool:** GitGuardian, TruffleHog, or similar
- **Integration:** GitHub Actions workflow step
- **Action:** Fail CI if credentials detected
- **Configuration:** Scan all files, including git history

**Evidence:** CI credential scanning workflow configured and tested

#### 3.3.3 Code Review Requirements

**Policy:**
- All code changes must be reviewed by security team
- Security team must verify no credentials in code
- Automated scanning must pass before merge

**Evidence:** Code review policy documented, security team trained

---

## 4. Release Gate Independence

### 4.1 Current Release Gate Dependencies

#### 4.1.1 CI Artifact Dependencies

**Current Implementation:**
- Release gate downloads artifacts from CI (`actions/download-artifact@v4`)
- Release gate downloads signing public key from CI
- Release gate depends on CI artifact retention (90 days)

**Problems:**
1. **Artifact Expiration:** CI artifacts expire after 90 days, release gate cannot run
2. **CI Failure Dependency:** If CI fails, release gate cannot access artifacts
3. **Long-Term Verification:** Cannot verify releases after artifact expiration

#### 4.1.2 Required Changes

**Objective:** Release gate must be fully independent of CI artifact retention.

### 4.2 Redesigned Release Gate Architecture

#### 4.2.1 Release Bundle Structure

**New Release Bundle Format:**
```
ransomeye-v1.0.0-release-bundle/
├── artifacts/
│   ├── core-installer.tar.gz
│   ├── linux-agent.tar.gz
│   ├── windows-agent.zip
│   └── dpi-probe.tar.gz
├── signatures/
│   ├── core-installer.tar.gz.manifest.json
│   ├── core-installer.tar.gz.manifest.sig
│   ├── linux-agent.tar.gz.manifest.json
│   ├── linux-agent.tar.gz.manifest.sig
│   ├── windows-agent.zip.manifest.json
│   ├── windows-agent.zip.manifest.sig
│   ├── dpi-probe.tar.gz.manifest.json
│   └── dpi-probe.tar.gz.manifest.sig
├── sbom/
│   ├── manifest.json
│   └── manifest.json.sig
├── keys/
│   └── vendor-signing-key-1.pub
├── evidence/
│   ├── runtime_smoke_result.json
│   ├── release_integrity_result.json
│   ├── evidence_bundle.json
│   └── evidence_bundle.json.sig
└── metadata/
    ├── build-info.json
    ├── build-environment.json
    └── release-notes.md
```

#### 4.2.2 Release Bundle Creation

**Process:**
1. **Artifact Collection:** Collect all artifacts from build process
2. **Signature Collection:** Collect all signatures from signing process
3. **SBOM Collection:** Collect SBOM and SBOM signature
4. **Public Key Inclusion:** Include public key in release bundle
5. **Evidence Collection:** Collect Phase-8 evidence bundles
6. **Bundle Creation:** Create tarball or ZIP of complete release bundle

**Implementation:**
```bash
# Create release bundle
mkdir -p release/ransomeye-v1.0.0-release-bundle
cp build/artifacts/*.tar.gz release/ransomeye-v1.0.0-release-bundle/artifacts/
cp build/artifacts/*.zip release/ransomeye-v1.0.0-release-bundle/artifacts/
cp build/artifacts/signed/*.manifest.* release/ransomeye-v1.0.0-release-bundle/signatures/
cp build/artifacts/sbom/* release/ransomeye-v1.0.0-release-bundle/sbom/
cp keys/vendor-signing-key-1.pub release/ransomeye-v1.0.0-release-bundle/keys/
cp validation/evidence_bundle/* release/ransomeye-v1.0.0-release-bundle/evidence/
tar czf ransomeye-v1.0.0-release-bundle.tar.gz release/ransomeye-v1.0.0-release-bundle/
```

#### 4.2.3 Offline Release Gate Execution

**Updated Release Gate Workflow:**
```yaml
- name: Extract release bundle
  run: |
    tar xzf ransomeye-v1.0.0-release-bundle.tar.gz
    cd ransomeye-v1.0.0-release-bundle

- name: PHASE 6 Gate 1 - Validation Complete
  run: |
    # Verify evidence bundle exists
    test -f evidence/evidence_bundle.json
    # Verify GA verdict
    python3 -c "import json; assert json.load(open('evidence/evidence_bundle.json'))['ga_verdict'] == 'PASS'"

- name: PHASE 6 Gate 2 - All Artifacts Signed
  run: |
    # Verify all artifacts have signatures
    for artifact in artifacts/*; do
      ARTIFACT_NAME=$(basename "$artifact")
      test -f "signatures/${ARTIFACT_NAME}.manifest.json"
      test -f "signatures/${ARTIFACT_NAME}.manifest.sig"
    done

- name: PHASE 6 Gate 4 - Signature Verification
  run: |
    # Verify signatures using public key from bundle
    python3 supply-chain/cli/verify_artifacts.py \
      --artifact artifacts/core-installer.tar.gz \
      --manifest signatures/core-installer.tar.gz.manifest.json \
      --public-key keys/vendor-signing-key-1.pub
    # Repeat for all artifacts
```

**Key Changes:**
- No `actions/download-artifact@v4` steps
- All artifacts, signatures, and keys from release bundle
- Release gate can run offline (no CI dependency)

### 4.3 Data Flow Diagram

**Textual Data Flow:**

```
[Source Code] 
    ↓
[Build Process] → [Artifacts] → [Signing Process] → [Signed Artifacts]
    ↓                                                    ↓
[SBOM Generation] → [SBOM] → [SBOM Signing] → [Signed SBOM]
    ↓
[Phase-8 Validation] → [Evidence Bundle] → [Evidence Bundle Signing]
    ↓
[Release Bundle Creation] → [Release Bundle] → [Release Gate] → [Release Approval]
    ↓
[Public Distribution] → [Customer Verification] → [Installation]
```

**Key Points:**
1. **Build Process:** Creates artifacts independently
2. **Signing Process:** Signs artifacts using HSM (not CI-generated keys)
3. **Release Bundle:** Contains all artifacts, signatures, keys, and evidence
4. **Release Gate:** Operates on release bundle (not CI artifacts)
5. **Customer Verification:** Uses public key from release bundle (no CI dependency)

### 4.4 Long-Term Verifiability

**Requirements:**
- Release bundles stored in long-term storage (7+ years for SOX compliance)
- Public keys published in public key registry
- Release bundles can be verified years after creation

**Implementation:**
1. **Release Bundle Storage:** Release bundles stored in S3/Blob Storage with versioning
2. **Public Key Registry:** Public keys published on vendor website and in release bundles
3. **Verification Tools:** Standalone verification tools that work with release bundles

**Evidence:** Release bundle storage configuration, public key registry documentation

---

## 5. Phase-9 Acceptance Criteria

### 5.1 Build System Acceptance Criteria

#### 5.1.1 Real Builds Exist

**What Must Exist:**
- All four components (Core, Linux Agent, Windows Agent, DPI Probe) have real build processes
- Build processes produce functional binaries/packages
- Build artifacts are not empty files

**How It Is Verified:**
1. **Build Execution:** Run build process for each component
2. **Artifact Inspection:** Verify artifacts are non-empty and contain expected content
3. **Functional Testing:** Install and run artifacts to verify functionality

**Evidence Produced:**
- Build logs showing compilation/packaging steps
- Artifact size verification (not 0 bytes)
- Installation and runtime test results

**Pass/Fail Conditions:**
- **PASS:** All artifacts are non-empty, contain expected content, and execute correctly
- **FAIL:** Any artifact is empty, missing expected content, or fails to execute

#### 5.1.2 Deterministic Builds

**What Must Exist:**
- Same source code produces identical binaries (bit-for-bit)
- Build environment is documented and reproducible
- Build reproducibility is verified through testing

**How It Is Verified:**
1. **Reproducibility Test:** Build same source code twice in different environments
2. **Hash Comparison:** Compare SHA256 hashes of artifacts
3. **Environment Documentation:** Verify build environment is fully documented

**Evidence Produced:**
- Reproducibility test results (`build/artifacts/reproducibility-test.json`)
- Build environment documentation (`build/artifacts/build-environment.json`)
- Hash comparison results

**Pass/Fail Conditions:**
- **PASS:** Artifacts from two builds are bit-for-bit identical (same SHA256 hash)
- **FAIL:** Artifacts differ between builds or build environment is not documented

#### 5.1.3 Build Metadata

**What Must Exist:**
- Build metadata includes git commit SHA, build timestamp, build environment
- Build metadata is embedded in artifacts or stored alongside artifacts

**How It Is Verified:**
1. **Metadata Inspection:** Verify `build-info.json` contains required fields
2. **Git Commit Verification:** Verify git commit SHA matches actual commit
3. **Timestamp Verification:** Verify build timestamp is RFC3339 format

**Evidence Produced:**
- `build/artifacts/build-info.json` file
- Git commit SHA verification
- Build timestamp verification

**Pass/Fail Conditions:**
- **PASS:** All required metadata fields present and accurate
- **FAIL:** Missing metadata fields or inaccurate data

### 5.2 Cryptographic Authority Acceptance Criteria

#### 5.2.1 Persistent Key Storage

**What Must Exist:**
- Signing keys stored in HSM or secure key vault (not ephemeral CI storage)
- Keys persist across CI runs
- Key access is logged and auditable

**How It Is Verified:**
1. **Key Storage Inspection:** Verify keys are stored in HSM/vault (not `/tmp`)
2. **Key Persistence Test:** Verify keys exist after CI run completes
3. **Access Log Review:** Review HSM/vault access logs

**Evidence Produced:**
- HSM/vault configuration documentation
- Key storage location verification
- HSM/vault access logs

**Pass/Fail Conditions:**
- **PASS:** Keys stored in HSM/vault, persist across CI runs, access is logged
- **FAIL:** Keys stored in ephemeral storage, lost after CI run, or access not logged

#### 5.2.2 Key Lifecycle Management

**What Must Exist:**
- Key generation procedures documented
- Key rotation procedures documented and tested
- Key escrow/backup procedures documented and tested
- Key revocation procedures documented

**How It Is Verified:**
1. **Documentation Review:** Review key lifecycle documentation
2. **Rotation Test:** Execute key rotation procedure (test environment)
3. **Escrow Test:** Execute key escrow restoration (test environment)
4. **Revocation Test:** Execute key revocation procedure (test environment)

**Evidence Produced:**
- Key lifecycle documentation
- Key rotation test results
- Key escrow restoration test results
- Key revocation test results

**Pass/Fail Conditions:**
- **PASS:** All key lifecycle procedures documented and tested successfully
- **FAIL:** Missing documentation or failed tests

#### 5.2.3 Phase-8 Integration

**What Must Exist:**
- Phase-8 evidence bundles signed with persistent keys (not CI-generated keys)
- Public keys available for offline verification
- Phase-8 verification works without CI access

**How It Is Verified:**
1. **Evidence Bundle Inspection:** Verify evidence bundles signed with persistent keys
2. **Public Key Availability:** Verify public keys available in release bundles
3. **Offline Verification Test:** Verify Phase-8 verification works offline

**Evidence Produced:**
- Evidence bundle signature verification
- Public key availability verification
- Offline verification test results

**Pass/Fail Conditions:**
- **PASS:** Evidence bundles signed with persistent keys, public keys available, offline verification works
- **FAIL:** Evidence bundles signed with ephemeral keys, public keys missing, or offline verification fails

### 5.3 Credential Remediation Acceptance Criteria

#### 5.3.1 Hardcoded Credentials Removed

**What Must Exist:**
- Zero hardcoded credentials in version control
- All credentials moved to secure secret stores (GitHub Secrets, etc.)
- Credential scanning passes (no false positives)

**How It Is Verified:**
1. **Code Scan:** Scan codebase for hardcoded credentials
2. **Secret Store Verification:** Verify credentials in secret stores
3. **CI Verification:** Verify CI still works with secrets

**Evidence Produced:**
- Credential scan results (no hardcoded credentials found)
- Secret store configuration documentation
- CI validation passing with secrets

**Pass/Fail Conditions:**
- **PASS:** No hardcoded credentials found, all credentials in secret stores, CI passes
- **FAIL:** Hardcoded credentials found or CI fails with secrets

#### 5.3.2 Credential Rotation

**What Must Exist:**
- All exposed credentials rotated
- New credentials in secret stores
- Systems updated to use new credentials

**How It Is Verified:**
1. **Rotation Log Review:** Review credential rotation log
2. **Secret Store Verification:** Verify new credentials in secret stores
3. **System Verification:** Verify systems work with new credentials

**Evidence Produced:**
- Credential rotation log (`security/credential-rotation-log.json`)
- Secret store verification
- System verification results

**Pass/Fail Conditions:**
- **PASS:** All exposed credentials rotated, new credentials in use, systems working
- **FAIL:** Exposed credentials not rotated or systems not updated

#### 5.3.3 Enforcement Mechanisms

**What Must Exist:**
- Pre-commit hooks prevent credential commits
- CI credential scanning configured and passing
- Code review policy requires security review

**How It Is Verified:**
1. **Pre-Commit Hook Test:** Attempt to commit credential, verify hook blocks it
2. **CI Scan Verification:** Verify CI credential scanning runs and passes
3. **Policy Review:** Review code review policy

**Evidence Produced:**
- Pre-commit hook test results
- CI credential scanning results
- Code review policy documentation

**Pass/Fail Conditions:**
- **PASS:** Pre-commit hooks work, CI scanning passes, policy documented
- **FAIL:** Pre-commit hooks not working, CI scanning fails, or policy missing

### 5.4 Release Gate Independence Acceptance Criteria

#### 5.4.1 Release Bundle Creation

**What Must Exist:**
- Release bundles contain all artifacts, signatures, keys, and evidence
- Release bundles are self-contained (no external dependencies)
- Release bundles can be created independently of CI

**How It Is Verified:**
1. **Bundle Inspection:** Verify release bundle contains all required components
2. **Self-Contained Test:** Verify release bundle has no external dependencies
3. **Independent Creation Test:** Create release bundle without CI

**Evidence Produced:**
- Release bundle structure documentation
- Release bundle creation test results
- Release bundle inspection results

**Pass/Fail Conditions:**
- **PASS:** Release bundles contain all components, are self-contained, and can be created independently
- **FAIL:** Missing components, external dependencies, or CI required for creation

#### 5.4.2 Offline Release Gate Execution

**What Must Exist:**
- Release gate can run offline (no CI artifact downloads)
- Release gate uses artifacts from release bundle
- Release gate verification works without CI access

**How It Is Verified:**
1. **Offline Execution Test:** Run release gate offline (no network access)
2. **Bundle Source Verification:** Verify release gate uses bundle artifacts
3. **Verification Test:** Verify all gates pass using bundle artifacts

**Evidence Produced:**
- Offline release gate execution test results
- Release gate workflow updated (no `actions/download-artifact`)
- Gate verification results

**Pass/Fail Conditions:**
- **PASS:** Release gate runs offline, uses bundle artifacts, all gates pass
- **FAIL:** Release gate requires CI access, uses CI artifacts, or gates fail

#### 5.4.3 Long-Term Verifiability

**What Must Exist:**
- Release bundles stored in long-term storage
- Public keys available for verification
- Verification tools work with old release bundles

**How It Is Verified:**
1. **Storage Verification:** Verify release bundles in long-term storage
2. **Public Key Availability:** Verify public keys available
3. **Old Bundle Verification:** Verify old release bundles can be verified

**Evidence Produced:**
- Long-term storage configuration
- Public key registry documentation
- Old bundle verification test results

**Pass/Fail Conditions:**
- **PASS:** Release bundles in long-term storage, public keys available, old bundles verifiable
- **FAIL:** Release bundles not in long-term storage, public keys missing, or old bundles not verifiable

### 5.5 Phase-8 Evidence Protection

#### 5.5.1 Real Artifact Protection

**What Must Exist:**
- Phase-8 evidence bundles protect real artifacts (not placeholders)
- Evidence bundle hashes match real artifact hashes
- Evidence bundle signatures verify against real artifacts

**How It Is Verified:**
1. **Artifact Hash Verification:** Verify evidence bundle hashes match real artifact hashes
2. **Signature Verification:** Verify evidence bundle signatures verify against real artifacts
3. **Functional Verification:** Verify artifacts protected by evidence bundles are functional

**Evidence Produced:**
- Artifact hash comparison results
- Signature verification results
- Functional verification results

**Pass/Fail Conditions:**
- **PASS:** Evidence bundles protect real artifacts, hashes match, signatures verify, artifacts functional
- **FAIL:** Evidence bundles protect placeholders, hashes mismatch, signatures fail, or artifacts non-functional

---

## 6. Implementation Constraints

### 6.1 Phase-8 Preservation

**Constraint:** Phase-8 logic must not be modified except where required to bind evidence to real artifacts.

**Allowed Modifications:**
- Update evidence bundle to include real artifact hashes (instead of placeholder hashes)
- Update verification scripts to verify real artifacts (instead of placeholders)
- No changes to evidence bundle structure, signature format, or verification logic

**Prohibited Modifications:**
- Changes to evidence bundle format
- Changes to signature algorithm (ed25519)
- Changes to verification logic (except artifact hash verification)

### 6.2 CI Trust Boundaries

**Constraint:** CI remains convenience, not trust root.

**Requirements:**
- Release gate does not depend on CI artifact retention
- Verification works offline (no CI dependency)
- Public keys available independently of CI

### 6.3 No Placeholders

**Constraint:** All implementations must be real, not placeholders.

**Requirements:**
- Real build processes (not `touch` commands)
- Real key management (not ephemeral keys)
- Real credential management (not hardcoded credentials)

---

## 7. Evidence Requirements

### 7.1 Build System Evidence

**Required Evidence:**
1. Build logs showing real compilation/packaging
2. Artifact size verification (not 0 bytes)
3. Build reproducibility test results
4. Build environment documentation
5. Build metadata files

### 7.2 Cryptographic Authority Evidence

**Required Evidence:**
1. HSM/vault configuration documentation
2. Key generation ceremony logs
3. Key rotation test results
4. Key escrow restoration test results
5. Key revocation test results
6. HSM/vault access logs

### 7.3 Credential Remediation Evidence

**Required Evidence:**
1. Credential scan results (no hardcoded credentials)
2. Secret store configuration documentation
3. Credential rotation log
4. Git history audit report
5. Pre-commit hook test results
6. CI credential scanning results

### 7.4 Release Gate Independence Evidence

**Required Evidence:**
1. Release bundle structure documentation
2. Release bundle creation test results
3. Offline release gate execution test results
4. Long-term storage configuration
5. Public key registry documentation

---

## 8. Conclusion

Phase-9 transforms RansomEye v1.0 from an architecturally complete but operationally incomplete system into a production-ready platform. This design document provides a comprehensive blueprint for:

1. **Real, deterministic builds** for all four components
2. **Persistent, auditable cryptographic authority** with HSM integration
3. **Complete credential remediation** with enforcement mechanisms
4. **Independent release gate** that works offline without CI dependencies

All acceptance criteria are defined with concrete verification procedures and evidence requirements. Implementation must follow these specifications exactly, with no placeholders or assumptions.

**Status:** Design Complete — Ready for Implementation Review

---

**Document End**
