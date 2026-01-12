# RansomEye System Explanation Engine (SEE)

**AUTHORITATIVE:** End-to-end, signed, validator-verifiable explanation bundles explaining why the system acted

## Overview

The RansomEye System Explanation Engine (SEE) produces **end-to-end, signed, validator-verifiable explanation bundles** that explain why the system acted in certain ways. It reconstructs reasoning from evidence across all subsystems, producing immutable, cryptographically signed explanations.

## Core Principles

### Deterministic Reconstruction

**CRITICAL**: Explanations are deterministic:

- ✅ **Same inputs → same explanation**: Same evidence always produces same explanation
- ✅ **Fully reconstructable**: Explanations can be rebuilt from scratch from ledger
- ✅ **No assumptions**: All reasoning is based on evidence, no assumptions
- ✅ **No heuristics**: No heuristic reasoning, only evidence-based reconstruction

### Read-Only Access

**CRITICAL**: SEE only reads from subsystems:

- ✅ **No mutation**: Never modifies source subsystems
- ✅ **Read-only**: Only reads audit ledger, killchain, graph, risk index
- ✅ **No side effects**: No side effects on subsystems

### Cryptographic Signing

**CRITICAL**: All explanations are cryptographically signed:

- ✅ **Dedicated keypair**: Uses dedicated signing keypair
- ✅ **Immutable bundles**: Signed bundles cannot be modified
- ✅ **Validator-verifiable**: Validators can verify signatures
- ✅ **Complete chain**: Complete chain of evidence

### Zero Ambiguity

**CRITICAL**: All explanations are unambiguous:

- ✅ **Explicit causal links**: All causal links are explicit
- ✅ **No missing links**: No missing causal links
- ✅ **Complete reasoning chain**: Complete reasoning chain from evidence
- ✅ **No implicit steps**: All steps are explicit

## Explanation Types

### Incident Explanation

Explains why an incident existed:

- **Evidence sources**: Audit ledger entries related to incident
- **Reasoning chain**: Ordered chain of events leading to incident
- **Causal links**: Explicit links between events

### KillChain Stage Advancement

Explains why a killchain stage advanced:

- **Evidence sources**: Killchain events, audit ledger entries
- **Reasoning chain**: Events leading to stage advancement
- **Causal links**: Links between killchain events

### Campaign Inference

Explains why campaign inference occurred:

- **Evidence sources**: Threat graph relationships, audit ledger entries
- **Reasoning chain**: Graph relationships leading to inference
- **Causal links**: Links between graph relationships

### Risk Score Change

Explains why risk score changed:

- **Evidence sources**: Risk computations, audit ledger entries
- **Reasoning chain**: Computations leading to score change
- **Causal links**: Links between risk computations

### Policy Recommendation

Explains why policy recommendation escalated:

- **Evidence sources**: Policy decisions, audit ledger entries
- **Reasoning chain**: Decisions leading to recommendation
- **Causal links**: Links between policy decisions

## Reasoning Reconstruction

### Evidence Sources

SEE reads from (read-only):

- **Audit Ledger**: Root of truth for all system actions
- **KillChain & Forensics**: Timeline events and evidence
- **Threat Correlation Graph**: Entity relationships
- **Risk Index Engine**: Risk computations
- **Policy Engine**: Policy decisions
- **Human Override**: Human override records (future)

### Reconstruction Process

1. **Identify subject**: Identify subject being explained (incident, event, etc.)
2. **Read evidence**: Read all evidence related to subject from subsystems
3. **Build reasoning chain**: Build ordered chain of reasoning steps
4. **Extract evidence references**: Extract all evidence references
5. **Build causal links**: Build explicit causal links between steps
6. **Sign bundle**: Cryptographically sign bundle

### Deterministic Rules

All reconstruction uses **deterministic rules**:

- **Temporal ordering**: Steps ordered by timestamp
- **Causal link types**: Link types determined by step types
- **Evidence extraction**: Evidence references extracted deterministically
- **No randomness**: No random or probabilistic reasoning

## Explanation Bundle Structure

### Bundle Fields

- **bundle_id**: Unique identifier (UUID)
- **timestamp**: Creation timestamp
- **explanation_type**: Type of explanation
- **subject_id**: Subject being explained
- **reasoning_chain**: Ordered chain of reasoning steps
- **evidence_references**: All evidence references
- **causal_links**: Explicit causal links
- **signature**: Cryptographic signature
- **public_key_id**: Public key identifier

### Reasoning Steps

Each reasoning step contains:

