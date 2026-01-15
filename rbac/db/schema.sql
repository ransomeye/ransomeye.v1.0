-- RansomEye v1.0 RBAC Schema
-- AUTHORITATIVE: Immutable schema for Role-Based Access Control
-- PostgreSQL 14+ compatible
-- Zero optional fields, default DENY

-- ============================================================================
-- ROLES
-- ============================================================================
-- Exactly five roles: SUPER_ADMIN, SECURITY_ANALYST, POLICY_MANAGER, IT_ADMIN, AUDITOR

CREATE TYPE rbac_role AS ENUM (
    'SUPER_ADMIN',
    'SECURITY_ANALYST',
    'POLICY_MANAGER',
    'IT_ADMIN',
    'AUDITOR'
);

-- ============================================================================
-- PERMISSIONS
-- ============================================================================
-- Explicit permission model (default DENY)

CREATE TYPE rbac_permission AS ENUM (
    -- Incident permissions
    'incident:view',
    'incident:view_all',
    'incident:acknowledge',
    'incident:resolve',
    'incident:close',
    'incident:export',
    'incident:assign',
    
    -- Policy permissions
    'policy:view',
    'policy:create',
    'policy:update',
    'policy:delete',
    'policy:execute',
    'policy:simulate',
    
    -- Threat Response permissions
    'tre:view',
    'tre:execute',
    'tre:rollback',
    'tre:view_all',
    
    -- Human Authority permissions
    'haf:view',
    'haf:create_override',
    'haf:approve',
    'haf:reject',
    
    -- Forensics permissions
    'forensics:view',
    'forensics:export',
    
    -- Reporting permissions
    'report:view',
    'report:generate',
    'report:export',
    'report:view_all',
    
    -- Agent permissions
    'agent:install',
    'agent:uninstall',
    'agent:update',
    'agent:view',
    
    -- User management permissions
    'user:create',
    'user:delete',
    'user:role_assign',
    
    -- System permissions
    'system:view_config',
    'system:modify_config',
    'system:view_logs',
    'system:manage_users',
    'system:manage_roles',
    
    -- Billing permissions
    'billing:view',
    'billing:manage',
    
    -- Audit permissions
    'audit:view',
    'audit:view_all',
    'audit:export'
);

-- ============================================================================
-- USERS
-- ============================================================================
-- User accounts with authentication credentials

CREATE TABLE rbac_users (
    user_id VARCHAR(255) NOT NULL PRIMARY KEY,
    -- User identifier (username, email, or unique identifier)
    -- VARCHAR(255) sufficient for any identifier format
    
    username VARCHAR(255) NOT NULL UNIQUE,
    -- Username for login (unique constraint)
    
    password_hash VARCHAR(255) NOT NULL,
    -- Password hash (bcrypt, argon2, or similar)
    -- VARCHAR(255) sufficient for any hash format
    
    email VARCHAR(255),
    -- Email address (optional for contact)
    
    full_name VARCHAR(255),
    -- Full name (optional for display)
    
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    -- Whether user account is active (can be disabled)
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- When user account was created
    
    last_login_at TIMESTAMPTZ,
    -- Last successful login timestamp
    -- NULL if never logged in
    
    created_by VARCHAR(255) NOT NULL,
    -- User who created this account
    -- References rbac_users(user_id)
    
    CONSTRAINT rbac_users_user_id_not_empty CHECK (LENGTH(TRIM(user_id)) > 0),
    CONSTRAINT rbac_users_username_not_empty CHECK (LENGTH(TRIM(username)) > 0),
    CONSTRAINT rbac_users_password_hash_not_empty CHECK (LENGTH(TRIM(password_hash)) > 0),
    CONSTRAINT rbac_users_created_by_not_empty CHECK (LENGTH(TRIM(created_by)) > 0)
);

COMMENT ON TABLE rbac_users IS 'User accounts with authentication credentials. One role per user enforced by user_roles table.';
COMMENT ON COLUMN rbac_users.user_id IS 'Unique user identifier (primary key)';
COMMENT ON COLUMN rbac_users.username IS 'Username for login (unique)';
COMMENT ON COLUMN rbac_users.password_hash IS 'Password hash (never store plaintext)';
COMMENT ON COLUMN rbac_users.is_active IS 'Whether user account is active (can be disabled without deletion)';

