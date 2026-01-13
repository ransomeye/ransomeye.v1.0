-- RansomEye v1.0 Threat Response Engine Tables
-- AUTHORITATIVE: Database schema for TRE actions and rollbacks
-- PostgreSQL 14+ compatible

-- Command type enumeration
CREATE TYPE command_type AS ENUM (
    'ISOLATE_HOST',
    'QUARANTINE_HOST',
    'BLOCK_PROCESS',
    'BLOCK_NETWORK',
    'QUARANTINE_FILE',
    'TERMINATE_PROCESS',
    'DISABLE_USER',
    'REVOKE_ACCESS'
);

-- Authority level enumeration
CREATE TYPE authority_level AS ENUM (
    'NONE',
    'HUMAN',
    'ROLE'
);

-- Execution status enumeration
CREATE TYPE execution_status AS ENUM (
    'PENDING',
    'EXECUTING',
    'SUCCEEDED',
    'FAILED',
    'ROLLED_BACK'
);

-- Rollback reason enumeration
CREATE TYPE rollback_reason AS ENUM (
    'FALSE_POSITIVE',
    'HUMAN_OVERRIDE',
    'SYSTEM_ERROR',
    'POLICY_CHANGE',
    'OTHER'
);

-- Rollback type enumeration
CREATE TYPE rollback_type AS ENUM (
    'FULL',
    'PARTIAL'
);

-- ============================================================================
-- RESPONSE ACTIONS
-- ============================================================================
-- Immutable log of all response actions executed by TRE

CREATE TABLE response_actions (
    action_id UUID NOT NULL PRIMARY KEY,
    -- UUID v4 for action identifier (immutable, never reused)
    
    policy_decision_id UUID NOT NULL,
    -- Policy decision identifier that triggered this action
    -- References policy decision (not foreign key to allow flexibility)
    
    incident_id UUID NOT NULL REFERENCES incidents(incident_id) ON DELETE RESTRICT,
    -- Foreign key to incidents table
    
    machine_id VARCHAR(255) NOT NULL REFERENCES machines(machine_id) ON DELETE RESTRICT,
    -- Foreign key to machines table
    
    command_type command_type NOT NULL,
    -- Type of command executed
    
    command_payload JSONB NOT NULL,
    -- Command payload (command_id, command_type, target_machine_id, incident_id, issued_at)
    -- Stored as JSONB for querying
    
    command_signature TEXT NOT NULL,
    -- Base64-encoded ed25519 signature of command payload
    
    command_signing_key_id VARCHAR(64) NOT NULL,
    -- SHA256 hash of TRE signing public key
    
    required_authority authority_level NOT NULL DEFAULT 'NONE',
    -- Required authority level for execution
    
    authority_action_id UUID,
    -- Human authority action identifier (if required_authority is HUMAN or ROLE)
    
    execution_status execution_status NOT NULL DEFAULT 'PENDING',
    -- Execution status
    
    executed_at TIMESTAMPTZ,
    -- When action was executed (NULL if not executed)
    
    executed_by VARCHAR(50) NOT NULL DEFAULT 'TRE',
    -- Entity that executed the action (TRE, HUMAN)
    
    rollback_capable BOOLEAN NOT NULL DEFAULT TRUE,
    -- Whether this action can be rolled back
    
    rollback_id UUID,
    -- Rollback identifier (if rolled back)
    -- References rollback_records table
    
    ledger_entry_id UUID NOT NULL,
    -- Audit ledger entry ID for this action
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT response_actions_executed_check CHECK (
        (execution_status IN ('PENDING', 'EXECUTING') AND executed_at IS NULL) OR
        (execution_status IN ('SUCCEEDED', 'FAILED', 'ROLLED_BACK') AND executed_at IS NOT NULL)
    ),
    -- If executed, executed_at must be set
    CONSTRAINT response_actions_authority_check CHECK (
        (required_authority = 'NONE' AND authority_action_id IS NULL) OR
        (required_authority IN ('HUMAN', 'ROLE') AND authority_action_id IS NOT NULL)
    ),
    -- If authority required, authority_action_id must be set
    CONSTRAINT response_actions_rollback_check CHECK (
        (rollback_id IS NULL) OR
        (rollback_id IS NOT NULL AND execution_status = 'ROLLED_BACK')
    )
    -- If rolled back, rollback_id must be set and status must be ROLLED_BACK
);

