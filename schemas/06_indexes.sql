-- RansomEye v1.0 Index Strategy
-- AUTHORITATIVE: Comprehensive index definitions and strategies
-- PostgreSQL 14+ compatible
-- NOTE: Most indexes are defined inline with table definitions.
-- This file contains additional composite indexes and index strategy documentation.

-- ============================================================================
-- ADDITIONAL COMPOSITE INDEXES
-- ============================================================================
-- Composite indexes for common query patterns not covered by single-column indexes

-- Raw events: Find events by machine and time (common host-centric time-range queries)
CREATE INDEX IF NOT EXISTS idx_raw_events_machine_ingested_at 
    ON raw_events(machine_id, ingested_at DESC);

-- Raw events: Find events by component instance and time (component timeline queries)
CREATE INDEX IF NOT EXISTS idx_raw_events_component_instance_ingested_at 
    ON raw_events(component_instance_id, ingested_at DESC);

-- Raw events: Find events by component and time (component type time-range queries)
CREATE INDEX IF NOT EXISTS idx_raw_events_component_ingested_at 
    ON raw_events(component, ingested_at DESC);

-- Raw events: Find late arrival events by machine (stale host queries)
CREATE INDEX IF NOT EXISTS idx_raw_events_machine_late_arrival 
    ON raw_events(machine_id, late_arrival) 
    WHERE late_arrival = TRUE;

-- Process activity: Find process activity by machine and time (host-centric process timeline)
CREATE INDEX IF NOT EXISTS idx_process_activity_machine_observed_at 
    ON process_activity(machine_id, observed_at DESC);

-- Process activity: Find process activity by PID and time (process lifecycle queries)
CREATE INDEX IF NOT EXISTS idx_process_activity_pid_observed_at 
    ON process_activity(process_pid, observed_at DESC);

-- Process activity: Find parent-child process relationships
CREATE INDEX IF NOT EXISTS idx_process_activity_parent_pid_pid 
    ON process_activity(parent_pid, process_pid) 
    WHERE parent_pid IS NOT NULL;

-- File activity: Find file activity by machine and time (host-centric file timeline)
CREATE INDEX IF NOT EXISTS idx_file_activity_machine_observed_at 
    ON file_activity(machine_id, observed_at DESC);

-- File activity: Find file activity by PID and time (process file activity timeline)
CREATE INDEX IF NOT EXISTS idx_file_activity_pid_observed_at 
    ON file_activity(process_pid, observed_at DESC);

-- File activity: Find file activity by file path (trigram search)
CREATE INDEX IF NOT EXISTS idx_file_activity_file_path_trgm 
    ON file_activity USING gin (file_path gin_trgm_ops);

-- File activity: Find file activity by file path and time (file access timeline)
CREATE INDEX IF NOT EXISTS idx_file_activity_file_path_observed_at 
    ON file_activity(file_path, observed_at DESC);

-- Persistence: Find persistence by machine and time (host-centric persistence timeline)
CREATE INDEX IF NOT EXISTS idx_persistence_machine_observed_at 
    ON persistence(machine_id, observed_at DESC);

-- Persistence: Find enabled persistence by machine (active persistence per host)
CREATE INDEX IF NOT EXISTS idx_persistence_machine_enabled 
    ON persistence(machine_id, enabled) 
    WHERE enabled = TRUE;

-- Network intent: Find network intent by machine and time (host-centric network timeline)
CREATE INDEX IF NOT EXISTS idx_network_intent_machine_observed_at 
    ON network_intent(machine_id, observed_at DESC);

-- Network intent: Find network intent by PID and time (process network timeline)
CREATE INDEX IF NOT EXISTS idx_network_intent_pid_observed_at 
    ON network_intent(process_pid, observed_at DESC);

-- DPI flows: Find flows by machine and time (host-centric flow timeline)
CREATE INDEX IF NOT EXISTS idx_dpi_flows_machine_observed_at 
    ON dpi_flows(machine_id, observed_at DESC) 
    WHERE machine_id IS NOT NULL;

-- DPI flows: Find active flows by local IP and port (flow lookup)
CREATE INDEX IF NOT EXISTS idx_dpi_flows_active_local 
    ON dpi_flows(local_ip, local_port, protocol) 
    WHERE flow_ended_at IS NULL;

-- DPI flows: Find active flows by remote IP and port (flow lookup)
CREATE INDEX IF NOT EXISTS idx_dpi_flows_active_remote 
    ON dpi_flows(remote_ip, remote_port, protocol) 
    WHERE flow_ended_at IS NULL;

-- DNS: Find DNS queries by machine and time (host-centric DNS timeline)
CREATE INDEX IF NOT EXISTS idx_dns_machine_observed_at 
    ON dns(machine_id, observed_at DESC) 
    WHERE machine_id IS NOT NULL;

-- DNS: Find DNS queries by query name and time (domain timeline)
CREATE INDEX IF NOT EXISTS idx_dns_query_name_observed_at 
    ON dns(query_name, observed_at DESC);

-- DNS: Find DNS responses with resolved IPs by client IP (IP-based DNS correlation)
CREATE INDEX IF NOT EXISTS idx_dns_client_ip_observed_at 
    ON dns(client_ip, observed_at DESC);

-- Incidents: Find incidents by machine and stage (host-centric incident queries)
CREATE INDEX IF NOT EXISTS idx_incidents_machine_stage 
    ON incidents(machine_id, current_stage);

-- Incidents: Find unresolved incidents by machine (active incidents per host)
CREATE INDEX IF NOT EXISTS idx_incidents_machine_unresolved 
    ON incidents(machine_id, resolved) 
    WHERE resolved = FALSE;

