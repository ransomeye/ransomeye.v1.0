# Validation Step 13 — Installer, Bootstrap & Systemd Orchestration

**Component Identity:**
- **Name:** Unified Installer & Bootstrap Layer
- **Primary Paths:**
  - `/home/ransomeye/rebuild/installer/core/install.sh` - Core installer script
  - `/home/ransomeye/rebuild/installer/linux-agent/install.sh` - Linux agent installer script
  - `/home/ransomeye/rebuild/installer/dpi-probe/install.sh` - DPI probe installer script
  - `/home/ransomeye/rebuild/installer/windows-agent/install.bat` - Windows agent installer script
  - `/home/ransomeye/rebuild/installer/core/ransomeye-core.service` - Core systemd unit
  - `/home/ransomeye/rebuild/installer/linux-agent/ransomeye-linux-agent.service` - Linux agent systemd unit
  - `/home/ransomeye/rebuild/installer/dpi-probe/ransomeye-dpi.service` - DPI probe systemd unit
- **Entry Points:**
  - Core installer: `installer/core/install.sh:773-836` - `main()` function
  - Linux agent installer: `installer/linux-agent/install.sh:356-396` - `main()` function
  - DPI probe installer: `installer/dpi-probe/install.sh:413-456` - `main()` function
  - Windows agent installer: `installer/windows-agent/install.bat` - Batch script

**Master Spec References:**
- Installer Bundle (`installer/INSTALLER_BUNDLE.md`)
- Environment Variable Contract (`installer/env.contract.md`, `installer/env.contract.json`)
- Installer Failure Policy (`installer/installer-failure-policy.md`, `installer/installer-failure-policy.json`)
- Privilege Model (`installer/privilege-model.md`)
- Validation Step 1: `validation/01-governance-repo-level.md` - Credential governance (binding)
- Validation Step 2: `validation/02-core-kernel-trust-root.md` - Trust root validation (binding)
- Validation Step 3: `validation/03-secure-bus-interservice-trust.md` - Inter-service trust (binding)

---

## PURPOSE

This validation proves that installation and bootstrap:

1. **Enforce same security guarantees as runtime** — Installer does not introduce weaker trust boundaries than runtime components
2. **Are fail-closed** — Installation fails immediately on any security violation, missing credential, or invalid configuration
3. **Do not introduce weaker trust boundaries** — Installer-generated credentials meet same strength requirements as runtime validation
4. **Enforce SBOM at install time** — Installation cannot proceed without validated SBOM manifest
5. **Enforce systemd hardening** — systemd units use capabilities, sandboxing, and least-privilege execution

This validation does NOT validate threat logic, correlation, or AI. This validation validates installer and bootstrap security guarantees only.

---

## MASTER SPEC REFERENCES

- **Installer Bundle:** `installer/INSTALLER_BUNDLE.md` - Authoritative installer specification
- **Environment Variable Contract:** `installer/env.contract.json` - Required environment variables
- **Installer Failure Policy:** `installer/installer-failure-policy.json` - Fail-closed behavior requirements
- **Privilege Model:** `installer/privilege-model.md` - Runtime user and capability requirements

---

## COMPONENT DEFINITION

**Installer Components:**
- Core installer: `installer/core/install.sh` - Installs Core runtime and services
- Linux agent installer: `installer/linux-agent/install.sh` - Installs standalone Linux agent
- DPI probe installer: `installer/dpi-probe/install.sh` - Installs standalone DPI probe
- Windows agent installer: `installer/windows-agent/install.bat` - Installs standalone Windows agent

**Bootstrap Components:**
- Environment file generation: `installer/core/install.sh:388-445` - `generate_environment_file()` function
- Manifest generation: `installer/core/install.sh:505-613` - `create_manifest()` function
- systemd service installation: `installer/core/install.sh:481-504` - `install_systemd_service()` function

**Systemd Units:**
- Core systemd unit: `installer/core/ransomeye-core.service` - Core runtime service
- Linux agent systemd unit: `installer/linux-agent/ransomeye-linux-agent.service` - Linux agent service
- DPI probe systemd unit: `installer/dpi-probe/ransomeye-dpi.service` - DPI probe service

---

## WHAT IS VALIDATED

1. **SBOM Enforcement at Install Time** — Installer verifies SBOM manifest and signature before proceeding
2. **Credential Handling** — No hardcoded secrets, no weak defaults, all credentials from environment
3. **Privilege Model** — Installer runs as root, runtime drops to service user
4. **systemd Unit Hardening** — Capabilities, sandboxing, resource limits, restart policies
5. **Installer vs Runtime Parity** — Installer enforces same security guarantees as runtime
6. **Re-runnability & Idempotence** — Installer can be run multiple times safely

---

