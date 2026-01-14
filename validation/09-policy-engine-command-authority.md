# Validation Step 9 — Policy Engine & Command Authority (In-Depth)

**Component Identity:**
- **Name:** Policy Engine (Decision & Response Authority)
- **Primary Paths:**
  - `/home/ransomeye/rebuild/services/policy-engine/app/main.py` - Main policy engine batch processing
  - `/home/ransomeye/rebuild/services/policy-engine/app/rules.py` - Policy rule evaluation
  - `/home/ransomeye/rebuild/services/policy-engine/app/signer.py` - Command signing
  - `/home/ransomeye/rebuild/services/policy-engine/app/db.py` - Database operations
  - `/home/ransomeye/rebuild/threat-response-engine/` - TRE (execution subsystem)
- **Entry Point:** Batch processing loop - `services/policy-engine/app/main.py:200` - `run_policy_engine()`

**Master Spec References:**
- Phase 7 — Simulation-First Policy Engine
- Policy Engine README (`services/policy-engine/README.md`)
- Validation File 06 (Ingest Pipeline) — **TREATED AS FAILED AND LOCKED**
- Validation File 07 (Correlation Engine) — **TREATED AS FAILED AND LOCKED**
- Validation File 08 (AI Core) — **TREATED AS FAILED AND LOCKED**

---

## PURPOSE

This validation proves that the Policy Engine enforces explicit authority, cryptographically verifies command origin, prevents unauthorized or replayed commands, and cannot be bypassed by agents or services.

This validation does NOT assume ingest determinism, correlation determinism, or AI determinism. Validation Files 06, 07, and 08 are treated as FAILED and LOCKED. This validation must account for non-deterministic inputs affecting policy decisions.

This file validates:
- Command signing & verification
- Authority chain (who is allowed to issue which commands)
- Replay protection (nonces / sequence)
- Fail-closed behavior on invalid commands
- Dependency on Core trust root
- Credential handling (signing keys, rotation, scope)

This validation does NOT validate UI, reporting, installer, or provide fixes/recommendations.

---

## POLICY ENGINE DEFINITION

**Policy Engine Requirements (Master Spec):**

1. **Command Signing & Verification** — All commands are cryptographically signed, signature verification is mandatory
2. **Authority Chain** — Explicit authority validation (who is allowed to issue which commands)
3. **Replay Protection** — Nonces or sequence numbers prevent command replay
4. **Fail-Closed Behavior** — Invalid commands are rejected, no fail-open behavior
5. **Dependency on Core Trust Root** — Policy Engine depends on Core trust root for key management
6. **Credential Handling** — Signing keys are properly managed, rotated, and scoped

**Policy Engine Structure:**
- **Entry Point:** Batch processing loop (`run_policy_engine()`)
- **Processing Chain:** Read incidents → Evaluate policy rules → Create signed commands → Store commands
- **Command Flow:** Policy Engine → TRE → Agents (TRE signs with ed25519, agents verify)

---

## WHAT IS VALIDATED

### 1. Command Signing & Verification
- All commands are cryptographically signed
- Signature verification is mandatory
- Signing algorithm is appropriate

### 2. Authority Chain
- Explicit authority validation
- Who is allowed to issue which commands
- Authority cannot be bypassed

### 3. Replay Protection
- Nonces or sequence numbers prevent replay
- Command idempotency is enforced

### 4. Fail-Closed Behavior
- Invalid commands are rejected
- No fail-open behavior exists

### 5. Dependency on Core Trust Root
- Policy Engine depends on Core trust root
- Key management is correct

### 6. Credential Handling
- Signing keys are properly managed
- Key rotation is supported
- Key scope is correct

---

## WHAT IS EXPLICITLY NOT ASSUMED

- **NOT ASSUMED:** That ingest_time (ingested_at) is deterministic (Validation File 06 is FAILED)
- **NOT ASSUMED:** That correlation engine produces deterministic incidents (Validation File 07 is FAILED)
- **NOT ASSUMED:** That AI Core produces deterministic outputs (Validation File 08 is FAILED)
- **NOT ASSUMED:** That Policy Engine receives deterministic inputs (incidents may differ on replay)

---

## VALIDATION METHODOLOGY

### Evidence Collection Strategy

