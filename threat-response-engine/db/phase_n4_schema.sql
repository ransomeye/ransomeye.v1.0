-- RansomEye v1.0 Phase N4 - Rate Limiting, Blast Radius & Post-Incident Accountability
-- AUTHORITATIVE: Database schema for Phase N4 safety controls
-- PostgreSQL 14+ compatible

-- ============================================================================
-- RATE LIMITS
-- ============================================================================
-- Tracks rate limit usage (immutable log)

CREATE TABLE tre_rate_limits (
    rate_limit_id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    -- UUID v4 for rate limit record identifier
    
    user_id VARCHAR(255) NOT NULL,
    -- User identifier
    
    incident_id UUID,
    -- Incident identifier (if applicable)
    
    machine_id VARCHAR(255),
    -- Machine identifier (if applicable)
    
    limit_type VARCHAR(50) NOT NULL,
    -- Type of limit: PER_USER_PER_MINUTE, PER_INCIDENT_TOTAL, PER_HOST_PER_10_MINUTES, EMERGENCY_OVERRIDE_PER_INCIDENT
    
    limit_value INTEGER NOT NULL,
    -- Limit value (10, 25, 5, 2)
    
    current_count INTEGER NOT NULL,
    -- Current count at time of check
    
    action_id UUID,
    -- Action identifier that triggered limit check
    
    is_emergency BOOLEAN NOT NULL DEFAULT FALSE,
    -- Whether this is an emergency override
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT tre_rate_limits_limit_type_check CHECK (
        limit_type IN ('PER_USER_PER_MINUTE', 'PER_INCIDENT_TOTAL', 'PER_HOST_PER_10_MINUTES', 'EMERGENCY_OVERRIDE_PER_INCIDENT')
    )
);

COMMENT ON TABLE tre_rate_limits IS 'Immutable log of rate limit checks. All rate limit hits are recorded.';
COMMENT ON COLUMN tre_rate_limits.limit_type IS 'Type of rate limit: PER_USER_PER_MINUTE (10), PER_INCIDENT_TOTAL (25), PER_HOST_PER_10_MINUTES (5), EMERGENCY_OVERRIDE_PER_INCIDENT (2)';

-- Indexes for tre_rate_limits
CREATE INDEX idx_tre_rate_limits_user_id ON tre_rate_limits(user_id);
CREATE INDEX idx_tre_rate_limits_incident_id ON tre_rate_limits(incident_id) WHERE incident_id IS NOT NULL;
CREATE INDEX idx_tre_rate_limits_machine_id ON tre_rate_limits(machine_id) WHERE machine_id IS NOT NULL;
CREATE INDEX idx_tre_rate_limits_created_at ON tre_rate_limits(created_at);

-- ============================================================================
-- BLAST RADIUS
-- ============================================================================
-- Tracks blast radius declarations and validations (immutable log)

CREATE TABLE tre_blast_radius (
    blast_radius_id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    -- UUID v4 for blast radius record identifier
    
    action_id UUID NOT NULL REFERENCES response_actions(action_id) ON DELETE RESTRICT,
    -- Foreign key to response_actions table
    
    incident_id UUID NOT NULL REFERENCES incidents(incident_id) ON DELETE RESTRICT,
    -- Foreign key to incidents table
    
    blast_scope VARCHAR(20) NOT NULL,
    -- Blast scope: HOST, GROUP, NETWORK, GLOBAL
    
    target_count INTEGER NOT NULL,
    -- Expected target count
    
    resolved_target_count INTEGER NOT NULL,
    -- Actual resolved target count
    
    expected_impact VARCHAR(20) NOT NULL,
    -- Expected impact: LOW, MEDIUM, HIGH
    
    requires_approval BOOLEAN NOT NULL,
    -- Whether blast scope requires approval
    
    validation_status VARCHAR(20) NOT NULL,
    -- Validation status: VALID, REJECTED
    
    rejection_reason TEXT,
    -- Reason for rejection (if rejected)
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT tre_blast_radius_blast_scope_check CHECK (
        blast_scope IN ('HOST', 'GROUP', 'NETWORK', 'GLOBAL')
    ),
    CONSTRAINT tre_blast_radius_expected_impact_check CHECK (
        expected_impact IN ('LOW', 'MEDIUM', 'HIGH')
    ),
    CONSTRAINT tre_blast_radius_validation_status_check CHECK (
        validation_status IN ('VALID', 'REJECTED')
    )
);

