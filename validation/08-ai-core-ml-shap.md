# Validation Step 8 — AI Core / ML / SHAP (In-Depth)

**Component Identity:**
- **Name:** AI Core (Low-Compute ML Layer)
- **Primary Paths:**
  - `/home/ransomeye/rebuild/services/ai-core/app/main.py` - Main AI Core batch processing
  - `/home/ransomeye/rebuild/services/ai-core/app/feature_extraction.py` - Feature extraction
  - `/home/ransomeye/rebuild/services/ai-core/app/clustering.py` - KMeans clustering
  - `/home/ransomeye/rebuild/services/ai-core/app/shap_explainer.py` - SHAP explainability
  - `/home/ransomeye/rebuild/services/ai-core/app/db.py` - Database operations
  - `/home/ransomeye/rebuild/ai-model-registry/` - Model registry (if applicable)
- **Entry Point:** Batch processing loop - `services/ai-core/app/main.py:95` - `run_ai_core()`

**Master Spec References:**
- Phase 6 — Read-Only, Non-Blocking AI Core
- AI Metadata Schema (`schemas/05_ai_metadata.sql`)
- Validation File 06 (Ingest Pipeline) — **TREATED AS FAILED AND LOCKED**
- Validation File 07 (Correlation Engine) — **TREATED AS FAILED AND LOCKED**

---

## PURPOSE

This validation proves that AI/ML components are explainable, reproducible, auditable, and not black-box.

This validation does NOT assume ingest determinism or correlation determinism. Validation Files 06 and 07 are treated as FAILED and LOCKED. This validation must account for non-deterministic inputs affecting AI/ML behavior.

This file validates:
- Model registry & provenance
- Training & retraining discipline
- Inference determinism (non-LLM)
- SHAP explainability
- Replay & auditability
- No black-box paths

This validation does NOT validate UI, agents, installer, or provide fixes/recommendations.

---

## AI CORE DEFINITION

**AI Core Requirements (Master Spec):**

1. **Model Registry & Provenance** — Model versioning, model lineage, training data traceability
2. **Training & Retraining Discipline** — Presence of training pipeline, deterministic training inputs, ability to retrain models
3. **Inference Determinism (Non-LLM)** — Identical inputs → identical outputs, no hidden randomness
4. **SHAP Explainability** — SHAP artifacts generated, SHAP references persisted, SHAP explanations tied to model version
5. **Replay & Auditability** — AI outputs can be recomputed later, non-deterministic inputs do not break audit trails
6. **No Black-Box Paths** — No inference path bypasses explanation, no opaque scores

**AI Core Structure:**
- **Entry Point:** Batch processing loop (`run_ai_core()`)
- **Processing Chain:** Read incidents → Extract features → Cluster → Generate SHAP → Store metadata
- **Storage Tables:** `feature_vectors`, `clusters`, `cluster_memberships`, `shap_explanations`, `ai_model_versions`

---

## WHAT IS VALIDATED

### 1. Model Registry & Provenance
- Model versioning
- Model lineage
- Training data traceability

### 2. Training & Retraining Discipline
- Presence of training pipeline
- Deterministic training inputs
- Ability to retrain models

### 3. Inference Determinism (Non-LLM)
- Identical inputs → identical outputs
- No hidden randomness

### 4. SHAP Explainability
- SHAP artifacts are generated
- SHAP references are persisted
- SHAP explanations are tied to model version

### 5. Replay & Auditability
- Whether AI outputs can be recomputed later
- Whether non-deterministic inputs break audit trails

### 6. No Black-Box Paths
- No inference path bypasses explanation
- No opaque scores

---

## WHAT IS EXPLICITLY NOT ASSUMED

- **NOT ASSUMED:** That ingest_time (ingested_at) is deterministic (Validation File 06 is FAILED, ingested_at is non-deterministic)
- **NOT ASSUMED:** That correlation engine produces deterministic incidents (Validation File 07 is FAILED, incidents may differ on replay)
- **NOT ASSUMED:** That AI Core receives deterministic inputs (incidents may differ on replay)
- **NOT ASSUMED:** That AI outputs can be recomputed from stored evidence if inputs are non-deterministic

---

## VALIDATION METHODOLOGY

### Evidence Collection Strategy

