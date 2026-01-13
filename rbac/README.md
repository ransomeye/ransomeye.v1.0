# RansomEye v1.0 Role-Based Access Control (RBAC)

**AUTHORITATIVE**: Production-grade RBAC system with server-side enforcement and zero assumptions.

---

## Overview

The RansomEye RBAC system provides **military-grade security control** for all system operations. It enforces **explicit permissions** with **default DENY** behavior, ensuring that unauthorized actions are blocked even if the UI is bypassed.

### Core Principles

1. **Server-Side Enforcement**: UI hiding is insufficient; backend must block unauthorized actions
2. **Explicit Permission Model**: Default DENY, no implied permissions
3. **Exactly Five Roles**: SUPER_ADMIN, SECURITY_ANALYST, POLICY_MANAGER, IT_ADMIN, AUDITOR
4. **One Role Per User**: Each user has exactly one role (multiple users per role allowed)
5. **Full Audit Logging**: All permission checks are logged to audit ledger
6. **Zero Placeholders**: No TODOs, no mock data, no demo-only logic

---

## Architecture

### Components

```
rbac/
├── db/
│   └── schema.sql                    # Database schema (users, roles, permissions)
├── schema/
│   ├── permission.schema.json        # Permission schema (frozen)
│   └── role.schema.json              # Role schema (frozen)
├── engine/
│   ├── permission_checker.py         # Core permission checking logic
│   └── role_permission_mapper.py     # Role-permission mappings
├── api/
│   └── rbac_api.py                   # Public RBAC API
├── middleware/
│   └── fastapi_auth.py               # FastAPI authentication middleware
├── integration/
│   ├── tre_integration.py            # TRE permission enforcement
│   ├── policy_integration.py         # Policy Engine permission enforcement
│   └── haf_integration.py            # HAF permission enforcement
├── cli/
│   └── init_rbac.py                  # RBAC initialization CLI
└── README.md                         # This file
```

---

## Roles and Permissions

### SUPER_ADMIN

**Who**: CTO / Head of Security / Platform Owner  
**Authority Level**: Absolute

**Permissions**: All permissions (complete system access)

- All incident operations
- All policy operations
- All TRE operations
- All HAF operations
- All forensics operations
- All reporting operations
- All agent management
- All user management
- All system configuration
- All billing operations
- All audit operations

---

### SECURITY_ANALYST

**Who**: SOC analysts, threat hunters  
**Goal**: Actively defend against attacks

**Allowed**:
- View and manage incidents (acknowledge, resolve, close, assign)
- Execute Threat Response actions (isolate host, kill process, block network)
- Rollback TRE actions
- Access forensics (logs, memory dumps)
- Generate incident-scoped reports
- Create and approve HAF overrides
- View audit logs

**Explicitly FORBIDDEN**:
- Editing policies
- Managing users
- Managing agents
- Billing or licensing
- Deleting logs

---

### POLICY_MANAGER

**Who**: Senior security engineers  
**Goal**: Prevention and detection tuning

**Allowed**:
- View and edit policies (create, update, delete)
- Configure detection thresholds
- Run policy simulations
- View incidents (for context)
- View TRE actions (read-only)
- Create and approve HAF overrides
- Generate reports
- View audit logs

**Explicitly FORBIDDEN**:
- Executing response actions
- Managing users
- Managing agents
- Billing
- Viewing raw forensics

---

### IT_ADMIN

**Who**: Sysadmins, infrastructure teams  
**Goal**: Platform health and deployment

**Allowed**:
- Install / uninstall agents
- Upgrade agents
- View agent health
- View host status
- View system configuration
- Modify system configuration
- View system logs
- View incidents (read-only, for context)
- View TRE actions (read-only)
- View reports (read-only)
- View audit logs (read-only)

**Explicitly FORBIDDEN**:
- Viewing incident details
- Viewing forensics
- Executing threat responses
- Editing policies
- Billing or licensing

---

### AUDITOR

**Who**: Compliance officers, external auditors  
**Goal**: Verification and compliance

**Allowed**:
- Read-only dashboards
- View audit logs
- Generate compliance reports (PDF/CSV)
- View incidents (read-only)
- View policies (read-only)
- View TRE actions (read-only)
- View HAF overrides (read-only)
- View forensics (read-only)
- Export all read-only data

**Explicitly FORBIDDEN**:
- Clicking ANY action buttons
- Executing responses
- Editing anything
- Managing users
- Managing agents

---

## Permission Model

### Permission Format

Permissions follow the format: `resource:action`

Examples:
- `incident:view` - View incidents
- `incident:resolve` - Resolve incidents
- `tre:execute` - Execute TRE actions
- `policy:edit` - Edit policies
- `user:create` - Create users

