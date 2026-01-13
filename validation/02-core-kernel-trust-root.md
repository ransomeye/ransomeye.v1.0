# Validation Step 2 — Core Kernel / Trust Root Validation

**Component Identity:**
- **Name:** Core Kernel (Trust Root)
- **Primary Entry Points:**
  - `/home/ransomeye/rebuild/core/main.py` - Main entry point
  - `/home/ransomeye/rebuild/core/runtime.py` - Runtime coordinator
- **Runtime Ownership:** Core runtime initializes first, then loads components as modules
- **Component Independence:** ⚠️ **Services CAN start independently** - All services have `if __name__ == "__main__"` blocks allowing standalone execution

**Spec Reference:**
- Phase 10.1 — Core Runtime Hardening (Startup & Shutdown)
- Master specification: Core as single runtime coordinator

---

## 1. COMPONENT IDENTITY

### Evidence

**Component Name:**
- ✅ Core Kernel is identified as "Core Runtime" in `core/runtime.py:1-5`
- ✅ Entry point is `core/main.py:1-6` which calls `run_core()` from `core/runtime.py`

**Primary Entry Points:**
- ✅ `core/main.py:21-32` - Main entry point with exception handling
- ✅ `core/runtime.py:544-571` - `run_core()` function coordinates initialization

**Runtime Ownership:**
- ✅ `core/runtime.py:477-489` - `_initialize_core()` registers signal handlers and performs startup validation
- ✅ `core/runtime.py:491-542` - `_load_component_modules()` loads services as modules (not standalone processes)
- ✅ `core/runtime.py:557-559` - Comments state "Components are not standalone services, they are Core modules"

**Component Independence Check:**
- ⚠️ **CRITICAL FINDING:** Services CAN operate independently:
  - `services/ingest/app/main.py:722-729` - Has `if __name__ == "__main__"` block for standalone execution
  - `services/correlation-engine/app/main.py:239-248` - Has `if __name__ == "__main__"` block for standalone execution
  - `services/policy-engine/app/main.py:334` - Has `if __name__ == "__main__"` block for standalone execution
  - `services/ai-core/app/main.py:399` - Has `if __name__ == "__main__"` block for standalone execution
  - `services/ui/backend/main.py:491` - Has `if __name__ == "__main__"` block for standalone execution

### Verdict: **FAIL**

**Justification:**
- Core is designed as runtime coordinator, but services have standalone entry points
- **CRITICAL:** Services can bypass Core's trust root validation by starting independently
- Core's trust root guarantees are NOT enforced if services start standalone
- This violates the "single authoritative trust root" requirement

---

## 2. TRUST ROOT MATERIAL (CRITICAL)

### Evidence

**What Constitutes Trust Root:**
- ⚠️ **CRITICAL FINDING:** Core does NOT explicitly define or validate trust root material at startup
- ✅ Signing keys exist: `RANSOMEYE_COMMAND_SIGNING_KEY` (used by Policy Engine)
- ✅ Database credentials: `RANSOMEYE_DB_PASSWORD` (validated by Core)
- ❌ **NO** root certificates found in Core
- ❌ **NO** authority keys validated by Core at startup

**Where Trust Material is Sourced From:**
- ✅ `RANSOMEYE_DB_PASSWORD` - From environment variable (validated by Core)
- ✅ `RANSOMEYE_COMMAND_SIGNING_KEY` - From environment variable (NOT validated by Core)
- ✅ `common/security/secrets.py:50-116` - `validate_signing_key()` validates signing keys
- ⚠️ Signing key validation occurs in Policy Engine module, NOT in Core startup

**What Happens if Trust Key is Missing:**
- ✅ `common/security/secrets.py:72-76` - Missing signing key causes `sys.exit(1)` with "SECURITY VIOLATION"
- ✅ `services/policy-engine/app/signer.py:55-59` - Missing signing key causes `sys.exit(1)`
- ⚠️ **CRITICAL:** Core does NOT check for signing key at startup - only when Policy Engine module loads
- ✅ `core/runtime.py:123` - Core only validates `RANSOMEYE_DB_PASSWORD` in `_validate_environment()`

**What Happens if Trust Key is Malformed:**
- ✅ `common/security/secrets.py:98-101` - Too short key causes `sys.exit(1)`
- ✅ `common/security/secrets.py:104-107` - Insufficient entropy causes `sys.exit(1)`
- ✅ `common/security/secrets.py:111-114` - Weak format (alphabetic only) causes `sys.exit(1)`
- ⚠️ **CRITICAL:** Core does NOT validate signing key format at startup

