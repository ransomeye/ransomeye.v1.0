# Validation Step 29 — UBA Drift (In-Depth)

**Component Identity:**
- **Name:** UBA Drift (Behavioral Drift Detection Engine)
- **Primary Paths:**
  - `/home/ransomeye/rebuild/uba-drift/api/drift_api.py` - Main drift API
  - `/home/ransomeye/rebuild/uba-drift/engine/delta_comparator.py` - Deterministic delta comparison
  - `/home/ransomeye/rebuild/uba-drift/engine/delta_classifier.py` - Delta type classification
  - `/home/ransomeye/rebuild/uba-drift/engine/delta_hasher.py` - Deterministic delta hashing
  - `/home/ransomeye/rebuild/uba-drift/engine/window_builder.py` - Explicit observation window building
  - `/home/ransomeye/rebuild/uba-drift/storage/delta_store.py` - Append-only, immutable storage
- **Entry Point:** `uba-drift/api/drift_api.py:146` - `DriftAPI.compute_behavior_deltas()`

**Master Spec References:**
- Phase B2 — UBA Drift (Master Spec)
- Validation File 27 (UBA Core) — **TREATED AS PASSED AND LOCKED**
- Validation File 22 (Audit Ledger) — **TREATED AS PASSED AND LOCKED**
- Master Spec: Behavioral drift ≠ malicious behavior
- Master Spec: Deterministic delta analysis requirements
- Master Spec: UBA Core read-only requirements

---

## PURPOSE

This validation proves that UBA Drift detects behavioral change deterministically without ML, scoring, alerts, or inference. This validation proves UBA Drift is deterministic, replayable, and regulator-safe.

This validation does NOT assume UBA Core determinism or provide fixes/recommendations. Validation File 27 (UBA Core) is treated as PASSED and LOCKED. Validation File 22 (Audit Ledger) is treated as PASSED and LOCKED. This validation must account for non-deterministic upstream inputs affecting delta computation.

This file validates:
- Behavioral drift ≠ malicious behavior (change detection only, no judgment)
- Deterministic delta analysis (explicit comparison, no heuristics, environment-defined thresholds)
- UBA Core read-only access (no mutations, separate storage)
- Immutable storage (deltas cannot be modified after creation)
- Deterministic delta hashing (bit-for-bit identical rebuilds)
- Audit ledger integration (all operations emit ledger entries)

This validation does NOT validate UI, reporting, installer, or provide fixes/recommendations.

---

## UBA DRIFT DEFINITION

**UBA Drift Requirements (Master Spec):**

1. **Behavioral Drift ≠ Malicious Behavior** — Detects behavioral change, not intent. No ML, no scoring, no judgment
2. **Deterministic Delta Analysis** — Explicit comparison logic, no heuristics, environment-defined thresholds
3. **UBA Core Read-Only Access** — UBA Core stores are read-only, no mutations, separate storage
4. **Immutable Storage** — Deltas cannot be modified after creation
5. **Deterministic Delta Hashing** — Bit-for-bit identical rebuilds, same events → same deltas
6. **Audit Ledger Integration** — All operations emit audit ledger entries

**UBA Drift Structure:**
- **Entry Point:** `DriftAPI.compute_behavior_deltas()` - Compute behavior deltas
- **Processing:** Baseline retrieval → Observation window building → Delta comparison → Delta classification → Storage
- **Storage:** Immutable delta records (append-only)
- **Output:** Delta records (immutable, deterministic, facts-only)

---

## WHAT IS VALIDATED

### 1. Behavioral Drift ≠ Malicious Behavior
- Change detection only (no intent inference)
- No ML (no machine learning models)
- No scoring (no risk scores, alerts, confidence labels)
- No judgment (no words like suspicious, malicious, abnormal)
- Facts only (deltas are facts, not conclusions)

### 2. Deterministic Delta Analysis
- Explicit comparison logic (no heuristics)
- Environment-defined thresholds (no hardcoded thresholds)
- Bit-for-bit reconstructable (every delta is reconstructable)
- Replayable (Global Validator can rebuild all deltas)

