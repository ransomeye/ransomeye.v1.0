# Validation Step 10 — Endpoint Agents (Linux & Windows) Execution, Trust & Safety Boundaries

**Component Identity:**
- **Name:** Endpoint Agents (Linux Agent + Windows Agent)
- **Primary Paths:**
  - `/home/ransomeye/rebuild/agents/linux/agent_main.py` - Linux agent main entry point
  - `/home/ransomeye/rebuild/agents/linux/command_gate.py` - Linux command acceptance gate
  - `/home/ransomeye/rebuild/agents/windows/agent/agent_main.py` - Windows agent main entry point
  - `/home/ransomeye/rebuild/agents/windows/command_gate.ps1` - Windows command acceptance gate
- **Entry Points:**
  - Linux: `agents/linux/agent_main.py:34` - `LinuxAgent` class
  - Windows: `agents/windows/agent/agent_main.py:43` - `WindowsAgent` class

**Spec Reference:**
- Agent Enforcement Compliance (`agents/AGENT_ENFORCEMENT_COMPLIANCE.md`)
- Agent Enforcement Verification (`agents/AGENT_ENFORCEMENT_VERIFICATION.md`)

---

## 1. COMPONENT IDENTITY & ROLE

### Evidence

**Agent Entry Points:**
- ✅ Linux agent entry: `agents/linux/agent_main.py:34` - `LinuxAgent` class with `receive_command()` method
- ✅ Windows agent entry: `agents/windows/agent/agent_main.py:43` - `WindowsAgent` class with `start()` method
- ✅ Linux command gate: `agents/linux/command_gate.py:47` - `CommandGate` class with `receive_command()` method
- ✅ Windows command gate: `agents/windows/command_gate.ps1:26` - `Receive-Command` function

**Supported Platforms:**
- ✅ Linux: `agents/linux/agent_main.py` - Python 3.10+ agent for Linux
- ✅ Windows: `agents/windows/agent/agent_main.py` - Python 3.10+ agent for Windows with ETW telemetry

**Explicit Statement of What Agents Can Do:**
- ✅ Linux agent: `agents/linux/agent_main.py:36-39` - "Linux Agent - Command receiver and executor. CRITICAL: Agents NEVER trust the network, NEVER trust the UI. Agents ONLY trust signed commands. FAIL CLOSED."
- ✅ Windows agent: `agents/windows/agent/agent_main.py:45-48` - "Windows Agent - ETW telemetry and command execution. CRITICAL: Agents NEVER trust the network, NEVER trust the UI. Agents ONLY trust signed commands. FAIL CLOSED."
- ✅ Command gate: `agents/linux/command_gate.py:51-52` - "CRITICAL: Agents NEVER trust the network, NEVER trust the UI. Agents ONLY trust signed commands. FAIL CLOSED."

**Explicit Statement of What Agents Must Never Do:**
- ✅ Linux agent: `agents/linux/agent_main.py:36-39` - "Agents NEVER trust the network, NEVER trust the UI. Agents ONLY trust signed commands."
- ✅ Windows agent: `agents/windows/agent/agent_main.py:45-48` - "Agents NEVER trust the network, NEVER trust the UI. Agents ONLY trust signed commands."
- ✅ Command gate: `agents/linux/command_gate.py:51-52` - "Agents NEVER trust the network, NEVER trust the UI. Agents ONLY trust signed commands."

**Agent Makes Enforcement Decisions:**
- ✅ **VERIFIED:** Agents do NOT make enforcement decisions:
  - `agents/linux/agent_main.py:86-93` - Agents execute commands based on `action_type` (no decision-making)
  - `agents/linux/command_gate.py:133-193` - Command gate validates commands (does not make decisions)
  - ✅ **VERIFIED:** Agents do NOT make enforcement decisions (agents execute commands, do not decide)

**Agent Escalates Incidents:**
- ✅ **VERIFIED:** Agents do NOT escalate incidents:
  - `agents/linux/agent_main.py:70-127` - Agents execute commands (do not escalate incidents)
  - `agents/windows/agent/agent_main.py:164-226` - Windows agent sends telemetry (does not escalate incidents)
  - ✅ **VERIFIED:** Agents do NOT escalate incidents (agents execute commands and send telemetry, do not escalate)

**Agent Writes to DB:**
- ✅ **VERIFIED:** Agents do NOT write to DB:
  - `agents/windows/agent/telemetry/sender.py:157-187` - Windows agent sends telemetry via HTTP POST (not direct DB write)
  - `agents/linux/agent_main.py:70-127` - Linux agent executes commands (no DB writes found)
  - ✅ **VERIFIED:** Agents do NOT write to DB (agents send telemetry via HTTP, do not write to DB)