**What Happens if Trust Key is Weak:**
- ✅ `common/security/secrets.py:82-95` - Known insecure keys cause `sys.exit(1)`
- ✅ `common/security/secrets.py:42-45` - Insufficient entropy causes `sys.exit(1)`
- ⚠️ **CRITICAL:** Core does NOT validate signing key strength at startup

**What Happens if Trust Key is Replaced at Runtime:**
- ✅ `services/policy-engine/app/signer.py:24` - Signing key is cached in `_SIGNING_KEY` global variable
- ✅ `services/policy-engine/app/signer.py:39-41` - Cached key is returned (never reloaded)
- ✅ Key is loaded once at module import time, not reloaded

**Default Trust Material:**
- ✅ `common/security/secrets.py:77-80` - Has fallback default key for development (`phase7_minimal_default_key_change_in_production`)
- ✅ `common/security/secrets.py:82-95` - Default keys are rejected when `fail_on_default=True` (production mode)
- ⚠️ **CRITICAL:** Core does NOT enforce `fail_on_default=True` at startup

**Auto-Generated Trust Keys:**
- ✅ No evidence of auto-generated trust keys at runtime
- ✅ All keys must come from environment variables

### Verdict: **FAIL**

**Justification:**
- **CRITICAL FAILURE:** Core does NOT validate signing keys (trust root material) at startup
- Signing key validation only occurs when Policy Engine module loads (deferred validation)
- Core only validates `RANSOMEYE_DB_PASSWORD`, not `RANSOMEYE_COMMAND_SIGNING_KEY`
- If Policy Engine module is not loaded, signing key is never validated
- This violates "trust root" requirement - Core should validate ALL trust material before allowing any operation

---

## 3. CONFIGURATION LOADING & INVARIANTS

### Evidence

**Single Configuration Path:**
- ✅ `core/runtime.py:69-87` - Uses single `ConfigLoader` instance for Core configuration
- ✅ `common/config/loader.py:19-395` - Single `ConfigLoader` class (no parallel loaders)
- ⚠️ **ISSUE:** Services have their own `ConfigLoader` instances (not centralized in Core)
  - `services/policy-engine/app/main.py:76` - Policy Engine has its own `ConfigLoader`
  - `services/ingest/app/main.py` - Ingest has its own `ConfigLoader`
  - `services/correlation-engine/app/main.py` - Correlation Engine has its own `ConfigLoader`

**Required vs Optional Config Distinction:**
- ✅ `common/config/loader.py:37-59` - `require()` method marks variables as required
- ✅ `common/config/loader.py:61-86` - `optional()` method marks variables as optional with defaults
- ✅ `core/runtime.py:71` - `RANSOMEYE_DB_PASSWORD` is required
- ✅ `core/runtime.py:72-83` - Other variables are optional with defaults

**Enforcement of DB URL:**
- ✅ `core/runtime.py:136-159` - `_validate_db_connectivity()` validates DB connection
- ✅ `core/runtime.py:144-150` - Uses config values for DB connection
- ✅ `core/runtime.py:156-159` - DB connection failure causes `exit_startup_error()`

**Enforcement of DB Credentials:**
- ✅ `core/runtime.py:71` - `RANSOMEYE_DB_PASSWORD` is required
- ✅ `core/runtime.py:123` - `_validate_environment()` checks for `RANSOMEYE_DB_PASSWORD`
- ✅ `core/runtime.py:415` - `_invariant_check_missing_env('RANSOMEYE_DB_PASSWORD')` validates at startup
- ✅ `common/config/loader.py:136-141` - Missing required vars raise `ConfigError`

**Enforcement of Signing Keys:**
- ❌ **CRITICAL:** Core does NOT enforce signing keys at startup
- ⚠️ Signing keys are enforced by Policy Engine module when it loads, not by Core

**Enforcement of Runtime Identity:**
- ✅ `core/runtime.py:25` - Component name is 'core' for logging
- ⚠️ No explicit runtime identity validation found

