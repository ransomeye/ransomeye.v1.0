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
  - `/home/ransomeye/rebuild/installer/install.manifest.schema.json` - Installation manifest schema
  - `/home/ransomeye/rebuild/installer/env.contract.json` - Environment variable contract
  - `/home/ransomeye/rebuild/installer/installer-failure-policy.json` - Installer failure policy
- **Entry Points:**
  - Core installer: `installer/core/install.sh:456-491` - `main()` function
  - Linux agent installer: `installer/linux-agent/install.sh:356-396` - `main()` function
  - DPI probe installer: `installer/dpi-probe/install.sh:413-456` - `main()` function
  - Windows agent installer: `installer/windows-agent/install.bat` - Batch script

**Spec Reference:**
- Installer Bundle (`installer/INSTALLER_BUNDLE.md`)
- Environment Variable Contract (`installer/env.contract.md`, `installer/env.contract.json`)
- Installer Failure Policy (`installer/installer-failure-policy.md`, `installer/installer-failure-policy.json`)
- Privilege Model (`installer/privilege-model.md`)

---

## 1. INSTALLER IDENTITY & AUTHORITY

### Evidence

**Installer Entry Points:**
- ✅ Core installer entry: `installer/core/install.sh:456-491` - `main()` function
- ✅ Linux agent installer entry: `installer/linux-agent/install.sh:356-396` - `main()` function
- ✅ DPI probe installer entry: `installer/dpi-probe/install.sh:413-456` - `main()` function
- ✅ Windows agent installer entry: `installer/windows-agent/install.bat` - Batch script

**Supported Installation Modes:**
- ✅ Core installation: `installer/core/install.sh` - Installs Core runtime and services
- ✅ Linux agent installation: `installer/linux-agent/install.sh` - Installs standalone Linux agent
- ✅ DPI probe installation: `installer/dpi-probe/install.sh` - Installs standalone DPI probe
- ✅ Windows agent installation: `installer/windows-agent/install.bat` - Installs standalone Windows agent

**Whether Installer Is the Only Supported Installation Method:**
- ⚠️ **ISSUE:** Services can start without installer:
  - `services/ingest/app/main.py:722-729` - Has `if __name__ == "__main__"` block for standalone execution
  - `services/correlation-engine/app/main.py:239-248` - Has `if __name__ == "__main__"` block for standalone execution
  - `services/policy-engine/app/main.py:334` - Has `if __name__ == "__main__"` block for standalone execution
  - `services/ai-core/app/main.py:399` - Has `if __name__ == "__main__"` block for standalone execution
  - `services/ui/backend/main.py:491` - Has `if __name__ == "__main__"` block for standalone execution
  - ⚠️ **ISSUE:** Services can start without installer (services have standalone entry points)

**Services Can Be Reliably Started Without Installer Guarantees:**
- ⚠️ **ISSUE:** Services can be started without installer guarantees:
  - `services/ingest/app/main.py:722-729` - Has `if __name__ == "__main__"` block for standalone execution
  - `services/correlation-engine/app/main.py:239-248` - Has `if __name__ == "__main__"` block for standalone execution
  - `services/policy-engine/app/main.py:334` - Has `if __name__ == "__main__"` block for standalone execution
  - `services/ai-core/app/main.py:399` - Has `if __name__ == "__main__"` block for standalone execution
  - `services/ui/backend/main.py:491` - Has `if __name__ == "__main__"` block for standalone execution
  - ⚠️ **ISSUE:** Services can be started without installer guarantees (services have standalone entry points)

### Verdict: **PARTIAL**

**Justification:**
- Installer entry points are clearly identified (Core, Linux agent, DPI probe, Windows agent)
- Supported installation modes are clearly defined (Core, Linux agent, DPI probe, Windows agent)
- **ISSUE:** Services can start without installer (services have standalone entry points)
- **ISSUE:** Services can be started without installer guarantees (services have standalone entry points)

---

## 2. MANIFEST-FIRST ENFORCEMENT (CRITICAL)

### Evidence

**Presence of Install Manifest(s):**
- ✅ Install manifest schema: `installer/install.manifest.schema.json` - JSON Schema (Draft 2020-12) defining canonical manifest structure
- ✅ Install manifest example: `installer/install.manifest.json` - Example manifest with placeholders
- ✅ Core installer manifest: `installer/core/installer.manifest.json` - Core installer manifest schema
- ✅ Core installer creates manifest: `installer/core/install.sh:364-399` - `create_manifest()` creates `installer.manifest.json`
- ✅ Linux agent installer creates manifest: `installer/linux-agent/install.sh:279-315` - `create_manifest()` creates `installer.manifest.json`
- ✅ DPI probe installer creates manifest: `installer/dpi-probe/install.sh:327-365` - `create_manifest()` creates `installer.manifest.json`

**Mandatory Validation Before Install:**
- ❌ **CRITICAL:** No manifest validation found:
  - `installer/core/install.sh:364-399` - `create_manifest()` creates manifest (but no validation found)
  - `installer/linux-agent/install.sh:279-315` - `create_manifest()` creates manifest (but no validation found)
  - `installer/dpi-probe/install.sh:327-365` - `create_manifest()` creates manifest (but no validation found)
  - ❌ **CRITICAL:** No manifest validation (manifest created, but no validation against schema found)

**Refusal to Proceed on Missing Components:**
- ⚠️ **ISSUE:** No explicit missing component check found:
  - `installer/core/install.sh:122-161` - `install_python_files()` copies files (but no explicit missing component check found)
  - `installer/linux-agent/install.sh:148-161` - `install_agent_binary()` copies binary (but no explicit missing component check found)
  - `installer/dpi-probe/install.sh:138-157` - `install_dpi_probe_script()` copies script (but no explicit missing component check found)
  - ⚠️ **ISSUE:** No explicit missing component check (files copied, but no explicit missing component check found)

**Refusal to Proceed on Schema Mismatch:**
- ❌ **CRITICAL:** No schema mismatch check found:
  - `installer/core/install.sh:364-399` - `create_manifest()` creates manifest (but no schema validation found)
  - `installer/linux-agent/install.sh:279-315` - `create_manifest()` creates manifest (but no schema validation found)
  - `installer/dpi-probe/install.sh:327-365` - `create_manifest()` creates manifest (but no schema validation found)
  - ❌ **CRITICAL:** No schema mismatch check (manifest created, but no schema validation found)

