# Validation Step 3 — Secure Telemetry Bus & Inter-Service Trust

**Component Identity:**
- **Name:** Inter-Service Communication Layer (No Explicit Bus)
- **Primary Paths:**
  - `/home/ransomeye/rebuild/services/ingest/app/main.py` - HTTP endpoint for agent events
  - `/home/ransomeye/rebuild/services/correlation-engine/app/main.py` - Database-based event consumption
  - `/home/ransomeye/rebuild/agents/*/telemetry/` - Agent telemetry signing
- **Transport:** HTTP POST (agents → ingest), Direct database access (services → database)
- **Bus Type:** ❌ **NO EXPLICIT BUS** - Uses HTTP + Database instead of message bus

**Spec Reference:**
- Phase 4 — Minimal Data Plane (Ingest Service)
- Event Envelope Contract (`contracts/event-envelope.schema.json`)
- Time Semantics Contract (`contracts/time-semantics.policy.json`)

---

## 1. COMPONENT IDENTITY

### Evidence

**Bus Implementation Name:**
- ❌ **NO EXPLICIT BUS IMPLEMENTATION FOUND**
- ✅ System uses HTTP POST from agents to ingest service
- ✅ System uses direct database access for inter-service communication

**Transport Used:**
- ✅ HTTP POST: `services/ingest/app/main.py:504` - `@app.post("/events")` endpoint
- ✅ Direct Database: `services/correlation-engine/app/db.py:70-121` - `get_unprocessed_events()` reads from `raw_events` table
- ❌ No NATS, RabbitMQ, Kafka, or gRPC found
- ❌ No message bus infrastructure found

**Bus Architecture:**
- ❌ **NOT CENTRALIZED** - No centralized message bus
- ❌ **NOT CLUSTERED** - No clustered message bus
- ❌ **NOT EMBEDDED** - No embedded message bus
- ✅ **HTTP + DATABASE** - Point-to-point HTTP and shared database

**Service Independence:**
- ⚠️ **CRITICAL:** Services can operate without explicit bus trust enforcement:
  - `services/ingest/app/main.py:504-698` - Ingest accepts HTTP POST without signature verification
  - `services/correlation-engine/app/db.py:70-121` - Correlation engine reads from database without authentication
  - No bus-level authentication found

### Verdict: **FAIL**

**Justification:**
- **CRITICAL:** No explicit secure telemetry bus exists
- System uses HTTP POST and direct database access instead of message bus
- Services can publish/consume messages without bus-level authentication
- This violates the requirement for a "Secure Telemetry Bus"

---

## 2. MESSAGE AUTHENTICATION (CRITICAL)

### Evidence

**How Messages are Authenticated:**
- ⚠️ **CRITICAL:** Ingest service does NOT verify cryptographic signatures:
  - `services/ingest/app/main.py:504-698` - `ingest_event()` endpoint does NOT verify signatures
  - `services/ingest/app/main.py:376-384` - `validate_hash_integrity()` only verifies SHA256 hash, NOT cryptographic signature
  - No signature verification code found in ingest service
- ✅ Agents sign events: `agents/windows/agent/telemetry/signer.py:85-122` - `sign_envelope()` signs with ed25519
- ✅ Agents include signatures: `agents/windows/agent/telemetry/signer.py:118-120` - Adds `signature` and `signing_key_id` to envelope
- ❌ **CRITICAL:** Ingest does NOT verify these signatures

**Who Signs:**
- ✅ Agents sign: `agents/windows/agent/telemetry/signer.py:38-122` - `TelemetrySigner` class signs event envelopes
- ✅ Windows Agent: `agents/windows/agent/telemetry/signer.py:85-122` - Signs with ed25519
- ⚠️ Linux Agent: `services/linux-agent/src/main.rs` - Uses HTTP POST but signature verification not found in ingest

**Who Verifies:**
- ❌ **CRITICAL:** Ingest service does NOT verify signatures
- ✅ Agents verify commands: `agents/linux/command_gate.py:302-334` - `_verify_signature()` verifies ed25519 signatures
- ⚠️ Verification exists for commands (agent-side), but NOT for events (ingest-side)