**Order of Validation:**
- ✅ `core/runtime.py:392-419` - `_core_startup_validation()` defines validation order:
  1. `_validate_environment()` - Environment variables
  2. `_validate_db_connectivity()` - DB connection
  3. `_validate_schema_presence()` - Schema presence
  4. `_validate_write_permissions()` - Write permissions
  5. `_validate_readonly_enforcement()` - Read-only enforcement
  6. `_invariant_check_missing_env('RANSOMEYE_DB_PASSWORD')` - Invariant checks
  7. `_invariant_check_db_connection()` - DB connection invariant
  8. `_invariant_check_schema_mismatch()` - Schema mismatch invariant

**Fallback Config Paths:**
- ⚠️ **ISSUE:** `core/runtime.py:22-66` - Has fallback path when `common` modules unavailable
- ⚠️ `core/runtime.py:88-91` - Falls back to basic env check if `ConfigLoader` unavailable
- ⚠️ Fallback still terminates on missing `RANSOMEYE_DB_PASSWORD`, but uses basic check

**Partial Startup with Missing Invariants:**
- ✅ `core/runtime.py:156-159` - DB connection failure causes termination (no partial startup)
- ✅ `core/runtime.py:200-202` - Missing schema tables cause termination
- ⚠️ **CRITICAL:** Missing signing key does NOT prevent Core startup (only prevents Policy Engine module load)

**Runtime "Fixups":**
- ✅ No evidence of runtime configuration fixups
- ✅ Configuration is loaded once at startup

### Verdict: **PARTIAL**

**Justification:**
- Core has single configuration path and proper required/optional distinction
- **CRITICAL ISSUE:** Signing keys are NOT enforced by Core (deferred to Policy Engine module)
- **ISSUE:** Services have their own ConfigLoader instances (not fully centralized)
- Fallback paths exist but still terminate on critical failures
- Missing signing key does NOT prevent Core startup (violates trust root requirement)

---

## 4. FAIL-CLOSED STARTUP BEHAVIOR

### Evidence

**Missing Env Var → Terminate:**
- ✅ `core/runtime.py:126-132` - Missing `RANSOMEYE_DB_PASSWORD` causes `exit_config_error()`
- ✅ `core/runtime.py:307-310` - `_invariant_check_missing_env()` calls `exit_fatal()` on missing env var
- ✅ `common/config/loader.py:136-141` - Missing required vars raise `ConfigError` which causes termination
- ✅ `common/security/secrets.py:32-34` - Missing secret causes `sys.exit(1)`
- ⚠️ **CRITICAL:** Missing `RANSOMEYE_COMMAND_SIGNING_KEY` does NOT prevent Core startup

**Invalid DB → Terminate:**
- ✅ `core/runtime.py:156-159` - DB connection failure causes `exit_startup_error()`
- ✅ `core/runtime.py:312-329` - `_invariant_check_db_connection()` calls `exit_fatal()` on DB failure
- ✅ `common/db/safety.py:179-184` - Connection creation failure calls `exit_fatal()`

**Invalid Schema → Terminate:**
- ✅ `core/runtime.py:199-202` - Missing required tables causes `exit_startup_error()`
- ✅ `core/runtime.py:331-363` - `_invariant_check_schema_mismatch()` calls `exit_fatal()` on schema mismatch
- ✅ `core/runtime.py:351-356` - Missing `raw_events.event_id` column causes termination

