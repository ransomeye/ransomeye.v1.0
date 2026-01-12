# RansomEye Incident Response & Playbook Engine

**AUTHORITATIVE:** Deterministic, sandboxed playbook execution with explicit authority and audit integration

## Overview

The RansomEye Incident Response & Playbook Engine provides **deterministic, sandboxed playbook execution** with **explicit authority requirements** and **complete audit integration**. Playbooks are **declarative data, not code**, ensuring safety, reproducibility, and verifiability.

## Core Principles

### Playbooks are Data, Not Code

**CRITICAL**: Playbooks are declarative only:

- ✅ **JSON/YAML only**: Playbooks are structured data, not executable code
- ✅ **No scripting**: No arbitrary scripts or shell execution
- ✅ **No runtime mutation**: Playbooks cannot be modified at runtime
- ✅ **No background autonomy**: No autonomous background execution

### Deterministic Execution

**CRITICAL**: Execution is deterministic:

- ✅ **Same inputs → same output**: Same playbook and inputs always produce same execution
- ✅ **Sandboxed**: No system calls, no network access, no privilege escalation
- ✅ **Replayable**: Executions can be replayed deterministically
- ✅ **Sequential**: Steps executed sequentially (no loops, branching, conditionals)

### Explicit Authority

**CRITICAL**: Every execution requires explicit authority:

- ✅ **Valid playbook signature**: Playbook must be signed and verified
- ✅ **Valid authority action**: Human authority action (HAF) required
- ✅ **Matching scope**: Scope must match between playbook and authority
- ✅ **Explanation bundle**: Explanation bundle reference (SEE) required

### Complete Audit Integration

**CRITICAL**: All operations are audited:

- ✅ **Execution records**: Every execution produces immutable record
- ✅ **Audit ledger entries**: Every operation emits audit ledger entry
- ✅ **Rollback logging**: All rollbacks are logged
- ✅ **Validator-verifiable**: All operations can be verified by Global Validator

## Playbook Model

### Step Types (Frozen Enum)

Supported step types:

- **isolate_host**: Isolate host from network
- **block_ip**: Block IP address
- **disable_account**: Disable user account
- **snapshot_memory**: Snapshot process memory
- **snapshot_disk**: Snapshot disk
- **notify_human**: Notify human operator

### Playbook Constraints

**STRICT**: Playbooks have strict constraints:

- ✅ **Declarative only**: JSON/YAML structure only
- ✅ **No loops**: No looping constructs
- ✅ **No branching**: No conditional branching
- ✅ **No conditionals**: No if/then/else logic
- ✅ **No variables**: No variable substitution
- ✅ **No scripting**: No script execution
- ✅ **Sequential only**: Steps executed in order

## Execution Rules

### Execution Requirements

Every execution requires:

1. **Valid playbook signature**: Playbook must be cryptographically signed
2. **Valid authority action**: Human authority action (HAF) must be valid
3. **Matching scope**: Playbook scope must match authority scope
4. **Explanation bundle reference**: Explanation bundle (SEE) must be referenced

### Execution Process

1. **Get playbook**: Retrieve playbook from registry
2. **Validate authority**: Verify authority action is valid
3. **Execute steps**: Execute steps sequentially
4. **Record results**: Record step results
5. **Store execution**: Store execution record
6. **Emit audit entry**: Emit audit ledger entry

### Sandbox Enforcement

Execution is sandboxed:

- ✅ **No system calls**: No direct system calls
- ✅ **No network access**: No network operations
- ✅ **No privilege escalation**: No privilege changes
- ✅ **Declarative output only**: Steps produce declarative output only

## Rollback

### Rollback Requirements

Rollback requires:

- ✅ **Explicit**: Rollbacks are explicit, never implicit
- ✅ **Signed**: Rollbacks are signed (via authority action)
- ✅ **Logged**: All rollbacks are logged to audit ledger
- ✅ **Deterministic**: Same execution always produces same rollback

### Rollback Process

1. **Get execution record**: Retrieve execution record
2. **Create rollback record**: Generate rollback steps (reverse order)
3. **Store rollback**: Store rollback record
4. **Update execution**: Update execution status
5. **Emit audit entry**: Emit audit ledger entry

## Usage

### Register Playbook