### Verdict: **PASS**

**Justification:**
- Agent entry points are clearly identified
- Supported platforms are Linux and Windows
- Explicit statements of what agents can do (execute signed commands, send telemetry)
- Explicit statements of what agents must never do (never trust network/UI, only trust signed commands)
- Agents do NOT make enforcement decisions, escalate incidents, or write to DB

---

## 2. STARTUP & FAIL-CLOSED BEHAVIOR

### Evidence

**Behavior on Missing Config:**
- ⚠️ **ISSUE:** Windows agent can start without signing key:
  - `agents/windows/agent/telemetry/signer.py:64-83` - `TelemetrySigner` initializes without signing key if key path not provided (logs warning, continues)
  - `agents/windows/agent/agent_main.py:97-100` - `TelemetrySigner` initialized with optional `signing_key_path` (not required)
  - ⚠️ **ISSUE:** Windows agent can start without signing key (fail-open behavior)
- ✅ Linux agent requires TRE public key: `agents/linux/agent_main.py:42-49` - `LinuxAgent` requires `tre_public_key` and `tre_key_id` (mandatory parameters)
- ⚠️ **ISSUE:** Linux agent can start without verifier: `agents/linux/command_gate.py:92-101` - If PyNaCl not available or `tre_public_key` is None, `verifier` is set to None (no termination)

**Behavior on Missing Signing Verification Key:**
- ⚠️ **ISSUE:** Linux agent can start without verifier: `agents/linux/command_gate.py:92-101` - If PyNaCl not available or `tre_public_key` is None, `verifier` is set to None (no termination)
- ⚠️ **ISSUE:** Windows agent can start without signing key: `agents/windows/agent/telemetry/signer.py:64-83` - `TelemetrySigner` initializes without signing key (logs warning, continues)
- ⚠️ **ISSUE:** Windows agent startup: `agents/windows/agent/agent_main.py:311-313` - If `agent.start()` returns False, agent exits with `sys.exit(1)` (but startup can succeed without signing key)

**Behavior on Missing Secure Bus Connectivity:**
- ⚠️ **ISSUE:** Windows agent can start without core endpoint: `agents/windows/agent/agent_main.py:102-103` - `core_endpoint` is optional (defaults to environment variable)
- ⚠️ **ISSUE:** Windows agent buffers events if offline: `agents/windows/agent/telemetry/sender.py:83-88` - Events are buffered if Core unavailable (fail-open behavior)
- ⚠️ **ISSUE:** Windows agent continues without connectivity: `agents/windows/agent/telemetry/sender.py:121-152` - Transmission loop continues even if Core unavailable (fail-open behavior)

**Behavior on Corrupt Local State:**
- ⚠️ **ISSUE:** No explicit corrupt state handling found:
  - `agents/linux/command_gate.py:103-105` - `_ensure_audit_log()` creates audit log directory (no validation)
  - `agents/windows/agent/etw/buffer_manager.py` - Buffer manager handles events (no explicit corrupt state handling)
  - ⚠️ **ISSUE:** No explicit corrupt state handling (agents continue operation)

**Agent Runs in Degraded Mode:**
- ⚠️ **ISSUE:** Windows agent runs in degraded mode:
  - `agents/windows/agent/telemetry/signer.py:64-83` - Agent can run without signing key (degraded mode)
  - `agents/windows/agent/agent_main.py:131-133` - Agent can start even if ETW session fails (returns False, but no termination)
  - ⚠️ **ISSUE:** Windows agent runs in degraded mode (can run without signing key or ETW session)

**Agent Emits Telemetry Without Trust Established:**
- ⚠️ **ISSUE:** Windows agent can emit telemetry without signing key:
  - `agents/windows/agent/telemetry/signer.py:85-122` - `sign_envelope()` can sign without signer (signature is None if signer not available)
  - `agents/windows/agent/agent_main.py:217` - Envelope is signed (but signature may be None if signer not available)
  - ⚠️ **ISSUE:** Windows agent can emit telemetry without signing key (unsigned telemetry possible)

**Agent Accepts Commands Before Validation Completes:**
- ✅ **VERIFIED:** Linux agent validates commands before execution:
  - `agents/linux/command_gate.py:133-193` - `receive_command()` validates command through 8-step pipeline before returning
  - `agents/linux/agent_main.py:84` - Command is validated before execution
  - ✅ **VERIFIED:** Linux agent validates commands before execution (validation completes before acceptance)
- ⚠️ **ISSUE:** Linux agent can accept commands without verifier: `agents/linux/command_gate.py:312-313` - If verifier not available, command is rejected (but agent can start without verifier)

