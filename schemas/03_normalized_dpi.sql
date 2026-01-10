-- RansomEye v1.0 Normalized DPI Tables
-- AUTHORITATIVE: Query-optimized normalized tables for DPI probe events
-- PostgreSQL 14+ compatible
-- Every normalized row MUST reference its raw event

-- Flow direction enumeration
CREATE TYPE flow_direction AS ENUM (
    'INBOUND',
    'OUTBOUND',
    'INTERNAL'
);

-- Flow state enumeration
CREATE TYPE flow_state AS ENUM (
    'ESTABLISHED',
    'CLOSED',
    'RESET',
    'TIMEOUT'
);

-- DNS record type enumeration
CREATE TYPE dns_record_type AS ENUM (
    'A',
    'AAAA',
    'CNAME',
    'MX',
    'TXT',
    'NS',
    'PTR',
    'SOA',
    'SRV',
    'OTHER'
);

-- DNS query type enumeration (query or response)
CREATE TYPE dns_query_type AS ENUM (
    'QUERY',
    'RESPONSE'
);

-- Deception type enumeration
CREATE TYPE deception_type AS ENUM (
    'HONEYPOT_TRIGGER',
    'DECOY_FILE_ACCESS',
    'DECOY_PROCESS_EXECUTION',
    'DECOY_NETWORK_CONNECTION',
    'HONEYTOKEN_ACCESS'
);

-- ============================================================================
-- DPI FLOWS
-- ============================================================================
-- Normalized network flows observed by DPI probe
-- Query-optimized for network flow analysis and correlation with agent network_intent

CREATE TABLE dpi_flows (
    id BIGSERIAL NOT NULL PRIMARY KEY,
    -- Auto-incrementing ID (immutable, never reused)
    
    event_id UUID NOT NULL REFERENCES raw_events(event_id) ON DELETE RESTRICT,
    -- Foreign key to raw_events (MUST reference source event)
    
    machine_id VARCHAR(255) REFERENCES machines(machine_id) ON DELETE RESTRICT,
    -- Foreign key to machines (NULL if machine not identified)
    -- Machine is identified by correlating flow with agent events
    
    component_instance_id VARCHAR(255) NOT NULL REFERENCES component_instances(component_instance_id) ON DELETE RESTRICT,
    -- DPI component instance that observed the flow
    
    observed_at TIMESTAMPTZ NOT NULL,
    -- Denormalized from raw_events.observed_at (for time-indexed queries)
    
    flow_started_at TIMESTAMPTZ NOT NULL,
    -- When flow was first observed (may be before observed_at if flow already existed)
    
    flow_ended_at TIMESTAMPTZ,
    -- When flow ended (NULL if flow still active)
    
    flow_state flow_state NOT NULL,
    -- Flow state (ESTABLISHED, CLOSED, RESET, TIMEOUT)
    
    direction flow_direction NOT NULL,
    -- Flow direction relative to observed network segment
    
    local_ip INET NOT NULL,
    -- Local IP address (from perspective of flow observation)
    -- INET for efficient IP address storage and queries
    
    local_port INTEGER NOT NULL,
    -- Local port
    -- INTEGER sufficient for port range (0 to 65535)
    
    remote_ip INET NOT NULL,
    -- Remote IP address
    -- INET for efficient IP address storage and queries
    
    remote_port INTEGER NOT NULL,
    -- Remote port
    -- INTEGER sufficient for port range (0 to 65535)
    
    protocol VARCHAR(16) NOT NULL,
    -- Protocol (TCP, UDP, ICMP, etc.)
    -- VARCHAR(16) sufficient for protocol names
    
    bytes_sent BIGINT NOT NULL DEFAULT 0,
    -- Bytes sent from local to remote
    -- BIGINT for large flows (up to 2^63-1 bytes)
    
    bytes_received BIGINT NOT NULL DEFAULT 0,
    -- Bytes received from remote to local
    -- BIGINT for large flows (up to 2^63-1 bytes)
    
    packets_sent BIGINT NOT NULL DEFAULT 0,
    -- Packets sent from local to remote
    -- BIGINT for large packet counts
    
    packets_received BIGINT NOT NULL DEFAULT 0,
    -- Packets received from remote to local
    -- BIGINT for large packet counts
    
    duration_seconds INTEGER,
    -- Flow duration in seconds
    -- NULL if flow still active
    -- INTEGER sufficient for flow durations (up to ~68 years)
    
    application_protocol VARCHAR(64),
    -- Application protocol detected by DPI (HTTP, HTTPS, FTP, SSH, etc.)
    -- NULL if not detected
    -- VARCHAR(64) sufficient for application protocol names
    
    server_name_indication VARCHAR(255),
    -- SNI from TLS handshake (for HTTPS)
    -- NULL if not applicable or not available
    -- VARCHAR(255) sufficient for SNI length limits
    
    user_agent TEXT,
    -- User-Agent from HTTP request (for HTTP/HTTPS)
    -- NULL if not applicable or not available
    -- TEXT for unlimited length (user agents can be long)
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT dpi_flows_local_port_range CHECK (local_port >= 0 AND local_port <= 65535),
    CONSTRAINT dpi_flows_remote_port_range CHECK (remote_port >= 0 AND remote_port <= 65535),
    CONSTRAINT dpi_flows_bytes_sent_non_negative CHECK (bytes_sent >= 0),
    CONSTRAINT dpi_flows_bytes_received_non_negative CHECK (bytes_received >= 0),
    CONSTRAINT dpi_flows_packets_sent_non_negative CHECK (packets_sent >= 0),
    CONSTRAINT dpi_flows_packets_received_non_negative CHECK (packets_received >= 0),
    CONSTRAINT dpi_flows_duration_non_negative CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
    CONSTRAINT dpi_flows_started_before_ended CHECK (flow_ended_at IS NULL OR flow_started_at <= flow_ended_at),
    CONSTRAINT dpi_flows_started_before_observed CHECK (flow_started_at <= observed_at)
);

