-- RansomEye v1.0 Normalized Agent Tables
-- AUTHORITATIVE: Query-optimized normalized tables for agent events
-- PostgreSQL 14+ compatible
-- Every normalized row MUST reference its raw event

-- Process activity types (agent-observed)
CREATE TYPE process_activity_type AS ENUM (
    'PROCESS_START',
    'PROCESS_EXIT',
    'PROCESS_INJECT',
    'PROCESS_MODIFY'
);

-- File activity types (agent-observed)
CREATE TYPE file_activity_type AS ENUM (
    'FILE_CREATE',
    'FILE_MODIFY',
    'FILE_DELETE',
    'FILE_READ',
    'FILE_EXECUTE',
    'FILE_ENCRYPT'
);

-- Persistence types (agent-observed)
CREATE TYPE persistence_type AS ENUM (
    'SCHEDULED_TASK',
    'SERVICE',
    'REGISTRY_RUN_KEY',
    'STARTUP_FOLDER',
    'CRONTAB',
    'SYSTEMD',
    'INIT_SCRIPT',
    'AUTOSTART'
);

-- Network intent types (agent-observed, before network activity)
CREATE TYPE network_intent_type AS ENUM (
    'DNS_QUERY',
    'CONNECTION_ATTEMPT',
    'LISTEN'
);

-- ============================================================================
-- PROCESS ACTIVITY
-- ============================================================================
-- Normalized process activity events from agents
-- Query-optimized for process tracking and analysis

CREATE TABLE process_activity (
    id BIGSERIAL NOT NULL PRIMARY KEY,
    -- Auto-incrementing ID (immutable, never reused)
    
    event_id UUID NOT NULL REFERENCES raw_events(event_id) ON DELETE RESTRICT,
    -- Foreign key to raw_events (MUST reference source event)
    
    machine_id VARCHAR(255) NOT NULL REFERENCES machines(machine_id) ON DELETE RESTRICT,
    -- Denormalized for query performance (host-centric queries)
    
    component_instance_id VARCHAR(255) NOT NULL REFERENCES component_instances(component_instance_id) ON DELETE RESTRICT,
    -- Denormalized for query performance
    
    observed_at TIMESTAMPTZ NOT NULL,
    -- Denormalized from raw_events.observed_at (for time-indexed queries)
    
    activity_type process_activity_type NOT NULL,
    -- Type of process activity (PROCESS_START, PROCESS_EXIT, etc.)
    
    process_pid INTEGER NOT NULL,
    -- Process ID (PID)
    -- INTEGER sufficient for PID ranges (typically 0 to 32768)
    
    parent_pid INTEGER,
    -- Parent process ID (PID)
    -- NULL if parent unknown
    
    process_name VARCHAR(255) NOT NULL,
    -- Process name (executable name)
    -- VARCHAR(255) sufficient for executable names
    
    process_path TEXT,
    -- Full path to process executable
    -- TEXT for unlimited length (paths can be long)
    
    command_line TEXT,
    -- Command line arguments
    -- TEXT for unlimited length (command lines can be long)
    
    user_name VARCHAR(255),
    -- User name running the process
    -- NULL if unknown
    
    user_id INTEGER,
    -- User ID (UID/GID) running the process
    -- NULL if unknown
    
    target_pid INTEGER,
    -- Target PID (for PROCESS_INJECT, PROCESS_MODIFY)
    -- NULL if not applicable
    
    target_process_name VARCHAR(255),
    -- Target process name (for PROCESS_INJECT, PROCESS_MODIFY)
    -- NULL if not applicable
    
    exit_code INTEGER,
    -- Exit code (for PROCESS_EXIT)
    -- NULL if not applicable
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT process_activity_pid_non_negative CHECK (process_pid >= 0),
    CONSTRAINT process_activity_parent_pid_non_negative CHECK (parent_pid IS NULL OR parent_pid >= 0),
    CONSTRAINT process_activity_target_pid_non_negative CHECK (target_pid IS NULL OR target_pid >= 0),
    CONSTRAINT process_activity_process_name_not_empty CHECK (LENGTH(TRIM(process_name)) > 0)
);

