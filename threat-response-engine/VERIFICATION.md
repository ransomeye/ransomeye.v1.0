# RansomEye v1.0 TRE Enforcement Verification

**AUTHORITATIVE**: Complete verification checklist for TRE enforcement mode activation with RBAC + HAF.

---

## 1. Enforcement Modes Verification

### Exactly Three Modes (FROZEN)

- [ ] `DRY_RUN` mode exists
- [ ] `GUARDED_EXEC` mode exists
- [ ] `FULL_ENFORCE` mode exists
- [ ] No additional modes exist

### Mode Behavior

#### DRY_RUN
- [ ] SAFE actions: Simulate only (no execution)
- [ ] DESTRUCTIVE actions: Simulate only (no execution)

#### GUARDED_EXEC
- [ ] SAFE actions: Execute
- [ ] DESTRUCTIVE actions: BLOCKED

#### FULL_ENFORCE
- [ ] SAFE actions: Execute
- [ ] DESTRUCTIVE actions: Execute only after HAF approval

### Mode Management

- [ ] Mode stored in database (`tre_execution_modes` table)
- [ ] Mode loaded at runtime
- [ ] Only SUPER_ADMIN can change mode
- [ ] Mode changes logged to audit ledger

### Verification Commands

```python
from threat_response_engine.engine.enforcement_mode import TREMode

# Verify exactly three modes
assert len(list(TREMode)) == 3
assert TREMode.DRY_RUN in TREMode
assert TREMode.GUARDED_EXEC in TREMode
assert TREMode.FULL_ENFORCE in TREMode
```

---

## 2. Action Classification Verification

### SAFE Actions (FROZEN)

- [ ] `BLOCK_PROCESS` classified as SAFE
- [ ] `BLOCK_NETWORK_CONNECTION` classified as SAFE
- [ ] `TEMPORARY_FIREWALL_RULE` classified as SAFE
- [ ] `QUARANTINE_FILE` classified as SAFE

### DESTRUCTIVE Actions (FROZEN)

- [ ] `ISOLATE_HOST` classified as DESTRUCTIVE
- [ ] `LOCK_USER` classified as DESTRUCTIVE
- [ ] `DISABLE_SERVICE` classified as DESTRUCTIVE
- [ ] `MASS_PROCESS_KILL` classified as DESTRUCTIVE
- [ ] `NETWORK_SEGMENT_ISOLATION` classified as DESTRUCTIVE

### Classification Immutability

- [ ] Classification not configurable
- [ ] Classification enforced in code
- [ ] Unknown actions raise ValueError

### Verification Commands

```python
from threat_response_engine.engine.enforcement_mode import (
    classify_action, ActionClassification, is_safe_action, is_destructive_action
)

# Verify SAFE actions
assert classify_action('BLOCK_PROCESS') == ActionClassification.SAFE
assert is_safe_action('BLOCK_PROCESS') == True

# Verify DESTRUCTIVE actions
assert classify_action('ISOLATE_HOST') == ActionClassification.DESTRUCTIVE
assert is_destructive_action('ISOLATE_HOST') == True

# Verify unknown action raises error
try:
    classify_action('UNKNOWN_ACTION')
    assert False, "Should have raised ValueError"
except ValueError:
    pass
```

---

## 3. Execution Pipeline Verification

### Pipeline Order (MANDATORY)

1. **Policy Decision** (input)
2. **RBAC Permission Check** (MANDATORY FIRST)
3. **TRE Mode Check**
4. **Action Classification Check**
5. **HAF Approval Check** (if required)
6. **Agent Command Signing**
7. **Agent Execution**
8. **Execution Result Recording**
9. **Rollback Record Creation**
10. **Audit Ledger Write**

### Pipeline Failure Behavior

- [ ] If RBAC check fails: STOP, LOG, RETURN FAILURE
- [ ] If mode check fails: STOP, LOG, RETURN FAILURE
- [ ] If HAF check fails: STOP, LOG, RETURN FAILURE
- [ ] No execution if any step fails

### Verification Test Cases

```python
# Test 1: RBAC denial blocks execution
try:
    pipeline.execute_pipeline(policy_decision, unauthorized_user_id, 'AUDITOR')
    assert False, "Should have raised PermissionDeniedError"
except PermissionDeniedError:
    pass

# Test 2: Mode blocks DESTRUCTIVE in GUARDED_EXEC
# Set mode to GUARDED_EXEC
# Try to execute ISOLATE_HOST
# Should raise EnforcementError

# Test 3: HAF approval required for DESTRUCTIVE in FULL_ENFORCE
# Set mode to FULL_ENFORCE
# Try to execute ISOLATE_HOST without approval
# Should raise EnforcementError with approval request
```

---

## 4. RBAC Integration Verification

### Required Permissions (EXACT)

