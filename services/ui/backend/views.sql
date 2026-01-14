-- RansomEye v1.0 SOC UI - Read-Only Views
-- AUTHORITATIVE: Read-only SQL views for SOC UI
-- PostgreSQL 14+ compatible
-- Phase 8 requirement: UI must NOT query base tables, UI must read from views only

-- ============================================================================
-- V_ACTIVE_INCIDENTS
-- ============================================================================
-- Read-only view of active (unresolved) incidents
-- Phase 8 requirement: UI reads from views only, not base tables

CREATE OR REPLACE VIEW v_active_incidents AS
SELECT 
    incident_id,
    machine_id,
    current_stage AS stage,
    confidence_score AS confidence,
    first_observed_at AS created_at,
    last_observed_at,
    total_evidence_count,
    title,
    description
FROM incidents
WHERE resolved = FALSE
ORDER BY first_observed_at DESC;

COMMENT ON VIEW v_active_incidents IS 'Read-only view of active (unresolved) incidents. UI reads from this view only, not base tables.';

-- ============================================================================
-- V_INCIDENT_TIMELINE
-- ============================================================================
-- Read-only view of incident stage transitions (timeline)
-- Phase 8 requirement: UI reads from views only, not base tables

CREATE OR REPLACE VIEW v_incident_timeline AS
SELECT 
    incident_id,
    to_stage AS stage,
    transitioned_at,
    from_stage,
    transitioned_by,
    transition_reason,
    evidence_count_at_transition,
    confidence_score_at_transition
FROM incident_stages
ORDER BY incident_id, transitioned_at ASC;

COMMENT ON VIEW v_incident_timeline IS 'Read-only view of incident stage transitions (timeline). UI reads from this view only, not base tables.';

-- ============================================================================
-- V_INCIDENT_EVIDENCE_SUMMARY
-- ============================================================================
-- Read-only view of evidence summary per incident
-- Phase 8 requirement: UI reads from views only, not base tables

CREATE OR REPLACE VIEW v_incident_evidence_summary AS
SELECT 
    incident_id,
    COUNT(*) AS evidence_count,
    COUNT(DISTINCT evidence_type) AS evidence_type_count,
    MAX(observed_at) AS last_evidence_at,
    MIN(observed_at) AS first_evidence_at
FROM evidence
GROUP BY incident_id;

COMMENT ON VIEW v_incident_evidence_summary IS 'Read-only view of evidence summary per incident. UI reads from this view only, not base tables.';

-- ============================================================================
-- V_POLICY_RECOMMENDATIONS
-- ============================================================================
-- Read-only view of policy recommendations
-- Phase 8 requirement: UI reads from views only, not base tables
-- Phase 8 minimal: Policy recommendations stored in files, view reads from JSON files
-- Note: For Phase 8 minimal, this view is a placeholder (policy decisions are file-based)
-- In production, this would read from policy_decisions table

CREATE OR REPLACE VIEW v_policy_recommendations AS
SELECT 
    NULL::UUID AS incident_id,
    NULL::VARCHAR AS recommended_action,
    NULL::BOOLEAN AS simulation_mode,
    NULL::TIMESTAMPTZ AS created_at
WHERE FALSE;  -- Empty view (Phase 8 minimal: policy decisions are file-based, not in DB)

COMMENT ON VIEW v_policy_recommendations IS 'Read-only view of policy recommendations. Phase 8 minimal: Empty view (policy decisions are file-based). In production, this would read from policy_decisions table.';

-- ============================================================================
-- V_AI_INSIGHTS
-- ============================================================================
-- Read-only view of AI insights (clusters, novelty scores, SHAP summaries)
-- Phase 8 requirement: UI reads from views only, not base tables

CREATE OR REPLACE VIEW v_ai_insights AS
SELECT DISTINCT
    e.incident_id,
    cm.cluster_id,
    ns.novelty_score,
    se.top_features_contributions AS shap_summary
FROM evidence e
LEFT JOIN cluster_memberships cm ON e.event_id = cm.event_id
LEFT JOIN novelty_scores ns ON e.event_id = ns.event_id
LEFT JOIN shap_explanations se ON e.event_id = se.event_id
WHERE e.incident_id IS NOT NULL;

COMMENT ON VIEW v_ai_insights IS 'Read-only view of AI insights (clusters, novelty scores, SHAP summaries). UI reads from this view only, not base tables. Joins through evidence table to link event_id to incident_id.';

-- ============================================================================
-- V_INCIDENT_DETAIL
-- ============================================================================
-- Read-only view combining incident details with evidence and AI insights
-- Phase 8 requirement: UI reads from views only, not base tables

CREATE OR REPLACE VIEW v_incident_detail AS
SELECT 
    i.incident_id,
    i.machine_id,
    i.current_stage AS stage,
    i.confidence_score AS confidence,
    i.first_observed_at AS created_at,
    i.last_observed_at,
    i.total_evidence_count,
    i.title,
    i.description,
    COALESCE(es.evidence_count, 0) AS evidence_count,
    ai.cluster_id,
    ai.novelty_score,
    ai.shap_summary
FROM incidents i
LEFT JOIN v_incident_evidence_summary es ON i.incident_id = es.incident_id
LEFT JOIN v_ai_insights ai ON i.incident_id = ai.incident_id
WHERE i.resolved = FALSE;

COMMENT ON VIEW v_incident_detail IS 'Read-only view combining incident details with evidence and AI insights. UI reads from this view only, not base tables.';

