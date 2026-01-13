# Validation Step 18 — Reporting, Dashboards & Evidence Exports (PDF / HTML / CSV)

**Component Identity:**
- **Name:** Reporting, Dashboards & Evidence Export System
- **Primary Paths:**
  - `/home/ransomeye/rebuild/signed-reporting/` - Signed Reporting Engine (PDF, HTML, CSV exports)
  - `/home/ransomeye/rebuild/services/ui/` - SOC UI Dashboard (read-only)
  - `/home/ransomeye/rebuild/explanation-assembly/` - Explanation Assembly Engine (source for reports)
  - `/home/ransomeye/rebuild/forensic-summarization/` - Forensic Summarization (evidence generation)
  - `/home/ransomeye/rebuild/services/ai-core/` - AI Core (SHAP explanations)
- **Entry Points:**
  - Signed Reporting: `signed-reporting/cli/generate_report.py` - Report generation CLI
  - Signed Reporting: `signed-reporting/api/reporting_api.py:139` - `generate_report()` API
  - UI Backend: `services/ui/backend/main.py:309` - `GET /api/incidents` endpoint
  - UI Frontend: `services/ui/frontend/src/App.jsx:11` - React component

**Spec Reference:**
- Signed Reporting README: `signed-reporting/README.md`
- Explanation Assembly README: `explanation-assembly/README.md`
- UI README: `services/ui/README.md`
- Validation Step 8: `validation/08-ai-core-ml-shap.md` - SHAP explanations
- Validation Step 14: `validation/14-ui-api-access-control.md` - UI access control

---

## 1. COMPONENT IDENTITY & ROLE

### Evidence

**Reporting Services/Modules:**
- ✅ Signed Reporting Engine: `signed-reporting/README.md:1-50` - "Deterministic, non-authoritative, regulator-grade signed reporting"
- ✅ Explanation Assembly Engine: `explanation-assembly/README.md:1-23` - "Human-facing explanation assembly from existing explanation fragments"
- ✅ Forensic Summarization: `forensic-summarization/README.md:49-126` - "Forensic summarization for incidents"
- ✅ UI Dashboard: `services/ui/README.md:1-50` - "Minimal read-only SOC UI for Phase 8 proof-of-concept"

**Dashboard Components:**
- ✅ UI Backend: `services/ui/backend/main.py:309-337` - `GET /api/incidents` endpoint (read-only)
- ✅ UI Frontend: `services/ui/frontend/src/App.jsx:11-176` - React component (read-only display)
- ✅ Database Views: `services/ui/backend/views.sql:1-134` - Read-only views (`v_active_incidents`, `v_incident_detail`, etc.)

**Intended Consumers:**
- ✅ SOC Analyst: `explanation-assembly/README.md:38-42` - `SOC_ANALYST` view type
- ✅ Incident Commander: `explanation-assembly/README.md:44-46` - `INCIDENT_COMMANDER` view type
- ✅ Executive: `explanation-assembly/README.md:48-50` - `EXECUTIVE` view type
- ✅ Regulator: `explanation-assembly/README.md:52-54` - `REGULATOR` view type

**Whether Reporting Modifies System State:**
- ✅ **VERIFIED:** Reporting does NOT modify system state:
  - `signed-reporting/api/reporting_api.py:78-88` - "All operations: Read-only access to Explanation Assembly Engine, Read-only access to Audit Ledger, Write ONLY to report_store, Emit audit ledger entries, Never modify source explanations"
  - `signed-reporting/README.md:175-188` - "Explicit Non-Features: This engine MUST NOT: Generate summaries, Rewrite explanations, Hide causality, Add interpretation"
  - ✅ **VERIFIED:** Reporting is read-only (never modifies source data)

**Whether Dashboards Influence Detection or Policy:**
- ✅ **VERIFIED:** Dashboards do NOT influence detection or policy:
  - `services/ui/README.md:34-50` - "UI is READ-ONLY and OBSERVATIONAL ONLY. Read-Only Enforcement: NO database writes, NO base table queries, NO state computation, NO action triggers"
  - `services/ui/frontend/src/App.jsx:158-161` - "Phase 8 requirement: NO buttons that execute actions, NO 'acknowledge', 'resolve', or 'close' buttons, NO edit forms, NO action triggers"
  - ✅ **VERIFIED:** UI is read-only (no influence on detection or policy)

