-- RansomEye v1.0 Correlation Tables
-- AUTHORITATIVE: Incident correlation and evidence linkage
-- PostgreSQL 14+ compatible

-- Incident stage enumeration (from Clean → Suspicious → Probable → Confirmed)
CREATE TYPE incident_stage AS ENUM (
    'CLEAN',
    'SUSPICIOUS',
    'PROBABLE',
    'CONFIRMED'
);

-- Evidence type enumeration (type of evidence linking event to incident)
CREATE TYPE evidence_type AS ENUM (
    'PROCESS_ACTIVITY',
    'FILE_ACTIVITY',
    'PERSISTENCE',
    'NETWORK_INTENT',
    'DPI_FLOW',
    'DNS_QUERY',
    'DECEPTION',
    'HEALTH_ANOMALY',
    'CORRELATION_PATTERN',
    'AI_SIGNAL'
);

-- Confidence level enumeration (confidence in evidence contribution)
CREATE TYPE confidence_level AS ENUM (
    'LOW',
    'MEDIUM',
    'HIGH',
    'CRITICAL'
);

-- ============================================================================
-- INCIDENTS
-- ============================================================================
-- Authoritative incident registry
-- Immutable primary key, auditable state transitions, no deletion

CREATE TABLE incidents (
    incident_id UUID NOT NULL PRIMARY KEY,
    -- UUID v4 for incident identifier (immutable, never reused)
    
    machine_id VARCHAR(255) NOT NULL REFERENCES machines(machine_id) ON DELETE RESTRICT,
    -- Foreign key to machines (host-centric incident tracking)
    -- Incident is associated with a specific machine
    
    current_stage incident_stage NOT NULL DEFAULT 'SUSPICIOUS',
    -- PHASE 3: Current incident stage (SUSPICIOUS, PROBABLE, CONFIRMED)
    -- Incidents start at SUSPICIOUS (single signal creates SUSPICIOUS incident)
    -- Updated via incident_stages table (auditable state transitions)
    
    first_observed_at TIMESTAMPTZ NOT NULL,
    -- Timestamp of first evidence event contributing to this incident
    -- Set on INSERT, never updated
    
    last_observed_at TIMESTAMPTZ NOT NULL,
    -- Timestamp of last evidence event contributing to this incident
    -- Updated when new evidence is added
    
    stage_changed_at TIMESTAMPTZ NOT NULL,
    -- PHASE 3: Deterministic timestamp - must be provided explicitly (use event observed_at)
    -- When current_stage was last changed
    -- Updated via incident_stages table
    
    total_evidence_count BIGINT NOT NULL DEFAULT 0,
    -- Total number of evidence entries contributing to this incident
    -- Incremented when evidence is added
    
    confidence_score NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    -- Accumulated confidence score (0.00 to 100.00)
    -- Computed from evidence confidence levels
    -- NUMERIC(5,2) for precise decimal scoring
    
    title VARCHAR(255),
    -- Human-readable incident title
    -- NULL until manually set
    -- VARCHAR(255) sufficient for titles
    
    description TEXT,
    -- Human-readable incident description
    -- NULL until manually set
    -- TEXT for unlimited length
    
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    -- TRUE if incident is resolved/closed
    -- Once TRUE, remains TRUE (no reopening)
    
    resolved_at TIMESTAMPTZ,
    -- When incident was resolved
    -- NULL if not resolved
    -- Set when resolved = TRUE
    
    resolved_by VARCHAR(255),
    -- User/entity that resolved the incident
    -- NULL if not resolved or resolution is automated
    -- VARCHAR(255) sufficient for user identifiers
    
    created_at TIMESTAMPTZ NOT NULL,
    -- PHASE 3: Deterministic timestamp - must be provided explicitly (use event observed_at)
    -- Schema-level timestamp (immutable)
    -- When incident was created
    
    CONSTRAINT incidents_confidence_score_range CHECK (confidence_score >= 0.00 AND confidence_score <= 100.00),
    CONSTRAINT incidents_first_before_last CHECK (first_observed_at <= last_observed_at),
    CONSTRAINT incidents_resolved_check CHECK (
        (resolved = FALSE AND resolved_at IS NULL AND resolved_by IS NULL) OR
        (resolved = TRUE AND resolved_at IS NOT NULL)
    ),
    -- If resolved = TRUE, resolved_at must be set
    -- If resolved = FALSE, resolved_at and resolved_by must be NULL
    CONSTRAINT incidents_evidence_count_non_negative CHECK (total_evidence_count >= 0)
);

