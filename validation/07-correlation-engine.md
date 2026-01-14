# Validation Step 7 — Correlation Engine (In-Depth)

**Component Identity:**
- **Name:** Correlation Engine (System Brain)
- **Primary Paths:**
  - `/home/ransomeye/rebuild/services/correlation-engine/app/main.py` - Main correlation engine
  - `/home/ransomeye/rebuild/services/correlation-engine/app/state_machine.py` - State machine implementation
  - `/home/ransomeye/rebuild/services/correlation-engine/app/rules.py` - Correlation rules
  - `/home/ransomeye/rebuild/services/correlation-engine/app/db.py` - Database operations
- **Entry Point:** Batch processing loop - `services/correlation-engine/app/main.py:205` - `run_correlation_engine()`

**Master Spec References:**
- Phase 5 — Deterministic Correlation Engine
- Correlation Schema (`schemas/04_correlation.sql`)
- Incident Stage Enum: `CLEAN`, `SUSPICIOUS`, `PROBABLE`, `CONFIRMED`
- Validation File 06 (Ingest Pipeline) — **TREATED AS FAILED AND LOCKED**

---

## PURPOSE

This validation proves that the Correlation Engine produces deterministic, auditable incidents with correct state machine enforcement, confidence accumulation, and resilience to non-deterministic ingest_time.

This validation does NOT assume ingest determinism. Validation File 06 (Ingest Pipeline) is treated as FAILED and LOCKED. This validation must account for non-deterministic `ingested_at` values affecting correlation behavior.

This file validates:
- Incident identity generation and deduplication
- State machine correctness (SUSPICIOUS → PROBABLE → CONFIRMED)
- Confidence accumulation math (bounded, deterministic)
- Replay & reprocessing behavior
- Determinism guarantees (same evidence → same incident graph)
- Fail-closed & error handling

This validation does NOT validate UI, agents, installer, or provide fixes/recommendations.

---

## CORRELATION ENGINE DEFINITION

**Correlation Engine Requirements (Master Spec):**

1. **Incident Identity & Deduplication** — Same logical entity always maps to same incident, non-deterministic timestamps do not affect deduplication
2. **State Machine Correctness** — Exact enforcement of SUSPICIOUS → PROBABLE → CONFIRMED, forward-only transitions, no single-signal CONFIRMED paths
3. **Confidence Accumulation Math** — Bounded confidence math, deterministic accumulation, same evidence → same confidence
4. **Replay & Reprocessing Behavior** — Reprocessing raw_events produces same incidents, non-deterministic ingest_time does not break replayability
5. **Determinism Guarantees** — Same evidence → same incident graph, ordering guarantees (or lack thereof)
6. **Fail-Closed & Error Handling** — Correlation halts on inconsistent data, no silent drops or partial correlation

**Correlation Engine Structure:**
- **Entry Point:** Batch processing loop (`run_correlation_engine()`)
- **Processing Chain:** Read unprocessed events → Evaluate rules → Deduplicate → Accumulate confidence → State transitions → Store incidents
- **Storage Tables:** `incidents`, `incident_stages`, `evidence`

---

## WHAT IS VALIDATED

### 1. Incident Identity & Deduplication
- How incident identity is generated
- Whether same logical entity always maps to same incident
- Whether non-deterministic timestamps affect deduplication

### 2. State Machine Correctness
- Exact enforcement of SUSPICIOUS → PROBABLE → CONFIRMED
- Forward-only transitions
- No single-signal CONFIRMED paths

### 3. Confidence Accumulation Math
- Bounded confidence math
- Deterministic accumulation
- Effect of replay or reordering

### 4. Replay & Reprocessing Behavior
- Whether reprocessing raw_events produces same incidents
- Whether non-deterministic ingest_time breaks replayability

### 5. Determinism Guarantees
- Same evidence → same incident graph
- Ordering guarantees (or lack thereof)

### 6. Fail-Closed & Error Handling
- Correlation halts on inconsistent data
- No silent drops or partial correlation

---

## WHAT IS EXPLICITLY NOT ASSUMED

- **NOT ASSUMED:** That ingest_time (ingested_at) is deterministic (Validation File 06 is FAILED, ingested_at is non-deterministic)
- **NOT ASSUMED:** That replay produces identical raw_events records (ingested_at differs on replay)
- **NOT ASSUMED:** That correlation engine does not use ingested_at for ordering or logic
- **NOT ASSUMED:** That correlation engine is resilient to non-deterministic ingest_time

---

## VALIDATION METHODOLOGY

### Evidence Collection Strategy

