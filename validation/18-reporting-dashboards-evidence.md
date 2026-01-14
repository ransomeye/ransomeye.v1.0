# Validation Step 18 — Reporting, Dashboards & Evidence Validity Meta-Validation

**Component Identity:**
- **Name:** Reporting & Dashboard Evidence Validity Assessment
- **Primary Paths:**
  - `/home/ransomeye/rebuild/signed-reporting/` - Signed Reporting Engine (PDF, HTML, CSV exports)
  - `/home/ransomeye/rebuild/services/ui/` - SOC UI Dashboard (read-only)
  - `/home/ransomeye/rebuild/explanation-assembly/` - Explanation Assembly Engine (source for reports)
  - `/home/ransomeye/rebuild/forensic-summarization/` - Forensic Summarization (evidence generation)
- **Entry Points:**
  - Signed Reporting: `signed-reporting/cli/generate_report.py` - Report generation CLI
  - Signed Reporting: `signed-reporting/api/reporting_api.py:139` - `generate_report()` API
  - UI Backend: `services/ui/backend/main.py:309` - `GET /api/incidents` endpoint
  - UI Frontend: `services/ui/frontend/src/App.jsx:11` - React component

**Master Spec References:**
- Validation Step 3: `validation/03-secure-bus-interservice-trust.md` - Inter-service trust (binding, GA verdict: **FAIL**)
- Validation Step 4: `validation/04-ingest-normalization-db-write.md` - Ingest determinism (binding, GA verdict: **FAIL**)
- Validation Step 7: `validation/07-correlation-engine.md` - Correlation determinism (binding, GA verdict: **FAIL**)
- Validation Step 8: `validation/08-ai-core-ml-shap.md` - AI determinism (binding, GA verdict: **FAIL**)
- Validation Step 9: `validation/09-policy-engine-command-authority.md` - Policy authority (binding, GA verdict: **PARTIAL**)
- Validation Step 14: `validation/14-ui-api-access-control.md` - UI authentication (binding, GA verdict: **FAIL**)
- Validation Step 16: `validation/16-end-to-end-threat-scenarios.md` - E2E validation validity (binding, GA verdict: **NOT VALID**)
- Validation Step 17: `validation/17-end-to-end-credential-chain.md` - Credential chain (binding, GA verdict: **FAIL**)

---

## PURPOSE

This meta-validation answers one question only:

**"Given upstream failures, are reporting and dashboards producing valid evidence, or are they presenting unverifiable representations?"**

This validation does NOT execute dashboards or generate reports. This validation determines whether dashboards and reports can produce valid, auditable, trustworthy evidence given the current trust boundary failures and non-determinism documented in validation files 01-17.

This validation does NOT validate threat logic, correlation, or AI. This validation validates the validity of reporting and dashboard evidence claims.

---

## MASTER SPEC REFERENCES

**Binding Validation Files (Treated as Authoritative):**
- Validation Step 3: `validation/03-secure-bus-interservice-trust.md` - Inter-service trust (binding, GA verdict: **FAIL**)
- Validation Step 4: `validation/04-ingest-normalization-db-write.md` - Ingest determinism (binding, GA verdict: **FAIL**)
- Validation Step 7: `validation/07-correlation-engine.md` - Correlation determinism (binding, GA verdict: **FAIL**)
- Validation Step 8: `validation/08-ai-core-ml-shap.md` - AI determinism (binding, GA verdict: **FAIL**)
- Validation Step 9: `validation/09-policy-engine-command-authority.md` - Policy authority (binding, GA verdict: **PARTIAL**)
- Validation Step 14: `validation/14-ui-api-access-control.md` - UI authentication (binding, GA verdict: **FAIL**)
- Validation Step 16: `validation/16-end-to-end-threat-scenarios.md` - E2E validation validity (binding, GA verdict: **NOT VALID**)
- Validation Step 17: `validation/17-end-to-end-credential-chain.md` - Credential chain (binding, GA verdict: **FAIL**)

---

## DEFINITION OF "EVIDENCE" VS "PRESENTATION"

**Evidence Definition:**

For reporting and dashboards to produce valid evidence, the following must be true:

1. **Evidence is verifiable** — Evidence can be cryptographically verified (signed, hashed)
2. **Evidence is reproducible** — Same inputs → same evidence (deterministic)
3. **Evidence is traceable** — Evidence can be traced back to source (chain-of-custody)
4. **Evidence is admissible** — Evidence can be defended in court (legal admissibility)

**Presentation Definition:**

Presentation is display-only, observational, and may not be:
- Cryptographically verifiable
- Reproducible
- Traceable
- Legally admissible

**If dashboards/reports claim "evidence" but cannot be verified, reproduced, traced, or defended in court → they are presentation-only, not evidence**

---

## UPSTREAM DEPENDENCY MATRIX (FILES 01-17)

### Upstream Failures (Binding)

**File 03 — Inter-Service Trust: FAIL**
- No service-to-service authentication
- Ingest does NOT verify agent signatures
- No service identity verification
- Plain HTTP used (no TLS)
- No replay protection

**File 04 — Ingest Determinism: FAIL**
- `ingested_at` is NOT deterministic (uses `datetime.now()`)
- SQL `NOW()` is NOT deterministic

**File 07 — Correlation Determinism: FAIL**
- Event ordering depends on `ingested_at` (non-deterministic)
- Same evidence set may produce different incident graph
- Confidence accumulation order depends on processing order

**File 08 — AI Determinism: FAIL**
- Outputs cannot be re-derived from stored evidence
- Non-deterministic inputs break audit trails

