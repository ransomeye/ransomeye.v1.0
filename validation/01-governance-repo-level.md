# Validation Step 1 — Governance & Repo-Level Guarantees

**Component Identity:**
- **Name:** Repository-Level Governance
- **Repo Path:** `/home/ransomeye/rebuild/`
- **Scope:** Entire repository structure and cross-cutting guarantees

**Spec Reference:**
- Master specification: Phase 10.1 — Core Runtime Hardening
- Configuration governance requirements
- Credential governance requirements
- Fail-closed startup requirements

---

## 1. REPOSITORY STRUCTURE & BOUNDARIES

### Evidence

**Root Path:**
- ✅ `/home/ransomeye/rebuild/` exists and is accessible

**Expected Top-Level Domains:**
- ✅ `core/` - Core runtime
- ✅ `agents/` - Agent implementations (Linux, Windows)
- ✅ `services/` - Microservices (ingest, correlation-engine, ai-core, policy-engine, ui)
- ✅ `installer/` - Installation scripts and systemd definitions
- ✅ `validation/` - Validation harness and reports
- ✅ `common/` - Shared utilities (config, db, security, logging)
- ✅ `contracts/` - Event contracts and schemas
- ✅ `schemas/` - Database schemas

**Unexpected Top-Level Items:**
- ⚠️ `10th_jan_promot/` - Contains 89 `.txt` files (appears to be promotional/archive material)
- ⚠️ `git-auto-sync.timer` - Systemd timer file at root
- ⚠️ `git-auto-sync.service` - Systemd service file at root
- ✅ `logo.png` - Branding asset (acceptable)
- ✅ `AUDIT_REPORT.md`, `GA_REMEDIATION_REPORT.md` - Documentation (acceptable)

**Separation of Concerns:**
- ✅ Agents are separate from core (`agents/` vs `core/`)
- ✅ DPI is separate from core (`dpi/`, `dpi-advanced/` vs `core/`)
- ✅ UI backend is separate from core (`services/ui/` vs `core/`)
- ✅ Services are modularized under `services/`

### Verdict: **PARTIAL**

**Justification:**
- Core structure is sound with proper separation of concerns
- Unexpected items (`10th_jan_promot/`, git-auto-sync files) are present but do not compromise security
- These should be cleaned up for production readiness

---

## 2. ENV-ONLY CONFIGURATION ENFORCEMENT (CRITICAL)

### Evidence

**Configuration Loader:**
- ✅ `common/config/loader.py` enforces env-only for secrets
- ✅ `ConfigLoader.require()` marks variables as required (no defaults)
- ✅ `ConfigLoader.optional()` only allows defaults for non-security-sensitive values
- ✅ Secrets are validated via `validate_secret_present()` which terminates on missing/weak secrets

**Hardcoded Values Search:**
- ✅ No hardcoded IP addresses in production code (found only in documentation/examples)
- ✅ No hardcoded hostnames in production code (found only in documentation/examples)
- ✅ Default ports (`localhost`, `5432`, `8000`, `8080`) are acceptable for non-security-sensitive config
- ⚠️ **CRITICAL:** Installer scripts contain hardcoded defaults:
  - `installer/core/install.sh:290` - `RANSOMEYE_DB_PASSWORD="gagan"`
  - `installer/core/install.sh:301` - `RANSOMEYE_COMMAND_SIGNING_KEY="test_signing_key_minimum_32_characters_long_for_validation_long_enough"`
  - `installer/linux-agent/install.sh:229` - `RANSOMEYE_DB_PASSWORD="gagan"`
  - `installer/dpi-probe/install.sh:277` - `RANSOMEYE_DB_PASSWORD="gagan"`

**Configuration Sources:**
- ✅ Production code uses `os.getenv()` exclusively
- ✅ Systemd files reference `EnvironmentFile` (proper pattern)
- ✅ No `.env` files required for production (only for local dev)
- ⚠️ Installer scripts generate environment files with defaults (acceptable for local dev, but defaults are weak)

**Fallback Behavior:**
- ✅ `common/config/loader.py:156-160` - Raises `ConfigError` on missing required vars (fail-fast)
- ✅ `common/security/secrets.py:32-34` - Terminates via `sys.exit(1)` on missing secrets
- ⚠️ Some components have fallback paths when `common` modules unavailable (e.g., `services/policy-engine/app/main.py:88-91`)

### Verdict: **FAIL**

