# RansomEye UBA Signal (Signal Interpretation Layer)

**AUTHORITATIVE:** Risk-consuming, authority-bound, explanation-anchored signal interpretation

## Overview

The RansomEye UBA Signal Interpretation Layer is a **consumer-only layer** that interprets **UBA Drift deltas** in **context**, without producing *new facts*, *new risk*, or *new authority*. This layer answers **only**:

> "How should downstream systems *understand* behavioral drift when combined with other verified facts?"

It **does not**:
- Generate risk scores
- Create alerts
- Escalate incidents
- Modify baselines
- Infer intent

## Core Principles

### Signals Describe Context, Not Danger

**CRITICAL**: Signals describe context, not danger:

- ✅ **Context-aware**: Signals combine drift deltas with context references
- ✅ **No scoring**: No risk scores, thresholds, or probabilities
- ✅ **No ML**: No machine learning or statistics
- ✅ **No autonomous decisions**: No autonomous decision-making
- ✅ **No alerts**: No alert generation or enforcement
- ✅ **Explanation-first**: Every signal references an explanation bundle (SEE)
- ✅ **Authority-bound**: Signals respect human authority (HAF)

### Consumer-Only Architecture

**CRITICAL**: This layer never becomes a source of truth:

```
UBA Core (facts)
   ↓
UBA Drift (change deltas)
   ↓
UBA Signal Interpretation  ← YOU ARE HERE
   ↓
Risk Index / Policy / IR / SEE (consumers only)
```

This layer is a **lens**, not an authority.

## Interpretation Types

### CONTEXTUAL_SHIFT

- **Description**: Behavioral change in context (new event types, frequency shifts)
- **Delta sources**: NEW_EVENT_TYPE, FREQUENCY_SHIFT
- **Downstream consumers**: risk_index, policy_engine, see

### ROLE_EXPANSION

- **Description**: Expansion of role or privileges
- **Delta sources**: NEW_PRIVILEGE
- **Downstream consumers**: risk_index, policy_engine, ir_engine, see
- **Authority required**: Yes

### ACCESS_SURFACE_CHANGE

- **Description**: Change in access surface (new hosts, new resources)
- **Delta sources**: NEW_HOST
- **Downstream consumers**: risk_index, policy_engine, alert_engine, see
- **Authority required**: Yes

### TEMPORAL_BEHAVIOR_CHANGE

- **Description**: Change in temporal behavior patterns
- **Delta sources**: NEW_TIME_BUCKET
- **Downstream consumers**: risk_index, see

## What UBA Signal Does NOT Do

- ❌ **No risk scoring**: No risk scores or threat scores
- ❌ **No alerts**: No alert generation
- ❌ **No escalation**: No automatic escalation
- ❌ **No enforcement**: No enforcement actions
- ❌ **No inference**: No intent or motivation inference
- ❌ **No ML**: No machine learning or statistics
- ❌ **No thresholds**: No implicit thresholds or tuning logic

## Required Integrations

UBA Signal integrates with:

- **UBA Drift**: Read-only access to deltas
- **KillChain & Forensics**: Context references (read-only)
- **Threat Graph**: Context references (read-only)
- **Incident Store**: Context references (read-only)
- **System Explanation Engine (SEE)**: Explanation bundle references (mandatory)
- **Human Authority Framework (HAF)**: Authority requirement flags
- **Audit Ledger**: All actions (UBA_SIGNAL_INTERPRETED, UBA_SIGNAL_EXPORTED, UBA_SIGNAL_SUMMARY_BUILT)

## SEE & HAF Integration

### SEE (System Explanation Engine)

- **Every signal must reference an explanation bundle**: Mandatory explanation_bundle_id
- **Explanation traces**: Drift → Context → Interpretation
- **No silent interpretations**: All interpretations are explainable

### HAF (Human Authority Framework)

- **Authority requirement flags**: If `authority_required = true`, downstream execution MUST require human signature
- **This layer does not invoke authority**: It only flags requirement
- **Downstream enforcement**: Downstream systems enforce authority requirements

## Regulatory Posture

### How Regulators Should Read Signal Data

- **Signals are interpretations**: Signals represent contextual interpretations, not judgments
- **No inference**: No inference or scoring is applied
- **Replayable**: All signals can be rebuilt from deltas and context
- **Auditable**: Full audit trail of all signal interpretations

### Explicit Separation

- **From UBA Drift**: Signals interpret deltas, but do not modify them
- **From Risk Index**: Signals inform risk, but do not produce risk
- **From Policy Engine**: Signals inform policy, but do not enforce policy

## Usage

### Interpret Signals

```bash
export UBA_SIGNAL_MIN_DELTAS="1"

python3 uba-signal/cli/interpret_signals.py \
    --identity-id <identity-uuid> \
    --delta-ids <delta-uuid-1> <delta-uuid-2> \
    --explanation-bundle-id <explanation-bundle-uuid> \
    --killchain-ids <killchain-uuid-1> \
    --graph-ids <graph-uuid-1> \
    --incident-ids <incident-uuid-1> \
    --drift-deltas-store /var/lib/ransomeye/uba-drift/deltas.jsonl \
    --drift-summaries-store /var/lib/ransomeye/uba-drift/summaries.jsonl \
    --signals-store /var/lib/ransomeye/uba-signal/signals.jsonl \
    --summaries-store /var/lib/ransomeye/uba-signal/summaries.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output signals.json
```