-- Incidents: Find high-confidence incidents by machine (high-confidence incidents per host)
CREATE INDEX IF NOT EXISTS idx_incidents_machine_confidence 
    ON incidents(machine_id, confidence_score DESC) 
    WHERE confidence_score >= 50.00;

-- Evidence: Find evidence by incident and time (incident evidence timeline)
CREATE INDEX IF NOT EXISTS idx_evidence_incident_observed_at 
    ON evidence(incident_id, observed_at DESC);

-- Evidence: Find evidence by event and evidence type (event evidence analysis)
CREATE INDEX IF NOT EXISTS idx_evidence_event_type 
    ON evidence(event_id, evidence_type);

-- Evidence: Find high-confidence evidence by incident (high-confidence evidence per incident)
CREATE INDEX IF NOT EXISTS idx_evidence_incident_confidence 
    ON evidence(incident_id, confidence_score DESC) 
    WHERE confidence_score >= 50.00;

-- Component instances: Find component instances by machine and state (host component state)
CREATE INDEX IF NOT EXISTS idx_component_instances_machine_state 
    ON component_instances(machine_id, current_state);

-- Component instances: Find stale component instances (stale component detection)
CREATE INDEX IF NOT EXISTS idx_component_instances_state_stale 
    ON component_instances(current_state, last_seen_at) 
    WHERE current_state = 'STALE';

-- Feature vectors: Find feature vectors by model and status (model processing pipeline)
CREATE INDEX IF NOT EXISTS idx_feature_vectors_model_status 
    ON feature_vectors(model_version_id, status);

-- Novelty scores: Find high-novelty events by model (high-novelty events per model)
CREATE INDEX IF NOT EXISTS idx_novelty_scores_model_high_novelty 
    ON novelty_scores(model_version_id, novelty_score DESC) 
    WHERE novelty_score >= 0.8;

-- Cluster memberships: Find cluster memberships by cluster and score (cluster analysis)
CREATE INDEX IF NOT EXISTS idx_cluster_memberships_cluster_score 
    ON cluster_memberships(cluster_id, membership_score DESC) 
    WHERE membership_score IS NOT NULL;

-- ============================================================================
-- INDEX MAINTENANCE
-- ============================================================================
-- Index maintenance strategies and documentation

-- PostgreSQL index types used:
-- - B-tree (default): Most indexes (primary keys, foreign keys, time-based, equality)
-- - GIN (Generalized Inverted Index): Text search (trigram), array queries, JSONB
-- - Partial indexes: WHERE clauses for filtered indexes (e.g., active flows, unresolved incidents)
-- - Composite indexes: Multi-column indexes for common query patterns

-- Index maintenance recommendations:
-- 1. Monitor index bloat using pg_stat_user_indexes
-- 2. REINDEX regularly on high-write tables (raw_events, normalized tables)
-- 3. Analyze tables after bulk inserts (UPDATE STATISTICS)
-- 4. Consider index-only scans for frequently queried columns
-- 5. Monitor unused indexes and remove if not used

-- Index statistics collection:
-- Enable statistics collection for index usage:
-- ALTER TABLE <table> ALTER COLUMN <column> SET STATISTICS 1000;
-- (Adjust per-column statistics targets based on query patterns)

-- ============================================================================
-- INDEX USAGE NOTES
-- ============================================================================

-- Time-based indexes (observed_at, ingested_at, created_at):
-- - DESC ordering for "latest first" queries
-- - Used for time-range queries, time-series analysis
-- - Partition-aware (see 07_retention.sql for partitioning strategy)

-- Machine-centric indexes (machine_id):
-- - Host-centric query pattern (primary query pattern)
-- - Combined with time indexes for timeline queries
-- - Used for per-host analysis and correlation

-- Component-centric indexes (component_instance_id):
-- - Component lifecycle queries
-- - Sequence gap detection
-- - Component health monitoring

-- Foreign key indexes:
-- - Automatically created for primary keys
-- - Explicitly created for foreign keys for join performance
-- - Used for referential integrity checks

-- Text search indexes (GIN with trigram):
-- - Partial path matching (file_path, persistence_key, deception_target)
-- - Case-insensitive text search
-- - Requires pg_trgm extension: CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- JSONB indexes (if needed):
-- - GIN index on payload for flexible querying
-- - Consider adding if payload queries become frequent
-- - Example: CREATE INDEX idx_raw_events_payload_gin ON raw_events USING gin (payload);

-- Partial indexes:
-- - Reduce index size by filtering rows
-- - Improve query performance for filtered queries
-- - Examples: active flows, unresolved incidents, high-confidence evidence

-- ============================================================================
-- INDEX DEPENDENCIES
-- ============================================================================

-- Required PostgreSQL extensions:
-- - pg_trgm: For trigram text search (GIN indexes on text columns)
--   CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Index dependencies on partitioning (see 07_retention.sql):
-- - Partitioned tables require partition-specific indexes
-- - Global indexes may not be supported on all partitioned tables
-- - Consider local indexes per partition for better performance

-- ============================================================================
-- PERFORMANCE CONSIDERATIONS
-- ============================================================================

-- Write performance:
-- - Each index adds write overhead (index maintenance on INSERT/UPDATE/DELETE)
-- - Monitor write performance impact of indexes
-- - Consider deferring index creation for bulk loads

-- Query performance:
-- - Use EXPLAIN ANALYZE to verify index usage
-- - Ensure statistics are up-to-date (ANALYZE regularly)
-- - Consider index-only scans for frequently accessed columns

-- Storage considerations:
-- - Indexes consume additional storage space
-- - Monitor index size relative to table size
-- - Consider index compression for large indexes (if supported)

-- Hot/cold data partitioning:
-- - Time-based partitioning separates hot (recent) and cold (historical) data
-- - Indexes on partitioned tables are local to partitions
-- - Query performance improves when queries target single partitions
