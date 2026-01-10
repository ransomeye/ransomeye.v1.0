-- RansomEye v1.0 Partitioning and Retention Policies
-- AUTHORITATIVE: Time-based partitioning and data retention strategies
-- PostgreSQL 14+ compatible
-- Explicit partitioning and retention policies for all time-indexed tables

-- ============================================================================
-- PARTITIONING STRATEGY
-- ============================================================================
-- All time-indexed tables are partitioned by ingested_at (monthly partitions)
-- Retention policy: Hot (3 months), Warm (1 year), Cold (7 years), Archive (indefinite)

-- Partition naming convention: <table_name>_YYYY_MM (e.g., raw_events_2024_01)

-- ============================================================================
-- RAW EVENTS PARTITIONING
-- ============================================================================
-- Raw events are partitioned by ingested_at (monthly partitions)

-- Note: Table creation must use partitioning from the start
-- For existing tables, migration to partitioning requires data migration

-- Create partitioned table (if not already partitioned):
-- DROP TABLE IF EXISTS raw_events CASCADE;
-- CREATE TABLE raw_events (
--     ... (columns from 01_raw_events.sql) ...
-- ) PARTITION BY RANGE (ingested_at);

-- Example partition creation:
-- CREATE TABLE raw_events_2024_01 PARTITION OF raw_events
--     FOR VALUES FROM ('2024-01-01 00:00:00+00') TO ('2024-02-01 00:00:00+00');
-- CREATE TABLE raw_events_2024_02 PARTITION OF raw_events
--     FOR VALUES FROM ('2024-02-01 00:00:00+00') TO ('2024-03-01 00:00:00+00');

-- Partition indexes (local to each partition):
-- Indexes are automatically created on partitions based on parent table indexes
-- Each partition maintains its own set of indexes

-- ============================================================================
-- NORMALIZED TABLES PARTITIONING
-- ============================================================================
-- Normalized tables are partitioned by observed_at (monthly partitions)
-- observed_at is denormalized from raw_events.observed_at

-- Tables to partition:
-- - process_activity (partitioned by observed_at)
-- - file_activity (partitioned by observed_at)
-- - persistence (partitioned by observed_at)
-- - network_intent (partitioned by observed_at)
-- - health_heartbeat (partitioned by observed_at)
-- - dpi_flows (partitioned by observed_at)
-- - dns (partitioned by observed_at)
-- - deception (partitioned by observed_at)

-- Example for process_activity:
-- CREATE TABLE process_activity (
--     ... (columns from 02_normalized_agent.sql) ...
-- ) PARTITION BY RANGE (observed_at);

-- ============================================================================
-- CORRELATION TABLES PARTITIONING
-- ============================================================================
-- Correlation tables are partitioned by created_at or first_observed_at (monthly partitions)

-- Tables to partition:
-- - incidents (partitioned by first_observed_at)
-- - incident_stages (partitioned by transitioned_at)
-- - evidence (partitioned by observed_at)
-- - evidence_correlation_patterns (partitioned by pattern_matched_at)

-- Example for incidents:
-- CREATE TABLE incidents (
--     ... (columns from 04_correlation.sql) ...
-- ) PARTITION BY RANGE (first_observed_at);

-- ============================================================================
-- AI METADATA TABLES PARTITIONING
-- ============================================================================
-- AI metadata tables are partitioned by created_at or computed_at (monthly partitions)

-- Tables to partition:
-- - feature_vectors (partitioned by computed_at)
-- - clusters (partitioned by cluster_created_at) - Note: May need different strategy
-- - cluster_memberships (partitioned by added_at)
-- - novelty_scores (partitioned by computed_at)
-- - shap_explanations (partitioned by computed_at)

-- Example for feature_vectors:
-- CREATE TABLE feature_vectors (
--     ... (columns from 05_ai_metadata.sql) ...
-- ) PARTITION BY RANGE (computed_at);

-- Note: Clusters may require different partitioning strategy (by cluster_created_at or cluster_updated_at)

-- ============================================================================
-- RETENTION POLICY: HOT / WARM / COLD / ARCHIVE
-- ============================================================================

-- HOT (0-3 months):
-- - Active query workload
-- - Primary indexes maintained
-- - Fast storage (SSD)
-- - Retention: 3 months from current date
-- - Partition strategy: Keep last 3 partitions active

-- WARM (3-12 months):
-- - Reduced query workload
-- - Indexes maintained but less frequently
-- - Medium storage (SSD with compression)
-- - Retention: 1 year from current date
-- - Partition strategy: Keep partitions 3-12 months old

