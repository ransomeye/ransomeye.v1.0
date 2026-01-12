# RansomEye Notification & Delivery Engine

**AUTHORITATIVE:** Strictly downstream, non-authoritative delivery layer for immutable alert facts

## Overview

The RansomEye Notification & Delivery Engine delivers **immutable alert facts** to external systems (email, webhook, ticketing, SIEM). It is **strictly downstream** and **non-authoritative** - it consumes alerts and does nothing else. Delivery is **transport**, not logic.

## Core Principles

### Strictly Downstream, Non-Authoritative

**CRITICAL**: Notification Engine is downstream only:

- ✅ **No alert creation**: Does not create alerts
- ✅ **No alert mutation**: Never changes alerts
- ✅ **No policy evaluation**: Does not evaluate policies
- ✅ **No escalation logic**: Does not escalate
- ✅ **No retries with hidden state**: No implicit retries
- ✅ **No UI coupling**: No UI integration
- ✅ **No delivery without alert fact**: Every delivery requires alert fact

### Delivery is Transport, Not Logic

**CRITICAL**: Delivery is pure transport:

- ✅ **Best-effort**: Delivery is best-effort, not guaranteed
- ✅ **Failure recorded**: Failure is recorded, not retried implicitly
- ✅ **Replays explicit**: Replays are explicit (CLI-driven)
- ✅ **Deterministic formatting**: Payload formatting is deterministic
- ✅ **Same payload hash**: Same alert + same target → same payload hash

### Deterministic and Idempotent

**CRITICAL**: All deliveries are deterministic and idempotent:

- ✅ **Deterministic**: Same inputs always produce same delivery attempt
- ✅ **Idempotent**: Replaying same delivery produces same result
- ✅ **Replayable**: Deliveries can be replayed from ledger
- ✅ **Auditable**: All deliveries are auditable

## Delivery Fact Structure

### Required Fields

Each delivery record MUST include:

- **delivery_id**: Unique identifier (UUID)
- **alert_id**: Alert identifier being delivered
- **target_id**: Delivery target identifier
- **delivery_type**: Type of delivery (email, webhook, ticket, siem)
- **payload_hash**: SHA256 hash of delivery payload (deterministic)
- **explanation_bundle_id**: Explanation bundle identifier (SEE) - mandatory
- **authority_state**: Authority state (NONE | REQUIRED | VERIFIED)
- **delivered_at**: Delivery timestamp (RFC3339 UTC)
- **status**: Delivery status (DELIVERED | FAILED)
- **immutable_hash**: SHA256 hash of delivery record
- **ledger_entry_id**: Audit ledger entry ID

### Immutability Guarantee

- **immutable_hash**: SHA256 hash of delivery record ensures immutability
- **payload_hash**: SHA256 hash of payload ensures deterministic formatting
- **No mutable state**: Delivery records cannot be modified after creation

## Delivery Types

### Email Delivery

- **Format**: Structured email with alert details
- **Target config**: Email address
- **Payload**: Email subject and body with alert information

### Webhook Delivery

- **Format**: HTTP POST with JSON payload
- **Target config**: Webhook URL
- **Payload**: JSON payload with alert information

### Ticket Delivery

- **Format**: Ticket creation via API
- **Target config**: Ticket system configuration
- **Payload**: Ticket title and description with alert information

### SIEM Delivery

- **Format**: SIEM event format (Syslog, CEF, JSON)
- **Target config**: SIEM system configuration
- **Payload**: SIEM event with alert information

## Delivery Process

### Delivery Flow

1. **Resolve targets**: Resolve delivery targets based on routing decision
2. **Format payload**: Format payload for each target (deterministic)
3. **Calculate payload hash**: Calculate hash of payload
4. **Dispatch delivery**: Dispatch to appropriate adapter (best-effort)
5. **Record delivery**: Store delivery record (immutable)
6. **Emit audit entry**: Emit audit ledger entry

### Failure Handling

- **Best-effort**: Delivery is best-effort, not guaranteed
- **Failure recorded**: Failed deliveries are recorded with status=FAILED
- **No implicit retries**: No automatic retries (replays are explicit)
- **Explicit replays**: Replays are explicit (CLI-driven)

## Required Integrations

Notification Engine integrates with:

- **Alert Engine**: Alert facts only (read-only)
- **System Explanation Engine (SEE)**: Explanation bundle references
- **Human Authority Framework (HAF)**: Authority state
- **Audit Ledger**: Every delivery attempt
- **Global Validator**: Replayability

## Usage

### Replay Delivery

```bash
python3 notification-engine/cli/replay_delivery.py \
    --alert /path/to/alert.json \
    --routing-decision /path/to/routing_decision.json \
    --explanation-bundle-id <bundle-uuid> \
    --authority-state VERIFIED \
    --targets-store /var/lib/ransomeye/notifications/targets.jsonl \
    --deliveries-store /var/lib/ransomeye/notifications/deliveries.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output deliveries.json
```

### Programmatic API

```python
from api.notification_api import NotificationAPI

api = NotificationAPI(
    targets_store_path=Path('/var/lib/ransomeye/notifications/targets.jsonl'),
    deliveries_store_path=Path('/var/lib/ransomeye/notifications/deliveries.jsonl'),
    ledger_path=Path('/var/lib/ransomeye/audit/ledger.jsonl'),
    ledger_key_dir=Path('/var/lib/ransomeye/audit/keys')
)

# Deliver alert
delivery_records = api.deliver_alert(
    alert=alert_dict,
    routing_decision=routing_decision_dict,
    explanation_bundle_id='bundle-uuid',
    authority_state='VERIFIED'
)
```

## File Structure

```
notification-engine/
├── schema/
│   ├── delivery-target.schema.json    # Frozen JSON schema for targets
│   └── delivery-record.schema.json    # Frozen JSON schema for deliveries
├── engine/
│   ├── __init__.py
│   ├── dispatcher.py                  # Delivery dispatching
│   ├── target_resolver.py             # Target resolution
│   └── formatter.py                   # Deterministic payload formatting
├── adapters/
│   ├── __init__.py
│   ├── email_adapter.py               # Email delivery adapter
│   ├── webhook_adapter.py            # Webhook delivery adapter
│   ├── ticket_adapter.py              # Ticket delivery adapter
│   └── siem_adapter.py                # SIEM delivery adapter
├── api/
│   ├── __init__.py
│   └── notification_api.py           # Notification API with audit integration
├── cli/
│   ├── __init__.py
│   └── replay_delivery.py            # Replay delivery CLI
└── README.md                          # This file
```

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **Audit Ledger**: Required for audit trail (separate subsystem)

## Security Considerations

1. **No Alert Mutation**: Alerts are never modified
2. **No Decision Logic**: No policy evaluation or escalation logic
3. **Deterministic**: Same inputs always produce same outputs
4. **Auditable**: All deliveries are logged to audit ledger
5. **Replayable**: Deliveries can be replayed from ledger

## Limitations

1. **No Alert Creation**: Does not create alerts
2. **No Policy Evaluation**: Does not evaluate policies
3. **No Escalation Logic**: Does not escalate
4. **No Implicit Retries**: No automatic retries
5. **Best-Effort**: Delivery is best-effort, not guaranteed

## Future Enhancements

- Advanced delivery adapters (SMS, Slack, etc.)
- Delivery batching
- Delivery prioritization
- Delivery scheduling
- Delivery status tracking

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye Notification & Delivery Engine documentation.
