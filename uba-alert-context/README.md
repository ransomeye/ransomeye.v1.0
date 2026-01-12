# RansomEye UBA Alert Context Engine

**AUTHORITATIVE:** Human-facing contextual explanation for alerts using UBA signals

## Purpose Statement

The UBA Alert Context Engine provides **human-facing contextual explanations** for alerts using UBA (User Behavior Analytics) signals. This engine **does NOT create alerts**, **does NOT suppress alerts**, **does NOT escalate alerts**, **does NOT route alerts**, **does NOT modify alerts**, and **does NOT score risk**.

**It ONLY explains alerts to humans using UBA context.**

> **"UBA may change how an alert is explained — never whether it exists."**

## Non-Authority Declaration

This engine is **purely explanatory**. It has no authority over:

- **Alert Engine**: Remains authoritative for alert creation, routing, and lifecycle
- **UBA Signals**: Remains non-authoritative (context only)
- **System Explanation Engine (SEE)**: Remains explanation root
- **Human Authority Framework (HAF)**: Remains authority root
- **Risk Index**: Remains risk root

**Alert Context does not modify alerts. It explains alerts to humans using behavioral context.**

## Core Principles

### Deterministic Operation

- ✅ **No randomness**: Same inputs always produce same outputs
- ✅ **Order-preserving**: Consistent output ordering
- ✅ **No branching logic**: Explicit rules only
- ✅ **No ML**: No machine learning or heuristics
- ✅ **Replayable**: Validator can rebuild context from audit ledger

### Read-Only Access

- ✅ **Alert Engine**: Read-only access (via alert_id reference)
- ✅ **UBA Signal Store**: Read-only access (consumes signals only)
- ✅ **Write-only**: Writes ONLY to context_store
- ✅ **No mutation**: Never modifies alerts or UBA signals

### Factual Statements Only

- ✅ **No judgment words**: No "suspicious", "malicious", "risky"
- ✅ **No severity labels**: No severity classification
- ✅ **No probabilities**: No probabilistic statements
- ✅ **Controlled vocabulary**: Human-readable summaries use controlled vocabulary only
- ✅ **Behavioral facts**: Only factual statements about behavioral changes

## Architecture

### Data Flow

```
Alert Engine (alert_id)
    ↓
UBA Alert Context Engine
    ↓ (read-only)
UBA Signal Store (uba_signal_ids)
    ↓ (read-only)
System Explanation Engine (explanation_bundle_id)
    ↓
Alert Context Block (immutable)
    ↓
Human Analyst
```

### Integration Points

1. **Alert Engine**: Read-only reference via `alert_id`
2. **UBA Signal Store**: Read-only consumption of UBA signals
3. **System Explanation Engine (SEE)**: Mandatory explanation bundle reference
4. **Audit Ledger**: All operations emit ledger entries
5. **Global Validator**: Full replay capability

## Schema

### Alert Context Block

All fields are **mandatory** (zero optional fields):

- `alert_id` (UUID): Alert identifier (read-only reference)
- `context_block_id` (UUID): Unique identifier for context block
- `uba_signal_ids` (array of UUIDs): UBA signal identifiers consumed
- `context_types` (array of enums): Types of behavioral context present
- `human_readable_summary` (string): Controlled vocabulary summary
- `what_changed` (array of strings): Factual statements about what changed
- `what_did_not_change` (array of strings): Factual statements about what did not change
- `interpretation_guidance` (enum): Guidance for human interpretation
- `explanation_bundle_id` (UUID): SEE bundle identifier (mandatory)
- `generated_at` (RFC3339 UTC): Timestamp of generation

### Context Types

- `CONTEXTUAL_SHIFT`: Behavioral context has shifted
- `ROLE_EXPANSION`: Role or privilege scope has expanded
- `ACCESS_SURFACE_CHANGE`: Access surface has changed
- `TEMPORAL_BEHAVIOR_CHANGE`: Temporal behavior pattern has changed

### Interpretation Guidance

- `INFORMATIONAL`: Context is informational only
- `CONTEXT_ONLY`: Context provides additional context
- `REVIEW_RECOMMENDED`: Review recommended based on context

## Regulatory Positioning

### Insider Threat Compliance

- **Behavioral drift ≠ malicious intent**: Behavioral changes are context, not threat
- **No automatic escalation**: Context does not trigger automatic actions
- **Human review required**: Interpretation guidance recommends review when appropriate
- **Full audit trail**: All context generation is audit-logged

### SOX / SOC2 / ISO Compliance

- **Deterministic**: Same inputs → same outputs (auditable)
- **Immutable**: Context blocks cannot be modified after creation
- **Traceable**: Full chain from alert → UBA signal → explanation bundle
- **Validator-replayable**: All context can be rebuilt from audit ledger

## Analyst Guidance Examples

### Example 1: Role Expansion Context

**Alert**: User accessed sensitive file outside normal hours

**Context Block**:
- **Context Types**: `ROLE_EXPANSION`
- **Human Readable Summary**: "Role or privilege scope has expanded"
- **What Changed**: "Role or privilege scope expanded beyond baseline"
- **What Did Not Change**: "Baseline behavioral patterns remain unchanged"
- **Interpretation Guidance**: `REVIEW_RECOMMENDED`