1. **Code Path Analysis:** Trace command signing, signature verification, authority validation, replay protection
2. **Database Query Analysis:** Examine SQL queries for command storage, authority tracking
3. **Cryptographic Analysis:** Verify signing algorithms, key management, signature verification
4. **Authority Analysis:** Check authority chain, RBAC enforcement, issuer verification
5. **Replay Analysis:** Check nonce/sequence handling, idempotency enforcement
6. **Error Handling Analysis:** Check fail-closed behavior, error blocking, silent degradation

### Forbidden Patterns (Grep Validation)

- `continue.*except|pass.*except` — Silent error handling (forbidden, must fail-closed)
- `default.*allow|allow.*default` — Fail-open behavior (forbidden, must fail-closed)
- `unsigned|no.*signature|skip.*verification` — Missing signature verification (forbidden)

---

## 1. COMMAND SIGNING & VERIFICATION

### Evidence

**All Commands Are Cryptographically Signed:**
- ✅ Policy Engine signs commands: `services/policy-engine/app/signer.py:110-136` - `sign_command()` signs commands with HMAC-SHA256
- ✅ Policy Engine creates signed commands: `services/policy-engine/app/signer.py:139-169` - `create_signed_command()` creates signed command structure
- ✅ TRE signs commands: `threat-response-engine/crypto/signer.py:60-80` - `sign_command()` signs commands with ed25519
- ✅ TRE signs before dispatch: `threat-response-engine/api/tre_api.py:195` - `self.signer.sign_command(command_payload)` signs commands before dispatch
- ⚠️ **ISSUE:** Policy Engine uses HMAC-SHA256, TRE uses ed25519 (different signing algorithms)

**Signature Verification Is Mandatory:**
- ✅ Agents verify signatures: `agents/linux/command_gate.py:314-346` - `_verify_signature()` verifies ed25519 signature before execution
- ✅ Signature verification is required: `agents/linux/command_gate.py:324-325` - If verifier not available, command is rejected
- ✅ Signature verification is step 3: `agents/linux/command_gate.py:175` - Signature verification is step 3 of 9-step pipeline
- ⚠️ **ISSUE:** Windows agent has placeholder: `agents/windows/command_gate.ps1:122-129` - `Test-CommandSignature` has placeholder (not implemented)

**Signing Algorithm Is Appropriate:**
- ✅ Policy Engine uses HMAC-SHA256: `services/policy-engine/app/signer.py:134` - `hmac.new(signing_key, command_json.encode('utf-8'), hashlib.sha256).hexdigest()`
- ✅ TRE uses ed25519: `threat-response-engine/crypto/signer.py:50-53` - `self.private_key.sign(payload_json.encode('utf-8'), backend=default_backend())`
- ✅ Agents verify ed25519: `agents/linux/command_gate.py:342` - `self.verifier.verify(message, signature)` (ed25519 verification)
- ⚠️ **ISSUE:** Policy Engine and TRE use different signing algorithms (HMAC-SHA256 vs ed25519)

**Any Command Is Accepted Without Cryptographic Verification:**
- ✅ **VERIFIED:** Agents do NOT accept unsigned commands: `agents/linux/command_gate.py:314-346` - Signature verification is mandatory (step 3)
- ✅ **VERIFIED:** If signature verification fails, command is rejected: `agents/linux/command_gate.py:343-344` - Raises `CommandRejectionError` on signature verification failure
- ⚠️ **ISSUE:** Windows agent has placeholder for signature verification (not implemented)

### Verdict: **PARTIAL**

**Justification:**
- Policy Engine signs commands (HMAC-SHA256)
- TRE signs commands (ed25519)
- Agents verify signatures (ed25519 verification is mandatory)
- **ISSUE:** Policy Engine and TRE use different signing algorithms (HMAC-SHA256 vs ed25519)
- **ISSUE:** Windows agent has placeholder for signature verification (not implemented)

**PASS Conditions (Met):**
- All commands are cryptographically signed — **CONFIRMED** (Policy Engine and TRE sign commands)
- Signature verification is mandatory — **CONFIRMED** (agents verify signatures)

**FAIL Conditions (Met):**
- Any command is accepted without cryptographic verification — **PARTIAL** (Linux agent verifies, Windows agent has placeholder)

