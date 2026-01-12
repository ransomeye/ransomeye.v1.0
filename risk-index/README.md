# RansomEye Enterprise Risk Index Engine

**AUTHORITATIVE:** Deterministic engine for computing global, normalized enterprise risk scores

## Overview

The RansomEye Enterprise Risk Index is a **deterministic engine** that computes a global, normalized (0-100) risk score representing the security posture of the entire enterprise. This score serves as:

- **The single executive truth**: One authoritative risk score for the enterprise
- **The input to board reporting**: Executive and board-level risk metrics
- **The baseline for automation thresholds**: Foundation for automated response decisions

## Core Principles

### Deterministic Computation

**CRITICAL**: Risk computation is fully deterministic:

- ✅ **No randomness**: Same inputs always produce same outputs
- ✅ **Explicit weights**: All component weights are explicitly configured
- ✅ **Temporal decay**: Deterministic decay functions for signal aging
- ✅ **Confidence-aware**: Adjusts scores based on signal confidence
- ✅ **Explainable**: Component contributions are explicitly tracked

### Read-Only Signal Ingestion

**CRITICAL**: All signal ingestion is read-only:

- ✅ **No mutation**: Source signals are never modified
- ✅ **Read-only references**: Signal IDs are stored, not data
- ✅ **No assumptions**: Missing signals are explicitly detected

### Audit & Assurance

**CRITICAL**: Every computation is auditable:

- ✅ **Audit Ledger entry**: Every score computation emits ledger entry
- ✅ **Global Validator verification**: Scores can be recomputed deterministically
- ✅ **Missing signal detection**: Validator verifies no missing signals

## Risk Model

### Signal Sources

The risk index consumes signals from:

1. **Incidents** (correlation engine): Active security incidents
2. **AI Metadata**: Novelty scores, clusters, drift markers
3. **Policy Decisions**: Policy enforcement actions, overrides, violations
4. **Threat Correlation** (future): Threat intelligence correlation
5. **UBA** (future): User Behavior Analytics signals

### Weighted Aggregation

Risk scores are computed using **weighted aggregation**:

- **Explicit weights**: Each component has an explicit weight (must sum to 1.0)
- **Default weights**: Equal distribution if not specified
- **Configurable**: Weights can be configured per deployment

Default weights:
- Incidents: 0.3 (30%)
- AI Metadata: 0.3 (30%)
- Policy Decisions: 0.2 (20%)
- Threat Correlation: 0.1 (10%)
- UBA: 0.1 (10%)

### Temporal Decay

Risk signals age over time using **deterministic decay functions**:

- **Exponential decay**: `score * exp(-ln(2) * age / half_life)`
- **Linear decay**: `score * (1 - age / max_age)`
- **Step decay**: Constant within intervals, drops at boundaries
- **No decay**: Signals retain original score

### Confidence-Aware Scoring

Risk scores are adjusted based on **confidence**:

- **Signal completeness**: Ratio of processed to expected signals
- **Component confidence**: Confidence scores from AI metadata
- **Combined confidence**: Weighted average of completeness and component confidence

### Normalization

All risk scores are **normalized to 0-100 range**:

- **Strict bounds**: Scores are clamped to [0, 100]
- **Severity bands**: 
  - **LOW**: 0-25
  - **MODERATE**: 25-50
  - **HIGH**: 50-75
  - **CRITICAL**: 75-100

## Historical Tracking

### Immutable Records

Risk score records are **immutable**:

- **No modification**: Records cannot be changed after creation
- **No deletion**: Records are never deleted
- **Complete timeline**: Full historical record maintained

### Historical Queries

Risk store supports:

- **Latest score**: Get most recent risk score
- **Timestamp range**: Get scores within time range
- **Full history**: Get all historical scores

## Usage

### Compute Risk Score

```bash
python3 risk-index/cli/compute_risk.py \
    --incidents /path/to/incidents.json \
    --ai-metadata /path/to/ai-metadata.json \
    --policy-decisions /path/to/policy-decisions.json \
    --store /var/lib/ransomeye/risk/scores.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output risk-score.json
```

### With Custom Weights

```bash
python3 risk-index/cli/compute_risk.py \
    --incidents /path/to/incidents.json \
    --ai-metadata /path/to/ai-metadata.json \
    --weights /path/to/weights.json \
    --store /var/lib/ransomeye/risk/scores.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys
```

