-- RansomEye v1.0 Threat Response Engine - Enforcement Mode Schema
-- AUTHORITATIVE: Database schema for TRE enforcement modes and approvals
-- PostgreSQL 14+ compatible

-- Enforcement mode enumeration (FROZEN - exactly three modes)
CREATE TYPE tre_enforcement_mode AS ENUM (
    'DRY_RUN',
    'GUARDED_EXEC',
    'FULL_ENFORCE'
);

-- Action classification enumeration (FROZEN - immutable)
CREATE TYPE action_classification AS ENUM (
    'SAFE',
    'DESTRUCTIVE'
);

-- Approval status enumeration
CREATE TYPE approval_status AS ENUM (
    'PENDING',
    'APPROVED',
    'REJECTED',
    'EXPIRED'
);

-- ============================================================================
-- TRE EXECUTION MODES
-- ============================================================================
-- Stores current TRE enforcement mode (only one active mode at a time)

CREATE TABLE tre_execution_modes (
    mode_id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    -- UUID v4 for mode record identifier
    
    mode tre_enforcement_mode NOT NULL,
    -- Current enforcement mode
    
    changed_by_user_id VARCHAR(255) NOT NULL,
    -- User who changed the mode (must be SUPER_ADMIN)
    
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- When mode was changed
    
    reason TEXT,
    -- Reason for mode change
    
    ledger_entry_id UUID NOT NULL,
    -- Audit ledger entry ID for mode change
    
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    -- Only one active mode at a time
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT tre_execution_modes_single_active CHECK (
        (is_active = TRUE) OR (is_active = FALSE)
    )
);

COMMENT ON TABLE tre_execution_modes IS 'Stores TRE enforcement mode. Only one mode can be active at a time. Mode changes require SUPER_ADMIN role.';
COMMENT ON COLUMN tre_execution_modes.mode IS 'Current enforcement mode: DRY_RUN, GUARDED_EXEC, or FULL_ENFORCE';
COMMENT ON COLUMN tre_execution_modes.changed_by_user_id IS 'User who changed the mode (must be SUPER_ADMIN)';

-- Index for active mode lookup
CREATE UNIQUE INDEX idx_tre_execution_modes_active ON tre_execution_modes(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_tre_execution_modes_changed_at ON tre_execution_modes(changed_at);

-- ============================================================================
-- TRE ACTION APPROVALS
-- ============================================================================
-- Stores HAF approval requests for DESTRUCTIVE actions in FULL_ENFORCE mode

CREATE TABLE tre_action_approvals (
    approval_id UUID NOT NULL PRIMARY KEY,
    -- UUID v4 for approval identifier
    
    action_id UUID NOT NULL REFERENCES response_actions(action_id) ON DELETE RESTRICT,
    -- Foreign key to response_actions table
    
    requested_by_user_id VARCHAR(255) NOT NULL,
    -- User who requested the action
    
    requested_by_role VARCHAR(50) NOT NULL,
    -- Role of user who requested the action
    
    approval_status approval_status NOT NULL DEFAULT 'PENDING',
    -- Approval status
    
    approver_user_id VARCHAR(255),
    -- User who approved/rejected (NULL if pending)
    
    approver_role VARCHAR(50),
    -- Role of approver (must be SUPER_ADMIN or SECURITY_ANALYST with approval rights)
    
    approval_decision TEXT,
    -- Approval decision (APPROVED, REJECTED)
    
    approval_timestamp TIMESTAMPTZ,
    -- When approval/rejection occurred
    
    approval_signature TEXT,
    -- Cryptographic signature of approval decision
    
    expires_at TIMESTAMPTZ NOT NULL,
    -- When approval request expires
    
    reason TEXT,
    -- Reason for approval/rejection
    
    ledger_entry_id UUID,
    -- Audit ledger entry ID for approval
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Schema-level timestamp (immutable)
    
    CONSTRAINT tre_action_approvals_status_check CHECK (
        (approval_status = 'PENDING' AND approver_user_id IS NULL) OR
        (approval_status IN ('APPROVED', 'REJECTED', 'EXPIRED') AND approver_user_id IS NOT NULL)
    ),
    -- If approved/rejected, approver must be set
    CONSTRAINT tre_action_approvals_expiry_check CHECK (
        expires_at > created_at
    )
    -- Expiry must be after creation
);

COMMENT ON TABLE tre_action_approvals IS 'Stores HAF approval requests for DESTRUCTIVE actions in FULL_ENFORCE mode. Immutable approval history.';
COMMENT ON COLUMN tre_action_approvals.approval_id IS 'UUID v4 for approval identifier. Immutable, never reused.';
COMMENT ON COLUMN tre_action_approvals.approval_status IS 'Approval status: PENDING, APPROVED, REJECTED, or EXPIRED';

-- Indexes for tre_action_approvals
CREATE INDEX idx_tre_action_approvals_action_id ON tre_action_approvals(action_id);
CREATE INDEX idx_tre_action_approvals_status ON tre_action_approvals(approval_status);
CREATE INDEX idx_tre_action_approvals_requested_by ON tre_action_approvals(requested_by_user_id);
CREATE INDEX idx_tre_action_approvals_approver ON tre_action_approvals(approver_user_id) WHERE approver_user_id IS NOT NULL;
CREATE INDEX idx_tre_action_approvals_expires_at ON tre_action_approvals(expires_at) WHERE approval_status = 'PENDING';