### Verdict: **PASS**

**Justification:**
- Reporting services clearly identified (Signed Reporting, Explanation Assembly, Forensic Summarization, UI Dashboard)
- Dashboard components clearly identified (UI Backend, UI Frontend, Database Views)
- Intended consumers clearly identified (SOC Analyst, Incident Commander, Executive, Regulator)
- Reporting does NOT modify system state (read-only access only)
- Dashboards do NOT influence detection or policy (read-only, observational only)

---

## 2. DATA SOURCE AUTHORITY

### Evidence

**Reports Read from Authoritative Tables Only:**
- ✅ Signed Reporting reads from Explanation Assembly: `signed-reporting/api/reporting_api.py:161-176` - Gets assembled explanation from Explanation Assembly Engine (read-only)
- ✅ Explanation Assembly reads from source systems: `explanation-assembly/README.md:78-88` - "Integration Points: System Explanation Engine (SEE), Alert Engine, UBA Alert Context, Risk Index, KillChain & Forensics, Threat Graph" (all read-only)
- ✅ UI reads from database views only: `services/ui/backend/main.py:251-300` - `query_view()` function verifies view_name is actually a view (not base table)
- ✅ UI views are authoritative: `services/ui/backend/views.sql:1-134` - Views read from authoritative tables (`incidents`, `evidence`, `incident_stages`, `shap_explanations`, etc.)

**No Derived or Cached Data Without Provenance:**
- ✅ Reports are deterministic: `signed-reporting/engine/render_engine.py:42-82` - "Deterministic: Same inputs → same output, No text rewriting, No summarization, No inference, No omission"
- ✅ Content blocks have provenance: `signed-reporting/engine/render_engine.py:118-125` - Content blocks include `source_type`, `source_id`, `content_reference` (full provenance)
- ⚠️ **ISSUE:** UI may display cached data: `services/ui/frontend/src/App.jsx:12-14` - React state (`incidents`, `incidentDetail`) may be stale (no refresh mechanism visible)

**No UI-Side Computation Altering Facts:**
- ✅ UI does NOT compute state: `services/ui/README.md:133` - "NO state computation: UI does not compute or infer state (displays only)"
- ✅ UI displays data as-is: `services/ui/frontend/src/App.jsx:50-173` - React component displays data from API without modification
- ✅ Backend enforces read-only: `services/ui/backend/main.py:262-271` - Verifies view_name is actually a view (not base table), terminates Core if unauthorized

**Consistent Data Views Across Reports:**
- ✅ Reports are deterministic: `signed-reporting/engine/render_engine.py:42-82` - Same inputs → same output
- ✅ Reports are reproducible: `signed-reporting/README.md:116` - "Deterministic: Same inputs → same outputs (reproducible)"
- ⚠️ **ISSUE:** View types may show different data: `explanation-assembly/README.md:38-56` - Different view types (SOC_ANALYST, INCIDENT_COMMANDER, EXECUTIVE, REGULATOR) have different ordering and focus (intentional, but may show different content)

### Verdict: **PARTIAL**

**Justification:**
- Reports read from authoritative sources (Explanation Assembly, Audit Ledger)
- UI reads from authoritative database views
- Reports are deterministic and reproducible
- ⚠️ **ISSUE:** UI may display cached/stale data (React state, no refresh mechanism)
- ⚠️ **ISSUE:** View types intentionally show different data (different ordering and focus per view type)

---

## 3. EVIDENCE INTEGRITY & IMMUTABILITY

### Evidence

**Evidence Snapshots are Immutable:**
- ✅ Reports are immutable: `signed-reporting/storage/report_store.py:18-28` - "Immutable: Records cannot be modified after creation, Append-only: Only additions allowed, no updates or deletes"
- ✅ Report store is append-only: `signed-reporting/storage/report_store.py:40-62` - `store_report()` appends to file (no updates or deletes)
- ✅ No modification methods: `grep` search found no UPDATE or DELETE operations on reports
- ✅ Assembled explanations are immutable: `explanation-assembly/README.md:309` - "Immutable storage: Assembled explanations cannot be modified after creation"