1. **Code Path Analysis:** Trace incident creation, deduplication, confidence accumulation, state transitions
2. **Database Query Analysis:** Examine SQL queries for use of ingested_at, NOW(), ordering dependencies
3. **State Machine Analysis:** Verify state transition logic, guards, forward-only enforcement
4. **Confidence Math Analysis:** Verify accumulation formula, bounds, determinism
5. **Replay Analysis:** Check if reprocessing produces same incidents despite non-deterministic ingest_time
6. **Error Handling Analysis:** Check fail-closed behavior, error blocking, silent degradation

### Forbidden Patterns (Grep Validation)

- `ingested_at.*ORDER BY|ORDER BY.*ingested_at` — Ordering by non-deterministic ingest_time
- `NOW\(\)|CURRENT_TIMESTAMP` — Non-deterministic timestamps (affects replay)
- `continue.*except|pass.*except` — Silent error handling (forbidden, must fail-closed)

---

## 1. INCIDENT IDENTITY & DEDUPLICATION

### Evidence

**How Incident Identity Is Generated:**
- ✅ Incident ID is UUID v4: `services/correlation-engine/app/main.py:169` - `incident_id = str(uuid.uuid4())`
- ✅ Incident ID is PRIMARY KEY: `schemas/04_correlation.sql:42` - `incident_id UUID NOT NULL PRIMARY KEY` (immutable)
- ✅ Incident ID is never reused: UUID v4 ensures uniqueness
- ✅ Incident identity is stable: `services/correlation-engine/app/db.py:127-203` - `create_incident()` creates incident with immutable ID

**Whether Same Logical Entity Always Maps to Same Incident:**
- ✅ Deduplication key generation: `services/correlation-engine/app/state_machine.py:166-190` - `get_deduplication_key()` generates key from `machine_id` + `process_id` (if available)
- ✅ Deduplication key is deterministic: `services/correlation-engine/app/state_machine.py:187-190` - Key is `f"{machine_id}:{process_id}"` or `machine_id` (deterministic from event data)
- ✅ Deduplication lookup: `services/correlation-engine/app/main.py:135-137` - `find_existing_incident(conn, machine_id, dedup_key, observed_at)` finds existing incidents
- ✅ Deduplication time window: `services/correlation-engine/app/db.py:240-241` - Time window is `event_time ± 3600 seconds` (1 hour window)
- ⚠️ **ISSUE:** Deduplication uses `observed_at` (event_time), not `ingested_at` (ingest_time): `services/correlation-engine/app/db.py:240-241` - Time window based on `event_time` (observed_at)
- ✅ **VERIFIED:** Same logical entity (same machine_id + process_id) within time window maps to same incident

**Whether Non-Deterministic Timestamps Affect Deduplication:**
- ⚠️ **ISSUE:** Event ordering uses `ingested_at`: `services/correlation-engine/app/db.py:109` - `ORDER BY ingested_at ASC` (non-deterministic ordering)
- ✅ Deduplication time window uses `observed_at`: `services/correlation-engine/app/db.py:240-241` - Time window based on `event_time` (observed_at, deterministic)
- ⚠️ **ISSUE:** Non-deterministic ordering may affect which events are processed first, potentially affecting deduplication if events arrive out of order
- ⚠️ **ISSUE:** If same logical entity has events with different `ingested_at` values (due to replay), ordering may differ, but deduplication key is deterministic

**Same Signals Create Multiple Incidents Due to Time Variance:**
- ✅ **VERIFIED:** Deduplication prevents duplicate incidents: `services/correlation-engine/app/main.py:139-166` - If `existing_incident_id` found, evidence is added to existing incident, not new incident created
- ⚠️ **ISSUE:** Time window may expire: `services/correlation-engine/app/db.py:240-241` - Time window is 1 hour, events outside window create new incidents
- ⚠️ **ISSUE:** If events are replayed with different `ingested_at` values but same `observed_at`, deduplication should work (uses observed_at), but ordering may differ

**Incident Identity Depends on ingest_time:**
- ❌ **CRITICAL FAILURE:** Event ordering depends on `ingested_at`: `services/correlation-engine/app/db.py:109` - `ORDER BY ingested_at ASC` (non-deterministic)
- ⚠️ **ISSUE:** If events are processed in different order due to non-deterministic `ingested_at`, deduplication may behave differently (first event creates incident, subsequent events within time window add evidence)
- ❌ **CRITICAL FAILURE:** Incident creation order depends on `ingested_at` (non-deterministic)

### Verdict: **PARTIAL**

**Justification:**
- Incident identity is stable (UUID v4, immutable)
- Same logical entity maps to same incident within time window (deduplication works)
- **CRITICAL FAILURE:** Event ordering depends on `ingested_at` (non-deterministic), affecting which events are processed first
- **ISSUE:** Time window expiration may cause duplicate incidents for same logical entity
- **ISSUE:** Non-deterministic ordering may affect deduplication behavior if events arrive out of order