### Verdict: **PARTIAL**

**Justification:**
- Linux agent requires TRE public key (mandatory parameter)
- **ISSUE:** Windows agent can start without signing key (fail-open behavior)
- **ISSUE:** Linux agent can start without verifier (if PyNaCl not available, verifier is None)
- **ISSUE:** Windows agent can emit telemetry without signing key (unsigned telemetry possible)
- **ISSUE:** Windows agent runs in degraded mode (can run without signing key or ETW session)
- **ISSUE:** No explicit corrupt state handling (agents continue operation)
- Linux agent validates commands before execution (validation completes before acceptance)

---

## 3. TELEMETRY EMISSION & AUTHENTICATION

### Evidence

**Telemetry Signing:**
- ✅ Windows agent signs telemetry: `agents/windows/agent/telemetry/signer.py:85-122` - `sign_envelope()` signs envelope with ed25519
- ✅ Windows agent signs telemetry: `agents/windows/agent/agent_main.py:217` - `self.telemetry_signer.sign_envelope(envelope)` signs envelope
- ⚠️ **ISSUE:** Windows agent can sign without signer: `agents/windows/agent/telemetry/signer.py:108-115` - If signer not available, signature is None (unsigned telemetry possible)
- ⚠️ **ISSUE:** Windows agent can emit unsigned telemetry: `agents/windows/agent/telemetry/signer.py:118-120` - If signature is None, envelope is returned without signature (unsigned telemetry)

**Identity Binding (host_id, agent_id):**
- ✅ Windows agent binds identity: `agents/windows/agent/telemetry/event_envelope.py:29-137` - `EventEnvelopeBuilder` binds `machine_id`, `component_instance_id` (agent_id), `hostname`, `boot_id`
- ✅ Windows agent binds identity: `agents/windows/agent/agent_main.py:90-95` - `EventEnvelopeBuilder` initialized with `machine_id`, `component_instance_id` (agent_id), `hostname`, `boot_id`
- ✅ Linux agent binds identity: `agents/linux/command_gate.py:119` - `agent_id` is included in audit log events

**Schema Enforcement Before Emission:**
- ✅ Windows agent enforces schema: `agents/windows/agent/etw/schema_mapper.py` - `SchemaMapper` maps ETW events to normalized schemas
- ✅ Windows agent enforces schema: `agents/windows/agent/agent_main.py:199` - `self.schema_mapper.map_to_normalized(parsed_event)` enforces schema
- ✅ Windows agent enforces schema: `agents/windows/agent/telemetry/event_envelope.py:29-137` - `EventEnvelopeBuilder` builds envelope with schema enforcement

**Unsigned Telemetry:**
- ⚠️ **ISSUE:** Windows agent can emit unsigned telemetry:
  - `agents/windows/agent/telemetry/signer.py:108-115` - If signer not available, signature is None
  - `agents/windows/agent/telemetry/signer.py:118-120` - If signature is None, envelope is returned without signature
  - ⚠️ **ISSUE:** Windows agent can emit unsigned telemetry (if signer not available)

**Host Identity Inferred from Config Only:**
- ⚠️ **ISSUE:** Windows agent infers host identity from config:
  - `agents/windows/agent/agent_main.py:78-79` - `machine_id = machine_id or socket.gethostname()` (defaults to hostname)
  - `agents/windows/agent/agent_main.py:79` - `hostname = hostname or socket.gethostname()` (defaults to hostname)
  - ⚠️ **ISSUE:** Host identity inferred from config/hostname (not cryptographically bound)

**Schema-Less Emission:**
- ✅ **VERIFIED:** Windows agent enforces schema:
  - `agents/windows/agent/etw/schema_mapper.py` - `SchemaMapper` maps events to normalized schemas
  - `agents/windows/agent/agent_main.py:199` - Schema mapping enforced before emission
  - ✅ **VERIFIED:** Windows agent enforces schema (schema mapping enforced before emission)

### Verdict: **PARTIAL**

**Justification:**
- Windows agent signs telemetry with ed25519 (correctly implemented)
- Identity binding exists (machine_id, agent_id, hostname, boot_id)
- Schema enforcement exists (schema mapping enforced before emission)
- **ISSUE:** Windows agent can emit unsigned telemetry (if signer not available)
- **ISSUE:** Host identity inferred from config/hostname (not cryptographically bound)

---

## 4. COMMAND EXECUTION GATE (CRITICAL)

### Evidence