-- COLD (1-7 years):
-- - Historical queries only
-- - Indexes maintained but rarely used
-- - Slow storage (HDD with compression, possibly archive storage)
-- - Retention: 7 years from current date
-- - Partition strategy: Keep partitions 1-7 years old

-- ARCHIVE (7+ years):
-- - Compliance/audit queries only
-- - Indexes may be dropped to save space
-- - Archive storage (tape, object storage, compressed archives)
-- - Retention: Indefinite (compliance requirement)
-- - Partition strategy: Keep partitions 7+ years old

-- ============================================================================
-- RETENTION POLICY IMPLEMENTATION
-- ============================================================================

-- Function to create monthly partition for a table
CREATE OR REPLACE FUNCTION create_monthly_partition(
    parent_table_name TEXT,
    partition_date DATE
) RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    partition_start TIMESTAMPTZ;
    partition_end TIMESTAMPTZ;
BEGIN
    partition_name := parent_table_name || '_' || TO_CHAR(partition_date, 'YYYY_MM');
    partition_start := DATE_TRUNC('month', partition_date::TIMESTAMPTZ);
    partition_end := partition_start + INTERVAL '1 month';
    
    -- Check if partition already exists
    IF EXISTS (
        SELECT 1 FROM pg_class WHERE relname = partition_name
    ) THEN
        RAISE NOTICE 'Partition % already exists', partition_name;
        RETURN;
    END IF;
    
    -- Create partition (example for raw_events, adjust for other tables)
    EXECUTE format(
        'CREATE TABLE %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
        partition_name,
        parent_table_name,
        partition_start,
        partition_end
    );
    
    RAISE NOTICE 'Created partition %', partition_name;
END;
$$ LANGUAGE plpgsql;

-- Function to drop old partitions (archive/delete)
CREATE OR REPLACE FUNCTION drop_old_partitions(
    parent_table_name TEXT,
    retention_months INTEGER
) RETURNS VOID AS $$
DECLARE
    partition_record RECORD;
    cutoff_date DATE;
BEGIN
    cutoff_date := CURRENT_DATE - (retention_months || ' months')::INTERVAL;
    
    FOR partition_record IN
        SELECT tablename
        FROM pg_tables
        WHERE tablename LIKE parent_table_name || '_%'
        AND tablename ~ '^\d{4}_\d{2}$'
    LOOP
        -- Extract date from partition name
        DECLARE
            partition_date DATE;
        BEGIN
            partition_date := TO_DATE(
                SUBSTRING(partition_record.tablename FROM '\d{4}_\d{2}$'),
                'YYYY_MM'
            );
            
            IF partition_date < cutoff_date THEN
                -- Archive partition before dropping (implementation-specific)
                -- For now, just drop (DO NOT USE IN PRODUCTION WITHOUT ARCHIVE)
                RAISE NOTICE 'Would archive/drop partition % (older than % months)', 
                    partition_record.tablename, retention_months;
                -- EXECUTE format('DROP TABLE %I', partition_record.tablename);
            END IF;
        END;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- AUTOMATIC PARTITION MANAGEMENT
-- ============================================================================

-- Function to create partitions for next N months (pre-create partitions)
CREATE OR REPLACE FUNCTION create_future_partitions(
    parent_table_name TEXT,
    months_ahead INTEGER DEFAULT 3
) RETURNS VOID AS $$
DECLARE
    month_offset INTEGER;
    target_date DATE;
BEGIN
    FOR month_offset IN 0..months_ahead LOOP
        target_date := DATE_TRUNC('month', CURRENT_DATE + (month_offset || ' months')::INTERVAL)::DATE;
        PERFORM create_monthly_partition(parent_table_name, target_date);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Scheduled job (using pg_cron or external scheduler):
-- - Create partitions for next 3 months (monthly, at start of month)
-- - Archive partitions older than 7 years (monthly, at start of month)
-- - Update partition statistics (weekly, on weekends)

-- Example pg_cron jobs (if pg_cron extension is available):
-- SELECT cron.schedule('create-partitions', '0 0 1 * *', 'SELECT create_future_partitions(''raw_events'', 3)');
-- SELECT cron.schedule('archive-partitions', '0 2 1 * *', 'SELECT drop_old_partitions(''raw_events'', 84)'); -- 84 months = 7 years

-- ============================================================================
-- RETENTION POLICY BY TABLE
-- ============================================================================

-- Raw events:
-- - HOT: 3 months (0-3 months)
-- - WARM: 1 year (3-12 months)
-- - COLD: 7 years (1-7 years)
-- - ARCHIVE: Indefinite (7+ years)