**Evidence Required:**
- File paths: `services/policy-engine/app/signer.py:110-136,139-169`, `threat-response-engine/crypto/signer.py:60-80`, `threat-response-engine/api/tre_api.py:195`, `agents/linux/command_gate.py:314-346,175`, `agents/windows/command_gate.ps1:122-129`
- Command signing: HMAC-SHA256 (Policy Engine), ed25519 (TRE)
- Signature verification: ed25519 verification (agents)

---

## 2. AUTHORITY CHAIN

### Evidence

**Explicit Authority Validation:**
- ✅ RBAC validation: `agents/linux/command_gate.py:364-387` - `_validate_rbac()` validates `issued_by_role` and `issued_by_user_id`
- ✅ Role validation: `agents/linux/command_gate.py:385-387` - Valid roles are `{'SUPER_ADMIN', 'SECURITY_ANALYST', 'POLICY_MANAGER', 'IT_ADMIN', 'AUDITOR'}`
- ✅ Issuer verification: `agents/linux/command_gate.py:348-362` - `_verify_issuer()` verifies `signing_key_id` matches TRE key ID
- ✅ HAF approval validation: `agents/linux/command_gate.py:389-413` - `_validate_haf_approval()` validates HAF approval for destructive actions
- ⚠️ **ISSUE:** Policy Engine does not validate authority: `services/policy-engine/app/rules.py:22-56` - Policy rules do not validate authority (only evaluate incident stage)

**Who Is Allowed to Issue Which Commands:**
- ✅ Agents validate role: `agents/linux/command_gate.py:385-387` - Valid roles are defined (SUPER_ADMIN, SECURITY_ANALYST, etc.)
- ✅ Agents validate user_id: `agents/linux/command_gate.py:380-382` - `issued_by_user_id` must be present
- ⚠️ **ISSUE:** Policy Engine does not track who issues commands: `services/policy-engine/app/signer.py:71-107` - Command payload does not include `issued_by_user_id` or `issued_by_role`
- ⚠️ **ISSUE:** TRE adds user_id and role: `threat-response-engine/api/tre_api.py:189-190` - TRE adds `issued_by_user_id` and `issued_by_role` to command payload

**Authority Cannot Be Bypassed:**
- ✅ Agents validate authority: `agents/linux/command_gate.py:364-413` - RBAC, issuer, and HAF approval validation are mandatory (steps 4, 5, 6)
- ✅ Authority validation is in pipeline: `agents/linux/command_gate.py:177-184` - Authority validation is steps 4, 5, 6 of 9-step pipeline
- ⚠️ **ISSUE:** Policy Engine does not validate authority (authority validation happens at TRE/agent level)

**Any Command Executes Without Explicit Authority Validation:**
- ✅ **VERIFIED:** Agents do NOT execute without authority validation: `agents/linux/command_gate.py:177-184` - Authority validation is mandatory (steps 4, 5, 6)
- ⚠️ **ISSUE:** Policy Engine does not validate authority (authority validation deferred to TRE/agents)

### Verdict: **PARTIAL**

**Justification:**
- Agents validate authority (RBAC, issuer, HAF approval)
- Authority validation is mandatory (steps 4, 5, 6 of 9-step pipeline)
- **ISSUE:** Policy Engine does not validate authority (authority validation deferred to TRE/agents)
- **ISSUE:** Policy Engine does not track who issues commands (command payload does not include user_id/role)

**PASS Conditions (Met):**
- Explicit authority validation exists — **CONFIRMED** (agents validate authority)
- Authority cannot be bypassed — **CONFIRMED** (authority validation is mandatory)

**FAIL Conditions (Met):**
- Any command executes without explicit authority validation — **PARTIAL** (agents validate, but Policy Engine does not)

**Evidence Required:**
- File paths: `agents/linux/command_gate.py:364-387,348-362,389-413,177-184`, `services/policy-engine/app/rules.py:22-56`, `services/policy-engine/app/signer.py:71-107`, `threat-response-engine/api/tre_api.py:189-190`
- Authority validation: RBAC, issuer verification, HAF approval
- Authority tracking: user_id, role in command payload

---

## 3. REPLAY PROTECTION

### Evidence