COMMENT ON TABLE incidents IS 'Authoritative incident registry. Immutable primary key, auditable state transitions, no deletion. One incident per machine (host-centric).';
COMMENT ON COLUMN incidents.incident_id IS 'UUID v4 for incident identifier. Immutable, never reused.';
COMMENT ON COLUMN incidents.current_stage IS 'Current incident stage (CLEAN, SUSPICIOUS, PROBABLE, CONFIRMED). Updated via incident_stages table for auditable state transitions.';
COMMENT ON COLUMN incidents.first_observed_at IS 'Timestamp of first evidence event contributing to this incident. Set on INSERT, never updated.';
COMMENT ON COLUMN incidents.last_observed_at IS 'Timestamp of last evidence event contributing to this incident. Updated when new evidence is added.';
COMMENT ON COLUMN incidents.confidence_score IS 'Accumulated confidence score (0.00 to 100.00). Computed from evidence confidence levels. Updated when evidence is added.';
COMMENT ON COLUMN incidents.resolved IS 'TRUE if incident is resolved/closed. Once TRUE, remains TRUE (no reopening). Incident history is preserved.';

-- ============================================================================
-- INCIDENT STAGES
-- ============================================================================
-- Immutable log of all incident stage transitions
-- Auditable state transition history (no deletion)

CREATE TABLE incident_stages (
    id BIGSERIAL NOT NULL PRIMARY KEY,
    -- Auto-incrementing ID (immutable, never reused)
    
    incident_id UUID NOT NULL REFERENCES incidents(incident_id) ON DELETE RESTRICT,
    -- Foreign key to incidents
    
    from_stage incident_stage,
    -- Previous stage (NULL for initial stage)
    -- NULL if this is the first stage (CLEAN)
    
    to_stage incident_stage NOT NULL,
    -- New stage (transition target)
    
    transitioned_at TIMESTAMPTZ NOT NULL,
    -- PHASE 3: Deterministic timestamp - must be provided explicitly (use event observed_at)
    -- When stage transition occurred
    
    transitioned_by VARCHAR(255),
    -- User/entity that triggered the transition (NULL if automated)
    -- VARCHAR(255) sufficient for user identifiers
    
    transition_reason TEXT,
    -- Human-readable reason for stage transition
    -- NULL if not provided
    -- TEXT for unlimited length
    
    evidence_count_at_transition BIGINT NOT NULL,
    -- Number of evidence entries at time of transition
    -- Snapshot for audit trail
    
    confidence_score_at_transition NUMERIC(5,2) NOT NULL,
    -- Confidence score at time of transition
    -- Snapshot for audit trail
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT incident_stages_from_to_different CHECK (from_stage IS NULL OR from_stage != to_stage),
    CONSTRAINT incident_stages_evidence_count_non_negative CHECK (evidence_count_at_transition >= 0),
    CONSTRAINT incident_stages_confidence_score_range CHECK (confidence_score_at_transition >= 0.00 AND confidence_score_at_transition <= 100.00)
);

COMMENT ON TABLE incident_stages IS 'Immutable log of all incident stage transitions. Auditable state transition history (no deletion). Supports incident audit trail.';
COMMENT ON COLUMN incident_stages.from_stage IS 'Previous stage (NULL for initial stage). NULL if this is the first stage (CLEAN).';
COMMENT ON COLUMN incident_stages.to_stage IS 'New stage (transition target). Must be different from from_stage if from_stage is not NULL.';
COMMENT ON COLUMN incident_stages.evidence_count_at_transition IS 'Number of evidence entries at time of transition. Snapshot for audit trail.';
COMMENT ON COLUMN incident_stages.confidence_score_at_transition IS 'Confidence score at time of transition. Snapshot for audit trail.';

-- ============================================================================
-- EVIDENCE
-- ============================================================================
-- Evidence linkage: links events to incidents
-- One event can contribute to multiple incidents (many-to-many relationship)