**Refusal to Proceed on Version Mismatch:**
- ⚠️ **ISSUE:** No version mismatch check found:
  - `installer/core/install.sh:364-399` - `create_manifest()` creates manifest with version (but no version mismatch check found)
  - `installer/linux-agent/install.sh:279-315` - `create_manifest()` creates manifest with version (but no version mismatch check found)
  - `installer/dpi-probe/install.sh:327-365` - `create_manifest()` creates manifest with version (but no version mismatch check found)
  - ⚠️ **ISSUE:** No version mismatch check (manifest created with version, but no version mismatch check found)

**Installer Proceeds with Partial Manifest:**
- ⚠️ **ISSUE:** Installer may proceed with partial manifest:
  - `installer/core/install.sh:364-399` - `create_manifest()` creates manifest (but no validation found)
  - `installer/linux-agent/install.sh:279-315` - `create_manifest()` creates manifest (but no validation found)
  - `installer/dpi-probe/install.sh:327-365` - `create_manifest()` creates manifest (but no validation found)
  - ⚠️ **ISSUE:** Installer may proceed with partial manifest (manifest created, but no validation found)

**Manifest Validation Warnings Instead of Termination:**
- ⚠️ **ISSUE:** No manifest validation found (cannot determine if warnings or termination):
  - `installer/core/install.sh:364-399` - `create_manifest()` creates manifest (but no validation found)
  - `installer/linux-agent/install.sh:279-315` - `create_manifest()` creates manifest (but no validation found)
  - `installer/dpi-probe/install.sh:327-365` - `create_manifest()` creates manifest (but no validation found)
  - ⚠️ **ISSUE:** No manifest validation found (cannot determine if warnings or termination)

### Verdict: **FAIL**

**Justification:**
- Install manifest schema exists (JSON Schema Draft 2020-12)
- Install manifest example exists (example manifest with placeholders)
- Installers create manifests (Core, Linux agent, DPI probe installers create manifests)
- **CRITICAL:** No manifest validation (manifest created, but no validation against schema found)
- **CRITICAL:** No schema mismatch check (manifest created, but no schema validation found)
- **ISSUE:** No explicit missing component check (files copied, but no explicit missing component check found)
- **ISSUE:** No version mismatch check (manifest created with version, but no version mismatch check found)
- **ISSUE:** Installer may proceed with partial manifest (manifest created, but no validation found)

---

## 3. ENV-ONLY CONFIGURATION & CREDENTIAL HANDLING

### Evidence

**No Hardcoded Credentials:**
- ❌ **CRITICAL:** Hardcoded weak credentials found:
  - `installer/core/install.sh:289-290` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (hardcoded weak credentials)
  - `installer/core/install.sh:301` - `RANSOMEYE_COMMAND_SIGNING_KEY="test_signing_key_minimum_32_characters_long_for_validation_long_enough"` (hardcoded weak default key)
  - `installer/linux-agent/install.sh:228-229` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (hardcoded weak credentials)
  - `installer/dpi-probe/install.sh:276-277` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (hardcoded weak credentials)
  - ❌ **CRITICAL:** Hardcoded weak credentials (DB user/password "gagan", test signing key)

**No Default Passwords or Signing Keys:**
- ❌ **CRITICAL:** Default passwords and signing keys found:
  - `installer/core/install.sh:289-290` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (default weak credentials)
  - `installer/core/install.sh:301` - `RANSOMEYE_COMMAND_SIGNING_KEY="test_signing_key_minimum_32_characters_long_for_validation_long_enough"` (default weak signing key)
  - `installer/linux-agent/install.sh:228-229` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (default weak credentials)
  - `installer/dpi-probe/install.sh:276-277` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (default weak credentials)
  - ❌ **CRITICAL:** Default passwords and signing keys (DB user/password "gagan", test signing key)

**Environment Variables Required for All Secrets:**
- ⚠️ **ISSUE:** Secrets are hardcoded, not from environment:
  - `installer/core/install.sh:289-290` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (hardcoded, not from environment)
  - `installer/core/install.sh:301` - `RANSOMEYE_COMMAND_SIGNING_KEY="test_signing_key_minimum_32_characters_long_for_validation_long_enough"` (hardcoded, not from environment)
  - `installer/linux-agent/install.sh:228-229` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (hardcoded, not from environment)
  - `installer/dpi-probe/install.sh:276-277` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (hardcoded, not from environment)
  - ⚠️ **ISSUE:** Secrets are hardcoded, not from environment (DB user/password and signing key are hardcoded)

**Secrets Not Written to World-Readable Files:**
- ✅ Environment file permissions: `installer/core/install.sh:307` - `chmod 600 "${INSTALL_ROOT}/config/environment"` (600 = owner read/write only)
- ✅ Environment file permissions: `installer/linux-agent/install.sh:232` - `chmod 600 "${INSTALL_ROOT}/config/environment"` (600 = owner read/write only)
- ✅ Environment file permissions: `installer/dpi-probe/install.sh:280` - `chmod 600 "${INSTALL_ROOT}/config/environment"` (600 = owner read/write only)
- ✅ Manifest file permissions: `installer/core/install.sh:396` - `chmod 644 "$manifest_file"` (644 = owner/group read, world read)
- ⚠️ **ISSUE:** Manifest file is world-readable:
  - `installer/core/install.sh:396` - `chmod 644 "$manifest_file"` (644 = world-readable)
  - `installer/linux-agent/install.sh:311` - `chmod 644 "$manifest_file"` (644 = world-readable)
  - `installer/dpi-probe/install.sh:361` - `chmod 644 "$manifest_file"` (644 = world-readable)
  - ⚠️ **ISSUE:** Manifest file is world-readable (644 permissions, world-readable)

**Embedded Credentials:**
- ❌ **CRITICAL:** Embedded credentials found:
  - `installer/core/install.sh:289-290` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (embedded in installer script)
  - `installer/core/install.sh:301` - `RANSOMEYE_COMMAND_SIGNING_KEY="test_signing_key_minimum_32_characters_long_for_validation_long_enough"` (embedded in installer script)
  - `installer/linux-agent/install.sh:228-229` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (embedded in installer script)
  - `installer/dpi-probe/install.sh:276-277` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (embedded in installer script)
  - ❌ **CRITICAL:** Embedded credentials (DB user/password and signing key embedded in installer scripts)