COMMENT ON TABLE process_activity IS 'Normalized process activity events from agents. Query-optimized for process tracking and analysis. Every row references raw_events.';
COMMENT ON COLUMN process_activity.event_id IS 'Foreign key to raw_events. MUST reference source event. Immutable.';
COMMENT ON COLUMN process_activity.process_pid IS 'Process ID (PID). Always present.';
COMMENT ON COLUMN process_activity.parent_pid IS 'Parent process ID. NULL if parent unknown (e.g., orphan process).';
COMMENT ON COLUMN process_activity.process_path IS 'Full path to process executable. NULL if path not available.';
COMMENT ON COLUMN process_activity.command_line IS 'Command line arguments. NULL if command line not available.';
COMMENT ON COLUMN process_activity.target_pid IS 'Target PID for injection/modification activities. NULL if not applicable.';

-- ============================================================================
-- FILE ACTIVITY
-- ============================================================================
-- Normalized file activity events from agents
-- Query-optimized for file tracking and analysis

CREATE TABLE file_activity (
    id BIGSERIAL NOT NULL PRIMARY KEY,
    -- Auto-incrementing ID (immutable, never reused)
    
    event_id UUID NOT NULL REFERENCES raw_events(event_id) ON DELETE RESTRICT,
    -- Foreign key to raw_events (MUST reference source event)
    
    machine_id VARCHAR(255) NOT NULL REFERENCES machines(machine_id) ON DELETE RESTRICT,
    -- Denormalized for query performance (host-centric queries)
    
    component_instance_id VARCHAR(255) NOT NULL REFERENCES component_instances(component_instance_id) ON DELETE RESTRICT,
    -- Denormalized for query performance
    
    observed_at TIMESTAMPTZ NOT NULL,
    -- Denormalized from raw_events.observed_at (for time-indexed queries)
    
    activity_type file_activity_type NOT NULL,
    -- Type of file activity (FILE_CREATE, FILE_MODIFY, FILE_DELETE, etc.)
    
    file_path TEXT NOT NULL,
    -- Full path to file
    -- TEXT for unlimited length (paths can be very long)
    
    file_hash_sha256 CHAR(64),
    -- SHA256 hash of file content
    -- NULL if hash not computed or file not accessible
    -- CHAR(64) for exactly 64 hex characters
    
    file_size BIGINT,
    -- File size in bytes
    -- NULL if size not available
    -- BIGINT for large files (up to 2^63-1 bytes)
    
    process_pid INTEGER NOT NULL,
    -- Process ID (PID) performing the file operation
    -- INTEGER sufficient for PID ranges
    
    process_name VARCHAR(255) NOT NULL,
    -- Process name performing the file operation
    -- VARCHAR(255) sufficient for executable names
    
    user_name VARCHAR(255),
    -- User name performing the file operation
    -- NULL if unknown
    
    encryption_key_present BOOLEAN,
    -- TRUE if encryption key detected (for FILE_ENCRYPT)
    -- NULL if not applicable
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT file_activity_file_path_not_empty CHECK (LENGTH(TRIM(file_path)) > 0),
    CONSTRAINT file_activity_pid_non_negative CHECK (process_pid >= 0),
    CONSTRAINT file_activity_file_size_non_negative CHECK (file_size IS NULL OR file_size >= 0),
    CONSTRAINT file_activity_file_hash_format CHECK (file_hash_sha256 IS NULL OR file_hash_sha256 ~ '^[a-fA-F0-9]{64}$')
);

COMMENT ON TABLE file_activity IS 'Normalized file activity events from agents. Query-optimized for file tracking and analysis. Every row references raw_events.';
COMMENT ON COLUMN file_activity.event_id IS 'Foreign key to raw_events. MUST reference source event. Immutable.';
COMMENT ON COLUMN file_activity.file_path IS 'Full path to file. Always present. No path assumptions (supports all OS path formats).';
COMMENT ON COLUMN file_activity.file_hash_sha256 IS 'SHA256 hash of file content. NULL if hash not computed or file not accessible. Used for file correlation.';
COMMENT ON COLUMN file_activity.file_size IS 'File size in bytes. NULL if size not available. Used for anomaly detection (sudden size changes).';