**Hashing/Signing of Reports:**
- ✅ Content hash: `signed-reporting/api/reporting_api.py:184-185` - `content_hash = self.render_hasher.hash_content(rendered_content)` (SHA256)
- ✅ Cryptographic signature: `signed-reporting/api/reporting_api.py:187-191` - `signature = self.report_signer.sign_content(rendered_content)` (ed25519)
- ✅ Hash verification: `signed-reporting/engine/render_hasher.py:40-53` - `verify_content()` method verifies SHA256 hash
- ✅ Signature verification: `signed-reporting/cli/verify_report.py` - CLI tool for signature verification

**Clear Linkage to Incident IDs and Timestamps:**
- ✅ Incident ID linkage: `signed-reporting/api/reporting_api.py:207` - `incident_id` stored in report record
- ✅ Timestamp linkage: `signed-reporting/api/reporting_api.py:214` - `generated_at` timestamp stored in report record
- ✅ Assembled explanation ID linkage: `signed-reporting/api/reporting_api.py:208` - `assembled_explanation_id` stored in report record
- ✅ Audit ledger anchor: `signed-reporting/api/reporting_api.py:216` - `audit_ledger_anchor` links to audit ledger entry

**Evidence Regenerated Differently Without Versioning:**
- ✅ Reports are deterministic: `signed-reporting/engine/render_engine.py:42-82` - Same inputs → same output
- ✅ Reports are reproducible: `signed-reporting/cli/export_report.py:109-112` - Re-renders report deterministically from assembled explanation
- ⚠️ **ISSUE:** No versioning found: No code found for report versioning (reports can be regenerated, but no version tracking)

### Verdict: **PARTIAL**

**Justification:**
- Evidence snapshots are immutable (append-only storage, no updates or deletes)
- Reports are hashed (SHA256) and signed (ed25519)
- Clear linkage to incident IDs and timestamps
- ⚠️ **ISSUE:** No versioning mechanism found (reports can be regenerated, but no version tracking)

---

## 4. EXPLAINABILITY LINKAGE (CRITICAL)

### Evidence

**SHAP Explanations are Included or Referenced:**
- ✅ SHAP stored in database: `services/ai-core/app/db.py:320-366` - `store_shap_explanation()` stores in `shap_explanations` table
- ✅ SHAP linked to incidents: `services/ui/backend/views.sql:93-105` - `v_ai_insights` view joins `shap_explanations` table through `evidence` table
- ✅ SHAP displayed in UI: `services/ui/frontend/src/App.jsx:129-136` - Displays `shap_summary` from `ai_insights`
- ⚠️ **ISSUE:** SHAP not explicitly included in reports: `signed-reporting/engine/render_engine.py:118-125` - Content blocks include `source_type`, `source_id`, `content_reference`, but SHAP linkage not explicit
- ⚠️ **ISSUE:** SHAP linkage unclear: No code found that explicitly links SHAP explanations to report content blocks

**Clear "Why" Narratives Trace Back to Facts:**
- ✅ Content blocks have source references: `signed-reporting/engine/render_engine.py:118-125` - Content blocks include `source_type`, `source_id`, `content_reference` (provenance)
- ✅ Explanation Assembly preserves causality: `explanation-assembly/README.md:175-188` - "Explicit Non-Features: This engine MUST NOT: Hide causality, Add interpretation"
- ⚠️ **ISSUE:** "Why" narratives not explicit: Content blocks reference sources, but explicit "why" narratives not found

**No Opaque Scores Without Explanation:**
- ✅ SHAP provides explanations: `services/ai-core/app/shap_explainer.py:17-105` - `explain_incident_confidence()` generates SHAP explanations
- ✅ SHAP stored with top features: `services/ai-core/app/db.py:336` - Top N features stored as JSONB for quick access
- ⚠️ **ISSUE:** Scores may be opaque: `services/ui/frontend/src/App.jsx:101` - Displays `confidence` score, but SHAP explanation may be missing (conditional display)
- ⚠️ **ISSUE:** SHAP may be missing: `services/ui/frontend/src/App.jsx:129-136` - SHAP summary displayed conditionally (may be null)