1. **Code Path Analysis:** Trace model training, inference, SHAP generation, model versioning
2. **Database Query Analysis:** Examine SQL queries for model version storage, SHAP persistence, feature storage
3. **Determinism Analysis:** Verify inference determinism, training reproducibility, SHAP determinism
4. **Provenance Analysis:** Check model versioning, lineage tracking, training data traceability
5. **Explainability Analysis:** Verify SHAP generation, persistence, model version association
6. **Replay Analysis:** Check if AI outputs can be recomputed from stored evidence

### Forbidden Patterns (Grep Validation)

- `random\.|np\.random|torch\.rand` — Hidden randomness (must be seeded)
- `NOW\(\)|CURRENT_TIMESTAMP` — Non-deterministic timestamps (affects replay)
- `continue.*except|pass.*except` — Silent error handling (forbidden, must fail-closed)

---

## 1. MODEL REGISTRY & PROVENANCE

### Evidence

**Model Versioning:**
- ✅ Model version storage: `services/ai-core/app/db.py:155-199` - `get_model_version()` stores model versions in `ai_model_versions` table
- ✅ Model version fields: `services/ai-core/app/db.py:180-186` - Model versions include `model_type`, `model_version_string`, `deployed_at`, `description`
- ✅ Model version retrieval: `services/ai-core/app/main.py:191-192` - `get_model_version(write_conn, 'CLUSTERING', '1.0.0')` and `get_model_version(write_conn, 'EXPLAINABILITY', '1.0.0')`
- ⚠️ **ISSUE:** Model versions are hard-coded: `services/ai-core/app/main.py:191-192` - Model versions are `'1.0.0'` (hard-coded, not derived from training artifacts)
- ⚠️ **ISSUE:** Model version creation uses `NOW()`: `services/ai-core/app/db.py:184` - `deployed_at = NOW()` (non-deterministic timestamp)

**Model Lineage:**
- ⚠️ **ISSUE:** No model lineage tracking found: No code found that tracks model lineage (parent models, training data sources, training parameters)
- ⚠️ **ISSUE:** Model versions do not reference training data: `services/ai-core/app/db.py:180-186` - Model versions do not include training data references
- ⚠️ **ISSUE:** Model versions do not reference training parameters: `services/ai-core/app/db.py:180-186` - Model versions do not include training parameters

**Training Data Traceability:**
- ⚠️ **ISSUE:** No training data traceability found: No code found that tracks training data sources, training data versions, or training data hashes
- ⚠️ **ISSUE:** Models are trained at runtime: `services/ai-core/app/clustering.py:53-54` - `KMeans.fit_predict()` trains model at runtime (no persistent training data)
- ⚠️ **ISSUE:** Training data is incidents: `services/ai-core/app/main.py:153` - `get_unresolved_incidents(read_conn)` reads incidents (training data is incidents, not tracked separately)

**Any Model Is Used Without Provenance:**
- ⚠️ **ISSUE:** Models are trained at runtime: `services/ai-core/app/clustering.py:53-54` - Models are trained at runtime (no persistent trained models)
- ⚠️ **ISSUE:** Model versions are hard-coded: `services/ai-core/app/main.py:191-192` - Model versions are `'1.0.0'` (hard-coded, not derived from training artifacts)
- ⚠️ **ISSUE:** Model provenance is minimal: Model versions exist but do not include training data references, training parameters, or model lineage

### Verdict: **PARTIAL**

**Justification:**
- Model versioning exists (model versions are stored in database)
- **ISSUE:** Model versions are hard-coded (not derived from training artifacts)
- **ISSUE:** No model lineage tracking found
- **ISSUE:** No training data traceability found
- **ISSUE:** Models are trained at runtime (no persistent trained models)

**PASS Conditions (Met):**
- Model versioning exists — **CONFIRMED** (model versions are stored)

**FAIL Conditions (Met):**
- Any model is used without provenance — **PARTIAL** (model versions exist but provenance is minimal)

**Evidence Required:**
- File paths: `services/ai-core/app/db.py:155-199,180-186`, `services/ai-core/app/main.py:191-192`, `services/ai-core/app/clustering.py:53-54`
- Model versioning: Model version storage, retrieval, fields
- Provenance: Model lineage, training data traceability

---

## 2. TRAINING & RETRAINING DISCIPLINE

### Evidence

**Presence of Training Script:**
- ❌ **CRITICAL:** No separate training script found: No `*train*.py` files found in `services/ai-core/`
- ⚠️ **ISSUE:** Models are trained inline at runtime: `services/ai-core/app/clustering.py:53-54` - `kmeans = KMeans(...); cluster_labels = kmeans.fit_predict(feature_vectors)` (training happens inline)
- ❌ **CRITICAL:** No separate training script exists (training happens inline at runtime)