## WHAT IS EXPLICITLY NOT ASSUMED

- **NOT ASSUMED:** That installer defaults are acceptable (they are validated as insecure)
- **NOT ASSUMED:** That fallback paths are secure (they are validated for fail-closed behavior)
- **NOT ASSUMED:** That services start correctly after installation (validation checks actual startup)
- **NOT ASSUMED:** That systemd units are hardened (they are validated for capabilities and sandboxing)
- **NOT ASSUMED:** That SBOM verification is enforced (it is validated for mandatory enforcement)
- **NOT ASSUMED:** That credentials meet strength requirements (they are validated against runtime requirements)

---

## VALIDATION METHODOLOGY

### Evidence Collection Strategy

1. **Code Path Analysis:** Trace installer execution flow, credential generation, SBOM verification
2. **Pattern Matching:** Search for hardcoded credentials, weak defaults, missing validation
3. **systemd Unit Analysis:** Verify capabilities, sandboxing, resource limits, restart policies
4. **Schema Validation:** Verify manifest validation against schema
5. **Failure Behavior Analysis:** Verify fail-closed behavior on security violations

### Forbidden Patterns (Grep Validation)

- `RANSOMEYE_DB_PASSWORD.*=.*["']` — Hardcoded DB password
- `RANSOMEYE_COMMAND_SIGNING_KEY.*=.*["']` — Hardcoded signing key
- `password.*=.*["']` — Hardcoded password (context-dependent)
- `key.*=.*["']` — Hardcoded key (context-dependent)

---

## 1. SBOM ENFORCEMENT AT INSTALL TIME

### Evidence

**SBOM Verification Before Installation:**
- ✅ SBOM verification function: `installer/core/install.sh:99-169` - `verify_sbom()` function
- ✅ SBOM verification called: `installer/core/install.sh:795` - `verify_sbom()` called before installation
- ✅ Manifest file required: `installer/core/install.sh:112-114` - Terminates if `manifest.json` not found
- ✅ Signature file required: `installer/core/install.sh:116-118` - Terminates if `manifest.json.sig` not found
- ✅ Verification script required: `installer/core/install.sh:130` - Terminates if `verify_sbom.py` not found
- ✅ Verification failure terminates: `installer/core/install.sh:166` - Terminates on SBOM verification failure

**SBOM Verification Skipped:**
- ❌ **CRITICAL:** SBOM verification can be skipped:
  - `installer/linux-agent/install.sh` - No SBOM verification found
  - `installer/dpi-probe/install.sh` - No SBOM verification found
  - `installer/windows-agent/install.bat` - No SBOM verification found
  - ❌ **CRITICAL:** SBOM verification not enforced for all installers (only Core installer enforces SBOM)

**SBOM Verification Warnings Instead of Termination:**
- ✅ **VERIFIED:** SBOM verification does NOT use warnings:
  - `installer/core/install.sh:112-114` - `error_exit` on missing manifest (terminates, not warning)
  - `installer/core/install.sh:116-118` - `error_exit` on missing signature (terminates, not warning)
  - `installer/core/install.sh:166` - `error_exit` on verification failure (terminates, not warning)
  - ✅ **VERIFIED:** SBOM verification terminates on failure (no warnings, fail-closed)

### Verdict: **PARTIAL**

**Justification:**
- Core installer enforces SBOM verification before installation (manifest and signature required, verification script required, terminates on failure)
- SBOM verification terminates on failure (no warnings, fail-closed behavior)
- **CRITICAL:** SBOM verification not enforced for all installers (Linux agent, DPI probe, Windows agent installers do not verify SBOM)

---

## 2. CREDENTIAL HANDLING (NO HARDCODED SECRETS, NO WEAK DEFAULTS)

### Evidence

**No Hardcoded Credentials:**
- ❌ **CRITICAL:** Hardcoded weak credentials found:
  - `installer/core/install.sh:424-425` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (hardcoded weak credentials)
  - `installer/core/install.sh:436` - `RANSOMEYE_COMMAND_SIGNING_KEY="test_signing_key_minimum_32_characters_long_for_validation_long_enough"` (hardcoded weak default key)
  - `installer/linux-agent/install.sh:228-229` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (hardcoded weak credentials)
  - `installer/dpi-probe/install.sh:276-277` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (hardcoded weak credentials)
  - ❌ **CRITICAL:** Hardcoded weak credentials (DB user/password "gagan", test signing key)

**No Default Passwords or Signing Keys:**
- ❌ **CRITICAL:** Default passwords and signing keys found:
  - `installer/core/install.sh:424-425` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (default weak credentials)
  - `installer/core/install.sh:436` - `RANSOMEYE_COMMAND_SIGNING_KEY="test_signing_key_minimum_32_characters_long_for_validation_long_enough"` (default weak signing key)
  - `installer/linux-agent/install.sh:228-229` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (default weak credentials)
  - `installer/dpi-probe/install.sh:276-277` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (default weak credentials)
  - ❌ **CRITICAL:** Default passwords and signing keys (DB user/password "gagan", test signing key)