### 3. UBA Core Read-Only Access
- UBA Core stores are read-only (no mutations)
- No updates to baselines or events
- Separate storage (deltas stored separately)

### 4. Immutable Storage
- Deltas cannot be modified after creation
- Deltas are append-only
- No update or delete operations exist

### 5. Deterministic Delta Hashing
- Delta hashing is deterministic
- Same events → same deltas → same hashes
- Bit-for-bit identical rebuilds

### 6. Audit Ledger Integration
- All operations emit audit ledger entries
- Delta computation logged
- Delta export logged
- No silent operations

---

## WHAT IS EXPLICITLY NOT ASSUMED

- **NOT ASSUMED:** That UBA Core produces deterministic baselines (baselines may differ on replay)
- **NOT ASSUMED:** That deltas are deterministic if inputs are non-deterministic (deltas may differ on replay if inputs differ)

---

## VALIDATION METHODOLOGY

### Evidence Collection Strategy

1. **Code Path Analysis:** Trace delta computation, baseline comparison, delta classification, storage, ledger integration
2. **File System Analysis:** Verify immutable storage, append-only semantics, UBA Core read-only access
3. **Determinism Analysis:** Check for randomness, ML imports, scoring logic, inference logic, judgment words
4. **Configuration Analysis:** Check for hardcoded thresholds (thresholds must be from environment)
5. **Ledger Integration Analysis:** Verify audit ledger integration, ledger entry emission

### Forbidden Patterns (Grep Validation)

- `random|randint|choice` — Random number generation (forbidden)
- `ml|machine.*learning|sklearn|tensorflow|pytorch` — ML imports (forbidden)
- `score|scoring|risk.*score|threat.*score` — Scoring logic (forbidden)
- `suspicious|malicious|abnormal|anomaly` — Judgment words (forbidden)
- `infer|inference|predict|prediction|intent` — Inference logic (forbidden)
- `hardcoded.*threshold|threshold.*=.*[0-9]` — Hardcoded thresholds (forbidden, unless from env)

---

## 1. BEHAVIORAL DRIFT ≠ MALICIOUS BEHAVIOR

### Evidence

**Change Detection Only (No Intent Inference):**
- ✅ Change detection: `uba-drift/engine/delta_comparator.py:45-150` - Delta comparator detects behavioral change, not intent
- ✅ No intent logic: No intent or motivation inference logic found
- ✅ **VERIFIED:** Change detection only (no intent inference)

**No ML:**
- ✅ No ML imports: `uba-drift/api/drift_api.py:1-30` - No ML imports (sklearn, tensorflow, pytorch)
- ✅ No ML calls: No ML model calls found
- ✅ **VERIFIED:** No ML exists

**No Scoring:**
- ✅ No scoring logic: No scoring, risk scoring, or threat scoring logic found
- ✅ **VERIFIED:** No scoring exists

**No Judgment:**
- ✅ No judgment words: No words like suspicious, malicious, abnormal found in delta classification
- ✅ Facts only: `uba-drift/engine/delta_classifier.py:36-80` - Delta classifier classifies delta types (NEW_EVENT_TYPE, NEW_HOST, etc.), not judgments
- ✅ **VERIFIED:** No judgment exists

**Facts Only (Deltas Are Facts, Not Conclusions):**
- ✅ Facts only: Deltas are facts (delta types, delta magnitudes), not conclusions
- ✅ **VERIFIED:** Facts only (deltas are facts, not conclusions)

**ML, Scoring, Judgment, or Inference Exist:**
- ✅ **VERIFIED:** No ML, scoring, judgment, or inference exist (change detection only, facts only)

### Verdict: **PASS**

**Justification:**
- Change detection only (change detection, no intent logic)
- No ML exists (no ML imports, no ML calls)
- No scoring exists (no scoring logic)
- No judgment exists (no judgment words, facts only)
- Facts only (deltas are facts, not conclusions)

**PASS Conditions (Met):**
- Change detection only (no intent inference) — **CONFIRMED**
- No ML exists — **CONFIRMED**
- No scoring exists — **CONFIRMED**
- No judgment exists — **CONFIRMED**
- Facts only (deltas are facts, not conclusions) — **CONFIRMED**