**Ability to Train from Scratch:**
- ✅ Models can be trained from scratch: `services/ai-core/app/clustering.py:53-54` - `KMeans.fit_predict()` trains model from scratch each run
- ✅ Training happens at runtime: `services/ai-core/app/main.py:236` - `cluster_incidents(feature_vectors, n_clusters=n_clusters, random_state=42)` trains model from scratch
- ⚠️ **ISSUE:** Models are retrained from scratch each run (no persistent trained models)

**Deterministic Training Options:**
- ✅ Deterministic training: `services/ai-core/app/clustering.py:53` - `random_state=42` ensures reproducibility
- ✅ Deterministic training: `services/ai-core/app/clustering.py:53` - `n_init=10` fixed initialization count
- ✅ Reproducible: `services/ai-core/app/clustering.py:19-56` - `random_state=42` ensures same input → same output (reproducible)
- ✅ Training inputs are deterministic: `services/ai-core/app/feature_extraction.py:15-60` - Feature extraction is deterministic (no probabilistic logic)

**Model Versioning & Metadata:**
- ✅ Model versioning: `services/ai-core/app/main.py:191-192` - `get_model_version(write_conn, 'CLUSTERING', '1.0.0')` and `get_model_version(write_conn, 'EXPLAINABILITY', '1.0.0')`
- ✅ Model versions stored: `services/ai-core/app/db.py:155-199` - `get_model_version()` stores model versions in `ai_model_versions` table
- ✅ Model metadata: `services/ai-core/app/db.py:180-186` - Model versions include `model_type`, `model_version_string`, `deployed_at`, `description`
- ⚠️ **ISSUE:** Model versions are hard-coded (`'1.0.0'`), not derived from training artifacts

**Models Cannot Be Reproduced:**
- ⚠️ **ISSUE:** Models are retrained from scratch each run: `services/ai-core/app/clustering.py:53-54` - Models are retrained from scratch (no persistent trained models)
- ⚠️ **ISSUE:** Training data is incidents (may differ on replay): `services/ai-core/app/main.py:153` - `get_unresolved_incidents(read_conn)` reads incidents (training data may differ on replay if correlation is non-deterministic)
- ✅ Training is deterministic: `services/ai-core/app/clustering.py:53` - `random_state=42` ensures reproducibility
- ⚠️ **ISSUE:** But training data (incidents) may differ on replay (if correlation is non-deterministic)

**Training Code Is Missing:**
- ❌ **CRITICAL:** No separate training script found: No `*train*.py` files found in `services/ai-core/`
- ⚠️ **ISSUE:** Training code is inline: `services/ai-core/app/clustering.py:53-54` - Training code is inline (not in separate script)

### Verdict: **PARTIAL**

**Justification:**
- Models can be trained from scratch (training happens inline at runtime)
- Training is deterministic (random_state=42 ensures reproducibility)
- Model versioning exists (but versions are hard-coded, not derived from training artifacts)
- **CRITICAL ISSUE:** No separate training script found (training happens inline at runtime)
- **ISSUE:** Models are retrained from scratch each run (no persistent trained models)
- **ISSUE:** Training data (incidents) may differ on replay (if correlation is non-deterministic)

**PASS Conditions (Met):**
- Ability to train from scratch — **CONFIRMED** (training happens inline at runtime)
- Deterministic training options — **CONFIRMED** (random_state=42 ensures reproducibility)

**FAIL Conditions (Met):**
- Models cannot be reproduced — **PARTIAL** (training is deterministic, but training data may differ on replay)
- Training code is missing — **CONFIRMED** (no separate training script)

**Evidence Required:**
- File paths: `services/ai-core/app/clustering.py:53-54,19-56`, `services/ai-core/app/main.py:236,191-192`, `services/ai-core/app/feature_extraction.py:15-60`
- Training: Inline training, deterministic options, reproducibility
- Model versioning: Model version storage, hard-coded versions

---

## 3. INFERENCE DETERMINISM (NON-LLM)

### Evidence

**Identical Inputs → Identical Outputs:**
- ✅ Clustering is deterministic: `services/ai-core/app/clustering.py:53` - `random_state=42` ensures reproducibility
- ✅ Feature extraction is deterministic: `services/ai-core/app/feature_extraction.py:15-60` - Feature extraction is deterministic (no probabilistic logic)
- ✅ SHAP explanation is deterministic: `services/ai-core/app/shap_explainer.py:17-81` - SHAP explanation is deterministic (computed from feature values)
- ⚠️ **ISSUE:** But inputs (incidents) may differ on replay (if correlation is non-deterministic)