- **step_id**: Unique identifier (UUID)
- **step_type**: Type of step (ledger_entry, killchain_event, etc.)
- **description**: Human-readable description
- **evidence_source**: Source of evidence
- **evidence_id**: Evidence identifier
- **timestamp**: Step timestamp

### Causal Links

Each causal link contains:

- **from_step_id**: Source step identifier
- **to_step_id**: Target step identifier
- **link_type**: Type of link (triggers, enables, causes, etc.)
- **explanation**: Human-readable explanation

## Cryptographic Signing

### Signing Process

1. **Create bundle**: Build explanation bundle (without signature)
2. **Serialize**: Serialize to canonical JSON
3. **Sign**: Sign with private key (RSA-PSS with SHA256)
4. **Encode**: Encode signature as base64
5. **Attach**: Attach signature and key ID to bundle

### Verification Process

1. **Extract signature**: Extract signature from bundle
2. **Create copy**: Create bundle copy without signature
3. **Serialize**: Serialize to canonical JSON
4. **Verify**: Verify signature with public key
5. **Validate**: Validate bundle structure

## Usage

### Build Incident Explanation

```bash
python3 system-explainer/cli/build_explanation.py \
    --explanation-type incident_explanation \
    --subject-id <incident-id> \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --private-key /var/lib/ransomeye/explainer/keys/private.pem \
    --key-id explainer-key-1 \
    --output explanation.json
```

### Build KillChain Stage Explanation

```bash
python3 system-explainer/cli/build_explanation.py \
    --explanation-type killchain_stage_advancement \
    --subject-id <killchain-event-id> \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --killchain-store /var/lib/ransomeye/killchain/events.jsonl \
    --private-key /var/lib/ransomeye/explainer/keys/private.pem \
    --key-id explainer-key-1 \
    --output explanation.json
```

### Build Campaign Inference Explanation

```bash
python3 system-explainer/cli/build_explanation.py \
    --explanation-type campaign_inference \
    --subject-id <campaign-id> \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --threat-graph /var/lib/ransomeye/graph/graph.json \
    --private-key /var/lib/ransomeye/explainer/keys/private.pem \
    --key-id explainer-key-1 \
    --output explanation.json
```

### Programmatic API

```python
from api.explainer_api import ExplainerAPI

api = ExplainerAPI(
    ledger_path=Path('/var/lib/ransomeye/audit/ledger.jsonl'),
    private_key_path=Path('/var/lib/ransomeye/explainer/keys/private.pem'),
    key_id='explainer-key-1',
    killchain_store_path=Path('/var/lib/ransomeye/killchain/events.jsonl'),
    threat_graph_path=Path('/var/lib/ransomeye/graph/graph.json'),
    risk_store_path=Path('/var/lib/ransomeye/risk/scores.jsonl')
)

# Build explanation
bundle = api.explain_incident('incident-uuid')

# Verify explanation
from crypto.verifier import Verifier
verifier = Verifier(Path('/var/lib/ransomeye/explainer/keys/public.pem'))
is_valid = verifier.verify_bundle(bundle)
```

## File Structure

```
system-explainer/
├── schema/
│   └── explanation-bundle.schema.json    # Frozen JSON schema
├── engine/
│   ├── __init__.py
│   ├── reasoning_reconstructor.py        # Reasoning reconstruction
│   └── explanation_builder.py            # Explanation building
├── crypto/
│   ├── __init__.py
│   ├── signer.py                         # Cryptographic signing
│   └── verifier.py                       # Signature verification
├── api/
│   ├── __init__.py
│   └── explainer_api.py                  # Explanation API
├── cli/
│   ├── __init__.py
│   └── build_explanation.py              # CLI tool
└── README.md                              # This file
```

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **cryptography**: Required for cryptographic signing (RSA-PSS with SHA256)

## Security Considerations

1. **Immutable Bundles**: Signed bundles cannot be modified
2. **Cryptographic Signing**: All bundles are cryptographically signed
3. **Validator Verification**: Validators can verify signatures
4. **Read-Only Access**: SEE never mutates source subsystems
5. **Deterministic**: All reconstruction is deterministic (no randomness)

## Limitations

1. **No ML Inference**: No ML-based reasoning (only evidence-based)
2. **No Heuristics**: No heuristic reasoning
3. **No Free-Text Generation**: No free-text generation (structured only)
4. **No Assumptions**: No assumptions, only evidence

## Future Enhancements

- Human override explanation support
- Advanced causal link inference
- Multi-subject explanations
- Explanation visualization
- Explanation comparison

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye System Explanation Engine documentation.