**Algorithm Used:**
- ✅ Agents use ed25519: `agents/windows/agent/telemetry/signer.py:111` - Uses `nacl.signing.SigningKey` (ed25519)
- ✅ Commands use ed25519: `agents/linux/command_gate.py:330` - Uses `nacl.exceptions.BadSignatureError` (ed25519)
- ⚠️ Ingest does NOT use any signature verification algorithm

**Identity Bound to Message:**
- ✅ Event envelopes include identity: `contracts/event-envelope.schema.json:61-85` - `identity` object with `hostname`, `boot_id`, `agent_version`
- ✅ Event envelopes include component: `contracts/event-envelope.schema.json:31-34` - `component` field (enum: linux_agent, windows_agent, dpi, core)
- ✅ Event envelopes include machine_id: `contracts/event-envelope.schema.json:26-29` - `machine_id` field
- ⚠️ **ISSUE:** Identity is NOT cryptographically bound - can be spoofed

**Where Verification Happens:**
- ❌ **CRITICAL:** Verification does NOT happen at publish time (ingest does not verify)
- ❌ **CRITICAL:** Verification does NOT happen at consume time (correlation engine does not verify)
- ✅ Verification happens at agent command acceptance: `agents/linux/command_gate.py:166` - Commands are verified before execution

### Verdict: **FAIL**

**Justification:**
- **CRITICAL FAILURE:** Ingest service accepts unsigned messages (no signature verification)
- **CRITICAL FAILURE:** Ingest service does NOT verify cryptographic signatures from agents
- Agents sign events, but ingest does NOT verify those signatures
- Identity is NOT cryptographically bound to messages (can be spoofed)
- This violates zero-trust authentication requirements

---

## 3. AUTHORIZATION & ACL ENFORCEMENT

### Evidence

**Who Can Publish What:**
- ❌ **CRITICAL:** No authorization checks found in ingest service:
  - `services/ingest/app/main.py:504-698` - `ingest_event()` accepts any HTTP POST request
  - No authentication middleware found
  - No authorization checks found
  - No ACL enforcement found
- ✅ Event envelopes include component identity: `contracts/event-envelope.schema.json:31-34` - `component` field
- ⚠️ **ISSUE:** Component identity is NOT verified (can be spoofed)

**Agents Publishing Commands:**
- ✅ Agents do NOT publish commands - agents receive commands, not publish them
- ✅ Commands are sent TO agents: `agents/linux/command_gate.py:133-193` - `receive_command()` accepts commands
- ✅ Commands are verified: `agents/linux/command_gate.py:166` - Signature verification before acceptance

**Agents Masquerading as Core Services:**
- ⚠️ **CRITICAL:** Agents CAN masquerade as core services:
  - `contracts/event-envelope.schema.json:31-34` - `component` field can be set to "core" by any sender
  - `services/ingest/app/main.py:504-698` - Ingest does NOT verify component identity
  - No cryptographic proof of component identity

**DPI Emitting Enforcement Actions:**
- ✅ DPI is observation-only: `dpi-advanced/README.md:13-22` - "Observation Only, At Scale"
- ✅ DPI does NOT emit enforcement actions per specification
- ⚠️ **ISSUE:** DPI could emit enforcement actions if it wanted (no authorization check prevents it)

**DPI Masquerading as Agents:**
- ⚠️ **CRITICAL:** DPI CAN masquerade as agents:
  - `contracts/event-envelope.schema.json:31-34` - `component` field can be set to "linux_agent" or "windows_agent" by any sender
  - `services/ingest/app/main.py:504-698` - Ingest does NOT verify component identity
  - No cryptographic proof of component identity

**Topic-Only Trust:**
- ❌ **CRITICAL:** No topics found (no message bus)
- ❌ **CRITICAL:** No topic-based authorization found
- ⚠️ HTTP endpoint is public (no authentication required)