**File 16 — E2E Validation Validity: NOT VALID**
- E2E threat scenario validation is NOT VALID
- E2E validation cannot produce valid, auditable, trustworthy evidence

**File 17 — Credential Chain: FAIL**
- All credential types have critical failures
- No credential scoping
- No rotation/revocation

### Upstream Dependencies for Reporting/Dashboards

**Reporting/Dashboards Depend On:**
- Incidents (from Correlation Engine) — **FAIL** (File 07: incidents are non-deterministic)
- AI outputs (from AI Core) — **FAIL** (File 08: outputs cannot be re-derived)
- Timelines (from Correlation Engine) — **FAIL** (File 07: timelines depend on non-deterministic ingested_at)
- Confidence scores (from Correlation Engine) — **FAIL** (File 07: confidence depends on processing order)
- Evidence (from Ingest) — **FAIL** (File 04: ingested_at is non-deterministic)

**If upstream components are non-deterministic → reports/dashboards cannot be deterministic**

---

## EVIDENCE VALIDITY ANALYSIS

### 1. Evidence Definition

**What Dashboards/Reports Claim Is "Evidence":**

**UI Dashboard Claims:**
- ✅ Incident data: `services/ui/backend/views.sql:12-25` - `v_active_incidents` view exposes `incident_id`, `machine_id`, `stage`, `confidence`, `created_at`, `last_observed_at`, `total_evidence_count`, `title`, `description`
- ✅ Timeline data: `services/ui/backend/views.sql:35-48` - `v_incident_timeline` view exposes `incident_id`, `stage`, `transitioned_at`, `from_stage`, `transitioned_by`, `transition_reason`, `evidence_count_at_transition`, `confidence_score_at_transition`
- ✅ Evidence summary: `services/ui/backend/views.sql:56-66` - `v_incident_evidence_summary` view exposes `incident_id`, `evidence_count`, `evidence_type_count`, `last_evidence_at`, `first_evidence_at`
- ✅ AI insights: `services/ui/backend/views.sql:93-105` - `v_ai_insights` view exposes `incident_id`, `cluster_id`, `novelty_score`, `shap_summary`

**Signed Reports Claims:**
- ✅ Court-admissible reports: `signed-reporting/README.md:7` - "The Signed Reporting Engine produces **court-admissible, regulator-verifiable reports**"
- ✅ Signed and immutable: `signed-reporting/README.md:7` - "Reports are **signed**, **immutable**, and can be **re-verified years later**"
- ✅ Deterministic: `signed-reporting/README.md:116` - "**Deterministic**: Same inputs → same outputs (reproducible)"
- ✅ Verifiable: `signed-reporting/README.md:114` - "**Verifiable**: Offline verification without RansomEye system"

**Whether That Evidence Is Raw, Derived, Aggregated, or Inferred:**

**UI Dashboard Evidence:**
- ⚠️ **ISSUE:** Evidence is derived from non-deterministic sources:
  - `services/ui/backend/views.sql:12-25` - `v_active_incidents` view reads from `incidents` table (which is non-deterministic per File 07: FAIL)
  - `services/ui/backend/views.sql:35-48` - `v_incident_timeline` view reads from `incident_stages` table (which depends on non-deterministic ingested_at per File 07: FAIL)
  - `services/ui/backend/views.sql:56-66` - `v_incident_evidence_summary` view aggregates from `evidence` table (which depends on non-deterministic ingested_at per File 04: FAIL)
  - `services/ui/backend/views.sql:93-105` - `v_ai_insights` view joins AI outputs (which cannot be re-derived per File 08: FAIL)
  - ⚠️ **ISSUE:** Evidence is derived from non-deterministic sources (incidents, timelines, confidence scores are non-deterministic)

**Signed Reports Evidence:**
- ⚠️ **ISSUE:** Evidence is derived from non-deterministic sources:
  - `signed-reporting/api/reporting_api.py:161-176` - Reports read from Explanation Assembly (which depends on incidents, AI outputs)
  - `signed-reporting/api/reporting_api.py:180` - Reports use `incident_snapshot_time` (but incidents themselves are non-deterministic per File 07: FAIL)
  - ⚠️ **ISSUE:** Evidence is derived from non-deterministic sources (reports depend on incidents, AI outputs, which are non-deterministic)

**Verdict: PARTIAL**

**Justification:**
- Dashboards/reports claim to present evidence (incidents, timelines, confidence scores, AI insights)
- Evidence is derived from non-deterministic sources (incidents are non-deterministic, timelines depend on non-deterministic ingested_at, AI outputs cannot be re-derived)
- **ISSUE:** Evidence cannot be verified as authentic (depends on non-deterministic upstream components)

---

### 2. Determinism Dependency

**Whether Dashboards Assume Stable Incident IDs:**

**UI Dashboard Assumptions:**
- ✅ Incident IDs are stable: `services/ui/backend/views.sql:14` - `incident_id` column (assumes stable incident IDs)
- ⚠️ **ISSUE:** Incident IDs may not be stable upstream:
  - `validation/07-correlation-engine.md:527` - "Same evidence set may produce different incident graph if processed in different order"
  - `validation/07-correlation-engine.md:310` - "Reprocessing same raw_events with different `ingested_at` values may produce different incidents or different state transitions"
  - ⚠️ **ISSUE:** Incident IDs may not be stable (same evidence → different incidents on replay)

**Signed Reports Assumptions:**
- ✅ Incident IDs are stable: `signed-reporting/api/reporting_api.py:141` - `incident_id` parameter (assumes stable incident IDs)
- ⚠️ **ISSUE:** Incident IDs may not be stable upstream:
  - `validation/07-correlation-engine.md:527` - "Same evidence set may produce different incident graph if processed in different order"
  - ⚠️ **ISSUE:** Incident IDs may not be stable (same evidence → different incidents on replay)