**No Hidden Randomness:**
- ✅ Clustering uses fixed random_state: `services/ai-core/app/clustering.py:53` - `random_state=42` (no hidden randomness)
- ✅ Feature extraction has no randomness: `services/ai-core/app/feature_extraction.py:15-60` - Feature extraction is deterministic (no probabilistic logic)
- ✅ SHAP explanation has no randomness: `services/ai-core/app/shap_explainer.py:17-81` - SHAP explanation is deterministic (computed from feature values)
- ✅ **VERIFIED:** No hidden randomness found (all operations are deterministic)

**Outputs Vary Without Explanation:**
- ✅ **VERIFIED:** Outputs do not vary without explanation: All operations are deterministic (random_state=42, no probabilistic logic)
- ⚠️ **ISSUE:** But inputs (incidents) may differ on replay (if correlation is non-deterministic), causing outputs to differ

**Inference Depends on Non-Deterministic Inputs:**
- ⚠️ **ISSUE:** Inference depends on incidents: `services/ai-core/app/main.py:153` - `get_unresolved_incidents(read_conn)` reads incidents (inputs are incidents)
- ⚠️ **ISSUE:** Incidents may differ on replay (if correlation is non-deterministic): Validation File 07 is FAILED, incidents may differ on replay
- ⚠️ **ISSUE:** If incidents differ on replay, inference outputs will differ (inputs differ)

### Verdict: **PARTIAL**

**Justification:**
- Inference is deterministic (random_state=42, no hidden randomness)
- **ISSUE:** But inputs (incidents) may differ on replay (if correlation is non-deterministic), causing outputs to differ
- **ISSUE:** Inference depends on non-deterministic inputs (incidents from correlation engine)

**PASS Conditions (Met):**
- Identical inputs → identical outputs — **CONFIRMED** (inference is deterministic)
- No hidden randomness — **CONFIRMED** (random_state=42, no probabilistic logic)

**FAIL Conditions (Met):**
- Outputs vary without explanation — **PARTIAL** (outputs may vary if inputs differ on replay)

**Evidence Required:**
- File paths: `services/ai-core/app/clustering.py:53`, `services/ai-core/app/feature_extraction.py:15-60`, `services/ai-core/app/shap_explainer.py:17-81`, `services/ai-core/app/main.py:153`
- Inference determinism: random_state, deterministic operations
- Input dependencies: Incidents from correlation engine

---

## 4. SHAP EXPLAINABILITY

### Evidence

**SHAP Generation Per Inference:**
- ✅ SHAP generated per incident: `services/ai-core/app/main.py:338` - `shap_explanations = explain_batch(incidents, feature_vectors.tolist())`
- ✅ SHAP generated for all incidents: `services/ai-core/app/main.py:358-362` - Loop stores SHAP explanation for each incident
- ✅ SHAP generated per run: `services/ai-core/app/shap_explainer.py:84-106` - `explain_batch()` generates SHAP for all incidents
- ⚠️ **ISSUE:** SHAP is SHAP-like, not full SHAP: `services/ai-core/app/shap_explainer.py:29` - "Phase 6 minimal: Simple SHAP-like explanation method (full SHAP library not required)"
- ⚠️ **ISSUE:** SHAP is simplified: `services/ai-core/app/shap_explainer.py:46-70` - Simple linear contribution model (proportional to feature value)

**Storage of SHAP Artifacts:**
- ✅ SHAP artifacts stored: `services/ai-core/app/main.py:360-361` - `store_shap_explanation(write_conn, incident['incident_id'], explainability_model_version, shap_explanation, top_n=10)`
- ✅ SHAP stored in database: `services/ai-core/app/db.py:326-362` - `store_shap_explanation()` stores in `shap_explanations` table
- ✅ SHAP stored as references: `services/ai-core/app/db.py:336-339` - SHAP explanation stored as hash (reference only, not blob)
- ✅ Top N features stored: `services/ai-core/app/db.py:342` - Top N features stored as JSONB for quick access

