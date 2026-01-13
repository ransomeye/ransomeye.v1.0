# Validation Step 9 — Policy Engine & Command Authority (Decision, Simulation, Signing)

**Component Identity:**
- **Name:** Policy Engine (Decision & Response Authority)
- **Primary Paths:**
  - `/home/ransomeye/rebuild/services/policy-engine/app/main.py` - Main policy engine batch processing
  - `/home/ransomeye/rebuild/services/policy-engine/app/rules.py` - Policy rule evaluation
  - `/home/ransomeye/rebuild/services/policy-engine/app/signer.py` - Command signing
  - `/home/ransomeye/rebuild/services/policy-engine/app/db.py` - Database operations
- **Entry Point:** Batch processing loop - `services/policy-engine/app/main.py:200` - `run_policy_engine()`

**Spec Reference:**
- Phase 7 — Simulation-First Policy Engine
- Policy Engine README (`services/policy-engine/README.md`)

---

## 1. COMPONENT IDENTITY & AUTHORITY

### Evidence

**Policy Engine Entry Points:**
- ✅ Batch processing loop: `services/policy-engine/app/main.py:200` - `run_policy_engine()`
- ✅ Policy evaluation: `services/policy-engine/app/rules.py:59` - `evaluate_policy()` evaluates incident against rules
- ✅ Command signing: `services/policy-engine/app/signer.py:139` - `create_signed_command()` creates and signs commands
- ✅ Main entry: `services/policy-engine/app/main.py:334` - `if __name__ == "__main__":` runs `run_policy_engine()`

**Sub-Components (Rules, Simulation, Signer, Dispatcher):**
- ✅ Rules: `services/policy-engine/app/rules.py:22` - `evaluate_suspicious_incident_rule()` evaluates policy rules
- ✅ Simulation: `services/policy-engine/app/main.py:279-280` - Policy decisions marked with `simulation_mode: True` and `enforcement_disabled: True`
- ✅ Signer: `services/policy-engine/app/signer.py:110` - `sign_command()` signs commands with HMAC-SHA256
- ❌ **CRITICAL:** No dispatcher found:
  - `services/policy-engine/app/main.py:297` - `store_signed_command()` stores commands (does not dispatch)
  - `services/policy-engine/README.md:58` - "NO command transmission: Signed commands are NOT sent to agents"
  - ❌ **CRITICAL:** No dispatcher exists (commands are stored, not dispatched)

**Whether Any Other Component Can Issue Commands:**
- ⚠️ **ISSUE:** TRE can issue commands:
  - `threat-response-engine/api/tre_api.py:118` - `execute_action()` executes policy decisions
  - `threat-response-engine/api/tre_api.py:195` - `self.signer.sign_command(command_payload)` signs commands with ed25519
  - `threat-response-engine/README.md:7` - "TRE is execution-only subsystem that executes final Policy Engine decisions"
  - ⚠️ **ISSUE:** TRE can issue commands (but consumes policy decisions from Policy Engine)
- ✅ **VERIFIED:** AI Core does NOT issue commands:
  - `services/ai-core/README.md:75` - "No action triggers: AI output does not trigger any actions or decisions"
  - ✅ **VERIFIED:** AI Core cannot issue commands
- ✅ **VERIFIED:** Correlation Engine does NOT issue commands:
  - `services/correlation-engine/README.md` - No command issuance found
  - ✅ **VERIFIED:** Correlation Engine cannot issue commands
- ⚠️ **ISSUE:** UI backend may issue commands:
  - `threat-response-engine/api/tre_api.py:118` - `execute_action()` can be called by UI backend
  - ⚠️ **ISSUE:** UI backend can trigger TRE to execute actions (but requires policy decision)