COMMENT ON TABLE response_actions IS 'Immutable log of all response actions executed by TRE. All actions are signed, auditable, and rollback-capable.';
COMMENT ON COLUMN response_actions.action_id IS 'UUID v4 for action identifier. Immutable, never reused.';
COMMENT ON COLUMN response_actions.policy_decision_id IS 'Policy decision identifier that triggered this action.';
COMMENT ON COLUMN response_actions.command_signature IS 'Base64-encoded ed25519 signature of command payload.';
COMMENT ON COLUMN response_actions.rollback_capable IS 'Whether this action can be rolled back. All actions are rollback-capable by default.';

-- Indexes for response_actions
CREATE INDEX idx_response_actions_incident_id ON response_actions(incident_id);
CREATE INDEX idx_response_actions_machine_id ON response_actions(machine_id);
CREATE INDEX idx_response_actions_policy_decision_id ON response_actions(policy_decision_id);
CREATE INDEX idx_response_actions_execution_status ON response_actions(execution_status);
CREATE INDEX idx_response_actions_executed_at ON response_actions(executed_at);
CREATE INDEX idx_response_actions_rollback_id ON response_actions(rollback_id) WHERE rollback_id IS NOT NULL;

-- ============================================================================
-- ROLLBACK RECORDS
-- ============================================================================
-- Immutable log of all rollback operations

CREATE TABLE rollback_records (
    rollback_id UUID NOT NULL PRIMARY KEY,
    -- UUID v4 for rollback identifier (immutable, never reused)
    
    action_id UUID NOT NULL REFERENCES response_actions(action_id) ON DELETE RESTRICT,
    -- Foreign key to response_actions table
    
    rollback_reason rollback_reason NOT NULL,
    -- Reason for rollback
    
    rollback_type rollback_type NOT NULL DEFAULT 'FULL',
    -- Type of rollback (FULL, PARTIAL)
    
    rollback_payload JSONB NOT NULL,
    -- Rollback command payload
    -- Stored as JSONB for querying
    
    rollback_signature TEXT NOT NULL,
    -- Base64-encoded ed25519 signature of rollback payload
    
    rollback_signing_key_id VARCHAR(64) NOT NULL,
    -- SHA256 hash of TRE signing public key
    
    required_authority authority_level NOT NULL DEFAULT 'NONE',
    -- Required authority level for rollback
    
    authority_action_id UUID,
    -- Human authority action identifier (if required_authority is HUMAN or ROLE)
    
    rollback_status execution_status NOT NULL DEFAULT 'PENDING',
    -- Rollback execution status (PENDING, EXECUTING, SUCCEEDED, FAILED)
    
    rolled_back_at TIMESTAMPTZ,
    -- When rollback was executed (NULL if not executed)
    
    rolled_back_by VARCHAR(50) NOT NULL DEFAULT 'TRE',
    -- Entity that executed the rollback (TRE, HUMAN)
    
    ledger_entry_id UUID NOT NULL,
    -- Audit ledger entry ID for this rollback
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT rollback_records_executed_check CHECK (
        (rollback_status IN ('PENDING', 'EXECUTING') AND rolled_back_at IS NULL) OR
        (rollback_status IN ('SUCCEEDED', 'FAILED') AND rolled_back_at IS NOT NULL)
    ),
    -- If executed, rolled_back_at must be set
    CONSTRAINT rollback_records_authority_check CHECK (
        (required_authority = 'NONE' AND authority_action_id IS NULL) OR
        (required_authority IN ('HUMAN', 'ROLE') AND authority_action_id IS NOT NULL)
    )
    -- If authority required, authority_action_id must be set
);

COMMENT ON TABLE rollback_records IS 'Immutable log of all rollback operations. All rollbacks are signed, auditable, and linked to original actions.';
COMMENT ON COLUMN rollback_records.rollback_id IS 'UUID v4 for rollback identifier. Immutable, never reused.';
COMMENT ON COLUMN rollback_records.rollback_signature IS 'Base64-encoded ed25519 signature of rollback payload.';
COMMENT ON COLUMN rollback_records.rollback_type IS 'Type of rollback. FULL = complete reversal, PARTIAL = partial reversal.';

-- Indexes for rollback_records
CREATE INDEX idx_rollback_records_action_id ON rollback_records(action_id);
CREATE INDEX idx_rollback_records_rollback_status ON rollback_records(rollback_status);
CREATE INDEX idx_rollback_records_rolled_back_at ON rollback_records(rolled_back_at);
