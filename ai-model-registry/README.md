# RansomEye AI Model Registry & Governance Core

**AUTHORITATIVE:** Central governance system for all AI/ML/LLM models used in RansomEye

## Overview

The RansomEye AI Model Registry provides **full lifecycle governance** for every AI/ML/LLM model used anywhere in the RansomEye platform. No model may be loaded, executed, or referenced without registry approval. This subsystem ensures **cryptographic integrity**, **explicit lifecycle management**, and **complete auditability** for all AI models.

## Core Principles

### No Model Without Registry

**CRITICAL**: No model can exist outside the registry:

- ✅ **All models must be registered** before use
- ✅ **All model loads must verify registry** (enforced by consumers)
- ✅ **All model references must be validated** against registry
- ✅ **No implicit model loading** allowed

### Explicit Lifecycle Management

**CRITICAL**: All lifecycle transitions are explicit and auditable:

- ✅ **No implicit promotion** - models must be explicitly promoted
- ✅ **No silent revocation** - all revocations are recorded
- ✅ **Every transition** is written to Audit Ledger
- ✅ **State transitions** are validated and enforced

### Cryptographic Discipline

**CRITICAL**: All models are cryptographically verified:

- ✅ **Signature verification** before registry entry
- ✅ **Hash verification** at every load attempt
- ✅ **Fail-closed** on mismatch (rejection)
- ✅ **Separate signing keys** for model bundles

## Model Registry Features

### 1. Versioned Model Records

Each model is registered with:
- **Model ID**: Unique identifier (UUID)
- **Model Version**: Semantic versioning (e.g., 1.0.0)
- **Model Name**: Human-readable name
- **Model Type**: ML, DL, LLM, or ruleset
- **Intended Use**: Classification, clustering, summarization, etc.

### 2. Immutable Model Metadata

Model records are **immutable** after creation:
- **Artifact Hash**: SHA256 hash of model artifact
- **Artifact Signature**: ed25519 signature of artifact hash
- **Training Data Provenance**: Hash references to training data (not raw data)
- **Metadata**: Additional immutable metadata

### 3. Lifecycle States

Models progress through explicit states:

- **REGISTERED**: Model is registered but not active
- **PROMOTED**: Model is active and can be used
- **DEPRECATED**: Model is deprecated but still available
- **REVOKED**: Model is revoked and must not be used (terminal)

### 4. Valid State Transitions

Explicit transition rules:
- **REGISTERED** → **PROMOTED** or **REVOKED**
- **PROMOTED** → **DEPRECATED** or **REVOKED**
- **DEPRECATED** → **REVOKED**
- **REVOKED** → (terminal, no transitions)

### 5. Hot-Swap Governance

Registry allows marking models as "active":
- **Active models** are in PROMOTED state
- **No runtime loading logic** in this phase (consumers will query registry)
- **Control plane only** - governance, not execution

### 6. Drift Detection Metadata

Foundation for future drift detection:
- **Schema for drift metrics** (defined but not implemented)
- **Storage of drift observations** (placeholder)
- **NO detection logic** in this phase (future work)

## Cryptographic Verification

### Model Bundle Verification

Before registry entry:
1. **Calculate artifact hash** (SHA256)
2. **Verify signature** (ed25519)
3. **Verify hash matches** provided hash
4. **Reject on mismatch** (fail-closed)

### Load-Time Verification

At every load attempt:
1. **Query registry** for model record
2. **Verify artifact hash** matches registry
3. **Verify signature** using public key
4. **Reject on mismatch** (fail-closed)

### Separate Signing Keys

**CRITICAL**: Model registry uses **separate signing keys**:
- **Model Keys**: Used for signing model artifacts
- **Ledger Keys**: Used for signing audit ledger entries
- **Never Reused**: Keys are never shared between systems

## Audit & Validation

### Audit Ledger Integration

**Every registry action** emits an Audit Ledger entry:

- **ai_model_register**: Model registration
- **ai_model_promote**: Model promotion to active
- **ai_model_revoke**: Model revocation
- **ai_model_deprecate**: Model deprecation

### Global Validator Integration

Global Validator can verify:
- **No unregistered models exist** - all models must be in registry
- **No revoked model is active** - revoked models cannot be PROMOTED
- **Registry integrity matches ledger** - all actions have ledger entries