**Environment Variables Required for All Secrets:**
- ⚠️ **ISSUE:** Secrets are hardcoded, not from environment:
  - `installer/core/install.sh:424-425` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (hardcoded, not from environment)
  - `installer/core/install.sh:436` - `RANSOMEYE_COMMAND_SIGNING_KEY="test_signing_key_minimum_32_characters_long_for_validation_long_enough"` (hardcoded, not from environment)
  - ⚠️ **ISSUE:** Secrets are hardcoded, not from environment (DB user/password and signing key are hardcoded)

**Secrets Not Written to World-Readable Files:**
- ✅ Environment file permissions: `installer/core/install.sh:442` - `chmod 600 "${INSTALL_ROOT}/config/environment"` (600 = owner read/write only)
- ✅ Environment file ownership: `installer/core/install.sh:443` - `chown ransomeye:ransomeye "${INSTALL_ROOT}/config/environment"` (restricted ownership)
- ✅ Manifest file permissions: `installer/core/install.sh:612` - `chmod 644 "$manifest_file"` (644 = owner/group read, world read)
- ⚠️ **ISSUE:** Manifest file is world-readable:
  - `installer/core/install.sh:612` - `chmod 644 "$manifest_file"` (644 = world-readable)
  - ⚠️ **ISSUE:** Manifest file is world-readable (644 permissions, world-readable)

**Credential Strength Validation:**
- ❌ **CRITICAL:** Installer does NOT validate credential strength:
  - `installer/core/install.sh:424-425` - Weak password `"gagan"` (4 chars, insufficient entropy) accepted without validation
  - `installer/core/install.sh:436` - Weak default signing key accepted without validation
  - ❌ **CRITICAL:** Installer does NOT validate credential strength (weak credentials accepted without validation)

### Verdict: **FAIL**

**Justification:**
- Environment file permissions are correct (600 = owner read/write only)
- Environment file ownership is correct (restricted ownership)
- **CRITICAL:** Hardcoded weak credentials (DB user/password "gagan", test signing key)
- **CRITICAL:** Default passwords and signing keys (DB user/password "gagan", test signing key)
- **CRITICAL:** Installer does NOT validate credential strength (weak credentials accepted without validation)
- **ISSUE:** Secrets are hardcoded, not from environment (DB user/password and signing key are hardcoded)
- **ISSUE:** Manifest file is world-readable (644 permissions, world-readable)

---

## 3. PRIVILEGE MODEL (ROOT VS SERVICE USER)

### Evidence

**Installer Runs as Root:**
- ✅ Root check: `installer/core/install.sh:26-31` - `check_root()` function verifies `$EUID -ne 0`
- ✅ Root check called: `installer/core/install.sh:777` - `check_root()` called in `main()`
- ✅ Root required for systemd: `installer/core/install.sh:29` - Error message states "required for systemd service and user creation"

**Runtime Drops to Service User:**
- ✅ Systemd unit user: `installer/core/ransomeye-core.service:9` - `User=ransomeye`
- ✅ Systemd unit group: `installer/core/ransomeye-core.service:10` - `Group=ransomeye`
- ✅ Service user created: `installer/core/install.sh:109-114` - `create_system_user()` function creates `ransomeye` user
- ✅ Service user created before files: `installer/core/install.sh:792` - `create_system_user()` called before `install_python_files()`

**No Privilege Escalation:**
- ✅ NoNewPrivileges: `installer/core/ransomeye-core.service:28` - `NoNewPrivileges=true`
- ✅ No setuid/setgid: `installer/core/install.sh:373` - `chmod +x` (no setuid/setgid bits)
- ✅ **VERIFIED:** No privilege escalation (NoNewPrivileges=true, no setuid/setgid bits)

### Verdict: **PASS**

**Justification:**
- Installer runs as root (root check enforced, root required for systemd and user creation)
- Runtime drops to service user (systemd unit specifies User=ransomeye, Group=ransomeye, service user created before files)
- No privilege escalation (NoNewPrivileges=true, no setuid/setgid bits)

---

## 4. SYSTEMD UNIT HARDENING (CAPABILITIES, SANDBOXING)

### Evidence

**Capabilities:**
- ⚠️ **ISSUE:** Core systemd unit has no capabilities:
  - `installer/core/ransomeye-core.service:1-45` - No `CapabilityBoundingSet` or `AmbientCapabilities` directives
  - ⚠️ **ISSUE:** Core systemd unit has no capabilities (no capability restrictions)
