# RansomEye v1.0 Incident Execution Lifecycle

**AUTHORITATIVE**: Complete lifecycle for incident-bound execution.

---

## 1. Incident States

### Active States

- **NEW**: Incident just created
- **IN_PROGRESS**: Incident being investigated
- **ESCALATED**: Incident escalated for response

### Terminal States

- **CLOSED**: Incident resolved, no further actions allowed
- **ARCHIVED**: Incident archived, read-only access

---

## 2. Action Execution Rules

### Incident-Bound Execution

All response actions must:
- Reference `incident_id` (required)
- Reference `incident_stage` (required)
- Reference `policy_decision_id` (recommended)

### State-Based Restrictions

| Incident State | Action Execution | Emergency Override |
| -------------- | ---------------- | ------------------ |
| NEW            | ✅ Allowed       | ✅ Allowed (SUPER_ADMIN) |
| IN_PROGRESS    | ✅ Allowed       | ✅ Allowed (SUPER_ADMIN) |
| ESCALATED      | ✅ Allowed       | ✅ Allowed (SUPER_ADMIN) |
| CLOSED         | ❌ Blocked       | ✅ Allowed (SUPER_ADMIN) |
| ARCHIVED       | ❌ Blocked       | ✅ Allowed (SUPER_ADMIN) |

---

## 3. Execution Flow

### Standard Execution Flow

```
1. User clicks action button
   ↓
2. UI checks RBAC permissions (client-side)
   ↓
3. UI shows confirmation dialog
   ↓
4. User confirms action
   ↓
5. UI sends request to backend
   ↓
6. Backend checks RBAC permissions (server-side)
   ↓
7. Backend validates incident context
   ↓
8. Backend checks TRE mode
   ↓
9. Backend checks HAF approval (if required)
   ↓
10. Backend executes action via TRE
   ↓
11. TRE executes action on agent
   ↓
12. Agent executes action
   ↓
13. Execution result returned to UI
   ↓
14. UI updates display
```

### Destructive Action Flow

```
1. User clicks DESTRUCTIVE action button
   ↓
2. UI shows "Request Approval" button (not "Execute")
   ↓
3. User clicks "Request Approval"
   ↓
4. UI shows approval request dialog
   ↓
5. User fills justification and submits
   ↓
6. Backend creates approval request (status: PENDING)
   ↓
7. Approver views approval queue
   ↓
8. Approver approves/rejects request
   ↓
9. If approved, action executes automatically
   ↓
10. Execution result returned to UI
```

### Emergency Override Flow

```
1. SUPER_ADMIN clicks Emergency Override button
   ↓
2. UI shows emergency override dialog
   ↓
3. SUPER_ADMIN fills:
   - Action type
   - Target
   - Justification (required, min 10 chars)
   - Dual confirmation
   ↓
4. Backend validates:
   - SUPER_ADMIN role
   - Justification length
   - Dual confirmation
   ↓
5. Backend emits EMERGENCY_OVERRIDE_USED event
   ↓
6. Backend bypasses incident binding
   ↓
7. Backend executes action via TRE
   ↓
8. TRE creates rollback artifact
   ↓
9. Execution result returned to UI
```

---

## 4. Incident Execution Guard

### Validation Rules

1. **Incident ID Required** (unless emergency)
   - Non-emergency actions must have incident_id
   - Emergency actions can bypass incident_id

2. **Incident State Check**
   - CLOSED incidents: Actions blocked
   - ARCHIVED incidents: Actions blocked
   - Active incidents: Actions allowed

3. **Policy Decision ID** (recommended)
   - Not mandatory but recommended
   - Links action to policy decision

---

## 5. Rollback Lifecycle

### Rollback Execution Flow

```
1. User clicks Rollback button
   ↓
2. UI shows rollback confirmation dialog
   ↓
3. User fills rollback reason
   ↓
4. Backend checks RBAC permission (tre:rollback)
   ↓
5. Backend checks HAF approval (if original was destructive)
   ↓
6. Backend sends rollback command to TRE
   ↓
7. TRE sends rollback command to agent
   ↓
8. Agent loads rollback artifact
   ↓
9. Agent executes rollback
   ↓
10. Rollback result returned to UI
```

### Rollback Requirements

- **RBAC Permission**: tre:rollback required
- **HAF Approval**: Required if original action was destructive
- **Rollback Artifact**: Must exist (created before original execution)
- **Incident Scope**: Rollback must reference same incident_id

---

## 6. Audit Trail

### Execution Audit Events

Every action execution emits:
- `ui_action_requested` - User requested action
- `ui_action_blocked` - Action blocked (if blocked)
- `ui_action_approved` - Action approved (if required)
- `ui_action_executed` - Action executed
- `ui_action_rolled_back` - Action rolled back (if rolled back)

### Emergency Override Audit Events

Emergency overrides emit:
- `ui_emergency_override` - Emergency override used

### Event Payload

All events include:
- `user_id` - User who triggered action
- `role` - User role
- `incident_id` - Incident identifier
- `action_type` - Action type
- `decision` - Decision (ALLOW, DENY, APPROVED, REJECTED)
- `timestamp` - Event timestamp

---

**AUTHORITATIVE**: This lifecycle must be followed exactly for incident-bound execution.