COMMENT ON TABLE tre_blast_radius IS 'Immutable log of blast radius declarations and validations. All blast radius checks are recorded.';
COMMENT ON COLUMN tre_blast_radius.blast_scope IS 'Blast scope: HOST (single host), GROUP (group of hosts), NETWORK (network segment), GLOBAL (all hosts)';
COMMENT ON COLUMN tre_blast_radius.target_count IS 'Expected target count (must match resolved_target_count)';

-- Indexes for tre_blast_radius
CREATE INDEX idx_tre_blast_radius_action_id ON tre_blast_radius(action_id);
CREATE INDEX idx_tre_blast_radius_incident_id ON tre_blast_radius(incident_id);
CREATE INDEX idx_tre_blast_radius_validation_status ON tre_blast_radius(validation_status);

-- ============================================================================
-- INCIDENT ATTESTATIONS
-- ============================================================================
-- Mandatory attestations after destructive actions (immutable)

CREATE TABLE incident_attestations (
    attestation_id UUID NOT NULL PRIMARY KEY,
    -- UUID v4 for attestation identifier
    
    incident_id UUID NOT NULL REFERENCES incidents(incident_id) ON DELETE RESTRICT,
    -- Foreign key to incidents table
    
    action_id UUID NOT NULL REFERENCES response_actions(action_id) ON DELETE RESTRICT,
    -- Foreign key to response_actions table
    
    executor_user_id VARCHAR(255) NOT NULL,
    -- Executor user identifier (Security Analyst)
    
    executor_role VARCHAR(50) NOT NULL,
    -- Executor role
    
    executor_attestation TEXT,
    -- Executor attestation text (immutable once set)
    
    executor_attested_at TIMESTAMPTZ,
    -- When executor attested
    
    approver_user_id VARCHAR(255),
    -- Approver user identifier (HAF authority)
    
    approver_role VARCHAR(50),
    -- Approver role
    
    approver_attestation TEXT,
    -- Approver attestation text (immutable once set)
    
    approver_attested_at TIMESTAMPTZ,
    -- When approver attested
    
    attestation_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    -- Attestation status: PENDING, COMPLETE
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT incident_attestations_status_check CHECK (
        attestation_status IN ('PENDING', 'COMPLETE')
    ),
    CONSTRAINT incident_attestations_complete_check CHECK (
        (attestation_status = 'COMPLETE' AND executor_attestation IS NOT NULL AND approver_attestation IS NOT NULL) OR
        (attestation_status = 'PENDING')
    )
);

COMMENT ON TABLE incident_attestations IS 'Mandatory attestations after destructive actions. Attestation required from executor and approver. Immutable once complete.';
COMMENT ON COLUMN incident_attestations.attestation_status IS 'Attestation status: PENDING (awaiting attestations), COMPLETE (both attestations received)';

-- Indexes for incident_attestations
CREATE INDEX idx_incident_attestations_incident_id ON incident_attestations(incident_id);
CREATE INDEX idx_incident_attestations_action_id ON incident_attestations(action_id);
CREATE INDEX idx_incident_attestations_status ON incident_attestations(attestation_status);
CREATE INDEX idx_incident_attestations_executor ON incident_attestations(executor_user_id);
CREATE INDEX idx_incident_attestations_approver ON incident_attestations(approver_user_id) WHERE approver_user_id IS NOT NULL;