-- Normalized tables (process_activity, file_activity, etc.):
-- - HOT: 3 months (0-3 months)
-- - WARM: 1 year (3-12 months)
-- - COLD: 7 years (1-7 years)
-- - ARCHIVE: Indefinite (7+ years)

-- Correlation tables (incidents, evidence):
-- - HOT: 1 year (0-1 year) - Incidents may be active for longer
-- - WARM: 3 years (1-3 years) - Historical incident analysis
-- - COLD: 7 years (3-7 years)
-- - ARCHIVE: Indefinite (7+ years) - Compliance/audit requirement

-- AI metadata tables (feature_vectors, novelty_scores, etc.):
-- - HOT: 3 months (0-3 months) - Recent AI inferences
-- - WARM: 1 year (3-12 months)
-- - COLD: 3 years (1-3 years) - Historical AI analysis
-- - ARCHIVE: 7 years (3-7 years) - Model training data

-- Identity tables (machines, component_instances):
-- - Not partitioned (small tables, infrequent updates)
-- - Retention: Indefinite (reference data)

-- Component identity history:
-- - Partitioned by first_observed_at (monthly)
-- - HOT: 1 year (0-1 year)
-- - WARM: 3 years (1-3 years)
-- - COLD: 7 years (3-7 years)
-- - ARCHIVE: Indefinite (7+ years)

-- ============================================================================
-- PARTITIONING CONSTRAINTS
-- ============================================================================

-- Partitioning constraints:
-- 1. Partition key must be included in PRIMARY KEY or UNIQUE constraints
-- 2. Foreign keys to partitioned tables require special handling
-- 3. Indexes on partitioned tables are local to each partition
-- 4. Partition pruning: Queries must filter by partition key for optimal performance

-- Example constraint adjustments for partitioned tables:
-- - raw_events: PRIMARY KEY (event_id) - event_id is independent of partition key
--   Solution: Use UNIQUE (event_id, ingested_at) or partition-aware unique constraints
--   OR: Use event_id as PRIMARY KEY with ingested_at in UNIQUE constraint

-- Note: PostgreSQL 11+ supports PRIMARY KEY on partitioned tables if partition key is part of it
-- For raw_events: PRIMARY KEY (event_id, ingested_at) - ensures uniqueness across partitions

-- ============================================================================
-- ARCHIVE STRATEGY
-- ============================================================================

-- Archive implementation options:
-- 1. External archive storage (S3, Azure Blob, etc.)
-- 2. Compressed backups (pg_dump with compression)
-- 3. Table inheritance for archive tables
-- 4. Separate archive database

-- Archive process:
-- 1. Export partition data to archive format (CSV, Parquet, etc.)
-- 2. Upload to archive storage
-- 3. Verify archive integrity (checksums)
-- 4. Drop partition from production database
-- 5. Update archive catalog

-- Archive restore:
-- 1. Identify archive location
-- 2. Restore partition data from archive
-- 3. Recreate partition structure
-- 4. Import data into partition
-- 5. Rebuild indexes

-- ============================================================================
-- PERFORMANCE CONSIDERATIONS
-- ============================================================================

-- Partition pruning:
-- - Queries must include partition key in WHERE clause for partition pruning
-- - Example: WHERE ingested_at >= '2024-01-01' AND ingested_at < '2024-02-01'
-- - Avoid functions on partition key (prevents pruning)

-- Query optimization:
-- - Use EXPLAIN to verify partition pruning
-- - Ensure partition key is in WHERE clause
-- - Use DATE_TRUNC for month-based queries

-- Index maintenance:
-- - Indexes are local to each partition
-- - REINDEX on individual partitions (not entire table)
-- - ANALYZE per partition for accurate statistics

-- Vacuum and maintenance:
-- - VACUUM per partition (not entire table)
-- - Monitor partition bloat individually
-- - Adjust autovacuum settings per partition if needed

-- ============================================================================
-- MONITORING
-- ============================================================================

-- Monitor partition sizes:
-- SELECT 
--     schemaname,
--     tablename,
--     pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
-- FROM pg_tables
-- WHERE tablename LIKE 'raw_events_%'
-- ORDER BY tablename;

-- Monitor partition row counts:
-- SELECT 
--     tablename,
--     (SELECT COUNT(*) FROM pg_class WHERE relname = tablename) AS row_count
-- FROM pg_tables
-- WHERE tablename LIKE 'raw_events_%';

-- Monitor partition query performance:
-- Enable partition-wise joins and aggregates in PostgreSQL 11+
-- SET enable_partitionwise_join = ON;
-- SET enable_partitionwise_aggregate = ON;