**Whether Those Assumptions Are Invalid Upstream:**

**Binding Evidence from File 07:**
- ❌ **CRITICAL:** Incident IDs are NOT stable: `validation/07-correlation-engine.md:527` - "Same evidence set may produce different incident graph if processed in different order"
- ❌ **CRITICAL:** Reprocessing produces different incidents: `validation/07-correlation-engine.md:310` - "Reprocessing same raw_events with different `ingested_at` values may produce different incidents or different state transitions"

**Verdict: FAIL**

**Justification:**
- Dashboards assume stable incident IDs (incident_id column, incident_id parameter)
- **CRITICAL:** Incident IDs are NOT stable upstream (same evidence → different incidents on replay)
- **CRITICAL:** Assumptions are invalid (incident IDs are non-deterministic)

---

**Whether Dashboards Assume Stable Timelines:**

**UI Dashboard Assumptions:**
- ✅ Timelines are stable: `services/ui/backend/views.sql:35-48` - `v_incident_timeline` view exposes `transitioned_at`, `from_stage`, `to_stage` (assumes stable timelines)
- ⚠️ **ISSUE:** Timelines may not be stable upstream:
  - `validation/07-correlation-engine.md:539` - "State transition timestamps use `NOW()` (non-deterministic): `services/correlation-engine/app/db.py:343,354` — `NOW()` used for timestamps"
  - `validation/07-correlation-engine.md:521` - "Event ordering depends on `ingested_at` (non-deterministic): `services/correlation-engine/app/db.py:109` — `ORDER BY ingested_at ASC`"
  - ⚠️ **ISSUE:** Timelines may not be stable (state transition timestamps use NOW(), event ordering depends on ingested_at)

**Signed Reports Assumptions:**
- ✅ Timelines use incident snapshot time: `signed-reporting/api/reporting_api.py:180` - `incident_snapshot_time = self._get_incident_snapshot_time(incident_id)` (uses incident snapshot time, not system time)
- ⚠️ **ISSUE:** Incident snapshot time may not be stable:
  - `validation/07-correlation-engine.md:539` - "State transition timestamps use `NOW()` (non-deterministic)"
  - `validation/07-correlation-engine.md:521` - "Event ordering depends on `ingested_at` (non-deterministic)"
  - ⚠️ **ISSUE:** Incident snapshot time may not be stable (depends on non-deterministic state transitions)

**Whether Those Assumptions Are Invalid Upstream:**

**Binding Evidence from File 07:**
- ❌ **CRITICAL:** State transition timestamps use `NOW()`: `validation/07-correlation-engine.md:539` - "State transition timestamps use `NOW()` (non-deterministic): `services/correlation-engine/app/db.py:343,354` — `NOW()` used for timestamps"
- ❌ **CRITICAL:** Event ordering depends on `ingested_at`: `validation/07-correlation-engine.md:521` - "Event ordering depends on `ingested_at` (non-deterministic): `services/correlation-engine/app/db.py:109` — `ORDER BY ingested_at ASC`"

**Verdict: FAIL**

**Justification:**
- Dashboards assume stable timelines (transitioned_at, from_stage, to_stage)
- **CRITICAL:** Timelines are NOT stable upstream (state transition timestamps use NOW(), event ordering depends on ingested_at)
- **CRITICAL:** Assumptions are invalid (timelines are non-deterministic)

---

**Whether Dashboards Assume Stable Confidence Scores:**

**UI Dashboard Assumptions:**
- ✅ Confidence scores are stable: `services/ui/backend/views.sql:17` - `confidence_score AS confidence` (assumes stable confidence scores)
- ✅ Confidence scores at transition are stable: `services/ui/backend/views.sql:44` - `confidence_score_at_transition` (assumes stable confidence scores)
- ⚠️ **ISSUE:** Confidence scores may not be stable upstream:
  - `validation/07-correlation-engine.md:533` - "Confidence accumulation order depends on processing order (which depends on `ingested_at`): `services/correlation-engine/app/db.py:109` — `ORDER BY ingested_at ASC`"
  - `validation/07-correlation-engine.md:527` - "Same evidence set may produce different incident graph if processed in different order"
  - ⚠️ **ISSUE:** Confidence scores may not be stable (confidence accumulation order depends on processing order)

**Signed Reports Assumptions:**
- ⚠️ **ISSUE:** Reports may include confidence scores from assembled explanations (which depend on non-deterministic correlation)

**Whether Those Assumptions Are Invalid Upstream:**

**Binding Evidence from File 07:**
- ❌ **CRITICAL:** Confidence accumulation order depends on processing order: `validation/07-correlation-engine.md:533` - "Confidence accumulation order depends on processing order (which depends on `ingested_at`): `services/correlation-engine/app/db.py:109` — `ORDER BY ingested_at ASC`"
- ❌ **CRITICAL:** Same evidence → different confidence: `validation/07-correlation-engine.md:533` - "Same evidence set may produce different confidence if processed in different order"

**Verdict: FAIL**

**Justification:**
- Dashboards assume stable confidence scores (confidence_score, confidence_score_at_transition)
- **CRITICAL:** Confidence scores are NOT stable upstream (confidence accumulation order depends on processing order, same evidence → different confidence)
- **CRITICAL:** Assumptions are invalid (confidence scores are non-deterministic)

---

### 3. Cryptographic Validity

**What Is Signed vs Unsigned:**

