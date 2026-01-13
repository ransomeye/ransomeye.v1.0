# RansomEye v1.0 Threat Response Engine (TRE)

**AUTHORITATIVE:** Execution-only engine for Policy Engine decisions with mandatory rollback, cryptographic signing, and audit-ledger integration

## Overview

The RansomEye Threat Response Engine (TRE) is an **execution-only** subsystem that executes final Policy Engine decisions. TRE **does NOT make decisions** — it only executes decisions made by the Policy Engine, subject to Human Authority Framework (HAF) requirements.

## Core Principles

### Execution-Only, Not Decision-Making

**CRITICAL**: TRE is execution-only, not decision-making:

- ✅ **Executes ONLY final Policy Engine decisions**: TRE never makes its own decisions
- ✅ **Validates before execution**: All actions are validated before execution
- ✅ **Enforces HAF requirements**: Human authority is enforced where required
- ✅ **Agents validate and execute**: Agents validate commands but never decide
- ❌ **NO decision-making**: TRE does not decide what actions to take
- ❌ **NO policy evaluation**: TRE does not evaluate policy rules
- ❌ **NO heuristics**: TRE does not use heuristics or ML

### Cryptographic Signing and Verification

**CRITICAL**: All actions are cryptographically signed:

- ✅ **ed25519 signing**: All commands are signed with ed25519 (separate from Policy Engine's HMAC)
- ✅ **Separate trust root**: TRE has its own signing keypair (separate from Policy Engine, HAF, Audit Ledger)
- ✅ **Agent verification**: Agents verify all commands before execution
- ✅ **Non-repudiation**: Signatures provide non-repudiation

### Mandatory Rollback

**CRITICAL**: Rollback is mandatory and first-class:

- ✅ **All actions rollback-capable**: All actions can be rolled back
- ✅ **First-class rollback**: Rollback is a first-class operation, not an afterthought
- ✅ **Signed rollback commands**: Rollback commands are signed with ed25519
- ✅ **Complete rollback history**: All rollbacks are recorded immutably

### Immutable and Audit-Anchored

**CRITICAL**: All records are immutable and audit-anchored:

- ✅ **Immutable records**: All action and rollback records are immutable
- ✅ **Audit ledger integration**: All actions emit audit ledger entries
- ✅ **Complete audit trail**: Complete audit trail for all actions and rollbacks
- ✅ **No placeholders**: No placeholders, no dummy data, no heuristics, no ML

## Architecture

### Components

1. **Schema** (`schema/`):
   - `response-action.schema.json`: Frozen schema for response actions
   - `rollback-record.schema.json`: Frozen schema for rollback records
   - `agent-command.schema.json`: Frozen schema for agent commands

2. **Cryptography** (`crypto/`):
   - `key_manager.py`: Keypair generation and management (ed25519)
   - `signer.py`: Command signing with ed25519
   - `verifier.py`: Command verification with ed25519

3. **Engine** (`engine/`):
   - `action_validator.py`: Validates Policy Engine decisions and HAF requirements
   - `command_dispatcher.py`: Dispatches signed commands to agents
   - `rollback_manager.py`: Manages rollback of executed actions

4. **Database** (`db/`):
   - `schema.sql`: Database schema for response actions and rollbacks
   - `operations.py`: Database operations for actions and rollbacks

5. **API** (`api/`):
   - `tre_api.py`: Public API for executing actions and rollbacks

6. **CLI** (`cli/`):
   - `execute_action.py`: CLI tool for executing Policy Engine decisions
   - `rollback_action.py`: CLI tool for rolling back executed actions

## Command Types (Frozen Enum)

Supported command types:

- **ISOLATE_HOST**: Isolate host from network
- **QUARANTINE_HOST**: Quarantine host (isolate + restrict access)
- **BLOCK_PROCESS**: Block specific process
- **BLOCK_NETWORK**: Block network connection
- **QUARANTINE_FILE**: Quarantine file (move to quarantine directory)
- **TERMINATE_PROCESS**: Terminate specific process
- **DISABLE_USER**: Disable user account
- **REVOKE_ACCESS**: Revoke user access

## Execution Flow

### 1. Policy Engine Decision

Policy Engine creates a signed command (HMAC-SHA256) and stores it. TRE consumes this decision.

### 2. Action Validation

TRE validates:
- Policy decision is valid (recommends action)
- Required authority is satisfied (if HUMAN or ROLE required)
- Command type is valid

### 3. Command Signing

TRE signs command with ed25519 (separate from Policy Engine's HMAC):
- Command payload is serialized to canonical JSON
- Signed with TRE's private key
- Signature is base64-encoded

### 4. Command Dispatch

TRE dispatches signed command to agent:
- Command is sent to agent command endpoint
- Agent validates signature before execution
- Agent executes command and reports result

### 5. Action Recording

TRE records action in database:
- Action record is created (immutable)
- Audit ledger entry is emitted
- Execution status is tracked

### 6. Rollback (if needed)

If rollback is required:
- Rollback command is created and signed
- Rollback command is dispatched to agent
- Rollback record is created (immutable)
- Audit ledger entry is emitted

## Authority Requirements

### Authority Levels

- **NONE**: No authority required (automated execution)
- **HUMAN**: Human authority required (human must approve)
- **ROLE**: Role-based authority required (specific role must approve)

### HAF Integration

TRE integrates with Human Authority Framework (HAF):
- Validates authority actions before execution
- Enforces role requirements
- Records authority action IDs

## Database Schema

### response_actions Table

Stores all response actions:
- `action_id`: UUID v4 (primary key)
- `policy_decision_id`: Policy decision identifier
- `incident_id`: Incident identifier (foreign key)
- `machine_id`: Machine identifier (foreign key)
- `command_type`: Command type (enum)
- `command_payload`: Command payload (JSONB)
- `command_signature`: ed25519 signature (base64)
- `command_signing_key_id`: TRE signing key ID
- `required_authority`: Authority level (enum)
- `authority_action_id`: HAF action ID (if required)
- `execution_status`: Execution status (enum)
- `executed_at`: Execution timestamp
- `executed_by`: Entity that executed (TRE, HUMAN)
- `rollback_capable`: Whether rollback is possible
- `rollback_id`: Rollback identifier (if rolled back)
- `ledger_entry_id`: Audit ledger entry ID

### rollback_records Table

Stores all rollback operations:
- `rollback_id`: UUID v4 (primary key)
- `action_id`: Action identifier (foreign key)
- `rollback_reason`: Reason for rollback (enum)
- `rollback_type`: Type of rollback (FULL, PARTIAL)
- `rollback_payload`: Rollback command payload (JSONB)
- `rollback_signature`: ed25519 signature (base64)
- `rollback_signing_key_id`: TRE signing key ID
- `required_authority`: Authority level (enum)
- `authority_action_id`: HAF action ID (if required)
- `rollback_status`: Rollback status (enum)
- `rolled_back_at`: Rollback timestamp
- `rolled_back_by`: Entity that executed rollback
- `ledger_entry_id`: Audit ledger entry ID

## Usage

### Execute Action

```bash
python3 threat-response-engine/cli/execute_action.py \
    --policy-decision policy_decision.json \
    --required-authority NONE \
    --key-dir /var/lib/ransomeye/tre/keys \
    --db-host localhost \
    --db-port 5432 \
    --db-name ransomeye \
    --db-user ransomeye \
    --db-password <password> \
    --agent-command-endpoint http://localhost:8001/commands \
    --ledger-path /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output result.json
```

### Rollback Action

```bash
python3 threat-response-engine/cli/rollback_action.py \
    --action-id <action-uuid> \
    --rollback-reason FALSE_POSITIVE \
    --rollback-type FULL \
    --required-authority NONE \
    --key-dir /var/lib/ransomeye/tre/keys \
    --db-host localhost \
    --db-port 5432 \
    --db-name ransomeye \
    --db-user ransomeye \
    --db-password <password> \
    --agent-command-endpoint http://localhost:8001/commands \
    --ledger-path /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output rollback_result.json
```

### Programmatic API

```python
from threat_response_engine.api.tre_api import TREAPI
from pathlib import Path

tre_api = TREAPI(
    key_dir=Path('/var/lib/ransomeye/tre/keys'),
    db_conn_params={
        'host': 'localhost',
        'port': 5432,
        'database': 'ransomeye',
        'user': 'ransomeye',
        'password': '<password>'
    },
    agent_command_endpoint='http://localhost:8001/commands',
    ledger_path=Path('/var/lib/ransomeye/audit/ledger.jsonl'),
    ledger_key_dir=Path('/var/lib/ransomeye/audit/keys')
)

# Execute action
result = tre_api.execute_action(
    policy_decision=policy_decision_dict,
    required_authority='NONE'
)

# Rollback action
rollback_result = tre_api.rollback_action(
    action_id=result['action_id'],
    rollback_reason='FALSE_POSITIVE',
    rollback_type='FULL'
)
```

## Integration with Other Systems

### Policy Engine

- **Consumes**: Policy Engine decisions (signed commands)
- **Validates**: Policy decision validity before execution
- **Does NOT**: Make policy decisions or evaluate rules

### Human Authority Framework (HAF)

- **Enforces**: Human authority requirements
- **Validates**: Authority actions before execution
- **Records**: Authority action IDs in action records

### Audit Ledger

- **Emits**: Audit ledger entries for all actions and rollbacks
- **Records**: Ledger entry IDs in action/rollback records
- **Provides**: Complete audit trail for all operations

### Agents

- **Dispatches**: Signed commands to agents
- **Agents validate**: Commands are verified before execution
- **Agents execute**: Commands are executed by agents
- **Agents report**: Execution results are reported back

## Security Considerations

1. **Separate Trust Root**: TRE has its own signing keypair (separate from Policy Engine, HAF, Audit Ledger)
2. **Command Signing**: All commands are signed with ed25519 before dispatch
3. **Agent Verification**: Agents verify all commands before execution
4. **Authority Enforcement**: Human authority is enforced where required
5. **Immutable Records**: All action and rollback records are immutable
6. **Audit Trail**: Complete audit trail for all operations

## Legal / Regulatory Positioning

The Threat Response Engine is designed for **legal and compliance** use cases:

1. **Execution Accountability**: Complete accountability for all executed actions
2. **Non-Repudiation**: Cryptographic signatures prevent denial of actions
3. **Rollback Capability**: All actions can be rolled back if false positive
4. **Audit Trail**: Complete audit trail for all actions and rollbacks
5. **Authority Chain**: Complete authority chain from Policy Engine → HAF → TRE → Agent

### Compliance Standards

The TRE supports compliance with:
- **SOC 2**: Audit trail requirements for automated actions
- **ISO 27001**: Security event logging and response
- **HIPAA**: Audit controls for security actions
- **PCI DSS**: Audit trail for security responses
- **GDPR**: Audit trail for automated decisions

## Limitations

1. **Execution-Only**: TRE does not make decisions, only executes them
2. **Policy Engine Dependency**: TRE requires Policy Engine decisions
3. **Agent Dependency**: TRE requires agents to execute commands
4. **No Retries**: TRE does not retry failed commands (fail-fast)

## Future Enhancements

- Agent command endpoint implementation
- Real-time command status tracking
- Batch command execution
- Command execution timeouts
- Command execution retries (with limits)

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye Threat Response Engine documentation.