### With Temporal Decay

```bash
python3 risk-index/cli/compute_risk.py \
    --incidents /path/to/incidents.json \
    --ai-metadata /path/to/ai-metadata.json \
    --decay-config /path/to/decay-config.json \
    --store /var/lib/ransomeye/risk/scores.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys
```

### Programmatic API

```python
from api.risk_api import RiskAPI

api = RiskAPI(
    store_path=Path('/var/lib/ransomeye/risk/scores.jsonl'),
    ledger_path=Path('/var/lib/ransomeye/audit/ledger.jsonl'),
    ledger_key_dir=Path('/var/lib/ransomeye/audit/keys'),
    weights={
        'incidents': 0.3,
        'ai_metadata': 0.3,
        'policy_decisions': 0.2,
        'threat_correlation': 0.1,
        'uba': 0.1
    }
)

# Compute risk score
score_record = api.compute_risk(
    incidents=[{'id': 'inc-1', 'severity': 'high'}],
    ai_metadata=[{'id': 'ai-1', 'novelty_score': 75.0}],
    policy_decisions=[{'id': 'pol-1', 'action_type': 'block'}]
)

# Get latest score
latest = api.get_latest_score()

# Get score history
history = api.get_score_history(
    start_timestamp='2025-01-01T00:00:00Z',
    end_timestamp='2025-01-31T23:59:59Z'
)
```

## Signal Format

### Incidents

```json
[
  {
    "id": "incident-uuid",
    "severity": "high",
    "timestamp": "2025-01-10T12:00:00Z"
  }
]
```

### AI Metadata

```json
[
  {
    "id": "ai-metadata-uuid",
    "novelty_score": 75.0,
    "cluster_risk": 60.0,
    "drift_marker": 40.0,
    "confidence": 0.9,
    "timestamp": "2025-01-10T12:00:00Z"
  }
]
```

### Policy Decisions

```json
[
  {
    "id": "policy-decision-uuid",
    "action_type": "block",
    "timestamp": "2025-01-10T12:00:00Z"
  }
]
```

## Configuration

### Weights Configuration

```json
{
  "incidents": 0.3,
  "ai_metadata": 0.3,
  "policy_decisions": 0.2,
  "threat_correlation": 0.1,
  "uba": 0.1
}
```

### Decay Configuration

```json
{
  "function": "exponential",
  "half_life_seconds": 86400
}
```

Or linear decay:

```json
{
  "function": "linear",
  "max_age_seconds": 604800
}
```

Or step decay:

```json
{
  "function": "step",
  "step_intervals": [
    [3600, 1.0],
    [86400, 0.5],
    [604800, 0.25]
  ]
}
```

## File Structure

```
risk-index/
├── schema/
│   └── risk-score.schema.json    # Frozen JSON schema
├── engine/
│   ├── __init__.py
│   ├── aggregator.py              # Weighted aggregation
│   ├── decay.py                   # Temporal decay functions
│   └── normalizer.py              # Score normalization
├── storage/
│   ├── __init__.py
│   └── risk_store.py              # Immutable risk score storage
├── api/
│   ├── __init__.py
│   └── risk_api.py                # Risk computation API
├── cli/
│   ├── __init__.py
│   └── compute_risk.py            # Risk computation CLI
└── README.md                      # This file
```

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **Audit Ledger**: Required for audit trail (separate subsystem)

## Security Considerations

1. **Deterministic**: All computation is deterministic (no randomness)
2. **Read-Only**: Signal ingestion never mutates source data
3. **Auditable**: Every computation is recorded in audit ledger
4. **Immutable**: Historical records cannot be modified
5. **Explainable**: Component contributions are explicitly tracked

## Limitations

1. **No UI**: Phase B2 provides computation only, no UI
2. **No Alerting**: No alerting or notification logic
3. **No Enforcement**: No automated enforcement based on risk scores
4. **Future Signals**: Threat correlation and UBA are placeholders

## Future Enhancements

- Real-time risk score updates
- Risk trend analysis
- Automated threshold-based actions
- Integration with threat intelligence
- User Behavior Analytics integration

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye Enterprise Risk Index documentation.
