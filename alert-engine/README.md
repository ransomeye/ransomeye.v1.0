# RansomEye Alert Engine (Execution-Free Decision Engine)

**AUTHORITATIVE:** Immutable alert facts from incidents and policy routing decisions

## Overview

The RansomEye Alert Engine converts **incidents + policy routing decisions** into **alerts as immutable facts**. It enforces **cardinality, deduplication, suppression, and escalation** while producing **alert facts only** (no notifications, no enforcement, no execution).

## Core Principles

### Alerts are Facts, Not Messages

**CRITICAL**: Alerts are immutable facts:

- ✅ **Immutable**: Alerts cannot be modified after creation
- ✅ **Chainable**: Alerts are chainable per incident (prev_alert_hash)
- ✅ **Explainable**: All alerts have explanation bundle references
- ✅ **Deterministic**: Same inputs always produce same alert

### Execution-Free

**CRITICAL**: Alert Engine does not execute:

- ✅ **No notifications**: Does not send notifications
- ✅ **No UI**: No user interface
- ✅ **No enforcement**: Does not execute enforcement actions
- ✅ **No retries**: No retry logic
- ✅ **No background schedulers**: No background processing

### Deterministic Behavior

**CRITICAL**: All operations are deterministic:

- ✅ **Same input → same output**: Same incident + same policy = same alert
- ✅ **Content-based deduplication**: Deduplication based on content, not time
- ✅ **Explicit suppression**: All suppressions are explicit, never implicit
- ✅ **Deterministic escalation**: Escalation is deterministic

## Alert Fact Structure

### Required Fields

Each alert MUST include:

- **alert_id**: Unique identifier (UUID)
- **incident_id**: Incident identifier
- **policy_rule_id**: Policy rule identifier
- **severity**: Alert severity (LOW, MODERATE, HIGH, CRITICAL)
- **risk_score_at_emit**: Risk score at time of emission
- **explanation_bundle_id**: Explanation bundle identifier (SEE) - mandatory
- **authority_required**: Required authority level (NONE | HUMAN | ROLE)
- **routing_decision_id**: Routing decision identifier
- **emitted_at**: Emission timestamp (RFC3339 UTC)
- **immutable_hash**: SHA256 hash of alert content
- **prev_alert_hash**: Hash of previous alert for same incident (chainable)

### Immutability Guarantee

- **immutable_hash**: SHA256 hash of alert content ensures immutability
- **prev_alert_hash**: Links alerts for same incident in chain
- **No mutable state**: Alerts cannot be modified after creation

## Deduplication

### Content-Based Deduplication

Deduplication is **content-based**, not time-based:

- **Same content = duplicate**: Identical alert facts = single alert
- **Deterministic**: Same alerts always produce same deduplication result
- **Content hash**: Deduplication based on incident_id + policy_rule_id + severity + risk_score

### Deduplication Process

1. **Calculate content hash**: Hash of deduplication fields
2. **Check if seen**: Check if content hash has been seen
3. **Mark as seen**: Mark content hash as seen
4. **Emit audit entry**: Emit audit ledger entry for duplicate detection

## Suppression

### Suppression Rules

Suppression must be:

- ✅ **Explicit**: All suppressions are explicit, never implicit
- ✅ **Policy-driven**: Suppressions are driven by policy rules
- ✅ **Reason-coded**: Suppression reasons are coded (no free-text)
- ✅ **Replayable**: Suppressions can be replayed

### Suppression Reasons

Supported suppression reasons:

- **false_positive**: Alert is false positive
- **duplicate**: Alert is duplicate
- **policy_suppression**: Suppressed by policy rule
- **human_override**: Suppressed by human override
- **risk_acceptance**: Risk accepted

### Suppression Process

1. **Check routing decision**: Check if routing action is suppress
2. **Create suppression**: Create suppression record
3. **Store suppression**: Store suppression to file
4. **Store alert**: Store alert with suppression marker (still recorded as fact)
5. **Emit audit entry**: Emit audit ledger entry

