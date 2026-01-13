# Validation Step 16 — End-to-End Threat Scenarios & Detection State Machine

**Component Identity:**
- **Name:** System-Wide Threat Handling (Agents + DPI + Ingest + Correlation + AI + Policy)
- **Primary Paths:**
  - `/home/ransomeye/rebuild/services/correlation-engine/` - Correlation engine (incident creation)
  - `/home/ransomeye/rebuild/services/ai-core/` - AI Core (read-only metadata)
  - `/home/ransomeye/rebuild/services/policy-engine/` - Policy Engine (simulation-first)
  - `/home/ransomeye/rebuild/services/ui/backend/` - UI Backend (read-only)
  - `/home/ransomeye/rebuild/agents/` - Endpoint agents (Linux & Windows)
  - `/home/ransomeye/rebuild/dpi/probe/` - DPI Probe (network sensor)
- **Entry Points:**
  - Correlation engine: `services/correlation-engine/app/main.py:151` - `run_correlation_engine()`
  - AI Core: `services/ai-core/app/main.py` - Batch processing loop
  - Policy Engine: `services/policy-engine/app/main.py:200` - `run_policy_engine()`
  - UI Backend: `services/ui/backend/main.py:1` - FastAPI application

**Spec Reference:**
- State Machine: `schemas/04_correlation.sql:6-11` - `incident_stage` enum: `CLEAN`, `SUSPICIOUS`, `PROBABLE`, `CONFIRMED`
- Threat Analysis: `THREAT_PROTECTION_ANALYSIS.md`, `THREAT_PROTECTION_ANALYSIS_V2.md`
- Correlation Engine README: `services/correlation-engine/README.md`
- Validation Step 7: `validation/07-correlation-engine.md`

---

## SCENARIO 1: RANSOMWARE (FILELESS + ENCRYPTOR)

### 1. SIGNAL ORIGIN & GROUND TRUTH

**Evidence:**
- ✅ Agent can emit FILE_ENCRYPT events: `schemas/02_normalized_agent.sql:15-22` - `file_activity_type` enum includes `FILE_ENCRYPT`
- ✅ Windows Agent detects file encryption: `agents/windows/ETW_ARCHITECTURE_DESIGN.md:123` - File entropy change (heuristic) → `file_activity` table (activity_type: FILE_ENCRYPT)
- ✅ Ransomware detection documented: `THREAT_PROTECTION_ANALYSIS.md:25` - "File encryption events (`FILE_ENCRYPT`) monitored by agents"
- ⚠️ **ISSUE:** Signal is NOT authenticated: `validation/07-correlation-engine.md:122-129` - Events are NOT cryptographically authenticated (from previous validation)
- ⚠️ **ISSUE:** Signal alone is sufficient: `services/correlation-engine/app/rules.py:48` - `if component == 'linux_agent':` creates incident (single signal is sufficient, no cross-domain correlation required)

**Verdict:** **PARTIAL**

### 2. CROSS-DOMAIN CORRELATION

**Evidence:**
- ❌ **CRITICAL:** No Agent ↔ DPI linkage found:
  - `services/correlation-engine/app/rules.py:16-59` - Only rule checks `component == 'linux_agent'` (no DPI correlation)
  - No code found that links agent FILE_ENCRYPT events with DPI network events
- ❌ **CRITICAL:** No host ↔ network correlation found:
  - `validation/07-correlation-engine.md:167-183` - No contradiction detection found, no cross-domain correlation found
- ❌ **CRITICAL:** No identity binding found:
  - `services/correlation-engine/app/rules.py:44-48` - Only checks `component`, no machine_id/IP correlation with DPI flows

**Verdict:** **FAIL**

### 3. CONFIDENCE ACCUMULATION

**Evidence:**
- ❌ **CRITICAL:** No confidence accumulation found:
  - `services/correlation-engine/app/rules.py:54` - `confidence_score = 0.3` (constant, not accumulated)
  - `validation/07-correlation-engine.md:192-248` - No weight definitions, accumulation logic, or thresholds found
- ❌ **CRITICAL:** No incremental weights found:
  - Confidence is constant (0.3), not computed from multiple signals
- ❌ **CRITICAL:** Direct jump to SUSPICIOUS without accumulation:
  - `services/correlation-engine/app/rules.py:53` - `stage = 'SUSPICIOUS'` (constant, no accumulation required)

**Verdict:** **FAIL**

### 4. STATE MACHINE TRANSITIONS

**Evidence:**
- ❌ **CRITICAL:** No state transitions found:
  - `services/correlation-engine/app/rules.py:53` - `stage = 'SUSPICIOUS'` (constant, no transitions)
  - `validation/07-correlation-engine.md:257-298` - No state machine definition, no transition logic, no transition guards found
- ❌ **CRITICAL:** CLEAN state is skipped:
  - `services/correlation-engine/app/rules.py:53` - Incidents created directly with `stage='SUSPICIOUS'` (skips CLEAN)
- ❌ **CRITICAL:** No transitions to PROBABLE or CONFIRMED:
  - Incidents created with `stage='SUSPICIOUS'` and never transition

**Verdict:** **FAIL**

### 5. AI INVOLVEMENT

**Evidence:**
- ✅ AI operates only after correlation: `services/ai-core/README.md:11-12` - "Consumes Existing Incidents" (reads from incidents table, not raw events)
- ✅ AI does NOT change state: `services/ai-core/README.md:39` - "NO incident modification: Does not create, update, or delete incidents"
- ✅ AI produces explainability: `services/ai-core/README.md:24` - "SHAP Explanations: Explains incident confidence contributions"
- ✅ AI is read-only: `services/ai-core/README.md:35-48` - AI Core is read-only with respect to facts

**Verdict:** **PASS**

### 6. POLICY ELIGIBILITY

**Evidence:**
- ✅ Policy engine eligibility triggered only at SUSPICIOUS: `services/policy-engine/app/rules.py:18` - `evaluate_suspicious_incident_rule()` checks `incident.current_stage == 'SUSPICIOUS'`
- ✅ No enforcement during validation: `services/policy-engine/README.md:38-48` - Simulation-first mode, no execution, no enforcement
- ✅ Correct command readiness signals: `services/policy-engine/app/main.py:286-300` - Generates signed command but does NOT execute (simulation-first)
- ⚠️ **ISSUE:** Policy triggered by single sensor: `services/policy-engine/app/rules.py:18` - Evaluates incidents with `stage='SUSPICIOUS'` (which can be created by single agent signal)

**Verdict:** **PARTIAL**

### 7. FAILURE & PARTIAL-VISIBILITY HANDLING

**Evidence:**
- ⚠️ **ISSUE:** Full confidence with partial data:
  - `services/correlation-engine/app/rules.py:54` - `confidence_score = 0.3` (constant, not degraded when DPI missing)
- ⚠️ **ISSUE:** Silent blind spots:
  - No code found that detects missing sensors or degrades confidence
- ⚠️ **ISSUE:** Assumed sensor truth:
  - `services/correlation-engine/app/rules.py:48` - Single agent signal creates incident (no verification from other sensors)

**Verdict:** **FAIL**

### 8. NEGATIVE VALIDATION

**Evidence:**
- ❌ **CRITICAL:** Agent alone CAN confirm attack:
  - `services/correlation-engine/app/rules.py:48` - `if component == 'linux_agent':` creates incident (single agent signal is sufficient)
- ❌ **CRITICAL:** DPI alone CANNOT confirm attack:
  - `services/correlation-engine/app/rules.py:48` - Rule only checks `component == 'linux_agent'` (DPI events would not match)
- ✅ AI alone CANNOT confirm attack: `services/ai-core/README.md:39` - "NO incident modification: Does not create, update, or delete incidents"
- ✅ UI CANNOT escalate incident: `validation/14-ui-api-access-control.md` - UI is read-only, no action buttons, no edit forms
- ✅ Policy CANNOT enforce without correlation: `services/policy-engine/README.md:60` - "NO incident modification: Policy engine does NOT modify incident state"

