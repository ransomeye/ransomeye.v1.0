# RansomEye Explanation Assembly Engine

**AUTHORITATIVE:** Human-facing explanation assembly from existing explanation fragments

## Purpose Statement

The Explanation Assembly Engine assembles existing explanation fragments into audience-specific views. This engine **does NOT create new explanations**, **does NOT generate text**, **does NOT summarize**, and **does NOT infer new facts**.

**It ONLY reorders, filters, and presents explanations without changing meaning, authority, or causality.**

> **"One truth, many views. Never many truths."**

## Core Principle

> **"Explanation Assembly changes presentation, never meaning."**

## Difference Between Explanation and Assembly

- **Explanation**: Creates new explanation content (SEE, Alert Engine, UBA Alert Context, Risk Index)
- **Assembly**: Arranges existing explanations into audience-specific views (this engine)

This engine **does not explain events** — it **arranges explanations for humans**.

## Why No Summarization Exists Here

Summarization would:
- Create new facts (forbidden)
- Compress information (loss of fidelity)
- Introduce inference (forbidden)
- Modify meaning (forbidden)

Assembly only:
- Reorders existing content
- Filters by view_type
- Presents without modification
- Maintains full fidelity

## Supported View Types (EXACTLY 4)

1. **SOC_ANALYST**: Technical, chronological view
   - Ordering: CHRONOLOGICAL, TECHNICAL_HIERARCHY
   - Focus: Technical details, causality, timeline

2. **INCIDENT_COMMANDER**: Risk and accountability view
   - Ordering: RISK_IMPACT, ACCOUNTABILITY_CHAIN, CHRONOLOGICAL
   - Focus: Risk impact, accountability, decision points

3. **EXECUTIVE**: High-level risk and accountability view
   - Ordering: RISK_IMPACT, ACCOUNTABILITY_CHAIN
   - Focus: Business impact, accountability, strategic decisions

4. **REGULATOR**: Audit trail and chain-of-custody view
   - Ordering: LEDGER_ORDER, CHAIN_OF_CUSTODY, CHRONOLOGICAL
   - Focus: Audit trail, chain-of-custody, determinism

**No other view types. No free customization. No dynamic templates.**

## Architecture

### Data Flow

```
Source Explanations (read-only)
    ↓
Explanation Assembly Engine
    ↓ (read-only)
SEE Bundles
Alert Context Blocks
Risk Scores
KillChain Timelines
Threat Graph Paths
    ↓
Assembled Explanation View (immutable)
    ↓
Human Audience (SOC, Commander, Executive, Regulator)
```

### Integration Points

1. **System Explanation Engine (SEE)**: Read-only consumption of explanation bundles
2. **Alert Engine**: Read-only reference to alerts
3. **UBA Alert Context**: Read-only consumption of context blocks
4. **Risk Index**: Read-only reference to risk scores
5. **KillChain & Forensics**: Read-only reference to timelines
6. **Threat Graph**: Read-only reference to graph paths
7. **Audit Ledger**: All operations emit ledger entries
8. **Global Validator**: Full replay capability

## Schema

### Assembled Explanation

All fields are **mandatory** (zero optional fields):

- `assembled_explanation_id` (UUID): Unique identifier
- `incident_id` (UUID): Incident identifier
- `view_type` (enum): Audience-specific view type (exactly 4 types)
- `source_explanation_bundle_ids` (array of UUIDs): SEE bundle identifiers
- `source_alert_ids` (array of UUIDs): Alert identifiers
- `source_context_block_ids` (array of UUIDs): Alert context block identifiers
- `source_risk_ids` (array of UUIDs): Risk score identifiers
- `ordering_rules_applied` (array of enums): Explicit ordering rules
- `content_blocks` (array of structured objects): Content blocks (no prose generation)
- `integrity_hash` (SHA256): Deterministic hash
- `generated_at` (RFC3339 UTC): Timestamp of generation

### Ordering Rules

- `CHRONOLOGICAL`: Sort by timestamp
- `TECHNICAL_HIERARCHY`: Sort by source_type hierarchy
- `RISK_IMPACT`: Sort by risk score
- `ACCOUNTABILITY_CHAIN`: Sort by accountability order
- `LEDGER_ORDER`: Sort by ledger entry order
- `CHAIN_OF_CUSTODY`: Sort by chain-of-custody order

## Regulatory Positioning

### SOX / SOC2 / ISO Compliance

- **Deterministic**: Same inputs → same outputs (auditable)
- **Immutable**: Assembled explanations cannot be modified after creation
- **Traceable**: Full chain from source explanations → assembled view
- **Validator-replayable**: All assemblies can be rebuilt from audit ledger

### Regulator View

- **Audit trail**: Full ledger order preserved
- **Chain-of-custody**: Complete chain-of-custody maintained
- **Determinism**: All ordering is deterministic and replayable
- **No inference**: No new facts, no summarization, no compression

## Analyst vs Executive vs Regulator Differences

### SOC Analyst View

- **Focus**: Technical details, causality, timeline
- **Ordering**: Chronological, technical hierarchy
- **Content**: Technical details, behavioral context, causality

### Incident Commander View

- **Focus**: Risk impact, accountability, decision points
- **Ordering**: Risk impact, accountability chain, chronological
- **Content**: Risk assessments, accountability, decision points

### Executive View

- **Focus**: Business impact, accountability, strategic decisions
- **Ordering**: Risk impact, accountability chain
- **Content**: High-level risk, accountability, strategic context

### Regulator View