**Nonces or Sequence Numbers Prevent Replay:**
- ✅ Command ID idempotency: `agents/linux/command_gate.py:415-436` - `_check_idempotency()` checks if `command_id` already seen (replay protection)
- ✅ Nonce cache: `agents/linux/command_gate.py:91-92` - `self.nonce_cache = set()` (nonce cache for replay protection)
- ✅ Command ID is UUID: `services/policy-engine/app/signer.py:93` - `command_id = str(uuid.uuid4())` (UUID v4, unique)
- ⚠️ **ISSUE:** No sequence numbers: No sequence number field found in command payload
- ⚠️ **ISSUE:** No nonce field: No explicit nonce field found in command payload (only command_id used for idempotency)

**Command Idempotency Is Enforced:**
- ✅ Idempotency check: `agents/linux/command_gate.py:415-436` - `_check_idempotency()` prevents duplicate command execution
- ✅ Idempotency is step 7: `agents/linux/command_gate.py:187` - Idempotency check is step 7 of 9-step pipeline
- ✅ Replay detection: `agents/linux/command_gate.py:425-426` - If `command_id` already in cache, raises `CommandRejectionError` (replay attack)
- ⚠️ **ISSUE:** Nonce cache has size limit: `agents/linux/command_gate.py:432-436` - Nonce cache evicts oldest entries when full (may allow replay after eviction)

**Replay Protection Depends on Non-Deterministic Inputs:**
- ⚠️ **ISSUE:** Command ID is UUID (non-deterministic): `services/policy-engine/app/signer.py:93` - `command_id = str(uuid.uuid4())` (UUID v4, non-deterministic)
- ✅ Idempotency check is deterministic: `agents/linux/command_gate.py:425` - Idempotency check is deterministic (checks if command_id in cache)
- ⚠️ **ISSUE:** If same command is replayed with different command_id, idempotency check will not detect replay (command_id is non-deterministic)

### Verdict: **PARTIAL**

**Justification:**
- Command ID idempotency prevents replay (command_id is checked)
- Idempotency check is mandatory (step 7 of 9-step pipeline)
- **ISSUE:** No sequence numbers or explicit nonce field (only command_id used)
- **ISSUE:** Nonce cache has size limit (may allow replay after eviction)
- **ISSUE:** Command ID is UUID (non-deterministic), so same command replayed with different command_id will not be detected

**PASS Conditions (Met):**
- Replay protection exists — **CONFIRMED** (command ID idempotency)
- Command idempotency is enforced — **CONFIRMED** (idempotency check is mandatory)

**FAIL Conditions (Met):**
- Replay protection depends on non-deterministic inputs — **PARTIAL** (command_id is UUID, non-deterministic)

**Evidence Required:**
- File paths: `agents/linux/command_gate.py:415-436,91-92,187`, `services/policy-engine/app/signer.py:93`
- Replay protection: Command ID idempotency, nonce cache
- Idempotency: Command ID uniqueness, cache management

---

## 4. FAIL-CLOSED BEHAVIOR

### Evidence

**Invalid Commands Are Rejected:**
- ✅ Schema validation rejects invalid commands: `agents/linux/command_gate.py:207-282` - `_validate_schema()` validates command schema (required fields, UUIDs, enums, timestamps)
- ✅ Freshness check rejects expired commands: `agents/linux/command_gate.py:284-312` - `_validate_freshness()` rejects expired commands and commands with clock skew
- ✅ Signature verification rejects invalid signatures: `agents/linux/command_gate.py:314-346` - `_verify_signature()` rejects commands with invalid signatures
- ✅ Authority validation rejects unauthorized commands: `agents/linux/command_gate.py:364-413` - RBAC, issuer, and HAF approval validation reject unauthorized commands
- ✅ All validation steps must pass: `agents/linux/command_gate.py:167-194` - If any step fails, command is rejected

**No Fail-Open Behavior Exists:**
- ✅ **VERIFIED:** No fail-open behavior: `agents/linux/command_gate.py:200-205` - All exceptions raise `CommandRejectionError` (no fail-open)
- ✅ **VERIFIED:** Default deny: `agents/linux/command_gate.py:471-492` - Default deny policy when no cached policy exists (fail-closed)
- ✅ **VERIFIED:** Offline enforcement is fail-closed: `agents/linux/command_gate.py:614-678` - When Core is offline, cached policy enforces fail-closed (default deny)