**Agent Able to Emit Privileged Messages:**
- ⚠️ **CRITICAL:** Agents CAN emit any message type:
  - `services/ingest/app/main.py:504-698` - Ingest accepts any event envelope
  - No message type restrictions found
  - No privilege checks found

### Verdict: **FAIL**

**Justification:**
- **CRITICAL FAILURE:** No authorization checks in ingest service
- **CRITICAL FAILURE:** Agents can masquerade as core services (component identity not verified)
- **CRITICAL FAILURE:** DPI can masquerade as agents (component identity not verified)
- **CRITICAL FAILURE:** No ACL enforcement found
- This violates zero-trust authorization requirements

---

## 4. REPLAY PROTECTION & TEMPORAL SAFETY

### Evidence

**Presence of Timestamps:**
- ✅ Event envelopes include timestamps: `contracts/event-envelope.schema.json:41-49` - `observed_at` and `ingested_at` fields
- ✅ Timestamps are RFC3339 UTC: `contracts/event-envelope.schema.json:42-48` - Format validation
- ✅ Timestamps are validated: `services/ingest/app/main.py:330-374` - `validate_timestamps()` function

**Presence of Nonces:**
- ❌ **CRITICAL:** No nonces found in event envelopes
- ✅ Commands include nonces: `agents/linux/command_gate.py:272-298` - `_validate_freshness()` checks timestamps and nonces
- ⚠️ Events do NOT include nonces (only commands do)

**Presence of Sequence IDs:**
- ✅ Event envelopes include sequence: `contracts/event-envelope.schema.json:51-55` - `sequence` field (64-bit unsigned integer)
- ✅ Sequence is validated: `services/ingest/app/main.py:426-431` - `verify_sequence_monotonicity()` validates sequence
- ✅ Sequence is per-component-instance: `contracts/event-envelope.schema.json:55` - Sequence is within component instance

**Where Replay Checks Occur:**
- ✅ Duplicate detection: `services/ingest/app/main.py:386-390` - `check_duplicate()` checks `event_id`
- ✅ Sequence monotonicity: `services/ingest/app/main.py:426-431` - `verify_sequence_monotonicity()` validates sequence
- ✅ Hash chain continuity: `services/ingest/app/main.py:419-423` - `verify_hash_chain_continuity()` validates hash chain
- ⚠️ **ISSUE:** Replay checks are based on `event_id` and sequence, but no cryptographic nonce prevents replay of valid events

**What Happens on Replay Detection:**
- ✅ Duplicate events rejected: `services/ingest/app/main.py:632-647` - Returns HTTP 409 CONFLICT
- ✅ Sequence violations rejected: `services/ingest/app/main.py:428-431` - Raises `ValueError`
- ✅ Hash chain violations rejected: `services/ingest/app/main.py:422-423` - Raises `ValueError`

**Clock Skew Handling:**
- ✅ Timestamp validation includes clock skew tolerance: `services/ingest/app/main.py:350-356` - Allows 5 seconds future tolerance
- ✅ Timestamp validation includes age limit: `services/ingest/app/main.py:358-364` - Rejects events older than 30 days
- ✅ Late arrival detection: `services/ingest/app/main.py:366-367` - Detects late arrival (>1 hour)

**Infinite Validity Windows:**
- ✅ Validity window is limited: `services/ingest/app/main.py:358-364` - 30-day maximum age
- ✅ Future timestamps rejected: `services/ingest/app/main.py:350-356` - 5-second future tolerance
- ✅ No infinite validity windows found

**Replays Accepted:**
- ⚠️ **PARTIAL:** Replays are detected via `event_id` and sequence, but:
  - If an attacker can generate valid `event_id` and sequence, replay is possible
  - No cryptographic nonce prevents replay of valid event structures
  - Hash chain prevents out-of-order events, but not exact replays

### Verdict: **PARTIAL**