**Evidence Required:**
- File paths: `uba-drift/engine/delta_comparator.py:45-150`, `uba-drift/api/drift_api.py:1-30`, `uba-drift/engine/delta_classifier.py:36-80`
- Behavioral drift ≠ malicious behavior: Change detection only, no ML, no scoring, no judgment, facts only

---

## 2. DETERMINISTIC DELTA ANALYSIS

### Evidence

**Explicit Comparison Logic (No Heuristics):**
- ✅ Explicit comparison: `uba-drift/engine/delta_comparator.py:45-150` - Delta comparison uses explicit comparison logic
- ✅ No heuristics: No heuristic logic found
- ✅ **VERIFIED:** Explicit comparison logic is used

**Environment-Defined Thresholds:**
- ✅ Environment thresholds: `uba-drift/engine/delta_comparator.py:80-120` - Thresholds are from environment variables (UBA_DRIFT_FREQUENCY_THRESHOLD)
- ✅ No hardcoded thresholds: No hardcoded threshold values found
- ✅ **VERIFIED:** Environment-defined thresholds are used

**Bit-for-Bit Reconstructable:**
- ✅ Reconstructable: `uba-drift/engine/delta_comparator.py:45-150` - Deltas are reconstructable from baselines and events
- ✅ **VERIFIED:** Deltas are bit-for-bit reconstructable

**Replayable:**
- ✅ Replayable: `uba-drift/api/drift_api.py:146-200` - Delta computation is replayable (Global Validator can rebuild all deltas)
- ✅ **VERIFIED:** Deltas are replayable

**Delta Analysis Is Non-Deterministic or Uses Heuristics:**
- ✅ **VERIFIED:** Delta analysis is deterministic (explicit comparison, environment-defined thresholds, reconstructable, replayable)

### Verdict: **PASS**

**Justification:**
- Explicit comparison logic is used (explicit comparison, no heuristics)
- Environment-defined thresholds are used (environment thresholds, no hardcoded thresholds)
- Deltas are bit-for-bit reconstructable (reconstructable)
- Deltas are replayable (replayable)

**PASS Conditions (Met):**
- Explicit comparison logic (no heuristics) is used — **CONFIRMED**
- Environment-defined thresholds are used — **CONFIRMED**
- Deltas are bit-for-bit reconstructable — **CONFIRMED**
- Deltas are replayable — **CONFIRMED**

**Evidence Required:**
- File paths: `uba-drift/engine/delta_comparator.py:45-150,80-120`, `uba-drift/api/drift_api.py:146-200`
- Deterministic delta analysis: Explicit comparison, environment-defined thresholds, reconstructable, replayable

---

## 3. UBA CORE READ-ONLY ACCESS

### Evidence

**UBA Core Stores Are Read-Only:**
- ✅ Read-only access: `uba-drift/api/drift_api.py:90-145` - UBA Core stores are accessed read-only
- ✅ No mutations: No mutation operations found for UBA Core stores
- ✅ **VERIFIED:** UBA Core stores are read-only

**No Updates to Baselines or Events:**
- ✅ No updates: No update operations found for baselines or events
- ✅ **VERIFIED:** No updates to baselines or events

**Separate Storage:**
- ✅ Separate storage: `uba-drift/storage/delta_store.py:18-100` - Deltas are stored separately from UBA Core
- ✅ **VERIFIED:** Separate storage is used

**UBA Core Stores Are Mutated:**
- ✅ **VERIFIED:** UBA Core stores are not mutated (read-only access, no mutations, separate storage)

### Verdict: **PASS**

**Justification:**
- UBA Core stores are read-only (read-only access, no mutations)
- No updates to baselines or events (no updates)
- Separate storage is used (separate storage)

**PASS Conditions (Met):**
- UBA Core stores are read-only — **CONFIRMED**
- No updates to baselines or events — **CONFIRMED**
- Separate storage is used — **CONFIRMED**

**Evidence Required:**
- File paths: `uba-drift/api/drift_api.py:90-145`, `uba-drift/storage/delta_store.py:18-100`
- UBA Core read-only access: Read-only access, no mutations, separate storage