**Association with Model Version + Incident:**
- ✅ Associated with model version: `services/ai-core/app/main.py:360` - `store_shap_explanation(..., explainability_model_version, ...)`
- ✅ Associated with incident: `services/ai-core/app/main.py:360` - `store_shap_explanation(write_conn, incident['incident_id'], ...)`
- ✅ Stored with associations: `services/ai-core/app/db.py:345-350` - SHAP stored with `event_id` (incident_id) and `model_version_id`

**Any Inference Lacks Explainability:**
- ✅ **VERIFIED:** All inferences have SHAP: `services/ai-core/app/main.py:338` - `shap_explanations = explain_batch(incidents, feature_vectors.tolist())` (generates SHAP for all incidents)
- ✅ **VERIFIED:** SHAP stored for all incidents: `services/ai-core/app/main.py:358-362` - Loop stores SHAP explanation for each incident

**SHAP Data Cannot Be Verified Later:**
- ⚠️ **ISSUE:** SHAP is stored as hash: `services/ai-core/app/db.py:336-339` - SHAP explanation stored as hash (reference only, not blob)
- ⚠️ **ISSUE:** SHAP explanation itself is not stored: `services/ai-core/app/db.py:336-339` - Only hash is stored, not full explanation
- ⚠️ **ISSUE:** SHAP cannot be recomputed from stored data: SHAP explanation is not stored, only hash (cannot verify later)
- ⚠️ **ISSUE:** Top N features are stored: `services/ai-core/app/db.py:342` - Top N features stored as JSONB (partial explanation stored)

### Verdict: **PARTIAL**

**Justification:**
- SHAP is generated per inference (for all incidents)
- SHAP artifacts are stored (as references, with top N features)
- SHAP is associated with model version and incident
- **ISSUE:** SHAP is SHAP-like, not full SHAP library (simple linear contribution model)
- **ISSUE:** SHAP explanation itself is not stored (only hash), cannot be verified later

**PASS Conditions (Met):**
- SHAP generation per inference — **CONFIRMED** (SHAP generated for all incidents)
- Storage of SHAP artifacts — **CONFIRMED** (SHAP stored as references)
- Association with model version + incident — **CONFIRMED** (SHAP stored with associations)

**FAIL Conditions (Met):**
- Any inference lacks explainability — **NOT CONFIRMED** (all inferences have SHAP)
- SHAP data cannot be verified later — **CONFIRMED** (SHAP explanation not stored, only hash)

**Evidence Required:**
- File paths: `services/ai-core/app/main.py:338,360-361`, `services/ai-core/app/db.py:326-362,336-339,342,345-350`, `services/ai-core/app/shap_explainer.py:29,46-70`
- SHAP generation: SHAP generation per inference, SHAP-like vs full SHAP
- SHAP storage: Hash storage, top N features, associations

---

## 5. REPLAY & AUDITABILITY

### Evidence

**Whether AI Outputs Can Be Recomputed Later:**
- ⚠️ **ISSUE:** Models are retrained from scratch each run: `services/ai-core/app/clustering.py:53-54` - Models are retrained from scratch (no persistent trained models)
- ⚠️ **ISSUE:** Training data is incidents (may differ on replay): `services/ai-core/app/main.py:153` - `get_unresolved_incidents(read_conn)` reads incidents (training data may differ on replay if correlation is non-deterministic)
- ⚠️ **ISSUE:** If incidents differ on replay, models will differ (training data differs)
- ⚠️ **ISSUE:** If models differ, outputs will differ (inference depends on model)
- ✅ Feature extraction is deterministic: `services/ai-core/app/feature_extraction.py:15-60` - Feature extraction is deterministic (can be recomputed)
- ✅ SHAP explanation is deterministic: `services/ai-core/app/shap_explainer.py:17-81` - SHAP explanation is deterministic (can be recomputed)
- ⚠️ **ISSUE:** But inputs (incidents) may differ on replay (if correlation is non-deterministic)

**Whether Non-Deterministic Inputs Break Audit Trails:**
- ⚠️ **ISSUE:** Inputs are incidents: `services/ai-core/app/main.py:153` - `get_unresolved_incidents(read_conn)` reads incidents (inputs are incidents)
- ⚠️ **ISSUE:** Incidents may differ on replay (if correlation is non-deterministic): Validation File 07 is FAILED, incidents may differ on replay
- ⚠️ **ISSUE:** If incidents differ on replay, AI outputs will differ (inputs differ)
- ❌ **CRITICAL FAILURE:** Non-deterministic inputs break audit trails (cannot recompute same outputs from stored evidence if inputs differ)