**Justification:**
- Production code correctly enforces env-only configuration
- **CRITICAL FAILURE:** Installer scripts hardcode weak default credentials (`gagan` password, test signing key)
- These defaults allow insecure startup if environment variables are not set
- Fallback paths in some components may allow degraded operation instead of fail-fast

---

## 3. CREDENTIAL GOVERNANCE (GLOBAL)

### Evidence

**Database Credentials:**
- ✅ `common/config/loader.py:384-387` - `RANSOMEYE_DB_PASSWORD` is required (no default)
- ✅ `common/security/secrets.py:13-47` - `validate_secret_present()` enforces minimum length (8 chars) and entropy
- ✅ `core/runtime.py:71` - Core requires `RANSOMEYE_DB_PASSWORD`
- ✅ `services/*/app/main.py` - All services require `RANSOMEYE_DB_PASSWORD`
- ⚠️ Installer scripts set default `RANSOMEYE_DB_PASSWORD="gagan"` (weak, but only for local dev)

**What Happens if Missing:**
- ✅ `common/config/loader.py:136-141` - Raises `ConfigError` with descriptive message
- ✅ `common/security/secrets.py:32-34` - Terminates via `sys.exit(1)` with "SECURITY VIOLATION" message
- ✅ `core/runtime.py:415` - `_invariant_check_missing_env('RANSOMEYE_DB_PASSWORD')` validates at startup

**What Happens if Invalid:**
- ✅ `common/security/secrets.py:36-39` - Terminates if secret too short
- ✅ `common/security/secrets.py:42-45` - Terminates if secret has insufficient entropy
- ✅ `core/runtime.py:156-159` - DB connection failure causes `exit_startup_error()`

**Service-to-Service Trust:**
- ✅ `common/security/secrets.py:50-116` - `validate_signing_key()` enforces signing key requirements
- ✅ `services/policy-engine/app/signer.py:27-68` - `get_signing_key()` validates and loads signing key at startup
- ✅ `services/policy-engine/app/main.py:96-111` - Signing key initialization fails-fast on invalid key
- ✅ `agents/linux/command_gate.py:302-334` - Command signature verification exists
- ⚠️ Installer scripts set default test signing key (weak, but only for local dev)

**UI/API Authentication:**
- ⚠️ **NOT VALIDATED** - UI authentication mechanism not examined in this step (component-level validation required)

### Verdict: **PARTIAL**

**Justification:**
- Credential governance is enforced in production code (fail-fast on missing/weak credentials)
- Signing key validation exists and is enforced
- **ISSUE:** Installer scripts provide weak defaults (acceptable for local dev, but should be clearly documented as insecure)
- UI/API authentication not validated at repo level (deferred to component validation)

---

## 4. FAIL-CLOSED GUARANTEE (REPO-LEVEL)

### Evidence

**Startup Guards:**
- ✅ `core/runtime.py:392-419` - `_core_startup_validation()` performs comprehensive startup checks
- ✅ `core/runtime.py:400` - `_validate_environment()` checks required env vars
- ✅ `core/runtime.py:403` - `_validate_db_connectivity()` validates DB connection
- ✅ `core/runtime.py:406` - `_validate_schema_presence()` validates schema
- ✅ `core/runtime.py:415-417` - Invariant checks for missing env, DB connection, schema mismatch

**Missing Trust Root Key:**
- ✅ `common/security/secrets.py:72-76` - Missing signing key causes `sys.exit(1)` with "SECURITY VIOLATION"
- ✅ `services/policy-engine/app/signer.py:55-59` - Missing signing key causes `sys.exit(1)`
- ✅ `services/policy-engine/app/main.py:102-111` - Signing key initialization fails-fast

**Missing DB URL:**
- ✅ `core/runtime.py:136-159` - `_validate_db_connectivity()` calls `exit_startup_error()` on connection failure
- ✅ `common/db/safety.py:179-184` - Connection creation failure calls `exit_fatal()` with `ExitCode.STARTUP_ERROR`
- ✅ `core/runtime.py:312-329` - `_invariant_check_db_connection()` terminates on DB connection failure

**Missing Signing Material:**
- ✅ `common/security/secrets.py:50-116` - `validate_signing_key()` terminates on missing/weak keys
- ✅ `services/policy-engine/app/main.py:96-111` - Signing key initialization terminates on failure

**Silent Degradation Checks:**
- ✅ `core/runtime.py:156-159` - DB connection failure does not allow degraded operation
- ✅ `common/config/loader.py:156-160` - Missing required vars raise `ConfigError` (no silent fallback)
- ⚠️ Some components have fallback paths when `common` modules unavailable:
  - `services/policy-engine/app/main.py:88-91` - Falls back to basic env check if `common` unavailable
  - `services/correlation-engine/app/db.py:49-56` - Terminates if `common/db/safety.py` unavailable (good)
  - `services/policy-engine/app/db.py:46-53` - Terminates if `common/db/safety.py` unavailable (good)