COMMENT ON TABLE dpi_flows IS 'Normalized network flows observed by DPI probe. Query-optimized for network flow analysis and correlation with agent network_intent. Every row references raw_events.';
COMMENT ON COLUMN dpi_flows.event_id IS 'Foreign key to raw_events. MUST reference source event. Immutable.';
COMMENT ON COLUMN dpi_flows.machine_id IS 'Foreign key to machines. NULL if machine not identified (DPI may observe flows before machine is identified). Machine is identified by correlating flow with agent events.';
COMMENT ON COLUMN dpi_flows.flow_started_at IS 'When flow was first observed. May be before observed_at if flow already existed when DPI started observing.';
COMMENT ON COLUMN dpi_flows.flow_ended_at IS 'When flow ended. NULL if flow still active. Used for flow duration calculation.';
COMMENT ON COLUMN dpi_flows.local_ip IS 'Local IP address (from perspective of flow observation). INET type for efficient IP queries and subnet matching.';
COMMENT ON COLUMN dpi_flows.remote_ip IS 'Remote IP address. INET type for efficient IP queries and subnet matching.';
COMMENT ON COLUMN dpi_flows.application_protocol IS 'Application protocol detected by DPI (HTTP, HTTPS, FTP, SSH, etc.). NULL if not detected.';
COMMENT ON COLUMN dpi_flows.server_name_indication IS 'SNI from TLS handshake (for HTTPS). Used for domain-based correlation. NULL if not applicable.';

-- ============================================================================
-- DNS
-- ============================================================================
-- Normalized DNS queries and responses observed by DPI probe
-- Query-optimized for DNS analysis and correlation with agent network_intent