### Permission Categories

1. **Incident Permissions**
   - `incident:view` - View specific incident
   - `incident:view_all` - View all incidents
   - `incident:acknowledge` - Acknowledge incident
   - `incident:resolve` - Resolve incident
   - `incident:close` - Close incident
   - `incident:export` - Export incident data
   - `incident:assign` - Assign incident

2. **Policy Permissions**
   - `policy:view` - View policies
   - `policy:create` - Create policies
   - `policy:update` - Update policies
   - `policy:delete` - Delete policies
   - `policy:execute` - Execute policies
   - `policy:simulate` - Simulate policies

3. **Threat Response Permissions**
   - `tre:view` - View TRE actions
   - `tre:view_all` - View all TRE actions
   - `tre:execute` - Execute TRE actions
   - `tre:rollback` - Rollback TRE actions

4. **Human Authority Permissions**
   - `haf:view` - View HAF overrides
   - `haf:create_override` - Create HAF overrides
   - `haf:approve` - Approve HAF overrides
   - `haf:reject` - Reject HAF overrides

5. **Forensics Permissions**
   - `forensics:view` - View forensics data
   - `forensics:export` - Export forensics data

6. **Reporting Permissions**
   - `report:view` - View reports
   - `report:generate` - Generate reports
   - `report:export` - Export reports
   - `report:view_all` - View all reports

7. **Agent Permissions**
   - `agent:install` - Install agents
   - `agent:uninstall` - Uninstall agents
   - `agent:update` - Update agents
   - `agent:view` - View agent status

8. **User Management Permissions**
   - `user:create` - Create users
   - `user:delete` - Delete users
   - `user:role_assign` - Assign roles to users

9. **System Permissions**
   - `system:view_config` - View system configuration
   - `system:modify_config` - Modify system configuration
   - `system:view_logs` - View system logs
   - `system:manage_users` - Manage users
   - `system:manage_roles` - Manage roles

10. **Billing Permissions**
    - `billing:view` - View billing information
    - `billing:manage` - Manage billing

11. **Audit Permissions**
    - `audit:view` - View audit logs
    - `audit:view_all` - View all audit logs
    - `audit:export` - Export audit logs

---

## Database Schema

### Tables

1. **rbac_users**: User accounts with authentication credentials
2. **rbac_user_roles**: User-role assignments (one role per user)
3. **rbac_role_permissions**: Role-permission mappings (immutable at runtime)
4. **rbac_permission_audit**: Immutable log of all permission checks

### Schema Location

Database schema is defined in `rbac/db/schema.sql`.

### Initialization

Run the initialization CLI to set up role-permission mappings:

```bash
python3 rbac/cli/init_rbac.py \
  --db-host localhost \
  --db-port 5432 \
  --db-name ransomeye \
  --db-user ransomeye \
  --db-password <password> \
  --ledger-path /path/to/ledger \
  --ledger-key-dir /path/to/ledger/keys
```

---

## Backend Enforcement

### Permission Checking

All protected operations must check permissions before execution:

```python
from rbac.engine.permission_checker import PermissionChecker

permission_checker = PermissionChecker(db_conn_params, ledger_path, ledger_key_dir)

# Check permission
has_permission = permission_checker.check_permission(
    user_id=user_id,
    permission='tre:execute',
    resource_type='tre_action',
    resource_id=incident_id
)

if not has_permission:
    raise PermissionDeniedError("Permission denied")
```

### FastAPI Integration

Use the RBAC middleware for FastAPI endpoints:

```python
from rbac.middleware.fastapi_auth import RBACAuth
from rbac.api.rbac_api import RBACAPI

rbac_api = RBACAPI(db_conn_params, ledger_path, ledger_key_dir)
rbac_auth = RBACAuth(rbac_api)

@app.get("/api/incidents")
@rbac_auth.require_permission('incident:view', 'incident')
async def get_incidents(current_user: dict = Depends(rbac_auth.get_current_user)):
    # Endpoint implementation
    pass
```

---

## Integration with Other Systems

### Threat Response Engine (TRE)

RBAC enforces permissions for TRE operations:

- `tre:execute` - Required to execute TRE actions
- `tre:rollback` - Required to rollback TRE actions
- `tre:view` - Required to view TRE actions

Integration is provided by `rbac/integration/tre_integration.py`.

### Policy Engine

RBAC enforces permissions for Policy Engine operations:

- `policy:create` - Required to create policies
- `policy:update` - Required to update policies
- `policy:delete` - Required to delete policies
- `policy:simulate` - Required to simulate policies

Integration is provided by `rbac/integration/policy_integration.py`.

### Human Authority Framework (HAF)