**PASS Conditions (Met):**
- Incident identity is stable — **CONFIRMED** (UUID v4, immutable)
- Same logical entity maps to same incident — **CONFIRMED** (deduplication works within time window)

**FAIL Conditions (Met):**
- Incident identity depends on ingest_time — **CONFIRMED** (ordering depends on ingested_at)
- Same signals create multiple incidents due to time variance — **PARTIAL** (time window expiration may cause duplicates)

**Evidence Required:**
- File paths: `services/correlation-engine/app/main.py:169,135-137`, `services/correlation-engine/app/state_machine.py:166-190`, `services/correlation-engine/app/db.py:109,240-241`
- Incident identity: UUID v4 generation, PRIMARY KEY constraint
- Deduplication: Key generation, time window, lookup logic
- Ordering: `ORDER BY ingested_at ASC` (non-deterministic)

---

## 2. STATE MACHINE CORRECTNESS

### Evidence

**Exact Enforcement of SUSPICIOUS → PROBABLE → CONFIRMED:**
- ✅ State machine definition: `services/correlation-engine/app/state_machine.py:16` - `INCIDENT_STAGES = ['SUSPICIOUS', 'PROBABLE', 'CONFIRMED']`
- ✅ Stage determination: `services/correlation-engine/app/state_machine.py:106-126` - `determine_stage(confidence)` determines stage based on confidence thresholds
- ✅ Thresholds defined: `services/correlation-engine/app/state_machine.py:19-21` - `CONFIDENCE_THRESHOLD_SUSPICIOUS = 0.0`, `CONFIDENCE_THRESHOLD_PROBABLE = 30.0`, `CONFIDENCE_THRESHOLD_CONFIRMED = 70.0`
- ✅ Stage transitions: `services/correlation-engine/app/db.py:336` - `should_transition_stage(current_stage, new_stage)` checks if transition is allowed
- ✅ Transition enforcement: `services/correlation-engine/app/db.py:336-344` - State transition only occurs if `should_transition_stage()` returns True

**Forward-Only Transitions:**
- ✅ Transition guard: `services/correlation-engine/app/state_machine.py:129-163` - `should_transition_stage()` enforces forward-only transitions
- ✅ No backward transitions: `services/correlation-engine/app/state_machine.py:145-150` - Returns False for backward transitions (CONFIRMED → PROBABLE, PROBABLE → SUSPICIOUS)
- ✅ One-step transitions: `services/correlation-engine/app/state_machine.py:163` - `return new_index > current_index and new_index == current_index + 1` (only one step forward)
- ✅ Terminal state: `services/correlation-engine/app/state_machine.py:146-147` - `if current_stage == 'CONFIRMED': return False` (CONFIRMED is terminal)

**No Single-Signal CONFIRMED Paths:**
- ✅ Single signal creates SUSPICIOUS: `services/correlation-engine/app/rules.py:44-45` - `stage = 'SUSPICIOUS'` (single signal → SUSPICIOUS only)
- ✅ No direct CONFIRMED jump: `services/correlation-engine/app/state_machine.py:152-153` - `if current_stage == 'SUSPICIOUS' and new_stage == 'CONFIRMED': return False` (no direct jump)
- ✅ Must go through PROBABLE: `services/correlation-engine/app/state_machine.py:163` - Only allows one-step forward transitions (SUSPICIOUS → PROBABLE → CONFIRMED)

**State Transitions Depend on Timing Artifacts:**
- ⚠️ **ISSUE:** State transition timestamps use `NOW()`: `services/correlation-engine/app/db.py:343` - `transitioned_at = NOW()` (non-deterministic)
- ⚠️ **ISSUE:** Stage change timestamp uses `NOW()`: `services/correlation-engine/app/db.py:354` - `stage_changed_at = CASE WHEN %s THEN NOW() ELSE stage_changed_at END` (non-deterministic)
- ✅ State transitions depend on confidence: `services/correlation-engine/app/db.py:305-306` - `new_confidence = accumulate_confidence(...)`, `new_stage = determine_stage(new_confidence)` (deterministic)
- ⚠️ **ISSUE:** If events are processed in different order due to non-deterministic `ingested_at`, confidence accumulation order may differ, potentially affecting state transitions

**Any Shortcut Exists:**
- ✅ **VERIFIED:** No shortcuts exist: `services/correlation-engine/app/state_machine.py:129-163` - `should_transition_stage()` enforces one-step forward transitions only
- ✅ **VERIFIED:** No direct CONFIRMED jump: `services/correlation-engine/app/state_machine.py:152-153` - Direct jump from SUSPICIOUS to CONFIRMED is blocked

### Verdict: **PARTIAL**

