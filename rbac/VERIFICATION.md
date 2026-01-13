# RansomEye v1.0 RBAC Verification Checklist

**AUTHORITATIVE**: Complete verification checklist for RBAC implementation.

---

## 1. Database Schema Verification

### Required Tables

- [ ] `rbac_users` table exists with all required columns
- [ ] `rbac_user_roles` table exists with unique constraint on `user_id` (one role per user)
- [ ] `rbac_role_permissions` table exists with unique constraint on `(role, permission)`
- [ ] `rbac_permission_audit` table exists with all required columns

### Required Indexes

- [ ] `idx_rbac_user_roles_user_id` exists
- [ ] `idx_rbac_user_roles_role` exists
- [ ] `idx_rbac_role_permissions_role` exists
- [ ] `idx_rbac_role_permissions_permission` exists
- [ ] `idx_rbac_permission_audit_user_id` exists
- [ ] `idx_rbac_permission_audit_timestamp` exists
- [ ] `idx_rbac_permission_audit_decision` exists

### Verification Commands

```sql
-- Check tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name LIKE 'rbac_%';

-- Check constraints
SELECT constraint_name, table_name 
FROM information_schema.table_constraints 
WHERE table_schema = 'public' AND table_name LIKE 'rbac_%';

-- Check indexes
SELECT indexname FROM pg_indexes 
WHERE schemaname = 'public' AND indexname LIKE 'idx_rbac_%';
```

---

## 2. Role-Permission Mappings Verification

### Exactly Five Roles

- [ ] SUPER_ADMIN exists
- [ ] SECURITY_ANALYST exists
- [ ] POLICY_MANAGER exists
- [ ] IT_ADMIN exists
- [ ] AUDITOR exists
- [ ] No additional roles exist

### Permission Assignments

#### SUPER_ADMIN
- [ ] Has all permissions (verify count matches total permission count)

#### SECURITY_ANALYST
- [ ] Has `incident:*` permissions (view, view_all, acknowledge, resolve, close, export, assign)
- [ ] Has `tre:*` permissions (view, execute, rollback, view_all)
- [ ] Has `haf:*` permissions (view, create_override, approve)
- [ ] Has `forensics:*` permissions (view, export)
- [ ] Has `report:*` permissions (view, generate, export)
- [ ] Has `audit:*` permissions (view, view_all, export)
- [ ] Does NOT have `policy:create`, `policy:update`, `policy:delete`
- [ ] Does NOT have `user:*` permissions
- [ ] Does NOT have `agent:*` permissions
- [ ] Does NOT have `billing:*` permissions

#### POLICY_MANAGER
- [ ] Has `policy:*` permissions (view, create, update, delete, execute, simulate)
- [ ] Has `incident:view` and `incident:view_all` (read-only)
- [ ] Has `tre:view` and `tre:view_all` (read-only, no execute)
- [ ] Has `haf:*` permissions (view, create_override, approve)
- [ ] Has `report:*` permissions (view, generate, export)
- [ ] Has `audit:view` and `audit:view_all`
- [ ] Does NOT have `tre:execute` or `tre:rollback`
- [ ] Does NOT have `forensics:*` permissions
- [ ] Does NOT have `user:*` permissions
- [ ] Does NOT have `agent:*` permissions
- [ ] Does NOT have `billing:*` permissions

#### IT_ADMIN
- [ ] Has `agent:*` permissions (install, uninstall, update, view)
- [ ] Has `system:*` permissions (view_config, modify_config, view_logs)
- [ ] Has `incident:view` and `incident:view_all` (read-only)
- [ ] Has `tre:view` and `tre:view_all` (read-only)
- [ ] Has `report:view` and `report:export` (read-only)
- [ ] Has `audit:view` (read-only)
- [ ] Does NOT have `incident:acknowledge`, `incident:resolve`, `incident:close`
- [ ] Does NOT have `tre:execute` or `tre:rollback`
- [ ] Does NOT have `forensics:*` permissions
- [ ] Does NOT have `policy:*` permissions (except view)
- [ ] Does NOT have `user:*` permissions
- [ ] Does NOT have `billing:*` permissions