- ✅ DPI probe capabilities: `installer/dpi-probe/ransomeye-dpi.service:17-19` - Comments state "CAP_NET_RAW and CAP_NET_ADMIN capabilities set via setcap"
- ⚠️ **ISSUE:** DPI probe capabilities not in systemd unit:
  - `installer/dpi-probe/ransomeye-dpi.service:1-63` - No `CapabilityBoundingSet` or `AmbientCapabilities` directives
  - ⚠️ **ISSUE:** DPI probe capabilities not in systemd unit (capabilities set via setcap, not systemd)

**Sandboxing:**
- ✅ NoNewPrivileges: `installer/core/ransomeye-core.service:28` - `NoNewPrivileges=true`
- ✅ PrivateTmp: `installer/core/ransomeye-core.service:29` - `PrivateTmp=true`
- ✅ ProtectSystem: `installer/core/ransomeye-core.service:30` - `ProtectSystem=strict`
- ✅ ProtectHome: `installer/core/ransomeye-core.service:31` - `ProtectHome=true`
- ✅ ReadWritePaths: `installer/core/ransomeye-core.service:32` - `ReadWritePaths=@INSTALL_ROOT@/logs @INSTALL_ROOT@/runtime`
- ✅ Linux agent sandboxing: `installer/linux-agent/ransomeye-linux-agent.service:35-39` - Same sandboxing directives
- ✅ DPI probe sandboxing: `installer/dpi-probe/ransomeye-dpi.service:40-44` - Same sandboxing directives

**Resource Limits:**
- ✅ LimitNOFILE: `installer/core/ransomeye-core.service:24` - `LimitNOFILE=65536`
- ✅ LimitNPROC: `installer/core/ransomeye-core.service:25` - `LimitNPROC=4096`
- ✅ Linux agent limits: `installer/linux-agent/ransomeye-linux-agent.service:31-32` - Same limits
- ✅ DPI probe limits: `installer/dpi-probe/ransomeye-dpi.service:33-34` - Same limits

**Restart Policies:**
- ✅ Restart on failure: `installer/core/ransomeye-core.service:20` - `Restart=on-failure`
- ✅ Restart delay: `installer/core/ransomeye-core.service:21` - `RestartSec=10`
- ⚠️ **ISSUE:** Core has no restart limits:
  - `installer/core/ransomeye-core.service:20-21` - `Restart=on-failure`, `RestartSec=10` (but no restart limits found)
  - ⚠️ **ISSUE:** Core has no restart limits (may restart indefinitely)
- ✅ Linux agent restart limits: `installer/linux-agent/ransomeye-linux-agent.service:26-28` - `StartLimitIntervalSec=300`, `StartLimitBurst=5`, `StartLimitAction=none`
- ✅ DPI probe restart limits: `installer/dpi-probe/ransomeye-dpi.service:28-30` - `StartLimitIntervalSec=300`, `StartLimitBurst=5`, `StartLimitAction=none`
- ⚠️ **ISSUE:** Restart limits use `StartLimitAction=none`:
  - `installer/linux-agent/ransomeye-linux-agent.service:30` - `StartLimitAction=none` (may allow restart loops)
  - `installer/dpi-probe/ransomeye-dpi.service:30` - `StartLimitAction=none` (may allow restart loops)
  - ⚠️ **ISSUE:** Restart limits use `StartLimitAction=none` (may allow restart loops)

**Dependency Ordering:**
- ✅ Core dependencies: `installer/core/ransomeye-core.service:4-5` - `After=network.target postgresql.service`, `Wants=postgresql.service`
- ✅ Linux agent dependencies: `installer/linux-agent/ransomeye-linux-agent.service:4-5` - `After=network.target`, `Wants=network-online.target`
- ✅ DPI probe dependencies: `installer/dpi-probe/ransomeye-dpi.service:4-5` - `After=network.target`, `Wants=network-online.target`
- ⚠️ **ISSUE:** Core has `Wants` instead of `Requires`:
  - `installer/core/ransomeye-core.service:5` - `Wants=postgresql.service` (Wants = soft dependency, not hard dependency)
  - ⚠️ **ISSUE:** Core has `Wants` instead of `Requires` (Wants = soft dependency, PostgreSQL may not be available)

### Verdict: **PARTIAL**