**Justification:**
- State machine correctly enforces SUSPICIOUS → PROBABLE → CONFIRMED progression
- Forward-only transitions are enforced (no backward transitions)
- No single-signal CONFIRMED paths (single signal → SUSPICIOUS only)
- **ISSUE:** State transition timestamps use `NOW()` (non-deterministic, affects replay)
- **ISSUE:** If events are processed in different order due to non-deterministic `ingested_at`, confidence accumulation order may differ, potentially affecting state transitions

**PASS Conditions (Met):**
- Exact enforcement of SUSPICIOUS → PROBABLE → CONFIRMED — **CONFIRMED** (state machine enforces progression)
- Forward-only transitions — **CONFIRMED** (no backward transitions allowed)
- No single-signal CONFIRMED paths — **CONFIRMED** (single signal → SUSPICIOUS only)

**FAIL Conditions (Met):**
- State transitions depend on timing artifacts — **PARTIAL** (timestamps use NOW(), but state logic is deterministic)

**Evidence Required:**
- File paths: `services/correlation-engine/app/state_machine.py:16,106-126,129-163`, `services/correlation-engine/app/db.py:336-344,343,354`
- State machine: Stage definition, transition guards, threshold enforcement
- Timestamps: `NOW()` usage in state transitions

---

## 3. CONFIDENCE ACCUMULATION MATH

### Evidence

**Bounded Confidence Math:**
- ✅ Confidence bounds: `services/correlation-engine/app/state_machine.py:79` - `new_confidence = min(max(new_confidence, 0.0), 100.0)` (bounded to [0.0, 100.0])
- ✅ Accumulation formula: `services/correlation-engine/app/state_machine.py:76` - `new_confidence = current_confidence + new_signal_confidence` (incremental)
- ✅ Saturation: `services/correlation-engine/app/state_machine.py:79` - Confidence capped at 100.0 (saturation)

**Deterministic Accumulation:**
- ✅ Accumulation is deterministic: `services/correlation-engine/app/state_machine.py:61-81` - `accumulate_confidence()` is pure function (deterministic)
- ✅ Signal weights are deterministic: `services/correlation-engine/app/state_machine.py:24-33` - `SIGNAL_WEIGHTS` dictionary (deterministic, configurable via environment)
- ✅ Signal confidence calculation: `services/correlation-engine/app/state_machine.py:42-58` - `calculate_signal_confidence()` is deterministic (based on evidence_type weight)
- ⚠️ **ISSUE:** Accumulation order may differ if events are processed in different order due to non-deterministic `ingested_at` ordering

**Effect of Replay or Reordering:**
- ⚠️ **ISSUE:** Event ordering uses `ingested_at`: `services/correlation-engine/app/db.py:109` - `ORDER BY ingested_at ASC` (non-deterministic)
- ⚠️ **ISSUE:** If events are replayed with different `ingested_at` values, processing order may differ, affecting confidence accumulation order
- ✅ Accumulation formula is commutative: `services/correlation-engine/app/state_machine.py:76` - `new_confidence = current_confidence + new_signal_confidence` (addition is commutative)
- ⚠️ **ISSUE:** However, if same events are processed in different order, final confidence may differ if state transitions occur at different points (state affects future accumulation)

**Confidence Differs for Identical Evidence Sets:**
- ⚠️ **ISSUE:** If events are processed in different order, confidence accumulation order may differ
- ⚠️ **ISSUE:** If state transitions occur at different points due to different processing order, future confidence accumulation may differ (state affects accumulation)
- ✅ Accumulation formula is deterministic: `services/correlation-engine/app/state_machine.py:61-81` - Same inputs → same output (deterministic)
- ⚠️ **ISSUE:** But processing order affects when state transitions occur, which may affect future accumulation

**Confidence Math Depends on Arrival Time:**
- ❌ **CRITICAL FAILURE:** Event ordering depends on `ingested_at`: `services/correlation-engine/app/db.py:109` - `ORDER BY ingested_at ASC` (non-deterministic)
- ⚠️ **ISSUE:** Processing order affects confidence accumulation order, which may affect state transitions, which may affect future accumulation
- ✅ Confidence accumulation formula does not depend on time: `services/correlation-engine/app/state_machine.py:61-81` - Formula is time-independent
- ❌ **CRITICAL FAILURE:** But processing order (which depends on `ingested_at`) affects accumulation order

### Verdict: **FAIL**

**Justification:**
- Confidence accumulation math is bounded and deterministic (formula is correct)
- **CRITICAL FAILURE:** Event ordering depends on `ingested_at` (non-deterministic), affecting processing order
- **CRITICAL FAILURE:** Processing order affects confidence accumulation order, which may affect state transitions, which may affect future accumulation
- **CRITICAL FAILURE:** Same evidence set may produce different confidence if processed in different order