-- ============================================================================
-- USER ROLES
-- ============================================================================
-- One role per user (enforced by unique constraint)

CREATE TABLE rbac_user_roles (
    user_role_id VARCHAR(255) NOT NULL PRIMARY KEY,
    -- Unique identifier for user-role assignment
    
    user_id VARCHAR(255) NOT NULL REFERENCES rbac_users(user_id) ON DELETE CASCADE,
    -- Foreign key to rbac_users
    
    role rbac_role NOT NULL,
    -- Role assigned to user
    
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- When role was assigned
    
    assigned_by VARCHAR(255) NOT NULL,
    -- User who assigned this role
    -- References rbac_users(user_id)
    
    CONSTRAINT rbac_user_roles_user_role_id_not_empty CHECK (LENGTH(TRIM(user_role_id)) > 0),
    CONSTRAINT rbac_user_roles_assigned_by_not_empty CHECK (LENGTH(TRIM(assigned_by)) > 0),
    -- Enforce one role per user
    CONSTRAINT rbac_user_roles_one_role_per_user UNIQUE (user_id)
);

COMMENT ON TABLE rbac_user_roles IS 'User-role assignments. Exactly one role per user (enforced by unique constraint).';
COMMENT ON COLUMN rbac_user_roles.user_id IS 'User identifier (foreign key to rbac_users)';
COMMENT ON COLUMN rbac_user_roles.role IS 'Role assigned to user (exactly one)';
COMMENT ON CONSTRAINT rbac_user_roles_one_role_per_user ON rbac_user_roles IS 'Enforces one role per user (multiple users per role allowed)';

-- ============================================================================
-- REFRESH TOKENS
-- ============================================================================
-- Refresh token storage for JWT session management (logout + rotation)

CREATE TABLE rbac_refresh_tokens (
    token_id VARCHAR(255) NOT NULL PRIMARY KEY,
    -- Unique token identifier (jti)

    user_id VARCHAR(255) NOT NULL REFERENCES rbac_users(user_id) ON DELETE CASCADE,
    -- Token owner

    token_hash VARCHAR(255) NOT NULL,
    -- SHA256 hash of refresh token (never store raw token)

    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- When refresh token was issued

    expires_at TIMESTAMPTZ NOT NULL,
    -- Token expiration timestamp

    revoked_at TIMESTAMPTZ,
    -- When token was revoked (NULL if active)

    revoked_by VARCHAR(255),
    -- User or system that revoked the token

    revocation_reason VARCHAR(255),
    -- Reason for revocation

    user_agent VARCHAR(512),
    -- Optional user agent for audit traceability

    ip_address VARCHAR(128),
    -- Optional IP address for audit traceability

    CONSTRAINT rbac_refresh_tokens_token_id_not_empty CHECK (LENGTH(TRIM(token_id)) > 0),
    CONSTRAINT rbac_refresh_tokens_token_hash_not_empty CHECK (LENGTH(TRIM(token_hash)) > 0)
);

COMMENT ON TABLE rbac_refresh_tokens IS 'Refresh token store for UI authentication. Stores hashed tokens for rotation and logout invalidation.';
COMMENT ON COLUMN rbac_refresh_tokens.token_hash IS 'SHA256 hash of refresh token; raw tokens are never stored.';

CREATE INDEX idx_rbac_refresh_tokens_user_id ON rbac_refresh_tokens(user_id);
CREATE INDEX idx_rbac_refresh_tokens_expires_at ON rbac_refresh_tokens(expires_at);
CREATE INDEX idx_rbac_refresh_tokens_revoked_at ON rbac_refresh_tokens(revoked_at);

-- ============================================================================
-- ROLE PERMISSIONS
-- ============================================================================
-- Role-permission mappings (many-to-many)