CREATE TABLE evidence (
    id BIGSERIAL NOT NULL PRIMARY KEY,
    -- Auto-incrementing ID (immutable, never reused)
    
    incident_id UUID NOT NULL REFERENCES incidents(incident_id) ON DELETE RESTRICT,
    -- Foreign key to incidents
    -- Evidence is linked to a specific incident
    
    event_id UUID NOT NULL REFERENCES raw_events(event_id) ON DELETE RESTRICT,
    -- Foreign key to raw_events
    -- Evidence is linked to a specific event
    -- One event can contribute to multiple incidents (many-to-many)
    
    evidence_type evidence_type NOT NULL,
    -- Type of evidence (PROCESS_ACTIVITY, FILE_ACTIVITY, etc.)
    
    confidence_level confidence_level NOT NULL DEFAULT 'LOW',
    -- Confidence level in this evidence contribution (LOW, MEDIUM, HIGH, CRITICAL)
    
    confidence_score NUMERIC(5,2) NOT NULL,
    -- Confidence score contribution (0.00 to 100.00)
    -- Used for confidence_score accumulation in incidents
    -- NUMERIC(5,2) for precise decimal scoring
    
    normalized_table_name VARCHAR(64),
    -- Normalized table name where this evidence is stored
    -- NULL if evidence is only in raw_events
    -- Examples: 'process_activity', 'file_activity', 'dpi_flows', 'dns', 'deception'
    -- VARCHAR(64) sufficient for table names
    
    normalized_row_id BIGINT,
    -- Row ID in normalized table (if applicable)
    -- NULL if evidence is only in raw_events
    -- BIGINT for large row IDs
    
    description TEXT,
    -- Human-readable description of why this event is evidence
    -- NULL if not provided
    -- TEXT for unlimited length
    
    observed_at TIMESTAMPTZ NOT NULL,
    -- Timestamp of evidence event (denormalized from raw_events.observed_at)
    -- Used for time-based evidence queries
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    -- When evidence was linked to incident
    
    CONSTRAINT evidence_confidence_score_range CHECK (confidence_score >= 0.00 AND confidence_score <= 100.00),
    CONSTRAINT evidence_normalized_row_id_check CHECK (
        (normalized_table_name IS NULL AND normalized_row_id IS NULL) OR
        (normalized_table_name IS NOT NULL AND normalized_row_id IS NOT NULL)
    ),
    -- If normalized_table_name is set, normalized_row_id must be set
    -- If normalized_table_name is NULL, normalized_row_id must be NULL
    CONSTRAINT evidence_unique_incident_event UNIQUE (incident_id, event_id)
    -- One event can contribute to one incident only once
    -- But same event can contribute to different incidents (remove this constraint if needed)
    -- NOTE: Actually, requirement says "One event can contribute to multiple incidents"
    -- So we should allow same event_id + different incident_id
    -- But we should not allow duplicate (incident_id, event_id) pairs
);

COMMENT ON TABLE evidence IS 'Evidence linkage: links events to incidents. One event can contribute to multiple incidents (many-to-many relationship). Immutable log of evidence contributions.';
COMMENT ON COLUMN evidence.incident_id IS 'Foreign key to incidents. Evidence is linked to a specific incident.';
COMMENT ON COLUMN evidence.event_id IS 'Foreign key to raw_events. Evidence is linked to a specific event. One event can contribute to multiple incidents (many-to-many).';
COMMENT ON COLUMN evidence.evidence_type IS 'Type of evidence (PROCESS_ACTIVITY, FILE_ACTIVITY, PERSISTENCE, NETWORK_INTENT, DPI_FLOW, DNS_QUERY, DECEPTION, etc.).';
COMMENT ON COLUMN evidence.confidence_score IS 'Confidence score contribution (0.00 to 100.00). Used for confidence_score accumulation in incidents table.';
COMMENT ON COLUMN evidence.normalized_table_name IS 'Normalized table name where this evidence is stored. NULL if evidence is only in raw_events. Examples: process_activity, file_activity, dpi_flows, dns, deception.';
COMMENT ON COLUMN evidence.normalized_row_id IS 'Row ID in normalized table (if applicable). NULL if evidence is only in raw_events. Used for direct lookup of normalized evidence.';

-- ============================================================================
-- EVIDENCE CORRELATION PATTERNS
-- ============================================================================
-- Correlation patterns that link multiple events to an incident
-- Supports pattern-based evidence (e.g., "process X created file Y then encrypted files")

CREATE TABLE evidence_correlation_patterns (
    id BIGSERIAL NOT NULL PRIMARY KEY,
    -- Auto-incrementing ID (immutable, never reused)
    
    incident_id UUID NOT NULL REFERENCES incidents(incident_id) ON DELETE RESTRICT,
    -- Foreign key to incidents
    
    pattern_name VARCHAR(255) NOT NULL,
    -- Pattern name/identifier (e.g., "PROCESS_FILE_ENCRYPTION_PATTERN")
    -- VARCHAR(255) sufficient for pattern names
    
    pattern_description TEXT,
    -- Human-readable pattern description
    -- NULL if not provided
    -- TEXT for unlimited length
    
    event_ids UUID[] NOT NULL,
    -- Array of event_ids that match this pattern
    -- UUID[] for efficient array storage
    -- Must have at least one event_id
    
    pattern_confidence NUMERIC(5,2) NOT NULL,
    -- Confidence score for this pattern (0.00 to 100.00)
    -- NUMERIC(5,2) for precise decimal scoring
    
    pattern_matched_at TIMESTAMPTZ NOT NULL,
    -- When pattern was matched (timestamp of last event in pattern)
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT evidence_correlation_patterns_pattern_name_not_empty CHECK (LENGTH(TRIM(pattern_name)) > 0),
    CONSTRAINT evidence_correlation_patterns_event_ids_not_empty CHECK (array_length(event_ids, 1) > 0),
    CONSTRAINT evidence_correlation_patterns_confidence_score_range CHECK (pattern_confidence >= 0.00 AND pattern_confidence <= 100.00)
);