**Behavior on Invalid Commands:**
- ✅ Invalid commands are rejected: `agents/linux/command_gate.py:200-205` - All validation failures raise `CommandRejectionError`
- ✅ Rejection is logged: `agents/linux/command_gate.py:201-202` - Rejection is logged to audit log
- ✅ No silent acceptance: `agents/linux/command_gate.py:200-205` - No silent acceptance of invalid commands

**Any Fail-Open Behavior Exists:**
- ✅ **VERIFIED:** No fail-open behavior found: All validation failures cause rejection (no fail-open)

### Verdict: **PASS**

**Justification:**
- Invalid commands are rejected (all validation steps must pass)
- No fail-open behavior exists (default deny, offline enforcement is fail-closed)
- Rejection is logged (audit trail exists)

**PASS Conditions (Met):**
- Invalid commands are rejected — **CONFIRMED** (all validation steps must pass)
- No fail-open behavior exists — **CONFIRMED** (default deny, fail-closed)

**Evidence Required:**
- File paths: `agents/linux/command_gate.py:207-282,284-312,314-346,364-413,167-194,200-205,471-492,614-678`
- Fail-closed behavior: Default deny, offline enforcement, rejection logging

---

## 5. DEPENDENCY ON CORE TRUST ROOT

### Evidence

**Policy Engine Depends on Core Trust Root:**
- ✅ Signing key from environment: `services/policy-engine/app/signer.py:45-68` - `get_signing_key()` reads `RANSOMEYE_COMMAND_SIGNING_KEY` from environment
- ✅ Signing key validation: `services/policy-engine/app/signer.py:45-50` - `validate_signing_key()` validates key strength (min 32 characters)
- ✅ Signing key initialization: `services/policy-engine/app/main.py:97-114` - Signing key is initialized at startup (fail-fast on invalid key)
- ⚠️ **ISSUE:** Policy Engine does not use Core trust root directly (signing key is from environment, not from Core trust root)

**Key Management Is Correct:**
- ✅ Signing key is loaded once: `services/policy-engine/app/signer.py:24-41` - Signing key is cached (loaded once, never reloaded)
- ✅ Signing key is never logged: `services/policy-engine/app/signer.py:24-41` - Signing key is never logged (security)
- ⚠️ **ISSUE:** No key rotation found: No key rotation logic found in Policy Engine
- ⚠️ **ISSUE:** No key versioning found: No key versioning logic found in Policy Engine

**Dependency on Core Trust Root Is Explicit:**
- ⚠️ **ISSUE:** Policy Engine does not explicitly depend on Core trust root (signing key is from environment, not from Core trust root)
- ⚠️ **ISSUE:** TRE uses separate key management: `threat-response-engine/crypto/key_manager.py` - TRE uses separate key management (not from Core trust root)

### Verdict: **PARTIAL**

**Justification:**
- Signing key is properly managed (loaded once, never logged, validated)
- **ISSUE:** Policy Engine does not explicitly depend on Core trust root (signing key is from environment)
- **ISSUE:** No key rotation or versioning found
- **ISSUE:** TRE uses separate key management (not from Core trust root)

**PASS Conditions (Met):**
- Key management is correct — **CONFIRMED** (signing key is properly managed)

**FAIL Conditions (Met):**
- Dependency on Core trust root is explicit — **NOT CONFIRMED** (signing key is from environment, not from Core trust root)

**Evidence Required:**
- File paths: `services/policy-engine/app/signer.py:45-68,24-41`, `services/policy-engine/app/main.py:97-114`, `threat-response-engine/crypto/key_manager.py`
- Key management: Signing key loading, validation, caching
- Core trust root: Dependency on Core trust root

---

## 6. CREDENTIAL HANDLING

### Evidence

**Signing Keys Are Properly Managed:**
- ✅ Signing key is loaded once: `services/policy-engine/app/signer.py:24-41` - Signing key is cached (loaded once, never reloaded)
- ✅ Signing key is never logged: `services/policy-engine/app/signer.py:24-41` - Signing key is never logged (security)
- ✅ Signing key validation: `services/policy-engine/app/signer.py:45-50` - `validate_signing_key()` validates key strength (min 32 characters)
- ✅ Signing key fail-fast: `services/policy-engine/app/signer.py:55-59` - Missing or weak signing key causes termination (fail-fast)

