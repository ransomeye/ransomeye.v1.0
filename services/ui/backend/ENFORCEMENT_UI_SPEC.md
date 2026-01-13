# RansomEye v1.0 UI Enforcement Specification

**AUTHORITATIVE**: Complete specification for UI enforcement controls and human-in-the-loop safety.

---

## 1. Role-Aware Action Panels

### SUPER_ADMIN

**UI Capabilities:**
- ✅ All actions enabled
- ✅ Emergency override button
- ✅ Policy management
- ✅ User management
- ✅ Agent management
- ✅ Approval queue access

**Button States:**
- All action buttons: **ENABLED**
- Emergency override: **ENABLED** (with dual confirmation)
- Policy edit: **ENABLED**
- User management: **ENABLED**

### SECURITY_ANALYST

**UI Capabilities:**
- ✅ Execute SAFE actions
- ✅ Request DESTRUCTIVE actions (submit for approval)
- ✅ View approval queue
- ✅ Approve actions (if has haf:approve permission)
- ✅ Rollback actions

**Button States:**
- SAFE action buttons: **ENABLED** (if has tre:execute permission)
- DESTRUCTIVE action buttons: **DISABLED** (shows "Request Approval" button instead)
- Rollback button: **ENABLED** (if has tre:rollback permission)
- Policy edit: **DISABLED**

### POLICY_MANAGER

**UI Capabilities:**
- ✅ Policy tuning only
- ❌ No execution buttons
- ❌ No approval buttons

**Button States:**
- All action buttons: **DISABLED**
- Policy edit: **ENABLED** (if has policy:update permission)
- Execution buttons: **HIDDEN**

### IT_ADMIN

**UI Capabilities:**
- ✅ Agent operations only
- ❌ No incident actions
- ❌ No policy actions

**Button States:**
- Agent install/update: **ENABLED** (if has agent:* permissions)
- Incident actions: **DISABLED**
- Policy actions: **DISABLED**

### AUDITOR

**UI Capabilities:**
- ✅ Read-only access
- ❌ No action buttons
- ❌ No edit buttons

**Button States:**
- All action buttons: **HIDDEN**
- All edit buttons: **HIDDEN**
- View-only mode: **ENABLED**

---

## 2. Action Button Requirements

### Button States

1. **ENABLED**: Button is clickable, action will execute
2. **DISABLED**: Button is visible but disabled, shows reason
3. **HIDDEN**: Button is not rendered

### Disabled Button Display

When a button is disabled, it must:
- Show tooltip with reason (e.g., "Requires tre:execute permission")
- Display reason in button label or nearby text
- Be visually distinct (grayed out)

### Confirmation Dialogs

All action buttons must:
- Show confirmation dialog before execution
- Display action preview (action_type, target, incident_id)
- Require explicit confirmation click
- Show rollback availability

---

## 3. Human Authority Workflow UI

### Destructive Action Request Flow

1. **Analyst clicks DESTRUCTIVE action button**
   - Button shows "Request Approval" instead of "Execute"
   - Click opens approval request dialog

2. **Analyst submits request**
   - Fills in justification (optional but recommended)
   - Clicks "Submit for Approval"
   - Request stored in database with status PENDING

3. **Approver views pending requests**
   - Approval queue shows all pending requests
   - Shows: requested_by, action_type, incident_id, justification, expires_at

4. **Approver approves/rejects**
   - Clicks "Approve" or "Reject"
   - Optionally adds reason
   - Status updated to APPROVED or REJECTED

5. **TRE executes after approval**
   - Action executes automatically when approval_id is present
   - UI shows execution status

### Approval Queue UI

**Display:**
- List of pending approvals
- Sortable by: created_at, expires_at, requested_by
- Filterable by: incident_id, action_type, requested_by

**Actions:**
- Approve button (if user has haf:approve permission)
- Reject button (if user has haf:approve permission)
- View details button

---

## 4. Emergency Override UI

### Emergency Override Flow

1. **SUPER_ADMIN clicks Emergency Override button**
   - Button only visible to SUPER_ADMIN
   - Opens emergency override dialog

2. **SUPER_ADMIN fills in details**
   - Action type
   - Target
   - Justification (required, minimum 10 characters)
   - Dual confirmation checkbox

3. **System validates**
   - Checks SUPER_ADMIN role
   - Validates justification length
   - Validates dual confirmation

4. **Action executes**
   - Bypasses incident binding
   - Emits EMERGENCY_OVERRIDE_USED audit event
   - Creates rollback artifact

### Emergency Override UI Elements

- **Button**: Red "Emergency Override" button (SUPER_ADMIN only)
- **Dialog**: Modal dialog with:
  - Action type selector
  - Target input
  - Justification textarea (required, min 10 chars)
  - Dual confirmation checkbox
  - Warning message about audit logging

---

## 5. Rollback UX

### Rollback Availability Display

For each executed action, UI must show:
- ✅ Rollback available (green indicator)
- ❌ Rollback not available (gray indicator)
- ⚠️ Rollback requires approval (yellow indicator)

### Rollback Button

- **One-click rollback** button (if rollback available)
- Shows confirmation dialog:
  - Rollback reason (required)
  - Original action details
  - Rollback preview

### Rollback History

- **Per-incident rollback history**
- Shows: rollback_id, action_id, rollback_reason, rolled_back_at, rolled_back_by
- Filterable by: action_type, date range

### Rollback Failure Display

If rollback fails:
- Show error message
- Display failure reason
- Show retry button (if applicable)

---

## 6. Server-Side Enforcement

### Permission Checks

All UI actions must:
1. **Check permissions server-side** (not just UI-side)
2. **Return 403 Forbidden** if permission denied
3. **Emit audit ledger event** for both allow and deny

### No Hidden Endpoints

- All endpoints must be documented
- No backdoor endpoints
- No optimistic execution

### Explicit Error Surfaces

- All errors must be displayed to user
- Error messages must be clear and actionable
- No silent failures

---

## 7. Deterministic Rendering

### RBAC-Based Rendering

UI must render based on:
- User role (from authentication)
- User permissions (from RBAC check)
- Current incident state
- TRE mode

### No Assumptions

- UI must not assume permissions
- UI must check permissions for every action
- UI must reflect actual backend state

---

**AUTHORITATIVE**: This specification must be followed exactly for UI enforcement controls.
