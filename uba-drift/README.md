# RansomEye UBA Drift (Behavioral Drift Detection Engine)

**AUTHORITATIVE:** Purely deterministic delta-analysis layer for behavioral change detection

## Overview

The RansomEye UBA Drift Engine is a **purely deterministic delta-analysis layer** on top of **UBA Core baselines**. This phase detects **behavioral change**, **not intent**, **not risk**, **not anomaly labels**. It answers only one question:

> *"Has observed behavior deviated from its own historical baseline, and how?"*

Nothing more.

## Core Principles

### Behavioral Drift ≠ Malicious Behavior

**CRITICAL**: Behavioral drift does not equal malicious behavior:

- ✅ **Change detection only**: Detects behavioral change, not intent
- ✅ **No ML**: No machine learning, statistics, or probabilistic models
- ✅ **No scoring**: No risk scores, alerts, or confidence labels
- ✅ **No judgment**: No words like suspicious, malicious, abnormal
- ✅ **Facts only**: Deltas are facts, not conclusions

### Deterministic Delta Analysis

**CRITICAL**: All delta analysis is deterministic:

- ✅ **Explicit comparison**: Explicit comparison logic only
- ✅ **No heuristics**: No heuristic logic
- ✅ **Environment-defined thresholds**: Thresholds from env vars only
- ✅ **Bit-for-bit reconstructable**: Every delta is reconstructable
- ✅ **Replayable**: Global Validator can rebuild all deltas

### UBA Core Remains Read-Only

**CRITICAL**: UBA Core is never modified:

- ✅ **Read-only access**: UBA Core stores are read-only
- ✅ **No mutations**: No updates to baselines or events
- ✅ **Separate storage**: Deltas stored separately

## Delta Types

### NEW_EVENT_TYPE

- **Description**: New event type observed that was not in baseline
- **Example**: Baseline has `login`, `file_access`; observation has `network_access`
- **Delta magnitude**: 1.0 (presence delta)

### NEW_HOST

- **Description**: New host observed that was not in baseline
- **Example**: Baseline has hosts `host1`, `host2`; observation has `host3`
- **Delta magnitude**: 1.0 (presence delta)

### NEW_TIME_BUCKET

- **Description**: New time bucket (hourly) observed that was not in baseline
- **Example**: Baseline has `2024-01-01T09:00` to `2024-01-01T17:00`; observation has `2024-01-01T22:00`
- **Delta magnitude**: 1.0 (presence delta)

### NEW_PRIVILEGE

- **Description**: New privilege observed that was not in baseline
- **Example**: Baseline has `sudo`, `docker`; observation has `root`
- **Delta magnitude**: 1.0 (presence delta)

### FREQUENCY_SHIFT

- **Description**: Frequency change in event type
- **Example**: Baseline has `login` 10 times; observation has `login` 50 times
- **Delta magnitude**: Numeric difference (count difference, NOT a score)

## What UBA Drift Does NOT Do

- ❌ **No ML inference**: No machine learning models
- ❌ **No risk scoring**: No risk or threat scoring
- ❌ **No alerts**: No alert generation
- ❌ **No anomaly detection**: No anomaly labels
- ❌ **No suspicious flags**: No implicit inference
- ❌ **No intent inference**: No intent or motivation inference
- ❌ **No enforcement**: No enforcement actions
- ❌ **No judgment**: No words like suspicious, malicious, abnormal

## Required Integrations

UBA Drift integrates with:

- **UBA Core**: Read-only access to baselines and events
- **Audit Ledger**: All actions (UBA_DELTA_COMPUTED, UBA_DELTA_EXPORTED, UBA_DELTA_SUMMARY_BUILT)
- **Global Validator**: Full replay and reconstruction

## Regulatory Posture

### How Regulators Should Read Delta Data

- **Deltas are facts**: Deltas represent observed changes, not judgments
- **No inference**: No inference or scoring is applied
- **Replayable**: All deltas can be rebuilt from raw events
- **Auditable**: Full audit trail of all delta computations

### How Later Layers MAY Consume

- **Risk Index**: May consume deltas as signals (not authoritative)
- **Incident Response**: May consume deltas as context (not authoritative)
- **Policy Engine**: May consume deltas as inputs (not authoritative)

## Usage

### Compute Deltas

```bash
export UBA_DRIFT_FREQUENCY_THRESHOLD="0.0"
export UBA_DRIFT_OBSERVATION_WINDOW_DAYS="7"

python3 uba-drift/cli/compute_deltas.py \
    --identity-id <identity-uuid> \
    --baseline-id <baseline-uuid> \
    --window-start "2024-01-01T00:00:00Z" \
    --window-end "2024-01-08T00:00:00Z" \
    --uba-identities-store /var/lib/ransomeye/uba/identities.jsonl \
    --uba-events-store /var/lib/ransomeye/uba/events.jsonl \
    --uba-baselines-store /var/lib/ransomeye/uba/baselines.jsonl \
    --deltas-store /var/lib/ransomeye/uba-drift/deltas.jsonl \
    --summaries-store /var/lib/ransomeye/uba-drift/summaries.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output deltas.json
```

### Export Deltas