CREATE TABLE dns (
    id BIGSERIAL NOT NULL PRIMARY KEY,
    -- Auto-incrementing ID (immutable, never reused)
    
    event_id UUID NOT NULL REFERENCES raw_events(event_id) ON DELETE RESTRICT,
    -- Foreign key to raw_events (MUST reference source event)
    
    machine_id VARCHAR(255) REFERENCES machines(machine_id) ON DELETE RESTRICT,
    -- Foreign key to machines (NULL if machine not identified)
    -- Machine is identified by correlating DNS query with agent events
    
    component_instance_id VARCHAR(255) NOT NULL REFERENCES component_instances(component_instance_id) ON DELETE RESTRICT,
    -- DPI component instance that observed the DNS activity
    
    observed_at TIMESTAMPTZ NOT NULL,
    -- Denormalized from raw_events.observed_at (for time-indexed queries)
    
    query_type dns_query_type NOT NULL,
    -- Query type: QUERY (DNS query) or RESPONSE (DNS response)
    
    query_name VARCHAR(255) NOT NULL,
    -- DNS query name (domain name being queried)
    -- VARCHAR(255) sufficient for DNS name length limits (253 characters max)
    
    record_type dns_record_type NOT NULL,
    -- DNS record type (A, AAAA, CNAME, MX, etc.)
    
    client_ip INET NOT NULL,
    -- Client IP address making the DNS query
    -- INET for efficient IP address storage and queries
    
    server_ip INET,
    -- DNS server IP address (for RESPONSE only)
    -- NULL for QUERY
    -- INET for efficient IP address storage and queries
    
    response_code INTEGER,
    -- DNS response code (0=NOERROR, 3=NXDOMAIN, etc.)
    -- NULL for QUERY
    -- INTEGER sufficient for DNS response codes (0 to 15)
    
    response_time_ms INTEGER,
    -- DNS response time in milliseconds (for RESPONSE only)
    -- NULL for QUERY or if response time not measured
    -- INTEGER sufficient for response times (up to ~24 days in ms)
    
    resolved_ips INET[],
    -- Array of resolved IP addresses (for RESPONSE only)
    -- Empty array for QUERY or NXDOMAIN
    -- INET[] for efficient IP address array storage
    
    canonical_name VARCHAR(255),
    -- CNAME target (for CNAME records)
    -- NULL if not applicable
    -- VARCHAR(255) sufficient for DNS name length limits
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT dns_query_name_not_empty CHECK (LENGTH(TRIM(query_name)) > 0),
    CONSTRAINT dns_response_code_range CHECK (response_code IS NULL OR (response_code >= 0 AND response_code <= 15)),
    CONSTRAINT dns_response_time_non_negative CHECK (response_time_ms IS NULL OR response_time_ms >= 0)
);

COMMENT ON TABLE dns IS 'Normalized DNS queries and responses observed by DPI probe. Query-optimized for DNS analysis and correlation with agent network_intent. Every row references raw_events.';
COMMENT ON COLUMN dns.event_id IS 'Foreign key to raw_events. MUST reference source event. Immutable.';
COMMENT ON COLUMN dns.machine_id IS 'Foreign key to machines. NULL if machine not identified (DPI may observe DNS before machine is identified). Machine is identified by correlating DNS query with agent events.';
COMMENT ON COLUMN dns.query_type IS 'Query type: QUERY (DNS query observed) or RESPONSE (DNS response observed).';
COMMENT ON COLUMN dns.query_name IS 'DNS query name (domain name being queried). Always present. Used for domain-based analysis and correlation.';
COMMENT ON COLUMN dns.resolved_ips IS 'Array of resolved IP addresses (for RESPONSE only). Empty array for QUERY or NXDOMAIN. Used for IP-based correlation with flows.';
COMMENT ON COLUMN dns.canonical_name IS 'CNAME target (for CNAME records). NULL if not applicable. Used for DNS resolution chain analysis.';

-- ============================================================================
-- DECEPTION
-- ============================================================================
-- Normalized deception events (honeypot triggers, decoy access, etc.)
-- Query-optimized for deception analysis and incident correlation