**Justification:**
- Sandboxing exists (NoNewPrivileges=true, PrivateTmp=true, ProtectSystem=strict, ProtectHome=true, ReadWritePaths restricted)
- Resource limits exist (LimitNOFILE=65536, LimitNPROC=4096)
- Restart policies exist (Restart=on-failure, RestartSec=10/60)
- Dependency ordering exists (After=network.target, Wants=postgresql.service/network-online.target)
- **ISSUE:** Core systemd unit has no capabilities (no capability restrictions)
- **ISSUE:** DPI probe capabilities not in systemd unit (capabilities set via setcap, not systemd)
- **ISSUE:** Core has no restart limits (may restart indefinitely)
- **ISSUE:** Restart limits use `StartLimitAction=none` (may allow restart loops)
- **ISSUE:** Core has `Wants` instead of `Requires` (Wants = soft dependency, PostgreSQL may not be available)

---

## 5. INSTALLER VS RUNTIME PARITY

### Evidence

**Runtime Credential Validation:**
- ✅ Runtime validates secrets: `common/security/secrets.py:32-34` - `sys.exit(1)` on missing secrets
- ✅ Runtime validates password strength: `common/security/secrets.py:36-39` - Minimum 8 characters enforced
- ✅ Runtime validates signing key strength: `common/security/secrets.py:98-101` - Minimum 32 characters enforced

**Installer Credential Validation:**
- ❌ **CRITICAL:** Installer does NOT validate credentials:
  - `installer/core/install.sh:424-425` - Weak password `"gagan"` (4 chars, insufficient entropy) accepted without validation
  - `installer/core/install.sh:436` - Weak default signing key accepted without validation
  - ❌ **CRITICAL:** Installer does NOT validate credentials (weak credentials accepted without validation)

**Runtime Fail-Closed Behavior:**
- ✅ Runtime terminates on missing secrets: `common/security/secrets.py:32-34` - `sys.exit(1)` with "SECURITY VIOLATION" message
- ✅ Runtime terminates on weak secrets: `common/security/secrets.py:36-39` - Terminates if too short

**Installer Fail-Closed Behavior:**
- ✅ Installer terminates on errors: `installer/core/install.sh:8` - `set -euo pipefail` (fail-fast)
- ✅ Installer terminates on SBOM failure: `installer/core/install.sh:166` - `error_exit` on SBOM verification failure
- ❌ **CRITICAL:** Installer does NOT terminate on weak credentials:
  - `installer/core/install.sh:424-425` - Weak password `"gagan"` accepted without validation
  - `installer/core/install.sh:436` - Weak default signing key accepted without validation
  - ❌ **CRITICAL:** Installer does NOT terminate on weak credentials (weak credentials accepted without validation)

### Verdict: **FAIL**

**Justification:**
- Runtime validates credentials (terminates on missing/weak secrets, enforces password and signing key strength)
- Installer terminates on errors (set -euo pipefail, terminates on SBOM failure)
- **CRITICAL:** Installer does NOT validate credentials (weak credentials accepted without validation)
- **CRITICAL:** Installer does NOT terminate on weak credentials (weak credentials accepted without validation)
- **CRITICAL:** Installer bypasses runtime validation by hardcoding weak defaults

---

## 6. RE-RUNNABILITY & IDEMPOTENCE

### Evidence

**Idempotent Directory Creation:**
- ✅ Directory creation checks: `installer/core/install.sh:95-101` - Checks if directory exists before creating
- ✅ Directory creation skips if exists: `installer/core/install.sh:97` - `mkdir -p` (idempotent)

**Idempotent User Creation:**
- ✅ User creation checks: `installer/core/install.sh:109-114` - Checks if user exists before creating
- ✅ User creation skips if exists: `installer/core/install.sh:111` - `id -u ransomeye` check (skips if exists)

**Idempotent File Installation:**
- ✅ File installation overwrites: `installer/core/install.sh:122-161` - `cp` commands overwrite existing files
- ✅ File installation idempotent: `installer/core/install.sh:122-161` - Same files installed on re-run

**Idempotent systemd Service Installation:**
- ✅ systemd service overwrites: `installer/core/install.sh:481-504` - `cp` command overwrites existing service file
- ✅ systemd daemon-reload: `installer/core/install.sh:500` - `systemctl daemon-reload` called after installation

**Idempotent Manifest Generation:**
- ✅ Manifest generation overwrites: `installer/core/install.sh:505-613` - Manifest file overwritten on re-run
- ✅ Manifest validation: `installer/core/install.sh:617-661` - `validate_manifest()` validates generated manifest

### Verdict: **PASS**

**Justification:**
- Idempotent directory creation (checks if exists, skips if exists)
- Idempotent user creation (checks if exists, skips if exists)
- Idempotent file installation (overwrites existing files, same files installed on re-run)
- Idempotent systemd service installation (overwrites existing service file, daemon-reload called)
- Idempotent manifest generation (manifest file overwritten on re-run, manifest validated)

---

## 7. MANIFEST VALIDATION

### Evidence

