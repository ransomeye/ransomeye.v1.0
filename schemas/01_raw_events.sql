-- RansomEye v1.0 Raw Events Storage
-- AUTHORITATIVE: Immutable storage of exact event envelopes as received
-- PostgreSQL 14+ compatible

-- Event validation status (from failure semantics contract)
CREATE TYPE event_validation_status AS ENUM (
    'VALID',
    'LATE_ARRIVAL',
    'SEQUENCE_GAP',
    'SEQUENCE_OUT_OF_ORDER',
    'CLOCK_SKEW_WARNING',
    'DUPLICATE_REJECTED',
    'SCHEMA_VALIDATION_FAILED',
    'TIMESTAMP_VALIDATION_FAILED',
    'INTEGRITY_CHAIN_BROKEN',
    'REJECTED'
);

-- ============================================================================
-- RAW EVENTS
-- ============================================================================
-- Immutable storage of exact event envelopes as received
-- Never updated, never deleted (immutable log)

CREATE TABLE raw_events (
    event_id UUID NOT NULL PRIMARY KEY,
    -- event_id from event envelope (UUID v4)
    -- PRIMARY KEY ensures duplicate detection at database level
    
    machine_id VARCHAR(255) NOT NULL REFERENCES machines(machine_id) ON DELETE RESTRICT,
    -- Foreign key to machines table
    -- ON DELETE RESTRICT: Cannot delete machine with events
    
    component_instance_id VARCHAR(255) NOT NULL REFERENCES component_instances(component_instance_id) ON DELETE RESTRICT,
    -- Foreign key to component_instances table
    
    component component_type NOT NULL,
    -- Component type from event envelope
    
    observed_at TIMESTAMPTZ NOT NULL,
    -- observed_at from event envelope (RFC3339 UTC converted to TIMESTAMPTZ)
    
    ingested_at TIMESTAMPTZ NOT NULL,
    -- ingested_at from event envelope (RFC3339 UTC converted to TIMESTAMPTZ)
    
    sequence BIGINT NOT NULL,
    -- sequence from event envelope (64-bit unsigned integer, stored as BIGINT)
    -- BIGINT covers uint64 range (0 to 2^64-1)
    
    payload JSONB NOT NULL,
    -- payload from event envelope (opaque JSON object)
    -- JSONB for efficient querying and indexing of payload fields
    -- Opaque structure: component-specific, not validated by schema
    
    hostname VARCHAR(255) NOT NULL,
    -- identity.hostname from event envelope
    -- Denormalized for query performance (also in component_identity_history)
    
    boot_id VARCHAR(255) NOT NULL,
    -- identity.boot_id from event envelope
    -- Denormalized for query performance
    
    agent_version VARCHAR(255) NOT NULL,
    -- identity.agent_version from event envelope
    -- Denormalized for query performance
    
    hash_sha256 CHAR(64) NOT NULL,
    -- integrity.hash_sha256 from event envelope
    -- CHAR(64) for exactly 64 hex characters
    -- Used for integrity chain validation
    
    prev_hash_sha256 CHAR(64),
    -- integrity.prev_hash_sha256 from event envelope
    -- NULL for first event (sequence=0), otherwise CHAR(64)
    -- Used for integrity chain validation
    
    validation_status event_validation_status NOT NULL DEFAULT 'VALID',
    -- Validation status determined at ingestion time
    -- From failure semantics contract
    
    late_arrival BOOLEAN NOT NULL DEFAULT FALSE,
    -- TRUE if ingested_at - observed_at > 1 hour (late arrival)
    
    arrival_latency_seconds INTEGER,
    -- Computed: ingested_at - observed_at in seconds
    -- NULL if not late arrival
    -- INTEGER sufficient for ~68 years of latency (unlikely)
    
    created_at TIMESTAMPTZ NOT NULL,
    -- PHASE 2: Deterministic timestamp - must be provided explicitly (use observed_at from envelope)
    -- Schema-level timestamp (immutable)
    -- When event was inserted into database (deterministic, from envelope)
    
    -- Constraints
    CONSTRAINT raw_events_sequence_non_negative CHECK (sequence >= 0),
    CONSTRAINT raw_events_observed_before_ingested CHECK (observed_at <= ingested_at + INTERVAL '5 seconds'),
    -- Allow 5 seconds clock skew tolerance (from time semantics contract)
    CONSTRAINT raw_events_hash_format CHECK (hash_sha256 ~ '^[a-fA-F0-9]{64}$'),
    CONSTRAINT raw_events_prev_hash_format CHECK (prev_hash_sha256 IS NULL OR prev_hash_sha256 ~ '^[a-fA-F0-9]{64}$'),
    CONSTRAINT raw_events_first_event_prev_hash_null CHECK (
        (sequence = 0 AND prev_hash_sha256 IS NULL) OR 
        (sequence > 0 AND prev_hash_sha256 IS NOT NULL)
    ),
    -- First event (sequence=0) must have prev_hash_sha256 = NULL
    -- Non-first events (sequence > 0) must have prev_hash_sha256 NOT NULL
    CONSTRAINT raw_events_hostname_not_empty CHECK (LENGTH(TRIM(hostname)) > 0),
    CONSTRAINT raw_events_boot_id_not_empty CHECK (LENGTH(TRIM(boot_id)) > 0),
    CONSTRAINT raw_events_agent_version_not_empty CHECK (LENGTH(TRIM(agent_version)) > 0),
    CONSTRAINT raw_events_payload_is_object CHECK (jsonb_typeof(payload) = 'object')
);