**Verdict:** **PARTIAL**

### Scenario 1 Verdict: **FAIL**

**Justification:**
- Signal origin exists (FILE_ENCRYPT events can be emitted by agents)
- Signal is NOT authenticated (from previous validation)
- Signal alone is sufficient (single agent signal creates incident)
- **CRITICAL:** No cross-domain correlation (no Agent ↔ DPI linkage, no host ↔ network correlation, no identity binding)
- **CRITICAL:** No confidence accumulation (confidence is constant 0.3, not accumulated)
- **CRITICAL:** No state transitions (incidents created with SUSPICIOUS and never transition, CLEAN state skipped)
- AI involvement is correct (read-only, produces SHAP explanations)
- Policy eligibility is partially correct (triggered at SUSPICIOUS, but can be triggered by single sensor)
- **CRITICAL:** Full confidence with partial data (confidence not degraded when sensors missing)
- **CRITICAL:** Agent alone CAN confirm attack (single agent signal creates incident)

---

## SCENARIO 2: WORM / LATERAL PROPAGATION

### 1. SIGNAL ORIGIN & GROUND TRUTH

**Evidence:**
- ✅ DPI can detect network scanning: `THREAT_PROTECTION_ANALYSIS.md:52` - "Network scanning patterns detectable via DPI probe"
- ✅ DPI can detect SMB traffic: `THREAT_PROTECTION_ANALYSIS_V2.md:25` - "SMB traffic (Ports 139/445) monitored"
- ✅ Worm propagation documented: `THREAT_PROTECTION_ANALYSIS.md:52` - "Worm propagation patterns detectable via correlation engine"
- ⚠️ **ISSUE:** Signal is NOT authenticated: `validation/07-correlation-engine.md:122-129` - Events are NOT cryptographically authenticated
- ⚠️ **ISSUE:** Signal alone is sufficient: `services/correlation-engine/app/rules.py:48` - `if component == 'linux_agent':` creates incident (single signal is sufficient)

**Verdict:** **PARTIAL**

### 2. CROSS-DOMAIN CORRELATION

**Evidence:**
- ❌ **CRITICAL:** No Agent ↔ DPI linkage found:
  - `services/correlation-engine/app/rules.py:16-59` - Only rule checks `component == 'linux_agent'` (no DPI correlation)
  - No code found that links agent process events with DPI network scanning events
- ❌ **CRITICAL:** No host ↔ network correlation found:
  - `validation/07-correlation-engine.md:167-183` - No contradiction detection found, no cross-domain correlation found
- ❌ **CRITICAL:** No identity binding found:
  - `services/correlation-engine/app/rules.py:44-48` - Only checks `component`, no machine_id/IP correlation

**Verdict:** **FAIL**

### 3. CONFIDENCE ACCUMULATION

**Evidence:**
- ❌ **CRITICAL:** No confidence accumulation found:
  - `services/correlation-engine/app/rules.py:54` - `confidence_score = 0.3` (constant, not accumulated)
  - No incremental weights found
- ❌ **CRITICAL:** Direct jump to SUSPICIOUS without accumulation:
  - `services/correlation-engine/app/rules.py:53` - `stage = 'SUSPICIOUS'` (constant, no accumulation required)

**Verdict:** **FAIL**

### 4. STATE MACHINE TRANSITIONS

**Evidence:**
- ❌ **CRITICAL:** No state transitions found:
  - `services/correlation-engine/app/rules.py:53` - `stage = 'SUSPICIOUS'` (constant, no transitions)
  - CLEAN state skipped, no transitions to PROBABLE or CONFIRMED

**Verdict:** **FAIL**

### 5. AI INVOLVEMENT

**Evidence:**
- ✅ AI operates only after correlation: `services/ai-core/README.md:11-12` - "Consumes Existing Incidents"
- ✅ AI does NOT change state: `services/ai-core/README.md:39` - "NO incident modification"
- ✅ AI produces explainability: `services/ai-core/README.md:24` - "SHAP Explanations"

**Verdict:** **PASS**

### 6. POLICY ELIGIBILITY

**Evidence:**
- ✅ Policy engine eligibility triggered only at SUSPICIOUS: `services/policy-engine/app/rules.py:18` - Checks `incident.current_stage == 'SUSPICIOUS'`
- ✅ No enforcement during validation: `services/policy-engine/README.md:38-48` - Simulation-first mode
- ✅ Correct command readiness signals: `services/policy-engine/app/main.py:286-300` - Generates signed command but does NOT execute
- ⚠️ **ISSUE:** Policy triggered by single sensor: `services/policy-engine/app/rules.py:18` - Evaluates incidents with `stage='SUSPICIOUS'` (which can be created by single signal)

**Verdict:** **PARTIAL**

### 7. FAILURE & PARTIAL-VISIBILITY HANDLING

**Evidence:**
- ⚠️ **ISSUE:** Full confidence with partial data:
  - `services/correlation-engine/app/rules.py:54` - `confidence_score = 0.3` (constant, not degraded when sensors missing)
- ⚠️ **ISSUE:** Silent blind spots:
  - No code found that detects missing sensors
- ⚠️ **ISSUE:** Assumed sensor truth:
  - Single signal creates incident (no verification from other sensors)

**Verdict:** **FAIL**

### 8. NEGATIVE VALIDATION

**Evidence:**
- ❌ **CRITICAL:** Agent alone CAN confirm attack:
  - `services/correlation-engine/app/rules.py:48` - `if component == 'linux_agent':` creates incident
- ❌ **CRITICAL:** DPI alone CANNOT confirm attack:
  - `services/correlation-engine/app/rules.py:48` - Rule only checks `component == 'linux_agent'` (DPI events would not match)
- ✅ AI alone CANNOT confirm attack: `services/ai-core/README.md:39` - "NO incident modification"
- ✅ UI CANNOT escalate incident: `validation/14-ui-api-access-control.md` - UI is read-only
- ✅ Policy CANNOT enforce without correlation: `services/policy-engine/README.md:60` - "NO incident modification"

**Verdict:** **PARTIAL**

### Scenario 2 Verdict: **FAIL**

**Justification:**
- Signal origin exists (DPI can detect network scanning, SMB traffic)
- Signal is NOT authenticated
- Signal alone is sufficient
- **CRITICAL:** No cross-domain correlation (no Agent ↔ DPI linkage, no host ↔ network correlation)
- **CRITICAL:** No confidence accumulation
- **CRITICAL:** No state transitions
- AI involvement is correct
- Policy eligibility is partially correct
- **CRITICAL:** Full confidence with partial data
- **CRITICAL:** Agent alone CAN confirm attack

---

## SCENARIO 3: TROJAN / BACKDOOR PERSISTENCE

### 1. SIGNAL ORIGIN & GROUND TRUTH

**Evidence:**
- ✅ Agent can detect persistence: `schemas/02_normalized_agent.sql:24-34` - `persistence_type` enum includes SCHEDULED_TASK, SERVICE, REGISTRY_RUN_KEY, etc.
- ✅ Windows Agent detects registry persistence: `agents/windows/ETW_ARCHITECTURE_DESIGN.md:125-139` - Registry activity monitoring for autorun & persistence
- ✅ Trojan detection documented: `THREAT_PROTECTION_ANALYSIS.md:43` - "Network connections monitored (DPI probe). Process execution monitored"
- ⚠️ **ISSUE:** Signal is NOT authenticated: `validation/07-correlation-engine.md:122-129` - Events are NOT cryptographically authenticated
- ⚠️ **ISSUE:** Signal alone is sufficient: `services/correlation-engine/app/rules.py:48` - Single signal creates incident

**Verdict:** **PARTIAL**