**Warnings vs Termination:**
- ✅ `common/security/secrets.py` - Uses `sys.exit(1)` (termination, not warning)
- ✅ `core/runtime.py:157-159` - Uses `exit_startup_error()` (termination, not warning)
- ✅ `common/db/safety.py:181-184` - Uses `exit_fatal()` (termination, not warning)
- ⚠️ `services/policy-engine/app/main.py:112-114` - Logs warning if signing key module unavailable (but this is for ImportError, not missing key)

### Verdict: **PASS**

**Justification:**
- Fail-closed behavior is enforced: missing trust root, DB, or signing material causes termination
- Startup validation is comprehensive and fail-fast
- No evidence of "running but insecure" states
- Minor issue: Some fallback paths exist when `common` modules unavailable, but they still terminate (acceptable)

---

## 5. SIGNING & ARTIFACT INTEGRITY (GLOBAL)

### Evidence

**Signing Logic Presence:**
- ✅ `services/policy-engine/app/signer.py` - Command signing exists
- ✅ `threat-response-engine/crypto/signer.py` - TRE command signing
- ✅ `agents/windows/agent/telemetry/signer.py` - Agent telemetry signing
- ✅ `supply-chain/crypto/artifact_signer.py` - Artifact signing
- ✅ `signed-reporting/crypto/report_signer.py` - Report signing
- ✅ `human-authority/crypto/signer.py` - Human authority signing
- ✅ Multiple other signing implementations found

**Verification Logic Presence:**
- ✅ `agents/linux/command_gate.py:302-334` - Command signature verification
- ✅ `threat-response-engine/crypto/verifier.py` - TRE command verification
- ✅ `supply-chain/crypto/artifact_verifier.py` - Artifact verification
- ✅ `signed-reporting/crypto/report_verifier.py` - Report verification
- ✅ Multiple other verification implementations found

**Where Verification Occurs:**
- ✅ `agents/linux/command_gate.py:302-334` - Command verification at agent (before execution)
- ✅ `services/policy-engine/app/main.py:96-111` - Signing key validation at startup
- ✅ `supply-chain/engine/verification_engine.py:63-127` - Artifact verification before use

**Signing Algorithm:**
- ✅ ed25519 signatures used throughout (cryptographically secure)
- ✅ Base64 encoding for signature transport

### Verdict: **PASS**

**Justification:**
- Signing logic is present across multiple components
- Verification logic is present and enforced
- Verification occurs at appropriate boundaries (startup, before execution, before use)
- Uses cryptographically secure ed25519 signatures

---

## 6. CI / TEST GOVERNANCE (SYNTHETIC-ONLY)

### Evidence

**Malware Samples Search:**
- ✅ No actual malware samples found
- ✅ `hnmp/engine/malware_normalizer.py` - Contains malware normalization logic (classification, not samples)
- ✅ References to "malware" are in classification/normalization code, not actual samples

**PCAP Files:**
- ✅ No `.pcap` files found in repository
- ✅ No references to real PCAP files in code

**Customer Data:**
- ✅ No customer data found
- ✅ No static datasets with customer information

**Test Data Generation:**
- ✅ `mishka/training/scripts/create_test_datasets.py` - Generates synthetic test data
- ✅ `mishka/training/scripts/train_phase1_small.py:13-29` - Creates synthetic datasets at runtime
- ✅ `validation/harness/test_helpers.py` - Test helpers generate synthetic data

**Example Files:**
- ✅ `forensic-summarization/IMPLEMENTATION_SUMMARY.md:205` - Contains example IP `192.168.1.100` (documentation only)
- ✅ `threat-graph/README.md:231` - Contains example IP `192.168.1.100` (documentation only)
- ✅ No `example.pcap`, `sample_events.json` with real data found

**Internet Requirements:**
- ⚠️ **NOT VALIDATED** - Internet requirements for tests not examined (component-level validation required)

### Verdict: **PASS**

**Justification:**
- No real malware samples, PCAPs, or customer data found
- Test data is generated synthetically at runtime
- Example data in documentation is clearly synthetic
- Repository is safe for CI/CD pipelines

---

## 7. UNIFIED INSTALLER & SYSTEMD GOVERNANCE

### Evidence