COMMENT ON TABLE raw_events IS 'Immutable storage of exact event envelopes as received. Never updated, never deleted. Authoritative event log.';
COMMENT ON COLUMN raw_events.event_id IS 'UUID v4 from event envelope. PRIMARY KEY ensures duplicate detection at database level.';
COMMENT ON COLUMN raw_events.observed_at IS 'RFC3339 UTC timestamp when event was observed at source. Converted to TIMESTAMPTZ.';
COMMENT ON COLUMN raw_events.ingested_at IS 'RFC3339 UTC timestamp when event was ingested into system. Converted to TIMESTAMPTZ.';
COMMENT ON COLUMN raw_events.sequence IS 'Monotonically increasing sequence number within component instance. 64-bit unsigned integer (0 to 2^64-1).';
COMMENT ON COLUMN raw_events.payload IS 'Opaque event payload (component-specific JSON object). Structure not validated by schema. Stored as JSONB for efficient querying.';
COMMENT ON COLUMN raw_events.hash_sha256 IS 'SHA256 hash of entire event envelope. Used for integrity chain validation.';
COMMENT ON COLUMN raw_events.prev_hash_sha256 IS 'SHA256 hash of previous event in sequence. NULL for first event (sequence=0).';
COMMENT ON COLUMN raw_events.validation_status IS 'Validation status determined at ingestion. From failure semantics contract (VALID, LATE_ARRIVAL, SEQUENCE_GAP, etc.).';
COMMENT ON COLUMN raw_events.late_arrival IS 'TRUE if ingested_at - observed_at > 1 hour. Marked as late arrival per time semantics contract.';

-- ============================================================================
-- EVENT VALIDATION LOG
-- ============================================================================
-- Immutable log of all validation operations (success and failure)
-- Supports audit trail and debugging of validation failures

CREATE TABLE event_validation_log (
    id BIGSERIAL NOT NULL PRIMARY KEY,
    -- Auto-incrementing ID (immutable, never reused)
    
    event_id UUID REFERENCES raw_events(event_id) ON DELETE RESTRICT,
    -- Foreign key to raw_events (NULL if event was rejected before insertion)
    
    validation_status event_validation_status NOT NULL,
    -- Validation status (same enum as raw_events)
    
    validation_timestamp TIMESTAMPTZ NOT NULL,
    -- PHASE 2: Deterministic timestamp - must be provided explicitly (use observed_at from envelope)
    -- When validation occurred (deterministic, from envelope)
    
    error_code VARCHAR(255),
    -- Error code from failure semantics contract (NULL if validation passed)
    -- Examples: SCHEMA_VIOLATION, TIMESTAMP_PARSE_ERROR, DUPLICATE_EVENT_ID, etc.
    
    error_message TEXT,
    -- Human-readable error message (for debugging)
    
    validation_details JSONB,
    -- Additional validation context (JSONB for flexibility)
    -- Examples: field paths, expected vs actual values, gap ranges, etc.
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT event_validation_log_error_code_check CHECK (
        (validation_status = 'VALID' AND error_code IS NULL) OR
        (validation_status != 'VALID' AND error_code IS NOT NULL)
    )
    -- VALID status must have NULL error_code
    -- Non-VALID status must have non-NULL error_code
);

COMMENT ON TABLE event_validation_log IS 'Immutable log of all validation operations (success and failure). Supports audit trail and debugging.';
COMMENT ON COLUMN event_validation_log.event_id IS 'Foreign key to raw_events. NULL if event was rejected before insertion (e.g., schema validation failed).';
COMMENT ON COLUMN event_validation_log.validation_status IS 'Validation status from failure semantics contract. VALID, LATE_ARRIVAL, SEQUENCE_GAP, etc.';
COMMENT ON COLUMN event_validation_log.error_code IS 'Error code from failure semantics contract. NULL if validation passed.';

