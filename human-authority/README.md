# RansomEye Human Authority & Override Framework (HAF)

**AUTHORITATIVE:** Cryptographic proof of human decisions with explicit override semantics and role-based authority validation

## Overview

The RansomEye Human Authority & Override Framework (HAF) provides **cryptographic proof of human decisions** with **explicit override semantics**, **role-based authority validation**, **non-repudiation**, and **audit-ledger anchoring**. It ensures that every human action is signed, validated, and recorded.

## Core Principles

### Cryptographic Proof

**CRITICAL**: Every human action has cryptographic proof:

- ✅ **Per-human keypairs**: Each human has their own ed25519 keypair
- ✅ **Separate trust root**: Keys are separate from other subsystems
- ✅ **No shared keys**: No keys shared between humans or subsystems
- ✅ **Non-repudiation**: Signatures provide non-repudiation

### Explicit Override Semantics

**CRITICAL**: All overrides are explicit:

- ✅ **Never implicit**: No implicit overrides
- ✅ **Supersedes, never erases**: Overrides supersede automated decisions, never erase them
- ✅ **Structured reasons**: Reasons are structured, not free-text
- ✅ **Complete audit trail**: Complete audit trail of all overrides

### Role-Based Authority Validation

**CRITICAL**: Authority is validated before acceptance:

- ✅ **Role assertions**: All actions require valid role assertions
- ✅ **Role requirements**: Each action type has explicit role requirements
- ✅ **Scope validation**: Scope must match role assertion scope
- ✅ **No anonymous actions**: No actions without identified humans

### Audit-Ledger Anchoring

**CRITICAL**: All actions are anchored in audit ledger:

- ✅ **Every action logged**: Every human action emits audit ledger entry
- ✅ **Replayable**: Actions can be replayed from ledger
- ✅ **Validator-verifiable**: Validators can verify authority chain end-to-end
- ✅ **Complete accountability**: Complete accountability for all actions

## Action Types (Frozen Enum)

Supported action types:

- **POLICY_OVERRIDE**: Override policy decision
- **INCIDENT_ESCALATION**: Escalate incident
- **INCIDENT_SUPPRESSION**: Suppress incident
- **PLAYBOOK_APPROVAL**: Approve playbook execution
- **PLAYBOOK_ABORT**: Abort playbook execution
- **RISK_ACCEPTANCE**: Accept risk
- **FALSE_POSITIVE_DECLARATION**: Declare false positive

## Role Requirements

Each action type has explicit role requirements:

- **POLICY_OVERRIDE**: policy_admin, security_manager, executive
- **INCIDENT_ESCALATION**: analyst, senior_analyst, incident_responder, security_manager, executive
- **INCIDENT_SUPPRESSION**: senior_analyst, incident_responder, security_manager, executive
- **PLAYBOOK_APPROVAL**: incident_responder, security_manager, executive
- **PLAYBOOK_ABORT**: incident_responder, security_manager, executive
- **RISK_ACCEPTANCE**: security_manager, executive
- **FALSE_POSITIVE_DECLARATION**: analyst, senior_analyst, incident_responder

## Role Assertions

### Role Types

- **analyst**: Basic analyst role
- **senior_analyst**: Senior analyst role
- **incident_responder**: Incident response role
- **security_manager**: Security management role
- **policy_admin**: Policy administration role
- **executive**: Executive role
- **auditor**: Audit role

### Scope Types

- **incident**: Incident scope
- **policy**: Policy scope
- **campaign**: Campaign scope
- **risk**: Risk scope
- **playbook**: Playbook scope
- **global**: Global scope

## Authority Validation

### Validation Process

Every action is validated:

1. **Role assertion validation**: Verify role assertion signature and validity period
2. **Role sufficiency**: Verify role is sufficient for action type
3. **Signature validation**: Verify action signature with human's public key
4. **Scope validation**: Verify scope matches role assertion scope
5. **Timestamp validation**: Verify timestamp is valid (not in future)

### Validation Failures

Action is invalid if:

- **Role insufficient**: Role is not sufficient for action type
- **Signature invalid**: Signature does not verify
- **Scope mismatch**: Scope does not match role assertion scope
- **Timestamp invalid**: Timestamp is invalid or in future
- **Assertion invalid**: Role assertion is invalid or expired

## Cryptographic Model

### Keypair Generation

- **Algorithm**: ed25519 (chosen for efficiency and security)
- **Per-human**: Each human has their own keypair
- **Key ID**: SHA256 hash of public key (deterministic)
- **Storage**: Keys stored in separate directory with restricted permissions

### Signing Process