#### AUDITOR
- [ ] Has read-only permissions only
- [ ] Has `incident:view`, `incident:view_all`, `incident:export`
- [ ] Has `policy:view`
- [ ] Has `tre:view`, `tre:view_all`
- [ ] Has `haf:view`
- [ ] Has `forensics:view`, `forensics:export`
- [ ] Has `report:view`, `report:export`, `report:view_all`
- [ ] Has `audit:view`, `audit:view_all`, `audit:export`
- [ ] Does NOT have ANY action permissions (acknowledge, resolve, close, execute, rollback, create, update, delete)
- [ ] Does NOT have `user:*` permissions
- [ ] Does NOT have `agent:*` permissions
- [ ] Does NOT have `billing:*` permissions

### Verification Commands

```python
from rbac.engine.role_permission_mapper import ROLE_PERMISSIONS, get_all_roles, get_all_permissions

# Verify exactly five roles
assert len(get_all_roles()) == 5

# Verify SUPER_ADMIN has all permissions
all_perms = get_all_permissions()
assert ROLE_PERMISSIONS['SUPER_ADMIN'] == all_perms

# Verify each role has correct permissions
# (Run specific checks per role)
```

---

## 3. Backend Enforcement Verification

### Permission Checker

- [ ] `PermissionChecker.check_permission()` returns False by default (default DENY)
- [ ] `PermissionChecker.check_permission()` logs to database
- [ ] `PermissionChecker.check_permission()` emits audit ledger entry
- [ ] `PermissionChecker.get_user_permissions()` returns correct permissions

### FastAPI Middleware

- [ ] `RBACAuth.require_permission()` decorator blocks unauthorized requests
- [ ] `RBACAuth.get_current_user()` validates authentication
- [ ] Unauthorized requests return 403 Forbidden
- [ ] Unauthenticated requests return 401 Unauthorized

### Integration Modules

- [ ] `TREPermissionEnforcer` enforces `tre:execute` and `tre:rollback`
- [ ] `PolicyPermissionEnforcer` enforces `policy:create`, `policy:update`, `policy:delete`
- [ ] `HAFPermissionEnforcer` enforces `haf:create_override` and `haf:approve`

### Test Cases

```python
# Test 1: Unauthorized user cannot execute TRE action
user_id = "unauthorized-user"
try:
    tre_enforcer.check_execute_permission(user_id, "incident-123")
    assert False, "Should have raised PermissionDeniedError"
except PermissionDeniedError:
    pass

# Test 2: Authorized user can execute TRE action
user_id = "security-analyst-user"
# (User must have SECURITY_ANALYST role)
tre_enforcer.check_execute_permission(user_id, "incident-123")
# Should not raise exception

# Test 3: Direct API call without permission is blocked
# (Test with curl or similar)
curl -X POST http://localhost:8080/api/tre/execute \
  -H "Authorization: Bearer unauthorized-token" \
  -H "Content-Type: application/json"
# Should return 403 Forbidden
```

---

## 4. Audit Logging Verification

### Database Audit Log

- [ ] Permission checks are logged to `rbac_permission_audit` table
- [ ] Both ALLOW and DENY decisions are logged
- [ ] All required fields are populated (user_id, role, permission, decision, reason, timestamp)
- [ ] `ledger_entry_id` is populated when audit ledger is available

### Audit Ledger Events

- [ ] Permission checks emit `rbac_permission_check` events
- [ ] Allowed actions emit `rbac_user_action_allowed` events
- [ ] Denied actions emit `rbac_user_action_denied` events
- [ ] Events include user_id, role, permission, resource_id, outcome

### Verification Commands