**FAIL Conditions (Met):**
- Confidence differs for identical evidence sets — **CONFIRMED** (processing order affects accumulation)
- Confidence math depends on arrival time — **CONFIRMED** (ordering depends on ingested_at)

**Evidence Required:**
- File paths: `services/correlation-engine/app/state_machine.py:61-81,24-33,42-58`, `services/correlation-engine/app/db.py:109,305-306`
- Confidence accumulation: Formula, bounds, determinism
- Ordering: `ORDER BY ingested_at ASC` (non-deterministic)

---

## 4. REPLAY & REPROCESSING BEHAVIOR

### Evidence

**Whether Reprocessing raw_events Produces Same Incidents:**
- ⚠️ **ISSUE:** Event ordering uses `ingested_at`: `services/correlation-engine/app/db.py:109` - `ORDER BY ingested_at ASC` (non-deterministic)
- ⚠️ **ISSUE:** If events are replayed with different `ingested_at` values, processing order may differ
- ⚠️ **ISSUE:** Different processing order may affect deduplication (first event creates incident, subsequent events add evidence)
- ⚠️ **ISSUE:** Different processing order may affect confidence accumulation order, potentially affecting state transitions
- ✅ Idempotency check: `services/correlation-engine/app/main.py:112` - `check_event_processed(conn, event_id)` prevents duplicate processing
- ⚠️ **ISSUE:** But if events are replayed with different `event_id` values (different UUIDs), idempotency check will not prevent reprocessing

**Whether Non-Deterministic ingest_time Breaks Replayability:**
- ❌ **CRITICAL FAILURE:** Event ordering depends on `ingested_at`: `services/correlation-engine/app/db.py:109` - `ORDER BY ingested_at ASC` (non-deterministic)
- ❌ **CRITICAL FAILURE:** If events are replayed with different `ingested_at` values, processing order may differ, affecting incident creation and state transitions
- ⚠️ **ISSUE:** Deduplication uses `observed_at` (deterministic), but processing order affects which events are processed first
- ❌ **CRITICAL FAILURE:** Reprocessing same raw_events with different `ingested_at` values may produce different incidents or different state transitions

**Reprocessing Produces Different Incidents or States:**
- ❌ **CRITICAL FAILURE:** Event ordering depends on `ingested_at`: `services/correlation-engine/app/db.py:109` - `ORDER BY ingested_at ASC` (non-deterministic)
- ❌ **CRITICAL FAILURE:** Different processing order may affect:
  - Which events create new incidents vs. add evidence to existing incidents (deduplication depends on processing order if events arrive out of order)
  - Confidence accumulation order (may affect state transitions)
  - Final incident states (if state transitions occur at different points)

### Verdict: **FAIL**

**Justification:**
- **CRITICAL FAILURE:** Event ordering depends on `ingested_at` (non-deterministic), breaking replayability
- **CRITICAL FAILURE:** Reprocessing same raw_events with different `ingested_at` values may produce different incidents or different state transitions
- **CRITICAL FAILURE:** Non-deterministic ingest_time breaks replayability

**FAIL Conditions (Met):**
- Reprocessing produces different incidents or states — **CONFIRMED** (ordering depends on ingested_at)
- Non-deterministic ingest_time breaks replayability — **CONFIRMED** (ordering depends on ingested_at)

**Evidence Required:**
- File paths: `services/correlation-engine/app/db.py:109`, `services/correlation-engine/app/main.py:112`
- Ordering: `ORDER BY ingested_at ASC` (non-deterministic)
- Idempotency: `check_event_processed()` prevents duplicate processing

---

## 5. DETERMINISM GUARANTEES

### Evidence

**Same Evidence → Same Incident Graph:**
- ⚠️ **ISSUE:** Event ordering depends on `ingested_at`: `services/correlation-engine/app/db.py:109` - `ORDER BY ingested_at ASC` (non-deterministic)
- ⚠️ **ISSUE:** Different processing order may affect:
  - Which events create new incidents vs. add evidence to existing incidents
  - Confidence accumulation order
  - State transitions
- ❌ **CRITICAL FAILURE:** Same evidence set may produce different incident graph if processed in different order

**Ordering Guarantees (or Lack Thereof):**
- ❌ **CRITICAL FAILURE:** No ordering guarantees: `services/correlation-engine/app/db.py:109` - `ORDER BY ingested_at ASC` (non-deterministic)
- ❌ **CRITICAL FAILURE:** Ordering depends on `ingested_at` (ingest_time), which is non-deterministic (from Validation File 06)
- ⚠️ **ISSUE:** No explicit ordering guarantees documented (ordering is best-effort based on ingested_at)