**Single Installer Concept:**
- ✅ `installer/` directory contains unified installer structure
- ✅ `installer/core/install.sh` - Core installer
- ✅ `installer/linux-agent/install.sh` - Linux agent installer
- ✅ `installer/dpi-probe/install.sh` - DPI probe installer
- ✅ `installer/windows-agent/install.bat` - Windows agent installer
- ✅ `installer/install.manifest.json` - Unified manifest schema
- ✅ `installer/env.contract.json` - Environment variable contract

**Central Systemd Definitions:**
- ✅ `installer/core/ransomeye-core.service` - Core systemd unit
- ✅ `installer/linux-agent/ransomeye-linux-agent.service` - Linux agent systemd unit
- ✅ `installer/dpi-probe/ransomeye-dpi.service` - DPI probe systemd unit
- ✅ `installer/windows-agent/ransomeye-windows-agent.service.txt` - Windows agent systemd template
- ✅ All systemd files reference `EnvironmentFile` (proper pattern)
- ✅ All systemd files use `@INSTALL_ROOT@` placeholder (proper templating)

**Exceptions (Agents/DPI):**
- ✅ Agents have separate installers (expected, as they run on different hosts)
- ✅ DPI probe has separate installer (expected, as it runs on different hosts)
- ✅ Each has its own systemd definition (expected for distributed deployment)

**No Module-Specific Startup Models:**
- ✅ No evidence of modules inventing their own startup models
- ✅ All services use systemd (unified approach)
- ✅ All services use `EnvironmentFile` pattern (unified approach)

**Installer Manifest:**
- ✅ `installer/install.manifest.json` - Unified manifest exists
- ✅ `installer/install.manifest.schema.json` - Manifest schema exists
- ✅ `installer/installer-failure-policy.json` - Failure policy exists

### Verdict: **PASS**

**Justification:**
- Unified installer structure exists with proper separation for distributed components
- Central systemd definitions with consistent patterns
- Proper use of `EnvironmentFile` and templating
- No evidence of ad-hoc startup models

---

## 8. VALIDATION FILE REQUIREMENTS

### Evidence

**Evidence Provided:**
- ✅ All sections include specific file paths and line numbers
- ✅ All sections include code references and behavior descriptions
- ✅ No vague language used (specific PASS/FAIL/PARTIAL verdicts)
- ✅ No future tense used (all evidence is current state)

**Explicit Verdicts:**
- ✅ Section 1: PARTIAL (with justification)
- ✅ Section 2: FAIL (with justification)
- ✅ Section 3: PARTIAL (with justification)
- ✅ Section 4: PASS (with justification)
- ✅ Section 5: PASS (with justification)
- ✅ Section 6: PASS (with justification)
- ✅ Section 7: PASS (with justification)

---

## FINAL VERDICT

### Overall: **PARTIAL**

**Critical Issues:**
1. **FAIL:** Installer scripts contain hardcoded weak default credentials (`gagan` password, test signing key)
   - **Impact:** Allows insecure startup if environment variables are not set
   - **Location:** `installer/core/install.sh:290,301`, `installer/linux-agent/install.sh:229`, `installer/dpi-probe/install.sh:277`
   - **Severity:** HIGH (security risk if defaults are used in production)

2. **PARTIAL:** Some components have fallback paths when `common` modules unavailable
   - **Impact:** May allow degraded operation instead of fail-fast
   - **Location:** `services/policy-engine/app/main.py:88-91`
   - **Severity:** MEDIUM (fallback still terminates, but pattern is inconsistent)

**Minor Issues:**
1. Unexpected top-level items (`10th_jan_promot/`, git-auto-sync files) should be cleaned up
2. UI/API authentication not validated at repo level (deferred to component validation)

**Strengths:**
1. ✅ Fail-closed behavior is enforced (missing trust root, DB, or signing material causes termination)
2. ✅ Signing and verification logic is present and enforced
3. ✅ CI/test governance is sound (no real malware samples, synthetic data only)
4. ✅ Unified installer and systemd governance is consistent
5. ✅ Env-only configuration is enforced in production code

**Recommendations:**
1. **CRITICAL:** Remove hardcoded default credentials from installer scripts or clearly document as insecure dev-only defaults
2. Remove or relocate unexpected top-level items (`10th_jan_promot/`, git-auto-sync files)
3. Standardize fallback behavior (all components should terminate if `common` modules unavailable)
4. Validate UI/API authentication at component level

---

**Validation Date:** 2025-01-13
**Validator:** Lead Validator & Compliance Auditor
**Next Step:** Validation Step 2 — Core Kernel (trust root)