**Outputs Cannot Be Re-Derived from Stored Evidence:**
- ⚠️ **ISSUE:** SHAP explanation is not stored: `services/ai-core/app/db.py:336-339` - Only hash is stored, not full explanation
- ⚠️ **ISSUE:** Models are not stored: `services/ai-core/app/clustering.py:53-54` - Models are retrained from scratch (no persistent trained models)
- ⚠️ **ISSUE:** Training data (incidents) may differ on replay (if correlation is non-deterministic)
- ❌ **CRITICAL FAILURE:** Outputs cannot be re-derived from stored evidence (SHAP not stored, models not stored, inputs may differ on replay)

### Verdict: **FAIL**

**Justification:**
- **CRITICAL FAILURE:** Non-deterministic inputs break audit trails (cannot recompute same outputs from stored evidence if inputs differ)
- **CRITICAL FAILURE:** Outputs cannot be re-derived from stored evidence (SHAP not stored, models not stored, inputs may differ on replay)
- **ISSUE:** Models are retrained from scratch each run (no persistent trained models)
- **ISSUE:** Training data (incidents) may differ on replay (if correlation is non-deterministic)

**FAIL Conditions (Met):**
- Outputs cannot be re-derived from stored evidence — **CONFIRMED** (SHAP not stored, models not stored, inputs may differ)
- Non-deterministic inputs break audit trails — **CONFIRMED** (inputs may differ on replay)

**Evidence Required:**
- File paths: `services/ai-core/app/main.py:153`, `services/ai-core/app/clustering.py:53-54`, `services/ai-core/app/db.py:336-339`
- Replay: Model retraining, input dependencies, output recomputation
- Audit trails: SHAP storage, model storage, input determinism

---

## 6. NO BLACK-BOX PATHS

### Evidence

**No Inference Path Bypasses Explanation:**
- ✅ All inferences generate SHAP: `services/ai-core/app/main.py:338` - `shap_explanations = explain_batch(incidents, feature_vectors.tolist())` (generates SHAP for all incidents)
- ✅ SHAP stored for all incidents: `services/ai-core/app/main.py:358-362` - Loop stores SHAP explanation for each incident
- ✅ **VERIFIED:** No inference path bypasses explanation (all inferences have SHAP)

**No Opaque Scores:**
- ✅ Feature extraction is explicit: `services/ai-core/app/feature_extraction.py:15-60` - Feature extraction is explicit (confidence_score, current_stage, total_evidence_count)
- ✅ Clustering is explicit: `services/ai-core/app/clustering.py:18-56` - Clustering is explicit (KMeans with random_state=42)
- ✅ SHAP explanation is explicit: `services/ai-core/app/shap_explainer.py:17-81` - SHAP explanation is explicit (feature contributions)
- ✅ **VERIFIED:** No opaque scores found (all operations are explicit)

**Any Decision Is Unexplainable:**
- ✅ **VERIFIED:** All decisions are explainable: All inferences have SHAP explanations
- ✅ **VERIFIED:** No black-box paths found (all operations are explicit and explainable)

### Verdict: **PASS**

**Justification:**
- All inferences generate SHAP explanations
- No inference path bypasses explanation
- No opaque scores found (all operations are explicit)
- All decisions are explainable

**PASS Conditions (Met):**
- No inference path bypasses explanation — **CONFIRMED** (all inferences have SHAP)
- No opaque scores — **CONFIRMED** (all operations are explicit)

**Evidence Required:**
- File paths: `services/ai-core/app/main.py:338,358-362`, `services/ai-core/app/feature_extraction.py:15-60`, `services/ai-core/app/clustering.py:18-56`, `services/ai-core/app/shap_explainer.py:17-81`
- Explainability: SHAP generation, explicit operations, no black-box paths

---

## CREDENTIAL TYPES VALIDATED

### Database Credentials
- **Type:** PostgreSQL user/password (`RANSOMEYE_DB_USER`/`RANSOMEYE_DB_PASSWORD`)
- **Source:** Environment variable (required, no default)
- **Validation:** ❌ **NOT VALIDATED** (validation file 05 covers database credentials)
- **Usage:** Database connection for AI metadata operations
- **Status:** ❌ **NOT VALIDATED** (outside scope of this validation)

---

## PASS CONDITIONS

### Section 1: Model Registry & Provenance
- ✅ Model versioning exists — **PASS**
- ⚠️ Model lineage exists — **PARTIAL**
- ⚠️ Training data traceability exists — **PARTIAL**

