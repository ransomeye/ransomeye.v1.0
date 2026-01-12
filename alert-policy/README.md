# RansomEye Alert Policy Engine - Policy Bundle Core

**AUTHORITATIVE:** Cryptographic trust, hot-reload, deterministic routing for alerts (≥10k alerts/min)

## Overview

The RansomEye Alert Policy Engine provides **cryptographic trust**, **hot-reload**, and **deterministic behavior** for routing alerts at scale (≥10,000 alerts/min). It governs how alerts are routed, escalated, suppressed, or forwarded based on policy rules.

## Core Principles

### Cryptographic Trust

**CRITICAL**: All policy bundles are cryptographically signed:

- ✅ **ed25519 signing**: All bundles signed with ed25519
- ✅ **Signature verification**: All bundles verified before loading
- ✅ **No unsigned policies**: No unsigned policy is accepted
- ✅ **Tamper detection**: Bundle tampering is detected

### Hot-Reload (Atomic)

**CRITICAL**: Bundle reload is atomic:

- ✅ **Atomic reload**: Old bundle remains active until new bundle is valid
- ✅ **No partial loading**: Bundle must be complete and valid
- ✅ **Reload failure = no change**: Failed reloads don't affect running system
- ✅ **Thread-safe**: Safe for concurrent access

### Deterministic Behavior

**CRITICAL**: All routing is deterministic:

- ✅ **Same input → same decision**: Same alert always produces same routing decision
- ✅ **Explicit rules**: All rules are explicit, no implicit defaults
- ✅ **No ambiguity**: Rules evaluated in priority order (no ties)
- ✅ **No silent fallbacks**: All fallbacks are explicit

### High-Throughput

**CRITICAL**: Engine supports high throughput:

- ✅ **≥10k alerts/min**: Supports at least 10,000 alerts per minute
- ✅ **Stateless**: Stateless per decision
- ✅ **No shared mutable state**: No shared state between decisions
- ✅ **Deterministic ordering**: Rules evaluated in deterministic order

## Policy Bundle Structure

### Bundle Fields

- **bundle_id**: Unique identifier (UUID)
- **bundle_version**: Semantic version
- **authority_scope**: Authority scope (one bundle = one scope)
- **created_at**: Creation timestamp
- **created_by**: Creator identifier
- **rules**: List of policy rules (ordered by priority)
- **bundle_signature**: Cryptographic signature
- **bundle_key_id**: Key identifier

### Policy Rule Structure

Each rule must specify:

- **rule_id**: Unique identifier (UUID)
- **match_conditions**: Explicit, typed match conditions
- **severity_thresholds**: Explicit severity thresholds
- **risk_score_thresholds**: Explicit risk score thresholds
- **allowed_actions**: Explicit list of allowed actions
- **required_authority**: Required authority level (NONE | HUMAN | ROLE)
- **explanation_template_id**: Explanation template ID (for SEE)
- **priority**: Explicit integer priority (no ties)

### Match Conditions

Match conditions are explicit and typed:

- **condition_type**: Logical operator (all, any)
- **conditions**: List of typed conditions
  - **field**: Field to match (alert_type, severity, risk_score, etc.)
  - **operator**: Comparison operator (equals, greater_than, in, etc.)
  - **value**: Value to compare

### Allowed Actions

- **route**: Route alert to destination
- **escalate**: Escalate alert
- **suppress**: Suppress alert
- **notify**: Notify human operator

## Routing Engine

### Routing Process

1. **Get current bundle**: Retrieve active policy bundle
2. **Evaluate rules**: Evaluate rules in priority order
3. **Match rule**: First matching rule is selected
4. **Build decision**: Build routing decision
5. **Emit audit entry**: Emit audit ledger entry

### Routing Decision

Each routing decision includes:

- **decision_id**: Unique identifier
- **alert_id**: Alert identifier
- **rule_id**: Matching rule identifier
- **routing_action**: Routing action
- **required_authority**: Required authority level
- **explanation_reference**: Reference to explanation (SEE)
- **decision_timestamp**: Decision timestamp
- **ledger_entry_id**: Audit ledger entry ID

## Hot-Reload

### Reload Process

1. **Load new bundle**: Load and validate new bundle
2. **Verify signature**: Verify bundle signature
3. **Validate rules**: Validate rules (no priority ties, no ambiguity)
4. **Atomic replace**: Atomically replace current bundle
5. **Emit audit entry**: Emit audit ledger entry

### Reload Guarantees