## Escalation

### Escalation Rules

Escalation is deterministic and requires:

- ✅ **Policy match**: Escalation requires policy rule match
- ✅ **Explanation reference**: Escalation requires explanation bundle reference
- ✅ **No auto-execution**: Escalation NEVER auto-executes IR
- ✅ **Authority requirement**: Escalation MAY require HAF authority

### Escalation Process

1. **Check routing decision**: Check if routing action is escalate
2. **Create escalation**: Create escalation record
3. **Store escalation**: Store escalation to file
4. **Emit audit entry**: Emit audit ledger entry

## Required Integrations

Alert Engine integrates with:

- **Alert Policy Engine**: Routing decisions
- **System Explanation Engine (SEE)**: Explanation bundle references
- **Audit Ledger**: Every alert, suppression, escalation
- **Human Authority Framework (HAF)**: Authority requirements
- **Global Validator**: Replay capability

## Usage

### Emit Alert

```bash
python3 alert-engine/cli/replay_alerts.py \
    --incident /path/to/incident.json \
    --routing-decision /path/to/routing_decision.json \
    --explanation-bundle-id <bundle-uuid> \
    --risk-score 75.5 \
    --alerts-store /var/lib/ransomeye/alerts/alerts.jsonl \
    --suppressions-store /var/lib/ransomeye/alerts/suppressions.jsonl \
    --escalations-store /var/lib/ransomeye/alerts/escalations.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output alert.json
```

### Programmatic API

```python
from api.alert_api import AlertAPI

api = AlertAPI(
    alerts_store_path=Path('/var/lib/ransomeye/alerts/alerts.jsonl'),
    suppressions_store_path=Path('/var/lib/ransomeye/alerts/suppressions.jsonl'),
    escalations_store_path=Path('/var/lib/ransomeye/alerts/escalations.jsonl'),
    ledger_path=Path('/var/lib/ransomeye/audit/ledger.jsonl'),
    ledger_key_dir=Path('/var/lib/ransomeye/audit/keys')
)

# Emit alert
alert = api.emit_alert(
    incident=incident_dict,
    routing_decision=routing_decision_dict,
    explanation_bundle_id='bundle-uuid',
    risk_score=75.5
)
```

## File Structure

```
alert-engine/
├── schema/
│   ├── alert.schema.json              # Frozen JSON schema for alerts
│   ├── alert-suppression.schema.json  # Frozen JSON schema for suppressions
│   └── alert-escalation.schema.json  # Frozen JSON schema for escalations
├── engine/
│   ├── __init__.py
│   ├── alert_builder.py               # Alert building
│   ├── deduplicator.py                # Content-based deduplication
│   ├── suppressor.py                  # Explicit suppression
│   └── escalator.py                   # Deterministic escalation
├── api/
│   ├── __init__.py
│   └── alert_api.py                   # Alert API with audit integration
├── cli/
│   ├── __init__.py
│   └── replay_alerts.py               # Replay alerts CLI
└── README.md                          # This file
```

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **Audit Ledger**: Required for audit trail (separate subsystem)

## Security Considerations

1. **Immutable Alerts**: Alerts cannot be modified after creation
2. **No Mutable State**: No mutable alert state
3. **Explicit Suppression**: All suppressions are explicit
4. **Deterministic**: Same inputs always produce same outputs
5. **Validator-Reconstructable**: Alerts can be rebuilt from ledger

## Limitations

1. **No Notifications**: Phase F-2 provides alert facts only, no notifications
2. **No UI**: No user interface
3. **No Enforcement**: No enforcement actions
4. **No Retries**: No retry logic
5. **No Background Schedulers**: No background processing

## Future Enhancements

- Alert notification (Phase F-3)
- Alert delivery channels
- Alert aggregation
- Alert correlation
- Alert prioritization

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye Alert Engine documentation.