**Weak Defaults:**
- ❌ **CRITICAL:** Weak defaults found:
  - `installer/core/install.sh:289-290` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (weak default credentials)
  - `installer/core/install.sh:301` - `RANSOMEYE_COMMAND_SIGNING_KEY="test_signing_key_minimum_32_characters_long_for_validation_long_enough"` (weak default signing key)
  - `installer/linux-agent/install.sh:228-229` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (weak default credentials)
  - `installer/dpi-probe/install.sh:276-277` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (weak default credentials)
  - ❌ **CRITICAL:** Weak defaults (DB user/password "gagan", test signing key)

**Secrets Logged or Echoed:**
- ⚠️ **ISSUE:** Secrets may be logged or echoed:
  - `installer/core/install.sh:260-305` - `generate_environment_file()` writes secrets to environment file (but no explicit logging found)
  - `installer/core/install.sh:336` - `export PGPASSWORD="gagan"` (password exported to environment, may be visible in process list)
  - ⚠️ **ISSUE:** Secrets may be logged or echoed (password exported to environment, may be visible in process list)

### Verdict: **FAIL**

**Justification:**
- Environment file permissions are correct (600 = owner read/write only)
- **CRITICAL:** Hardcoded weak credentials (DB user/password "gagan", test signing key)
- **CRITICAL:** Default passwords and signing keys (DB user/password "gagan", test signing key)
- **CRITICAL:** Embedded credentials (DB user/password and signing key embedded in installer scripts)
- **CRITICAL:** Weak defaults (DB user/password "gagan", test signing key)
- **ISSUE:** Secrets are hardcoded, not from environment (DB user/password and signing key are hardcoded)
- **ISSUE:** Manifest file is world-readable (644 permissions, world-readable)
- **ISSUE:** Secrets may be logged or echoed (password exported to environment, may be visible in process list)

---

## 4. SYSTEMD UNIT GOVERNANCE

### Evidence

**Centralized systemd Units:**
- ✅ Core systemd unit: `installer/core/ransomeye-core.service` - Single systemd unit for Core
- ✅ Linux agent systemd unit: `installer/linux-agent/ransomeye-linux-agent.service` - Single systemd unit for Linux agent
- ✅ DPI probe systemd unit: `installer/dpi-probe/ransomeye-dpi.service` - Single systemd unit for DPI probe
- ✅ Systemd units installed: `installer/core/install.sh:345-362` - `install_systemd_service()` installs systemd unit
- ✅ Systemd units installed: `installer/linux-agent/install.sh:260-277` - `install_systemd_service()` installs systemd unit
- ✅ Systemd units installed: `installer/dpi-probe/install.sh:308-325` - `install_systemd_service()` installs systemd unit

**Correct Dependency Ordering:**
- ✅ Core systemd dependencies: `installer/core/ransomeye-core.service:4` - `After=network.target postgresql.service`
- ✅ Core systemd dependencies: `installer/core/ransomeye-core.service:5` - `Wants=postgresql.service`
- ✅ Linux agent systemd dependencies: `installer/linux-agent/ransomeye-linux-agent.service:4` - `After=network.target`
- ✅ Linux agent systemd dependencies: `installer/linux-agent/ransomeye-linux-agent.service:5` - `Wants=network-online.target`
- ✅ DPI probe systemd dependencies: `installer/dpi-probe/ransomeye-dpi.service:4` - `After=network.target`
- ✅ DPI probe systemd dependencies: `installer/dpi-probe/ransomeye-dpi.service:5` - `Wants=network-online.target`

**Restart Policies:**
- ✅ Core restart policy: `installer/core/ransomeye-core.service:20` - `Restart=on-failure`
- ✅ Core restart policy: `installer/core/ransomeye-core.service:21` - `RestartSec=10`
- ✅ Linux agent restart policy: `installer/linux-agent/ransomeye-linux-agent.service:20` - `Restart=on-failure`
- ✅ Linux agent restart policy: `installer/linux-agent/ransomeye-linux-agent.service:21` - `RestartSec=60`
- ✅ Linux agent restart limits: `installer/linux-agent/ransomeye-linux-agent.service:26-28` - `StartLimitIntervalSec=300`, `StartLimitBurst=5`, `StartLimitAction=none`
- ✅ DPI probe restart policy: `installer/dpi-probe/ransomeye-dpi.service:22` - `Restart=on-failure`
- ✅ DPI probe restart policy: `installer/dpi-probe/ransomeye-dpi.service:23` - `RestartSec=60`
- ✅ DPI probe restart limits: `installer/dpi-probe/ransomeye-dpi.service:28-30` - `StartLimitIntervalSec=300`, `StartLimitBurst=5`, `StartLimitAction=none`

**Explicit Failure Handling:**
- ✅ Core failure handling: `installer/core/ransomeye-core.service:20-21` - `Restart=on-failure`, `RestartSec=10`
- ✅ Linux agent failure handling: `installer/linux-agent/ransomeye-linux-agent.service:20-28` - `Restart=on-failure`, `RestartSec=60`, restart limits
- ✅ DPI probe failure handling: `installer/dpi-probe/ransomeye-dpi.service:22-30` - `Restart=on-failure`, `RestartSec=60`, restart limits

**Services Start Out of Order:**
- ✅ **VERIFIED:** Services do NOT start out of order:
  - `installer/core/ransomeye-core.service:4-5` - `After=network.target postgresql.service`, `Wants=postgresql.service` (correct dependency ordering)
  - `installer/linux-agent/ransomeye-linux-agent.service:4-5` - `After=network.target`, `Wants=network-online.target` (correct dependency ordering)
  - `installer/dpi-probe/ransomeye-dpi.service:4-5` - `After=network.target`, `Wants=network-online.target` (correct dependency ordering)
  - ✅ **VERIFIED:** Services do NOT start out of order (correct dependency ordering)