1. **Create action**: Create action dictionary (without signature)
2. **Serialize**: Serialize to canonical JSON
3. **Sign**: Sign with ed25519 private key
4. **Encode**: Encode signature as base64
5. **Attach**: Attach signature and key ID to action

### Verification Process

1. **Extract signature**: Extract signature from action
2. **Get public key**: Get human's public key by identifier
3. **Verify key ID**: Verify key ID matches
4. **Serialize**: Serialize action to canonical JSON
5. **Verify**: Verify signature with public key

## Override Processing

### Override Properties

- **Explicit**: All overrides are explicit, never implicit
- **Supersedes**: Overrides supersede automated decisions, never erase them
- **Immutable**: Overrides cannot be modified after creation
- **Deterministic**: Same inputs always produce same override

### Override History

Override history tracks:

- **All overrides**: All overrides for a subject
- **Ordered by timestamp**: Overrides ordered by timestamp
- **Active override**: Most recent override that supersedes automated decision

## Usage

### Sign Override

```bash
python3 human-authority/cli/sign_override.py \
    --action-type POLICY_OVERRIDE \
    --human-identifier analyst@example.com \
    --role-assertion-id <assertion-uuid> \
    --scope policy \
    --subject-id <policy-id> \
    --subject-type policy \
    --reason "Business justification: policy conflicts with operational requirements" \
    --supersedes-automated \
    --keys-dir /var/lib/ransomeye/authority/keys \
    --role-assertions /var/lib/ransomeye/authority/assertions.jsonl \
    --actions-store /var/lib/ransomeye/authority/actions.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output override.json
```

### Verify Override

```bash
python3 human-authority/cli/verify_override.py \
    --action override.json \
    --keys-dir /var/lib/ransomeye/authority/keys \
    --role-assertions /var/lib/ransomeye/authority/assertions.jsonl \
    --actions-store /var/lib/ransomeye/authority/actions.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys
```

### Programmatic API

```python
from api.authority_api import AuthorityAPI

api = AuthorityAPI(
    keys_dir=Path('/var/lib/ransomeye/authority/keys'),
    role_assertions_path=Path('/var/lib/ransomeye/authority/assertions.jsonl'),
    actions_store_path=Path('/var/lib/ransomeye/authority/actions.jsonl'),
    ledger_path=Path('/var/lib/ransomeye/audit/ledger.jsonl'),
    ledger_key_dir=Path('/var/lib/ransomeye/audit/keys')
)

# Create override
action = api.create_override(
    action_type='POLICY_OVERRIDE',
    human_identifier='analyst@example.com',
    role_assertion_id='assertion-uuid',
    scope='policy',
    subject_id='policy-uuid',
    subject_type='policy',
    reason='Business justification: policy conflicts with operational requirements',
    supersedes_automated_decision=True
)

# Verify action
is_valid = api.verify_action(action)
```

## File Structure

```
human-authority/
├── schema/
│   ├── authority-action.schema.json    # Frozen JSON schema for actions
│   └── role-assertion.schema.json      # Frozen JSON schema for role assertions
├── crypto/
│   ├── __init__.py
│   ├── human_key_manager.py            # Per-human keypair management
│   ├── signer.py                        # Action signing
│   └── verifier.py                     # Action verification
├── engine/
│   ├── __init__.py
│   ├── authority_validator.py           # Authority validation
│   └── override_processor.py           # Override processing
├── api/
│   ├── __init__.py
│   └── authority_api.py                 # Authority API with audit integration
├── cli/
│   ├── __init__.py
│   ├── sign_override.py                 # Sign override CLI
│   └── verify_override.py               # Verify override CLI
└── README.md                            # This file
```

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **cryptography**: Required for ed25519 signing (pip install cryptography)
- **Audit Ledger**: Required for audit trail (separate subsystem)

## Security Considerations

1. **Per-Human Keypairs**: Each human has their own keypair (no shared keys)
2. **Separate Trust Root**: Keys are separate from other subsystems
3. **Non-Repudiation**: Signatures provide non-repudiation
4. **Role Validation**: All actions require valid role assertions
5. **No Anonymous Actions**: No actions without identified humans
6. **No Revocation Ambiguity**: Clear revocation semantics

## Limitations

1. **No UI**: Phase C4 provides computation only, no UI
2. **No Workflow Engine**: No workflow engine integration
3. **No Assumptions**: No assumptions about humans
4. **No Free-Text**: Reasons are structured, not free-text

## Future Enhancements

- Role assertion issuance workflow
- Revocation management
- Multi-signature support
- Time-based authority delegation
- Authority delegation chains

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye Human Authority & Override Framework documentation.