**Signature Verification Before Execution:**
- ✅ Linux agent verifies signature: `agents/linux/command_gate.py:302-334` - `_verify_signature()` verifies ed25519 signature before execution
- ✅ Linux agent verifies signature: `agents/linux/command_gate.py:166` - `_verify_signature(command)` called before execution
- ⚠️ **ISSUE:** Linux agent can verify without verifier: `agents/linux/command_gate.py:312-313` - If verifier not available, command is rejected (but agent can start without verifier)
- ⚠️ **ISSUE:** Windows command gate has placeholder: `agents/windows/command_gate.ps1:122-129` - `Test-CommandSignature` has placeholder for signature verification (not implemented)

**Command Schema Validation:**
- ✅ Linux agent validates schema: `agents/linux/command_gate.py:195-270` - `_validate_schema()` validates command schema (required fields, UUIDs, enums, timestamps)
- ✅ Linux agent validates schema: `agents/linux/command_gate.py:160` - `_validate_schema(command)` called before execution
- ✅ Windows command gate validates schema: `agents/windows/command_gate.ps1:67-103` - `Test-CommandSchema` validates command schema

**Explicit Allow-List of Command Types:**
- ✅ Linux agent has allow-list: `agents/linux/command_gate.py:241-247` - `valid_action_types` defines allowed action types (BLOCK_PROCESS, BLOCK_NETWORK_CONNECTION, etc.)
- ✅ Linux agent enforces allow-list: `agents/linux/command_gate.py:246-247` - If `action_type` not in allow-list, command is rejected
- ✅ Windows command gate has allow-list: `agents/windows/command_gate.ps1:82-86` - `ValidActionTypes` defines allowed action types

**Unsigned Command Execution:**
- ✅ **VERIFIED:** Linux agent does NOT execute unsigned commands:
  - `agents/linux/command_gate.py:302-334` - `_verify_signature()` verifies signature before execution
  - `agents/linux/command_gate.py:312-313` - If verifier not available, command is rejected
  - ✅ **VERIFIED:** Linux agent does NOT execute unsigned commands (signature verification required)
- ⚠️ **ISSUE:** Windows command gate has placeholder: `agents/windows/command_gate.ps1:122-129` - `Test-CommandSignature` has placeholder (not implemented)

**Arbitrary Shell Execution:**
- ✅ **VERIFIED:** Linux agent does NOT execute arbitrary shell commands:
  - `agents/linux/execution/process_blocker.py:75` - `subprocess.run(['kill', '-9', str(process_id)], check=True, capture_output=True)` (explicit command, not shell)
  - `agents/linux/agent_main.py:86-93` - Agents execute based on `action_type` enum (not arbitrary)
  - ✅ **VERIFIED:** Linux agent does NOT execute arbitrary shell commands (explicit commands, not shell)

**Partial Command Verification:**
- ✅ **VERIFIED:** Linux agent verifies all steps:
  - `agents/linux/command_gate.py:133-193` - `receive_command()` validates through 8-step pipeline (all steps must pass)
  - `agents/linux/command_gate.py:188-193` - If any step fails, command is rejected
  - ✅ **VERIFIED:** Linux agent verifies all steps (8-step pipeline, all steps must pass)

### Verdict: **PARTIAL**

**Justification:**
- Linux agent verifies signature before execution (ed25519 signature verification)
- Command schema validation exists (required fields, UUIDs, enums, timestamps)
- Explicit allow-list of command types exists (BLOCK_PROCESS, BLOCK_NETWORK_CONNECTION, etc.)
- Linux agent does NOT execute unsigned commands or arbitrary shell commands
- **ISSUE:** Windows command gate has placeholder for signature verification (not implemented)
- **ISSUE:** Linux agent can start without verifier (if PyNaCl not available, verifier is None)

---

## 5. PRIVILEGE & SANDBOXING

### Evidence

**Required Privileges Per Action:**
- ⚠️ **ISSUE:** No explicit privilege checks found:
  - `agents/linux/execution/process_blocker.py:75` - `subprocess.run(['kill', '-9', str(process_id)])` (requires appropriate privileges, but no explicit check)
  - `agents/linux/execution/process_blocker.py:78` - `_add_to_cgroup_deny(process_id)` (requires appropriate privileges, but no explicit check)
  - ⚠️ **ISSUE:** No explicit privilege checks (actions require appropriate privileges, but no explicit validation)

**Separation of Monitoring vs Execution:**
- ✅ Linux agent separates monitoring and execution: `agents/linux/agent_main.py:34-68` - `LinuxAgent` has separate `command_gate` (execution) and no monitoring component (Linux agent is execution-only)
- ✅ Windows agent separates monitoring and execution: `agents/windows/agent/agent_main.py:43-120` - `WindowsAgent` has separate ETW components (monitoring) and command gate (execution)
- ⚠️ **ISSUE:** No explicit separation enforcement found (components are separate, but no explicit enforcement)