RBAC check happens **BEFORE** authority check:

- `haf:create_override` - Required to create HAF overrides
- `haf:approve` - Required to approve HAF overrides
- `haf:view` - Required to view HAF overrides

Integration is provided by `rbac/integration/haf_integration.py`.

### Audit Ledger

All permission checks are logged to the audit ledger:

- `rbac_permission_check` - Permission check event
- `rbac_user_action_allowed` - Action allowed event
- `rbac_user_action_denied` - Action denied event

---

## UI Integration

### Role-Aware Rendering

The UI must render components based on user permissions:

```javascript
// Check if user has permission
const hasPermission = userPermissions.includes('tre:execute');

// Render button only if permission exists
{hasPermission && (
  <button onClick={handleExecute}>Execute Action</button>
)}
```

### Server-Side Validation

**CRITICAL**: UI hiding is insufficient. Backend must validate all requests:

```python
# Backend endpoint
@app.post("/api/tre/execute")
@rbac_auth.require_permission('tre:execute', 'tre_action')
async def execute_action(request: Request, current_user: dict):
    # Even if UI is bypassed, this will block unauthorized requests
    pass
```

---

## Audit Logging

### Permission Audit Log

All permission checks are logged to `rbac_permission_audit` table:

- `audit_id` - Unique audit entry ID
- `user_id` - User who attempted action
- `role` - User's role
- `permission` - Permission checked
- `resource_type` - Resource type
- `resource_id` - Resource identifier
- `decision` - ALLOW or DENY
- `reason` - Reason for decision
- `timestamp` - When check occurred
- `ledger_entry_id` - Audit ledger entry ID

### Audit Ledger Events

Permission checks emit audit ledger entries:

```json
{
  "component": "rbac",
  "component_instance_id": "permission-checker",
  "action_type": "rbac_permission_check",
  "subject": {
    "type": "tre_action",
    "id": "incident-123"
  },
  "actor": {
    "type": "user",
    "identifier": "user-456"
  },
  "payload": {
    "permission": "tre:execute",
    "role": "SECURITY_ANALYST",
    "decision": "ALLOW",
    "reason": "Permission granted"
  }
}
```

---

## Security Considerations

1. **Default DENY**: All permissions are denied by default
2. **Server-Side Enforcement**: Backend must block unauthorized actions
3. **No Role Checks in Code**: Use permission checks, not role name checks
4. **Immutable Mappings**: Role-permission mappings are immutable at runtime
5. **Full Audit Trail**: All permission checks are logged
6. **No Bypass Flags**: No feature flags or temporary admin shortcuts

---

## Verification Checklist

### Database Schema

- [ ] `rbac_users` table exists
- [ ] `rbac_user_roles` table exists (one role per user enforced)
- [ ] `rbac_role_permissions` table exists
- [ ] `rbac_permission_audit` table exists
- [ ] All required indexes exist

### Role-Permission Mappings

- [ ] SUPER_ADMIN has all permissions
- [ ] SECURITY_ANALYST has correct permissions (no policy edit, no user management)
- [ ] POLICY_MANAGER has correct permissions (no TRE execute, no forensics)
- [ ] IT_ADMIN has correct permissions (no incidents, no forensics, no policies)
- [ ] AUDITOR has read-only permissions (no action buttons)

### Backend Enforcement

- [ ] All TRE endpoints enforce permissions
- [ ] All Policy Engine endpoints enforce permissions
- [ ] All HAF endpoints enforce permissions
- [ ] All UI backend endpoints enforce permissions
- [ ] Unauthorized requests are blocked (test with direct API calls)

### Audit Logging

- [ ] Permission checks are logged to database
- [ ] Permission checks emit audit ledger entries
- [ ] Both ALLOW and DENY decisions are logged

### UI Integration

- [ ] UI renders components based on permissions
- [ ] Action buttons are hidden if permission missing
- [ ] Backend blocks requests even if UI is bypassed

---

## Legal / Regulatory Positioning

The RBAC system supports compliance with:

- **SOC 2**: Access control requirements
- **ISO 27001**: Access management controls
- **HIPAA**: Access control requirements
- **PCI DSS**: Access control requirements
- **GDPR**: Access control and audit requirements

---

## Limitations

1. **One Role Per User**: Users cannot have multiple roles
2. **No Role Inheritance**: Roles do not inherit permissions
3. **No Dynamic Permissions**: Permissions are fixed at runtime
4. **No Custom Roles**: Only the five predefined roles are supported

---

## Future Enhancements

- JWT token-based authentication
- Session management
- Password reset functionality
- Multi-factor authentication (MFA)
- Role-based UI component library

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye RBAC documentation.