**Justification:**
- Timestamps, sequences, and duplicate detection exist
- **CRITICAL ISSUE:** No cryptographic nonces in events (only in commands)
- Replay protection relies on `event_id` uniqueness and sequence monotonicity, but not cryptographic nonces
- Clock skew is handled, but replay protection is incomplete without nonces

---

## 5. FAIL-CLOSED BEHAVIOR (BUS LEVEL)

### Evidence

**Signature Verification Failure:**
- ❌ **CRITICAL:** Signature verification does NOT exist in ingest service
- ✅ Command signature verification fails-closed: `agents/linux/command_gate.py:332` - Raises `CommandRejectionError` on signature failure
- ⚠️ Event signature verification does NOT exist (cannot fail-closed if it doesn't exist)

**Message Schema Invalid:**
- ✅ Schema validation fails-closed: `services/ingest/app/main.py:526-557` - Returns HTTP 400 BAD REQUEST
- ✅ Invalid schema rejected: `services/ingest/app/main.py:554-557` - Raises `HTTPException`
- ✅ Schema validation logs failure: `services/ingest/app/main.py:532-543` - Logs to `event_validation_log`

**Identity Missing:**
- ⚠️ **PARTIAL:** Identity fields are required by schema, but identity is NOT cryptographically verified:
  - `contracts/event-envelope.schema.json:61-85` - `identity` object is required
  - `services/ingest/app/main.py:316-328` - Schema validation checks for presence
  - ⚠️ **ISSUE:** Identity presence is checked, but identity authenticity is NOT verified

**Bus Crypto Unavailable:**
- ❌ **CRITICAL:** No bus-level crypto exists (no message bus)
- ⚠️ Agent signing can be unavailable: `agents/windows/agent/telemetry/signer.py:60-63` - Signing disabled if PyNaCl unavailable
  - `agents/windows/agent/telemetry/signer.py:83` - Logs warning but does NOT prevent transmission
  - ⚠️ **ISSUE:** Events can be sent unsigned if crypto unavailable

**Termination vs Drop vs Quarantine:**
- ✅ Invalid messages are rejected: `services/ingest/app/main.py:554-557` - Returns HTTP 400/409
- ✅ Invalid messages are logged: `services/ingest/app/main.py:532-543` - Logs to `event_validation_log`
- ✅ Messages are dropped (not quarantined): Invalid messages are rejected, not stored
- ⚠️ **ISSUE:** No quarantine mechanism for suspicious but valid-looking messages

**Warnings Only:**
- ✅ Failures cause rejection: `services/ingest/app/main.py:554-557` - Returns HTTP error codes
- ✅ Failures are logged: `services/ingest/app/main.py:532-543` - Logs validation failures
- ⚠️ **ISSUE:** Unsigned events are accepted (no signature verification = no failure)

**Silent Drops Without Audit:**
- ✅ Drops are audited: `services/ingest/app/main.py:532-543` - Logs to `event_validation_log`
- ✅ All validation failures are logged: `services/ingest/app/main.py:526-622` - Multiple validation checks log failures

**Auto-Trust Fallback:**
- ⚠️ **CRITICAL:** Unsigned events are accepted (no signature verification = auto-trust):
  - `services/ingest/app/main.py:504-698` - Ingest does NOT verify signatures
  - `agents/windows/agent/telemetry/signer.py:60-63` - Signing can be disabled
  - ⚠️ **ISSUE:** System falls back to accepting unsigned events

### Verdict: **FAIL**

**Justification:**
- Schema validation fails-closed, but signature verification does NOT exist
- **CRITICAL FAILURE:** Unsigned events are accepted (no signature verification)
- **CRITICAL FAILURE:** System falls back to accepting unsigned events if crypto unavailable
- Identity authenticity is NOT verified
- This violates fail-closed requirements for bus-level security

---

## 6. SCHEMA & CONTRACT ENFORCEMENT

### Evidence

**Presence of Schema Validation:**
- ✅ Schema validation exists: `services/ingest/app/main.py:316-328` - `validate_schema()` function
- ✅ Schema is loaded: `services/ingest/app/main.py:226-237` - Loads `event-envelope.schema.json`
- ✅ Schema validation uses jsonschema: `services/ingest/app/main.py:319` - Uses `jsonschema.validate()`

**Location of Schemas:**
- ✅ Schemas in contracts/: `contracts/event-envelope.schema.json` - Event envelope schema
- ✅ Schemas in contracts/: `contracts/time-semantics.policy.json` - Time semantics policy
- ✅ Schemas in contracts/: `contracts/failure-semantics.policy.json` - Failure semantics policy

**Producer and Consumer Validate Against Same Schema:**
- ✅ Producers validate: `agents/windows/agent/telemetry/event_envelope.py:29-139` - `EventEnvelopeBuilder` builds envelopes per schema
- ✅ Consumers validate: `services/ingest/app/main.py:316-328` - `validate_schema()` validates against schema
- ✅ Same schema used: Both reference `contracts/event-envelope.schema.json`

**Malformed Messages Rejected:**
- ✅ Malformed messages rejected: `services/ingest/app/main.py:526-557` - Returns HTTP 400 BAD REQUEST
- ✅ Schema violations logged: `services/ingest/app/main.py:532-543` - Logs to `event_validation_log`
- ✅ Schema violations cause rejection: `services/ingest/app/main.py:554-557` - Raises `HTTPException`

**Ad-Hoc JSON Without Schema:**
- ✅ All messages must conform to schema: `contracts/event-envelope.schema.json:19` - `additionalProperties: false`
- ✅ Schema validation enforces structure: `services/ingest/app/main.py:316-328` - Validates against schema
- ✅ No ad-hoc JSON accepted: Schema validation rejects non-conforming messages

**Consumer-Side "Best Effort" Parsing:**
- ✅ Schema validation is strict: `services/ingest/app/main.py:316-328` - Raises `ValidationError` on failure
- ✅ No best-effort parsing: `services/ingest/app/main.py:554-557` - Rejects invalid messages
- ✅ Correlation engine reads from database: `services/correlation-engine/app/db.py:70-121` - Reads validated events only

### Verdict: **PASS**

**Justification:**
- Schema validation is present and enforced
- Producers and consumers use the same schema
- Malformed messages are rejected
- No ad-hoc JSON or best-effort parsing found

---

## 7. NEGATIVE VALIDATION (MANDATORY)

### Evidence

**Agent Sends a Command:**
- ✅ **PROVEN IMPOSSIBLE:** Agents do NOT send commands - agents receive commands:
  - `agents/linux/command_gate.py:133-193` - `receive_command()` accepts commands (does not send)
  - `threat-response-engine/` - TRE sends commands to agents
  - ✅ **VERIFIED:** Agents cannot send commands (architecture prevents it)

**Agent Impersonates Core:**
- ❌ **PROVEN POSSIBLE:** Agents CAN impersonate core:
  - `contracts/event-envelope.schema.json:31-34` - `component` field can be set to "core" by any sender
  - `services/ingest/app/main.py:504-698` - Ingest does NOT verify component identity
  - No cryptographic proof of component identity
  - ✅ **VERIFIED:** Agents CAN impersonate core (no verification prevents it)

**DPI Injects Policy Actions:**
- ⚠️ **PARTIAL:** DPI specification says observation-only, but:
  - `contracts/event-envelope.schema.json:31-34` - DPI can set `component` to any value
  - `services/ingest/app/main.py:504-698` - Ingest does NOT verify component identity
  - ⚠️ **VERIFIED:** DPI CAN inject policy actions (no authorization prevents it, but specification says it shouldn't)

**Unsigned Message Reaches Correlation Engine:**
- ❌ **PROVEN POSSIBLE:** Unsigned messages CAN reach correlation engine:
  - `services/ingest/app/main.py:504-698` - Ingest does NOT verify signatures
  - `services/correlation-engine/app/db.py:70-121` - Correlation engine reads from database
  - Unsigned events are stored in database and read by correlation engine
  - ✅ **VERIFIED:** Unsigned messages CAN reach correlation engine (no signature verification prevents it)

**Replay of Kill/Isolate Command Succeeds:**
- ✅ **PROVEN IMPOSSIBLE:** Command replays are prevented:
  - `agents/linux/command_gate.py:272-298` - `_validate_freshness()` checks timestamps and nonces
  - `agents/linux/command_gate.py:177-178` - `_check_idempotency()` checks `command_id`
  - ✅ **VERIFIED:** Command replays are prevented (freshness and idempotency checks)

### Verdict: **PARTIAL**

**Justification:**
- Agents cannot send commands (architecture prevents it)
- Command replays are prevented (freshness and idempotency checks)
- **CRITICAL:** Agents CAN impersonate core (no verification)
- **CRITICAL:** Unsigned messages CAN reach correlation engine (no signature verification)
- **CRITICAL:** DPI CAN inject policy actions (no authorization)

---

## 8. VERDICT & IMPACT

### Section-by-Section Verdicts

1. **Component Identity:** FAIL
   - No explicit secure telemetry bus exists
   - System uses HTTP + Database instead of message bus

2. **Message Authentication:** FAIL
   - Ingest does NOT verify cryptographic signatures
   - Identity is NOT cryptographically bound

3. **Authorization & ACL Enforcement:** FAIL
   - No authorization checks in ingest service
   - Agents can masquerade as core services

4. **Replay Protection & Temporal Safety:** PARTIAL
   - Timestamps and sequences exist, but no cryptographic nonces in events

5. **Fail-Closed Behavior:** FAIL
   - Unsigned events are accepted
   - System falls back to accepting unsigned events

6. **Schema & Contract Enforcement:** PASS
   - Schema validation is present and enforced

7. **Negative Validation:** PARTIAL
   - Agents can impersonate core
   - Unsigned messages can reach correlation engine

### Overall Verdict: **FAIL**

**Justification:**
- **CRITICAL FAILURE:** No explicit secure telemetry bus exists
- **CRITICAL FAILURE:** Ingest service does NOT verify cryptographic signatures from agents
- **CRITICAL FAILURE:** No authorization checks in ingest service
- **CRITICAL FAILURE:** Agents can masquerade as core services (component identity not verified)
- **CRITICAL FAILURE:** Unsigned messages are accepted and can reach correlation engine
- This violates zero-trust, authenticated, non-spoofable communication requirements

**Blast Radius if Bus Trust is Broken:**
- **CRITICAL:** If ingest is compromised, all events can be injected (no signature verification)
- **CRITICAL:** If an agent is compromised, it can impersonate core services (no identity verification)
- **CRITICAL:** If network is compromised, unsigned events can be injected (no signature verification)
- **CRITICAL:** If database is compromised, all inter-service communication is compromised (database is the "bus")
- **HIGH:** If correlation engine is compromised, it can read all events (no access control)

**Whether Downstream Validations Remain Trustworthy:**
- ❌ **NO** - Downstream validations cannot be trusted if bus trust is broken
- ❌ If unsigned events can reach correlation engine, then correlation results are untrustworthy
- ❌ If agents can impersonate core, then all event attribution is untrustworthy
- ❌ If DPI can inject policy actions, then all policy decisions are untrustworthy
- ⚠️ Schema validation is trustworthy, but authentication/authorization are not

**Recommendations:**
1. **CRITICAL:** Implement cryptographic signature verification in ingest service
2. **CRITICAL:** Implement component identity verification (cryptographic proof of component identity)
3. **CRITICAL:** Implement authorization checks in ingest service (who can publish what)
4. **CRITICAL:** Add cryptographic nonces to event envelopes for replay protection
5. **HIGH:** Consider implementing explicit message bus (NATS, RabbitMQ, etc.) with built-in authentication
6. **MEDIUM:** Implement quarantine mechanism for suspicious but valid-looking messages

---

**Validation Date:** 2025-01-13
**Validator:** Lead Validator & Compliance Auditor
**Next Step:** Validation Step 4 — Ingest
