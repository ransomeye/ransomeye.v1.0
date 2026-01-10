-- RansomEye v1.0 Core Identity Tables
-- AUTHORITATIVE: Immutable schema for machine and component identity
-- PostgreSQL 14+ compatible

-- Component type enumeration (matches event envelope enum exactly)
CREATE TYPE component_type AS ENUM (
    'linux_agent',
    'windows_agent',
    'dpi',
    'core'
);

-- Component state enumeration (from failure semantics contract)
CREATE TYPE component_state AS ENUM (
    'HEALTHY',
    'DEGRADED',
    'STALE',
    'FAILED',
    'BROKEN'
);

-- ============================================================================
-- MACHINES (HOSTS)
-- ============================================================================
-- Authoritative registry of all machines that have sent events
-- Machine-first modeling: host-centric, not event-centric

CREATE TABLE machines (
    machine_id VARCHAR(255) NOT NULL PRIMARY KEY,
    -- machine_id is the canonical identifier from event envelope
    -- VARCHAR(255) sufficient for any machine identifier format
    
    first_seen_at TIMESTAMPTZ NOT NULL,
    -- First event received from this machine
    
    last_seen_at TIMESTAMPTZ NOT NULL,
    -- Last event received from this machine
    
    total_event_count BIGINT NOT NULL DEFAULT 0,
    -- Total events received from this machine (for monitoring)
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT machines_machine_id_not_empty CHECK (LENGTH(TRIM(machine_id)) > 0),
    CONSTRAINT machines_first_seen_before_last_seen CHECK (first_seen_at <= last_seen_at)
);

COMMENT ON TABLE machines IS 'Authoritative registry of all machines (hosts) that have generated events. Machine-first modeling: host-centric.';
COMMENT ON COLUMN machines.machine_id IS 'Canonical machine identifier from event envelope. MUST match event.machine_id exactly.';
COMMENT ON COLUMN machines.first_seen_at IS 'Timestamp of first event received from this machine. Set on INSERT, never updated.';
COMMENT ON COLUMN machines.last_seen_at IS 'Timestamp of last event received from this machine. Updated on every event.';
COMMENT ON COLUMN machines.total_event_count IS 'Total number of events received from this machine. Incremented on every event.';

-- ============================================================================
-- COMPONENT INSTANCES
-- ============================================================================
-- Registry of all component instances (agent/DPI instances)
-- Tracks component_instance_id across time

CREATE TABLE component_instances (
    component_instance_id VARCHAR(255) NOT NULL PRIMARY KEY,
    -- component_instance_id is the canonical identifier from event envelope
    
    machine_id VARCHAR(255) NOT NULL REFERENCES machines(machine_id) ON DELETE RESTRICT,
    -- Foreign key to machines table
    
    component component_type NOT NULL,
    -- Component type: linux_agent, windows_agent, dpi, core
    
    current_state component_state NOT NULL DEFAULT 'HEALTHY',
    -- Current component state (from failure semantics contract)
    
    state_changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- When current_state was last changed
    
    first_seen_at TIMESTAMPTZ NOT NULL,
    -- First event received from this component instance
    
    last_seen_at TIMESTAMPTZ NOT NULL,
    -- Last event received from this component instance
    
    last_sequence BIGINT,
    -- Last sequence number received (for gap detection)
    -- NULL if no events received yet
    -- BIGINT covers uint64 range (0 to 2^64-1)
    
    total_event_count BIGINT NOT NULL DEFAULT 0,
    -- Total events received from this component instance
    
    integrity_chain_broken BOOLEAN NOT NULL DEFAULT FALSE,
    -- TRUE if integrity chain is broken (from failure semantics)
    -- Once TRUE, remains TRUE until manual intervention
    
    last_hash_sha256 CHAR(64),
    -- Last hash_sha256 received (for integrity chain validation)
    -- NULL if no events received yet or chain broken
    -- CHAR(64) for exactly 64 hex characters
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT component_instances_instance_id_not_empty CHECK (LENGTH(TRIM(component_instance_id)) > 0),
    CONSTRAINT component_instances_first_seen_before_last_seen CHECK (first_seen_at <= last_seen_at),
    CONSTRAINT component_instances_last_sequence_non_negative CHECK (last_sequence IS NULL OR last_sequence >= 0),
    CONSTRAINT component_instances_last_hash_format CHECK (last_hash_sha256 IS NULL OR last_hash_sha256 ~ '^[a-fA-F0-9]{64}$')
);

