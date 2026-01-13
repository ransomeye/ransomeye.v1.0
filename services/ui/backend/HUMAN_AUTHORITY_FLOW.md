# RansomEye v1.0 Human Authority Flow

**AUTHORITATIVE**: Complete flow for human authority approval workflow.

---

## 1. Two-Step Approval Workflow

### Step 1: Analyst Submits Request

**Who**: SECURITY_ANALYST (or user with tre:execute permission)

**Action**:
1. Analyst clicks DESTRUCTIVE action button
2. UI shows "Request Approval" button (not "Execute")
3. Analyst clicks "Request Approval"
4. UI shows approval request dialog
5. Analyst fills:
   - Action type (pre-filled)
   - Target (pre-filled)
   - Incident ID (pre-filled)
   - Justification (optional but recommended)
6. Analyst clicks "Submit for Approval"

**Backend**:
- Creates approval request in `tre_action_approvals` table
- Status: PENDING
- Expires: 24 hours from creation
- Emits `ui_action_requested` audit event

### Step 2: Approver Approves

**Who**: SUPER_ADMIN or SECURITY_ANALYST with haf:approve permission

**Action**:
1. Approver views approval queue
2. Approver sees pending request:
   - Requested by (user_id, role)
   - Action type
   - Target
   - Incident ID
   - Justification
   - Expires at
3. Approver clicks "Approve" or "Reject"
4. If approving, optionally adds reason
5. Approver confirms approval

**Backend**:
- Updates approval request status to APPROVED or REJECTED
- Sets approver_user_id, approver_role, approval_timestamp
- Emits `ui_action_approved` or `ui_action_rejected` audit event
- If approved, action executes automatically

---

## 2. Approval Queue

### Display

**Columns**:
- Approval ID
- Requested By (user_id, role)
- Action Type
- Target
- Incident ID
- Justification
- Created At
- Expires At
- Status

**Filters**:
- Status (PENDING, APPROVED, REJECTED, EXPIRED)
- Incident ID
- Action Type
- Requested By

**Sorting**:
- Created At (newest first)
- Expires At (soonest first)
- Requested By

### Actions

- **Approve**: Approve request (requires haf:approve permission)
- **Reject**: Reject request (requires haf:approve permission)
- **View Details**: View full request details

---

## 3. Approval Requirements

### Who Can Approve

- **SUPER_ADMIN**: Can approve all requests
- **SECURITY_ANALYST**: Can approve if has haf:approve permission

### Approval Validation

1. **Role Check**: Approver must be SUPER_ADMIN or SECURITY_ANALYST
2. **Permission Check**: Approver must have haf:approve permission
3. **Status Check**: Request must be PENDING
4. **Expiry Check**: Request must not be expired

### Approval Expiry

- Requests expire 24 hours after creation
- Expired requests cannot be approved
- Expired requests are automatically marked as EXPIRED

---

## 4. Execution After Approval

### Automatic Execution

When approval is granted:
1. Backend receives approval notification
2. Backend checks approval status (must be APPROVED)
3. Backend executes action via TRE
4. TRE executes action on agent
5. Execution result returned to UI

### Execution Requirements

- Approval ID must be present in command
- Approval status must be APPROVED
- Approval must not be expired
- All other execution requirements must be met (RBAC, incident context, etc.)

---

## 5. Rejection Handling

### Rejection Flow

1. Approver clicks "Reject"
2. Approver optionally adds reason
3. Backend updates approval status to REJECTED
4. Backend emits `ui_action_rejected` audit event
5. UI shows rejection notification to analyst

### Rejection Consequences

- Action does not execute
- Analyst can submit new request if needed
- Rejection reason is logged for audit

---

## 6. Audit Trail

### Approval Events

- `ui_action_requested` - Analyst submitted request
- `ui_action_approved` - Approver approved request
- `ui_action_rejected` - Approver rejected request
- `ui_action_executed` - Action executed after approval

### Event Payload

All events include:
- `user_id` - User who triggered event
- `role` - User role
- `approval_id` - Approval identifier
- `action_type` - Action type
- `incident_id` - Incident identifier
- `decision` - Decision (REQUESTED, APPROVED, REJECTED)
- `timestamp` - Event timestamp

---

**AUTHORITATIVE**: This flow must be followed exactly for human authority approval workflow.
