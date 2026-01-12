# RansomEye UBA Core (Identity–Behavior Ground Truth Layer)

**AUTHORITATIVE:** Purely factual, evidence-grade user behavior analytics foundation

## Overview

The RansomEye UBA Core establishes **per-identity behavioral ground truth** without scoring, prediction, ML black boxes, or enforcement. This phase is the **foundation** for insider threat detection and must be **deterministic, replayable, and regulator-safe**. UBA Core establishes facts, not intent.

## Core Principles

### Facts Only, Not Intent

**CRITICAL**: UBA Core establishes facts, not intent:

- ✅ **No ML models**: This phase is ground truth only, not inference
- ✅ **No scoring**: No scoring, alerts, risk, or conclusions
- ✅ **No heuristics**: No heuristic logic
- ✅ **No optional fields**: Zero ambiguity in schemas
- ✅ **No background schedulers**: Explicit ingestion only
- ✅ **Facts only**: Baselines are facts, not conclusions

### Environment-Driven Configuration

**CRITICAL**: No hardcoded values:

- ✅ **No hardcoded IPs**: All IPs from environment or manifests
- ✅ **No hardcoded paths**: All paths from environment
- ✅ **No hardcoded users**: All users from environment
- ✅ **No hardcoded domains**: All domains from environment
- ✅ **No hardcoded interfaces**: All interfaces from environment

### Deterministic and Replayable

**CRITICAL**: All operations are deterministic and replayable:

- ✅ **Same input → same output**: Deterministic processing
- ✅ **Replayable from zero**: Global Validator can rebuild all baselines
- ✅ **Bit-for-bit identical**: Baselines rebuild bit-for-bit identical
- ✅ **Full audit chain**: Audit Ledger contains full chain

## Threat Model

### What UBA Core Does

- **Establishes identity ground truth**: Canonical identity resolution
- **Normalizes behavior events**: Canonical event normalization
- **Builds historical baselines**: Immutable baseline aggregation
- **Provides replay capability**: Full reconstruction from events

### What UBA Core Does NOT Do

- ❌ **No ML inference**: No machine learning models
- ❌ **No risk scoring**: No risk or threat scoring
- ❌ **No alerts**: No alert generation
- ❌ **No anomaly detection**: No anomaly labels
- ❌ **No suspicious flags**: No implicit inference
- ❌ **No intent inference**: No intent or motivation inference
- ❌ **No enforcement**: No enforcement actions

## Identity Resolution

### Identity Types

- **human**: Human user identity
- **service**: Service account identity
- **machine**: Machine identity

### Resolution Rules

- **Deterministic**: Same input = same identity
- **Explicit precedence**: Explicit precedence rules only
- **No heuristics**: No heuristic logic
- **Canonical hash**: Deterministic canonical identity hash

## Behavior Events

### Event Types

- **login**: Login event
- **file_access**: File access event
- **process_start**: Process start event
- **network_access**: Network access event
- **privilege_use**: Privilege use event
- **policy_override**: Policy override event

### Source Components

- **linux-agent**: Linux Agent
- **windows-agent**: Windows Agent
- **dpi**: DPI Probe
- **hnmp**: HNMP Engine
- **ir**: Incident Response Engine
- **deception**: Deception Framework

## Identity Baselines

### Baseline Content

- **Observed event types**: Event types observed in baseline window
- **Observed hosts**: Host identifiers observed
- **Observed time buckets**: Hourly time buckets observed
- **Observed privileges**: Privilege identifiers observed

### Baseline Properties

- **Immutable**: Baselines are immutable
- **Versioned**: Baselines are versioned by time window
- **Deterministic**: Same events = same baseline
- **Hashable**: Baselines have deterministic hashes for drift comparison

## Required Integrations

UBA Core integrates with:

- **Audit Ledger**: All actions (UBA_IDENTITY_CREATED, UBA_BEHAVIOR_INGESTED, UBA_BASELINE_BUILT, UBA_BASELINE_EXPORTED)
- **Global Validator**: Full replay and reconstruction
- **HNMP Engine**: Behavior event input
- **Linux/Windows Agents**: Behavior event input
- **DPI Probe**: Behavior event input

## Regulatory Posture

UBA Core is designed for:

- **SOX compliance**: Full audit trail, immutable records
- **SOC2 compliance**: Access controls, audit logging
- **ISO 27001 compliance**: Security controls, audit requirements
- **Insider Threat compliance**: Behavioral monitoring, audit requirements

## Usage

### Ingest Behavior Event

```bash
export UBA_AUTH_DOMAIN="example.com"
export UBA_SOURCE_SYSTEM="linux-agent"

python3 uba-core/cli/ingest_behavior.py \
    --event /path/to/event.json \
    --user-id "john.doe" \
    --identity-type human \
    --auth-domain example.com \
    --identities-store /var/lib/ransomeye/uba/identities.jsonl \
    --events-store /var/lib/ransomeye/uba/events.jsonl \
    --baselines-store /var/lib/ransomeye/uba/baselines.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output normalized_event.json
```