**Abuse Resistance (e.g., Command Injection):**
- ✅ Linux agent resists command injection: `agents/linux/execution/process_blocker.py:75` - `subprocess.run(['kill', '-9', str(process_id)], check=True, capture_output=True)` (explicit command, not shell, no user input)
- ✅ Linux agent resists command injection: `agents/linux/command_gate.py:241-247` - Action types are enum values (not user input)
- ✅ Linux agent resists command injection: `agents/linux/command_gate.py:266-270` - Unknown fields are rejected (prevents injection)

**Agent Runs Everything as Root Without Separation:**
- ⚠️ **ISSUE:** No explicit privilege separation found:
  - `agents/linux/execution/process_blocker.py:75` - `subprocess.run(['kill', '-9', str(process_id)])` (requires appropriate privileges, but no explicit separation)
  - ⚠️ **ISSUE:** No explicit privilege separation (actions require appropriate privileges, but no explicit separation)

**Command Execution Shares Telemetry Privileges:**
- ✅ **VERIFIED:** Linux agent separates execution and telemetry:
  - `agents/linux/agent_main.py:34-68` - `LinuxAgent` has `command_gate` (execution) and no telemetry component (Linux agent is execution-only)
  - ✅ **VERIFIED:** Linux agent separates execution and telemetry (Linux agent is execution-only, no telemetry)
- ✅ **VERIFIED:** Windows agent separates execution and telemetry:
  - `agents/windows/agent/agent_main.py:43-120` - `WindowsAgent` has separate ETW components (telemetry) and command gate (execution)
  - ✅ **VERIFIED:** Windows agent separates execution and telemetry (components are separate)

**Unsafe Shell Invocation:**
- ✅ **VERIFIED:** Linux agent does NOT use unsafe shell invocation:
  - `agents/linux/execution/process_blocker.py:75` - `subprocess.run(['kill', '-9', str(process_id)], check=True, capture_output=True)` (explicit command, not shell)
  - ✅ **VERIFIED:** Linux agent does NOT use unsafe shell invocation (explicit commands, not shell)

### Verdict: **PARTIAL**

**Justification:**
- Separation of monitoring vs execution exists (components are separate)
- Abuse resistance exists (explicit commands, not shell, enum values, unknown fields rejected)
- Linux agent does NOT use unsafe shell invocation (explicit commands, not shell)
- **ISSUE:** No explicit privilege checks (actions require appropriate privileges, but no explicit validation)
- **ISSUE:** No explicit privilege separation (actions require appropriate privileges, but no explicit separation)

---

## 6. LOCAL TAMPER & INTEGRITY PROTECTION

### Evidence

**Binary Integrity Checks:**
- ❌ **CRITICAL:** No binary integrity checks found:
  - `agents/linux/agent_main.py` - No binary integrity checks found
  - `agents/windows/agent/agent_main.py` - No binary integrity checks found
  - ❌ **CRITICAL:** No binary integrity checks (agents do not verify binary integrity)

**Self-Tamper Detection:**
- ❌ **CRITICAL:** No self-tamper detection found:
  - `agents/linux/agent_main.py` - No self-tamper detection found
  - `agents/windows/agent/agent_main.py` - No self-tamper detection found
  - ❌ **CRITICAL:** No self-tamper detection (agents do not detect tampering)

**Health Reporting Behavior:**
- ✅ Windows agent reports health: `agents/windows/agent/etw/health_monitor.py` - `HealthMonitor` monitors ETW session health
- ✅ Windows agent reports health: `agents/windows/agent/agent_main.py:110` - `HealthMonitor` initialized with health callback
- ✅ Windows agent reports health: `agents/windows/agent/agent_main.py:229-259` - `_on_health_event()` sends health events
- ⚠️ **ISSUE:** Linux agent does not report health: `agents/linux/agent_main.py` - No health reporting found (Linux agent is execution-only)

**Agent Continues Silently After Tamper:**
- ⚠️ **ISSUE:** No tamper detection (agents cannot detect tampering):
  - `agents/linux/agent_main.py` - No tamper detection found
  - `agents/windows/agent/agent_main.py` - No tamper detection found
  - ⚠️ **ISSUE:** Agents cannot detect tampering (no tamper detection exists)

**Health Telemetry Optional:**
- ⚠️ **ISSUE:** Health telemetry may be optional:
  - `agents/windows/agent/agent_main.py:229-259` - `_on_health_event()` sends health events (but health monitoring may fail)
  - ⚠️ **ISSUE:** Health telemetry may be optional (health monitoring may fail)