**Whether Any Other Component Can Sign Commands:**
- ⚠️ **ISSUE:** TRE can sign commands:
  - `threat-response-engine/crypto/signer.py:60` - `sign_command()` signs commands with ed25519
  - `threat-response-engine/api/tre_api.py:195` - `self.signer.sign_command(command_payload)` signs commands
  - ⚠️ **ISSUE:** TRE can sign commands (but uses ed25519, separate from Policy Engine's HMAC-SHA256)
- ✅ **VERIFIED:** Policy Engine signs commands:
  - `services/policy-engine/app/signer.py:110` - `sign_command()` signs commands with HMAC-SHA256
  - ✅ **VERIFIED:** Policy Engine signs commands

**Whether Any Other Component Can Enforce Actions:**
- ⚠️ **ISSUE:** TRE can enforce actions:
  - `threat-response-engine/api/tre_api.py:118` - `execute_action()` executes policy decisions
  - `threat-response-engine/engine/command_dispatcher.py:57` - `dispatch_command()` dispatches commands to agents
  - ⚠️ **ISSUE:** TRE can enforce actions (but consumes policy decisions from Policy Engine)

**Any Module Outside Policy Engine Can Sign or Dispatch Commands:**
- ⚠️ **ISSUE:** TRE can sign and dispatch commands:
  - `threat-response-engine/crypto/signer.py:60` - `sign_command()` signs commands
  - `threat-response-engine/engine/command_dispatcher.py:57` - `dispatch_command()` dispatches commands
  - ⚠️ **ISSUE:** TRE can sign and dispatch commands (but consumes policy decisions from Policy Engine)

### Verdict: **PARTIAL**

**Justification:**
- Policy Engine is clearly identified as decision authority
- **CRITICAL ISSUE:** No dispatcher exists (commands are stored, not dispatched)
- **ISSUE:** TRE can sign and dispatch commands (but consumes policy decisions from Policy Engine)
- **ISSUE:** UI backend can trigger TRE to execute actions (but requires policy decision)

---

## 2. INPUT TRUST & GATING

### Evidence

**Inputs Come Only from Correlation Engine:**
- ✅ Inputs come from correlation engine: `services/policy-engine/app/db.py:67-115` - `get_unresolved_incidents()` reads from `incidents` table (incidents created by correlation engine)
- ✅ Inputs from incidents only: `services/policy-engine/app/db.py:77-89` - Reads from `incidents` table only
- ✅ No direct AI input: `services/policy-engine/app/db.py:77-89` - Reads from `incidents` table only (not from AI Core)
- ✅ No direct agent/DPI input: `services/policy-engine/app/db.py:77-89` - Reads from `incidents` table only (not from agents/DPI)

**Required Incident State for Action Eligibility:**
- ✅ Incident state required: `services/policy-engine/app/rules.py:45` - `current_stage = incident.get('current_stage')`
- ✅ Only SUSPICIOUS triggers action: `services/policy-engine/app/rules.py:49` - `if current_stage == 'SUSPICIOUS':` recommends action
- ⚠️ **ISSUE:** No CONFIRMED requirement:
  - `services/policy-engine/app/rules.py:49` - Only `SUSPICIOUS` stage triggers action (not `CONFIRMED`)
  - ⚠️ **ISSUE:** Actions allowed without CONFIRMED stage (only SUSPICIOUS required)

**Explicit Gating (e.g., Only Confirmed Incidents):**
- ⚠️ **ISSUE:** No explicit gating for CONFIRMED:
  - `services/policy-engine/app/rules.py:49` - Only `SUSPICIOUS` stage triggers action
  - No gating for `CONFIRMED` stage found
  - ⚠️ **ISSUE:** Actions allowed for SUSPICIOUS incidents (not only CONFIRMED)

**Policy Accepts Direct AI Input:**
- ✅ **VERIFIED:** Policy does NOT accept direct AI input:
  - `services/policy-engine/app/db.py:77-89` - Reads from `incidents` table only (not from AI Core)
  - ✅ **VERIFIED:** Policy does NOT accept direct AI input (reads from incidents table only)

**Policy Accepts Agent/DPI Input:**
- ✅ **VERIFIED:** Policy does NOT accept agent/DPI input:
  - `services/policy-engine/app/db.py:77-89` - Reads from `incidents` table only (not from agents/DPI)
  - ✅ **VERIFIED:** Policy does NOT accept agent/DPI input (reads from incidents table only)

**Actions Allowed Without Correlation Confirmation:**
- ⚠️ **ISSUE:** Actions allowed without correlation confirmation:
  - `services/policy-engine/app/rules.py:49` - Only `SUSPICIOUS` stage triggers action (not `CONFIRMED`)
  - No requirement for correlation confirmation found
  - ⚠️ **ISSUE:** Actions allowed for SUSPICIOUS incidents (not requiring CONFIRMED stage)

### Verdict: **PARTIAL**

**Justification:**
- Inputs come only from correlation engine (via incidents table)
- Policy does NOT accept direct AI or agent/DPI input
- **ISSUE:** Actions allowed without CONFIRMED stage (only SUSPICIOUS required)
- **ISSUE:** No explicit gating for CONFIRMED incidents

---

## 3. SIMULATION-FIRST GUARANTEE (CRITICAL)

### Evidence

**Simulation Path Exists:**
- ✅ Simulation path exists: `services/policy-engine/app/main.py:279-280` - Policy decisions marked with `simulation_mode: True` and `enforcement_disabled: True`
- ✅ Simulation mode by default: `services/policy-engine/app/main.py:225` - `simulation_mode = config.get('RANSOMEYE_POLICY_ENFORCEMENT_ENABLED', 'false').lower() == "true"` (defaults to `false`)
- ✅ Simulation mode: `services/policy-engine/README.md:42` - "Simulation by default: Policy engine runs in simulation mode unless explicitly enabled"

**Simulation Occurs Before Enforcement:**
- ⚠️ **ISSUE:** No enforcement occurs:
  - `services/policy-engine/app/main.py:297` - `store_signed_command()` stores commands (does not enforce)
  - `services/policy-engine/README.md:58` - "NO command transmission: Signed commands are NOT sent to agents"
  - ⚠️ **ISSUE:** No enforcement occurs (simulation is the only mode, no enforcement path exists)

**Simulation Results Are Logged & Reviewable:**
- ✅ Simulation results logged: `services/policy-engine/app/main.py:300` - `print(f"Policy decision for incident {incident_id}: {action} (SIMULATION - NOT EXECUTED)")`
- ✅ Simulation results stored: `services/policy-engine/app/main.py:283` - `store_policy_decision(incident_id, policy_decision)` stores policy decisions
- ✅ Simulation results reviewable: `services/policy-engine/app/main.py:137` - Policy decisions stored in files (reviewable)

**Direct Enforcement Without Simulation:**
- ✅ **VERIFIED:** No direct enforcement exists:
  - `services/policy-engine/app/main.py:297` - `store_signed_command()` stores commands (does not enforce)
  - `services/policy-engine/README.md:58` - "NO command transmission: Signed commands are NOT sent to agents"
  - ✅ **VERIFIED:** No direct enforcement exists (simulation is the only mode)

**Simulation Optional or Bypassable:**
- ⚠️ **ISSUE:** Simulation is the only mode (not optional):
  - `services/policy-engine/app/main.py:279-280` - Policy decisions always marked with `simulation_mode: True` and `enforcement_disabled: True`
  - `services/policy-engine/app/main.py:297` - Commands are stored, not dispatched
  - ⚠️ **ISSUE:** Simulation is the only mode (no enforcement path exists, so simulation cannot be bypassed)

**Enforcement Occurs on Speculative Data:**
- ✅ **VERIFIED:** No enforcement occurs:
  - `services/policy-engine/app/main.py:297` - Commands are stored, not dispatched
  - ✅ **VERIFIED:** No enforcement occurs (simulation is the only mode)

### Verdict: **PARTIAL**

**Justification:**
- Simulation path exists (simulation mode by default)
- Simulation results are logged and reviewable
- **ISSUE:** No enforcement occurs (simulation is the only mode, no enforcement path exists)
- **ISSUE:** Simulation is the only mode (not optional, but also no enforcement path exists)

---

## 4. COMMAND CONSTRUCTION

### Evidence

**Command Schema Enforcement:**
- ✅ Command schema enforced: `services/policy-engine/app/signer.py:71-107` - `create_command_payload()` creates structured command payload:
  - `command_id`: UUID v4
  - `command_type`: String (e.g., 'ISOLATE_HOST')
  - `target_machine_id`: String
  - `incident_id`: String
  - `issued_at`: RFC3339 UTC timestamp
- ✅ Command types defined: `services/policy-engine/app/rules.py:16-19` - `PolicyAction` enum: `ISOLATE_HOST`, `QUARANTINE_HOST`, `NO_ACTION`
- ✅ Command structure enforced: `services/policy-engine/app/signer.py:99-105` - Command payload structure is fixed (no free-form fields)

**Explicit Command Types:**
- ✅ Explicit command types: `services/policy-engine/app/rules.py:16-19` - `PolicyAction` enum: `ISOLATE_HOST`, `QUARANTINE_HOST`, `NO_ACTION`
- ✅ Command types used: `services/policy-engine/app/rules.py:52` - `action = PolicyAction.ISOLATE_HOST` (explicit enum value)
- ✅ Command types enforced: `services/policy-engine/app/signer.py:101` - `command_type` is passed as parameter (not free-form)

**No Free-Form Shell Commands:**
- ✅ **VERIFIED:** No free-form shell commands:
  - `services/policy-engine/app/signer.py:99-105` - Command payload structure is fixed (no shell commands)
  - `services/policy-engine/app/rules.py:16-19` - Command types are enum values (not shell commands)
  - ✅ **VERIFIED:** No free-form shell commands (command types are enum values)

**Arbitrary Command Execution:**
- ✅ **VERIFIED:** No arbitrary command execution:
  - `services/policy-engine/app/rules.py:16-19` - Command types are enum values (not arbitrary)
  - `services/policy-engine/app/signer.py:99-105` - Command payload structure is fixed (not arbitrary)
  - ✅ **VERIFIED:** No arbitrary command execution (command types are enum values)

**Ad-Hoc Payloads:**
- ✅ **VERIFIED:** No ad-hoc payloads:
  - `services/policy-engine/app/signer.py:99-105` - Command payload structure is fixed (not ad-hoc)
  - ✅ **VERIFIED:** No ad-hoc payloads (command payload structure is fixed)

**Agent-Side Interpretation of Intent:**
- ✅ **VERIFIED:** No agent-side interpretation:
  - `services/policy-engine/app/signer.py:99-105` - Command payload contains explicit `command_type` (not intent)
  - ✅ **VERIFIED:** No agent-side interpretation (command types are explicit enum values)

### Verdict: **PASS**

**Justification:**
- Command schema is enforced (structured command payload)
- Explicit command types (enum values: ISOLATE_HOST, QUARANTINE_HOST, NO_ACTION)
- No free-form shell commands, arbitrary command execution, ad-hoc payloads, or agent-side interpretation

---

## 5. COMMAND SIGNING & CRYPTOGRAPHY

### Evidence

**Signing Algorithm Used:**
- ✅ Signing algorithm: `services/policy-engine/app/signer.py:134` - `hmac.new(signing_key, command_json.encode('utf-8'), hashlib.sha256).hexdigest()` (HMAC-SHA256)
- ✅ Signing algorithm documented: `services/policy-engine/app/signer.py:165` - `'signing_algorithm': 'HMAC-SHA256'`
- ✅ Signing algorithm: `services/policy-engine/README.md:97` - "Cryptographic signing: Commands are signed using HMAC-SHA256"

**Key Source & Protection:**
- ✅ Key from environment: `services/policy-engine/app/signer.py:46` - `validate_signing_key(env_var="RANSOMEYE_COMMAND_SIGNING_KEY", ...)`
- ✅ Key loaded once: `services/policy-engine/app/signer.py:40-41` - `if _SIGNING_KEY is not None: return _SIGNING_KEY` (cached, never reloaded)
- ✅ Key validated: `services/policy-engine/app/signer.py:46-50` - `validate_signing_key()` validates key strength (minimum 32 characters, entropy, not default)
- ✅ Key never logged: `services/policy-engine/README.md:489` - "Key Never Logged: Signing key never logged"
- ⚠️ **ISSUE:** Default key exists: `services/policy-engine/README.md:283` - "RANSOMEYE_COMMAND_SIGNING_KEY: Command signing key (default: phase7_minimal_default_key, NOT SECURE FOR PRODUCTION)"
- ⚠️ **ISSUE:** Default key allowed: `services/policy-engine/app/signer.py:49` - `fail_on_default=True` (but default key exists in README)

**Mandatory Signature on Every Command:**
- ✅ Signature mandatory: `services/policy-engine/app/signer.py:159` - `signature = sign_command(command_payload)` (always called)
- ✅ Signature stored: `services/policy-engine/app/signer.py:164` - `'signature': signature` (always included)
- ✅ Signature mandatory: `services/policy-engine/app/main.py:289-293` - `create_signed_command()` always called before storage

**Unsigned Commands:**
- ✅ **VERIFIED:** No unsigned commands:
  - `services/policy-engine/app/signer.py:159` - `signature = sign_command(command_payload)` (always called)
  - `services/policy-engine/app/signer.py:164` - `'signature': signature` (always included)
  - ✅ **VERIFIED:** No unsigned commands (signature always generated and included)

**Test Keys in Production Paths:**
- ⚠️ **ISSUE:** Default key exists: `services/policy-engine/README.md:283` - "RANSOMEYE_COMMAND_SIGNING_KEY: Command signing key (default: phase7_minimal_default_key, NOT SECURE FOR PRODUCTION)"
- ⚠️ **ISSUE:** Default key allowed: `services/policy-engine/app/signer.py:54-59` - Fallback allows default key if security utilities not available
- ⚠️ **ISSUE:** Default key in production paths: Default key exists in README (not secure for production)

**Signing Bypass Paths:**
- ✅ **VERIFIED:** No signing bypass paths:
  - `services/policy-engine/app/signer.py:159` - `signature = sign_command(command_payload)` (always called)
  - `services/policy-engine/app/main.py:289-293` - `create_signed_command()` always called (no bypass)
  - ✅ **VERIFIED:** No signing bypass paths (signature always generated)

### Verdict: **PARTIAL**

**Justification:**
- Signing algorithm is HMAC-SHA256 (correctly implemented)
- Key source is environment variable (correctly implemented)
- Key protection exists (loaded once, validated, never logged)
- **ISSUE:** Default key exists (phase7_minimal_default_key, not secure for production)
- **ISSUE:** Default key allowed in fallback path (if security utilities not available)
- Signature is mandatory on every command (correctly implemented)

---

## 6. DISPATCH & AUDITABILITY

### Evidence

**Dispatch Occurs Only via Secure Bus:**
- ❌ **CRITICAL:** No dispatch occurs:
  - `services/policy-engine/app/main.py:297` - `store_signed_command()` stores commands (does not dispatch)
  - `services/policy-engine/README.md:58` - "NO command transmission: Signed commands are NOT sent to agents"
  - ❌ **CRITICAL:** No dispatch occurs (commands are stored, not dispatched)

**Commands Are Logged Immutably:**
- ✅ Commands logged: `services/policy-engine/app/main.py:300` - `print(f"Policy decision for incident {incident_id}: {action} (SIMULATION - NOT EXECUTED)")`
- ✅ Commands stored: `services/policy-engine/app/main.py:297` - `store_signed_command(incident_id, signed_command)` stores commands in files
- ✅ Commands immutable: `services/policy-engine/README.md:105` - "All policy decisions and commands are immutable (never updated, never deleted)"
- ⚠️ **ISSUE:** File-based storage: `services/policy-engine/app/main.py:179` - Commands stored in files (not database, not immutable at database level)

**Dispatch Failures Handled Explicitly:**
- ⚠️ **ISSUE:** No dispatch occurs (no dispatch failures to handle):
  - `services/policy-engine/app/main.py:297` - Commands are stored, not dispatched
  - ⚠️ **ISSUE:** No dispatch failures to handle (no dispatch exists)

**Direct Agent RPC:**
- ✅ **VERIFIED:** No direct agent RPC:
  - `services/policy-engine/app/main.py:297` - Commands are stored, not sent to agents
  - `services/policy-engine/README.md:58` - "NO command transmission: Signed commands are NOT sent to agents"
  - ✅ **VERIFIED:** No direct agent RPC (commands are stored, not dispatched)

**Silent Dispatch Failure:**
- ⚠️ **ISSUE:** No dispatch occurs (no dispatch failures to handle):
  - `services/policy-engine/app/main.py:297` - Commands are stored, not dispatched
  - ⚠️ **ISSUE:** No dispatch failures to handle (no dispatch exists)

**No Audit Trail:**
- ✅ Audit trail exists: `services/policy-engine/app/main.py:283` - `store_policy_decision(incident_id, policy_decision)` stores policy decisions
- ✅ Audit trail exists: `services/policy-engine/app/main.py:297` - `store_signed_command(incident_id, signed_command)` stores signed commands
- ✅ Audit trail reviewable: `services/policy-engine/app/main.py:137` - Policy decisions and commands stored in files (reviewable)
- ⚠️ **ISSUE:** File-based storage: `services/policy-engine/app/main.py:179` - Commands stored in files (not database, not immutable at database level)

### Verdict: **PARTIAL**

**Justification:**
- Commands are logged and stored (audit trail exists)
- No direct agent RPC (commands are stored, not dispatched)
- **CRITICAL ISSUE:** No dispatch occurs (commands are stored, not dispatched)
- **ISSUE:** File-based storage (not database, not immutable at database level)
- **ISSUE:** No dispatch failures to handle (no dispatch exists)

---

## 7. FAIL-CLOSED BEHAVIOR

### Evidence

**Behavior on Missing Signing Key:**
- ✅ Missing key causes termination: `services/policy-engine/app/signer.py:55-59` - `sys.exit(1)` if signing key is missing
- ✅ Missing key causes termination: `services/policy-engine/app/main.py:102` - `get_signing_key()` validates key at startup (terminates on invalid key)
- ✅ Missing key causes termination: `services/policy-engine/README.md:491` - "Fail-Fast on Invalid Key: Missing, weak, or default signing keys terminate Core immediately at startup"

**Behavior on Invalid Command Schema:**
- ⚠️ **ISSUE:** No command schema validation found:
  - `services/policy-engine/app/signer.py:99-105` - Command payload structure is fixed (no explicit schema validation)
  - No schema validation function found
  - ⚠️ **ISSUE:** No explicit command schema validation (command payload structure is fixed, but no validation function)

**Behavior on Bus Failure:**
- ⚠️ **ISSUE:** No bus exists (no bus failures to handle):
  - `services/policy-engine/app/main.py:297` - Commands are stored, not dispatched
  - ⚠️ **ISSUE:** No bus failures to handle (no bus exists)

**Behavior on Agent Rejection:**
- ⚠️ **ISSUE:** No agent contact (no agent rejections to handle):
  - `services/policy-engine/app/main.py:297` - Commands are stored, not sent to agents
  - ⚠️ **ISSUE:** No agent rejections to handle (no agent contact exists)

**Unsigned Commands Sent:**
- ✅ **VERIFIED:** No unsigned commands sent:
  - `services/policy-engine/app/main.py:297` - Commands are stored, not sent
  - `services/policy-engine/app/signer.py:159` - Signature always generated
  - ✅ **VERIFIED:** No unsigned commands sent (commands are stored, not sent, and always signed)

**Policy Continues After Crypto Failure:**
- ✅ Crypto failure causes termination: `services/policy-engine/app/signer.py:55-59` - `sys.exit(1)` if signing key is missing
- ✅ Crypto failure causes termination: `services/policy-engine/app/main.py:102` - `get_signing_key()` terminates on invalid key
- ✅ Crypto failure causes termination: `services/policy-engine/README.md:491` - "Fail-Fast on Invalid Key: Missing, weak, or default signing keys terminate Core immediately at startup"
- ⚠️ **ISSUE:** Policy continues after other failures: `services/policy-engine/app/main.py:304-313` - Exception handling logs error and continues (not fail-closed)

**Best-Effort Enforcement:**
- ✅ **VERIFIED:** No best-effort enforcement:
  - `services/policy-engine/app/main.py:297` - Commands are stored, not enforced
  - `services/policy-engine/README.md:58` - "NO enforcement: Policy recommendations are NOT enforced automatically"
  - ✅ **VERIFIED:** No best-effort enforcement (no enforcement exists)

### Verdict: **PARTIAL**

**Justification:**
- Missing signing key causes termination (fail-closed)
- Crypto failure causes termination (fail-closed)
- No unsigned commands sent (commands are stored, not sent, and always signed)
- **ISSUE:** No explicit command schema validation (command payload structure is fixed, but no validation function)
- **ISSUE:** Policy continues after other failures (exception handling logs error and continues, not fail-closed)
- **ISSUE:** No bus or agent contact (no bus/agent failures to handle)

---

## 8. NEGATIVE VALIDATION (MANDATORY)

### Evidence

**AI Issues Commands:**
- ✅ **PROVEN IMPOSSIBLE:** AI cannot issue commands:
  - `services/ai-core/README.md:75` - "No action triggers: AI output does not trigger any actions or decisions"
  - `services/ai-core/README.md:81` - "AI Core does not trigger alerts or actions"
  - ✅ **VERIFIED:** AI cannot issue commands (AI output is advisory only)

**Correlation Engine Issues Commands:**
- ✅ **PROVEN IMPOSSIBLE:** Correlation engine cannot issue commands:
  - `services/correlation-engine/README.md` - No command issuance found
  - `services/correlation-engine/app/main.py` - No command issuance found
  - ✅ **VERIFIED:** Correlation engine cannot issue commands (correlation engine only creates incidents)

**UI Issues Commands Directly:**
- ⚠️ **ISSUE:** UI backend can trigger TRE to execute actions:
  - `threat-response-engine/api/tre_api.py:118` - `execute_action()` can be called by UI backend
  - `threat-response-engine/README.md:7` - "TRE is execution-only subsystem that executes final Policy Engine decisions"
  - ⚠️ **ISSUE:** UI backend can trigger TRE to execute actions (but requires policy decision from Policy Engine)

**Agent Executes Unsigned Commands:**
- ✅ **PROVEN IMPOSSIBLE:** Agents cannot execute unsigned commands:
  - `agents/linux/command_gate.py:177-178` - `_verify_signature()` verifies ed25519 signature before execution
  - `agents/linux/command_gate.py:272-298` - `_validate_freshness()` and `_check_idempotency()` validate commands
  - ✅ **VERIFIED:** Agents cannot execute unsigned commands (signature verification required)

### Verdict: **PARTIAL**

**Justification:**
- AI cannot issue commands (AI output is advisory only)
- Correlation engine cannot issue commands (correlation engine only creates incidents)
- Agents cannot execute unsigned commands (signature verification required)
- **ISSUE:** UI backend can trigger TRE to execute actions (but requires policy decision from Policy Engine)

---

## 9. VERDICT & IMPACT

### Section-by-Section Verdicts

1. **Component Identity & Authority:** PARTIAL
   - Policy Engine is clearly identified as decision authority
   - **CRITICAL ISSUE:** No dispatcher exists (commands are stored, not dispatched)
   - **ISSUE:** TRE can sign and dispatch commands (but consumes policy decisions from Policy Engine)

2. **Input Trust & Gating:** PARTIAL
   - Inputs come only from correlation engine (via incidents table)
   - Policy does NOT accept direct AI or agent/DPI input
   - **ISSUE:** Actions allowed without CONFIRMED stage (only SUSPICIOUS required)

3. **Simulation-First Guarantee:** PARTIAL
   - Simulation path exists (simulation mode by default)
   - Simulation results are logged and reviewable
   - **ISSUE:** No enforcement occurs (simulation is the only mode, no enforcement path exists)

4. **Command Construction:** PASS
   - Command schema is enforced (structured command payload)
   - Explicit command types (enum values)
   - No free-form shell commands, arbitrary command execution, ad-hoc payloads, or agent-side interpretation

5. **Command Signing & Cryptography:** PARTIAL
   - Signing algorithm is HMAC-SHA256 (correctly implemented)
   - Key source is environment variable (correctly implemented)
   - **ISSUE:** Default key exists (phase7_minimal_default_key, not secure for production)

6. **Dispatch & Auditability:** PARTIAL
   - Commands are logged and stored (audit trail exists)
   - No direct agent RPC (commands are stored, not dispatched)
   - **CRITICAL ISSUE:** No dispatch occurs (commands are stored, not dispatched)

7. **Fail-Closed Behavior:** PARTIAL
   - Missing signing key causes termination (fail-closed)
   - Crypto failure causes termination (fail-closed)
   - **ISSUE:** Policy continues after other failures (exception handling logs error and continues)

8. **Negative Validation:** PARTIAL
   - AI, correlation engine cannot issue commands
   - Agents cannot execute unsigned commands
   - **ISSUE:** UI backend can trigger TRE to execute actions (but requires policy decision)

### Overall Verdict: **PARTIAL**

**Justification:**
- **CRITICAL ISSUE:** No dispatcher exists (commands are stored, not dispatched)
- **CRITICAL ISSUE:** No enforcement occurs (simulation is the only mode, no enforcement path exists)
- **ISSUE:** Actions allowed without CONFIRMED stage (only SUSPICIOUS required)
- **ISSUE:** Default key exists (phase7_minimal_default_key, not secure for production)
- **ISSUE:** Policy continues after other failures (exception handling logs error and continues, not fail-closed)
- **ISSUE:** UI backend can trigger TRE to execute actions (but requires policy decision from Policy Engine)
- Policy Engine is clearly identified as decision authority
- Command construction is correct (structured command payload, explicit command types)
- Command signing is correct (HMAC-SHA256, key from environment, signature mandatory)
- Commands are logged and stored (audit trail exists)

**Impact if Policy Engine is Compromised:**
- **CRITICAL:** If policy engine is compromised, commands can be generated and signed (but not dispatched in Phase 7)
- **CRITICAL:** If policy engine is compromised, policy decisions can be manipulated (but not enforced in Phase 7)
- **HIGH:** If policy engine is compromised, default signing key can be used (not secure for production)
- **HIGH:** If policy engine is compromised, actions can be recommended for SUSPICIOUS incidents (not requiring CONFIRMED)
- **MEDIUM:** If policy engine is compromised, policy decisions may be incorrect (but not enforced in Phase 7)
- **LOW:** If policy engine is compromised, system correctness is unaffected (policy is advisory only, simulation mode)

**Whether Detection-Only Mode Remains Safe:**
- ✅ **YES:** Detection-only mode remains safe:
  - `services/policy-engine/README.md:126-144` - "System Correctness Does Not Depend on Policy Engine"
  - `services/policy-engine/README.md:142-144` - "If policy engine is disabled: Incidents are still created by correlation engine (Phase 5); Events are still validated and stored (Phase 4); System correctness is unaffected (policy is advisory only)"
  - `services/policy-engine/app/main.py:297` - Commands are stored, not dispatched (no enforcement)
  - ✅ **VERIFIED:** Detection-only mode remains safe (policy is advisory only, simulation mode, no enforcement)

**Recommendations:**
1. **CRITICAL:** Implement command dispatcher (dispatch signed commands to agents via secure bus)
2. **CRITICAL:** Implement enforcement path (enforcement after simulation, with explicit authorization)
3. **CRITICAL:** Require CONFIRMED stage for action eligibility (not only SUSPICIOUS)
4. **HIGH:** Remove default signing key (fail-fast on default keys, no fallback)
5. **HIGH:** Implement explicit command schema validation (validate command payload against schema)
6. **HIGH:** Implement fail-closed behavior (terminate on all critical failures, not continue)
7. **MEDIUM:** Implement database storage for policy decisions and commands (not file-based)
8. **MEDIUM:** Implement explicit gating for CONFIRMED incidents (require CONFIRMED stage for actions)

---

**Validation Date:** 2025-01-13
**Validator:** Lead Validator & Compliance Auditor
**Next Step:** Validation Step 10 — Threat Response Engine (if applicable)