**Determinism Depends on database NOW(), ingest_time, or Ordering Side Effects:**
- ❌ **CRITICAL FAILURE:** Event ordering depends on `ingested_at`: `services/correlation-engine/app/db.py:109` - `ORDER BY ingested_at ASC` (non-deterministic)
- ⚠️ **ISSUE:** State transition timestamps use `NOW()`: `services/correlation-engine/app/db.py:343,354` - `NOW()` used for timestamps (non-deterministic)
- ⚠️ **ISSUE:** Incident creation timestamps use `NOW()`: `services/correlation-engine/app/db.py:166,175` - `NOW()` used for timestamps (non-deterministic)
- ❌ **CRITICAL FAILURE:** Determinism depends on `ingested_at` ordering (non-deterministic)

### Verdict: **FAIL**

**Justification:**
- **CRITICAL FAILURE:** Same evidence set may produce different incident graph if processed in different order (ordering depends on ingested_at)
- **CRITICAL FAILURE:** No ordering guarantees (ordering depends on non-deterministic ingested_at)
- **CRITICAL FAILURE:** Determinism depends on ingest_time ordering (non-deterministic)

**FAIL Conditions (Met):**
- Same evidence → same incident graph — **NOT CONFIRMED** (ordering affects incident graph)
- Determinism depends on ingest_time — **CONFIRMED** (ordering depends on ingested_at)

**Evidence Required:**
- File paths: `services/correlation-engine/app/db.py:109,166,175,343,354`
- Ordering: `ORDER BY ingested_at ASC` (non-deterministic)
- Timestamps: `NOW()` usage in incident creation and state transitions

---

## 6. FAIL-CLOSED & ERROR HANDLING

### Evidence

**Correlation Halts on Inconsistent Data:**
- ✅ Duplicate incident creation check: `services/correlation-engine/app/db.py:143-152` - Checks if event already linked to incident, terminates on duplicate
- ✅ Error handling: `services/correlation-engine/app/main.py:184-187` - Exception handling rolls back transaction and raises
- ⚠️ **ISSUE:** Processing continues on error: `services/correlation-engine/app/main.py:260-272` - Exception handling logs error and continues with next event (not fail-closed)
- ⚠️ **ISSUE:** Errors are logged but processing continues: `services/correlation-engine/app/main.py:269-272` - `events_failed += 1`, `continue` (silent degradation)

**No Silent Drops or Partial Correlation:**
- ⚠️ **ISSUE:** Silent degradation exists: `services/correlation-engine/app/main.py:260-272` - Exception handling logs error and continues (silent degradation)
- ⚠️ **ISSUE:** Partial correlation is possible: If some events fail to process, correlation is partial (not all events processed)
- ✅ Duplicate processing is prevented: `services/correlation-engine/app/main.py:112` - `check_event_processed()` prevents duplicate processing

**Behavior on Missing Input Data:**
- ✅ Missing input data causes error: `services/correlation-engine/app/main.py:108` - `event_id = event['event_id']` (KeyError if missing)
- ⚠️ **ISSUE:** Missing input data does NOT cause termination: `services/correlation-engine/app/main.py:260-272` - Exception handling logs error and continues

**Behavior on Conflicting Signals:**
- ✅ Contradiction detection: `services/correlation-engine/app/main.py:144` - `detect_contradiction(event, [])` detects contradictions
- ✅ Contradiction handling: `services/correlation-engine/app/main.py:147-149` - `apply_contradiction_to_incident()` applies confidence decay
- ⚠️ **ISSUE:** Contradiction detection is simplified: `services/correlation-engine/app/state_machine.py:208-242` - Simple contradiction detection (logic only, no comprehensive rules)

### Verdict: **PARTIAL**

**Justification:**
- Duplicate incident creation is prevented (fail-fast on duplicate)
- Contradiction detection and handling exists (confidence decay on contradiction)
- **ISSUE:** Processing continues on error (not fail-closed, silent degradation)
- **ISSUE:** Partial correlation is possible (if some events fail to process)

**PASS Conditions (Met):**
- Correlation halts on inconsistent data — **PARTIAL** (duplicate creation halts, but other errors continue)

**FAIL Conditions (Met):**
- No silent drops or partial correlation — **NOT CONFIRMED** (silent degradation exists)

**Evidence Required:**
- File paths: `services/correlation-engine/app/db.py:143-152`, `services/correlation-engine/app/main.py:184-187,260-272,144,147-149`
- Error handling: Exception handling, rollback, continue logic
- Contradiction: Detection and handling logic

---

## CREDENTIAL TYPES VALIDATED

### Database Credentials
- **Type:** PostgreSQL user/password (`RANSOMEYE_DB_USER`/`RANSOMEYE_DB_PASSWORD`)
- **Source:** Environment variable (required, no default)
- **Validation:** ❌ **NOT VALIDATED** (validation file 05 covers database credentials)
- **Usage:** Database connection for correlation operations
- **Status:** ❌ **NOT VALIDATED** (outside scope of this validation)