### Section 2: Training & Retraining Discipline
- ✅ Ability to train from scratch — **PASS**
- ✅ Deterministic training options — **PASS**
- ❌ Separate training script exists — **FAIL**

### Section 3: Inference Determinism (Non-LLM)
- ✅ Identical inputs → identical outputs — **PASS**
- ✅ No hidden randomness — **PASS**
- ⚠️ Outputs do NOT vary without explanation — **PARTIAL**

### Section 4: SHAP Explainability
- ✅ SHAP generation per inference — **PASS**
- ✅ Storage of SHAP artifacts — **PASS**
- ✅ Association with model version + incident — **PASS**
- ⚠️ SHAP data can be verified later — **PARTIAL**

### Section 5: Replay & Auditability
- ❌ AI outputs can be recomputed later — **FAIL**
- ❌ Non-deterministic inputs do NOT break audit trails — **FAIL**

### Section 6: No Black-Box Paths
- ✅ No inference path bypasses explanation — **PASS**
- ✅ No opaque scores — **PASS**

---

## FAIL CONDITIONS

### Section 1: Model Registry & Provenance
- ⚠️ Any model is used without provenance — **PARTIAL** (model versions exist but provenance is minimal)

### Section 2: Training & Retraining Discipline
- ❌ **CONFIRMED:** Training code is missing — **No separate training script found**
- ⚠️ Models cannot be reproduced — **PARTIAL** (training is deterministic, but training data may differ on replay)

### Section 3: Inference Determinism (Non-LLM)
- ⚠️ Outputs vary without explanation — **PARTIAL** (outputs may vary if inputs differ on replay)

### Section 4: SHAP Explainability
- ❌ **CONFIRMED:** SHAP data cannot be verified later — **SHAP explanation not stored, only hash**

### Section 5: Replay & Auditability
- ❌ **CONFIRMED:** Outputs cannot be re-derived from stored evidence — **SHAP not stored, models not stored, inputs may differ**
- ❌ **CONFIRMED:** Non-deterministic inputs break audit trails — **Inputs may differ on replay**

### Section 6: No Black-Box Paths
- ❌ Any decision is unexplainable — **NOT CONFIRMED** (all decisions are explainable)

---

## EVIDENCE REQUIRED

### Model Registry & Provenance
- File paths: `services/ai-core/app/db.py:155-199,180-186`, `services/ai-core/app/main.py:191-192`, `services/ai-core/app/clustering.py:53-54`
- Model versioning: Model version storage, retrieval, fields
- Provenance: Model lineage, training data traceability

### Training & Retraining Discipline
- File paths: `services/ai-core/app/clustering.py:53-54,19-56`, `services/ai-core/app/main.py:236,191-192`, `services/ai-core/app/feature_extraction.py:15-60`
- Training: Inline training, deterministic options, reproducibility
- Model versioning: Model version storage, hard-coded versions

### Inference Determinism (Non-LLM)
- File paths: `services/ai-core/app/clustering.py:53`, `services/ai-core/app/feature_extraction.py:15-60`, `services/ai-core/app/shap_explainer.py:17-81`, `services/ai-core/app/main.py:153`
- Inference determinism: random_state, deterministic operations
- Input dependencies: Incidents from correlation engine

### SHAP Explainability
- File paths: `services/ai-core/app/main.py:338,360-361`, `services/ai-core/app/db.py:326-362,336-339,342,345-350`, `services/ai-core/app/shap_explainer.py:29,46-70`
- SHAP generation: SHAP generation per inference, SHAP-like vs full SHAP
- SHAP storage: Hash storage, top N features, associations

### Replay & Auditability
- File paths: `services/ai-core/app/main.py:153`, `services/ai-core/app/clustering.py:53-54`, `services/ai-core/app/db.py:336-339`
- Replay: Model retraining, input dependencies, output recomputation
- Audit trails: SHAP storage, model storage, input determinism

### No Black-Box Paths
- File paths: `services/ai-core/app/main.py:338,358-362`, `services/ai-core/app/feature_extraction.py:15-60`, `services/ai-core/app/clustering.py:18-56`, `services/ai-core/app/shap_explainer.py:17-81`
- Explainability: SHAP generation, explicit operations, no black-box paths

---

## GA VERDICT

### Overall: **FAIL**

**Critical Blockers:**