**Manifest Validation Function:**
- ✅ Manifest validation function: `installer/core/install.sh:617-661` - `validate_manifest()` function
- ✅ Manifest validation called: `installer/core/install.sh:821` - `validate_manifest()` called after manifest creation
- ✅ Schema file check: `installer/core/install.sh:628-631` - Checks if schema file exists
- ✅ Schema validation: `installer/core/install.sh:635-654` - Validates manifest against schema using `jsonschema`

**Manifest Validation Skipped:**
- ⚠️ **ISSUE:** Manifest validation can be skipped:
  - `installer/core/install.sh:628-631` - Skips validation if schema file not found (warning only)
  - `installer/core/install.sh:655-657` - Skips validation if `jsonschema` not available (warning only)
  - `installer/core/install.sh:658-660` - Skips validation if Python3 not available (warning only)
  - ⚠️ **ISSUE:** Manifest validation can be skipped (warnings instead of termination)

**Manifest Validation Failure:**
- ✅ Validation failure terminates: `installer/core/install.sh:653` - `error_exit` on validation failure
- ✅ **VERIFIED:** Manifest validation failure terminates (no warnings, fail-closed)

### Verdict: **PARTIAL**

**Justification:**
- Manifest validation function exists (validates manifest against schema using jsonschema)
- Manifest validation called after manifest creation
- Manifest validation failure terminates (no warnings, fail-closed)
- **ISSUE:** Manifest validation can be skipped (warnings instead of termination if schema file, jsonschema, or Python3 not available)

---

## 8. NEGATIVE VALIDATION (MANDATORY)

### Evidence

**System Starts Without Validated Manifest:**
- ⚠️ **ISSUE:** System may start without validated manifest:
  - `installer/core/install.sh:628-631` - Manifest validation skipped if schema file not found (warning only)
  - `installer/core/install.sh:655-657` - Manifest validation skipped if `jsonschema` not available (warning only)
  - `installer/core/install.sh:658-660` - Manifest validation skipped if Python3 not available (warning only)
  - ⚠️ **ISSUE:** System may start without validated manifest (manifest validation can be skipped)

**System Starts with Default Credentials:**
- ❌ **CRITICAL:** System starts with default credentials:
  - `installer/core/install.sh:424-425` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (default weak credentials)
  - `installer/core/install.sh:436` - `RANSOMEYE_COMMAND_SIGNING_KEY="test_signing_key_minimum_32_characters_long_for_validation_long_enough"` (default weak signing key)
  - ❌ **CRITICAL:** System starts with default credentials (DB user/password "gagan", test signing key)

**Partial Services Run Undetected:**
- ⚠️ **ISSUE:** Partial services may run undetected:
  - `installer/core/install.sh:823-853` - `validate_installation()` starts Core and performs health check (but no explicit partial service check found)
  - ⚠️ **ISSUE:** Partial services may run undetected (validation exists, but no explicit partial service check found)

**systemd Masks Fatal Failures:**
- ⚠️ **ISSUE:** systemd may mask fatal failures:
  - `installer/core/ransomeye-core.service:20-21` - `Restart=on-failure`, `RestartSec=10` (but no restart limits found, may restart indefinitely)
  - `installer/linux-agent/ransomeye-linux-agent.service:26-30` - `StartLimitAction=none` (may allow restart loops)
  - `installer/dpi-probe/ransomeye-dpi.service:28-30` - `StartLimitAction=none` (may allow restart loops)
  - ⚠️ **ISSUE:** systemd may mask fatal failures (Core has no restart limits, Linux agent and DPI probe have `StartLimitAction=none`)

### Verdict: **FAIL**

**Justification:**
- **CRITICAL:** System starts with default credentials (DB user/password "gagan", test signing key)
- **ISSUE:** System may start without validated manifest (manifest validation can be skipped)
- **ISSUE:** Partial services may run undetected (validation exists, but no explicit partial service check found)
- **ISSUE:** systemd may mask fatal failures (Core has no restart limits, Linux agent and DPI probe have `StartLimitAction=none`)

---

## 9. VERDICT & IMPACT

### Section-by-Section Verdicts

1. **SBOM Enforcement at Install Time:** PARTIAL
   - Core installer enforces SBOM verification before installation (manifest and signature required, verification script required, terminates on failure)
   - SBOM verification terminates on failure (no warnings, fail-closed behavior)
   - **CRITICAL:** SBOM verification not enforced for all installers (Linux agent, DPI probe, Windows agent installers do not verify SBOM)

2. **Credential Handling:** FAIL
   - Environment file permissions are correct (600 = owner read/write only)
   - Environment file ownership is correct (restricted ownership)
   - **CRITICAL:** Hardcoded weak credentials (DB user/password "gagan", test signing key)
   - **CRITICAL:** Default passwords and signing keys (DB user/password "gagan", test signing key)
   - **CRITICAL:** Installer does NOT validate credential strength (weak credentials accepted without validation)
   - **ISSUE:** Secrets are hardcoded, not from environment (DB user/password and signing key are hardcoded)
   - **ISSUE:** Manifest file is world-readable (644 permissions, world-readable)