COMMENT ON TABLE component_instances IS 'Registry of all component instances (agent/DPI instances). Tracks sequence, state, and integrity chain per instance.';
COMMENT ON COLUMN component_instances.component_instance_id IS 'Canonical component instance identifier from event envelope. MUST match event.component_instance_id exactly.';
COMMENT ON COLUMN component_instances.last_sequence IS 'Last sequence number received. Used for gap detection and out-of-order detection. NULL if no events received.';
COMMENT ON COLUMN component_instances.integrity_chain_broken IS 'TRUE if integrity chain is broken. Once TRUE, remains TRUE until manual intervention. All subsequent events from this instance marked as CHAIN_BROKEN.';
COMMENT ON COLUMN component_instances.last_hash_sha256 IS 'Last hash_sha256 received. Used for integrity chain validation. Must match prev_hash_sha256 of next event.';

-- ============================================================================
-- COMPONENT IDENTITY HISTORY
-- ============================================================================
-- Historical record of identity changes (hostname, boot_id, agent_version)
-- Immutable log of identity transitions per component instance

CREATE TABLE component_identity_history (
    id BIGSERIAL NOT NULL PRIMARY KEY,
    -- Auto-incrementing ID (immutable, never reused)
    
    component_instance_id VARCHAR(255) NOT NULL REFERENCES component_instances(component_instance_id) ON DELETE RESTRICT,
    -- Foreign key to component_instances
    
    hostname VARCHAR(255) NOT NULL,
    -- Hostname at time of identity snapshot
    -- VARCHAR(255) sufficient for hostname length limits
    
    boot_id VARCHAR(255) NOT NULL,
    -- Boot ID at time of identity snapshot
    -- VARCHAR(255) sufficient for boot ID format (UUID on most systems)
    
    agent_version VARCHAR(255) NOT NULL,
    -- Agent version at time of identity snapshot
    -- VARCHAR(255) sufficient for version strings
    
    first_observed_at TIMESTAMPTZ NOT NULL,
    -- First event observed with this identity (observed_at from event)
    
    last_observed_at TIMESTAMPTZ NOT NULL,
    -- Last event observed with this identity (observed_at from event)
    
    event_count BIGINT NOT NULL DEFAULT 1,
    -- Number of events observed with this identity
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT component_identity_history_hostname_not_empty CHECK (LENGTH(TRIM(hostname)) > 0),
    CONSTRAINT component_identity_history_boot_id_not_empty CHECK (LENGTH(TRIM(boot_id)) > 0),
    CONSTRAINT component_identity_history_agent_version_not_empty CHECK (LENGTH(TRIM(agent_version)) > 0),
    CONSTRAINT component_identity_history_first_before_last CHECK (first_observed_at <= last_observed_at)
);

COMMENT ON TABLE component_identity_history IS 'Immutable historical log of identity changes (hostname, boot_id, agent_version) per component instance. Tracks identity transitions over time.';
COMMENT ON COLUMN component_identity_history.hostname IS 'Hostname from event.identity.hostname. Changes when machine hostname changes.';
COMMENT ON COLUMN component_identity_history.boot_id IS 'Boot ID from event.identity.boot_id. Changes on each system boot.';
COMMENT ON COLUMN component_identity_history.agent_version IS 'Agent version from event.identity.agent_version. Changes when agent is upgraded.';

-- Index for finding current identity for a component instance
-- Latest entry (by created_at) represents current identity
CREATE INDEX idx_component_identity_history_instance_created 
    ON component_identity_history(component_instance_id, created_at DESC);

-- Index for finding identity history by time range
CREATE INDEX idx_component_identity_history_first_observed 
    ON component_identity_history(first_observed_at);

-- ============================================================================
-- INDEXES (CORE IDENTITY)
-- ============================================================================

-- Machines: Find machines by last seen (for staleness detection)
CREATE INDEX idx_machines_last_seen_at 
    ON machines(last_seen_at DESC);

-- Component instances: Find instances by machine
CREATE INDEX idx_component_instances_machine_id 
    ON component_instances(machine_id);

-- Component instances: Find instances by component type
CREATE INDEX idx_component_instances_component 
    ON component_instances(component);

-- Component instances: Find instances by state (for monitoring)
CREATE INDEX idx_component_instances_state 
    ON component_instances(current_state);

-- Component instances: Find instances by last seen (for staleness detection)
CREATE INDEX idx_component_instances_last_seen_at 
    ON component_instances(last_seen_at DESC);

-- Component instances: Find instances with broken integrity chains
CREATE INDEX idx_component_instances_integrity_broken 
    ON component_instances(integrity_chain_broken) 
    WHERE integrity_chain_broken = TRUE;