-- ============================================================================
-- SEQUENCE GAPS
-- ============================================================================
-- Explicit tracking of sequence gaps per component instance
-- Supports gap detection and analysis

CREATE TABLE sequence_gaps (
    id BIGSERIAL NOT NULL PRIMARY KEY,
    -- Auto-incrementing ID (immutable, never reused)
    
    component_instance_id VARCHAR(255) NOT NULL REFERENCES component_instances(component_instance_id) ON DELETE RESTRICT,
    -- Foreign key to component_instances
    
    gap_start_sequence BIGINT NOT NULL,
    -- Start of gap (last_sequence + 1)
    
    gap_end_sequence BIGINT NOT NULL,
    -- End of gap (incoming_sequence - 1)
    
    gap_detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- When gap was detected
    
    gap_size BIGINT NOT NULL,
    -- Computed: gap_end_sequence - gap_start_sequence + 1
    
    first_event_after_gap UUID REFERENCES raw_events(event_id) ON DELETE RESTRICT,
    -- First event received after gap (for analysis)
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT sequence_gaps_start_before_end CHECK (gap_start_sequence < gap_end_sequence),
    CONSTRAINT sequence_gaps_start_non_negative CHECK (gap_start_sequence >= 0),
    CONSTRAINT sequence_gaps_end_non_negative CHECK (gap_end_sequence >= 0),
    CONSTRAINT sequence_gaps_size_positive CHECK (gap_size > 0)
);

COMMENT ON TABLE sequence_gaps IS 'Explicit tracking of sequence gaps per component instance. Supports gap detection and analysis per failure semantics contract.';
COMMENT ON COLUMN sequence_gaps.gap_start_sequence IS 'Start of gap (last_sequence + 1). First missing sequence number.';
COMMENT ON COLUMN sequence_gaps.gap_end_sequence IS 'End of gap (incoming_sequence - 1). Last missing sequence number.';
COMMENT ON COLUMN sequence_gaps.gap_size IS 'Number of missing sequence numbers (gap_end_sequence - gap_start_sequence + 1).';

-- ============================================================================
-- INDEXES (RAW EVENTS)
-- ============================================================================

-- Raw events: Find events by machine (host-centric queries)
CREATE INDEX idx_raw_events_machine_id 
    ON raw_events(machine_id);

-- Raw events: Find events by component instance
CREATE INDEX idx_raw_events_component_instance_id 
    ON raw_events(component_instance_id);

-- Raw events: Find events by component type
CREATE INDEX idx_raw_events_component 
    ON raw_events(component);

-- Raw events: Find events by observed time (time-indexed queries)
-- Partitioned by ingested_at (see 07_retention.sql)
CREATE INDEX idx_raw_events_observed_at 
    ON raw_events(observed_at DESC);

-- Raw events: Find events by ingested time (time-indexed queries)
-- Primary partitioning key
CREATE INDEX idx_raw_events_ingested_at 
    ON raw_events(ingested_at DESC);

-- Raw events: Find events by sequence (for gap/out-of-order detection)
CREATE INDEX idx_raw_events_component_instance_sequence 
    ON raw_events(component_instance_id, sequence);

-- Raw events: Find events by validation status (for monitoring)
CREATE INDEX idx_raw_events_validation_status 
    ON raw_events(validation_status) 
    WHERE validation_status != 'VALID';

-- Raw events: Find late arrival events
CREATE INDEX idx_raw_events_late_arrival 
    ON raw_events(late_arrival) 
    WHERE late_arrival = TRUE;

-- Raw events: Integrity chain validation (find previous event by hash)
CREATE INDEX idx_raw_events_hash_sha256 
    ON raw_events(hash_sha256);

-- Raw events: Find events by hostname (for host-centric queries)
CREATE INDEX idx_raw_events_hostname 
    ON raw_events(hostname);

-- Raw events: Find events by boot_id (for boot session analysis)
CREATE INDEX idx_raw_events_boot_id 
    ON raw_events(boot_id);

-- Event validation log: Find validations by event_id
CREATE INDEX idx_event_validation_log_event_id 
    ON event_validation_log(event_id);

-- Event validation log: Find validations by status
CREATE INDEX idx_event_validation_log_status 
    ON event_validation_log(validation_status);

-- Event validation log: Find validations by timestamp
CREATE INDEX idx_event_validation_log_timestamp 
    ON event_validation_log(validation_timestamp DESC);

-- Sequence gaps: Find gaps by component instance
CREATE INDEX idx_sequence_gaps_component_instance_id 
    ON sequence_gaps(component_instance_id);

-- Sequence gaps: Find gaps by detection time
CREATE INDEX idx_sequence_gaps_detected_at 
    ON sequence_gaps(gap_detected_at DESC);