CREATE TABLE deception (
    id BIGSERIAL NOT NULL PRIMARY KEY,
    -- Auto-incrementing ID (immutable, never reused)
    
    event_id UUID NOT NULL REFERENCES raw_events(event_id) ON DELETE RESTRICT,
    -- Foreign key to raw_events (MUST reference source event)
    
    machine_id VARCHAR(255) REFERENCES machines(machine_id) ON DELETE RESTRICT,
    -- Foreign key to machines (NULL if machine not identified)
    -- Machine is identified by correlating deception event with agent events
    
    component_instance_id VARCHAR(255) NOT NULL REFERENCES component_instances(component_instance_id) ON DELETE RESTRICT,
    -- Component instance that observed/deployed the deception
    
    observed_at TIMESTAMPTZ NOT NULL,
    -- Denormalized from raw_events.observed_at (for time-indexed queries)
    
    deception_type deception_type NOT NULL,
    -- Type of deception event (HONEYPOT_TRIGGER, DECOY_FILE_ACCESS, etc.)
    
    deception_target TEXT NOT NULL,
    -- Deception target identifier (file path, process name, network endpoint, etc.)
    -- TEXT for unlimited length (paths, endpoints can be long)
    
    source_ip INET,
    -- Source IP address of the deception trigger
    -- NULL if not applicable or not available
    -- INET for efficient IP address storage and queries
    
    source_process_pid INTEGER,
    -- Source process PID (for file/process deception)
    -- NULL if not applicable or not available
    -- INTEGER sufficient for PID ranges
    
    source_process_name VARCHAR(255),
    -- Source process name (for file/process deception)
    -- NULL if not applicable or not available
    -- VARCHAR(255) sufficient for executable names
    
    user_name VARCHAR(255),
    -- User name that triggered the deception
    -- NULL if not applicable or not available
    -- VARCHAR(255) sufficient for user names
    
    honeytoken_value TEXT,
    -- Honeytoken value that was accessed (for HONEYTOKEN_ACCESS)
    -- NULL if not applicable
    -- TEXT for unlimited length (honeytokens can be long)
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT deception_deception_target_not_empty CHECK (LENGTH(TRIM(deception_target)) > 0),
    CONSTRAINT deception_source_pid_non_negative CHECK (source_process_pid IS NULL OR source_process_pid >= 0)
);

COMMENT ON TABLE deception IS 'Normalized deception events (honeypot triggers, decoy access, etc.). Query-optimized for deception analysis and incident correlation. Every row references raw_events.';
COMMENT ON COLUMN deception.event_id IS 'Foreign key to raw_events. MUST reference source event. Immutable.';
COMMENT ON COLUMN deception.machine_id IS 'Foreign key to machines. NULL if machine not identified. Machine is identified by correlating deception event with agent events.';
COMMENT ON COLUMN deception.deception_target IS 'Deception target identifier. Examples: decoy file path, honeypot endpoint, honeytoken value. Always present.';
COMMENT ON COLUMN deception.source_process_pid IS 'Source process PID that triggered the deception. NULL if not applicable (e.g., network-based deception).';

-- ============================================================================
-- INDEXES (NORMALIZED DPI)
-- ============================================================================

-- DPI flows: Find by component instance
CREATE INDEX idx_dpi_flows_component_instance_id 
    ON dpi_flows(component_instance_id);

-- DPI flows: Find by machine (host-centric queries)
CREATE INDEX idx_dpi_flows_machine_id 
    ON dpi_flows(machine_id) 
    WHERE machine_id IS NOT NULL;

-- DPI flows: Find by time (time-indexed queries)
CREATE INDEX idx_dpi_flows_observed_at 
    ON dpi_flows(observed_at DESC);

-- DPI flows: Find by flow start time (flow timeline queries)
CREATE INDEX idx_dpi_flows_flow_started_at 
    ON dpi_flows(flow_started_at DESC);

-- DPI flows: Find by local IP (IP-based queries)
CREATE INDEX idx_dpi_flows_local_ip 
    ON dpi_flows(local_ip);

-- DPI flows: Find by remote IP (IP-based queries)
CREATE INDEX idx_dpi_flows_remote_ip 
    ON dpi_flows(remote_ip);

-- DPI flows: Find by local port (port-based queries)
CREATE INDEX idx_dpi_flows_local_port 
    ON dpi_flows(local_port);