-- ============================================================================
-- V_INCIDENT_CONTRADICTIONS
-- ============================================================================
-- PHASE 5: Read-only view of contradictions detected for incidents
-- Detects contradictions from incident_stages where confidence decayed without stage progression

CREATE OR REPLACE VIEW v_incident_contradictions AS
SELECT DISTINCT
    i.incident_id,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM incident_stages is1
            JOIN incident_stages is2 ON is1.incident_id = is2.incident_id
            WHERE is1.incident_id = i.incident_id
            AND is2.transitioned_at > is1.transitioned_at
            AND is2.confidence_score_at_transition < is1.confidence_score_at_transition
            AND is2.to_stage = is1.to_stage  -- Stage did not progress despite new evidence
        ) THEN TRUE
        ELSE FALSE
    END AS has_contradiction,
    (
        SELECT COUNT(*) FROM incident_stages
        WHERE incident_id = i.incident_id
        AND transition_reason IS NOT NULL
        AND transition_reason LIKE '%contradiction%'
    ) AS contradiction_count
FROM incidents i
WHERE i.resolved = FALSE;

COMMENT ON VIEW v_incident_contradictions IS 'PHASE 5: Read-only view of contradictions detected for incidents. Detects contradictions from confidence decay without stage progression.';

-- ============================================================================
-- V_INCIDENT_AI_PROVENANCE
-- ============================================================================
-- PHASE 5: Read-only view of AI provenance information for incidents
-- Includes model version, training data hash, SHAP explanations

CREATE OR REPLACE VIEW v_incident_ai_provenance AS
SELECT DISTINCT
    e.incident_id,
    amv.model_version_id,
    amv.model_type,
    amv.model_version_string,
    amv.model_hash_sha256,
    amv.training_data_hash_sha256,
    amv.model_storage_path,
    CASE WHEN se.shap_explanation_full IS NOT NULL THEN TRUE ELSE FALSE END AS has_shap_explanation,
    CASE WHEN se.shap_explanation_full IS NOT NULL THEN se.shap_explanation_full ELSE NULL END AS shap_explanation_full,
    se.top_features_contributions AS shap_top_features
FROM evidence e
LEFT JOIN raw_events re ON e.event_id = re.event_id
LEFT JOIN feature_vectors fv ON re.event_id = fv.event_id
LEFT JOIN ai_model_versions amv ON fv.model_version_id = amv.model_version_id
LEFT JOIN shap_explanations se ON re.event_id = se.event_id
WHERE e.incident_id IS NOT NULL;

COMMENT ON VIEW v_incident_ai_provenance IS 'PHASE 5: Read-only view of AI provenance information for incidents. Includes model version, training data hash, SHAP explanations.';

-- ============================================================================
-- V_INCIDENT_EVIDENCE_QUALITY
-- ============================================================================
-- PHASE 5: Read-only view of evidence quality indicators for incidents
-- Includes completeness, determinism status, contradictions, AI provenance

CREATE OR REPLACE VIEW v_incident_evidence_quality AS
SELECT 
    i.incident_id,
    i.current_stage,
    i.confidence_score,
    COALESCE(es.evidence_count, 0) AS evidence_count,
    -- PHASE 5: Evidence completeness (minimum 3 evidence items for PROBABLE, 5 for CONFIRMED)
    CASE 
        WHEN i.current_stage = 'CONFIRMED' AND COALESCE(es.evidence_count, 0) < 5 THEN 'INCOMPLETE'
        WHEN i.current_stage = 'PROBABLE' AND COALESCE(es.evidence_count, 0) < 3 THEN 'INCOMPLETE'
        WHEN COALESCE(es.evidence_count, 0) = 0 THEN 'NO_EVIDENCE'
        ELSE 'COMPLETE'
    END AS evidence_completeness,
    -- PHASE 5: Determinism status (all timestamps should be deterministic)
    CASE 
        WHEN i.stage_changed_at = i.first_observed_at THEN 'DETERMINISTIC'
        WHEN i.stage_changed_at IS NOT NULL AND i.first_observed_at IS NOT NULL THEN 'DETERMINISTIC'
        ELSE 'UNKNOWN'
    END AS determinism_status,
    -- PHASE 5: Contradiction presence
    COALESCE(ic.has_contradiction, FALSE) AS has_contradiction,
    COALESCE(ic.contradiction_count, 0) AS contradiction_count,
    -- PHASE 5: AI provenance availability
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM v_incident_ai_provenance ap
            WHERE ap.incident_id = i.incident_id
            AND ap.model_version_id IS NOT NULL
            AND ap.training_data_hash_sha256 IS NOT NULL
        ) THEN TRUE
        ELSE FALSE
    END AS has_ai_provenance,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM v_incident_ai_provenance ap
            WHERE ap.incident_id = i.incident_id
            AND ap.has_shap_explanation = TRUE
        ) THEN TRUE
        ELSE FALSE
    END AS has_shap_explanation
FROM incidents i
LEFT JOIN v_incident_evidence_summary es ON i.incident_id = es.incident_id
LEFT JOIN v_incident_contradictions ic ON i.incident_id = ic.incident_id
WHERE i.resolved = FALSE;

COMMENT ON VIEW v_incident_evidence_quality IS 'PHASE 5: Read-only view of evidence quality indicators for incidents. Includes completeness, determinism status, contradictions, AI provenance.';