**No Integrity Verification:**
- ❌ **CRITICAL:** No integrity verification found:
  - `agents/linux/agent_main.py` - No integrity verification found
  - `agents/windows/agent/agent_main.py` - No integrity verification found
  - ❌ **CRITICAL:** No integrity verification (agents do not verify integrity)

### Verdict: **FAIL**

**Justification:**
- Windows agent reports health (health monitoring exists)
- **CRITICAL:** No binary integrity checks (agents do not verify binary integrity)
- **CRITICAL:** No self-tamper detection (agents do not detect tampering)
- **CRITICAL:** No integrity verification (agents do not verify integrity)
- **ISSUE:** Linux agent does not report health (Linux agent is execution-only)
- **ISSUE:** Health telemetry may be optional (health monitoring may fail)

---

## 7. CREDENTIAL HANDLING (AGENT-SIDE)

### Evidence

**Storage of Any Secrets:**
- ✅ Windows agent stores signing key: `agents/windows/agent/telemetry/signer.py:64-68` - Signing key loaded from file (not stored in code)
- ✅ Linux agent stores TRE public key: `agents/linux/command_gate.py:75` - TRE public key passed as parameter (not stored in code)
- ✅ Windows agent stores signing key: `agents/windows/agent/agent_main.py:98-100` - `TelemetrySigner` initialized with `signing_key_path` (key loaded from file)

**Rotation / Renewal Behavior:**
- ⚠️ **ISSUE:** No explicit rotation/renewal behavior found:
  - `agents/windows/agent/telemetry/signer.py:64-68` - Signing key loaded once at initialization (no rotation)
  - `agents/linux/command_gate.py:75` - TRE public key passed once at initialization (no rotation)
  - ⚠️ **ISSUE:** No explicit rotation/renewal behavior (keys loaded once, no rotation)

**No Hardcoded Credentials:**
- ✅ **VERIFIED:** No hardcoded credentials:
  - `agents/windows/agent/telemetry/signer.py:64-68` - Signing key loaded from file (not hardcoded)
  - `agents/linux/command_gate.py:75` - TRE public key passed as parameter (not hardcoded)
  - ✅ **VERIFIED:** No hardcoded credentials (keys loaded from files/parameters, not hardcoded)

**Embedded Secrets:**
- ✅ **VERIFIED:** No embedded secrets:
  - `agents/windows/agent/telemetry/signer.py:64-68` - Signing key loaded from file (not embedded)
  - `agents/linux/command_gate.py:75` - TRE public key passed as parameter (not embedded)
  - ✅ **VERIFIED:** No embedded secrets (keys loaded from files/parameters, not embedded)

**Long-Lived Static Tokens:**
- ⚠️ **ISSUE:** Keys are long-lived:
  - `agents/windows/agent/telemetry/signer.py:64-68` - Signing key loaded once at initialization (long-lived)
  - `agents/linux/command_gate.py:75` - TRE public key passed once at initialization (long-lived)
  - ⚠️ **ISSUE:** Keys are long-lived (keys loaded once, no rotation)

**Credentials Logged or Exposed:**
- ✅ **VERIFIED:** Credentials are NOT logged:
  - `agents/windows/agent/telemetry/signer.py:64-68` - Signing key loaded from file (not logged)
  - `agents/linux/command_gate.py:75` - TRE public key passed as parameter (not logged)
  - ✅ **VERIFIED:** Credentials are NOT logged (keys loaded, not logged)

### Verdict: **PARTIAL**

**Justification:**
- No hardcoded credentials (keys loaded from files/parameters)
- No embedded secrets (keys loaded from files/parameters)
- Credentials are NOT logged (keys loaded, not logged)
- **ISSUE:** No explicit rotation/renewal behavior (keys loaded once, no rotation)
- **ISSUE:** Keys are long-lived (keys loaded once, no rotation)

---

## 8. NEGATIVE VALIDATION (MANDATORY)

### Evidence

**Agent Executes Unsigned Commands:**
- ✅ **PROVEN IMPOSSIBLE:** Linux agent does NOT execute unsigned commands:
  - `agents/linux/command_gate.py:302-334` - `_verify_signature()` verifies ed25519 signature before execution
  - `agents/linux/command_gate.py:312-313` - If verifier not available, command is rejected
  - `agents/linux/command_gate.py:166` - `_verify_signature(command)` called before execution
  - ✅ **VERIFIED:** Linux agent does NOT execute unsigned commands (signature verification required)
- ⚠️ **ISSUE:** Windows command gate has placeholder: `agents/windows/command_gate.ps1:122-129` - `Test-CommandSignature` has placeholder (not implemented)