## Usage

### Register a Model

```bash
python3 ai-model-registry/cli/register_model.py \
    --artifact /path/to/model.bin \
    --model-name "threat-detection-v1" \
    --model-version "1.0.0" \
    --model-type "ML" \
    --intended-use "threat_detection" \
    --training-data /path/to/training-provenance.json \
    --registered-by "admin" \
    --registry /var/lib/ransomeye/models/registry.jsonl \
    --model-key-dir /var/lib/ransomeye/models/keys \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output model-record.json
```

### Promote a Model

```bash
python3 ai-model-registry/cli/promote_model.py \
    --model-id <model-uuid> \
    --model-version "1.0.0" \
    --promoted-by "admin" \
    --reason "Production deployment" \
    --registry /var/lib/ransomeye/models/registry.jsonl \
    --model-key-dir /var/lib/ransomeye/models/keys \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys
```

### Revoke a Model

```bash
python3 ai-model-registry/cli/revoke_model.py \
    --model-id <model-uuid> \
    --model-version "1.0.0" \
    --revoked-by "admin" \
    --reason "Security vulnerability" \
    --registry /var/lib/ransomeye/models/registry.jsonl \
    --model-key-dir /var/lib/ransomeye/models/keys \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys
```

### Programmatic API

```python
from api.registry_api import RegistryAPI

api = RegistryAPI(
    registry_path=Path('/var/lib/ransomeye/models/registry.jsonl'),
    model_key_dir=Path('/var/lib/ransomeye/models/keys'),
    ledger_path=Path('/var/lib/ransomeye/audit/ledger.jsonl'),
    ledger_key_dir=Path('/var/lib/ransomeye/audit/keys')
)

# Register model
model_record = api.register_model(
    artifact_path=Path('/path/to/model.bin'),
    artifact_hash='<sha256-hash>',
    artifact_signature='<base64-signature>',
    signing_key_id='<key-id>',
    model_name='threat-detection-v1',
    model_version='1.0.0',
    model_type='ML',
    intended_use='threat_detection',
    training_data_provenance={'data_hashes': [], 'data_sources': []},
    registered_by='admin'
)

# Promote model
api.promote_model(
    model_id=model_record['model_id'],
    model_version='1.0.0',
    promoted_by='admin'
)

# List active models
active_models = api.list_active_models()
```

## File Structure

```
ai-model-registry/
├── schema/
│   └── model-record.schema.json    # Frozen JSON schema
├── crypto/
│   ├── __init__.py
│   ├── key_manager.py             # Model bundle key management
│   └── bundle_verifier.py         # Model bundle verification
├── registry/
│   ├── __init__.py
│   ├── registry_store.py          # Immutable registry storage
│   └── lifecycle.py               # Lifecycle state management
├── api/
│   ├── __init__.py
│   └── registry_api.py            # Registry API with audit integration
├── cli/
│   ├── __init__.py
│   ├── register_model.py          # Model registration CLI
│   ├── promote_model.py           # Model promotion CLI
│   └── revoke_model.py            # Model revocation CLI
└── README.md                      # This file
```

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **cryptography**: Required for ed25519 signing/verification
  - Install: `pip install cryptography`
- **Audit Ledger**: Required for audit trail (separate subsystem)

## Security Considerations

1. **Separate Keys**: Model registry uses separate signing keys from audit ledger
2. **Key Protection**: Model private keys must be protected (0o600 permissions)
3. **Fail-Closed**: All verification failures result in rejection
4. **Immutable Records**: Model records cannot be modified after creation
5. **Explicit Transitions**: All lifecycle transitions are explicit and auditable

## Limitations

1. **No Runtime Loading**: Phase B1 provides governance only, no runtime loading logic
2. **No Inference Logic**: No AI inference logic in this module
3. **No Online Dependencies**: Registry is offline-capable (no network required)
4. **No Drift Detection**: Drift detection metadata schema only, no detection logic

## Future Enhancements

- Runtime model loading with registry verification
- Drift detection implementation
- Model versioning and rollback
- Model performance metrics
- Automated model validation

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye AI Model Registry documentation.