**Restart Loops Hide Failure:**
- ⚠️ **ISSUE:** Restart loops may hide failure:
  - `installer/core/ransomeye-core.service:20-21` - `Restart=on-failure`, `RestartSec=10` (but no restart limits found)
  - `installer/linux-agent/ransomeye-linux-agent.service:26-28` - `StartLimitIntervalSec=300`, `StartLimitBurst=5`, `StartLimitAction=none` (restart limits exist, but `StartLimitAction=none` may allow restart loops)
  - `installer/dpi-probe/ransomeye-dpi.service:28-30` - `StartLimitIntervalSec=300`, `StartLimitBurst=5`, `StartLimitAction=none` (restart limits exist, but `StartLimitAction=none` may allow restart loops)
  - ⚠️ **ISSUE:** Restart loops may hide failure (Core has no restart limits, Linux agent and DPI probe have `StartLimitAction=none`)

**Missing Hard Dependencies:**
- ⚠️ **ISSUE:** Core has `Wants` instead of `Requires`:
  - `installer/core/ransomeye-core.service:5` - `Wants=postgresql.service` (Wants = soft dependency, not hard dependency)
  - ⚠️ **ISSUE:** Core has `Wants` instead of `Requires` (Wants = soft dependency, PostgreSQL may not be available)

### Verdict: **PARTIAL**

**Justification:**
- Centralized systemd units exist (Core, Linux agent, DPI probe have single systemd units)
- Correct dependency ordering exists (After=network.target, Wants=postgresql.service/network-online.target)
- Restart policies exist (Restart=on-failure, RestartSec=10/60)
- Explicit failure handling exists (restart policies and restart limits)
- Services do NOT start out of order (correct dependency ordering)
- **ISSUE:** Restart loops may hide failure (Core has no restart limits, Linux agent and DPI probe have `StartLimitAction=none`)
- **ISSUE:** Core has `Wants` instead of `Requires` (Wants = soft dependency, PostgreSQL may not be available)

---

## 5. FAIL-CLOSED BOOTSTRAP BEHAVIOR

### Evidence

**Behavior on Missing Env Vars:**
- ✅ Fail-fast on errors: `installer/core/install.sh:8` - `set -euo pipefail` (fail-fast: exit on any error, undefined variable, or pipe failure)
- ✅ Fail-fast on errors: `installer/linux-agent/install.sh:8` - `set -euo pipefail` (fail-fast: exit on any error, undefined variable, or pipe failure)
- ✅ Fail-fast on errors: `installer/dpi-probe/install.sh:8` - `set -euo pipefail` (fail-fast: exit on any error, undefined variable, or pipe failure)
- ⚠️ **ISSUE:** No explicit env var validation found:
  - `installer/core/install.sh:254-310` - `generate_environment_file()` generates environment file (but no explicit env var validation found)
  - `installer/linux-agent/install.sh:196-236` - `generate_environment_file()` generates environment file (but no explicit env var validation found)
  - `installer/dpi-probe/install.sh:234-284` - `generate_environment_file()` generates environment file (but no explicit env var validation found)
  - ⚠️ **ISSUE:** No explicit env var validation (environment file generated, but no explicit env var validation found)

**Behavior on Invalid DB Connectivity:**
- ✅ DB connectivity check: `installer/core/install.sh:326-343` - `check_postgresql()` tests PostgreSQL connection
- ✅ DB connectivity check: `installer/core/install.sh:340` - `error_exit "Cannot connect to PostgreSQL"` (terminates on failure)
- ⚠️ **ISSUE:** DB connectivity check uses hardcoded credentials:
  - `installer/core/install.sh:336` - `export PGPASSWORD="gagan"` (uses hardcoded password)
  - `installer/core/install.sh:337` - `psql -h localhost -U gagan -d ransomeye` (uses hardcoded user)
  - ⚠️ **ISSUE:** DB connectivity check uses hardcoded credentials (uses hardcoded user/password "gagan")

**Behavior on Missing Signing Keys:**
- ⚠️ **ISSUE:** No signing key validation found:
  - `installer/core/install.sh:301` - `RANSOMEYE_COMMAND_SIGNING_KEY="test_signing_key_minimum_32_characters_long_for_validation_long_enough"` (hardcoded default key, no validation)
  - `installer/linux-agent/install.sh` - No signing key found (Linux agent does not use signing key)
  - `installer/dpi-probe/install.sh` - No signing key found (DPI probe does not use signing key)
  - ⚠️ **ISSUE:** No signing key validation (signing key is hardcoded default, no validation)

**Behavior on Manifest Validation Failure:**
- ❌ **CRITICAL:** No manifest validation found:
  - `installer/core/install.sh:364-399` - `create_manifest()` creates manifest (but no validation found)
  - `installer/linux-agent/install.sh:279-315` - `create_manifest()` creates manifest (but no validation found)
  - `installer/dpi-probe/install.sh:327-365` - `create_manifest()` creates manifest (but no validation found)
  - ❌ **CRITICAL:** No manifest validation (manifest created, but no validation found)

**Services Start Partially:**
- ⚠️ **ISSUE:** Services may start partially:
  - `installer/core/install.sh:401-453` - `validate_installation()` starts Core and performs health check (but no explicit partial startup check found)
  - `installer/linux-agent/install.sh:317-353` - `validate_installation()` starts agent and performs validation (but no explicit partial startup check found)
  - `installer/dpi-probe/install.sh:367-410` - `validate_installation()` starts probe and performs validation (but no explicit partial startup check found)
  - ⚠️ **ISSUE:** Services may start partially (validation exists, but no explicit partial startup check found)

**Warnings Instead of Termination:**
- ⚠️ **ISSUE:** Warnings may be used instead of termination:
  - `installer/core/install.sh:449` - `echo -e "${YELLOW}WARNING: Health check endpoints not accessible"` (warning, not termination)
  - `installer/linux-agent/install.sh:341` - `echo -e "${YELLOW}WARNING:${NC} Agent exited with status"` (warning, not termination)
  - `installer/dpi-probe/install.sh:391` - `echo -e "${YELLOW}WARNING:${NC} DPI Probe exited with status"` (warning, not termination)
  - ⚠️ **ISSUE:** Warnings may be used instead of termination (warnings logged, but installation may continue)