**Signed Reports:**
- ✅ Reports are signed: `signed-reporting/api/reporting_api.py:196-198` - `signature = self.report_signer.sign_content(evidence_content)` (reports are signed with ed25519)
- ✅ Reports have content hash: `signed-reporting/api/reporting_api.py:192` - `content_hash = self.render_hasher.hash_content(evidence_content)` (reports have SHA256 content hash)
- ✅ Evidence content is signed: `signed-reporting/api/reporting_api.py:185-187` - `evidence_content = self.render_engine.render_evidence_content(...)` (evidence content is signed, branding excluded)

**UI Dashboard:**
- ❌ **CRITICAL:** UI dashboard is NOT signed: `services/ui/backend/main.py:309-489` - All endpoints return JSON (no signatures, no hashes)
- ❌ **CRITICAL:** UI dashboard responses are NOT cryptographically verifiable: `services/ui/backend/main.py:309-489` - No signatures, no hashes, no cryptographic verification

**What Hashes Exist:**

**Signed Reports:**
- ✅ Content hash exists: `signed-reporting/api/reporting_api.py:192` - `content_hash = self.render_hasher.hash_content(evidence_content)` (SHA256 hash of evidence content)
- ✅ Hash covers evidence content only: `signed-reporting/api/reporting_api.py:185-187` - `evidence_content = self.render_engine.render_evidence_content(...)` (branding excluded from hash)

**UI Dashboard:**
- ❌ **CRITICAL:** No hashes exist: `services/ui/backend/main.py:309-489` - No hashes in API responses
- ❌ **CRITICAL:** Dashboard responses are NOT hashed: `services/ui/backend/main.py:309-489` - No content hashes, no integrity verification

**Whether Hashes Cover Unverifiable Inputs:**

**Signed Reports:**
- ⚠️ **ISSUE:** Hashes cover unverifiable inputs:
  - `signed-reporting/api/reporting_api.py:161-176` - Reports read from Explanation Assembly (which depends on incidents, AI outputs)
  - `signed-reporting/api/reporting_api.py:180` - Reports use `incident_snapshot_time` (but incidents themselves are non-deterministic per File 07: FAIL)
  - ⚠️ **ISSUE:** Hashes cover unverifiable inputs (reports depend on non-deterministic incidents, AI outputs, timelines)

**UI Dashboard:**
- ❌ **CRITICAL:** No hashes exist (cannot determine if hashes cover unverifiable inputs)

**Verdict: PARTIAL**

**Justification:**
- Reports are signed and hashed (ed25519 signature, SHA256 content hash)
- Reports have content hash (SHA256 hash of evidence content, branding excluded)
- **CRITICAL:** UI dashboard is NOT signed (no signatures, no hashes, no cryptographic verification)
- **ISSUE:** Hashes cover unverifiable inputs (reports depend on non-deterministic incidents, AI outputs, timelines)

---

### 4. Chain-of-Custody

**Can Dashboard Output Be Reproduced:**

**UI Dashboard:**
- ❌ **CRITICAL:** Dashboard output cannot be reproduced:
  - `services/ui/backend/views.sql:12-25` - `v_active_incidents` view reads from `incidents` table (which is non-deterministic per File 07: FAIL)
  - `services/ui/backend/views.sql:35-48` - `v_incident_timeline` view reads from `incident_stages` table (which depends on non-deterministic ingested_at per File 07: FAIL)
  - `validation/07-correlation-engine.md:527` - "Same evidence set may produce different incident graph if processed in different order"
  - ❌ **CRITICAL:** Dashboard output cannot be reproduced (depends on non-deterministic incidents, timelines)

**Signed Reports:**
- ⚠️ **ISSUE:** Reports may not be reproducible:
  - `signed-reporting/api/reporting_api.py:161-176` - Reports read from Explanation Assembly (which depends on incidents, AI outputs)
  - `validation/07-correlation-engine.md:527` - "Same evidence set may produce different incident graph if processed in different order"
  - `validation/08-ai-core-ml-shap.md:445` - "AI outputs can be recomputed later — **FAIL**"
  - ⚠️ **ISSUE:** Reports may not be reproducible (depends on non-deterministic incidents, AI outputs)

**Can Dashboard Output Be Verified:**

**UI Dashboard:**
- ❌ **CRITICAL:** Dashboard output cannot be verified:
  - `services/ui/backend/main.py:309-489` - No signatures, no hashes, no cryptographic verification
  - ❌ **CRITICAL:** Dashboard output cannot be verified (no cryptographic verification)

**Signed Reports:**
- ✅ Reports can be verified: `signed-reporting/cli/verify_report.py:76-78` - `verifier.verify_signature(rendered_content, signature)` (signature verification)
- ✅ Content hash can be verified: `signed-reporting/cli/verify_report.py:68-72` - `content_hash = hasher.hash_content(rendered_content)` (content hash verification)
- ⚠️ **ISSUE:** Verification depends on unverifiable inputs:
  - Reports depend on incidents (which are non-deterministic per File 07: FAIL)
  - Reports depend on AI outputs (which cannot be re-derived per File 08: FAIL)
  - ⚠️ **ISSUE:** Verification depends on unverifiable inputs (cannot verify if underlying data is non-deterministic)

**Can Dashboard Output Be Defended in Court:**

**UI Dashboard:**
- ❌ **CRITICAL:** Dashboard output cannot be defended in court:
  - `services/ui/backend/main.py:309-489` - No signatures, no hashes, no cryptographic verification
  - `validation/07-correlation-engine.md:527` - "Same evidence set may produce different incident graph if processed in different order"
  - ❌ **CRITICAL:** Dashboard output cannot be defended in court (no cryptographic verification, depends on non-deterministic data)