- **Focus**: Audit trail, chain-of-custody, determinism
- **Ordering**: Ledger order, chain-of-custody, chronological
- **Content**: Audit trail, chain-of-custody, deterministic evidence

## Failure Semantics

### Source Explanation Missing

- **Behavior**: Assembly fails with explicit error
- **Impact**: Assembly cannot proceed without all required sources
- **Recovery**: Ensure all source explanations exist before assembly

### View Type Invalid

- **Behavior**: Assembly fails (view_type must be one of 4 valid types)
- **Impact**: Invalid view_type rejected
- **Recovery**: Use valid view_type (SOC_ANALYST, INCIDENT_COMMANDER, EXECUTIVE, REGULATOR)

### Integrity Hash Mismatch

- **Behavior**: Validator detects hash mismatch
- **Impact**: Assembly integrity compromised
- **Recovery**: Rebuild assembly from audit ledger

## Validator Guarantees

The Global Validator can rebuild assembled explanations from:

1. **Audit Ledger**: All assemblies are audit-logged
2. **SEE Bundles**: Source explanation bundles are immutable
3. **UBA Alert Context**: Source context blocks are immutable
4. **Risk Index**: Source risk scores are immutable
5. **KillChain & Forensics**: Source timelines are immutable
6. **Threat Graph**: Source graph paths are immutable
7. **Deterministic Logic**: Same inputs → same outputs

**Validation Rules**:
- Same incident_id + same view_type + same sources → same assembled_explanation
- Integrity hash can be verified
- All assemblies are replayable from audit ledger
- No missing or reordered facts

## Explicit Non-Features

This engine **MUST NOT**:

- ❌ Generate text
- ❌ Rewrite explanations
- ❌ Collapse explanations
- ❌ Hide causality
- ❌ Create "TL;DR"
- ❌ Score explanations
- ❌ Decide importance
- ❌ Introduce LLMs
- ❌ Modify existing explanation content

## Usage

### Assemble Explanation

```bash
python3 explanation-assembly/cli/assemble_explanation.py \
    --incident-id <incident-uuid> \
    --view-type SOC_ANALYST \
    --source-explanation-bundle-ids <bundle-uuid-1> <bundle-uuid-2> \
    --source-alert-ids <alert-uuid-1> <alert-uuid-2> \
    --source-context-block-ids <context-uuid-1> \
    --source-risk-ids <risk-uuid-1> \
    --source-content /path/to/source-content.json \
    --store /var/lib/ransomeye/explanation-assembly/assemblies.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output assembled-explanation.json
```

### Export Explanation

```bash
python3 explanation-assembly/cli/export_explanation.py \
    --assembled-explanation-id <assembly-uuid> \
    --store /var/lib/ransomeye/explanation-assembly/assemblies.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output assembled-explanation.json
```

### Programmatic API

```python
from api.assembly_api import AssemblyAPI

api = AssemblyAPI(
    store_path=Path('/var/lib/ransomeye/explanation-assembly/assemblies.jsonl'),
    ledger_path=Path('/var/lib/ransomeye/audit/ledger.jsonl'),
    ledger_key_dir=Path('/var/lib/ransomeye/audit/keys')
)

# Assemble explanation
assembled = api.assemble_incident_explanation(
    incident_id='incident-uuid',
    view_type='SOC_ANALYST',
    source_explanation_bundle_ids=['bundle-uuid-1'],
    source_alert_ids=['alert-uuid-1'],
    source_context_block_ids=['context-uuid-1'],
    source_risk_ids=['risk-uuid-1'],
    source_content={
        'see_bundles': {'bundle-uuid-1': {'reference': 'see://bundle-uuid-1'}},
        'alerts': {'alert-uuid-1': {'reference': 'alert://alert-uuid-1'}},
        'alert_contexts': {'context-uuid-1': {'reference': 'context://context-uuid-1'}},
        'risk_scores': {'risk-uuid-1': {'reference': 'risk://risk-uuid-1'}}
    }
)

# Get assembled explanation
assembly = api.get_assembled_explanation('assembly-uuid')

# List assemblies for incident
assemblies = api.list_assembled_explanations('incident-uuid')
```

## File Structure

```
explanation-assembly/
├── schema/
│   └── assembled-explanation.schema.json    # Frozen JSON schema
├── engine/
│   ├── __init__.py
│   ├── assembly_engine.py                  # Deterministic assembly engine
│   └── assembly_hasher.py                 # SHA256 hashing
├── storage/
│   ├── __init__.py
│   └── assembly_store.py                   # Immutable, append-only storage
├── api/
│   ├── __init__.py
│   └── assembly_api.py                     # Assembly API
├── cli/
│   ├── __init__.py
│   ├── assemble_explanation.py             # Assemble explanation CLI
│   └── export_explanation.py              # Export explanation CLI
└── README.md                               # This file
```

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **Audit Ledger**: Required for audit trail (separate subsystem)
- **System Explanation Engine (SEE)**: Required for explanation bundle references (separate subsystem)
- **Alert Engine**: Required for alert references (separate subsystem)
- **UBA Alert Context**: Required for context block references (separate subsystem)
- **Risk Index**: Required for risk score references (separate subsystem)

## Security Considerations

1. **Read-only access**: Never modifies source explanations
2. **Immutable storage**: Assembled explanations cannot be modified after creation
3. **Auditable**: All operations are audit-logged
4. **Deterministic**: Same inputs → same outputs (replayable)
5. **No inference**: No new facts, no summarization, no compression

## Final Statement

> **Explanation Assembly does not explain events — it arranges explanations for humans.**

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye Explanation Assembly Engine documentation.