**AI Explanations Without Linkage to Incidents:**
- ✅ SHAP linked to incidents via evidence: `services/ui/backend/views.sql:93-105` - `v_ai_insights` view joins `shap_explanations` through `evidence` table (links `event_id` to `incident_id`)
- ⚠️ **ISSUE:** SHAP stored with event_id: `schemas/05_ai_metadata.sql:304` - `shap_explanations.event_id` references `raw_events(event_id)`, not `incidents(incident_id)` directly
- ⚠️ **ISSUE:** Linkage through evidence table: SHAP linked to incidents through `evidence` table join (indirect linkage)

### Verdict: **PARTIAL**

**Justification:**
- SHAP explanations are stored and displayed in UI
- Content blocks have source references (provenance)
- ⚠️ **ISSUE:** SHAP not explicitly included in reports (content blocks reference sources, but SHAP linkage not explicit)
- ⚠️ **ISSUE:** "Why" narratives not explicit (content blocks reference sources, but explicit "why" narratives not found)
- ⚠️ **ISSUE:** Scores may be opaque (confidence scores displayed, but SHAP may be missing)
- ⚠️ **ISSUE:** SHAP linked indirectly (through evidence table, not direct linkage)

---

## 5. EXPORT FORMAT COMPLIANCE (MANDATORY)

### Evidence

**PDF Format Support:**
- ✅ PDF format supported: `signed-reporting/engine/render_engine.py:75-134` - `_render_pdf()` method exists
- ✅ PDF format validated: `signed-reporting/api/reporting_api.py:158` - `if format_type not in ['PDF', 'HTML', 'CSV']` (PDF is valid)
- ⚠️ **ISSUE:** PDF is text representation: `signed-reporting/engine/render_engine.py:98-100` - "For Phase M7, generate a structured text representation. In production, this would use a PDF library (e.g., reportlab). For now, generate deterministic text that can be converted to PDF"

**HTML Format Support:**
- ✅ HTML format supported: `signed-reporting/engine/render_engine.py:136-196` - `_render_html()` method exists
- ✅ HTML format validated: `signed-reporting/api/reporting_api.py:158` - HTML is valid format
- ✅ HTML is complete: `signed-reporting/engine/render_engine.py:150-196` - Generates complete HTML document with header, main content, footer

**CSV Format Support:**
- ✅ CSV format supported: `signed-reporting/engine/render_engine.py:198-237` - `_render_csv()` method exists
- ✅ CSV format validated: `signed-reporting/api/reporting_api.py:158` - CSV is valid format
- ✅ CSV is complete: `signed-reporting/engine/render_engine.py:212-237` - Generates CSV with header row and data rows

**Content Parity Across Formats:**
- ✅ Same content blocks: `signed-reporting/engine/render_engine.py:72-73` - Content blocks sorted deterministically (same for all formats)
- ✅ Same incident ID: `signed-reporting/engine/render_engine.py:70` - Same `incident_id` used for all formats
- ✅ Same view type: `signed-reporting/engine/render_engine.py:68` - Same `view_type` used for all formats
- ⚠️ **ISSUE:** Format-specific rendering: `signed-reporting/engine/render_engine.py:75-80` - Different rendering methods for PDF, HTML, CSV (may have format-specific differences)

**Deterministic Generation:**
- ✅ Deterministic rendering: `signed-reporting/engine/render_engine.py:42-82` - "Deterministic: Same inputs → same output"
- ✅ Deterministic sorting: `signed-reporting/engine/render_engine.py:72-73` - Content blocks sorted by `display_order` (deterministic)
- ✅ Deterministic hashing: `signed-reporting/engine/render_hasher.py:26-38` - SHA256 hashing is deterministic