**Key Rotation Is Supported:**
- ⚠️ **ISSUE:** No key rotation found: No key rotation logic found in Policy Engine
- ⚠️ **ISSUE:** No key versioning found: No key versioning logic found in Policy Engine
- ⚠️ **ISSUE:** Signing key is static: Signing key is loaded once and never rotated

**Key Scope Is Correct:**
- ✅ Policy Engine signing key scope: `services/policy-engine/app/signer.py:45-68` - Policy Engine uses `RANSOMEYE_COMMAND_SIGNING_KEY` (HMAC-SHA256)
- ✅ TRE signing key scope: `threat-response-engine/crypto/key_manager.py` - TRE uses separate ed25519 key (different scope)
- ⚠️ **ISSUE:** Two different signing keys (Policy Engine uses HMAC-SHA256, TRE uses ed25519)

**Signing Keys Are Not Properly Managed:**
- ✅ **VERIFIED:** Signing keys are properly managed: Signing key is loaded once, never logged, validated, fail-fast on invalid key

### Verdict: **PARTIAL**

**Justification:**
- Signing keys are properly managed (loaded once, never logged, validated, fail-fast)
- **ISSUE:** No key rotation or versioning found
- **ISSUE:** Two different signing keys (Policy Engine uses HMAC-SHA256, TRE uses ed25519)

**PASS Conditions (Met):**
- Signing keys are properly managed — **CONFIRMED** (loaded once, never logged, validated)

**FAIL Conditions (Met):**
- Key rotation is supported — **NOT CONFIRMED** (no key rotation found)
- Key scope is correct — **PARTIAL** (two different signing keys)

**Evidence Required:**
- File paths: `services/policy-engine/app/signer.py:24-41,45-68,55-59`, `threat-response-engine/crypto/key_manager.py`
- Credential handling: Signing key loading, validation, caching, rotation

---

## CREDENTIAL TYPES VALIDATED

### Command Signing Keys
- **Type:** HMAC-SHA256 key (`RANSOMEYE_COMMAND_SIGNING_KEY`) for Policy Engine, ed25519 key for TRE
- **Source:** Environment variable (required, no default)
- **Validation:** ✅ **VALIDATED** (signing key is validated, fail-fast on invalid key)
- **Usage:** Command signing (Policy Engine: HMAC-SHA256, TRE: ed25519)
- **Status:** ✅ **VALIDATED** (signing keys are properly managed)

---

## PASS CONDITIONS

### Section 1: Command Signing & Verification
- ✅ All commands are cryptographically signed — **PASS**
- ✅ Signature verification is mandatory — **PASS**
- ⚠️ Signing algorithm is appropriate — **PARTIAL**

### Section 2: Authority Chain
- ✅ Explicit authority validation exists — **PASS**
- ⚠️ Who is allowed to issue which commands is explicit — **PARTIAL**
- ✅ Authority cannot be bypassed — **PASS**

### Section 3: Replay Protection
- ⚠️ Nonces or sequence numbers prevent replay — **PARTIAL**
- ✅ Command idempotency is enforced — **PASS**

### Section 4: Fail-Closed Behavior
- ✅ Invalid commands are rejected — **PASS**
- ✅ No fail-open behavior exists — **PASS**

### Section 5: Dependency on Core Trust Root
- ⚠️ Policy Engine depends on Core trust root — **PARTIAL**
- ✅ Key management is correct — **PASS**

### Section 6: Credential Handling
- ✅ Signing keys are properly managed — **PASS**
- ❌ Key rotation is supported — **FAIL**
- ⚠️ Key scope is correct — **PARTIAL**

---

## FAIL CONDITIONS

### Section 1: Command Signing & Verification
- ⚠️ Any command is accepted without cryptographic verification — **PARTIAL** (Linux agent verifies, Windows agent has placeholder)

### Section 2: Authority Chain
- ⚠️ Any command executes without explicit authority validation — **PARTIAL** (agents validate, but Policy Engine does not)

### Section 3: Replay Protection
- ⚠️ Replay protection depends on non-deterministic inputs — **PARTIAL** (command_id is UUID, non-deterministic)