-- DPI flows: Find by remote port (port-based queries)
CREATE INDEX idx_dpi_flows_remote_port 
    ON dpi_flows(remote_port);

-- DPI flows: Find by protocol
CREATE INDEX idx_dpi_flows_protocol 
    ON dpi_flows(protocol);

-- DPI flows: Find by flow state (active flows, closed flows, etc.)
CREATE INDEX idx_dpi_flows_flow_state 
    ON dpi_flows(flow_state);

-- DPI flows: Find by application protocol (HTTP, HTTPS, etc.)
CREATE INDEX idx_dpi_flows_application_protocol 
    ON dpi_flows(application_protocol) 
    WHERE application_protocol IS NOT NULL;

-- DPI flows: Find by SNI (domain-based correlation)
CREATE INDEX idx_dpi_flows_server_name_indication 
    ON dpi_flows(server_name_indication) 
    WHERE server_name_indication IS NOT NULL;

-- DPI flows: Find active flows (for flow correlation)
CREATE INDEX idx_dpi_flows_active 
    ON dpi_flows(local_ip, local_port, remote_ip, remote_port, protocol) 
    WHERE flow_ended_at IS NULL;

-- DNS: Find by component instance
CREATE INDEX idx_dns_component_instance_id 
    ON dns(component_instance_id);

-- DNS: Find by machine (host-centric queries)
CREATE INDEX idx_dns_machine_id 
    ON dns(machine_id) 
    WHERE machine_id IS NOT NULL;

-- DNS: Find by time (time-indexed queries)
CREATE INDEX idx_dns_observed_at 
    ON dns(observed_at DESC);

-- DNS: Find by query name (domain-based queries)
CREATE INDEX idx_dns_query_name 
    ON dns(query_name);

-- DNS: Find by client IP (IP-based queries)
CREATE INDEX idx_dns_client_ip 
    ON dns(client_ip);

-- DNS: Find by server IP (DNS server queries)
CREATE INDEX idx_dns_server_ip 
    ON dns(server_ip) 
    WHERE server_ip IS NOT NULL;

-- DNS: Find by record type
CREATE INDEX idx_dns_record_type 
    ON dns(record_type);

-- DNS: Find by query type (QUERY vs RESPONSE)
CREATE INDEX idx_dns_query_type 
    ON dns(query_type);

-- DNS: Find by response code (NXDOMAIN, etc.)
CREATE INDEX idx_dns_response_code 
    ON dns(response_code) 
    WHERE response_code IS NOT NULL;

-- DNS: Find DNS responses with resolved IPs (for IP-based correlation)
CREATE INDEX idx_dns_resolved_ips 
    ON dns USING gin (resolved_ips);

-- Deception: Find by component instance
CREATE INDEX idx_deception_component_instance_id 
    ON deception(component_instance_id);

-- Deception: Find by machine (host-centric queries)
CREATE INDEX idx_deception_machine_id 
    ON deception(machine_id) 
    WHERE machine_id IS NOT NULL;

-- Deception: Find by time (time-indexed queries)
CREATE INDEX idx_deception_observed_at 
    ON deception(observed_at DESC);

-- Deception: Find by deception type
CREATE INDEX idx_deception_deception_type 
    ON deception(deception_type);

-- Deception: Find by source IP (IP-based queries)
CREATE INDEX idx_deception_source_ip 
    ON deception(source_ip) 
    WHERE source_ip IS NOT NULL;

-- Deception: Find by source process PID (process-based queries)
CREATE INDEX idx_deception_source_process_pid 
    ON deception(source_process_pid) 
    WHERE source_process_pid IS NOT NULL;

-- Deception: Find by source process name (process-based queries)
CREATE INDEX idx_deception_source_process_name 
    ON deception(source_process_name) 
    WHERE source_process_name IS NOT NULL;

-- Deception: Find by deception target (deception analysis)
CREATE INDEX idx_deception_deception_target 
    ON deception USING gin (deception_target gin_trgm_ops);
-- GIN index with trigram for partial target matching