**No Data Loss Between Formats:**
- ✅ Same content blocks: `signed-reporting/engine/render_engine.py:72-73` - Same content blocks used for all formats
- ⚠️ **ISSUE:** Format-specific structure: `signed-reporting/engine/render_engine.py:75-80` - Different rendering methods may have different structure (PDF text, HTML table, CSV rows)
- ⚠️ **ISSUE:** Format-specific content: PDF uses text lines, HTML uses table, CSV uses rows (structure differs, but content should be same)

**Manual Export Steps Required:**
- ✅ CLI export tool: `signed-reporting/cli/export_report.py:20-165` - CLI tool for exporting reports
- ✅ Programmatic API: `signed-reporting/api/reporting_api.py:139-247` - `generate_report()` API method
- ⚠️ **ISSUE:** Manual steps required: `signed-reporting/cli/export_report.py:83-90` - Requires report_id, store path, assembly store, ledger, signing key (multiple manual steps)

### Verdict: **PARTIAL**

**Justification:**
- All three formats (PDF, HTML, CSV) are supported
- Content parity across formats (same content blocks, incident ID, view type)
- Deterministic generation (same inputs → same output)
- ⚠️ **ISSUE:** PDF is text representation (not actual PDF library, placeholder implementation)
- ⚠️ **ISSUE:** Format-specific structure (different rendering methods may have different structure)
- ⚠️ **ISSUE:** Manual export steps required (CLI tool requires multiple parameters)

---

## 6. ACCESS CONTROL & REDACTION

### Evidence

**Role-Based Access to Reports:**
- ✅ RBAC permissions: `rbac/db/schema.sql:58-62` - Reporting permissions: `report:view`, `report:generate`, `report:export`, `report:view_all`
- ✅ Role-based permissions: `rbac/engine/role_permission_mapper.py:125-194` - Role-permission mappings (SUPER_ADMIN, SECURITY_ANALYST, POLICY_MANAGER, IT_ADMIN, AUDITOR)
- ⚠️ **ISSUE:** RBAC not enforced in reporting API: `signed-reporting/api/reporting_api.py:139-247` - `generate_report()` method does NOT check RBAC permissions
- ⚠️ **ISSUE:** RBAC not enforced in CLI: `signed-reporting/cli/generate_report.py:20-138` - CLI tool does NOT check RBAC permissions

**Redaction of Sensitive Fields:**
- ✅ Redaction engine exists: `llm-summarizer/redaction/redaction_engine.py:23-82` - `RedactionEngine` class for PII redaction
- ✅ Redaction policy: `llm-summarizer/redaction/redaction_policy.py:23-80` - `RedactionPolicy` class with STRICT, BALANCED, FORENSIC modes
- ⚠️ **ISSUE:** Redaction not applied to reports: `signed-reporting/engine/render_engine.py:42-237` - Render engine does NOT apply redaction
- ⚠️ **ISSUE:** Redaction not applied to dashboards: `services/ui/backend/main.py:309-422` - UI endpoints do NOT apply redaction

**Separation Between SOC and Executive Views:**
- ✅ View types exist: `explanation-assembly/README.md:38-56` - `SOC_ANALYST`, `INCIDENT_COMMANDER`, `EXECUTIVE`, `REGULATOR` view types
- ✅ Different ordering per view: `explanation-assembly/README.md:38-56` - Different ordering rules per view type (SOC_ANALYST: CHRONOLOGICAL, EXECUTIVE: RISK_IMPACT)
- ⚠️ **ISSUE:** View type selection not RBAC-enforced: `signed-reporting/api/reporting_api.py:142` - `view_type` parameter accepted without RBAC check
- ⚠️ **ISSUE:** No access control on view types: No code found that restricts view types based on user role

**Hardcoded Redaction Rules:**
- ✅ Redaction policy is configurable: `llm-summarizer/redaction/redaction_policy.py:32-45` - Policy mode (STRICT, BALANCED, FORENSIC) is configurable
- ⚠️ **ISSUE:** Redaction rules are hardcoded: `llm-summarizer/redaction/redaction_policy.py:47-80` - Redaction rules (should_hash_ip, should_hash_hostname, etc.) are hardcoded in policy class
- ⚠️ **ISSUE:** Redaction not applied: Redaction engine exists, but not applied to reports or dashboards