### 2. CROSS-DOMAIN CORRELATION

**Evidence:**
- ❌ **CRITICAL:** No Agent ↔ DPI linkage found:
  - `services/correlation-engine/app/rules.py:16-59` - Only rule checks `component == 'linux_agent'` (no DPI correlation)
  - No code found that links agent persistence events with DPI network connection events
- ❌ **CRITICAL:** No host ↔ network correlation found:
  - `validation/07-correlation-engine.md:167-183` - No cross-domain correlation found
- ❌ **CRITICAL:** No identity binding found:
  - `services/correlation-engine/app/rules.py:44-48` - Only checks `component`, no machine_id/IP correlation

**Verdict:** **FAIL**

### 3. CONFIDENCE ACCUMULATION

**Evidence:**
- ❌ **CRITICAL:** No confidence accumulation found:
  - `services/correlation-engine/app/rules.py:54` - `confidence_score = 0.3` (constant, not accumulated)
- ❌ **CRITICAL:** Direct jump to SUSPICIOUS without accumulation:
  - `services/correlation-engine/app/rules.py:53` - `stage = 'SUSPICIOUS'` (constant, no accumulation required)

**Verdict:** **FAIL**

### 4. STATE MACHINE TRANSITIONS

**Evidence:**
- ❌ **CRITICAL:** No state transitions found:
  - `services/correlation-engine/app/rules.py:53` - `stage = 'SUSPICIOUS'` (constant, no transitions)
  - CLEAN state skipped, no transitions to PROBABLE or CONFIRMED

**Verdict:** **FAIL**

### 5. AI INVOLVEMENT

**Evidence:**
- ✅ AI operates only after correlation: `services/ai-core/README.md:11-12` - "Consumes Existing Incidents"
- ✅ AI does NOT change state: `services/ai-core/README.md:39` - "NO incident modification"
- ✅ AI produces explainability: `services/ai-core/README.md:24` - "SHAP Explanations"

**Verdict:** **PASS**

### 6. POLICY ELIGIBILITY

**Evidence:**
- ✅ Policy engine eligibility triggered only at SUSPICIOUS: `services/policy-engine/app/rules.py:18` - Checks `incident.current_stage == 'SUSPICIOUS'`
- ✅ No enforcement during validation: `services/policy-engine/README.md:38-48` - Simulation-first mode
- ✅ Correct command readiness signals: `services/policy-engine/app/main.py:286-300` - Generates signed command but does NOT execute
- ⚠️ **ISSUE:** Policy triggered by single sensor: `services/policy-engine/app/rules.py:18` - Evaluates incidents with `stage='SUSPICIOUS'` (which can be created by single signal)

**Verdict:** **PARTIAL**

### 7. FAILURE & PARTIAL-VISIBILITY HANDLING

**Evidence:**
- ⚠️ **ISSUE:** Full confidence with partial data:
  - `services/correlation-engine/app/rules.py:54` - `confidence_score = 0.3` (constant, not degraded when sensors missing)
- ⚠️ **ISSUE:** Silent blind spots:
  - No code found that detects missing sensors
- ⚠️ **ISSUE:** Assumed sensor truth:
  - Single signal creates incident (no verification from other sensors)

**Verdict:** **FAIL**

### 8. NEGATIVE VALIDATION

**Evidence:**
- ❌ **CRITICAL:** Agent alone CAN confirm attack:
  - `services/correlation-engine/app/rules.py:48` - `if component == 'linux_agent':` creates incident
- ❌ **CRITICAL:** DPI alone CANNOT confirm attack:
  - `services/correlation-engine/app/rules.py:48` - Rule only checks `component == 'linux_agent'` (DPI events would not match)
- ✅ AI alone CANNOT confirm attack: `services/ai-core/README.md:39` - "NO incident modification"
- ✅ UI CANNOT escalate incident: `validation/14-ui-api-access-control.md` - UI is read-only
- ✅ Policy CANNOT enforce without correlation: `services/policy-engine/README.md:60` - "NO incident modification"

**Verdict:** **PARTIAL**

### Scenario 3 Verdict: **FAIL**

**Justification:**
- Signal origin exists (agents can detect persistence, DPI can detect network connections)
- Signal is NOT authenticated
- Signal alone is sufficient
- **CRITICAL:** No cross-domain correlation (no Agent ↔ DPI linkage, no host ↔ network correlation)
- **CRITICAL:** No confidence accumulation
- **CRITICAL:** No state transitions
- AI involvement is correct
- Policy eligibility is partially correct
- **CRITICAL:** Full confidence with partial data
- **CRITICAL:** Agent alone CAN confirm attack

---

## SCENARIO 4: CREDENTIAL HARVESTING / PASSWORD SPRAY

### 1. SIGNAL ORIGIN & GROUND TRUTH

**Evidence:**
- ✅ Agent can detect credential access: `hnmp/schema/host-event.schema.json:33` - `event_type` enum includes `credential_access_attempt`
- ✅ Authentication monitoring documented: `THREAT_PROTECTION_ANALYSIS_V2.md:178` - "Strong brute force and credential attack detection"
- ⚠️ **ISSUE:** Signal is NOT authenticated: `validation/07-correlation-engine.md:122-129` - Events are NOT cryptographically authenticated
- ⚠️ **ISSUE:** Signal alone is sufficient: `services/correlation-engine/app/rules.py:48` - Single signal creates incident

**Verdict:** **PARTIAL**

### 2. CROSS-DOMAIN CORRELATION

**Evidence:**
- ❌ **CRITICAL:** No Agent ↔ DPI linkage found:
  - `services/correlation-engine/app/rules.py:16-59` - Only rule checks `component == 'linux_agent'` (no DPI correlation)
  - No code found that links agent credential access events with DPI authentication traffic
- ❌ **CRITICAL:** No host ↔ network correlation found:
  - `validation/07-correlation-engine.md:167-183` - No cross-domain correlation found
- ❌ **CRITICAL:** No identity binding found:
  - `services/correlation-engine/app/rules.py:44-48` - Only checks `component`, no machine_id/IP correlation

**Verdict:** **FAIL**

### 3. CONFIDENCE ACCUMULATION

**Evidence:**
- ❌ **CRITICAL:** No confidence accumulation found:
  - `services/correlation-engine/app/rules.py:54` - `confidence_score = 0.3` (constant, not accumulated)
- ❌ **CRITICAL:** Direct jump to SUSPICIOUS without accumulation:
  - `services/correlation-engine/app/rules.py:53` - `stage = 'SUSPICIOUS'` (constant, no accumulation required)

**Verdict:** **FAIL**

### 4. STATE MACHINE TRANSITIONS

**Evidence:**
- ❌ **CRITICAL:** No state transitions found:
  - `services/correlation-engine/app/rules.py:53` - `stage = 'SUSPICIOUS'` (constant, no transitions)
  - CLEAN state skipped, no transitions to PROBABLE or CONFIRMED

**Verdict:** **FAIL**

### 5. AI INVOLVEMENT

**Evidence:**
- ✅ AI operates only after correlation: `services/ai-core/README.md:11-12` - "Consumes Existing Incidents"
- ✅ AI does NOT change state: `services/ai-core/README.md:39` - "NO incident modification"
- ✅ AI produces explainability: `services/ai-core/README.md:24` - "SHAP Explanations"

**Verdict:** **PASS**

### 6. POLICY ELIGIBILITY

**Evidence:**
- ✅ Policy engine eligibility triggered only at SUSPICIOUS: `services/policy-engine/app/rules.py:18` - Checks `incident.current_stage == 'SUSPICIOUS'`
- ✅ No enforcement during validation: `services/policy-engine/README.md:38-48` - Simulation-first mode
- ✅ Correct command readiness signals: `services/policy-engine/app/main.py:286-300` - Generates signed command but does NOT execute
- ⚠️ **ISSUE:** Policy triggered by single sensor: `services/policy-engine/app/rules.py:18` - Evaluates incidents with `stage='SUSPICIOUS'` (which can be created by single signal)