- [ ] Execute SAFE action: `tre:execute` permission required
- [ ] Execute DESTRUCTIVE action: `tre:execute` permission required
- [ ] Rollback action: `tre:rollback` permission required
- [ ] Change TRE mode: `system:modify_config` permission required (SUPER_ADMIN only)

### RBAC Check Order

- [ ] RBAC check happens BEFORE HAF check
- [ ] RBAC check happens BEFORE mode check
- [ ] RBAC denial emits audit ledger entry

### Negative Tests

- [ ] Unauthorized user cannot execute SAFE action
- [ ] Unauthorized user cannot execute DESTRUCTIVE action
- [ ] Unauthorized user cannot rollback action
- [ ] Non-SUPER_ADMIN cannot change mode

### Verification Commands

```python
from rbac.integration.tre_integration import TREPermissionEnforcer

# Test RBAC denial
try:
    enforcer.check_execute_safe_permission('unauthorized-user', 'incident-123')
    assert False, "Should have raised PermissionDeniedError"
except PermissionDeniedError:
    pass
```

---

## 5. HAF Integration Verification

### HAF Check Order

- [ ] RBAC check happens BEFORE HAF check
- [ ] HAF check only for DESTRUCTIVE actions in FULL_ENFORCE mode

### HAF Approval Requirements

- [ ] Approval request created for DESTRUCTIVE actions
- [ ] Approval request persisted in database
- [ ] Approval must include: approver_user_id, role, timestamp, signed decision
- [ ] Only SUPER_ADMIN or SECURITY_ANALYST with approval rights can approve

### HAF Rejection Behavior

- [ ] Rejected approvals block execution
- [ ] Expired approvals block execution
- [ ] Pending approvals block execution

### Verification Test Cases

```python
# Test 1: HAF approval required
# Execute DESTRUCTIVE action in FULL_ENFORCE mode
# Should create approval request
# Should raise EnforcementError with approval_id

# Test 2: HAF rejection blocks execution
# Reject approval request
# Try to execute action
# Should raise EnforcementError

# Test 3: HAF approval allows execution
# Approve request
# Execute action
# Should succeed
```

---

## 6. Agent Command Execution Verification

### Command Requirements

- [ ] Command signed with ed25519
- [ ] Command includes: command_id, action_type, target_id, incident_id, issued_by_user_id, tre_mode, approval_id
- [ ] Command is idempotent
- [ ] Rollback token generated

### Agent Verification

- [ ] Agent verifies signature
- [ ] Agent verifies freshness
- [ ] Agent executes exactly once
- [ ] Agent emits execution receipt

### Verification Commands

```python
# Verify command structure
assert 'command_id' in command_payload
assert 'action_type' in command_payload
assert 'target_id' in command_payload
assert 'incident_id' in command_payload
assert 'issued_by_user_id' in command_payload
assert 'tre_mode' in command_payload
assert 'approval_id' in command_payload or action is SAFE
```

---

## 7. Rollback Verification

### Rollback Requirements

- [ ] Rollback record created BEFORE execution
- [ ] Rollback requires RBAC check
- [ ] Rollback requires HAF approval if original action was destructive
- [ ] Rollback fully auditable

### Rollback Failure Handling

- [ ] Rollback failures logged
- [ ] Rollback failures never silently ignored

### Verification Test Cases

```python
# Test 1: Rollback requires RBAC permission
try:
    tre_api.rollback_action(action_id, 'reason', user_id='unauthorized-user')
    assert False, "Should have raised PermissionDeniedError"
except PermissionDeniedError:
    pass

# Test 2: Rollback of destructive action requires HAF
# Rollback ISOLATE_HOST action
# Should require HAF approval
```

---

## 8. Database Schema Verification

### Required Tables

- [ ] `tre_execution_modes` table exists
- [ ] `tre_action_executions` table exists (response_actions)
- [ ] `tre_action_approvals` table exists
- [ ] `tre_rollback_records` table exists (rollback_records)

### Table Constraints

- [ ] Only one active mode at a time
- [ ] All records immutable
- [ ] All records timestamped
- [ ] All records linked via IDs

### Verification Commands

```sql
-- Check tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name LIKE 'tre_%';

-- Check only one active mode
SELECT COUNT(*) FROM tre_execution_modes WHERE is_active = TRUE;
-- Should return 1 or 0
```

---

## 9. Audit Ledger Verification

### Required Event Types

- [ ] `tre_mode_changed` - Mode change events
- [ ] `tre_action_requested` - Action request events
- [ ] `tre_action_blocked` - Action block events
- [ ] `tre_action_approved` - Action approval events
- [ ] `tre_action_executed` - Action execution events
- [ ] `tre_action_failed` - Action failure events
- [ ] `tre_rollback_requested` - Rollback request events
- [ ] `tre_rollback_executed` - Rollback execution events
- [ ] `tre_rbac_deny` - RBAC denial events
- [ ] `tre_haf_deny` - HAF denial events

