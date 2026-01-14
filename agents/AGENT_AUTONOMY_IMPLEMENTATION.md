# RansomEye v1.0 GA - Agent Autonomy Implementation

**AUTHORITATIVE:** Agent autonomous enforcement when Core is offline (GA-BLOCKING)

## Overview

This document describes the implementation of agent autonomy - the ability for endpoint agents to continue enforcing policy even when the Core/C2 server is unreachable, destroyed, or under attack.

## GA-BLOCKING Requirements

1. **Agent MUST NOT fail open** when Core is unreachable
2. **Agent MUST enforce last known good policy** from secure cache
3. **If no policy exists, agent MUST default to DENY** (fail-closed)
4. **Agent MUST NOT crash** when Core is offline
5. **Behavior MUST be deterministic and logged**

## Implementation

### Policy Cache

**Location:** `/var/lib/ransomeye/agent/cached_policy.json` (configurable via `RANSOMEYE_CACHED_POLICY_PATH`)

**Structure:**
```json
{
  "version": "1.0",
  "prohibited_actions": [
    "BLOCK_PROCESS",
    "QUARANTINE_FILE",
    "ISOLATE_HOST"
  ],
  "allowed_actions": [],
  "last_updated": "2024-01-15T10:30:00Z",
  "integrity_hash": "sha256_hash_of_policy"
}
```

**Security:**
- Policy cache is integrity-checked at startup using SHA256 hash
- If integrity check fails, agent defaults to DENY (fail-closed)
- Policy is updated only when Core is online and provides new policy

### Autonomous Enforcement Logic

**When Core is Online:**
- Normal operation
- Core verifies all commands
- Policy cache is updated when Core provides new policy

**When Core is Offline:**
1. Agent detects Core is unreachable (health check fails)
2. Agent loads cached policy (or defaults to DENY if no policy exists)
3. Agent enforces cached policy autonomously:
   - **Prohibited actions** → REJECT (fail-closed)
   - **Actions not in allow-list** → REJECT (fail-closed)
   - **No allow-list exists** → REJECT (default deny)
   - **Explicitly allowed actions** → ALLOW (with logging)

### Core Connectivity Check

**Method:** `_is_core_online()`

**Endpoint:** `http://localhost:8000/health` (configurable via `RANSOMEYE_CORE_ENDPOINT`)

**Timeout:** 2 seconds

**Behavior:**
- Returns `True` if Core health endpoint responds with HTTP 200
- Returns `False` if Core is unreachable (connection refused, timeout, etc.)

### Logging

**Autonomous Enforcement Log Messages:**

1. **Policy Loaded:**
   ```
   GA-BLOCKING: Cached policy loaded successfully. Version: 1.0, Last updated: 2024-01-15T10:30:00Z
   ```

2. **Core Offline - Autonomous Enforcement Active:**
   ```
   GA-BLOCKING: Core offline — autonomous enforcement active. Action: BLOCK_PROCESS, Cached policy version: 1.0
   ```

3. **Action Blocked (Prohibited):**
   ```
   GA-BLOCKING: Core offline — Action BLOCK_PROCESS is prohibited by cached policy. Agent enforcing autonomous fail-closed policy. Action denied.
   ```

4. **Action Blocked (Default Deny):**
   ```
   GA-BLOCKING: Core offline — No policy available — default deny enforced. Action BLOCK_PROCESS denied (fail-closed).
   ```

5. **Action Allowed:**
   ```
   GA-BLOCKING: Core offline — Action BLOCK_PROCESS allowed by cached policy. Autonomous enforcement: ALLOWED
   ```

## Validation Test

**Test File:** `agents/linux/tests/test_agent_autonomy.py`

**Test Scenarios:**

1. **Agent enforces policy when Core offline**
   - Agent starts with cached policy
   - Core becomes unreachable
   - Prohibited action attempted
   - Agent blocks action (fail-closed)

2. **Agent defaults to DENY when no policy exists**
   - Agent starts with no cached policy
   - Core becomes unreachable
   - Any action attempted
   - Agent blocks action (default deny)

3. **Agent does not crash when Core offline**
   - Agent starts normally
   - Core becomes unreachable
   - Multiple commands processed
   - Agent remains running (no crash)

4. **Agent logs autonomous enforcement explicitly**
   - Agent starts with cached policy
   - Core becomes unreachable
   - Action attempted
   - Agent logs explicit autonomous enforcement message

## Example Logs (Offline Enforcement)

```
2024-01-15T10:30:00Z [WARNING] GA-BLOCKING: Core offline — autonomous enforcement active. Action: BLOCK_PROCESS, Cached policy version: 1.0
2024-01-15T10:30:00Z [ERROR] GA-BLOCKING: Core offline — Action BLOCK_PROCESS is prohibited by cached policy. Agent enforcing autonomous fail-closed policy. Action denied.
2024-01-15T10:30:00Z [INFO] Audit log: command_rejected, command_id: test-command-1, outcome: REJECTED, reason: GA-BLOCKING: Core offline — Action BLOCK_PROCESS is prohibited...
```

## Fail-Closed Guarantees

1. **No fail-open paths:** All code paths default to DENY when Core is offline
2. **No silent degradation:** All enforcement decisions are explicitly logged
3. **No best-effort mode:** Agent either enforces policy or denies action (no partial enforcement)
4. **Deterministic behavior:** Same policy + same action → same result (logged)
5. **No crashes:** Agent handles all error conditions gracefully

## Acceptance Criteria

✅ Agent enforces policy without Core  
✅ No fail-open paths  
✅ No crash  
✅ Behavior is deterministic and logged  