3. **Privilege Model:** PASS
   - Installer runs as root (root check enforced, root required for systemd and user creation)
   - Runtime drops to service user (systemd unit specifies User=ransomeye, Group=ransomeye, service user created before files)
   - No privilege escalation (NoNewPrivileges=true, no setuid/setgid bits)

4. **systemd Unit Hardening:** PARTIAL
   - Sandboxing exists (NoNewPrivileges=true, PrivateTmp=true, ProtectSystem=strict, ProtectHome=true, ReadWritePaths restricted)
   - Resource limits exist (LimitNOFILE=65536, LimitNPROC=4096)
   - Restart policies exist (Restart=on-failure, RestartSec=10/60)
   - Dependency ordering exists (After=network.target, Wants=postgresql.service/network-online.target)
   - **ISSUE:** Core systemd unit has no capabilities (no capability restrictions)
   - **ISSUE:** DPI probe capabilities not in systemd unit (capabilities set via setcap, not systemd)
   - **ISSUE:** Core has no restart limits (may restart indefinitely)
   - **ISSUE:** Restart limits use `StartLimitAction=none` (may allow restart loops)
   - **ISSUE:** Core has `Wants` instead of `Requires` (Wants = soft dependency, PostgreSQL may not be available)

5. **Installer vs Runtime Parity:** FAIL
   - Runtime validates credentials (terminates on missing/weak secrets, enforces password and signing key strength)
   - Installer terminates on errors (set -euo pipefail, terminates on SBOM failure)
   - **CRITICAL:** Installer does NOT validate credentials (weak credentials accepted without validation)
   - **CRITICAL:** Installer does NOT terminate on weak credentials (weak credentials accepted without validation)
   - **CRITICAL:** Installer bypasses runtime validation by hardcoding weak defaults

6. **Re-runnability & Idempotence:** PASS
   - Idempotent directory creation (checks if exists, skips if exists)
   - Idempotent user creation (checks if exists, skips if exists)
   - Idempotent file installation (overwrites existing files, same files installed on re-run)
   - Idempotent systemd service installation (overwrites existing service file, daemon-reload called)
   - Idempotent manifest generation (manifest file overwritten on re-run, manifest validated)

7. **Manifest Validation:** PARTIAL
   - Manifest validation function exists (validates manifest against schema using jsonschema)
   - Manifest validation called after manifest creation
   - Manifest validation failure terminates (no warnings, fail-closed)
   - **ISSUE:** Manifest validation can be skipped (warnings instead of termination if schema file, jsonschema, or Python3 not available)

8. **Negative Validation:** FAIL
   - **CRITICAL:** System starts with default credentials (DB user/password "gagan", test signing key)
   - **ISSUE:** System may start without validated manifest (manifest validation can be skipped)
   - **ISSUE:** Partial services may run undetected (validation exists, but no explicit partial service check found)
   - **ISSUE:** systemd may mask fatal failures (Core has no restart limits, Linux agent and DPI probe have `StartLimitAction=none`)

### Overall Verdict: **FAIL**