### Section 4: Fail-Closed Behavior
- ❌ Any fail-open behavior exists — **NOT CONFIRMED** (no fail-open behavior found)

### Section 5: Dependency on Core Trust Root
- ❌ Dependency on Core trust root is explicit — **NOT CONFIRMED** (signing key is from environment, not from Core trust root)

### Section 6: Credential Handling
- ❌ Key rotation is supported — **NOT CONFIRMED** (no key rotation found)
- ⚠️ Key scope is correct — **PARTIAL** (two different signing keys)

---

## EVIDENCE REQUIRED

### Command Signing & Verification
- File paths: `services/policy-engine/app/signer.py:110-136,139-169`, `threat-response-engine/crypto/signer.py:60-80`, `threat-response-engine/api/tre_api.py:195`, `agents/linux/command_gate.py:314-346,175`, `agents/windows/command_gate.ps1:122-129`
- Command signing: HMAC-SHA256 (Policy Engine), ed25519 (TRE)
- Signature verification: ed25519 verification (agents)

### Authority Chain
- File paths: `agents/linux/command_gate.py:364-387,348-362,389-413,177-184`, `services/policy-engine/app/rules.py:22-56`, `services/policy-engine/app/signer.py:71-107`, `threat-response-engine/api/tre_api.py:189-190`
- Authority validation: RBAC, issuer verification, HAF approval
- Authority tracking: user_id, role in command payload

### Replay Protection
- File paths: `agents/linux/command_gate.py:415-436,91-92,187`, `services/policy-engine/app/signer.py:93`
- Replay protection: Command ID idempotency, nonce cache
- Idempotency: Command ID uniqueness, cache management

### Fail-Closed Behavior
- File paths: `agents/linux/command_gate.py:207-282,284-312,314-346,364-413,167-194,200-205,471-492,614-678`
- Fail-closed behavior: Default deny, offline enforcement, rejection logging

### Dependency on Core Trust Root
- File paths: `services/policy-engine/app/signer.py:45-68,24-41`, `services/policy-engine/app/main.py:97-114`, `threat-response-engine/crypto/key_manager.py`
- Key management: Signing key loading, validation, caching
- Core trust root: Dependency on Core trust root

### Credential Handling
- File paths: `services/policy-engine/app/signer.py:24-41,45-68,55-59`, `threat-response-engine/crypto/key_manager.py`
- Credential handling: Signing key loading, validation, caching, rotation

---

## GA VERDICT

### Overall: **PARTIAL**

**Critical Blockers:**

1. **PARTIAL:** Policy Engine and TRE use different signing algorithms (HMAC-SHA256 vs ed25519)
   - **Impact:** Policy Engine signs with HMAC-SHA256, TRE signs with ed25519, agents verify ed25519 (inconsistent)
   - **Location:** `services/policy-engine/app/signer.py:134` — HMAC-SHA256, `threat-response-engine/crypto/signer.py:50-53` — ed25519
   - **Severity:** **HIGH** (inconsistent signing algorithms)
   - **Master Spec Violation:** Command signing should be consistent

2. **PARTIAL:** Windows agent has placeholder for signature verification (not implemented)
   - **Impact:** Windows agent cannot verify command signatures (placeholder only)
   - **Location:** `agents/windows/command_gate.ps1:122-129` — `Test-CommandSignature` has placeholder
   - **Severity:** **CRITICAL** (Windows agent cannot verify signatures)
   - **Master Spec Violation:** All agents must verify command signatures

3. **PARTIAL:** Policy Engine does not validate authority (authority validation deferred to TRE/agents)
   - **Impact:** Policy Engine does not track who issues commands (authority validation happens at TRE/agent level)
   - **Location:** `services/policy-engine/app/signer.py:71-107` — Command payload does not include user_id/role
   - **Severity:** **MEDIUM** (authority validation deferred, not missing)
   - **Master Spec Violation:** Policy Engine should validate authority

4. **PARTIAL:** No key rotation or versioning found
   - **Impact:** Signing keys cannot be rotated or versioned
   - **Location:** `services/policy-engine/app/signer.py:24-41` — Signing key is static (no rotation)
   - **Severity:** **MEDIUM** (key rotation not supported)
   - **Master Spec Violation:** Key rotation should be supported