**Agent Sends Fake Telemetry:**
- ⚠️ **ISSUE:** Windows agent can send unsigned telemetry:
  - `agents/windows/agent/telemetry/signer.py:108-115` - If signer not available, signature is None
  - `agents/windows/agent/telemetry/signer.py:118-120` - If signature is None, envelope is returned without signature
  - ⚠️ **ISSUE:** Windows agent can send unsigned telemetry (if signer not available)
- ✅ **VERIFIED:** Windows agent signs telemetry: `agents/windows/agent/telemetry/signer.py:85-122` - `sign_envelope()` signs envelope with ed25519 (if signer available)

**Agent Bypasses Secure Bus:**
- ✅ **VERIFIED:** Windows agent does NOT bypass secure bus:
  - `agents/windows/agent/telemetry/sender.py:157-187` - `_send_to_core()` sends events via HTTP POST (not direct DB write)
  - `agents/windows/agent/telemetry/sender.py:37` - `CORE_ENDPOINT` is HTTP endpoint (not direct DB)
  - ✅ **VERIFIED:** Windows agent does NOT bypass secure bus (sends telemetry via HTTP, not direct DB)
- ✅ **VERIFIED:** Linux agent does NOT bypass secure bus: `agents/linux/agent_main.py:70-127` - Linux agent executes commands (no telemetry, no DB writes)

**Agent Mutates System State Without Authorization:**
- ✅ **VERIFIED:** Linux agent does NOT mutate system state without authorization:
  - `agents/linux/command_gate.py:133-193` - `receive_command()` validates command through 8-step pipeline (authorization required)
  - `agents/linux/command_gate.py:166` - `_verify_signature(command)` verifies signature (authorization required)
  - ✅ **VERIFIED:** Linux agent does NOT mutate system state without authorization (signature verification required)
- ⚠️ **ISSUE:** Windows command gate has placeholder: `agents/windows/command_gate.ps1:122-129` - `Test-CommandSignature` has placeholder (not implemented)

### Verdict: **PARTIAL**

**Justification:**
- Linux agent does NOT execute unsigned commands (signature verification required)
- Linux agent does NOT bypass secure bus (no telemetry, no DB writes)
- Linux agent does NOT mutate system state without authorization (signature verification required)
- **ISSUE:** Windows agent can send unsigned telemetry (if signer not available)
- **ISSUE:** Windows command gate has placeholder for signature verification (not implemented)

---

## 9. VERDICT & IMPACT

### Section-by-Section Verdicts

1. **Component Identity & Role:** PASS
   - Agent entry points are clearly identified
   - Supported platforms are Linux and Windows
   - Explicit statements of what agents can do and must never do
   - Agents do NOT make enforcement decisions, escalate incidents, or write to DB

2. **Startup & Fail-Closed Behavior:** PARTIAL
   - Linux agent requires TRE public key (mandatory parameter)
   - **ISSUE:** Windows agent can start without signing key (fail-open behavior)
   - **ISSUE:** Linux agent can start without verifier (if PyNaCl not available)
   - **ISSUE:** Windows agent can emit telemetry without signing key
   - **ISSUE:** Windows agent runs in degraded mode

3. **Telemetry Emission & Authentication:** PARTIAL
   - Windows agent signs telemetry with ed25519 (correctly implemented)
   - Identity binding exists (machine_id, agent_id, hostname, boot_id)
   - Schema enforcement exists (schema mapping enforced before emission)
   - **ISSUE:** Windows agent can emit unsigned telemetry (if signer not available)
   - **ISSUE:** Host identity inferred from config/hostname (not cryptographically bound)

4. **Command Execution Gate:** PARTIAL
   - Linux agent verifies signature before execution (ed25519 signature verification)
   - Command schema validation exists (required fields, UUIDs, enums, timestamps)
   - Explicit allow-list of command types exists
   - **ISSUE:** Windows command gate has placeholder for signature verification (not implemented)
   - **ISSUE:** Linux agent can start without verifier

5. **Privilege & Sandboxing:** PARTIAL
   - Separation of monitoring vs execution exists (components are separate)
   - Abuse resistance exists (explicit commands, not shell, enum values)
   - **ISSUE:** No explicit privilege checks (actions require appropriate privileges, but no explicit validation)
   - **ISSUE:** No explicit privilege separation

6. **Local Tamper & Integrity Protection:** FAIL
   - Windows agent reports health (health monitoring exists)
   - **CRITICAL:** No binary integrity checks (agents do not verify binary integrity)
   - **CRITICAL:** No self-tamper detection (agents do not detect tampering)
   - **CRITICAL:** No integrity verification (agents do not verify integrity)