**Justification:**
- **CRITICAL:** Hardcoded weak credentials (DB user/password "gagan", test signing key in all installer scripts)
- **CRITICAL:** Default passwords and signing keys (DB user/password "gagan", test signing key)
- **CRITICAL:** Installer does NOT validate credential strength (weak credentials accepted without validation)
- **CRITICAL:** Installer bypasses runtime validation by hardcoding weak defaults
- **CRITICAL:** System starts with default credentials (DB user/password "gagan", test signing key)
- **CRITICAL:** SBOM verification not enforced for all installers (Linux agent, DPI probe, Windows agent installers do not verify SBOM)
- **ISSUE:** Secrets are hardcoded, not from environment (DB user/password and signing key are hardcoded)
- **ISSUE:** Manifest file is world-readable (644 permissions, world-readable)
- **ISSUE:** Manifest validation can be skipped (warnings instead of termination if schema file, jsonschema, or Python3 not available)
- **ISSUE:** Core systemd unit has no capabilities (no capability restrictions)
- **ISSUE:** Core has no restart limits (may restart indefinitely)
- **ISSUE:** Restart limits use `StartLimitAction=none` (may allow restart loops)
- **ISSUE:** Core has `Wants` instead of `Requires` (Wants = soft dependency, PostgreSQL may not be available)
- **ISSUE:** Partial services may run undetected (validation exists, but no explicit partial service check found)
- **ISSUE:** systemd may mask fatal failures (Core has no restart limits, Linux agent and DPI probe have `StartLimitAction=none`)
- Environment file permissions are correct (600 = owner read/write only)
- Environment file ownership is correct (restricted ownership)
- Installer runs as root (root check enforced, root required for systemd and user creation)
- Runtime drops to service user (systemd unit specifies User=ransomeye, Group=ransomeye, service user created before files)
- No privilege escalation (NoNewPrivileges=true, no setuid/setgid bits)
- Sandboxing exists (NoNewPrivileges=true, PrivateTmp=true, ProtectSystem=strict, ProtectHome=true, ReadWritePaths restricted)
- Resource limits exist (LimitNOFILE=65536, LimitNPROC=4096)
- Restart policies exist (Restart=on-failure, RestartSec=10/60)
- Dependency ordering exists (After=network.target, Wants=postgresql.service/network-online.target)
- Idempotent directory creation (checks if exists, skips if exists)
- Idempotent user creation (checks if exists, skips if exists)
- Idempotent file installation (overwrites existing files, same files installed on re-run)
- Idempotent systemd service installation (overwrites existing service file, daemon-reload called)
- Idempotent manifest generation (manifest file overwritten on re-run, manifest validated)
- Core installer enforces SBOM verification before installation (manifest and signature required, verification script required, terminates on failure)
- SBOM verification terminates on failure (no warnings, fail-closed behavior)
- Manifest validation function exists (validates manifest against schema using jsonschema)
- Manifest validation called after manifest creation
- Manifest validation failure terminates (no warnings, fail-closed)

**Impact if Installer is Compromised:**
- **CRITICAL:** If installer is compromised, weak default credentials can be installed (DB user/password "gagan", test signing key)
- **CRITICAL:** If installer is compromised, system can start with default credentials (DB user/password "gagan", test signing key)
- **CRITICAL:** If installer is compromised, invalid manifests can be installed (manifest validation can be skipped)
- **CRITICAL:** If installer is compromised, partial installations can occur (no explicit partial service check)
- **HIGH:** If installer is compromised, systemd may mask fatal failures (Core has no restart limits, Linux agent and DPI probe have `StartLimitAction=none`)
- **MEDIUM:** If installer is compromised, manifest file is world-readable (644 permissions, world-readable)
- **LOW:** If installer is compromised, file ownership and permissions remain correct (environment files 600, directories 755, executables +x)
- **LOW:** If installer is compromised, centralized systemd units remain (Core, Linux agent, DPI probe have single systemd units)
- **LOW:** If installer is compromised, correct dependency ordering remains (After=network.target, Wants=postgresql.service/network-online.target)

**Whether Runtime Guarantees Remain Trustworthy:**
- ❌ **FAIL:** Runtime guarantees do NOT remain trustworthy if installer is compromised:
  - Hardcoded weak credentials (DB user/password "gagan", test signing key)
  - Default passwords and signing keys (DB user/password "gagan", test signing key)
  - Installer bypasses runtime validation by hardcoding weak defaults
  - System starts with default credentials (DB user/password "gagan", test signing key)
  - ❌ **FAIL:** Runtime guarantees do NOT remain trustworthy if installer is compromised (critical installer security issues)

---

## UPSTREAM IMPACT STATEMENT

**Binding Results from Validation Files 01-11:**
- Validation Step 1 (`validation/01-governance-repo-level.md`): Credential governance requirements (binding)
- Validation Step 2 (`validation/02-core-kernel-trust-root.md`): Trust root validation (binding)
- Validation Step 3 (`validation/03-secure-bus-interservice-trust.md`): Inter-service trust (binding)

**Upstream Dependencies:**
- Installer requires SBOM manifest and signature from release bundle (upstream dependency)
- Installer requires runtime credential validation utilities (`common/security/secrets.py`) (upstream dependency)
- Installer requires systemd service files (upstream dependency)

**Upstream Failures Impact Installer:**
- If SBOM manifest is invalid, installer terminates (fail-closed)
- If runtime credential validation is missing, installer bypasses validation (security gap)
- If systemd service files are missing, installer terminates (fail-closed)

---

## DOWNSTREAM IMPACT STATEMENT

**Downstream Dependencies:**
- Runtime services depend on installer-generated environment file (downstream dependency)
- Runtime services depend on installer-created system user (downstream dependency)
- Runtime services depend on installer-installed systemd service (downstream dependency)

**Installer Failures Impact Runtime:**
- If installer generates weak credentials, runtime accepts them (security gap)
- If installer does not create system user, runtime fails to start (fail-closed)
- If installer does not install systemd service, runtime cannot start via systemd (fail-closed)

---

**Validation Date:** 2025-01-13
**Validator:** Lead Validator & Compliance Auditor
**GA Verdict:** **FAIL**
