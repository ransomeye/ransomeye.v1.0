-- RansomEye v1.0 Database Users & Roles
-- AUTHORITATIVE: Separate database users per service with least-privilege access
-- PostgreSQL 14+ compatible
--
-- PHASE A2 REQUIREMENT: Credential scoping with separate DB users per service
-- This schema creates service-specific database roles and enforces least-privilege access

-- ============================================================================
-- DATABASE ROLES (Service-Specific)
-- ============================================================================
-- Each service has its own database role with least-privilege access

-- Ingest Service Role
-- Required: Write to raw_events, machines, component_instances, event_validation_log
CREATE ROLE ransomeye_ingest LOGIN PASSWORD NULL;
-- Password must be set via ALTER ROLE after creation (no defaults)

-- Correlation Engine Role
-- Required: Write to incidents, incident_stages, evidence
CREATE ROLE ransomeye_correlation LOGIN PASSWORD NULL;
-- Password must be set via ALTER ROLE after creation (no defaults)

-- AI Core Role
-- Required: Write to ai_model_versions, feature_vectors, clusters, cluster_memberships, shap_explanations
CREATE ROLE ransomeye_ai_core LOGIN PASSWORD NULL;
-- Password must be set via ALTER ROLE after creation (no defaults)

-- Policy Engine Role
-- Required: Read-only access (Policy Engine does not write to DB)
CREATE ROLE ransomeye_policy_engine LOGIN PASSWORD NULL;
-- Password must be set via ALTER ROLE after creation (no defaults)

-- UI Backend Role
-- Required: Read-only access (UI is read-only)
CREATE ROLE ransomeye_ui LOGIN PASSWORD NULL;
-- Password must be set via ALTER ROLE after creation (no defaults)

-- ============================================================================
-- GRANT STATEMENTS (Least-Privilege Enforcement)
-- ============================================================================

-- Ingest Service Permissions
-- Write access to: raw_events, machines, component_instances, event_validation_log
GRANT INSERT, SELECT, UPDATE ON TABLE raw_events TO ransomeye_ingest;
GRANT INSERT, SELECT, UPDATE ON TABLE machines TO ransomeye_ingest;
GRANT INSERT, SELECT, UPDATE ON TABLE component_instances TO ransomeye_ingest;
GRANT INSERT, SELECT ON TABLE event_validation_log TO ransomeye_ingest;
GRANT INSERT, SELECT ON TABLE sequence_gaps TO ransomeye_ingest;
-- Read access to: component_identity_history (for identity tracking)
GRANT SELECT ON TABLE component_identity_history TO ransomeye_ingest;
-- Usage on sequences
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ransomeye_ingest;

-- Correlation Engine Permissions
-- Write access to: incidents, incident_stages, evidence
GRANT INSERT, SELECT, UPDATE ON TABLE incidents TO ransomeye_correlation;
GRANT INSERT, SELECT ON TABLE incident_stages TO ransomeye_correlation;
GRANT INSERT, SELECT ON TABLE evidence TO ransomeye_correlation;
-- Read access to: raw_events, machines, component_instances (for correlation)
GRANT SELECT ON TABLE raw_events TO ransomeye_correlation;
GRANT SELECT ON TABLE machines TO ransomeye_correlation;
GRANT SELECT ON TABLE component_instances TO ransomeye_correlation;
-- Usage on sequences
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ransomeye_correlation;

-- AI Core Permissions
-- Write access to: ai_model_versions, feature_vectors, clusters, cluster_memberships, shap_explanations
GRANT INSERT, SELECT, UPDATE ON TABLE ai_model_versions TO ransomeye_ai_core;
GRANT INSERT, SELECT ON TABLE feature_vectors TO ransomeye_ai_core;
GRANT INSERT, SELECT, UPDATE ON TABLE clusters TO ransomeye_ai_core;
GRANT INSERT, SELECT ON TABLE cluster_memberships TO ransomeye_ai_core;
GRANT INSERT, SELECT ON TABLE shap_explanations TO ransomeye_ai_core;
-- Read access to: incidents (for feature extraction)
GRANT SELECT ON TABLE incidents TO ransomeye_ai_core;
-- Usage on sequences
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ransomeye_ai_core;

-- Policy Engine Permissions
-- Read-only access: incidents, evidence (for policy evaluation)
GRANT SELECT ON TABLE incidents TO ransomeye_policy_engine;
GRANT SELECT ON TABLE evidence TO ransomeye_policy_engine;
GRANT SELECT ON TABLE machines TO ransomeye_policy_engine;
GRANT SELECT ON TABLE component_instances TO ransomeye_policy_engine;
-- NO WRITE ACCESS (Policy Engine does not write to DB)

-- UI Backend Permissions
-- Read-only access: All tables for display
GRANT SELECT ON TABLE machines TO ransomeye_ui;
GRANT SELECT ON TABLE component_instances TO ransomeye_ui;
GRANT SELECT ON TABLE component_identity_history TO ransomeye_ui;
GRANT SELECT ON TABLE raw_events TO ransomeye_ui;
GRANT SELECT ON TABLE event_validation_log TO ransomeye_ui;
GRANT SELECT ON TABLE incidents TO ransomeye_ui;
GRANT SELECT ON TABLE incident_stages TO ransomeye_ui;
GRANT SELECT ON TABLE evidence TO ransomeye_ui;
GRANT SELECT ON TABLE ai_model_versions TO ransomeye_ui;
GRANT SELECT ON TABLE feature_vectors TO ransomeye_ui;
GRANT SELECT ON TABLE clusters TO ransomeye_ui;
GRANT SELECT ON TABLE cluster_memberships TO ransomeye_ui;
GRANT SELECT ON TABLE shap_explanations TO ransomeye_ui;
-- NO WRITE ACCESS (UI is read-only)

-- ============================================================================
-- REVOKE STATEMENTS (Explicit Deny)
-- ============================================================================
-- Revoke all privileges from public role (default deny)
REVOKE ALL ON DATABASE ransomeye FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM PUBLIC;

-- Revoke any default privileges that might exist
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON ROLE ransomeye_ingest IS 'Database role for Ingest Service. Write access to raw_events, machines, component_instances, event_validation_log.';
COMMENT ON ROLE ransomeye_correlation IS 'Database role for Correlation Engine. Write access to incidents, incident_stages, evidence. Read access to raw_events for correlation.';
COMMENT ON ROLE ransomeye_ai_core IS 'Database role for AI Core Service. Write access to AI metadata tables. Read access to incidents for feature extraction.';
COMMENT ON ROLE ransomeye_policy_engine IS 'Database role for Policy Engine. Read-only access (Policy Engine does not write to DB).';
COMMENT ON ROLE ransomeye_ui IS 'Database role for UI Backend. Read-only access (UI is read-only).';