**Silent Skips:**
- ⚠️ **ISSUE:** Silent skips may occur:
  - `installer/core/install.sh:95-101` - Directory creation checks if directory exists (skips if exists, but no explicit error)
  - `installer/core/install.sh:109-114` - User creation checks if user exists (skips if exists, but no explicit error)
  - ⚠️ **ISSUE:** Silent skips may occur (directory and user creation skip if exists, but no explicit error)

### Verdict: **PARTIAL**

**Justification:**
- Fail-fast on errors exists (`set -euo pipefail` in all installers)
- DB connectivity check exists (tests PostgreSQL connection, terminates on failure)
- **CRITICAL:** No manifest validation (manifest created, but no validation found)
- **ISSUE:** No explicit env var validation (environment file generated, but no explicit env var validation found)
- **ISSUE:** DB connectivity check uses hardcoded credentials (uses hardcoded user/password "gagan")
- **ISSUE:** No signing key validation (signing key is hardcoded default, no validation)
- **ISSUE:** Services may start partially (validation exists, but no explicit partial startup check found)
- **ISSUE:** Warnings may be used instead of termination (warnings logged, but installation may continue)
- **ISSUE:** Silent skips may occur (directory and user creation skip if exists, but no explicit error)

---

## 6. PERMISSIONS & FILESYSTEM SAFETY

### Evidence

**File Ownership:**
- ✅ Environment file ownership: `installer/core/install.sh:308` - `chown ransomeye:ransomeye "${INSTALL_ROOT}/config/environment"` (correct ownership)
- ✅ Environment file ownership: `installer/linux-agent/install.sh:233` - `chown ransomeye-agent:ransomeye-agent "${INSTALL_ROOT}/config/environment"` (correct ownership)
- ✅ Environment file ownership: `installer/dpi-probe/install.sh:281` - `chown ransomeye-dpi:ransomeye-dpi "${INSTALL_ROOT}/config/environment"` (correct ownership)
- ✅ Directory ownership: `installer/core/install.sh:159-160` - `chown -R ransomeye:ransomeye "${INSTALL_ROOT}/lib"` and `chown -R ransomeye:ransomeye "${INSTALL_ROOT}/config"` (correct ownership)
- ✅ Logs and runtime ownership: `installer/core/install.sh:318-319` - `chown -R ransomeye:ransomeye "${INSTALL_ROOT}/logs"` and `chown -R ransomeye:ransomeye "${INSTALL_ROOT}/runtime"` (correct ownership)

**Permission Masks:**
- ✅ Environment file permissions: `installer/core/install.sh:307` - `chmod 600 "${INSTALL_ROOT}/config/environment"` (600 = owner read/write only)
- ✅ Environment file permissions: `installer/linux-agent/install.sh:232` - `chmod 600 "${INSTALL_ROOT}/config/environment"` (600 = owner read/write only)
- ✅ Environment file permissions: `installer/dpi-probe/install.sh:280` - `chmod 600 "${INSTALL_ROOT}/config/environment"` (600 = owner read/write only)
- ✅ Directory permissions: `installer/core/install.sh:320-321` - `chmod 755 "${INSTALL_ROOT}/logs"` and `chmod 755 "${INSTALL_ROOT}/runtime"` (755 = owner/group/others read/execute, owner/group write)
- ✅ Manifest file permissions: `installer/core/install.sh:396` - `chmod 644 "$manifest_file"` (644 = owner/group read, world read)
- ✅ Binary permissions: `installer/linux-agent/install.sh:156` - `chmod +x "${INSTALL_ROOT}/bin/ransomeye-linux-agent"` (executable)
- ✅ Script permissions: `installer/core/install.sh:238` - `chmod +x "${INSTALL_ROOT}/bin/ransomeye-core"` (executable)

**No World-Writable Binaries or Configs:**
- ✅ **VERIFIED:** No world-writable binaries or configs:
  - `installer/core/install.sh:307` - `chmod 600 "${INSTALL_ROOT}/config/environment"` (600 = owner read/write only, not world-writable)
  - `installer/core/install.sh:238` - `chmod +x "${INSTALL_ROOT}/bin/ransomeye-core"` (executable, but no explicit world-writable check found)
  - `installer/linux-agent/install.sh:156` - `chmod +x "${INSTALL_ROOT}/bin/ransomeye-linux-agent"` (executable, but no explicit world-writable check found)
  - ✅ **VERIFIED:** No world-writable binaries or configs (environment files are 600, binaries are executable but not world-writable)

**World-Readable Secrets:**
- ⚠️ **ISSUE:** Manifest file is world-readable:
  - `installer/core/install.sh:396` - `chmod 644 "$manifest_file"` (644 = world-readable)
  - `installer/linux-agent/install.sh:311` - `chmod 644 "$manifest_file"` (644 = world-readable)
  - `installer/dpi-probe/install.sh:361` - `chmod 644 "$manifest_file"` (644 = world-readable)
  - ⚠️ **ISSUE:** Manifest file is world-readable (644 permissions, world-readable, but manifest may not contain secrets)

**Executables Writable by Non-Root:**
- ✅ **VERIFIED:** Executables are NOT writable by non-root:
  - `installer/core/install.sh:238` - `chmod +x "${INSTALL_ROOT}/bin/ransomeye-core"` (executable, but no explicit world-writable check found)
  - `installer/core/install.sh:239` - `chown ransomeye:ransomeye "${INSTALL_ROOT}/bin/ransomeye-core"` (owned by ransomeye user, not world-writable)
  - `installer/linux-agent/install.sh:156-158` - `chmod +x` and `chown ransomeye-agent:ransomeye-agent` (executable, owned by ransomeye-agent, not world-writable)
  - ✅ **VERIFIED:** Executables are NOT writable by non-root (executables owned by runtime user, not world-writable)

**Insecure tmp Usage:**
- ✅ **VERIFIED:** No insecure tmp usage found:
  - `installer/core/install.sh:82-102` - `create_directory_structure()` creates directories (no insecure tmp usage found)
  - `installer/linux-agent/install.sh:108-128` - `create_directory_structure()` creates directories (no insecure tmp usage found)
  - `installer/dpi-probe/install.sh:99-119` - `create_directory_structure()` creates directories (no insecure tmp usage found)
  - ✅ **VERIFIED:** No insecure tmp usage (directories created in install root, not system tmp)