### Event Requirements

- [ ] All events include: user_id, role, action_type, target, incident_id, outcome
- [ ] Both ALLOW and DENY decisions logged
- [ ] Events immutable and tamper-evident

### Verification Commands

```python
# Verify event types in schema
from audit_ledger.schema.ledger_entry import ACTION_TYPES

assert 'tre_mode_changed' in ACTION_TYPES
assert 'tre_action_requested' in ACTION_TYPES
assert 'tre_action_blocked' in ACTION_TYPES
assert 'tre_action_approved' in ACTION_TYPES
assert 'tre_action_executed' in ACTION_TYPES
assert 'tre_action_failed' in ACTION_TYPES
assert 'tre_rollback_requested' in ACTION_TYPES
assert 'tre_rollback_executed' in ACTION_TYPES
assert 'tre_rbac_deny' in ACTION_TYPES
assert 'tre_haf_deny' in ACTION_TYPES
```

---

## 10. UI Integration Verification

### Role-Aware Rendering

- [ ] Execute buttons shown only if RBAC allows
- [ ] Approval queue shown only to HAF approvers
- [ ] SAFE vs DESTRUCTIVE clearly labeled
- [ ] DRY_RUN vs ENFORCE clearly labeled
- [ ] Execution history shown (immutable)
- [ ] Bulk destructive actions require confirmation

### Server-Side Validation

- [ ] Backend blocks unauthorized requests
- [ ] Backend blocks even if UI bypassed
- [ ] UI hiding is NOT security (backend enforces)

### Verification Test Cases

```bash
# Test 1: Direct API call without permission
curl -X POST http://localhost:8080/api/tre/execute \
  -H "Authorization: Bearer unauthorized-token" \
  -H "Content-Type: application/json" \
  -d '{"action": "ISOLATE_HOST", "incident_id": "123"}'
# Should return 403 Forbidden

# Test 2: Direct API call with permission but wrong mode
# Set mode to GUARDED_EXEC
# Try to execute DESTRUCTIVE action
# Should return 403 Forbidden or 400 Bad Request
```

---

## 11. Negative Tests (MANDATORY)

### RBAC Bypass Tests

- [ ] Cannot bypass RBAC by calling API directly
- [ ] Cannot bypass RBAC by modifying UI
- [ ] Cannot bypass RBAC by manipulating requests

### HAF Rejection Tests

- [ ] Rejected approvals block execution
- [ ] Expired approvals block execution
- [ ] Pending approvals block execution

### Mode Bypass Tests

- [ ] Cannot execute DESTRUCTIVE in GUARDED_EXEC by bypassing mode check
- [ ] Cannot execute without HAF in FULL_ENFORCE by bypassing approval check

### Verification Test Cases

```python
# Test 1: RBAC bypass attempt
# Try to execute action without RBAC check
# Should fail

# Test 2: HAF bypass attempt
# Try to execute DESTRUCTIVE action without approval
# Should fail

# Test 3: Mode bypass attempt
# Try to execute DESTRUCTIVE in GUARDED_EXEC
# Should fail
```

---

## 12. Proof of Enforcement

### Destructive Actions Do NOT Run Without Approval

- [ ] Test: Execute ISOLATE_HOST in FULL_ENFORCE without approval
- [ ] Result: Action blocked, approval request created
- [ ] Test: Execute ISOLATE_HOST in FULL_ENFORCE with approval
- [ ] Result: Action executed

### Rollback is Impossible Without Permission

- [ ] Test: Rollback action without `tre:rollback` permission
- [ ] Result: Rollback blocked, RBAC denial logged

### Audit Trail is Complete and Replayable

- [ ] All actions logged to database
- [ ] All actions logged to audit ledger
- [ ] Audit trail can be replayed
- [ ] Audit trail is immutable

### Verification Commands

```python
# Test complete audit trail
action_id = execute_action(...)
rollback_id = rollback_action(action_id, ...)

# Verify audit trail
audit_entries = get_audit_entries(action_id)
assert len(audit_entries) >= 2  # Execution + rollback
assert all(entry['immutable'] for entry in audit_entries)
```

---

## Final Verification

Run complete verification script:

```bash
python3 threat-response-engine/verify_enforcement.py \
  --db-host localhost \
  --db-port 5432 \
  --db-name ransomeye \
  --db-user ransomeye \
  --db-password <password>
```

Expected output:
```
✅ Enforcement modes verified
✅ Action classification verified
✅ Execution pipeline verified
✅ RBAC integration verified
✅ HAF integration verified
✅ Agent command execution verified
✅ Rollback verified
✅ Database schema verified
✅ Audit ledger verified
✅ UI integration verified
✅ Negative tests passed
✅ Proof of enforcement verified

STATUS: ✅ FULLY COMPLIANT
```

---

**AUTHORITATIVE**: This verification checklist must be completed before TRE enforcement is considered production-ready.