### Verdict: **FAIL**

**Justification:**
- RBAC permissions exist, but NOT enforced in reporting API or CLI
- Redaction engine exists, but NOT applied to reports or dashboards
- View types exist, but view type selection not RBAC-enforced
- Redaction rules are hardcoded (not configurable beyond policy mode)

---

## 7. FAILURE & CONSISTENCY BEHAVIOR

### Evidence

**Behavior on Partial Data Availability:**
- ✅ Missing assembled explanation fails: `signed-reporting/api/reporting_api.py:171-176` - Raises `ReportingAPIError` if assembled explanation not found
- ✅ Missing explanation assembly API fails: `signed-reporting/api/reporting_api.py:162-163` - Raises `ReportingAPIError` if Explanation Assembly API not configured
- ⚠️ **ISSUE:** Partial data may be accepted: `signed-reporting/engine/render_engine.py:118-125` - Content blocks rendered even if some fields are missing (empty strings/defaults used)

**DB Unavailability:**
- ✅ DB connection failure handled: `services/ui/backend/main.py:319-337` - Exception handling with HTTP 500 error (no silent failure)
- ✅ DB connection validation: `services/ui/backend/main.py:322` - `get_db_connection()` validates connection
- ⚠️ **ISSUE:** DB unavailability may cause silent failure: `services/ui/frontend/src/App.jsx:34-37` - Error logged to console, but UI continues (no user-visible error)

**SHAP Artifacts Missing:**
- ✅ SHAP may be null: `services/ui/backend/views.sql:93-105` - `v_ai_insights` view uses LEFT JOIN (SHAP may be null)
- ✅ SHAP displayed conditionally: `services/ui/frontend/src/App.jsx:129-136` - SHAP summary displayed conditionally (may be null)
- ⚠️ **ISSUE:** No warning when SHAP missing: `services/ui/frontend/src/App.jsx:129-136` - SHAP displayed if present, but no warning if missing
- ⚠️ **ISSUE:** Reports may omit SHAP: `signed-reporting/engine/render_engine.py:118-125` - Content blocks rendered, but SHAP linkage not explicit (may be omitted)

**Silent Omission of Data:**
- ⚠️ **ISSUE:** Missing data may be silently omitted: `signed-reporting/engine/render_engine.py:118-125` - Content blocks rendered with empty strings/defaults if fields missing
- ⚠️ **ISSUE:** No status indication: `signed-reporting/api/reporting_api.py:139-247` - Report generation does NOT indicate if data is incomplete
- ⚠️ **ISSUE:** No warning on partial data: Reports generated without warning if some data is missing

**Reports Generated with Incomplete Context:**
- ⚠️ **ISSUE:** Reports may be incomplete: `signed-reporting/engine/render_engine.py:118-125` - Content blocks rendered even if some fields are missing
- ⚠️ **ISSUE:** No completeness check: `signed-reporting/api/reporting_api.py:139-247` - Report generation does NOT check if all required data is present

### Verdict: **FAIL**

**Justification:**
- Missing assembled explanation fails (explicit error)
- DB connection failure handled (HTTP 500 error)
- ⚠️ **ISSUE:** Partial data may be accepted (content blocks rendered with empty strings/defaults)
- ⚠️ **ISSUE:** SHAP missing without warning (SHAP displayed conditionally, no warning if missing)
- ⚠️ **ISSUE:** Silent omission of data (missing fields use empty strings/defaults)
- ⚠️ **ISSUE:** No completeness check (reports generated without checking if all required data is present)

---

## 8. NEGATIVE VALIDATION (MANDATORY)

### Evidence

**Report Alters Incident State:**
- ✅ **PROVEN IMPOSSIBLE:** Reports do NOT alter incident state:
  - `signed-reporting/api/reporting_api.py:78-88` - "All operations: Read-only access to Explanation Assembly Engine, Read-only access to Audit Ledger, Write ONLY to report_store, Emit audit ledger entries, Never modify source explanations"
  - `signed-reporting/README.md:175-188` - "Explicit Non-Features: This engine MUST NOT: Generate summaries, Rewrite explanations, Hide causality"
  - ✅ **VERIFIED:** Reports are read-only (never modify incident state)