---

## 4. IMMUTABLE STORAGE

### Evidence

**Deltas Cannot Be Modified After Creation:**
- ✅ Immutable deltas: `uba-drift/storage/delta_store.py:18-100` - Delta store is append-only
- ✅ No update operations: No `update()` or `modify()` methods found in storage layer
- ✅ **VERIFIED:** Deltas cannot be modified after creation

**Deltas Are Append-Only:**
- ✅ Append-only semantics: `uba-drift/storage/delta_store.py:40-80` - Deltas are appended, never modified
- ✅ **VERIFIED:** Deltas are append-only

**No Update or Delete Operations Exist:**
- ✅ No delete operations: No `delete()` or `remove()` methods found in storage layer
- ✅ **VERIFIED:** No update or delete operations exist

**Deltas Can Be Modified or Deleted:**
- ✅ **VERIFIED:** Deltas cannot be modified or deleted (immutable deltas, append-only semantics, no update/delete operations)

### Verdict: **PASS**

**Justification:**
- Deltas cannot be modified after creation (immutable deltas, no update operations)
- Deltas are append-only (append-only semantics)
- No update or delete operations exist (no delete operations)

**PASS Conditions (Met):**
- Deltas cannot be modified after creation — **CONFIRMED**
- Deltas are append-only — **CONFIRMED**
- No update or delete operations exist — **CONFIRMED**

**Evidence Required:**
- File paths: `uba-drift/storage/delta_store.py:18-100,40-80`
- Immutable storage: Append-only store, no update/delete operations

---

## 5. DETERMINISTIC DELTA HASHING

### Evidence

**Delta Hashing Is Deterministic:**
- ✅ Deterministic hashing: `uba-drift/engine/delta_hasher.py:20-80` - Delta hashing is deterministic
- ✅ Hash determinism: Same delta inputs always produce same hash
- ✅ **VERIFIED:** Delta hashing is deterministic

**Same Events → Same Deltas → Same Hashes:**
- ✅ Deterministic deltas: `uba-drift/engine/delta_comparator.py:45-150` - Delta computation is deterministic
- ✅ Deterministic hashes: Delta hashing is deterministic
- ✅ **VERIFIED:** Same events → same deltas → same hashes

**Bit-for-Bit Identical Rebuilds:**
- ✅ Rebuild capability: `uba-drift/api/drift_api.py:146-200` - Deltas can be rebuilt from baselines and events
- ✅ Identical rebuilds: Same inputs always produce same deltas (bit-for-bit identical)
- ✅ **VERIFIED:** Bit-for-bit identical rebuilds are possible

**Delta Hashing Is Non-Deterministic:**
- ✅ **VERIFIED:** Delta hashing is deterministic (deterministic hashing, hash determinism, bit-for-bit identical rebuilds)

### Verdict: **PASS**

**Justification:**
- Delta hashing is deterministic (deterministic hashing, hash determinism)
- Same events → same deltas → same hashes (deterministic deltas, deterministic hashes)
- Bit-for-bit identical rebuilds are possible (rebuild capability, identical rebuilds)

**PASS Conditions (Met):**
- Delta hashing is deterministic — **CONFIRMED**
- Same events → same deltas → same hashes — **CONFIRMED**
- Bit-for-bit identical rebuilds are possible — **CONFIRMED**

**Evidence Required:**
- File paths: `uba-drift/engine/delta_hasher.py:20-80`, `uba-drift/engine/delta_comparator.py:45-150`, `uba-drift/api/drift_api.py:146-200`
- Deterministic delta hashing: Deterministic hashing, hash determinism, bit-for-bit identical rebuilds

---

## 6. AUDIT LEDGER INTEGRATION

### Evidence

**All Operations Emit Audit Ledger Entries:**
- ✅ Delta computation: `uba-drift/api/drift_api.py:200-240` - Delta computation emits audit ledger entry (`UBA_DELTA_COMPUTED`)
- ✅ Delta export: `uba-drift/api/drift_api.py:280-320` - Delta export emits audit ledger entry (`UBA_DELTA_EXPORTED`)
- ✅ **VERIFIED:** All operations emit audit ledger entries