-- ============================================================================
-- PERSISTENCE
-- ============================================================================
-- Normalized persistence events from agents
-- Query-optimized for persistence tracking and analysis

CREATE TABLE persistence (
    id BIGSERIAL NOT NULL PRIMARY KEY,
    -- Auto-incrementing ID (immutable, never reused)
    
    event_id UUID NOT NULL REFERENCES raw_events(event_id) ON DELETE RESTRICT,
    -- Foreign key to raw_events (MUST reference source event)
    
    machine_id VARCHAR(255) NOT NULL REFERENCES machines(machine_id) ON DELETE RESTRICT,
    -- Denormalized for query performance (host-centric queries)
    
    component_instance_id VARCHAR(255) NOT NULL REFERENCES component_instances(component_instance_id) ON DELETE RESTRICT,
    -- Denormalized for query performance
    
    observed_at TIMESTAMPTZ NOT NULL,
    -- Denormalized from raw_events.observed_at (for time-indexed queries)
    
    persistence_type persistence_type NOT NULL,
    -- Type of persistence mechanism (SCHEDULED_TASK, SERVICE, etc.)
    
    persistence_key TEXT NOT NULL,
    -- Persistence key/identifier (registry key, file path, service name, etc.)
    -- TEXT for unlimited length (registry keys, paths can be long)
    
    target_path TEXT NOT NULL,
    -- Path to executable being persisted
    -- TEXT for unlimited length (paths can be long)
    
    target_command_line TEXT,
    -- Command line for persisted executable
    -- NULL if not applicable
    -- TEXT for unlimited length
    
    process_pid INTEGER NOT NULL,
    -- Process ID (PID) creating the persistence
    -- INTEGER sufficient for PID ranges
    
    process_name VARCHAR(255) NOT NULL,
    -- Process name creating the persistence
    -- VARCHAR(255) sufficient for executable names
    
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    -- TRUE if persistence is enabled, FALSE if disabled/removed
    -- For tracking persistence removal events
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT persistence_persistence_key_not_empty CHECK (LENGTH(TRIM(persistence_key)) > 0),
    CONSTRAINT persistence_target_path_not_empty CHECK (LENGTH(TRIM(target_path)) > 0),
    CONSTRAINT persistence_pid_non_negative CHECK (process_pid >= 0),
    CONSTRAINT persistence_process_name_not_empty CHECK (LENGTH(TRIM(process_name)) > 0)
);

COMMENT ON TABLE persistence IS 'Normalized persistence events from agents. Query-optimized for persistence tracking and analysis. Every row references raw_events.';
COMMENT ON COLUMN persistence.event_id IS 'Foreign key to raw_events. MUST reference source event. Immutable.';
COMMENT ON COLUMN persistence.persistence_key IS 'Persistence key/identifier. Examples: registry key path, scheduled task name, service name, crontab line.';
COMMENT ON COLUMN persistence.target_path IS 'Path to executable being persisted. Always present.';
COMMENT ON COLUMN persistence.enabled IS 'TRUE if persistence is enabled, FALSE if disabled/removed. Tracks both creation and removal events.';

-- ============================================================================
-- NETWORK INTENT (AGENT-SIDE)
-- ============================================================================
-- Normalized network intent events from agents (before network activity)
-- Query-optimized for network intent tracking and correlation with DPI flows