**Signed Reports:**
- ⚠️ **ISSUE:** Reports may not be defensible in court:
  - `signed-reporting/README.md:7` - Claims "court-admissible, regulator-verifiable reports"
  - `validation/07-correlation-engine.md:527` - "Same evidence set may produce different incident graph if processed in different order"
  - `validation/08-ai-core-ml-shap.md:445` - "AI outputs can be recomputed later — **FAIL**"
  - ⚠️ **ISSUE:** Reports may not be defensible in court (depends on non-deterministic incidents, AI outputs, cannot be reproduced)

**Or Is It Presentation-Only:**

**UI Dashboard:**
- ❌ **CRITICAL:** UI dashboard is presentation-only:
  - `services/ui/backend/main.py:309-489` - No signatures, no hashes, no cryptographic verification
  - `services/ui/backend/main.py:309-489` - Returns JSON responses (presentation format, not evidence format)
  - ❌ **CRITICAL:** UI dashboard is presentation-only (no cryptographic verification, no evidence-grade guarantees)

**Signed Reports:**
- ⚠️ **ISSUE:** Reports may be presentation-only:
  - Reports are signed and hashed, but depend on non-deterministic upstream components
  - Reports cannot be reproduced if underlying data is non-deterministic
  - ⚠️ **ISSUE:** Reports may be presentation-only (signed presentation of unverifiable data)

**Verdict: FAIL**

**Justification:**
- **CRITICAL:** Dashboard output cannot be reproduced (depends on non-deterministic incidents, timelines)
- **CRITICAL:** Dashboard output cannot be verified (no signatures, no hashes, no cryptographic verification)
- **CRITICAL:** Dashboard output cannot be defended in court (no cryptographic verification, depends on non-deterministic data)
- **CRITICAL:** UI dashboard is presentation-only (no evidence-grade guarantees)
- **ISSUE:** Reports may not be reproducible (depends on non-deterministic incidents, AI outputs)
- **ISSUE:** Verification depends on unverifiable inputs (cannot verify if underlying data is non-deterministic)
- **ISSUE:** Reports may not be defensible in court (depends on non-deterministic incidents, AI outputs, cannot be reproduced)
- **ISSUE:** Reports may be presentation-only (signed presentation of unverifiable data)

---

### 5. Operator Risk

**Whether Dashboards May Mislead Operators:**

**UI Dashboard:**
- ❌ **CRITICAL:** Dashboards may mislead operators:
  - `services/ui/backend/views.sql:17` - Displays `confidence_score AS confidence` (implies confidence is stable, but it is non-deterministic per File 07: FAIL)
  - `services/ui/backend/views.sql:39` - Displays `transitioned_at` (implies timeline is stable, but it is non-deterministic per File 07: FAIL)
  - `services/ui/backend/views.sql:14` - Displays `incident_id` (implies incident is stable, but it is non-deterministic per File 07: FAIL)
  - ❌ **CRITICAL:** Dashboards may mislead operators (displays non-deterministic data as if it were stable)

**Signed Reports:**
- ❌ **CRITICAL:** Reports may mislead operators:
  - `signed-reporting/README.md:7` - Claims "court-admissible, regulator-verifiable reports" (implies reports are evidence-grade, but depend on non-deterministic upstream components)
  - `signed-reporting/README.md:116` - Claims "**Deterministic**: Same inputs → same outputs (reproducible)" (but inputs are non-deterministic per File 07: FAIL)
  - ❌ **CRITICAL:** Reports may mislead operators (claims evidence-grade guarantees, but depends on non-deterministic upstream components)

**Whether They Imply Guarantees That Do Not Exist:**

**UI Dashboard:**
- ❌ **CRITICAL:** Dashboards imply guarantees that do not exist:
  - `services/ui/backend/views.sql:17` - Displays `confidence_score AS confidence` (implies confidence is stable, but it is non-deterministic)
  - `services/ui/backend/views.sql:39` - Displays `transitioned_at` (implies timeline is stable, but it is non-deterministic)
  - `services/ui/backend/views.sql:14` - Displays `incident_id` (implies incident is stable, but it is non-deterministic)
  - ❌ **CRITICAL:** Dashboards imply guarantees that do not exist (displays non-deterministic data as if it were stable)

**Signed Reports:**
- ❌ **CRITICAL:** Reports imply guarantees that do not exist:
  - `signed-reporting/README.md:7` - Claims "court-admissible, regulator-verifiable reports" (implies reports are evidence-grade, but depend on non-deterministic upstream components)
  - `signed-reporting/README.md:116` - Claims "**Deterministic**: Same inputs → same outputs (reproducible)" (but inputs are non-deterministic)
  - `signed-reporting/README.md:114` - Claims "**Verifiable**: Offline verification without RansomEye system" (but cannot verify if underlying data is non-deterministic)
  - ❌ **CRITICAL:** Reports imply guarantees that do not exist (claims evidence-grade guarantees, but depends on non-deterministic upstream components)

**Verdict: FAIL**

**Justification:**
- **CRITICAL:** Dashboards may mislead operators (displays non-deterministic data as if it were stable)
- **CRITICAL:** Dashboards imply guarantees that do not exist (confidence, timeline, incident stability)
- **CRITICAL:** Reports may mislead operators (claims evidence-grade guarantees, but depends on non-deterministic upstream components)
- **CRITICAL:** Reports imply guarantees that do not exist (court-admissible, deterministic, verifiable claims)

---

## DETERMINISM & HASH STABILITY ANALYSIS

### Hash Stability Requirements

**For reports to have stable hashes, the following must be true:**

1. **Same incident snapshot → same hash** — Same incident snapshot must produce same hash
2. **Same inputs → same hash** — Same inputs must produce same hash
3. **Hash covers verifiable inputs only** — Hash must not cover unverifiable inputs