**No Silent Operations:**
- ✅ No silent operations: All operations emit ledger entries
- ✅ **VERIFIED:** No silent operations exist

**Complete Audit Trail:**
- ✅ Complete trail: All UBA Drift operations are logged to audit ledger
- ✅ **VERIFIED:** Complete audit trail exists

**Operations Do Not Emit Audit Ledger Entries:**
- ✅ **VERIFIED:** All operations emit audit ledger entries (delta computation, delta export)

### Verdict: **PASS**

**Justification:**
- All operations emit audit ledger entries (delta computation, delta export)
- No silent operations exist (all operations emit ledger entries)
- Complete audit trail exists (complete trail)

**PASS Conditions (Met):**
- All operations emit audit ledger entries — **CONFIRMED**
- No silent operations — **CONFIRMED**
- Complete audit trail — **CONFIRMED**

**Evidence Required:**
- File paths: `uba-drift/api/drift_api.py:200-240,280-320`
- Audit ledger integration: Delta computation logging, delta export logging

---

## CREDENTIAL TYPES VALIDATED

### Audit Ledger Keys (for UBA Drift operations)
- **Type:** ed25519 key pair for audit ledger entry signing
- **Source:** Audit Ledger key manager (shared with Audit Ledger subsystem)
- **Validation:** ✅ **VALIDATED** (keys are properly managed by Audit Ledger subsystem per File 22)
- **Usage:** UBA Drift operation audit ledger entry signing
- **Status:** ✅ **VALIDATED** (key management is correct per File 22)

---

## PASS CONDITIONS

### Section 1: Behavioral Drift ≠ Malicious Behavior
- ✅ Change detection only (no intent inference) — **PASS**
- ✅ No ML exists — **PASS**
- ✅ No scoring exists — **PASS**
- ✅ No judgment exists — **PASS**
- ✅ Facts only (deltas are facts, not conclusions) — **PASS**

### Section 2: Deterministic Delta Analysis
- ✅ Explicit comparison logic (no heuristics) is used — **PASS**
- ✅ Environment-defined thresholds are used — **PASS**
- ✅ Deltas are bit-for-bit reconstructable — **PASS**
- ✅ Deltas are replayable — **PASS**

### Section 3: UBA Core Read-Only Access
- ✅ UBA Core stores are read-only — **PASS**
- ✅ No updates to baselines or events — **PASS**
- ✅ Separate storage is used — **PASS**

### Section 4: Immutable Storage
- ✅ Deltas cannot be modified after creation — **PASS**
- ✅ Deltas are append-only — **PASS**
- ✅ No update or delete operations exist — **PASS**

### Section 5: Deterministic Delta Hashing
- ✅ Delta hashing is deterministic — **PASS**
- ✅ Same events → same deltas → same hashes — **PASS**
- ✅ Bit-for-bit identical rebuilds are possible — **PASS**

### Section 6: Audit Ledger Integration
- ✅ All operations emit audit ledger entries — **PASS**
- ✅ No silent operations — **PASS**
- ✅ Complete audit trail — **PASS**

---

## FAIL CONDITIONS

### Section 1: Behavioral Drift ≠ Malicious Behavior
- ❌ ML, scoring, judgment, or inference exist — **NOT CONFIRMED** (change detection only, facts only)

### Section 2: Deterministic Delta Analysis
- ❌ Delta analysis is non-deterministic or uses heuristics — **NOT CONFIRMED** (delta analysis is deterministic)

### Section 3: UBA Core Read-Only Access
- ❌ UBA Core stores are mutated — **NOT CONFIRMED** (UBA Core stores are read-only)

### Section 4: Immutable Storage
- ❌ Deltas can be modified or deleted — **NOT CONFIRMED** (deltas are immutable)

### Section 5: Deterministic Delta Hashing
- ❌ Delta hashing is non-deterministic — **NOT CONFIRMED** (delta hashing is deterministic)

### Section 6: Audit Ledger Integration
- ❌ Operations do not emit audit ledger entries — **NOT CONFIRMED** (all operations emit audit ledger entries)

---

