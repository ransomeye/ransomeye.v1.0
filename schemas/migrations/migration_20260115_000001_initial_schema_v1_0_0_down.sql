-- RansomEye v1.0 Initial Schema Migration (DOWN)
-- Phase 1: Rollback for v1.0.0 schema bundle

-- Drop tables (reverse dependency order)
DROP TABLE IF EXISTS shap_explanations CASCADE;
DROP TABLE IF EXISTS novelty_scores CASCADE;
DROP TABLE IF EXISTS cluster_memberships CASCADE;
DROP TABLE IF EXISTS clusters CASCADE;
DROP TABLE IF EXISTS feature_vectors CASCADE;
DROP TABLE IF EXISTS ai_model_versions CASCADE;

DROP TABLE IF EXISTS evidence_correlation_patterns CASCADE;
DROP TABLE IF EXISTS evidence CASCADE;
DROP TABLE IF EXISTS incident_stages CASCADE;
DROP TABLE IF EXISTS incidents CASCADE;

DROP TABLE IF EXISTS deception CASCADE;
DROP TABLE IF EXISTS dns CASCADE;
DROP TABLE IF EXISTS dpi_flows CASCADE;

DROP TABLE IF EXISTS health_heartbeat CASCADE;
DROP TABLE IF EXISTS network_intent CASCADE;
DROP TABLE IF EXISTS persistence CASCADE;
DROP TABLE IF EXISTS file_activity CASCADE;
DROP TABLE IF EXISTS process_activity CASCADE;

DROP TABLE IF EXISTS sequence_gaps CASCADE;
DROP TABLE IF EXISTS event_validation_log CASCADE;
DROP TABLE IF EXISTS raw_events CASCADE;

DROP TABLE IF EXISTS component_identity_history CASCADE;
DROP TABLE IF EXISTS component_instances CASCADE;
DROP TABLE IF EXISTS machines CASCADE;

-- Drop retention/partition helper functions
DROP FUNCTION IF EXISTS create_future_partitions(TEXT, INTEGER);
DROP FUNCTION IF EXISTS drop_old_partitions(TEXT, INTEGER);
DROP FUNCTION IF EXISTS create_monthly_partition(TEXT, DATE);

-- Drop enum types
DROP TYPE IF EXISTS cluster_status;
DROP TYPE IF EXISTS feature_vector_status;
DROP TYPE IF EXISTS ai_model_type;
DROP TYPE IF EXISTS confidence_level;
DROP TYPE IF EXISTS evidence_type;
DROP TYPE IF EXISTS incident_stage;
DROP TYPE IF EXISTS deception_type;
DROP TYPE IF EXISTS dns_query_type;
DROP TYPE IF EXISTS dns_record_type;
DROP TYPE IF EXISTS flow_state;
DROP TYPE IF EXISTS flow_direction;
DROP TYPE IF EXISTS network_intent_type;
DROP TYPE IF EXISTS persistence_type;
DROP TYPE IF EXISTS file_activity_type;
DROP TYPE IF EXISTS process_activity_type;
DROP TYPE IF EXISTS event_validation_status;
DROP TYPE IF EXISTS component_state;
DROP TYPE IF EXISTS component_type;

-- Revoke privileges before dropping roles
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM ransomeye_ingest, ransomeye_correlation, ransomeye_ai_core, ransomeye_policy_engine, ransomeye_ui;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM ransomeye_ingest, ransomeye_correlation, ransomeye_ai_core, ransomeye_policy_engine, ransomeye_ui;
REVOKE ALL ON SCHEMA public FROM ransomeye_ingest, ransomeye_correlation, ransomeye_ai_core, ransomeye_policy_engine, ransomeye_ui;

-- Drop roles created for service access
DROP ROLE IF EXISTS ransomeye_ui;
DROP ROLE IF EXISTS ransomeye_policy_engine;
DROP ROLE IF EXISTS ransomeye_ai_core;
DROP ROLE IF EXISTS ransomeye_correlation;
DROP ROLE IF EXISTS ransomeye_ingest;

-- Drop extensions
DROP EXTENSION IF EXISTS pg_trgm;