### Current Platform State

**Binding Evidence from File 07:**
- ❌ **CRITICAL:** Same evidence set → different incidents: `validation/07-correlation-engine.md:527` - "Same evidence set may produce different incident graph if processed in different order"
- ❌ **CRITICAL:** Reprocessing produces different incidents: `validation/07-correlation-engine.md:310` - "Reprocessing same raw_events with different `ingested_at` values may produce different incidents or different state transitions"

**Binding Evidence from File 08:**
- ❌ **CRITICAL:** AI outputs cannot be re-derived: `validation/08-ai-core-ml-shap.md:445` - "AI outputs can be recomputed later — **FAIL**"
- ❌ **CRITICAL:** Non-deterministic inputs break audit trails: `validation/08-ai-core-ml-shap.md:446` - "Non-deterministic inputs do NOT break audit trails — **FAIL**"

**Evidence:**
- ✅ Reports use incident snapshot time: `signed-reporting/api/reporting_api.py:180` - `incident_snapshot_time = self._get_incident_snapshot_time(incident_id)` (uses incident snapshot time, not system time)
- ✅ Reports hash evidence content only: `signed-reporting/api/reporting_api.py:185-187` - `evidence_content = self.render_engine.render_evidence_content(...)` (branding excluded from hash)
- ⚠️ **ISSUE:** Reports depend on non-deterministic incidents:
  - `signed-reporting/api/reporting_api.py:161-176` - Reports read from Explanation Assembly (which depends on incidents)
  - `validation/07-correlation-engine.md:527` - "Same evidence set may produce different incident graph if processed in different order"
  - ⚠️ **ISSUE:** Same incident snapshot may not exist (incidents are non-deterministic, same evidence → different incidents)

### Hash Stability Verdict: FAIL

**Justification:**
- Reports use incident snapshot time (uses incident snapshot time, not system time)
- Reports hash evidence content only (branding excluded from hash)
- **CRITICAL:** Reports depend on non-deterministic incidents (same evidence → different incidents on replay)
- **CRITICAL:** Same incident snapshot may not exist (incidents are non-deterministic, cannot guarantee same incident snapshot)
- **CRITICAL:** Hash stability is broken (cannot guarantee same inputs → same hash if inputs are non-deterministic)

---

## CRYPTOGRAPHIC COVERAGE ANALYSIS

### What Is Cryptographically Covered

**Signed Reports:**
- ✅ Evidence content is signed: `signed-reporting/api/reporting_api.py:196-198` - `signature = self.report_signer.sign_content(evidence_content)` (ed25519 signature)
- ✅ Evidence content is hashed: `signed-reporting/api/reporting_api.py:192` - `content_hash = self.render_hasher.hash_content(evidence_content)` (SHA256 hash)
- ✅ Branding is excluded from hash: `signed-reporting/api/reporting_api.py:185-187` - `evidence_content = self.render_engine.render_evidence_content(...)` (branding excluded)

**UI Dashboard:**
- ❌ **CRITICAL:** Nothing is cryptographically covered: `services/ui/backend/main.py:309-489` - No signatures, no hashes, no cryptographic coverage

### What Is NOT Cryptographically Covered

**Signed Reports:**
- ⚠️ **ISSUE:** Upstream data is NOT cryptographically covered:
  - Reports depend on incidents (which are non-deterministic per File 07: FAIL)
  - Reports depend on AI outputs (which cannot be re-derived per File 08: FAIL)
  - Reports depend on timelines (which depend on non-deterministic ingested_at per File 07: FAIL)
  - ⚠️ **ISSUE:** Upstream data is NOT cryptographically covered (incidents, AI outputs, timelines are not signed or hashed)

**UI Dashboard:**
- ❌ **CRITICAL:** Nothing is cryptographically covered: `services/ui/backend/main.py:309-489` - No signatures, no hashes, no cryptographic coverage

### Cryptographic Coverage Verdict: PARTIAL

**Justification:**
- Reports are signed and hashed (ed25519 signature, SHA256 content hash)
- Branding is excluded from hash (branding excluded from hash domain)
- **CRITICAL:** UI dashboard is NOT cryptographically covered (no signatures, no hashes)
- **ISSUE:** Upstream data is NOT cryptographically covered (incidents, AI outputs, timelines are not signed or hashed)
- **ISSUE:** Cryptographic coverage is incomplete (reports are signed, but depend on unsigned upstream data)

---

## LEGAL & AUDIT ADMISSIBILITY

### Legal Admissibility Requirements

**For dashboards/reports to be legally admissible, the following must be true:**

1. **Be defended in court** — Evidence must be cryptographically verifiable and tamper-proof
2. **Be reproduced months later** — Evidence must be reproducible from stored data
3. **Be cryptographically verified** — Evidence must have cryptographic signatures and hashes

### Current Platform State

**Binding Evidence from File 07:**
- ❌ **CRITICAL:** Incidents cannot be reproduced: `validation/07-correlation-engine.md:527` - "Same evidence set may produce different incident graph if processed in different order"
- ❌ **CRITICAL:** Reprocessing produces different incidents: `validation/07-correlation-engine.md:310` - "Reprocessing same raw_events with different `ingested_at` values may produce different incidents or different state transitions"

**Binding Evidence from File 08:**
- ❌ **CRITICAL:** AI outputs cannot be re-derived: `validation/08-ai-core-ml-shap.md:445` - "AI outputs can be recomputed later — **FAIL**"
- ❌ **CRITICAL:** Audit trails are broken: `validation/08-ai-core-ml-shap.md:446` - "Non-deterministic inputs do NOT break audit trails — **FAIL**"