**Dashboard Triggers Enforcement:**
- ✅ **PROVEN IMPOSSIBLE:** Dashboard does NOT trigger enforcement:
  - `services/ui/README.md:34-50` - "UI is READ-ONLY and OBSERVATIONAL ONLY. Read-Only Enforcement: NO database writes, NO base table queries, NO state computation, NO action triggers"
  - `services/ui/frontend/src/App.jsx:158-161` - "Phase 8 requirement: NO buttons that execute actions, NO 'acknowledge', 'resolve', or 'close' buttons, NO edit forms, NO action triggers"
  - ✅ **VERIFIED:** UI is read-only (no enforcement triggers)

**Evidence Regenerated Inconsistently:**
- ✅ **PROVEN IMPOSSIBLE:** Evidence is NOT regenerated inconsistently:
  - `signed-reporting/engine/render_engine.py:42-82` - "Deterministic: Same inputs → same output"
  - `signed-reporting/cli/export_report.py:109-112` - Re-renders report deterministically from assembled explanation
  - ✅ **VERIFIED:** Reports are deterministic (same inputs → same output)

**Exports Omit Critical Context Silently:**
- ❌ **CRITICAL:** Exports may omit critical context silently:
  - `signed-reporting/engine/render_engine.py:118-125` - Content blocks rendered with empty strings/defaults if fields missing
  - `signed-reporting/api/reporting_api.py:139-247` - Report generation does NOT check if all required data is present
  - ❌ **CRITICAL:** Reports may omit SHAP explanations (SHAP linkage not explicit)
  - ❌ **CRITICAL:** Reports may omit evidence (content blocks may be incomplete)

### Verdict: **PARTIAL**

**Justification:**
- Reports do NOT alter incident state (read-only)
- Dashboard does NOT trigger enforcement (read-only)
- Evidence is NOT regenerated inconsistently (deterministic)
- ❌ **CRITICAL:** Exports may omit critical context silently (missing fields use empty strings/defaults, no completeness check)

---

## 9. VERDICT & IMPACT

### Section-by-Section Verdicts

1. **Component Identity & Role:** PASS
   - Reporting services and dashboard components clearly identified
   - Reporting does NOT modify system state
   - Dashboards do NOT influence detection or policy

2. **Data Source Authority:** PARTIAL
   - Reports read from authoritative sources
   - ⚠️ **ISSUE:** UI may display cached/stale data
   - ⚠️ **ISSUE:** View types intentionally show different data

3. **Evidence Integrity & Immutability:** PARTIAL
   - Evidence snapshots are immutable
   - Reports are hashed and signed
   - ⚠️ **ISSUE:** No versioning mechanism found

4. **Explainability Linkage (CRITICAL):** PARTIAL
   - SHAP explanations are stored and displayed
   - ⚠️ **ISSUE:** SHAP not explicitly included in reports
   - ⚠️ **ISSUE:** "Why" narratives not explicit
   - ⚠️ **ISSUE:** Scores may be opaque (SHAP may be missing)

5. **Export Format Compliance (MANDATORY):** PARTIAL
   - All three formats (PDF, HTML, CSV) are supported
   - ⚠️ **ISSUE:** PDF is text representation (not actual PDF library)
   - ⚠️ **ISSUE:** Manual export steps required

6. **Access Control & Redaction:** FAIL
   - RBAC permissions exist, but NOT enforced
   - Redaction engine exists, but NOT applied
   - View type selection not RBAC-enforced

7. **Failure & Consistency Behavior:** FAIL
   - Missing data fails (explicit error)
   - ⚠️ **ISSUE:** Partial data may be accepted
   - ⚠️ **ISSUE:** Silent omission of data
   - ⚠️ **ISSUE:** No completeness check