7. **Credential Handling:** PARTIAL
   - No hardcoded credentials (keys loaded from files/parameters)
   - No embedded secrets (keys loaded from files/parameters)
   - Credentials are NOT logged (keys loaded, not logged)
   - **ISSUE:** No explicit rotation/renewal behavior (keys loaded once, no rotation)

8. **Negative Validation:** PARTIAL
   - Linux agent does NOT execute unsigned commands (signature verification required)
   - Linux agent does NOT bypass secure bus (no telemetry, no DB writes)
   - **ISSUE:** Windows agent can send unsigned telemetry (if signer not available)
   - **ISSUE:** Windows command gate has placeholder for signature verification (not implemented)

### Overall Verdict: **PARTIAL**

**Justification:**
- **CRITICAL:** No binary integrity checks (agents do not verify binary integrity)
- **CRITICAL:** No self-tamper detection (agents do not detect tampering)
- **CRITICAL:** No integrity verification (agents do not verify integrity)
- **ISSUE:** Windows agent can start without signing key (fail-open behavior)
- **ISSUE:** Windows agent can emit unsigned telemetry (if signer not available)
- **ISSUE:** Windows command gate has placeholder for signature verification (not implemented)
- **ISSUE:** Linux agent can start without verifier (if PyNaCl not available)
- **ISSUE:** No explicit privilege checks or separation
- **ISSUE:** No explicit rotation/renewal behavior for keys
- Agent entry points are clearly identified
- Linux agent verifies signature before execution (ed25519 signature verification)
- Command schema validation exists (required fields, UUIDs, enums, timestamps)
- Explicit allow-list of command types exists
- No hardcoded credentials or embedded secrets
- Linux agent does NOT execute unsigned commands or bypass secure bus

**Impact if Agent is Compromised:**
- **CRITICAL:** If agent is compromised, unsigned telemetry can be sent (Windows agent can emit unsigned telemetry)
- **CRITICAL:** If agent is compromised, unsigned commands can be executed (Windows command gate has placeholder for signature verification)
- **CRITICAL:** If agent is compromised, binary integrity cannot be verified (no binary integrity checks)
- **CRITICAL:** If agent is compromised, tampering cannot be detected (no self-tamper detection)
- **HIGH:** If agent is compromised, system state can be mutated without authorization (Windows command gate has placeholder)
- **HIGH:** If agent is compromised, fake telemetry can be sent (Windows agent can emit unsigned telemetry)
- **MEDIUM:** If agent is compromised, keys cannot be rotated (no explicit rotation/renewal behavior)
- **LOW:** If agent is compromised, Linux agent still requires signature verification (Linux agent verifies signature)

**Whether Core Remains Trustworthy:**
- ⚠️ **PARTIAL:** Core remains trustworthy if Linux agent is compromised:
  - `agents/linux/command_gate.py:302-334` - Linux agent verifies signature before execution (signature verification required)
  - ⚠️ **PARTIAL:** Core remains trustworthy if Linux agent is compromised (Linux agent verifies signature, but can start without verifier)
- ❌ **NO:** Core does NOT remain trustworthy if Windows agent is compromised:
  - `agents/windows/agent/telemetry/signer.py:108-115` - Windows agent can emit unsigned telemetry (if signer not available)
  - `agents/windows/command_gate.ps1:122-129` - Windows command gate has placeholder for signature verification (not implemented)
  - ❌ **NO:** Core does NOT remain trustworthy if Windows agent is compromised (Windows agent can emit unsigned telemetry, command gate has placeholder)

**Recommendations:**
1. **CRITICAL:** Implement binary integrity checks (verify binary integrity at startup)
2. **CRITICAL:** Implement self-tamper detection (detect tampering of agent binary)
3. **CRITICAL:** Implement integrity verification (verify integrity of agent components)
4. **CRITICAL:** Implement Windows command gate signature verification (replace placeholder with actual ed25519 verification)
5. **CRITICAL:** Require signing key for Windows agent startup (fail-closed if signing key not available)
6. **CRITICAL:** Require verifier for Linux agent startup (fail-closed if verifier not available)
7. **HIGH:** Implement explicit privilege checks (validate privileges before actions)
8. **HIGH:** Implement explicit privilege separation (separate privileges for monitoring vs execution)
9. **HIGH:** Implement key rotation/renewal (rotate keys periodically)
10. **MEDIUM:** Implement health reporting for Linux agent (report health events)
11. **MEDIUM:** Implement cryptographically bound host identity (bind host identity cryptographically)

---

**Validation Date:** 2025-01-13
**Validator:** Lead Validator & Compliance Auditor
**Next Step:** Validation complete (all 10 steps completed)