**Invalid Signing Material → Terminate:**
- ✅ `common/security/secrets.py:72-76` - Missing signing key causes `sys.exit(1)`
- ✅ `services/policy-engine/app/signer.py:55-59` - Missing signing key causes `sys.exit(1)`
- ⚠️ **CRITICAL:** Invalid signing material does NOT prevent Core startup - only prevents Policy Engine module load
- ⚠️ Core can start successfully even if signing key is missing/invalid (Policy Engine just won't load)

**Exit Paths:**
- ✅ `core/runtime.py:132` - `exit_config_error()` → `ExitCode.CONFIG_ERROR` (1)
- ✅ `core/runtime.py:159` - `exit_startup_error()` → `ExitCode.STARTUP_ERROR` (2)
- ✅ `core/runtime.py:310` - `exit_fatal()` → `ExitCode.CONFIG_ERROR` (1) or `ExitCode.STARTUP_ERROR` (2)
- ✅ `common/shutdown/handler.py:16-23` - Exit codes defined: SUCCESS (0), CONFIG_ERROR (1), STARTUP_ERROR (2), RUNTIME_ERROR (3), FATAL_ERROR (4)

**Exit Codes:**
- ✅ `common/shutdown/handler.py:16-23` - Standard exit codes defined
- ✅ `core/runtime.py:132` - Uses `exit_config_error()` for config errors
- ✅ `core/runtime.py:159` - Uses `exit_startup_error()` for startup errors
- ✅ `core/runtime.py:310` - Uses `exit_fatal()` for invariant violations

**Whether Termination is Guaranteed:**
- ✅ `core/runtime.py:132` - `exit_config_error()` calls `exit_fatal()` which calls `sys.exit()`
- ✅ `core/runtime.py:159` - `exit_startup_error()` calls `exit_fatal()` which calls `sys.exit()`
- ✅ `common/shutdown/handler.py:117-118` - `exit_fatal()` calls `sys.exit(int(exit_code))`
- ✅ Termination is guaranteed (no retry loops, no warnings-only)

**Retry Loops:**
- ✅ No retry loops found in Core startup
- ✅ All failures cause immediate termination

**Warning-Only Behavior:**
- ✅ No warning-only behavior found
- ✅ All failures cause termination
- ⚠️ `services/policy-engine/app/main.py:112-114` - Logs warning if signing key module unavailable, but this is for ImportError, not missing key

**Degraded Mode:**
- ✅ No degraded mode found
- ✅ Core terminates on critical failures
- ⚠️ **CRITICAL:** Core can start without signing key (Policy Engine just won't load) - this is a form of degraded operation

### Verdict: **PARTIAL**

**Justification:**
- Core terminates on missing DB, invalid schema, missing DB password
- **CRITICAL ISSUE:** Core does NOT terminate on missing/invalid signing key
- Core can start successfully even if signing key is missing (Policy Engine module just fails to load)
- This violates fail-closed requirement for trust root material
- All other failures cause guaranteed termination

---

## 5. CREDENTIAL CHAIN ENFORCEMENT

### Evidence

**DB Credentials:**
- ✅ `core/runtime.py:71` - `RANSOMEYE_DB_PASSWORD` is required
- ✅ `common/config/loader.py:384-387` - `create_db_config_loader()` requires `RANSOMEYE_DB_PASSWORD`
- ✅ `common/security/secrets.py:13-47` - `validate_secret_present()` enforces minimum length (8 chars) and entropy
- ✅ `core/runtime.py:123` - `_validate_environment()` checks for `RANSOMEYE_DB_PASSWORD`
- ✅ `core/runtime.py:415` - `_invariant_check_missing_env('RANSOMEYE_DB_PASSWORD')` validates at startup

**Signing Credentials:**
- ✅ `common/security/secrets.py:50-116` - `validate_signing_key()` enforces minimum length (32 chars)
- ✅ `common/security/secrets.py:82-95` - Rejects known insecure keys
- ✅ `common/security/secrets.py:98-101` - Validates key length
- ✅ `common/security/secrets.py:104-107` - Validates entropy
- ✅ `common/security/secrets.py:111-114` - Validates key format
- ⚠️ **CRITICAL:** Core does NOT enforce signing credentials at startup

**Inter-Service Credentials:**
- ⚠️ **NOT VALIDATED** - Inter-service credentials not examined (component-level validation required)

**Minimum Strength Enforcement:**
- ✅ `common/security/secrets.py:36-39` - DB password minimum length: 8 characters
- ✅ `common/security/secrets.py:42-45` - DB password entropy check: minimum 3 unique characters
- ✅ `common/security/secrets.py:98-101` - Signing key minimum length: 32 characters
- ✅ `common/security/secrets.py:104-107` - Signing key entropy check: minimum 30% unique characters or 8 unique characters
- ✅ `common/security/secrets.py:111-114` - Signing key format check: must have non-alphabetic characters

**Length Checks:**
- ✅ `common/security/secrets.py:36-39` - DB password length check
- ✅ `common/security/secrets.py:98-101` - Signing key length check

**Entropy Checks:**
- ✅ `common/security/secrets.py:42-45` - DB password entropy check (minimum 3 unique characters)
- ✅ `common/security/secrets.py:104-107` - Signing key entropy check (minimum 30% unique or 8 unique)

**Format Checks:**
- ✅ `common/security/secrets.py:111-114` - Signing key format check (must have non-alphabetic characters)
- ✅ `common/security/secrets.py:82-95` - Rejects known insecure key values

**Kernel Enforces Minimum Strength:**
- ✅ `common/security/secrets.py` - Provides validation functions
- ⚠️ **CRITICAL:** Core does NOT call these validation functions for signing keys at startup
- ✅ Core calls validation for DB password via `ConfigLoader.require()`

**Validation Delegated Downstream:**
- ⚠️ **CRITICAL:** Signing key validation is delegated to Policy Engine module
- ⚠️ Core does NOT validate signing keys before allowing any operation

### Verdict: **PARTIAL**

**Justification:**
- DB credentials are enforced by Core with proper strength requirements
- Signing credentials have proper strength validation functions
- **CRITICAL ISSUE:** Core does NOT enforce signing credentials at startup (delegated to Policy Engine)
- Validation functions exist but are not called by Core for signing keys
- This violates "kernel enforces minimum strength" requirement

---

## 6. CRYPTOGRAPHIC BOUNDARIES

### Evidence

**Algorithms Used:**
- ✅ `services/policy-engine/app/signer.py:134` - Uses HMAC-SHA256 for command signing
- ✅ `agents/linux/command_gate.py:302-334` - Uses ed25519 for command verification (different from Policy Engine's HMAC)
- ✅ `threat-response-engine/crypto/signer.py` - Uses ed25519 for TRE command signing
- ⚠️ **ISSUE:** Multiple signing algorithms used (HMAC-SHA256 for Policy Engine, ed25519 for TRE)

**Where Signing Occurs:**
- ✅ `services/policy-engine/app/signer.py:110-136` - Policy Engine signs commands
- ✅ `threat-response-engine/crypto/signer.py` - TRE signs commands
- ⚠️ Signing occurs in service modules, not in Core

**Where Verification Occurs:**
- ✅ `agents/linux/command_gate.py:302-334` - Agents verify commands
- ✅ `threat-response-engine/crypto/verifier.py` - TRE verifies commands
- ⚠️ Verification occurs in service/agent modules, not in Core

**Whether Kernel Refuses to Operate if Crypto Layer Unavailable:**
- ⚠️ **CRITICAL:** Core does NOT check if crypto layer is available at startup
- ⚠️ `services/policy-engine/app/main.py:112-114` - Logs warning if signing key module unavailable (ImportError), but Core still starts
- ⚠️ Core can start even if crypto layer is unavailable (Policy Engine just won't load)

**Crypto Optionality:**
- ⚠️ **CRITICAL:** Crypto appears optional - Core can start without signing key validation
- ⚠️ Policy Engine module fails to load if signing key unavailable, but Core continues

**No-Op Crypto Paths:**
- ✅ No evidence of no-op crypto paths
- ✅ All crypto operations use real algorithms

**Test-Only Crypto in Prod Paths:**
- ✅ `common/security/secrets.py:77-80` - Has development default key, but only used when `fail_on_default=False`
- ✅ `common/security/secrets.py:82-95` - Default keys are rejected in production mode
- ✅ No test-only crypto in production paths

### Verdict: **PARTIAL**

**Justification:**
- Cryptographic algorithms are properly implemented (HMAC-SHA256, ed25519)
- **CRITICAL ISSUE:** Core does NOT refuse to operate if crypto layer unavailable
- Core can start successfully even if signing key is missing (Policy Engine just won't load)
- This violates "kernel refuses to operate if crypto layer unavailable" requirement
- Multiple signing algorithms used (may be intentional, but should be documented)

---

## 7. NEGATIVE VALIDATION (MANDATORY)

### Evidence

**Core Starts Without DB:**
- ✅ **PROVEN IMPOSSIBLE:** `core/runtime.py:136-159` - `_validate_db_connectivity()` validates DB connection
- ✅ `core/runtime.py:156-159` - DB connection failure causes `exit_startup_error()`
- ✅ `core/runtime.py:312-329` - `_invariant_check_db_connection()` calls `exit_fatal()` on DB failure
- ✅ **VERIFIED:** Core cannot start without DB

**Core Starts Without Signing Key:**
- ❌ **PROVEN POSSIBLE:** Core does NOT validate signing key at startup
- ⚠️ `core/runtime.py:123` - Only validates `RANSOMEYE_DB_PASSWORD`, not `RANSOMEYE_COMMAND_SIGNING_KEY`
- ⚠️ `services/policy-engine/app/main.py:96-111` - Signing key validation occurs when Policy Engine module loads
- ✅ **VERIFIED:** Core CAN start without signing key (Policy Engine just won't load)

**Core Starts With Placeholder Secrets:**
- ✅ **PROVEN IMPOSSIBLE:** `common/security/secrets.py:82-95` - Rejects known insecure keys
- ✅ `common/security/secrets.py:42-45` - Rejects weak secrets (insufficient entropy)
- ✅ `common/config/loader.py:136-141` - Missing required secrets raise `ConfigError`
- ⚠️ **PARTIAL:** DB password placeholders are rejected, but signing key placeholders are only rejected when Policy Engine loads

**Core Starts With Mismatched Schema:**
- ✅ **PROVEN IMPOSSIBLE:** `core/runtime.py:199-202` - Missing required tables causes `exit_startup_error()`
- ✅ `core/runtime.py:331-363` - `_invariant_check_schema_mismatch()` validates schema structure
- ✅ `core/runtime.py:351-356` - Missing `raw_events.event_id` column causes termination
- ✅ **VERIFIED:** Core cannot start with mismatched schema

**Core Starts With Partially Initialized Subsystems:**
- ⚠️ **PARTIAL:** Core validates DB, schema, permissions before starting
- ⚠️ **ISSUE:** Core does NOT validate signing key before starting
- ⚠️ Policy Engine subsystem can be uninitialized (missing signing key) while Core runs
- ✅ Other subsystems (DB, schema) must be fully initialized

### Verdict: **PARTIAL**

**Justification:**
- Core cannot start without DB (verified)
- Core cannot start with mismatched schema (verified)
- **CRITICAL:** Core CAN start without signing key (violates trust root requirement)
- **CRITICAL:** Core CAN start with partially initialized subsystems (Policy Engine can be uninitialized)

---

## 8. VERDICT & IMPACT

### Section-by-Section Verdicts

1. **Component Identity:** FAIL
   - Services can start independently, bypassing Core's trust root validation

2. **Trust Root Material:** FAIL
   - Core does NOT validate signing keys at startup
   - Signing key validation is deferred to Policy Engine module

3. **Configuration Loading & Invariants:** PARTIAL
   - Core has proper configuration loading, but does NOT enforce signing keys

4. **Fail-Closed Startup Behavior:** PARTIAL
   - Core terminates on DB/schema failures, but NOT on signing key failures

5. **Credential Chain Enforcement:** PARTIAL
   - DB credentials enforced, but signing credentials NOT enforced by Core

6. **Cryptographic Boundaries:** PARTIAL
   - Crypto algorithms proper, but Core does NOT refuse to operate if crypto unavailable

7. **Negative Validation:** PARTIAL
   - Core cannot start without DB/schema, but CAN start without signing key

### Overall Verdict: **FAIL**

**Justification:**
- **CRITICAL FAILURE:** Core does NOT act as authoritative trust root for signing keys
- Core can start successfully even if signing key is missing/invalid
- Services can bypass Core's trust root validation by starting independently
- Signing key validation is deferred to Policy Engine module, not enforced by Core
- This violates the fundamental requirement: "Core Kernel acts as single, authoritative trust root"

**Blast Radius if Kernel is Compromised:**
- **CRITICAL:** If Core is compromised, all services running as Core modules are compromised
- **CRITICAL:** If Core is compromised, all DB connections are compromised
- **CRITICAL:** If Core is compromised, all configuration is compromised
- **CRITICAL:** If Core is compromised, all component coordination is compromised
- **HIGH:** Services can start independently, so compromise of Core does NOT prevent service operation (but services won't have Core's guarantees)

**Whether Downstream Validations are Trustworthy:**
- ❌ **NO** - Downstream validations cannot be trusted if Core does NOT enforce trust root material
- ❌ If Core can start without signing keys, then trust root guarantees are NOT enforced
- ❌ If services can start independently, then Core's trust root is NOT authoritative
- ⚠️ DB and schema validations are trustworthy, but cryptographic trust root is NOT enforced

**Recommendations:**
1. **CRITICAL:** Core MUST validate `RANSOMEYE_COMMAND_SIGNING_KEY` at startup (before loading any modules)
2. **CRITICAL:** Core MUST terminate if signing key is missing, weak, or invalid
3. **CRITICAL:** Remove or disable standalone service entry points, or ensure they also validate trust root
4. **HIGH:** Core should validate ALL trust root material before allowing any operation
5. **MEDIUM:** Document why multiple signing algorithms are used (HMAC-SHA256 vs ed25519)

---

**Validation Date:** 2025-01-13
**Validator:** Lead Validator & Compliance Auditor
**Next Step:** Validation Step 3 — Secure Bus (if applicable) or Validation Step 4 — Ingest