COMMENT ON TABLE evidence_correlation_patterns IS 'Correlation patterns that link multiple events to an incident. Supports pattern-based evidence (e.g., "process X created file Y then encrypted files").';
COMMENT ON COLUMN evidence_correlation_patterns.pattern_name IS 'Pattern name/identifier. Examples: PROCESS_FILE_ENCRYPTION_PATTERN, PERSISTENCE_NETWORK_PATTERN, etc.';
COMMENT ON COLUMN evidence_correlation_patterns.event_ids IS 'Array of event_ids that match this pattern. Must have at least one event_id. Used for pattern-based evidence linkage.';
COMMENT ON COLUMN evidence_correlation_patterns.pattern_confidence IS 'Confidence score for this pattern (0.00 to 100.00). Used for confidence_score accumulation in incidents table.';

-- ============================================================================
-- INDEXES (CORRELATION)
-- ============================================================================

-- Incidents: Find incidents by machine (host-centric queries)
CREATE INDEX idx_incidents_machine_id 
    ON incidents(machine_id);

-- Incidents: Find incidents by current stage
CREATE INDEX idx_incidents_current_stage 
    ON incidents(current_stage);

-- Incidents: Find incidents by first observed time (time-indexed queries)
CREATE INDEX idx_incidents_first_observed_at 
    ON incidents(first_observed_at DESC);

-- Incidents: Find incidents by last observed time (time-indexed queries)
CREATE INDEX idx_incidents_last_observed_at 
    ON incidents(last_observed_at DESC);

-- Incidents: Find unresolved incidents (active incidents)
CREATE INDEX idx_incidents_resolved 
    ON incidents(resolved) 
    WHERE resolved = FALSE;

-- Incidents: Find incidents by confidence score (high-confidence incidents)
CREATE INDEX idx_incidents_confidence_score 
    ON incidents(confidence_score DESC) 
    WHERE confidence_score >= 50.00;

-- Incident stages: Find stage transitions by incident
CREATE INDEX idx_incident_stages_incident_id 
    ON incident_stages(incident_id);

-- Incident stages: Find stage transitions by time (audit trail queries)
CREATE INDEX idx_incident_stages_transitioned_at 
    ON incident_stages(transitioned_at DESC);

-- Incident stages: Find stage transitions by target stage
CREATE INDEX idx_incident_stages_to_stage 
    ON incident_stages(to_stage);

-- Evidence: Find evidence by incident (all evidence for an incident)
CREATE INDEX idx_evidence_incident_id 
    ON evidence(incident_id);

-- Evidence: Find evidence by event (all incidents for an event)
CREATE INDEX idx_evidence_event_id 
    ON evidence(event_id);

-- Evidence: Find evidence by evidence type
CREATE INDEX idx_evidence_evidence_type 
    ON evidence(evidence_type);

-- Evidence: Find evidence by confidence level (high-confidence evidence)
CREATE INDEX idx_evidence_confidence_level 
    ON evidence(confidence_level);

-- Evidence: Find evidence by confidence score (high-confidence evidence)
CREATE INDEX idx_evidence_confidence_score 
    ON evidence(confidence_score DESC) 
    WHERE confidence_score >= 50.00;

-- Evidence: Find evidence by time (time-indexed queries)
CREATE INDEX idx_evidence_observed_at 
    ON evidence(observed_at DESC);

-- Evidence: Find evidence by normalized table/row (direct lookup)
CREATE INDEX idx_evidence_normalized 
    ON evidence(normalized_table_name, normalized_row_id) 
    WHERE normalized_table_name IS NOT NULL;

-- Evidence correlation patterns: Find patterns by incident
CREATE INDEX idx_evidence_correlation_patterns_incident_id 
    ON evidence_correlation_patterns(incident_id);

-- Evidence correlation patterns: Find patterns by match time
CREATE INDEX idx_evidence_correlation_patterns_matched_at 
    ON evidence_correlation_patterns(pattern_matched_at DESC);

-- Evidence correlation patterns: Find patterns by confidence
CREATE INDEX idx_evidence_correlation_patterns_confidence 
    ON evidence_correlation_patterns(pattern_confidence DESC) 
    WHERE pattern_confidence >= 50.00;

-- Evidence correlation patterns: Find patterns containing an event
CREATE INDEX idx_evidence_correlation_patterns_event_ids 
    ON evidence_correlation_patterns USING gin (event_ids);