8. **Negative Validation:** PARTIAL
   - Reports do NOT alter incident state
   - Dashboard does NOT trigger enforcement
   - Evidence is NOT regenerated inconsistently
   - ❌ **CRITICAL:** Exports may omit critical context silently

### Overall Verdict: **FAIL**

**Justification:**
- **CRITICAL:** Access control NOT enforced (RBAC permissions exist, but not enforced in reporting API or CLI)
- **CRITICAL:** Redaction NOT applied (redaction engine exists, but not applied to reports or dashboards)
- **CRITICAL:** Exports may omit critical context silently (missing fields use empty strings/defaults, no completeness check)
- **CRITICAL:** SHAP explanations not explicitly included in reports (SHAP linkage not explicit)
- **CRITICAL:** PDF is text representation (not actual PDF library, placeholder implementation)
- **ISSUE:** UI may display cached/stale data (React state, no refresh mechanism)
- **ISSUE:** No versioning mechanism found (reports can be regenerated, but no version tracking)

### Impact if Reporting Layer is Compromised

**CRITICAL IMPACTS:**

1. **Access Control Bypass:**
   - **Impact:** Unauthorized users can generate reports with sensitive data
   - **Evidence:** `signed-reporting/api/reporting_api.py:139-247` - `generate_report()` does NOT check RBAC permissions
   - **Severity:** HIGH (sensitive data exposure)

2. **Redaction Bypass:**
   - **Impact:** Reports may contain PII or sensitive data without redaction
   - **Evidence:** `signed-reporting/engine/render_engine.py:42-237` - Render engine does NOT apply redaction
   - **Severity:** HIGH (PII exposure, regulatory violation)

3. **Incomplete Reports:**
   - **Impact:** Reports may omit critical context (SHAP explanations, evidence) without warning
   - **Evidence:** `signed-reporting/engine/render_engine.py:118-125` - Content blocks rendered with empty strings/defaults if fields missing
   - **Severity:** MEDIUM (misleading reports, incomplete evidence)

4. **View Type Bypass:**
   - **Impact:** Users can generate reports with view types they should not have access to
   - **Evidence:** `signed-reporting/api/reporting_api.py:142` - `view_type` parameter accepted without RBAC check
   - **Severity:** MEDIUM (unauthorized access to executive/regulator views)

### Whether RansomEye Remains Auditable and Defensible

**Verdict: ❌ FAIL**

**Justification:**
- **CRITICAL:** Reports are NOT fully auditable:
  - Access control NOT enforced (unauthorized users can generate reports)
  - Redaction NOT applied (PII may be exposed)
  - Incomplete reports may be generated (missing SHAP, evidence)
- **CRITICAL:** Reports are NOT fully defensible:
  - PDF is text representation (not actual PDF library, may not meet court requirements)
  - SHAP explanations not explicitly included (explainability linkage unclear)
  - No completeness check (reports may omit critical context)
- **CRITICAL:** Regulatory compliance at risk:
  - Redaction NOT applied (regulatory violation risk)
  - Access control NOT enforced (unauthorized access risk)
  - Incomplete reports (evidence integrity risk)

**Recommendations:**
1. **CRITICAL:** Enforce RBAC in reporting API and CLI (check permissions before report generation)
2. **CRITICAL:** Apply redaction to reports and dashboards (use RedactionEngine for PII redaction)
3. **CRITICAL:** Enforce view type access control (restrict view types based on user role)
4. **CRITICAL:** Add completeness check (verify all required data is present before report generation)
5. **CRITICAL:** Explicitly include SHAP explanations in reports (link SHAP to content blocks)
6. **CRITICAL:** Implement actual PDF library (replace text representation with reportlab or similar)
7. **HIGH:** Add report versioning (track report versions for audit trail)
8. **HIGH:** Add data freshness indicators (warn when UI data is stale)
9. **MEDIUM:** Add warning when SHAP missing (explicit indication when explainability data is unavailable)
10. **MEDIUM:** Add status indication for incomplete reports (warn when data is partial)

---

**Validation Date:** 2025-01-13
**Validator:** Lead Validator & Compliance Auditor
**Next Step:** Validation complete (all 18 steps completed)