```bash
python3 uba-drift/cli/export_deltas.py \
    --identity-id <identity-uuid> \
    --window-start "2024-01-01T00:00:00Z" \
    --window-end "2024-01-08T00:00:00Z" \
    --deltas-store /var/lib/ransomeye/uba-drift/deltas.jsonl \
    --summaries-store /var/lib/ransomeye/uba-drift/summaries.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output exported_deltas.json
```

### Export Delta Summary

```bash
python3 uba-drift/cli/export_delta_summary.py \
    --identity-id <identity-uuid> \
    --baseline-hash <baseline-hash> \
    --window-start "2024-01-01T00:00:00Z" \
    --window-end "2024-01-08T00:00:00Z" \
    --uba-identities-store /var/lib/ransomeye/uba/identities.jsonl \
    --uba-events-store /var/lib/ransomeye/uba/events.jsonl \
    --uba-baselines-store /var/lib/ransomeye/uba/baselines.jsonl \
    --deltas-store /var/lib/ransomeye/uba-drift/deltas.jsonl \
    --summaries-store /var/lib/ransomeye/uba-drift/summaries.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output summary.json
```

### Programmatic API

```python
from api.drift_api import DriftAPI

api = DriftAPI(
    uba_identities_store_path=Path('/var/lib/ransomeye/uba/identities.jsonl'),
    uba_events_store_path=Path('/var/lib/ransomeye/uba/events.jsonl'),
    uba_baselines_store_path=Path('/var/lib/ransomeye/uba/baselines.jsonl'),
    deltas_store_path=Path('/var/lib/ransomeye/uba-drift/deltas.jsonl'),
    summaries_store_path=Path('/var/lib/ransomeye/uba-drift/summaries.jsonl'),
    ledger_path=Path('/var/lib/ransomeye/audit/ledger.jsonl'),
    ledger_key_dir=Path('/var/lib/ransomeye/audit/keys')
)

# Compute deltas
deltas = api.compute_behavior_deltas(
    identity_id=identity_id,
    baseline_id=baseline_id,
    observation_window_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
    observation_window_end=datetime(2024, 1, 8, tzinfo=timezone.utc)
)

# Get deltas
deltas = api.get_behavior_deltas(identity_id)

# Get summary
summary = api.get_delta_summary(
    identity_id=identity_id,
    baseline_hash=baseline_hash,
    observation_window_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
    observation_window_end=datetime(2024, 1, 8, tzinfo=timezone.utc)
)
```

## File Structure

```
uba-drift/
├── schema/
│   ├── behavior-delta.schema.json        # Frozen JSON schema for deltas
│   └── delta-summary.schema.json        # Frozen JSON schema for summaries
├── engine/
│   ├── __init__.py
│   ├── delta_comparator.py             # Deterministic delta comparison
│   ├── window_builder.py               # Explicit observation window building
│   ├── delta_hasher.py                 # Deterministic delta hashing
│   └── delta_classifier.py             # Delta type classification (type only)
├── storage/
│   ├── __init__.py
│   └── delta_store.py                  # Append-only, immutable storage
├── api/
│   ├── __init__.py
│   └── drift_api.py                    # Drift API with audit integration
├── cli/
│   ├── __init__.py
│   ├── compute_deltas.py               # Compute deltas CLI
│   ├── export_deltas.py                # Export deltas CLI
│   └── export_delta_summary.py         # Export summary CLI
└── README.md                           # This file
```

## Environment Variables

- **UBA_DRIFT_FREQUENCY_THRESHOLD**: Frequency shift threshold (default: 0.0)
- **UBA_DRIFT_OBSERVATION_WINDOW_DAYS**: Observation window size in days (default: 7)

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **UBA Core**: Required for baseline and event access (read-only)
- **Audit Ledger**: Required for audit trail (separate subsystem)

## Security Considerations

1. **No Inference**: No inference logic exists
2. **Facts Only**: All outputs are facts, not conclusions
3. **Immutable Storage**: All records are immutable
4. **Deterministic**: Same inputs always produce same outputs
5. **Replayable**: All deltas can be rebuilt from events

## Limitations

1. **No ML**: No machine learning models
2. **No Scoring**: No risk or threat scoring
3. **No Alerts**: No alert generation
4. **No Inference**: No intent or motivation inference
5. **Change Detection Only**: Detects change, not intent

## Determinism Guarantees

- ✅ **Same baseline + same events → same deltas**: Deterministic delta computation
- ✅ **Same input → same output**: Deterministic processing
- ✅ **Bit-for-bit identical**: Deltas rebuild bit-for-bit identical
- ✅ **Replayable from zero**: Global Validator can rebuild all deltas

## Replay Guarantees

- ✅ **Rebuild from zero**: Global Validator can rebuild all deltas
- ✅ **Verify hashes**: Delta hashes can be verified
- ✅ **Detect alterations**: Missing or altered events can be detected
- ✅ **Confirm no inference**: Validator confirms no inference occurred

## Global Validator Compatibility

Validator MUST be able to:

- **Recompute deltas**: From raw behavior events and baselines
- **Verify hashes**: Delta hashes and summary hashes
- **Detect tampering**: Missing events, altered baselines, tampering

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye UBA Drift documentation.

**STATEMENT**: Behavioral drift ≠ malicious behavior. UBA Drift quantifies change, not intent.