5. **PARTIAL:** Replay protection depends on non-deterministic command_id (UUID)
   - **Impact:** Same command replayed with different command_id will not be detected (command_id is UUID, non-deterministic)
   - **Location:** `services/policy-engine/app/signer.py:93` — `command_id = str(uuid.uuid4())` (UUID v4, non-deterministic)
   - **Severity:** **MEDIUM** (replay protection may not detect replay if command_id differs)
   - **Master Spec Violation:** Replay protection should not depend on non-deterministic inputs

**Non-Blocking Issues:**

1. Agents validate authority (RBAC, issuer, HAF approval)
2. Invalid commands are rejected (all validation steps must pass)
3. No fail-open behavior exists (default deny, fail-closed)
4. Signing keys are properly managed (loaded once, never logged, validated)

**Strengths:**

1. ✅ Agents verify signatures (ed25519 verification is mandatory)
2. ✅ Authority validation is mandatory (steps 4, 5, 6 of 9-step pipeline)
3. ✅ Command idempotency prevents replay (command_id is checked)
4. ✅ Invalid commands are rejected (all validation steps must pass)
5. ✅ No fail-open behavior exists (default deny, offline enforcement is fail-closed)
6. ✅ Signing keys are properly managed (loaded once, never logged, validated, fail-fast)

**Summary of Critical Blockers:**

1. **CRITICAL:** Windows agent has placeholder for signature verification (not implemented) — Windows agent cannot verify signatures
2. **HIGH:** Policy Engine and TRE use different signing algorithms (HMAC-SHA256 vs ed25519) — Inconsistent signing
3. **MEDIUM:** Policy Engine does not validate authority (authority validation deferred to TRE/agents) — Authority validation deferred
4. **MEDIUM:** No key rotation or versioning found — Key rotation not supported
5. **MEDIUM:** Replay protection depends on non-deterministic command_id (UUID) — Replay protection may not detect replay

---

**Validation Date:** 2025-01-13  
**Validator:** Independent System Validator  
**Next Step:** Validation Step 10 — Endpoint Agents Execution Trust  
**GA Status:** **BLOCKED** (Critical failures in Windows agent signature verification and signing algorithm consistency)

---

## UPSTREAM IMPACT STATEMENT

**Documentation Only:** This section documents upstream impact of Policy Engine non-determinism and authority validation failures on downstream validations.

**Upstream Validations Impacted by Policy Engine Failures:**

1. **Correlation Engine (Validation Step 7):**
   - Policy Engine reads incidents created by correlation engine
   - Incidents may differ on replay (if correlation is non-deterministic)
   - Policy Engine validation must NOT assume deterministic incident inputs

2. **AI Core (Validation Step 8):**
   - Policy Engine may read AI metadata (if policy rules use AI metadata)
   - AI metadata may differ on replay (if AI is non-deterministic)
   - Policy Engine validation must NOT assume deterministic AI metadata

**Requirements for Upstream Validations:**

- Upstream validations must NOT assume Policy Engine receives deterministic inputs (incidents may differ on replay)
- Upstream validations must NOT assume Policy Engine produces deterministic outputs (policy decisions may differ on replay)
- Upstream validations must validate their components based on actual behavior, not assumptions about Policy Engine determinism

---

## DOWNSTREAM IMPACT STATEMENT

**Documentation Only:** This section documents downstream impact of Policy Engine failures on downstream validations.

**Downstream Validations Impacted by Policy Engine Failures:**

1. **Endpoint Agents (Validation Step 10):**
   - Agents receive commands from Policy Engine (via TRE)
   - Commands may differ on replay (if Policy Engine is non-deterministic)
   - Agent validation must NOT assume deterministic command inputs

2. **Sentinel / Survivability (Validation Step 12):**
   - Agents enforce policy when Core is offline (cached policy)
   - Policy cache may differ on replay (if Policy Engine is non-deterministic)
   - Survivability validation must NOT assume deterministic policy cache

**Requirements for Downstream Validations:**

- Downstream validations must NOT assume deterministic command inputs (commands may differ on replay)
- Downstream validations must NOT assume deterministic policy cache (policy cache may differ on replay)
- Downstream validations must validate their components based on actual behavior, not assumptions about Policy Engine determinism