## EVIDENCE REQUIRED

### Behavioral Drift ≠ Malicious Behavior
- File paths: `uba-drift/engine/delta_comparator.py:45-150`, `uba-drift/api/drift_api.py:1-30`, `uba-drift/engine/delta_classifier.py:36-80`
- Behavioral drift ≠ malicious behavior: Change detection only, no ML, no scoring, no judgment, facts only

### Deterministic Delta Analysis
- File paths: `uba-drift/engine/delta_comparator.py:45-150,80-120`, `uba-drift/api/drift_api.py:146-200`
- Deterministic delta analysis: Explicit comparison, environment-defined thresholds, reconstructable, replayable

### UBA Core Read-Only Access
- File paths: `uba-drift/api/drift_api.py:90-145`, `uba-drift/storage/delta_store.py:18-100`
- UBA Core read-only access: Read-only access, no mutations, separate storage

### Immutable Storage
- File paths: `uba-drift/storage/delta_store.py:18-100,40-80`
- Immutable storage: Append-only store, no update/delete operations

### Deterministic Delta Hashing
- File paths: `uba-drift/engine/delta_hasher.py:20-80`, `uba-drift/engine/delta_comparator.py:45-150`, `uba-drift/api/drift_api.py:146-200`
- Deterministic delta hashing: Deterministic hashing, hash determinism, bit-for-bit identical rebuilds

### Audit Ledger Integration
- File paths: `uba-drift/api/drift_api.py:200-240,280-320`
- Audit ledger integration: Delta computation logging, delta export logging

---

## GA VERDICT

### Overall: **PASS**

**Critical Blockers:**
None. All validation criteria are met.

**Non-Blocking Issues:**
None.

**Strengths:**

1. ✅ Behavioral drift ≠ malicious behavior (change detection only, no ML, no scoring, no judgment, facts only)
2. ✅ Delta analysis is deterministic (explicit comparison, environment-defined thresholds, reconstructable, replayable)
3. ✅ UBA Core is read-only (read-only access, no mutations, separate storage)
4. ✅ Deltas are immutable (append-only storage, no update/delete operations)
5. ✅ Delta hashing is deterministic (deterministic hashing, bit-for-bit identical rebuilds)
6. ✅ All operations emit audit ledger entries (complete audit trail)

**Summary of Critical Blockers:**
None. UBA Drift validation **PASSES** all criteria.

**Note on Upstream Non-Determinism:**
While UBA Drift delta computation itself is deterministic, if upstream components (UBA Core) produce non-deterministic baselines, deltas may differ on replay. This is a limitation of upstream components, not UBA Drift itself. UBA Drift correctly computes deterministic deltas from whatever inputs it receives.

---

**Validation Date:** 2025-01-13  
**Validator:** Independent System Validator  
**Next Step:** Validation Step 30 — UBA Alert Context  
**GA Status:** **PASS** (All validation criteria met)

---

## UPSTREAM IMPACT STATEMENT

**Documentation Only:** This section documents upstream impact of UBA Drift validation on downstream validations.

**Upstream Validations Impacted by UBA Drift:**
None. UBA Drift is a delta-analysis layer with no upstream dependencies that affect its validation.

**Requirements for Upstream Validations:**
- Upstream validations must NOT assume UBA Drift receives deterministic baselines (UBA Core may produce non-deterministic baselines per File 27)
- Upstream validations must validate their components based on actual behavior, not assumptions about UBA Drift determinism

---

## DOWNSTREAM IMPACT STATEMENT

**Documentation Only:** This section documents downstream impact of UBA Drift validation on downstream validations.

**Downstream Validations Impacted by UBA Drift:**
All downstream validations that consume UBA deltas can assume:
- Deltas are facts (not conclusions, not judgments)
- Delta computation is deterministic (same inputs → same outputs)
- Deltas are immutable (cannot be modified after creation)

**Requirements for Downstream Validations:**
- Downstream validations must NOT assume deltas are deterministic if upstream inputs are non-deterministic (deltas may differ on replay if inputs differ)
- Downstream validations must validate their components based on actual behavior, not assumptions about UBA Drift determinism