---

## PASS CONDITIONS

### Section 1: Incident Identity & Deduplication
- ✅ Incident identity is stable — **PASS**
- ✅ Same logical entity maps to same incident — **PASS**
- ❌ Incident identity does NOT depend on ingest_time — **FAIL**

### Section 2: State Machine Correctness
- ✅ Exact enforcement of SUSPICIOUS → PROBABLE → CONFIRMED — **PASS**
- ✅ Forward-only transitions — **PASS**
- ✅ No single-signal CONFIRMED paths — **PASS**
- ⚠️ State transitions do NOT depend on timing artifacts — **PARTIAL**

### Section 3: Confidence Accumulation Math
- ✅ Bounded confidence math — **PASS**
- ✅ Deterministic accumulation — **PARTIAL** (formula is deterministic, but order affects result)
- ❌ Confidence does NOT differ for identical evidence sets — **FAIL**
- ❌ Confidence math does NOT depend on arrival time — **FAIL**

### Section 4: Replay & Reprocessing Behavior
- ❌ Reprocessing produces same incidents — **FAIL**
- ❌ Non-deterministic ingest_time does NOT break replayability — **FAIL**

### Section 5: Determinism Guarantees
- ❌ Same evidence → same incident graph — **FAIL**
- ❌ Ordering guarantees exist — **FAIL**

### Section 6: Fail-Closed & Error Handling
- ⚠️ Correlation halts on inconsistent data — **PARTIAL**
- ⚠️ No silent drops or partial correlation — **PARTIAL**

---

## FAIL CONDITIONS

### Section 1: Incident Identity & Deduplication
- ❌ **CONFIRMED:** Incident identity depends on ingest_time — **Event ordering depends on ingested_at (non-deterministic)**

### Section 2: State Machine Correctness
- ❌ State transitions depend on timing artifacts — **PARTIAL** (timestamps use NOW(), but state logic is deterministic)

### Section 3: Confidence Accumulation Math
- ❌ **CONFIRMED:** Confidence differs for identical evidence sets — **Processing order affects accumulation**
- ❌ **CONFIRMED:** Confidence math depends on arrival time — **Ordering depends on ingested_at**

### Section 4: Replay & Reprocessing Behavior
- ❌ **CONFIRMED:** Reprocessing produces different incidents or states — **Ordering depends on ingested_at**
- ❌ **CONFIRMED:** Non-deterministic ingest_time breaks replayability — **Ordering depends on ingested_at**

### Section 5: Determinism Guarantees
- ❌ **CONFIRMED:** Same evidence → different incident graph — **Ordering affects incident graph**
- ❌ **CONFIRMED:** Determinism depends on ingest_time — **Ordering depends on ingested_at**

### Section 6: Fail-Closed & Error Handling
- ❌ Silent drops or partial correlation exist — **CONFIRMED** (silent degradation exists)

---

## EVIDENCE REQUIRED

### Incident Identity & Deduplication
- File paths: `services/correlation-engine/app/main.py:169,135-137`, `services/correlation-engine/app/state_machine.py:166-190`, `services/correlation-engine/app/db.py:109,240-241`
- Incident identity: UUID v4 generation, PRIMARY KEY constraint
- Deduplication: Key generation, time window, lookup logic
- Ordering: `ORDER BY ingested_at ASC` (non-deterministic)

### State Machine Correctness
- File paths: `services/correlation-engine/app/state_machine.py:16,106-126,129-163`, `services/correlation-engine/app/db.py:336-344,343,354`
- State machine: Stage definition, transition guards, threshold enforcement
- Timestamps: `NOW()` usage in state transitions

### Confidence Accumulation Math
- File paths: `services/correlation-engine/app/state_machine.py:61-81,24-33,42-58`, `services/correlation-engine/app/db.py:109,305-306`
- Confidence accumulation: Formula, bounds, determinism
- Ordering: `ORDER BY ingested_at ASC` (non-deterministic)

### Replay & Reprocessing Behavior
- File paths: `services/correlation-engine/app/db.py:109`, `services/correlation-engine/app/main.py:112`
- Ordering: `ORDER BY ingested_at ASC` (non-deterministic)
- Idempotency: `check_event_processed()` prevents duplicate processing

### Determinism Guarantees
- File paths: `services/correlation-engine/app/db.py:109,166,175,343,354`
- Ordering: `ORDER BY ingested_at ASC` (non-deterministic)
- Timestamps: `NOW()` usage in incident creation and state transitions

### Fail-Closed & Error Handling
- File paths: `services/correlation-engine/app/db.py:143-152`, `services/correlation-engine/app/main.py:184-187,260-272,144,147-149`
- Error handling: Exception handling, rollback, continue logic
- Contradiction: Detection and handling logic