1. **FAIL:** Outputs cannot be re-derived from stored evidence
   - **Impact:** SHAP explanation is not stored (only hash), models are not stored (retrained from scratch), inputs (incidents) may differ on replay
   - **Location:** `services/ai-core/app/db.py:336-339` — SHAP stored as hash only, `services/ai-core/app/clustering.py:53-54` — Models retrained from scratch
   - **Severity:** **CRITICAL** (violates auditability requirement)
   - **Master Spec Violation:** AI outputs must be recomputable from stored evidence

2. **FAIL:** Non-deterministic inputs break audit trails
   - **Impact:** Inputs (incidents) may differ on replay (if correlation is non-deterministic), causing AI outputs to differ
   - **Location:** `services/ai-core/app/main.py:153` — `get_unresolved_incidents(read_conn)` reads incidents (inputs may differ on replay)
   - **Severity:** **CRITICAL** (violates auditability requirement)
   - **Master Spec Violation:** Audit trails must not be broken by non-deterministic inputs

3. **FAIL:** No separate training script found
   - **Impact:** Training happens inline at runtime, not in separate script
   - **Location:** `services/ai-core/app/clustering.py:53-54` — Training happens inline
   - **Severity:** **CRITICAL** (violates training discipline requirement)
   - **Master Spec Violation:** Training pipeline must be separate and reproducible

4. **PARTIAL:** SHAP data cannot be verified later
   - **Impact:** SHAP explanation is not stored (only hash), cannot be verified later
   - **Location:** `services/ai-core/app/db.py:336-339` — SHAP stored as hash only
   - **Severity:** **HIGH** (affects explainability verification)
   - **Master Spec Violation:** SHAP data must be verifiable later

5. **PARTIAL:** Model provenance is minimal
   - **Impact:** Model versions exist but do not include training data references, training parameters, or model lineage
   - **Location:** `services/ai-core/app/db.py:180-186` — Model versions do not include provenance fields
   - **Severity:** **MEDIUM** (affects model traceability)
   - **Master Spec Violation:** Model provenance must include training data and parameters

**Non-Blocking Issues:**

1. Inference is deterministic (random_state=42, no hidden randomness)
2. All inferences generate SHAP explanations
3. No black-box paths found (all operations are explicit)
4. Feature extraction is deterministic
5. SHAP explanation is deterministic (but SHAP-like, not full SHAP)

**Strengths:**

1. ✅ Inference is deterministic (random_state=42, no hidden randomness)
2. ✅ All inferences generate SHAP explanations
3. ✅ No black-box paths found (all operations are explicit)
4. ✅ Feature extraction is deterministic
5. ✅ SHAP explanation is deterministic
6. ✅ Model versioning exists (but provenance is minimal)

**Summary of Critical Blockers:**

1. **CRITICAL:** Outputs cannot be re-derived from stored evidence — SHAP not stored, models not stored, inputs may differ on replay
2. **CRITICAL:** Non-deterministic inputs break audit trails — Inputs may differ on replay, causing outputs to differ
3. **CRITICAL:** No separate training script found — Training happens inline at runtime
4. **HIGH:** SHAP data cannot be verified later — SHAP explanation not stored, only hash
5. **MEDIUM:** Model provenance is minimal — Model versions do not include training data or parameters

---

**Validation Date:** 2025-01-13  
**Validator:** Independent System Validator  
**Next Step:** Validation Step 9 — Policy Engine (if applicable)  
**GA Status:** **BLOCKED** (Critical failures in auditability and training discipline)

---

## DOWNSTREAM IMPACT STATEMENT

**Documentation Only:** This section documents downstream impact of AI Core non-determinism and auditability failures on downstream validations.

**Downstream Validations Impacted by AI Core Failures:**

1. **Policy Engine (Validation Step 9, if applicable):**
   - Policy Engine may read AI metadata (clusters, SHAP explanations)
   - AI metadata may differ on replay (if inputs differ on replay)
   - Policy Engine validation must NOT assume deterministic AI metadata

2. **Reporting & Dashboards (Validation Step 18, if applicable):**
   - Reporting may display AI metadata (clusters, SHAP explanations)
   - AI metadata may differ on replay (if inputs differ on replay)
   - Reporting validation must NOT assume deterministic AI metadata

**Requirements for Downstream Validations:**

- Downstream validations must NOT assume deterministic AI metadata (AI metadata may differ on replay)
- Downstream validations must NOT assume replay fidelity for AI outputs (outputs may differ on replay)
- Downstream validations must validate their components based on actual behavior, not assumptions about AI determinism
- Downstream validations must explicitly document any dependencies on AI determinism if they exist