**Verdict:** **PARTIAL**

### 7. FAILURE & PARTIAL-VISIBILITY HANDLING

**Evidence:**
- ⚠️ **ISSUE:** Full confidence with partial data:
  - `services/correlation-engine/app/rules.py:54` - `confidence_score = 0.3` (constant, not degraded when sensors missing)
- ⚠️ **ISSUE:** Silent blind spots:
  - No code found that detects missing sensors
- ⚠️ **ISSUE:** Assumed sensor truth:
  - Single signal creates incident (no verification from other sensors)

**Verdict:** **FAIL**

### 8. NEGATIVE VALIDATION

**Evidence:**
- ❌ **CRITICAL:** Agent alone CAN confirm attack:
  - `services/correlation-engine/app/rules.py:48` - `if component == 'linux_agent':` creates incident
- ❌ **CRITICAL:** DPI alone CANNOT confirm attack:
  - `services/correlation-engine/app/rules.py:48` - Rule only checks `component == 'linux_agent'` (DPI events would not match)
- ✅ AI alone CANNOT confirm attack: `services/ai-core/README.md:39` - "NO incident modification"
- ✅ UI CANNOT escalate incident: `validation/14-ui-api-access-control.md` - UI is read-only
- ✅ Policy CANNOT enforce without correlation: `services/policy-engine/README.md:60` - "NO incident modification"

**Verdict:** **PARTIAL**

### Scenario 4 Verdict: **FAIL**

**Justification:**
- Signal origin exists (agents can detect credential access attempts)
- Signal is NOT authenticated
- Signal alone is sufficient
- **CRITICAL:** No cross-domain correlation (no Agent ↔ DPI linkage, no host ↔ network correlation)
- **CRITICAL:** No confidence accumulation
- **CRITICAL:** No state transitions
- AI involvement is correct
- Policy eligibility is partially correct
- **CRITICAL:** Full confidence with partial data
- **CRITICAL:** Agent alone CAN confirm attack

---

## SCENARIO 5: DNS TUNNELING

### 1. SIGNAL ORIGIN & GROUND TRUTH