```sql
-- Check audit log entries
SELECT decision, COUNT(*) 
FROM rbac_permission_audit 
GROUP BY decision;

-- Check recent permission checks
SELECT user_id, permission, decision, reason, timestamp
FROM rbac_permission_audit
ORDER BY timestamp DESC
LIMIT 10;
```

---

## 5. UI Integration Verification

### Role-Aware Rendering

- [ ] UI components are hidden based on user permissions
- [ ] Action buttons are disabled if permission missing
- [ ] Tabs are hidden if user lacks required permissions

### Server-Side Validation

- [ ] Backend blocks requests even if UI is bypassed
- [ ] Direct API calls without permission return 403 Forbidden
- [ ] UI permission checks match backend permission checks

### Test Cases

1. **Test as SECURITY_ANALYST**:
   - [ ] Can view incidents
   - [ ] Can execute TRE actions
   - [ ] Cannot edit policies
   - [ ] Cannot manage users

2. **Test as POLICY_MANAGER**:
   - [ ] Can view and edit policies
   - [ ] Can view incidents (read-only)
   - [ ] Cannot execute TRE actions
   - [ ] Cannot manage users

3. **Test as IT_ADMIN**:
   - [ ] Can manage agents
   - [ ] Can view system configuration
   - [ ] Cannot view incident details
   - [ ] Cannot execute TRE actions

4. **Test as AUDITOR**:
   - [ ] Can view all read-only data
   - [ ] Cannot click any action buttons
   - [ ] Cannot execute any actions
   - [ ] Cannot edit anything

---

## 6. Integration Verification

### Threat Response Engine (TRE)

- [ ] TRE API checks permissions before executing actions
- [ ] `tre:execute` permission is required
- [ ] `tre:rollback` permission is required
- [ ] Unauthorized requests are blocked

### Policy Engine

- [ ] Policy Engine API checks permissions before operations
- [ ] `policy:create`, `policy:update`, `policy:delete` permissions are required
- [ ] `policy:simulate` permission is required
- [ ] Unauthorized requests are blocked

### Human Authority Framework (HAF)

- [ ] HAF checks RBAC permissions BEFORE authority check
- [ ] `haf:create_override` permission is required
- [ ] `haf:approve` permission is required
- [ ] Unauthorized requests are blocked

### Audit Ledger

- [ ] RBAC component is in audit ledger component enum
- [ ] RBAC action types are in audit ledger action_type enum
- [ ] Permission checks emit audit ledger entries

---

## 7. Security Verification

### Default DENY

- [ ] Users without roles are denied all permissions
- [ ] Users with roles but missing specific permission are denied
- [ ] No implicit permissions are granted

### Server-Side Enforcement

- [ ] Backend blocks unauthorized requests
- [ ] UI hiding is not sufficient (test with direct API calls)
- [ ] No bypass flags or temporary admin shortcuts exist

### No Role Checks in Code

- [ ] No `if role == "ADMIN"` checks in code
- [ ] All access decisions use permission checks
- [ ] Permission names are used, not role names

---

## 8. Documentation Verification

- [ ] README.md exists and is complete
- [ ] Role definitions match specification exactly
- [ ] Permission model is documented
- [ ] Integration instructions are provided
- [ ] Verification checklist is provided (this document)

---

## Final Verification

Run the complete verification script:

```bash
python3 rbac/verify_rbac.py \
  --db-host localhost \
  --db-port 5432 \
  --db-name ransomeye \
  --db-user ransomeye \
  --db-password <password>
```

Expected output:
```
✅ Database schema verified
✅ Role-permission mappings verified
✅ Backend enforcement verified
✅ Audit logging verified
✅ UI integration verified
✅ Integration with other systems verified
✅ Security verified
✅ Documentation verified

STATUS: ✅ FULLY COMPLIANT
```

---

**AUTHORITATIVE**: This verification checklist must be completed before RBAC is considered production-ready.