CREATE TABLE rbac_role_permissions (
    role_permission_id VARCHAR(255) NOT NULL PRIMARY KEY,
    -- Unique identifier for role-permission mapping
    
    role rbac_role NOT NULL,
    -- Role
    
    permission rbac_permission NOT NULL,
    -- Permission granted to role
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- When permission was granted to role
    
    created_by VARCHAR(255) NOT NULL,
    -- User who created this mapping
    -- References rbac_users(user_id)
    
    CONSTRAINT rbac_role_permissions_role_permission_id_not_empty CHECK (LENGTH(TRIM(role_permission_id)) > 0),
    CONSTRAINT rbac_role_permissions_created_by_not_empty CHECK (LENGTH(TRIM(created_by)) > 0),
    -- Prevent duplicate role-permission mappings
    CONSTRAINT rbac_role_permissions_unique UNIQUE (role, permission)
);

COMMENT ON TABLE rbac_role_permissions IS 'Role-permission mappings. Defines which permissions each role has.';
COMMENT ON COLUMN rbac_role_permissions.role IS 'Role (exactly five roles)';
COMMENT ON COLUMN rbac_role_permissions.permission IS 'Permission granted to role';
COMMENT ON CONSTRAINT rbac_role_permissions_unique ON rbac_role_permissions IS 'Prevents duplicate role-permission mappings';

-- ============================================================================
-- PERMISSION AUDIT LOG
-- ============================================================================
-- Immutable log of all permission checks (allow/deny decisions)

CREATE TABLE rbac_permission_audit (
    audit_id VARCHAR(255) NOT NULL PRIMARY KEY,
    -- Unique identifier for audit entry
    
    user_id VARCHAR(255) NOT NULL,
    -- User who attempted action
    -- References rbac_users(user_id) (but may be NULL for deleted users)
    
    role rbac_role NOT NULL,
    -- Role of user at time of check
    
    permission rbac_permission NOT NULL,
    -- Permission that was checked
    
    resource_type VARCHAR(255) NOT NULL,
    -- Type of resource (incident, policy, tre_action, etc.)
    
    resource_id VARCHAR(255),
    -- Resource identifier (incident_id, policy_id, etc.)
    -- NULL for global permissions
    
    decision VARCHAR(10) NOT NULL,
    -- Decision: 'ALLOW' or 'DENY'
    
    reason VARCHAR(500),
    -- Reason for decision (e.g., 'Permission granted', 'Role lacks permission')
    
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- When permission check occurred
    
    ledger_entry_id VARCHAR(255),
    -- Audit ledger entry ID (if audit ledger integration enabled)
    -- References audit ledger entry
    
    CONSTRAINT rbac_permission_audit_audit_id_not_empty CHECK (LENGTH(TRIM(audit_id)) > 0),
    CONSTRAINT rbac_permission_audit_resource_type_not_empty CHECK (LENGTH(TRIM(resource_type)) > 0),
    CONSTRAINT rbac_permission_audit_decision_valid CHECK (decision IN ('ALLOW', 'DENY'))
);

COMMENT ON TABLE rbac_permission_audit IS 'Immutable log of all permission checks (allow/deny decisions). Used for audit and compliance.';
COMMENT ON COLUMN rbac_permission_audit.decision IS 'Decision: ALLOW or DENY';
COMMENT ON COLUMN rbac_permission_audit.ledger_entry_id IS 'Audit ledger entry ID (links to central audit ledger)';

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX idx_rbac_user_roles_user_id ON rbac_user_roles(user_id);
CREATE INDEX idx_rbac_user_roles_role ON rbac_user_roles(role);
CREATE INDEX idx_rbac_role_permissions_role ON rbac_role_permissions(role);
CREATE INDEX idx_rbac_role_permissions_permission ON rbac_role_permissions(permission);
CREATE INDEX idx_rbac_permission_audit_user_id ON rbac_permission_audit(user_id);
CREATE INDEX idx_rbac_permission_audit_timestamp ON rbac_permission_audit(timestamp);
CREATE INDEX idx_rbac_permission_audit_decision ON rbac_permission_audit(decision);