- **Atomic**: Reload is atomic (old bundle remains active until new bundle is valid)
- **No partial loading**: Bundle must be complete and valid
- **Reload failure = no change**: Failed reloads don't affect running system
- **Validator-replayable**: Reload can be replayed by Global Validator

## Required Integrations

Policy Engine integrates with:

- **Audit Ledger**: Every decision emits audit ledger entry
- **System Explanation Engine (SEE)**: Explanation template references
- **Human Authority Framework (HAF)**: Authority requirements
- **Global Validator**: Replay capability
- **Incident Response Engine**: Future handoff (NOT execution)

## Usage

### Verify Bundle

```bash
python3 alert-policy/cli/verify_bundle.py \
    --bundle /path/to/bundle.yaml \
    --public-keys-dir /var/lib/ransomeye/policy/keys
```

### Load Bundle (Hot-Reload)

```bash
python3 alert-policy/cli/load_bundle.py \
    --bundle /path/to/bundle.yaml \
    --public-keys-dir /var/lib/ransomeye/policy/keys \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output loaded_bundle.json
```

### Programmatic API

```python
from api.policy_api import PolicyAPI

api = PolicyAPI(
    public_keys_dir=Path('/var/lib/ransomeye/policy/keys'),
    ledger_path=Path('/var/lib/ransomeye/audit/ledger.jsonl'),
    ledger_key_dir=Path('/var/lib/ransomeye/audit/keys')
)

# Load bundle
bundle = api.load_bundle(Path('/path/to/bundle.yaml'))

# Route alert
alert = {
    'alert_id': 'alert-uuid',
    'alert_type': 'incident',
    'severity': 'HIGH',
    'risk_score': 75
}
decision = api.route_alert(alert)
```

## Policy Bundle Format (YAML)

```yaml
bundle_id: "bundle-uuid"
bundle_version: "1.0.0"
authority_scope: "incident"
created_at: "2025-01-10T12:00:00Z"
created_by: "analyst@example.com"
rules:
  - rule_id: "rule-uuid-1"
    match_conditions:
      condition_type: "all"
      conditions:
        - field: "severity"
          operator: "greater_than_or_equal"
          value: "HIGH"
        - field: "risk_score"
          operator: "greater_than"
          value: 70
    severity_thresholds:
      min_severity: "HIGH"
      max_severity: "CRITICAL"
    risk_score_thresholds:
      min_risk_score: 70
      max_risk_score: 100
    allowed_actions:
      - "escalate"
      - "notify"
    required_authority: "HUMAN"
    explanation_template_id: "template-uuid"
    priority: 100
```

## File Structure

```
alert-policy/
├── schema/
│   ├── policy-bundle.schema.json    # Frozen JSON schema for bundles
│   ├── policy-rule.schema.json     # Frozen JSON schema for rules
│   └── routing-decision.schema.json # Frozen JSON schema for decisions
├── crypto/
│   ├── __init__.py
│   ├── bundle_signer.py            # Bundle signing
│   └── bundle_verifier.py          # Bundle verification
├── engine/
│   ├── __init__.py
│   ├── bundle_loader.py            # Hot-reload, atomic loading
│   ├── rule_evaluator.py           # Deterministic rule evaluation
│   └── router.py                   # High-throughput routing
├── api/
│   ├── __init__.py
│   └── policy_api.py               # Policy API with audit integration
├── cli/
│   ├── __init__.py
│   ├── verify_bundle.py            # Verify bundle CLI
│   └── load_bundle.py              # Load bundle CLI
└── README.md                       # This file
```

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **cryptography**: Required for ed25519 signing (pip install cryptography)
- **PyYAML**: Required for YAML parsing (pip install pyyaml)
- **Audit Ledger**: Required for audit trail (separate subsystem)

## Security Considerations

1. **Cryptographic Trust**: All bundles are cryptographically signed
2. **No Unsigned Policies**: No unsigned policy is accepted
3. **Tamper Detection**: Bundle tampering is detected
4. **Atomic Reload**: Reload failures don't affect running system
5. **Deterministic**: Same inputs always produce same outputs

## Limitations

1. **No Alert Ingestion**: Phase F-1 provides policy core only, no alert ingestion
2. **No UI**: No user interface
3. **No Enforcement**: No enforcement actions (routing only)
4. **No ML**: No machine learning or heuristics

## Future Enhancements

- Alert ingestion (Phase F-2)
- Advanced rule conditions
- Rule templates
- Performance optimizations
- Multi-bundle support

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye Alert Policy Engine documentation.