### Build Baseline

```bash
export UBA_BASELINE_WINDOW_DAYS="30"

python3 uba-core/cli/build_baseline.py \
    --identity-id <identity-uuid> \
    --window-start "2024-01-01T00:00:00Z" \
    --window-end "2024-01-31T23:59:59Z" \
    --identities-store /var/lib/ransomeye/uba/identities.jsonl \
    --events-store /var/lib/ransomeye/uba/events.jsonl \
    --baselines-store /var/lib/ransomeye/uba/baselines.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output baseline.json
```

### Export Baseline

```bash
python3 uba-core/cli/export_baseline.py \
    --identity-id <identity-uuid> \
    --baseline-id <baseline-uuid> \
    --identities-store /var/lib/ransomeye/uba/identities.jsonl \
    --events-store /var/lib/ransomeye/uba/events.jsonl \
    --baselines-store /var/lib/ransomeye/uba/baselines.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output exported_baseline.json
```

### Programmatic API

```python
from api.uba_api import UBAAPI

api = UBAAPI(
    identities_store_path=Path('/var/lib/ransomeye/uba/identities.jsonl'),
    events_store_path=Path('/var/lib/ransomeye/uba/events.jsonl'),
    baselines_store_path=Path('/var/lib/ransomeye/uba/baselines.jsonl'),
    ledger_path=Path('/var/lib/ransomeye/audit/ledger.jsonl'),
    ledger_key_dir=Path('/var/lib/ransomeye/audit/keys')
)

# Ingest behavior event
normalized = api.ingest_behavior_event(
    raw_event=raw_event_dict,
    user_id='john.doe',
    identity_type='human',
    auth_domain='example.com'
)

# Build baseline
baseline = api.build_identity_baseline(
    identity_id=identity_id,
    window_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
    window_end=datetime(2024, 1, 31, tzinfo=timezone.utc)
)

# Get baseline
baseline = api.get_identity_baseline(identity_id)
```

## File Structure

```
uba-core/
├── schema/
│   ├── identity.schema.json              # Frozen JSON schema for identities
│   ├── behavior-event.schema.json        # Frozen JSON schema for behavior events
│   └── identity-baseline.schema.json     # Frozen JSON schema for baselines
├── engine/
│   ├── __init__.py
│   ├── identity_resolver.py             # Deterministic identity resolution
│   ├── behavior_normalizer.py           # Canonical behavior normalization
│   ├── baseline_builder.py              # Historical baseline building
│   └── baseline_hasher.py               # Deterministic baseline hashing
├── storage/
│   ├── __init__.py
│   └── uba_store.py                     # Append-only, immutable storage
├── api/
│   ├── __init__.py
│   └── uba_api.py                       # UBA API with audit integration
├── cli/
│   ├── __init__.py
│   ├── ingest_behavior.py               # Ingest behavior event CLI
│   ├── build_baseline.py                # Build baseline CLI
│   └── export_baseline.py               # Export baseline CLI
└── README.md                            # This file
```

## Environment Variables

- **UBA_AUTH_DOMAIN**: Authentication domain (default: 'local')
- **UBA_SOURCE_SYSTEM**: Source system identifier (default: 'linux-agent')
- **UBA_BASELINE_WINDOW_DAYS**: Baseline window in days (default: 30)

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **Audit Ledger**: Required for audit trail (separate subsystem)

## Security Considerations

1. **No Inference**: No inference logic exists
2. **Facts Only**: All outputs are facts, not conclusions
3. **Immutable Storage**: All records are immutable
4. **Deterministic**: Same inputs always produce same outputs
5. **Replayable**: All baselines can be rebuilt from events

## Limitations

1. **No ML**: No machine learning models
2. **No Scoring**: No risk or threat scoring
3. **No Alerts**: No alert generation
4. **No Inference**: No intent or motivation inference
5. **Ground Truth Only**: Establishes facts, not intent

## Determinism Guarantees

- ✅ **Same events → same baseline**: Deterministic baseline building
- ✅ **Same identity → same hash**: Deterministic identity hashing
- ✅ **Same input → same output**: Deterministic processing
- ✅ **Bit-for-bit identical**: Baselines rebuild bit-for-bit identical

## Replay Guarantees

- ✅ **Rebuild from zero**: Global Validator can rebuild all baselines
- ✅ **Verify hashes**: Baseline hashes can be verified
- ✅ **Detect alterations**: Missing or altered events can be detected
- ✅ **Confirm no inference**: Validator confirms no inference occurred

## Regulatory Compliance

UBA Core supports:

- **SOX**: Full audit trail, immutable records
- **SOC2**: Access controls, audit logging
- **ISO 27001**: Security controls, audit requirements
- **Insider Threat**: Behavioral monitoring, audit requirements

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye UBA Core documentation.

**STATEMENT**: UBA Core establishes facts, not intent.