### Verdict: **PARTIAL**

**Justification:**
- File ownership is correct (environment files, directories, binaries owned by runtime user)
- Permission masks are correct (600 for environment files, 755 for directories, 644 for manifests, +x for executables)
- No world-writable binaries or configs (environment files are 600, binaries are executable but not world-writable)
- Executables are NOT writable by non-root (executables owned by runtime user, not world-writable)
- No insecure tmp usage (directories created in install root, not system tmp)
- **ISSUE:** Manifest file is world-readable (644 permissions, world-readable, but manifest may not contain secrets)

---

## 7. UPGRADE & ROLLBACK SAFETY

### Evidence

**Upgrade Paths:**
- ❌ **CRITICAL:** No upgrade paths found:
  - `installer/core/install.sh` - No upgrade logic found
  - `installer/linux-agent/install.sh` - No upgrade logic found
  - `installer/dpi-probe/install.sh` - No upgrade logic found
  - ❌ **CRITICAL:** No upgrade paths (no upgrade logic found)

**Rollback Behavior:**
- ❌ **CRITICAL:** No rollback mechanism found:
  - `installer/core/install.sh:8` - `set -euo pipefail` (fail-fast, but no rollback mechanism found)
  - `installer/core/install.sh:21-24` - `error_exit()` exits with code 1 (but no rollback mechanism found)
  - `installer/linux-agent/install.sh:8` - `set -euo pipefail` (fail-fast, but no rollback mechanism found)
  - `installer/linux-agent/install.sh:21-24` - `error_exit()` exits with code 1 (but no rollback mechanism found)
  - `installer/dpi-probe/install.sh:8` - `set -euo pipefail` (fail-fast, but no rollback mechanism found)
  - `installer/dpi-probe/install.sh:21-24` - `error_exit()` exits with code 1 (but no rollback mechanism found)
  - ❌ **CRITICAL:** No rollback mechanism (fail-fast exists, but no rollback mechanism found)

**State Consistency Guarantees:**
- ⚠️ **ISSUE:** No state consistency guarantees found:
  - `installer/core/install.sh:364-399` - `create_manifest()` creates manifest (but no state consistency check found)
  - `installer/linux-agent/install.sh:279-315` - `create_manifest()` creates manifest (but no state consistency check found)
  - `installer/dpi-probe/install.sh:327-365` - `create_manifest()` creates manifest (but no state consistency check found)
  - ⚠️ **ISSUE:** No state consistency guarantees (manifest created, but no state consistency check found)

**In-Place Destructive Upgrades:**
- ⚠️ **ISSUE:** No upgrade logic exists (cannot determine if upgrades are destructive):
  - `installer/core/install.sh` - No upgrade logic found
  - `installer/linux-agent/install.sh` - No upgrade logic found
  - `installer/dpi-probe/install.sh` - No upgrade logic found
  - ⚠️ **ISSUE:** No upgrade logic exists (cannot determine if upgrades are destructive)

**No Rollback Path:**
- ❌ **CRITICAL:** No rollback path found:
  - `installer/core/install.sh:8` - `set -euo pipefail` (fail-fast, but no rollback mechanism found)
  - `installer/core/install.sh:21-24` - `error_exit()` exits with code 1 (but no rollback mechanism found)
  - `installer/installer-failure-policy.md:107-180` - Rollback rules defined in contract (but no implementation found)
  - ❌ **CRITICAL:** No rollback path (rollback rules defined in contract, but no implementation found)

**Mixed-Version Runtime Allowed:**
- ⚠️ **ISSUE:** No version check found (cannot determine if mixed-version runtime is allowed):
  - `installer/core/install.sh:364-399` - `create_manifest()` creates manifest with version (but no version check found)
  - `installer/linux-agent/install.sh:279-315` - `create_manifest()` creates manifest with version (but no version check found)
  - `installer/dpi-probe/install.sh:327-365` - `create_manifest()` creates manifest with version (but no version check found)
  - ⚠️ **ISSUE:** No version check found (cannot determine if mixed-version runtime is allowed)

### Verdict: **FAIL**

**Justification:**
- **CRITICAL:** No upgrade paths (no upgrade logic found)
- **CRITICAL:** No rollback mechanism (fail-fast exists, but no rollback mechanism found)
- **CRITICAL:** No rollback path (rollback rules defined in contract, but no implementation found)
- **ISSUE:** No state consistency guarantees (manifest created, but no state consistency check found)
- **ISSUE:** No upgrade logic exists (cannot determine if upgrades are destructive)
- **ISSUE:** No version check found (cannot determine if mixed-version runtime is allowed)

---

## 8. NEGATIVE VALIDATION (MANDATORY)

### Evidence

**System Starts Without Validated Manifest:**
- ⚠️ **ISSUE:** System may start without validated manifest:
  - `installer/core/install.sh:364-399` - `create_manifest()` creates manifest (but no validation found)
  - `installer/core/install.sh:401-453` - `validate_installation()` starts Core (but no manifest validation found)
  - `services/ingest/app/main.py:722-729` - Has `if __name__ == "__main__"` block for standalone execution (can start without installer)
  - ⚠️ **ISSUE:** System may start without validated manifest (manifest created, but no validation found; services can start standalone)

**System Starts with Default Credentials:**
- ❌ **CRITICAL:** System starts with default credentials:
  - `installer/core/install.sh:289-290` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (default weak credentials)
  - `installer/core/install.sh:301` - `RANSOMEYE_COMMAND_SIGNING_KEY="test_signing_key_minimum_32_characters_long_for_validation_long_enough"` (default weak signing key)
  - `installer/linux-agent/install.sh:228-229` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (default weak credentials)
  - `installer/dpi-probe/install.sh:276-277` - `RANSOMEYE_DB_USER="gagan"` and `RANSOMEYE_DB_PASSWORD="gagan"` (default weak credentials)
  - ❌ **CRITICAL:** System starts with default credentials (DB user/password "gagan", test signing key)

**Partial Services Run Undetected:**
- ⚠️ **ISSUE:** Partial services may run undetected:
  - `installer/core/install.sh:401-453` - `validate_installation()` starts Core and performs health check (but no explicit partial service check found)
  - `installer/core/install.sh:216-229` - `create_core_wrapper()` starts Ingest and UI Backend in background (but no explicit partial service check found)
  - ⚠️ **ISSUE:** Partial services may run undetected (services started, but no explicit partial service check found)