**Binding Evidence from File 16:**
- ❌ **CRITICAL:** E2E validation is NOT VALID: `validation/16-end-to-end-threat-scenarios.md` - "End-to-end threat scenario validation is **NOT VALID** given the current platform state"
- ❌ **CRITICAL:** E2E validation cannot produce valid evidence: `validation/16-end-to-end-threat-scenarios.md` - "E2E threat scenario execution would NOT produce valid, auditable, trustworthy evidence"

**Evidence:**
- ✅ Reports are signed: `signed-reporting/api/reporting_api.py:196-198` - `signature = self.report_signer.sign_content(evidence_content)` (ed25519 signature)
- ✅ Reports have content hash: `signed-reporting/api/reporting_api.py:192` - `content_hash = self.render_hasher.hash_content(evidence_content)` (SHA256 hash)
- ⚠️ **ISSUE:** Reports depend on non-deterministic upstream components (incidents, AI outputs, timelines)

### Legal Admissibility Verdict: FAIL

**Justification:**
- Reports are signed and hashed (ed25519 signature, SHA256 content hash)
- **CRITICAL:** Evidence cannot be defended in court — incidents cannot be reproduced, AI outputs cannot be re-derived, audit trails are broken
- **CRITICAL:** Evidence cannot be reproduced months later — same evidence → different incidents on replay, AI outputs cannot be re-derived
- **CRITICAL:** Evidence cannot be cryptographically verified — upstream data is not signed or hashed, reports depend on unverifiable inputs
- **CRITICAL:** E2E validation is NOT VALID — E2E validation cannot produce valid evidence, reports depend on invalid E2E validation

---

## WHAT IS EXPLICITLY NOT ASSUMED

- **NOT ASSUMED:** That incidents are stable (they are validated as non-deterministic)
- **NOT ASSUMED:** That timelines are stable (they are validated as non-deterministic)
- **NOT ASSUMED:** That confidence scores are stable (they are validated as non-deterministic)
- **NOT ASSUMED:** That AI outputs are reproducible (they are validated as non-reproducible)
- **NOT ASSUMED:** That reports are evidence-grade (they are validated as potentially presentation-only)
- **NOT ASSUMED:** That dashboards produce valid evidence (they are validated as presentation-only)
- **NOT ASSUMED:** That upstream components are deterministic (they are validated as non-deterministic)

---

## EVIDENCE REQUIRED

For each validation area:
- File and line numbers from binding validation files (01-17)
- Explicit citation of upstream failures
- Explicit citation of determinism failures
- Explicit citation of cryptographic coverage gaps
- Explicit citation of legal admissibility failures

---

## GA VERDICT

### Section-by-Section Verdicts

1. **Evidence Definition:** PARTIAL
   - Dashboards/reports claim to present evidence (incidents, timelines, confidence scores, AI insights)
   - Evidence is derived from non-deterministic sources (incidents are non-deterministic, timelines depend on non-deterministic ingested_at, AI outputs cannot be re-derived)
   - **ISSUE:** Evidence cannot be verified as authentic (depends on non-deterministic upstream components)

2. **Determinism Dependency:** FAIL
   - Dashboards assume stable incident IDs, timelines, confidence scores
   - **CRITICAL:** Incident IDs are NOT stable upstream (same evidence → different incidents on replay)
   - **CRITICAL:** Timelines are NOT stable upstream (state transition timestamps use NOW(), event ordering depends on ingested_at)
   - **CRITICAL:** Confidence scores are NOT stable upstream (confidence accumulation order depends on processing order, same evidence → different confidence)
   - **CRITICAL:** Assumptions are invalid (all stability assumptions are invalid)

3. **Cryptographic Validity:** PARTIAL
   - Reports are signed and hashed (ed25519 signature, SHA256 content hash)
   - Reports have content hash (SHA256 hash of evidence content, branding excluded)
   - **CRITICAL:** UI dashboard is NOT signed (no signatures, no hashes, no cryptographic verification)
   - **ISSUE:** Hashes cover unverifiable inputs (reports depend on non-deterministic incidents, AI outputs, timelines)
   - **ISSUE:** Cryptographic coverage is incomplete (reports are signed, but depend on unsigned upstream data)

4. **Chain-of-Custody:** FAIL
   - **CRITICAL:** Dashboard output cannot be reproduced (depends on non-deterministic incidents, timelines)
   - **CRITICAL:** Dashboard output cannot be verified (no signatures, no hashes, no cryptographic verification)
   - **CRITICAL:** Dashboard output cannot be defended in court (no cryptographic verification, depends on non-deterministic data)
   - **CRITICAL:** UI dashboard is presentation-only (no evidence-grade guarantees)
   - **ISSUE:** Reports may not be reproducible (depends on non-deterministic incidents, AI outputs)
   - **ISSUE:** Verification depends on unverifiable inputs (cannot verify if underlying data is non-deterministic)
   - **ISSUE:** Reports may not be defensible in court (depends on non-deterministic incidents, AI outputs, cannot be reproduced)
   - **ISSUE:** Reports may be presentation-only (signed presentation of unverifiable data)

5. **Operator Risk:** FAIL
   - **CRITICAL:** Dashboards may mislead operators (displays non-deterministic data as if it were stable)
   - **CRITICAL:** Dashboards imply guarantees that do not exist (confidence, timeline, incident stability)
   - **CRITICAL:** Reports may mislead operators (claims evidence-grade guarantees, but depends on non-deterministic upstream components)
   - **CRITICAL:** Reports imply guarantees that do not exist (court-admissible, deterministic, verifiable claims)