**Evidence:**
- ✅ DPI can detect DNS queries: `schemas/03_normalized_dpi.sql:100-150` - `dns_queries` table for DNS query/response events
- ✅ DNS query monitoring documented: `THREAT_PROTECTION_ANALYSIS.md:97` - "DNS query/response anomalies detectable via DPI probe"
- ⚠️ **ISSUE:** Signal is NOT authenticated: `validation/07-correlation-engine.md:122-129` - Events are NOT cryptographically authenticated
- ⚠️ **ISSUE:** Signal alone is NOT sufficient (but correlation engine doesn't check):
  - `services/correlation-engine/app/rules.py:48` - Rule only checks `component == 'linux_agent'` (DPI events would not match, so DNS tunneling would NOT be detected)

**Verdict:** **FAIL**

### 2. CROSS-DOMAIN CORRELATION

**Evidence:**
- ❌ **CRITICAL:** No Agent ↔ DPI linkage found:
  - `services/correlation-engine/app/rules.py:16-59` - Only rule checks `component == 'linux_agent'` (no DPI correlation)
  - No code found that links agent DNS query events with DPI DNS query events
- ❌ **CRITICAL:** No host ↔ network correlation found:
  - `validation/07-correlation-engine.md:167-183` - No cross-domain correlation found
- ❌ **CRITICAL:** No identity binding found:
  - `services/correlation-engine/app/rules.py:44-48` - Only checks `component`, no machine_id/IP correlation

**Verdict:** **FAIL**

### 3. CONFIDENCE ACCUMULATION

**Evidence:**
- ❌ **CRITICAL:** No confidence accumulation found:
  - `services/correlation-engine/app/rules.py:54` - `confidence_score = 0.3` (constant, not accumulated)
- ❌ **CRITICAL:** Direct jump to SUSPICIOUS without accumulation:
  - `services/correlation-engine/app/rules.py:53` - `stage = 'SUSPICIOUS'` (constant, no accumulation required)

**Verdict:** **FAIL**

### 4. STATE MACHINE TRANSITIONS

**Evidence:**
- ❌ **CRITICAL:** No state transitions found:
  - `services/correlation-engine/app/rules.py:53` - `stage = 'SUSPICIOUS'` (constant, no transitions)
  - CLEAN state skipped, no transitions to PROBABLE or CONFIRMED

**Verdict:** **FAIL**

### 5. AI INVOLVEMENT

**Evidence:**
- ✅ AI operates only after correlation: `services/ai-core/README.md:11-12` - "Consumes Existing Incidents"
- ✅ AI does NOT change state: `services/ai-core/README.md:39` - "NO incident modification"
- ✅ AI produces explainability: `services/ai-core/README.md:24` - "SHAP Explanations"

**Verdict:** **PASS**

### 6. POLICY ELIGIBILITY

**Evidence:**
- ✅ Policy engine eligibility triggered only at SUSPICIOUS: `services/policy-engine/app/rules.py:18` - Checks `incident.current_stage == 'SUSPICIOUS'`
- ✅ No enforcement during validation: `services/policy-engine/README.md:38-48` - Simulation-first mode
- ✅ Correct command readiness signals: `services/policy-engine/app/main.py:286-300` - Generates signed command but does NOT execute
- ⚠️ **ISSUE:** Policy triggered by single sensor: `services/policy-engine/app/rules.py:18` - Evaluates incidents with `stage='SUSPICIOUS'` (which can be created by single signal)

**Verdict:** **PARTIAL**

### 7. FAILURE & PARTIAL-VISIBILITY HANDLING

**Evidence:**
- ⚠️ **ISSUE:** Full confidence with partial data:
  - `services/correlation-engine/app/rules.py:54` - `confidence_score = 0.3` (constant, not degraded when sensors missing)
- ⚠️ **ISSUE:** Silent blind spots:
  - No code found that detects missing sensors
- ⚠️ **ISSUE:** Assumed sensor truth:
  - Single signal creates incident (no verification from other sensors)

**Verdict:** **FAIL**

### 8. NEGATIVE VALIDATION

**Evidence:**
- ❌ **CRITICAL:** Agent alone CAN confirm attack:
  - `services/correlation-engine/app/rules.py:48` - `if component == 'linux_agent':` creates incident
- ❌ **CRITICAL:** DPI alone CANNOT confirm attack:
  - `services/correlation-engine/app/rules.py:48` - Rule only checks `component == 'linux_agent'` (DPI events would not match)
- ✅ AI alone CANNOT confirm attack: `services/ai-core/README.md:39` - "NO incident modification"
- ✅ UI CANNOT escalate incident: `validation/14-ui-api-access-control.md` - UI is read-only
- ✅ Policy CANNOT enforce without correlation: `services/policy-engine/README.md:60` - "NO incident modification"

**Verdict:** **PARTIAL**

### Scenario 5 Verdict: **FAIL**

**Justification:**
- Signal origin exists (DPI can detect DNS queries)
- Signal is NOT authenticated
- **CRITICAL:** Signal alone is NOT sufficient AND correlation engine doesn't detect DPI events (rule only checks `component == 'linux_agent'`, so DNS tunneling would NOT be detected)
- **CRITICAL:** No cross-domain correlation (no Agent ↔ DPI linkage, no host ↔ network correlation)
- **CRITICAL:** No confidence accumulation
- **CRITICAL:** No state transitions
- AI involvement is correct
- Policy eligibility is partially correct
- **CRITICAL:** Full confidence with partial data
- **CRITICAL:** Agent alone CAN confirm attack (but DPI alone CANNOT)

---

## SCENARIO 6: LOW-AND-SLOW DATA EXFILTRATION

### 1. SIGNAL ORIGIN & GROUND TRUTH

**Evidence:**
- ✅ DPI can detect data exfiltration: `THREAT_PROTECTION_ANALYSIS.md:26` - "Can detect file access patterns and exfiltration via network monitoring (DPI)"
- ✅ Exfiltration detection documented: `forensic-summarization/FORENSIC_SUMMARIZATION_ARCHITECTURE.md:424-430` - "Exfiltration Prep: Network connections, data collection, encryption"
- ⚠️ **ISSUE:** Signal is NOT authenticated: `validation/07-correlation-engine.md:122-129` - Events are NOT cryptographically authenticated
- ⚠️ **ISSUE:** Signal alone is NOT sufficient (but correlation engine doesn't check):
  - `services/correlation-engine/app/rules.py:48` - Rule only checks `component == 'linux_agent'` (DPI events would not match, so exfiltration would NOT be detected)

**Verdict:** **FAIL**

### 2. CROSS-DOMAIN CORRELATION

**Evidence:**
- ❌ **CRITICAL:** No Agent ↔ DPI linkage found:
  - `services/correlation-engine/app/rules.py:16-59` - Only rule checks `component == 'linux_agent'` (no DPI correlation)
  - No code found that links agent file access events with DPI network exfiltration events
- ❌ **CRITICAL:** No host ↔ network correlation found:
  - `validation/07-correlation-engine.md:167-183` - No cross-domain correlation found
- ❌ **CRITICAL:** No identity binding found:
  - `services/correlation-engine/app/rules.py:44-48` - Only checks `component`, no machine_id/IP correlation

**Verdict:** **FAIL**

### 3. CONFIDENCE ACCUMULATION

**Evidence:**
- ❌ **CRITICAL:** No confidence accumulation found:
  - `services/correlation-engine/app/rules.py:54` - `confidence_score = 0.3` (constant, not accumulated)
- ❌ **CRITICAL:** Direct jump to SUSPICIOUS without accumulation:
  - `services/correlation-engine/app/rules.py:53` - `stage = 'SUSPICIOUS'` (constant, no accumulation required)

**Verdict:** **FAIL**

### 4. STATE MACHINE TRANSITIONS

**Evidence:**
- ❌ **CRITICAL:** No state transitions found:
  - `services/correlation-engine/app/rules.py:53` - `stage = 'SUSPICIOUS'` (constant, no transitions)
  - CLEAN state skipped, no transitions to PROBABLE or CONFIRMED

**Verdict:** **FAIL**

### 5. AI INVOLVEMENT

**Evidence:**
- ✅ AI operates only after correlation: `services/ai-core/README.md:11-12` - "Consumes Existing Incidents"
- ✅ AI does NOT change state: `services/ai-core/README.md:39` - "NO incident modification"
- ✅ AI produces explainability: `services/ai-core/README.md:24` - "SHAP Explanations"

**Verdict:** **PASS**

### 6. POLICY ELIGIBILITY

**Evidence:**
- ✅ Policy engine eligibility triggered only at SUSPICIOUS: `services/policy-engine/app/rules.py:18` - Checks `incident.current_stage == 'SUSPICIOUS'`
- ✅ No enforcement during validation: `services/policy-engine/README.md:38-48` - Simulation-first mode
- ✅ Correct command readiness signals: `services/policy-engine/app/main.py:286-300` - Generates signed command but does NOT execute
- ⚠️ **ISSUE:** Policy triggered by single sensor: `services/policy-engine/app/rules.py:18` - Evaluates incidents with `stage='SUSPICIOUS'` (which can be created by single signal)

**Verdict:** **PARTIAL**

### 7. FAILURE & PARTIAL-VISIBILITY HANDLING

**Evidence:**
- ⚠️ **ISSUE:** Full confidence with partial data:
  - `services/correlation-engine/app/rules.py:54` - `confidence_score = 0.3` (constant, not degraded when sensors missing)
- ⚠️ **ISSUE:** Silent blind spots:
  - No code found that detects missing sensors
- ⚠️ **ISSUE:** Assumed sensor truth:
  - Single signal creates incident (no verification from other sensors)

**Verdict:** **FAIL**

### 8. NEGATIVE VALIDATION

**Evidence:**
- ❌ **CRITICAL:** Agent alone CAN confirm attack:
  - `services/correlation-engine/app/rules.py:48` - `if component == 'linux_agent':` creates incident
- ❌ **CRITICAL:** DPI alone CANNOT confirm attack:
  - `services/correlation-engine/app/rules.py:48` - Rule only checks `component == 'linux_agent'` (DPI events would not match)
- ✅ AI alone CANNOT confirm attack: `services/ai-core/README.md:39` - "NO incident modification"
- ✅ UI CANNOT escalate incident: `validation/14-ui-api-access-control.md` - UI is read-only
- ✅ Policy CANNOT enforce without correlation: `services/policy-engine/README.md:60` - "NO incident modification"

**Verdict:** **PARTIAL**

### Scenario 6 Verdict: **FAIL**

**Justification:**
- Signal origin exists (DPI can detect data exfiltration)
- Signal is NOT authenticated
- **CRITICAL:** Signal alone is NOT sufficient AND correlation engine doesn't detect DPI events (rule only checks `component == 'linux_agent'`, so exfiltration would NOT be detected)
- **CRITICAL:** No cross-domain correlation (no Agent ↔ DPI linkage, no host ↔ network correlation)
- **CRITICAL:** No confidence accumulation
- **CRITICAL:** No state transitions
- AI involvement is correct
- Policy eligibility is partially correct
- **CRITICAL:** Full confidence with partial data
- **CRITICAL:** Agent alone CAN confirm attack (but DPI alone CANNOT)

---

## SCENARIO 7: LIVING-OFF-THE-LAND (LOLBINS)

### 1. SIGNAL ORIGIN & GROUND TRUTH

**Evidence:**
- ✅ Agent can detect process execution: `schemas/02_normalized_agent.sql:7-12` - `process_activity_type` enum includes PROCESS_START, PROCESS_EXIT, PROCESS_INJECT
- ✅ Process monitoring documented: `THREAT_PROTECTION_ANALYSIS.md:35` - "Process execution and PowerShell/WMI activity monitored"
- ⚠️ **ISSUE:** Signal is NOT authenticated: `validation/07-correlation-engine.md:122-129` - Events are NOT cryptographically authenticated
- ⚠️ **ISSUE:** Signal alone is sufficient: `services/correlation-engine/app/rules.py:48` - Single signal creates incident

**Verdict:** **PARTIAL**

### 2. CROSS-DOMAIN CORRELATION

**Evidence:**
- ❌ **CRITICAL:** No Agent ↔ DPI linkage found:
  - `services/correlation-engine/app/rules.py:16-59` - Only rule checks `component == 'linux_agent'` (no DPI correlation)
  - No code found that links agent process execution events with DPI network activity
- ❌ **CRITICAL:** No host ↔ network correlation found:
  - `validation/07-correlation-engine.md:167-183` - No cross-domain correlation found
- ❌ **CRITICAL:** No identity binding found:
  - `services/correlation-engine/app/rules.py:44-48` - Only checks `component`, no machine_id/IP correlation

**Verdict:** **FAIL**

### 3. CONFIDENCE ACCUMULATION

**Evidence:**
- ❌ **CRITICAL:** No confidence accumulation found:
  - `services/correlation-engine/app/rules.py:54` - `confidence_score = 0.3` (constant, not accumulated)
- ❌ **CRITICAL:** Direct jump to SUSPICIOUS without accumulation:
  - `services/correlation-engine/app/rules.py:53` - `stage = 'SUSPICIOUS'` (constant, no accumulation required)

**Verdict:** **FAIL**

### 4. STATE MACHINE TRANSITIONS

**Evidence:**
- ❌ **CRITICAL:** No state transitions found:
  - `services/correlation-engine/app/rules.py:53` - `stage = 'SUSPICIOUS'` (constant, no transitions)
  - CLEAN state skipped, no transitions to PROBABLE or CONFIRMED

**Verdict:** **FAIL**

### 5. AI INVOLVEMENT

**Evidence:**
- ✅ AI operates only after correlation: `services/ai-core/README.md:11-12` - "Consumes Existing Incidents"
- ✅ AI does NOT change state: `services/ai-core/README.md:39` - "NO incident modification"
- ✅ AI produces explainability: `services/ai-core/README.md:24` - "SHAP Explanations"

**Verdict:** **PASS**

### 6. POLICY ELIGIBILITY

**Evidence:**
- ✅ Policy engine eligibility triggered only at SUSPICIOUS: `services/policy-engine/app/rules.py:18` - Checks `incident.current_stage == 'SUSPICIOUS'`
- ✅ No enforcement during validation: `services/policy-engine/README.md:38-48` - Simulation-first mode
- ✅ Correct command readiness signals: `services/policy-engine/app/main.py:286-300` - Generates signed command but does NOT execute
- ⚠️ **ISSUE:** Policy triggered by single sensor: `services/policy-engine/app/rules.py:18` - Evaluates incidents with `stage='SUSPICIOUS'` (which can be created by single signal)

**Verdict:** **PARTIAL**

### 7. FAILURE & PARTIAL-VISIBILITY HANDLING

**Evidence:**
- ⚠️ **ISSUE:** Full confidence with partial data:
  - `services/correlation-engine/app/rules.py:54` - `confidence_score = 0.3` (constant, not degraded when sensors missing)
- ⚠️ **ISSUE:** Silent blind spots:
  - No code found that detects missing sensors
- ⚠️ **ISSUE:** Assumed sensor truth:
  - Single signal creates incident (no verification from other sensors)

**Verdict:** **FAIL**

### 8. NEGATIVE VALIDATION

**Evidence:**
- ❌ **CRITICAL:** Agent alone CAN confirm attack:
  - `services/correlation-engine/app/rules.py:48` - `if component == 'linux_agent':` creates incident
- ❌ **CRITICAL:** DPI alone CANNOT confirm attack:
  - `services/correlation-engine/app/rules.py:48` - Rule only checks `component == 'linux_agent'` (DPI events would not match)
- ✅ AI alone CANNOT confirm attack: `services/ai-core/README.md:39` - "NO incident modification"
- ✅ UI CANNOT escalate incident: `validation/14-ui-api-access-control.md` - UI is read-only
- ✅ Policy CANNOT enforce without correlation: `services/policy-engine/README.md:60` - "NO incident modification"

**Verdict:** **PARTIAL**

### Scenario 7 Verdict: **FAIL**

**Justification:**
- Signal origin exists (agents can detect process execution)
- Signal is NOT authenticated
- Signal alone is sufficient
- **CRITICAL:** No cross-domain correlation (no Agent ↔ DPI linkage, no host ↔ network correlation)
- **CRITICAL:** No confidence accumulation
- **CRITICAL:** No state transitions
- AI involvement is correct
- Policy eligibility is partially correct
- **CRITICAL:** Full confidence with partial data
- **CRITICAL:** Agent alone CAN confirm attack

---

## SCENARIO 8: TOR / DARKNET C2

### 1. SIGNAL ORIGIN & GROUND TRUTH

**Evidence:**
- ✅ DPI can detect network connections: `schemas/03_normalized_dpi.sql:56-100` - `dpi_flows` table for network flow events
- ✅ C2 detection documented: `THREAT_PROTECTION_ANALYSIS.md:60` - "Network connections to C2 servers detectable via DPI probe"
- ⚠️ **ISSUE:** Signal is NOT authenticated: `validation/07-correlation-engine.md:122-129` - Events are NOT cryptographically authenticated
- ⚠️ **ISSUE:** Signal alone is NOT sufficient (but correlation engine doesn't check):
  - `services/correlation-engine/app/rules.py:48` - Rule only checks `component == 'linux_agent'` (DPI events would not match, so TOR C2 would NOT be detected)

**Verdict:** **FAIL**

### 2. CROSS-DOMAIN CORRELATION

**Evidence:**
- ❌ **CRITICAL:** No Agent ↔ DPI linkage found:
  - `services/correlation-engine/app/rules.py:16-59` - Only rule checks `component == 'linux_agent'` (no DPI correlation)
  - No code found that links agent process events with DPI TOR/C2 network events
- ❌ **CRITICAL:** No host ↔ network correlation found:
  - `validation/07-correlation-engine.md:167-183` - No cross-domain correlation found
- ❌ **CRITICAL:** No identity binding found:
  - `services/correlation-engine/app/rules.py:44-48` - Only checks `component`, no machine_id/IP correlation

**Verdict:** **FAIL**

### 3. CONFIDENCE ACCUMULATION

**Evidence:**
- ❌ **CRITICAL:** No confidence accumulation found:
  - `services/correlation-engine/app/rules.py:54` - `confidence_score = 0.3` (constant, not accumulated)
- ❌ **CRITICAL:** Direct jump to SUSPICIOUS without accumulation:
  - `services/correlation-engine/app/rules.py:53` - `stage = 'SUSPICIOUS'` (constant, no accumulation required)

**Verdict:** **FAIL**

### 4. STATE MACHINE TRANSITIONS

**Evidence:**
- ❌ **CRITICAL:** No state transitions found:
  - `services/correlation-engine/app/rules.py:53` - `stage = 'SUSPICIOUS'` (constant, no transitions)
  - CLEAN state skipped, no transitions to PROBABLE or CONFIRMED

**Verdict:** **FAIL**

### 5. AI INVOLVEMENT

**Evidence:**
- ✅ AI operates only after correlation: `services/ai-core/README.md:11-12` - "Consumes Existing Incidents"
- ✅ AI does NOT change state: `services/ai-core/README.md:39` - "NO incident modification"
- ✅ AI produces explainability: `services/ai-core/README.md:24` - "SHAP Explanations"

**Verdict:** **PASS**

### 6. POLICY ELIGIBILITY

**Evidence:**
- ✅ Policy engine eligibility triggered only at SUSPICIOUS: `services/policy-engine/app/rules.py:18` - Checks `incident.current_stage == 'SUSPICIOUS'`
- ✅ No enforcement during validation: `services/policy-engine/README.md:38-48` - Simulation-first mode
- ✅ Correct command readiness signals: `services/policy-engine/app/main.py:286-300` - Generates signed command but does NOT execute
- ⚠️ **ISSUE:** Policy triggered by single sensor: `services/policy-engine/app/rules.py:18` - Evaluates incidents with `stage='SUSPICIOUS'` (which can be created by single signal)

**Verdict:** **PARTIAL**

### 7. FAILURE & PARTIAL-VISIBILITY HANDLING

**Evidence:**
- ⚠️ **ISSUE:** Full confidence with partial data:
  - `services/correlation-engine/app/rules.py:54` - `confidence_score = 0.3` (constant, not degraded when sensors missing)
- ⚠️ **ISSUE:** Silent blind spots:
  - No code found that detects missing sensors
- ⚠️ **ISSUE:** Assumed sensor truth:
  - Single signal creates incident (no verification from other sensors)

**Verdict:** **FAIL**

### 8. NEGATIVE VALIDATION

**Evidence:**
- ❌ **CRITICAL:** Agent alone CAN confirm attack:
  - `services/correlation-engine/app/rules.py:48` - `if component == 'linux_agent':` creates incident
- ❌ **CRITICAL:** DPI alone CANNOT confirm attack:
  - `services/correlation-engine/app/rules.py:48` - Rule only checks `component == 'linux_agent'` (DPI events would not match)
- ✅ AI alone CANNOT confirm attack: `services/ai-core/README.md:39` - "NO incident modification"
- ✅ UI CANNOT escalate incident: `validation/14-ui-api-access-control.md` - UI is read-only
- ✅ Policy CANNOT enforce without correlation: `services/policy-engine/README.md:60` - "NO incident modification"

**Verdict:** **PARTIAL**

### Scenario 8 Verdict: **FAIL**

**Justification:**
- Signal origin exists (DPI can detect network connections to C2 servers)
- Signal is NOT authenticated
- **CRITICAL:** Signal alone is NOT sufficient AND correlation engine doesn't detect DPI events (rule only checks `component == 'linux_agent'`, so TOR C2 would NOT be detected)
- **CRITICAL:** No cross-domain correlation (no Agent ↔ DPI linkage, no host ↔ network correlation)
- **CRITICAL:** No confidence accumulation
- **CRITICAL:** No state transitions
- AI involvement is correct
- Policy eligibility is partially correct
- **CRITICAL:** Full confidence with partial data
- **CRITICAL:** Agent alone CAN confirm attack (but DPI alone CANNOT)

---

## SCENARIO 9: DPI SENSOR BLINDING / EVASION

### 1. SIGNAL ORIGIN & GROUND TRUTH

**Evidence:**
- ✅ Agent can detect process execution: `schemas/02_normalized_agent.sql:7-12` - `process_activity_type` enum includes PROCESS_START, PROCESS_EXIT
- ✅ Agent can detect file activity: `schemas/02_normalized_agent.sql:15-22` - `file_activity_type` enum includes FILE_CREATE, FILE_MODIFY, FILE_DELETE
- ⚠️ **ISSUE:** Signal is NOT authenticated: `validation/07-correlation-engine.md:122-129` - Events are NOT cryptographically authenticated
- ⚠️ **ISSUE:** Signal alone is sufficient: `services/correlation-engine/app/rules.py:48` - Single signal creates incident
- ⚠️ **ISSUE:** No DPI evasion detection found:
  - No code found that detects DPI sensor blinding or evasion attempts
  - No code found that detects missing DPI events when agent events exist

**Verdict:** **FAIL**

### 2. CROSS-DOMAIN CORRELATION

**Evidence:**
- ❌ **CRITICAL:** No Agent ↔ DPI linkage found:
  - `services/correlation-engine/app/rules.py:16-59` - Only rule checks `component == 'linux_agent'` (no DPI correlation)
  - No code found that detects contradiction when agent events exist but DPI events are missing
- ❌ **CRITICAL:** No host ↔ network correlation found:
  - `validation/07-correlation-engine.md:167-183` - No cross-domain correlation found
- ❌ **CRITICAL:** No identity binding found:
  - `services/correlation-engine/app/rules.py:44-48` - Only checks `component`, no machine_id/IP correlation

**Verdict:** **FAIL**

### 3. CONFIDENCE ACCUMULATION

**Evidence:**
- ❌ **CRITICAL:** No confidence accumulation found:
  - `services/correlation-engine/app/rules.py:54` - `confidence_score = 0.3` (constant, not accumulated)
- ❌ **CRITICAL:** Direct jump to SUSPICIOUS without accumulation:
  - `services/correlation-engine/app/rules.py:53` - `stage = 'SUSPICIOUS'` (constant, no accumulation required)
- ⚠️ **ISSUE:** Confidence NOT degraded when DPI missing:
  - `services/correlation-engine/app/rules.py:54` - `confidence_score = 0.3` (constant, not degraded when sensors missing)

**Verdict:** **FAIL**

### 4. STATE MACHINE TRANSITIONS

**Evidence:**
- ❌ **CRITICAL:** No state transitions found:
  - `services/correlation-engine/app/rules.py:53` - `stage = 'SUSPICIOUS'` (constant, no transitions)
  - CLEAN state skipped, no transitions to PROBABLE or CONFIRMED

**Verdict:** **FAIL**

### 5. AI INVOLVEMENT

**Evidence:**
- ✅ AI operates only after correlation: `services/ai-core/README.md:11-12` - "Consumes Existing Incidents"
- ✅ AI does NOT change state: `services/ai-core/README.md:39` - "NO incident modification"
- ✅ AI produces explainability: `services/ai-core/README.md:24` - "SHAP Explanations"

**Verdict:** **PASS**

### 6. POLICY ELIGIBILITY

**Evidence:**
- ✅ Policy engine eligibility triggered only at SUSPICIOUS: `services/policy-engine/app/rules.py:18` - Checks `incident.current_stage == 'SUSPICIOUS'`
- ✅ No enforcement during validation: `services/policy-engine/README.md:38-48` - Simulation-first mode
- ✅ Correct command readiness signals: `services/policy-engine/app/main.py:286-300` - Generates signed command but does NOT execute
- ⚠️ **ISSUE:** Policy triggered by single sensor: `services/policy-engine/app/rules.py:18` - Evaluates incidents with `stage='SUSPICIOUS'` (which can be created by single signal)

**Verdict:** **PARTIAL**

### 7. FAILURE & PARTIAL-VISIBILITY HANDLING

**Evidence:**
- ❌ **CRITICAL:** Full confidence with partial data:
  - `services/correlation-engine/app/rules.py:54` - `confidence_score = 0.3` (constant, not degraded when DPI missing)
- ❌ **CRITICAL:** Silent blind spots:
  - No code found that detects missing DPI sensor or degrades confidence
- ❌ **CRITICAL:** Assumed sensor truth:
  - Single signal creates incident (no verification from other sensors, no detection of missing sensors)

**Verdict:** **FAIL**

### 8. NEGATIVE VALIDATION

**Evidence:**
- ❌ **CRITICAL:** Agent alone CAN confirm attack:
  - `services/correlation-engine/app/rules.py:48` - `if component == 'linux_agent':` creates incident
- ❌ **CRITICAL:** DPI alone CANNOT confirm attack:
  - `services/correlation-engine/app/rules.py:48` - Rule only checks `component == 'linux_agent'` (DPI events would not match)
- ✅ AI alone CANNOT confirm attack: `services/ai-core/README.md:39` - "NO incident modification"
- ✅ UI CANNOT escalate incident: `validation/14-ui-api-access-control.md` - UI is read-only
- ✅ Policy CANNOT enforce without correlation: `services/policy-engine/README.md:60` - "NO incident modification"

**Verdict:** **PARTIAL**

### Scenario 9 Verdict: **FAIL**

**Justification:**
- Signal origin exists (agents can detect process/file activity)
- Signal is NOT authenticated
- Signal alone is sufficient
- **CRITICAL:** No DPI evasion detection found (no code that detects missing DPI events when agent events exist)
- **CRITICAL:** No cross-domain correlation (no Agent ↔ DPI linkage, no host ↔ network correlation)
- **CRITICAL:** No confidence accumulation
- **CRITICAL:** No state transitions
- **CRITICAL:** Confidence NOT degraded when DPI missing (constant 0.3, not degraded)
- **CRITICAL:** Silent blind spots (no detection of missing sensors)
- AI involvement is correct
- Policy eligibility is partially correct
- **CRITICAL:** Agent alone CAN confirm attack

---

## FINAL SECTION — SYSTEM-LEVEL ASSESSMENT

### Summary Table of All Scenarios

| Scenario | Signal Origin | Cross-Domain Correlation | Confidence Accumulation | State Transitions | AI Involvement | Policy Eligibility | Partial-Visibility Handling | Overall Verdict |
|----------|---------------|--------------------------|-------------------------|-------------------|----------------|-------------------|----------------------------|----------------|
| 1. Ransomware (Fileless + Encryptor) | PARTIAL | FAIL | FAIL | FAIL | PASS | PARTIAL | FAIL | **FAIL** |
| 2. Worm / Lateral Propagation | PARTIAL | FAIL | FAIL | FAIL | PASS | PARTIAL | FAIL | **FAIL** |
| 3. Trojan / Backdoor Persistence | PARTIAL | FAIL | FAIL | FAIL | PASS | PARTIAL | FAIL | **FAIL** |
| 4. Credential Harvesting / Password Spray | PARTIAL | FAIL | FAIL | FAIL | PASS | PARTIAL | FAIL | **FAIL** |
| 5. DNS Tunneling | FAIL | FAIL | FAIL | FAIL | PASS | PARTIAL | FAIL | **FAIL** |
| 6. Low-and-Slow Data Exfiltration | FAIL | FAIL | FAIL | FAIL | PASS | PARTIAL | FAIL | **FAIL** |
| 7. Living-off-the-Land (LOLBins) | PARTIAL | FAIL | FAIL | FAIL | PASS | PARTIAL | FAIL | **FAIL** |
| 8. TOR / Darknet C2 | FAIL | FAIL | FAIL | FAIL | PASS | PARTIAL | FAIL | **FAIL** |
| 9. DPI Sensor Blinding / Evasion | FAIL | FAIL | FAIL | FAIL | PASS | PARTIAL | FAIL | **FAIL** |

### Weakest Link(s) Discovered

**CRITICAL WEAKNESSES:**

1. **No Cross-Domain Correlation (ALL SCENARIOS):**
   - **Evidence:** `services/correlation-engine/app/rules.py:16-59` - Only rule checks `component == 'linux_agent'` (no DPI correlation)
   - **Impact:** Agent events and DPI events are never linked. Single-sensor confirmation is possible.
   - **Component:** Correlation Engine (`services/correlation-engine/app/rules.py`)

2. **No Confidence Accumulation (ALL SCENARIOS):**
   - **Evidence:** `services/correlation-engine/app/rules.py:54` - `confidence_score = 0.3` (constant, not accumulated)
   - **Impact:** Confidence does not increase with multiple signals. No incremental weights.
   - **Component:** Correlation Engine (`services/correlation-engine/app/rules.py`)

3. **No State Machine Transitions (ALL SCENARIOS):**
   - **Evidence:** `services/correlation-engine/app/rules.py:53` - `stage = 'SUSPICIOUS'` (constant, no transitions)
   - **Impact:** Incidents created with `stage='SUSPICIOUS'` and never transition to PROBABLE or CONFIRMED. CLEAN state is skipped.
   - **Component:** Correlation Engine (`services/correlation-engine/app/rules.py`)

4. **No Scenario-Specific Detection Rules (ALL SCENARIOS):**
   - **Evidence:** `services/correlation-engine/app/rules.py:16-59` - Only ONE rule exists: `apply_linux_agent_rule()` (checks `component == 'linux_agent'`)
   - **Impact:** No scenario-specific detection. All scenarios treated identically (if component == 'linux_agent', create incident).
   - **Component:** Correlation Engine (`services/correlation-engine/app/rules.py`)

5. **DPI Events Not Detected (SCENARIOS 5, 6, 8):**
   - **Evidence:** `services/correlation-engine/app/rules.py:48` - Rule only checks `component == 'linux_agent'` (DPI events with `component == 'dpi'` would not match)
   - **Impact:** DNS tunneling, data exfiltration, and TOR C2 scenarios would NOT be detected if only DPI events exist (no agent events).
   - **Component:** Correlation Engine (`services/correlation-engine/app/rules.py`)

6. **No Partial-Visibility Handling (ALL SCENARIOS):**
   - **Evidence:** `services/correlation-engine/app/rules.py:54` - `confidence_score = 0.3` (constant, not degraded when sensors missing)
   - **Impact:** Full confidence with partial data. Silent blind spots. Assumed sensor truth.
   - **Component:** Correlation Engine (`services/correlation-engine/app/rules.py`)

7. **No Contradiction Detection (ALL SCENARIOS):**
   - **Evidence:** `validation/07-correlation-engine.md:167-183` - No contradiction detection found
   - **Impact:** Host vs network contradictions are not detected. Single-signal escalation is possible.
   - **Component:** Correlation Engine (`services/correlation-engine/app/rules.py`)

### Whether RansomEye Actually Fulfills "Correlation > Isolation"

**Verdict: ❌ FAIL**

**Justification:**
- **CRITICAL:** Correlation engine does NOT fulfill "Correlation > Isolation":
  - `services/correlation-engine/app/rules.py:48` - Single agent signal creates incident (no correlation required)
  - `validation/07-correlation-engine.md:167-183` - No cross-domain correlation found
  - `validation/07-correlation-engine.md:162-165` - Single-signal escalation is possible (no contradiction required)
- **CRITICAL:** Isolation is NOT enforced:
  - Single sensor can confirm attack (agent alone can create incident)
  - No cross-domain correlation required
  - No contradiction detection required
- **CRITICAL:** "Correlation > Isolation" principle is violated:
  - Correlation engine creates incidents from single signals (isolation, not correlation)
  - No multi-sensor correlation exists
  - No cross-domain verification exists

### Whether Production Readiness Claims Are Valid

**Verdict: ❌ FAIL**

**Justification:**
- **CRITICAL:** Production readiness claims are NOT valid:
  - No end-to-end threat scenario detection exists (only generic rule: if component == 'linux_agent', create incident)
  - No cross-domain correlation exists (agent events and DPI events are never linked)
  - No confidence accumulation exists (confidence is constant, not accumulated)
  - No state machine transitions exist (incidents created with SUSPICIOUS and never transition)
  - No scenario-specific detection rules exist (all scenarios treated identically)
  - DPI events are NOT detected (rule only checks `component == 'linux_agent'`)
  - No partial-visibility handling exists (full confidence with partial data, silent blind spots)
  - No contradiction detection exists (single-signal escalation is possible)
- **CRITICAL:** "Correlation > Isolation" principle is violated:
  - Single sensor can confirm attack (agent alone can create incident)
  - No multi-sensor correlation required
  - No cross-domain verification required
- **CRITICAL:** End-to-end flows are broken:
  - Threat scenarios cannot be correctly detected end-to-end
  - State machine transitions do not occur
  - Confidence does not accumulate
  - Cross-domain correlation does not exist

**Recommendations:**
1. **CRITICAL:** Implement cross-domain correlation (Agent ↔ DPI linkage, host ↔ network correlation, identity binding)
2. **CRITICAL:** Implement confidence accumulation (weight definitions, accumulation logic, saturation behavior, thresholds)
3. **CRITICAL:** Implement state machine transitions (CLEAN → SUSPICIOUS → PROBABLE → CONFIRMED with transition guards)
4. **CRITICAL:** Implement scenario-specific detection rules (ransomware, worm, trojan, credential harvesting, DNS tunneling, exfiltration, LOLBins, TOR C2, DPI evasion)
5. **CRITICAL:** Implement contradiction detection (host vs network contradiction, execution vs timing contradiction, persistence vs silence contradiction)
6. **CRITICAL:** Implement partial-visibility handling (confidence degradation when sensors missing, explicit uncertainty signaling, no assumed sensor truth)
7. **CRITICAL:** Enforce "Correlation > Isolation" principle (require multi-sensor correlation, no single-sensor confirmation, cross-domain verification required)
8. **HIGH:** Add DPI event detection rules (correlation engine must detect DPI events, not just agent events)
9. **HIGH:** Add scenario-specific correlation patterns (link agent file encryption with DPI network events, link agent process execution with DPI network connections, etc.)
10. **MEDIUM:** Add temporal correlation (time-window logic for linking events across time)
11. **MEDIUM:** Add identity binding (machine_id/IP correlation between agent and DPI events)

---

**Validation Date:** 2025-01-13
**Validator:** Lead Validator & Compliance Auditor
**Next Step:** Validation complete (all 16 steps completed)