**systemd Masks Fatal Failures:**
- ⚠️ **ISSUE:** systemd may mask fatal failures:
  - `installer/core/ransomeye-core.service:20-21` - `Restart=on-failure`, `RestartSec=10` (but no restart limits found, may restart indefinitely)
  - `installer/linux-agent/ransomeye-linux-agent.service:26-28` - `StartLimitIntervalSec=300`, `StartLimitBurst=5`, `StartLimitAction=none` (restart limits exist, but `StartLimitAction=none` may allow restart loops)
  - `installer/dpi-probe/ransomeye-dpi.service:28-30` - `StartLimitIntervalSec=300`, `StartLimitBurst=5`, `StartLimitAction=none` (restart limits exist, but `StartLimitAction=none` may allow restart loops)
  - ⚠️ **ISSUE:** systemd may mask fatal failures (Core has no restart limits, Linux agent and DPI probe have `StartLimitAction=none`)

### Verdict: **FAIL**

**Justification:**
- **CRITICAL:** System starts with default credentials (DB user/password "gagan", test signing key)
- **ISSUE:** System may start without validated manifest (manifest created, but no validation found; services can start standalone)
- **ISSUE:** Partial services may run undetected (services started, but no explicit partial service check found)
- **ISSUE:** systemd may mask fatal failures (Core has no restart limits, Linux agent and DPI probe have `StartLimitAction=none`)

---

## 9. VERDICT & IMPACT

### Section-by-Section Verdicts

1. **Installer Identity & Authority:** PARTIAL
   - Installer entry points are clearly identified (Core, Linux agent, DPI probe, Windows agent)
   - Supported installation modes are clearly defined (Core, Linux agent, DPI probe, Windows agent)
   - **ISSUE:** Services can start without installer (services have standalone entry points)
   - **ISSUE:** Services can be started without installer guarantees (services have standalone entry points)

2. **Manifest-First Enforcement:** FAIL
   - Install manifest schema exists (JSON Schema Draft 2020-12)
   - Installers create manifests (Core, Linux agent, DPI probe installers create manifests)
   - **CRITICAL:** No manifest validation (manifest created, but no validation against schema found)
   - **CRITICAL:** No schema mismatch check (manifest created, but no schema validation found)
   - **ISSUE:** No explicit missing component check (files copied, but no explicit missing component check found)

3. **Env-Only Configuration & Credential Handling:** FAIL
   - Environment file permissions are correct (600 = owner read/write only)
   - **CRITICAL:** Hardcoded weak credentials (DB user/password "gagan", test signing key)
   - **CRITICAL:** Default passwords and signing keys (DB user/password "gagan", test signing key)
   - **CRITICAL:** Embedded credentials (DB user/password and signing key embedded in installer scripts)
   - **CRITICAL:** Weak defaults (DB user/password "gagan", test signing key)
   - **ISSUE:** Secrets are hardcoded, not from environment (DB user/password and signing key are hardcoded)

4. **Systemd Unit Governance:** PARTIAL
   - Centralized systemd units exist (Core, Linux agent, DPI probe have single systemd units)
   - Correct dependency ordering exists (After=network.target, Wants=postgresql.service/network-online.target)
   - Restart policies exist (Restart=on-failure, RestartSec=10/60)
   - **ISSUE:** Restart loops may hide failure (Core has no restart limits, Linux agent and DPI probe have `StartLimitAction=none`)
   - **ISSUE:** Core has `Wants` instead of `Requires` (Wants = soft dependency, PostgreSQL may not be available)

5. **Fail-Closed Bootstrap Behavior:** PARTIAL
   - Fail-fast on errors exists (`set -euo pipefail` in all installers)
   - DB connectivity check exists (tests PostgreSQL connection, terminates on failure)
   - **CRITICAL:** No manifest validation (manifest created, but no validation found)
   - **ISSUE:** No explicit env var validation (environment file generated, but no explicit env var validation found)
   - **ISSUE:** DB connectivity check uses hardcoded credentials (uses hardcoded user/password "gagan")
   - **ISSUE:** No signing key validation (signing key is hardcoded default, no validation)

6. **Permissions & Filesystem Safety:** PARTIAL
   - File ownership is correct (environment files, directories, binaries owned by runtime user)
   - Permission masks are correct (600 for environment files, 755 for directories, 644 for manifests, +x for executables)
   - No world-writable binaries or configs (environment files are 600, binaries are executable but not world-writable)
   - **ISSUE:** Manifest file is world-readable (644 permissions, world-readable, but manifest may not contain secrets)

7. **Upgrade & Rollback Safety:** FAIL
   - **CRITICAL:** No upgrade paths (no upgrade logic found)
   - **CRITICAL:** No rollback mechanism (fail-fast exists, but no rollback mechanism found)
   - **CRITICAL:** No rollback path (rollback rules defined in contract, but no implementation found)
   - **ISSUE:** No state consistency guarantees (manifest created, but no state consistency check found)

8. **Negative Validation:** FAIL
   - **CRITICAL:** System starts with default credentials (DB user/password "gagan", test signing key)
   - **ISSUE:** System may start without validated manifest (manifest created, but no validation found; services can start standalone)
   - **ISSUE:** Partial services may run undetected (services started, but no explicit partial service check found)
   - **ISSUE:** systemd may mask fatal failures (Core has no restart limits, Linux agent and DPI probe have `StartLimitAction=none`)

### Overall Verdict: **FAIL**