### Overall Verdict: **NOT VALID**

**Justification:**
- **CRITICAL:** 2 out of 5 validation areas are FAIL
- **CRITICAL:** 2 out of 5 validation areas are PARTIAL (not fully valid)
- **CRITICAL:** Determinism dependencies are invalid (all stability assumptions are invalid)
- **CRITICAL:** Chain-of-custody is broken (cannot be reproduced, verified, or defended in court)
- **CRITICAL:** Operator risk is high (dashboards/reports may mislead operators, imply guarantees that do not exist)

**Explicit Statement:** Reporting and dashboards are **NOT VALID** for producing evidence-grade output given the current platform state. Dashboards are **presentation-only** (not evidence-grade). Reports are **signed presentation of unverifiable data** (not evidence-grade).

**Reasons Reporting/Dashboards Are NOT VALID:**

1. **Upstream Data Is Non-Deterministic:**
   - Incidents are non-deterministic (`validation/07-correlation-engine.md:527` - "Same evidence set may produce different incident graph")
   - Timelines are non-deterministic (`validation/07-correlation-engine.md:539` - "State transition timestamps use `NOW()`")
   - Confidence scores are non-deterministic (`validation/07-correlation-engine.md:533` - "Confidence accumulation order depends on processing order")
   - AI outputs cannot be re-derived (`validation/08-ai-core-ml-shap.md:445` - "AI outputs can be recomputed later — **FAIL**")

2. **Dashboards Are Presentation-Only:**
   - No signatures, no hashes, no cryptographic verification (`services/ui/backend/main.py:309-489`)
   - Displays non-deterministic data as if it were stable (`services/ui/backend/views.sql:17,39,14`)
   - Cannot be reproduced, verified, or defended in court

3. **Reports Depend on Unverifiable Inputs:**
   - Reports depend on non-deterministic incidents (`signed-reporting/api/reporting_api.py:161-176`)
   - Reports depend on non-deterministic AI outputs (`signed-reporting/api/reporting_api.py:161-176`)
   - Reports depend on non-deterministic timelines (`signed-reporting/api/reporting_api.py:180`)
   - Reports are signed, but sign unverifiable data

4. **Claims Exceed Guarantees:**
   - Reports claim "court-admissible" (`signed-reporting/README.md:7`) but depend on non-deterministic upstream components
   - Reports claim "deterministic" (`signed-reporting/README.md:116`) but inputs are non-deterministic
   - Reports claim "verifiable" (`signed-reporting/README.md:114`) but cannot verify if underlying data is non-deterministic

5. **E2E Validation Is NOT VALID:**
   - E2E validation is NOT VALID (`validation/16-end-to-end-threat-scenarios.md` - "E2E threat scenario validation is **NOT VALID**")
   - Reports depend on E2E validation results (which are NOT VALID)

---

## UPSTREAM IMPACT STATEMENT

**Binding Results from Validation Files 01-17:**
- Validation Step 3 (`validation/03-secure-bus-interservice-trust.md`): Inter-service trust (binding, GA verdict: **FAIL**)
- Validation Step 4 (`validation/04-ingest-normalization-db-write.md`): Ingest determinism (binding, GA verdict: **FAIL**)
- Validation Step 7 (`validation/07-correlation-engine.md`): Correlation determinism (binding, GA verdict: **FAIL**)
- Validation Step 8 (`validation/08-ai-core-ml-shap.md`): AI determinism (binding, GA verdict: **FAIL**)
- Validation Step 9 (`validation/09-policy-engine-command-authority.md`): Policy authority (binding, GA verdict: **PARTIAL**)
- Validation Step 14 (`validation/14-ui-api-access-control.md`): UI authentication (binding, GA verdict: **FAIL**)
- Validation Step 16 (`validation/16-end-to-end-threat-scenarios.md`): E2E validation validity (binding, GA verdict: **NOT VALID**)
- Validation Step 17 (`validation/17-end-to-end-credential-chain.md`): Credential chain (binding, GA verdict: **FAIL**)

**Upstream Failures Invalidate Reporting/Dashboards:**
- If incidents are non-deterministic (File 07: FAIL), dashboards/reports cannot display stable incident data
- If timelines are non-deterministic (File 07: FAIL), dashboards/reports cannot display stable timeline data
- If confidence scores are non-deterministic (File 07: FAIL), dashboards/reports cannot display stable confidence data
- If AI outputs cannot be re-derived (File 08: FAIL), dashboards/reports cannot display verifiable AI insights
- If E2E validation is NOT VALID (File 16: NOT VALID), reports cannot claim evidence-grade guarantees

---

## DOWNSTREAM IMPACT STATEMENT

**Downstream Dependencies:**
- Operators depend on dashboards/reports for incident visibility (downstream dependency)
- Courts/regulators depend on reports for legal admissibility (downstream dependency)
- Auditors depend on reports for audit trails (downstream dependency)

**Reporting/Dashboard Failures Impact:**
- If dashboards are presentation-only, operators may make decisions based on unverifiable data
- If reports are not evidence-grade, courts/regulators cannot use them as evidence
- If reports cannot be reproduced, auditors cannot verify audit trails

---

**Validation Date:** 2025-01-13
**Validator:** Lead Validator & Compliance Auditor
**GA Verdict:** **NOT VALID**

**Explicit Statement:** Reporting and dashboards are **NOT VALID** for producing evidence-grade output given the current platform state. Dashboards are **presentation-only** (not evidence-grade). Reports are **signed presentation of unverifiable data** (not evidence-grade). Dashboards and reports should NOT be used as evidence until upstream determinism and trust boundary failures are resolved.