---

## GA VERDICT

### Overall: **FAIL**

**Critical Blockers:**

1. **FAIL:** Event ordering depends on `ingested_at` (non-deterministic)
   - **Impact:** Processing order is non-deterministic, affecting incident creation, deduplication, confidence accumulation, and state transitions
   - **Location:** `services/correlation-engine/app/db.py:109` — `ORDER BY ingested_at ASC`
   - **Severity:** **CRITICAL** (violates determinism requirement)
   - **Master Spec Violation:** Correlation engine must be deterministic, not dependent on non-deterministic ingest_time

2. **FAIL:** Same evidence set may produce different incident graph if processed in different order
   - **Impact:** Reprocessing same raw_events with different `ingested_at` values may produce different incidents or different state transitions
   - **Location:** `services/correlation-engine/app/db.py:109` — `ORDER BY ingested_at ASC`
   - **Severity:** **CRITICAL** (violates replay determinism requirement)
   - **Master Spec Violation:** Reprocessing must produce same incidents

3. **FAIL:** Confidence accumulation order depends on processing order (which depends on `ingested_at`)
   - **Impact:** Same evidence set may produce different confidence if processed in different order
   - **Location:** `services/correlation-engine/app/db.py:109` — `ORDER BY ingested_at ASC`
   - **Severity:** **CRITICAL** (violates confidence determinism requirement)
   - **Master Spec Violation:** Confidence accumulation must be deterministic

4. **PARTIAL:** State transition timestamps use `NOW()` (non-deterministic)
   - **Impact:** Timestamps are non-deterministic, affecting replay fidelity
   - **Location:** `services/correlation-engine/app/db.py:343,354` — `NOW()` used for timestamps
   - **Severity:** **HIGH** (affects replay determinism)
   - **Master Spec Violation:** Timestamps should be deterministic for replay

5. **PARTIAL:** Processing continues on error (not fail-closed)
   - **Impact:** Silent degradation, partial correlation possible
   - **Location:** `services/correlation-engine/app/main.py:260-272` — Exception handling continues processing
   - **Severity:** **MEDIUM** (affects fail-closed behavior)
   - **Master Spec Violation:** Correlation must halt on inconsistent data

**Non-Blocking Issues:**

1. State machine correctly enforces SUSPICIOUS → PROBABLE → CONFIRMED progression
2. Forward-only transitions are enforced (no backward transitions)
3. No single-signal CONFIRMED paths (single signal → SUSPICIOUS only)
4. Confidence accumulation math is bounded and deterministic (formula is correct)
5. Deduplication works within time window (uses observed_at, not ingested_at)
6. Contradiction detection and handling exists (confidence decay on contradiction)

**Strengths:**

1. ✅ State machine correctly enforces state progression
2. ✅ Forward-only transitions are enforced
3. ✅ No single-signal CONFIRMED paths
4. ✅ Confidence accumulation math is bounded
5. ✅ Deduplication works (uses observed_at for time window)
6. ✅ Contradiction detection and handling exists

**Summary of Critical Blockers:**

1. **CRITICAL:** Event ordering depends on `ingested_at` (non-deterministic) — breaks determinism, replayability, and confidence accumulation determinism
2. **CRITICAL:** Same evidence set may produce different incident graph if processed in different order — breaks replay determinism
3. **CRITICAL:** Confidence accumulation order depends on processing order — breaks confidence determinism
4. **HIGH:** State transition timestamps use `NOW()` (non-deterministic) — affects replay fidelity
5. **MEDIUM:** Processing continues on error (not fail-closed) — affects fail-closed behavior

---

**Validation Date:** 2025-01-13  
**Validator:** Independent System Validator  
**Next Step:** Validation Step 8 — AI Core / ML / SHAP  
**GA Status:** **BLOCKED** (Critical failures in determinism and replayability)

---

## DOWNSTREAM IMPACT STATEMENT

**Documentation Only:** This section documents downstream impact of correlation engine non-determinism on downstream validations.

**Downstream Validations Impacted by Correlation Non-Determinism:**

1. **AI Core / ML / SHAP (Validation Step 8):**
   - AI Core reads incidents created by correlation engine
   - Correlation engine produces non-deterministic incidents (due to non-deterministic ordering)
   - AI Core validation (File 08) must NOT assume deterministic incident creation
   - AI Core validation must NOT assume replay fidelity for incident data

**Requirements for Downstream Validations:**

- File 08 must NOT assume deterministic incident creation (incidents may differ on replay)
- File 08 must NOT assume replay fidelity (same events may produce different incidents)
- File 08 must validate AI/ML components based on actual behavior, not assumptions about correlation determinism
- File 08 must explicitly document any dependencies on correlation determinism if they exist