**Justification:**
- **CRITICAL:** Hardcoded weak credentials (DB user/password "gagan", test signing key in Core installer)
- **CRITICAL:** Default passwords and signing keys (DB user/password "gagan", test signing key)
- **CRITICAL:** Embedded credentials (DB user/password and signing key embedded in installer scripts)
- **CRITICAL:** Weak defaults (DB user/password "gagan", test signing key)
- **CRITICAL:** No manifest validation (manifest created, but no validation against schema found)
- **CRITICAL:** No schema mismatch check (manifest created, but no schema validation found)
- **CRITICAL:** No upgrade paths (no upgrade logic found)
- **CRITICAL:** No rollback mechanism (fail-fast exists, but no rollback mechanism found)
- **CRITICAL:** No rollback path (rollback rules defined in contract, but no implementation found)
- **CRITICAL:** System starts with default credentials (DB user/password "gagan", test signing key)
- **ISSUE:** Services can start without installer (services have standalone entry points)
- **ISSUE:** Secrets are hardcoded, not from environment (DB user/password and signing key are hardcoded)
- **ISSUE:** No explicit missing component check (files copied, but no explicit missing component check found)
- **ISSUE:** No version mismatch check (manifest created with version, but no version mismatch check found)
- **ISSUE:** Installer may proceed with partial manifest (manifest created, but no validation found)
- **ISSUE:** Restart loops may hide failure (Core has no restart limits, Linux agent and DPI probe have `StartLimitAction=none`)
- **ISSUE:** Core has `Wants` instead of `Requires` (Wants = soft dependency, PostgreSQL may not be available)
- **ISSUE:** No explicit env var validation (environment file generated, but no explicit env var validation found)
- **ISSUE:** DB connectivity check uses hardcoded credentials (uses hardcoded user/password "gagan")
- **ISSUE:** No signing key validation (signing key is hardcoded default, no validation)
- **ISSUE:** Services may start partially (validation exists, but no explicit partial startup check found)
- **ISSUE:** Warnings may be used instead of termination (warnings logged, but installation may continue)
- **ISSUE:** Manifest file is world-readable (644 permissions, world-readable, but manifest may not contain secrets)
- Install manifest schema exists (JSON Schema Draft 2020-12)
- Installers create manifests (Core, Linux agent, DPI probe installers create manifests)
- Fail-fast on errors exists (`set -euo pipefail` in all installers)
- DB connectivity check exists (tests PostgreSQL connection, terminates on failure)
- File ownership and permissions are correct (environment files 600, directories 755, manifests 644, executables +x)
- Centralized systemd units exist (Core, Linux agent, DPI probe have single systemd units)
- Correct dependency ordering exists (After=network.target, Wants=postgresql.service/network-online.target)

**Impact if Installer is Compromised:**
- **CRITICAL:** If installer is compromised, weak default credentials can be installed (DB user/password "gagan", test signing key)
- **CRITICAL:** If installer is compromised, system can start with default credentials (DB user/password "gagan", test signing key)
- **CRITICAL:** If installer is compromised, invalid manifests can be installed (no manifest validation)
- **CRITICAL:** If installer is compromised, partial installations can occur (no rollback mechanism)
- **CRITICAL:** If installer is compromised, upgrades can be destructive (no upgrade logic)
- **HIGH:** If installer is compromised, services can start without installer guarantees (services have standalone entry points)
- **HIGH:** If installer is compromised, systemd may mask fatal failures (Core has no restart limits, Linux agent and DPI probe have `StartLimitAction=none`)
- **MEDIUM:** If installer is compromised, manifest file is world-readable (644 permissions, world-readable)
- **MEDIUM:** If installer is compromised, DB connectivity check uses hardcoded credentials (uses hardcoded user/password "gagan")
- **LOW:** If installer is compromised, file ownership and permissions remain correct (environment files 600, directories 755, manifests 644, executables +x)
- **LOW:** If installer is compromised, centralized systemd units remain (Core, Linux agent, DPI probe have single systemd units)
- **LOW:** If installer is compromised, correct dependency ordering remains (After=network.target, Wants=postgresql.service/network-online.target)

**Whether Runtime Guarantees Remain Trustworthy:**
- ❌ **FAIL:** Runtime guarantees do NOT remain trustworthy if installer is compromised:
  - Hardcoded weak credentials (DB user/password "gagan", test signing key)
  - Default passwords and signing keys (DB user/password "gagan", test signing key)
  - Embedded credentials (DB user/password and signing key embedded in installer scripts)
  - No manifest validation (manifest created, but no validation against schema found)
  - No rollback mechanism (fail-fast exists, but no rollback mechanism found)
  - Services can start without installer guarantees (services have standalone entry points)
  - ❌ **FAIL:** Runtime guarantees do NOT remain trustworthy if installer is compromised (critical installer security issues)

**Recommendations:**
1. **CRITICAL:** Remove hardcoded weak credentials (require DB user/password and signing key from environment variables)
2. **CRITICAL:** Remove default passwords and signing keys (require all secrets from environment variables)
3. **CRITICAL:** Remove embedded credentials (require all secrets from environment variables, not hardcoded)
4. **CRITICAL:** Implement manifest validation (validate generated manifest against `install.manifest.schema.json` before proceeding)
5. **CRITICAL:** Implement schema mismatch check (validate manifest schema before proceeding)
6. **CRITICAL:** Implement rollback mechanism (rollback all changes on installation failure)
7. **CRITICAL:** Implement rollback path (implement rollback rules from `installer-failure-policy.json`)
8. **CRITICAL:** Implement upgrade paths (support upgrading existing installations)
9. **HIGH:** Prevent services from starting without installer (remove standalone entry points or enforce installer guarantees)
10. **HIGH:** Implement explicit missing component check (check for missing components before proceeding)
11. **HIGH:** Implement version mismatch check (check for version mismatches before proceeding)
12. **HIGH:** Implement restart limits for Core (add `StartLimitIntervalSec` and `StartLimitBurst` to Core systemd unit)
13. **HIGH:** Change Core systemd dependency from `Wants` to `Requires` (hard dependency on PostgreSQL)
14. **HIGH:** Change `StartLimitAction=none` to `StartLimitAction=reboot` or `StartLimitAction=poweroff` (prevent restart loops)
15. **MEDIUM:** Implement explicit env var validation (validate environment variables before generating environment file)
16. **MEDIUM:** Implement signing key validation (validate signing key strength before proceeding)
17. **MEDIUM:** Implement explicit partial service check (check for partial service startup)
18. **MEDIUM:** Change manifest file permissions from 644 to 600 (prevent world-readable manifest)
19. **MEDIUM:** Remove password from environment export (use PostgreSQL .pgpass file instead of `export PGPASSWORD`)

---

**Validation Date:** 2025-01-13
**Validator:** Lead Validator & Compliance Auditor
**Next Step:** Validation complete (all 13 steps completed)