CREATE TABLE network_intent (
    id BIGSERIAL NOT NULL PRIMARY KEY,
    -- Auto-incrementing ID (immutable, never reused)
    
    event_id UUID NOT NULL REFERENCES raw_events(event_id) ON DELETE RESTRICT,
    -- Foreign key to raw_events (MUST reference source event)
    
    machine_id VARCHAR(255) NOT NULL REFERENCES machines(machine_id) ON DELETE RESTRICT,
    -- Denormalized for query performance (host-centric queries)
    
    component_instance_id VARCHAR(255) NOT NULL REFERENCES component_instances(component_instance_id) ON DELETE RESTRICT,
    -- Denormalized for query performance
    
    observed_at TIMESTAMPTZ NOT NULL,
    -- Denormalized from raw_events.observed_at (for time-indexed queries)
    
    intent_type network_intent_type NOT NULL,
    -- Type of network intent (DNS_QUERY, CONNECTION_ATTEMPT, LISTEN)
    
    process_pid INTEGER NOT NULL,
    -- Process ID (PID) initiating network intent
    -- INTEGER sufficient for PID ranges
    
    process_name VARCHAR(255) NOT NULL,
    -- Process name initiating network intent
    -- VARCHAR(255) sufficient for executable names
    
    remote_host VARCHAR(255),
    -- Remote hostname or IP address (for DNS_QUERY, CONNECTION_ATTEMPT)
    -- NULL for LISTEN
    -- VARCHAR(255) sufficient for hostnames and IP addresses
    
    remote_port INTEGER,
    -- Remote port (for CONNECTION_ATTEMPT, LISTEN)
    -- NULL for DNS_QUERY
    -- INTEGER sufficient for port range (0 to 65535)
    
    local_port INTEGER,
    -- Local port (for CONNECTION_ATTEMPT, LISTEN)
    -- NULL for DNS_QUERY
    -- INTEGER sufficient for port range (0 to 65535)
    
    protocol VARCHAR(16),
    -- Protocol (TCP, UDP, etc.)
    -- NULL if unknown
    -- VARCHAR(16) sufficient for protocol names
    
    dns_query_name VARCHAR(255),
    -- DNS query name (for DNS_QUERY only)
    -- NULL for other intent types
    -- VARCHAR(255) sufficient for DNS names (with length limits)
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT network_intent_pid_non_negative CHECK (process_pid >= 0),
    CONSTRAINT network_intent_remote_port_range CHECK (remote_port IS NULL OR (remote_port >= 0 AND remote_port <= 65535)),
    CONSTRAINT network_intent_local_port_range CHECK (local_port IS NULL OR (local_port >= 0 AND local_port <= 65535)),
    CONSTRAINT network_intent_process_name_not_empty CHECK (LENGTH(TRIM(process_name)) > 0)
);

COMMENT ON TABLE network_intent IS 'Normalized network intent events from agents (before network activity). Query-optimized for network intent tracking and correlation with DPI flows. Every row references raw_events.';
COMMENT ON COLUMN network_intent.event_id IS 'Foreign key to raw_events. MUST reference source event. Immutable.';
COMMENT ON COLUMN network_intent.intent_type IS 'Type of network intent: DNS_QUERY (before DNS resolution), CONNECTION_ATTEMPT (before connection), LISTEN (before listen).';
COMMENT ON COLUMN network_intent.remote_host IS 'Remote hostname or IP address. NULL for LISTEN. Used for correlation with DPI flows.';
COMMENT ON COLUMN network_intent.dns_query_name IS 'DNS query name (for DNS_QUERY only). Used for correlation with DNS table.';

-- ============================================================================
-- HEALTH / HEARTBEAT
-- ============================================================================
-- Normalized health/heartbeat events from agents
-- Query-optimized for component health monitoring