### Export Signals

```bash
python3 uba-signal/cli/export_signals.py \
    --identity-id <identity-uuid> \
    --window-start "2024-01-01T00:00:00Z" \
    --window-end "2024-01-08T00:00:00Z" \
    --drift-deltas-store /var/lib/ransomeye/uba-drift/deltas.jsonl \
    --drift-summaries-store /var/lib/ransomeye/uba-drift/summaries.jsonl \
    --signals-store /var/lib/ransomeye/uba-signal/signals.jsonl \
    --summaries-store /var/lib/ransomeye/uba-signal/summaries.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output exported_signals.json
```

### Export Signal Summary

```bash
python3 uba-signal/cli/export_signal_summary.py \
    --identity-id <identity-uuid> \
    --window-start "2024-01-01T00:00:00Z" \
    --window-end "2024-01-08T00:00:00Z" \
    --drift-deltas-store /var/lib/ransomeye/uba-drift/deltas.jsonl \
    --drift-summaries-store /var/lib/ransomeye/uba-drift/summaries.jsonl \
    --signals-store /var/lib/ransomeye/uba-signal/signals.jsonl \
    --summaries-store /var/lib/ransomeye/uba-signal/summaries.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output summary.json
```

### Programmatic API

```python
from api.signal_api import SignalAPI

api = SignalAPI(
    drift_deltas_store_path=Path('/var/lib/ransomeye/uba-drift/deltas.jsonl'),
    drift_summaries_store_path=Path('/var/lib/ransomeye/uba-drift/summaries.jsonl'),
    signals_store_path=Path('/var/lib/ransomeye/uba-signal/signals.jsonl'),
    summaries_store_path=Path('/var/lib/ransomeye/uba-signal/summaries.jsonl'),
    ledger_path=Path('/var/lib/ransomeye/audit/ledger.jsonl'),
    ledger_key_dir=Path('/var/lib/ransomeye/audit/keys')
)

# Interpret deltas
signals = api.interpret_deltas(
    identity_id=identity_id,
    delta_ids=[delta_id1, delta_id2],
    contextual_inputs={
        'killchain_ids': [killchain_id],
        'graph_ids': [graph_id],
        'incident_ids': [incident_id]
    },
    explanation_bundle_id=explanation_bundle_id
)

# Get signals
signals = api.get_signals(identity_id)

# Get summary
summary = api.get_signal_summary(
    identity_id=identity_id,
    observation_window_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
    observation_window_end=datetime(2024, 1, 8, tzinfo=timezone.utc)
)
```

## File Structure

```
uba-signal/
├── schema/
│   ├── interpreted-signal.schema.json    # Frozen JSON schema for signals
│   └── signal-summary.schema.json         # Frozen JSON schema for summaries
├── engine/
│   ├── __init__.py
│   ├── signal_interpreter.py            # Signal interpretation (explicit mappings)
│   ├── context_resolver.py              # Context resolution (read-only)
│   └── signal_hasher.py                 # Deterministic signal hashing
├── storage/
│   ├── __init__.py
│   └── signal_store.py                  # Append-only, immutable storage
├── api/
│   ├── __init__.py
│   └── signal_api.py                    # Signal API with audit integration
├── cli/
│   ├── __init__.py
│   ├── interpret_signals.py             # Interpret signals CLI
│   ├── export_signals.py                # Export signals CLI
│   └── export_signal_summary.py         # Export summary CLI
└── README.md                            # This file
```

## Environment Variables

- **UBA_SIGNAL_MIN_DELTAS**: Minimum deltas required for signal interpretation (default: 1)

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **UBA Drift**: Required for delta access (read-only)
- **Audit Ledger**: Required for audit trail (separate subsystem)
- **SEE**: Required for explanation bundle references (separate subsystem)
- **HAF**: Required for authority requirement flags (separate subsystem)

## Security Considerations

1. **No Inference**: No inference logic exists
2. **Context Only**: All outputs are contextual interpretations, not conclusions
3. **Immutable Storage**: All records are immutable
4. **Deterministic**: Same inputs always produce same outputs
5. **Replayable**: All signals can be rebuilt from deltas and context

## Limitations

1. **No Scoring**: No risk or threat scoring
2. **No Alerts**: No alert generation
3. **No Inference**: No intent or motivation inference
4. **No Enforcement**: No enforcement actions
5. **Consumer Only**: Never becomes a source of truth

## Determinism Guarantees

- ✅ **Same deltas + same context → same signals**: Deterministic signal interpretation
- ✅ **Same input → same output**: Deterministic processing
- ✅ **Bit-for-bit identical**: Signals rebuild bit-for-bit identical
- ✅ **Replayable from zero**: Global Validator can rebuild all signals

## Replay Guarantees

- ✅ **Rebuild from zero**: Global Validator can rebuild all signals
- ✅ **Verify hashes**: Signal hashes can be verified
- ✅ **Detect alterations**: Missing or altered deltas can be detected
- ✅ **Confirm no inference**: Validator confirms no inference occurred

## Global Validator Compatibility

Validator MUST be able to:

- **Rebuild signals**: From drift deltas and context references
- **Verify hashes**: Signal hashes and summary hashes
- **Detect tampering**: Missing deltas, altered interpretation logic, unauthorized execution attempts

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye UBA Signal documentation.

**STATEMENT**: Signals describe context, not danger. UBA Signal interprets drift in context, but never produces risk or authority.
