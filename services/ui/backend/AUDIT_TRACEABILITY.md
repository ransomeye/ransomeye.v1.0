# RansomEye v1.0 Audit Traceability

**AUTHORITATIVE**: Complete audit traceability specification for UI actions.

---

## 1. Audit Event Types

### UI Action Events

- `ui_action_requested` - User requested action
- `ui_action_blocked` - Action blocked (RBAC/incident state/etc.)
- `ui_action_approved` - Action approved (HAF approval)
- `ui_action_executed` - Action executed
- `ui_action_rolled_back` - Action rolled back
- `ui_emergency_override` - Emergency override used

### Event Payload Structure

All UI events must include:
```json
{
  "user_id": "uuid",
  "role": "SUPER_ADMIN|SECURITY_ANALYST|...",
  "incident_id": "uuid|null",
  "action_type": "BLOCK_PROCESS|...",
  "decision": "ALLOW|DENY|APPROVED|REJECTED",
  "timestamp": "RFC3339",
  "reason": "string|null"
}
```

---

## 2. Event Emission Rules

### Every Click → Auditable Decision

- **Action Button Click**: Emit `ui_action_requested`
- **Permission Denied**: Emit `ui_action_blocked`
- **Approval Granted**: Emit `ui_action_approved`
- **Action Executed**: Emit `ui_action_executed`
- **Rollback Executed**: Emit `ui_action_rolled_back`
- **Emergency Override**: Emit `ui_emergency_override`

### Server-Side Only

- All events emitted server-side (not client-side)
- Client-side actions are advisory only
- Server-side validation is authoritative

---

## 3. Audit Trail Completeness

### Required Information

Every audit event must include:
1. **Who**: user_id, role
2. **What**: action_type, target
3. **When**: timestamp
4. **Where**: incident_id (if applicable)
5. **Why**: reason, justification
6. **Outcome**: decision, result

### Immutability

- Audit events are immutable
- Events cannot be modified or deleted
- Events are append-only

---

## 4. Traceability Requirements

### Action Traceability

For every action, audit trail must show:
1. Who requested it (user_id, role)
2. When it was requested (timestamp)
3. Whether it was approved (if required)
4. Who approved it (if applicable)
5. When it was executed (timestamp)
6. Execution result (SUCCESS, FAILED)
7. Whether it was rolled back (if applicable)
8. Who rolled it back (if applicable)

### Incident Traceability

For every incident, audit trail must show:
1. All actions executed for that incident
2. All approvals granted/rejected
3. All rollbacks executed
4. All emergency overrides used

### User Traceability

For every user, audit trail must show:
1. All actions requested
2. All actions approved/rejected
3. All actions executed
4. All rollbacks executed
5. All emergency overrides used

---

## 5. Audit Ledger Integration

### Event Forwarding

- UI events forwarded to audit ledger
- Events stored in append-only ledger
- Events are tamper-evident

### Event Querying

- Events queryable by: user_id, incident_id, action_type, timestamp
- Events sortable by timestamp
- Events filterable by decision, role, etc.

---

## 6. Compliance Requirements

### Regulatory Compliance

Audit trail supports:
- **SOC 2**: Access control and audit requirements
- **ISO 27001**: Audit logging requirements
- **HIPAA**: Audit trail requirements
- **PCI DSS**: Audit logging requirements
- **GDPR**: Audit trail requirements

### Audit Retention

- Audit events retained indefinitely
- Events are immutable and tamper-evident
- Events can be exported for compliance reporting

---

**AUTHORITATIVE**: This specification must be followed exactly for audit traceability.