CREATE TABLE health_heartbeat (
    id BIGSERIAL NOT NULL PRIMARY KEY,
    -- Auto-incrementing ID (immutable, never reused)
    
    event_id UUID NOT NULL REFERENCES raw_events(event_id) ON DELETE RESTRICT,
    -- Foreign key to raw_events (MUST reference source event)
    
    machine_id VARCHAR(255) NOT NULL REFERENCES machines(machine_id) ON DELETE RESTRICT,
    -- Denormalized for query performance (host-centric queries)
    
    component_instance_id VARCHAR(255) NOT NULL REFERENCES component_instances(component_instance_id) ON DELETE RESTRICT,
    -- Denormalized for query performance
    
    observed_at TIMESTAMPTZ NOT NULL,
    -- Denormalized from raw_events.observed_at (for time-indexed queries)
    
    heartbeat_type VARCHAR(64) NOT NULL,
    -- Heartbeat type (e.g., 'periodic', 'health_check', 'component_start', 'component_stop')
    -- VARCHAR(64) sufficient for heartbeat type identifiers
    
    component_state component_state,
    -- Component state reported in heartbeat (from failure semantics contract)
    -- NULL if not reported
    
    uptime_seconds BIGINT,
    -- Component uptime in seconds
    -- NULL if not reported
    -- BIGINT for long uptimes
    
    event_count_since_start BIGINT,
    -- Number of events generated since component start
    -- NULL if not reported
    -- BIGINT for large event counts
    
    synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    -- TRUE if this is a synthetic heartbeat (generated by core due to no events received)
    -- FALSE if this is a real heartbeat from agent
    -- From failure semantics contract: "No events received" scenario
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT health_heartbeat_heartbeat_type_not_empty CHECK (LENGTH(TRIM(heartbeat_type)) > 0),
    CONSTRAINT health_heartbeat_uptime_non_negative CHECK (uptime_seconds IS NULL OR uptime_seconds >= 0),
    CONSTRAINT health_heartbeat_event_count_non_negative CHECK (event_count_since_start IS NULL OR event_count_since_start >= 0)
);

COMMENT ON TABLE health_heartbeat IS 'Normalized health/heartbeat events from agents. Query-optimized for component health monitoring. Every row references raw_events.';
COMMENT ON COLUMN health_heartbeat.event_id IS 'Foreign key to raw_events. MUST reference source event. Immutable.';
COMMENT ON COLUMN health_heartbeat.synthetic IS 'TRUE if this is a synthetic heartbeat generated by core due to no events received (timeout threshold exceeded). From failure semantics contract.';
COMMENT ON COLUMN health_heartbeat.component_state IS 'Component state reported in heartbeat (HEALTHY, DEGRADED, STALE, FAILED, BROKEN). NULL if not reported.';

-- ============================================================================
-- INDEXES (NORMALIZED AGENT)
-- ============================================================================

-- Process activity: Find by machine (host-centric queries)
CREATE INDEX idx_process_activity_machine_id 
    ON process_activity(machine_id);

-- Process activity: Find by component instance
CREATE INDEX idx_process_activity_component_instance_id 
    ON process_activity(component_instance_id);

-- Process activity: Find by time (time-indexed queries)
CREATE INDEX idx_process_activity_observed_at 
    ON process_activity(observed_at DESC);

-- Process activity: Find by PID (process tracking)
CREATE INDEX idx_process_activity_pid 
    ON process_activity(process_pid);

-- Process activity: Find by parent PID (process tree queries)
CREATE INDEX idx_process_activity_parent_pid 
    ON process_activity(parent_pid) 
    WHERE parent_pid IS NOT NULL;

-- Process activity: Find by process name (process name queries)
CREATE INDEX idx_process_activity_process_name 
    ON process_activity(process_name);

-- Process activity: Find by activity type
CREATE INDEX idx_process_activity_activity_type 
    ON process_activity(activity_type);

-- Process activity: Find by target PID (injection/modification queries)
CREATE INDEX idx_process_activity_target_pid 
    ON process_activity(target_pid) 
    WHERE target_pid IS NOT NULL;

-- File activity: Find by machine (host-centric queries)
CREATE INDEX idx_file_activity_machine_id 
    ON file_activity(machine_id);

-- File activity: Find by component instance
CREATE INDEX idx_file_activity_component_instance_id 
    ON file_activity(component_instance_id);

-- File activity: Find by time (time-indexed queries)
CREATE INDEX idx_file_activity_observed_at 
    ON file_activity(observed_at DESC);

-- File activity: Find by file path (file tracking)
CREATE INDEX idx_file_activity_file_path 
    ON file_activity USING gin (file_path gin_trgm_ops);