**Analyst Action**: Review role expansion in context of alert. Determine if expansion is authorized or unauthorized.

### Example 2: Temporal Behavior Change Context

**Alert**: User accessed system from new geographic location

**Context Block**:
- **Context Types**: `TEMPORAL_BEHAVIOR_CHANGE`
- **Human Readable Summary**: "Temporal behavior pattern has changed"
- **What Changed**: "Temporal behavior pattern changed relative to baseline"
- **What Did Not Change**: "Baseline behavioral patterns remain unchanged"
- **Interpretation Guidance**: `CONTEXT_ONLY`

**Analyst Action**: Consider temporal behavior change when investigating alert. May indicate legitimate travel or unauthorized access.

## Failure Semantics

### UBA Signal Store Unavailable

- **Behavior**: Context build fails with explicit error
- **Impact**: Alert remains unchanged (context is optional)
- **Recovery**: Restore UBA Signal Store and rebuild context

### Explanation Bundle Missing

- **Behavior**: Context build fails (explanation bundle is mandatory)
- **Impact**: Context cannot be built without SEE reference
- **Recovery**: Ensure SEE bundle exists before building context

### Alert Does Not Exist

- **Behavior**: Context can still be built (read-only reference)
- **Impact**: Context exists independently of alert
- **Recovery**: Alert Engine remains authoritative

## Validator Replay Guarantees

The Global Validator can rebuild alert context blocks from:

1. **Audit Ledger**: All context builds are audit-logged
2. **UBA Signals**: Signals are immutable and replayable
3. **Explanation Bundles**: SEE bundles are immutable
4. **Deterministic Logic**: Same inputs → same outputs

**Validation Rules**:
- Same alert_id + same uba_signal_ids + same explanation_bundle_id → same context_block
- Context block hash can be verified
- All context blocks are replayable from audit ledger

## Explicit Non-Features

This engine **MUST NOT**:

- ❌ Change alert severity
- ❌ Suppress alerts
- ❌ Escalate alerts
- ❌ Trigger notifications
- ❌ Modify routing
- ❌ Modify alert content
- ❌ Introduce ML
- ❌ Introduce risk math
- ❌ Introduce policy logic
- ❌ Introduce human authority
- ❌ Introduce automation

## Usage

### Build Alert Context

```bash
python3 uba-alert-context/cli/build_alert_context.py \
    --alert-id <alert-uuid> \
    --uba-signal-ids <signal-uuid-1> <signal-uuid-2> \
    --explanation-bundle-id <bundle-uuid> \
    --uba-signals-store /var/lib/ransomeye/uba-signal/signals.jsonl \
    --uba-summaries-store /var/lib/ransomeye/uba-signal/summaries.jsonl \
    --store /var/lib/ransomeye/uba-alert-context/contexts.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output context-block.json
```

### Export Alert Context

```bash
python3 uba-alert-context/cli/export_alert_context.py \
    --alert-id <alert-uuid> \
    --store /var/lib/ransomeye/uba-alert-context/contexts.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output context-block.json
```

### Programmatic API

```python
from api.alert_context_api import AlertContextAPI

api = AlertContextAPI(
    store_path=Path('/var/lib/ransomeye/uba-alert-context/contexts.jsonl'),
    ledger_path=Path('/var/lib/ransomeye/audit/ledger.jsonl'),
    ledger_key_dir=Path('/var/lib/ransomeye/audit/keys'),
    uba_signals_store_path=Path('/var/lib/ransomeye/uba-signal/signals.jsonl'),
    uba_summaries_store_path=Path('/var/lib/ransomeye/uba-signal/summaries.jsonl')
)

# Build context
context_block = api.build_context(
    alert_id='alert-uuid',
    uba_signal_ids=['signal-uuid-1', 'signal-uuid-2'],
    explanation_bundle_id='bundle-uuid'
)

# Get context
context = api.get_alert_context('alert-uuid')
```

## File Structure

```
uba-alert-context/
├── schema/
│   └── alert-context.schema.json    # Frozen JSON schema
├── engine/
│   ├── __init__.py
│   ├── context_builder.py          # Deterministic context builder
│   └── context_hasher.py            # SHA256 hashing
├── storage/
│   ├── __init__.py
│   └── context_store.py             # Immutable, append-only storage
├── api/
│   ├── __init__.py
│   └── alert_context_api.py        # Alert context API
├── cli/
│   ├── __init__.py
│   ├── build_alert_context.py      # Build context CLI
│   └── export_alert_context.py     # Export context CLI
└── README.md                        # This file
```

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **Audit Ledger**: Required for audit trail (separate subsystem)
- **UBA Signal Store**: Required for UBA signal consumption (separate subsystem)
- **System Explanation Engine**: Required for explanation bundle references (separate subsystem)

## Security Considerations

1. **Read-only access**: Never modifies alerts or UBA signals
2. **Immutable storage**: Context blocks cannot be modified after creation
3. **Auditable**: All operations are audit-logged
4. **Deterministic**: Same inputs → same outputs (replayable)
5. **No authority**: Does not have authority over alerts or risk

## Final Statement

> **UBA Alert Context changes understanding, never outcomes.**

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye UBA Alert Context Engine documentation.