```bash
python3 incident-response/cli/register_playbook.py \
    --playbook /path/to/playbook.json \
    --registry /var/lib/ransomeye/ir/playbooks.jsonl \
    --public-keys-dir /var/lib/ransomeye/ir/keys \
    --executions-store /var/lib/ransomeye/ir/executions.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output registered_playbook.json
```

### Execute Playbook

```bash
python3 incident-response/cli/execute_playbook.py \
    --playbook-id <playbook-uuid> \
    --subject-id <incident-id> \
    --authority-action-id <authority-action-uuid> \
    --explanation-bundle-id <explanation-bundle-uuid> \
    --executed-by analyst@example.com \
    --registry /var/lib/ransomeye/ir/playbooks.jsonl \
    --public-keys-dir /var/lib/ransomeye/ir/keys \
    --executions-store /var/lib/ransomeye/ir/executions.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output execution.json
```

### Rollback Execution

```bash
python3 incident-response/cli/rollback_playbook.py \
    --execution-id <execution-uuid> \
    --rolled-back-by analyst@example.com \
    --rollback-reason "False positive, revert isolation" \
    --registry /var/lib/ransomeye/ir/playbooks.jsonl \
    --public-keys-dir /var/lib/ransomeye/ir/keys \
    --executions-store /var/lib/ransomeye/ir/executions.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output rollback.json
```

## Playbook Format

```json
{
  "playbook_id": "playbook-uuid",
  "playbook_name": "Isolate Host Playbook",
  "playbook_version": "1.0.0",
  "scope": "incident",
  "steps": [
    {
      "step_id": "step-uuid-1",
      "step_type": "isolate_host",
      "step_order": 0,
      "parameters": {
        "host_id": "${subject_id}",
        "isolation_method": "network_quarantine"
      }
    },
    {
      "step_id": "step-uuid-2",
      "step_type": "notify_human",
      "step_order": 1,
      "parameters": {
        "notification_target": "security-team@example.com",
        "notification_message": "Host isolated",
        "notification_channel": "email"
      }
    }
  ],
  "playbook_signature": "base64-signature",
  "playbook_key_id": "key-id",
  "created_at": "2025-01-10T12:00:00Z",
  "created_by": "analyst@example.com"
}
```

## File Structure

```
incident-response/
├── schema/
│   ├── playbook.schema.json           # Frozen JSON schema for playbooks
│   ├── playbook-step.schema.json      # Frozen JSON schema for steps
│   └── execution-record.schema.json  # Frozen JSON schema for executions
├── crypto/
│   ├── __init__.py
│   ├── playbook_signer.py             # Playbook signing
│   └── playbook_verifier.py            # Playbook verification
├── engine/
│   ├── __init__.py
│   ├── playbook_registry.py           # Playbook storage and retrieval
│   ├── execution_engine.py            # Deterministic execution
│   └── rollback_engine.py              # Rollback processing
├── api/
│   ├── __init__.py
│   └── ir_api.py                      # IR API with audit integration
├── cli/
│   ├── __init__.py
│   ├── register_playbook.py           # Register playbook CLI
│   ├── execute_playbook.py            # Execute playbook CLI
│   └── rollback_playbook.py          # Rollback CLI
└── README.md                          # This file
```

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **cryptography**: Required for ed25519 signing (pip install cryptography)
- **Audit Ledger**: Required for audit trail (separate subsystem)

## Security Considerations

1. **Sandboxed Execution**: No system calls, network access, or privilege escalation
2. **Declarative Only**: Playbooks are data, not code
3. **Explicit Authority**: Every execution requires valid authority action
4. **Cryptographic Signing**: All playbooks are signed and verified
5. **Complete Audit**: All operations are logged to audit ledger
6. **Deterministic**: Same inputs always produce same execution

## Limitations

1. **No Implicit Execution**: All execution is explicit
2. **No Silent Automation**: All automation is logged
3. **No Unsigned Actions**: All actions are signed
4. **No Authority Bypass**: Authority is mandatory
5. **No Scripting**: No script execution in playbooks

## Future Enhancements

- Advanced step types
- Step dependencies
- Execution scheduling
- Multi-subject execution
- Execution templates

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye Incident Response & Playbook Engine documentation.