-- GIN index with trigram for partial path matching

-- File activity: Find by file hash (file correlation)
CREATE INDEX idx_file_activity_file_hash 
    ON file_activity(file_hash_sha256) 
    WHERE file_hash_sha256 IS NOT NULL;

-- File activity: Find by PID (process file activity queries)
CREATE INDEX idx_file_activity_pid 
    ON file_activity(process_pid);

-- File activity: Find by activity type
CREATE INDEX idx_file_activity_activity_type 
    ON file_activity(activity_type);

-- Persistence: Find by machine (host-centric queries)
CREATE INDEX idx_persistence_machine_id 
    ON persistence(machine_id);

-- Persistence: Find by component instance
CREATE INDEX idx_persistence_component_instance_id 
    ON persistence(component_instance_id);

-- Persistence: Find by time (time-indexed queries)
CREATE INDEX idx_persistence_observed_at 
    ON persistence(observed_at DESC);

-- Persistence: Find by persistence key (persistence tracking)
CREATE INDEX idx_persistence_persistence_key 
    ON persistence USING gin (persistence_key gin_trgm_ops);
-- GIN index with trigram for partial key matching

-- Persistence: Find by persistence type
CREATE INDEX idx_persistence_persistence_type 
    ON persistence(persistence_type);

-- Persistence: Find by target path
CREATE INDEX idx_persistence_target_path 
    ON persistence USING gin (target_path gin_trgm_ops);
-- GIN index with trigram for partial path matching

-- Persistence: Find enabled persistence (active persistence)
CREATE INDEX idx_persistence_enabled 
    ON persistence(enabled) 
    WHERE enabled = TRUE;

-- Network intent: Find by machine (host-centric queries)
CREATE INDEX idx_network_intent_machine_id 
    ON network_intent(machine_id);

-- Network intent: Find by component instance
CREATE INDEX idx_network_intent_component_instance_id 
    ON network_intent(component_instance_id);

-- Network intent: Find by time (time-indexed queries)
CREATE INDEX idx_network_intent_observed_at 
    ON network_intent(observed_at DESC);

-- Network intent: Find by PID (process network intent queries)
CREATE INDEX idx_network_intent_pid 
    ON network_intent(process_pid);

-- Network intent: Find by remote host (for correlation with DPI flows)
CREATE INDEX idx_network_intent_remote_host 
    ON network_intent(remote_host) 
    WHERE remote_host IS NOT NULL;

-- Network intent: Find by remote port (for correlation with DPI flows)
CREATE INDEX idx_network_intent_remote_port 
    ON network_intent(remote_port) 
    WHERE remote_port IS NOT NULL;

-- Network intent: Find by DNS query name (for correlation with DNS table)
CREATE INDEX idx_network_intent_dns_query_name 
    ON network_intent(dns_query_name) 
    WHERE dns_query_name IS NOT NULL;

-- Network intent: Find by intent type
CREATE INDEX idx_network_intent_intent_type 
    ON network_intent(intent_type);

-- Health heartbeat: Find by machine (host-centric queries)
CREATE INDEX idx_health_heartbeat_machine_id 
    ON health_heartbeat(machine_id);

-- Health heartbeat: Find by component instance (component health monitoring)
CREATE INDEX idx_health_heartbeat_component_instance_id 
    ON health_heartbeat(component_instance_id);

-- Health heartbeat: Find by time (time-indexed queries)
CREATE INDEX idx_health_heartbeat_observed_at 
    ON health_heartbeat(observed_at DESC);

-- Health heartbeat: Find by component state (component state monitoring)
CREATE INDEX idx_health_heartbeat_component_state 
    ON health_heartbeat(component_state) 
    WHERE component_state IS NOT NULL;

-- Health heartbeat: Find synthetic heartbeats (stale component detection)
CREATE INDEX idx_health_heartbeat_synthetic 
    ON health_heartbeat(synthetic) 
    WHERE synthetic = TRUE;
