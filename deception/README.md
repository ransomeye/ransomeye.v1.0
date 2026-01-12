# RansomEye Deception Framework

**AUTHORITATIVE:** Active defense, non-destructive deception for observation and evidence collection

## Overview

The RansomEye Deception Framework deploys **decoy assets** (hosts, services, credentials, files) to attract attacker interaction, generate **high-confidence signals**, and produce **evidence-grade telemetry**. It never interferes with production assets. Deception is **observation with intent**, not enforcement.

## Core Principles

### Observation with Intent, Not Enforcement

**CRITICAL**: Deception is observation, not enforcement:

- ✅ **No counter-attacks**: No counter-attack logic
- ✅ **No malware execution**: No malware execution
- ✅ **No real credential exposure**: No real credentials exposed
- ✅ **No production host modification**: No production host changes
- ✅ **No automatic blocking**: No automatic blocking
- ✅ **No retaliation logic**: No retaliation logic
- ✅ **No background autonomy**: No background autonomy
- ✅ **No dynamic learning or ML**: No ML during deception

### Explicit and Deterministic

**CRITICAL**: Everything is explicit and deterministic:

- ✅ **Explicit deployment**: Deployment is explicit only
- ✅ **Deterministic**: Same decoy = same behavior
- ✅ **Reversible**: All deployments are reversible
- ✅ **Isolated**: Decoys are isolated from production

### Evidence-Grade Telemetry

**CRITICAL**: All interactions are evidence-grade:

- ✅ **High confidence**: All interactions are HIGH confidence by default
- ✅ **Immutable**: Interactions are immutable facts
- ✅ **No aggregation**: No aggregation at capture time
- ✅ **No drops**: No interactions are dropped

## Decoy Types

### Host Decoys

- **Fake Linux/Windows hosts**: Fake hosts that appear real
- **Never real production IPs**: Decoys never use production IPs
- **Isolated**: Decoys are isolated from production assets

### Service Decoys

- **Fake SSH/SMB/HTTP banners**: Fake service banners
- **Banner-only**: Banner-only, no real backend
- **Attractive**: Banners designed to attract interaction

### Credential Decoys

- **Honey credentials**: Fake credentials that appear valid
- **Cryptographically tagged**: Credentials are cryptographically tagged
- **Never valid in real systems**: Credentials never valid in production

### File/Artifact Decoys

- **Fake configs, keys, documents**: Fake files that appear valuable
- **Read-only access**: Files are read-only
- **Attractive**: Files designed to attract interaction

## Interaction Capture

### Required Fields

Every interaction must record:

- **interaction_id**: Unique identifier (UUID)
- **decoy_id**: Decoy identifier
- **interaction_type**: Type of interaction (auth_attempt, scan, access, command)
- **source_ip**: Source IP address
- **source_host**: Source hostname (if available)
- **source_process**: Source process identifier (if available)
- **timestamp**: Interaction timestamp (RFC3339 UTC)
- **evidence_reference**: Evidence reference identifier (KillChain & Forensics)
- **confidence_level**: Confidence level (HIGH by default)
- **immutable_hash**: SHA256 hash of interaction record
- **ledger_entry_id**: Audit ledger entry ID

### Interaction Types

- **auth_attempt**: Authentication attempt
- **scan**: Network scan
- **access**: File or resource access
- **command**: Command execution

## Signal Requirements

### Signal Properties

Signals produced by deception must be:

- ✅ **High confidence by design**: Signals are high confidence by design
- ✅ **Deterministic**: Same interactions = same signals
- ✅ **Explicitly explainable**: Signals are explicitly explainable
- ✅ **Chain-of-custody protected**: Signals are chain-of-custody protected

### Signal Flow

Signals flow into:

- **KillChain & Forensics**: Evidence references
- **Threat Graph**: Entity + edge creation
- **Risk Index**: Risk scoring
- **Alert Engine**: Alert generation
- **System Explanation Engine (SEE)**: Explanation bundles

## Required Integrations

Deception Framework integrates with:

- **Audit Ledger**: Deployment, interaction, teardown
- **Network Scanner**: Topology-aware placement
- **Linux Agent**: Host-level decoys
- **Threat Graph**: Entity + edge creation
- **KillChain & Forensics**: Evidence
- **Global Validator**: Replayability

## Usage

### Deploy Decoy

```bash
python3 deception/cli/deploy_decoy.py \
    --decoy-type service \
    --decoy-name "Fake SSH Server" \
    --decoy-config /path/to/decoy_config.json \
    --deployment-target 192.168.1.100 \
    --deployed-by operator \
    --decoys-store /var/lib/ransomeye/deception/decoys.jsonl \
    --deployments-store /var/lib/ransomeye/deception/deployments.jsonl \
    --interactions-store /var/lib/ransomeye/deception/interactions.jsonl \
    --signals-store /var/lib/ransomeye/deception/signals.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output deployment.json
```

### Collect Interaction

```bash
python3 deception/cli/collect_interactions.py \
    --decoy-id <decoy-uuid> \
    --interaction-type auth_attempt \
    --source-ip 192.168.1.50 \
    --source-host attacker.example.com \
    --evidence-reference <evidence-uuid> \
    --decoys-store /var/lib/ransomeye/deception/decoys.jsonl \
    --deployments-store /var/lib/ransomeye/deception/deployments.jsonl \
    --interactions-store /var/lib/ransomeye/deception/interactions.jsonl \
    --signals-store /var/lib/ransomeye/deception/signals.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output interaction.json
```

### Programmatic API

```python
from api.deception_api import DeceptionAPI

api = DeceptionAPI(
    decoys_store_path=Path('/var/lib/ransomeye/deception/decoys.jsonl'),
    deployments_store_path=Path('/var/lib/ransomeye/deception/deployments.jsonl'),
    interactions_store_path=Path('/var/lib/ransomeye/deception/interactions.jsonl'),
    signals_store_path=Path('/var/lib/ransomeye/deception/signals.jsonl'),
    ledger_path=Path('/var/lib/ransomeye/audit/ledger.jsonl'),
    ledger_key_dir=Path('/var/lib/ransomeye/audit/keys')
)

# Register decoy
decoy = api.register_decoy(
    decoy_type='service',
    decoy_name='Fake SSH Server',
    decoy_config={'port': 22, 'banner': 'SSH-2.0-OpenSSH_7.4'},
    deployment_target='192.168.1.100'
)

# Deploy decoy
deployment = api.deploy_decoy(
    decoy_id=decoy.get('decoy_id', ''),
    deployed_by='operator'
)

# Collect interaction
interaction = api.collect_interaction(
    decoy_id=decoy.get('decoy_id', ''),
    interaction_type='auth_attempt',
    source_ip='192.168.1.50',
    source_host='attacker.example.com'
)

# Build signal
signal = api.build_signal(decoy.get('decoy_id', ''))
```

## File Structure

```
deception/
├── schema/
│   ├── decoy.schema.json              # Frozen JSON schema for decoys
│   ├── interaction.schema.json       # Frozen JSON schema for interactions
│   └── deployment.schema.json         # Frozen JSON schema for deployments
├── engine/
│   ├── __init__.py
│   ├── decoy_registry.py             # Immutable decoy definitions
│   ├── deployment_engine.py          # Explicit deployment only
│   ├── interaction_collector.py      # Interaction capture
│   └── signal_builder.py             # High-confidence signals
├── integrations/
│   ├── __init__.py
│   ├── linux_agent_hooks.py         # Host-level decoy integration
│   └── network_scanner_hooks.py      # Topology-aware placement
├── api/
│   ├── __init__.py
│   └── deception_api.py            # Deception API with audit integration
├── cli/
│   ├── __init__.py
│   ├── deploy_decoy.py              # Deploy decoy CLI
│   └── collect_interactions.py      # Collect interactions CLI
└── README.md                        # This file
```

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **Audit Ledger**: Required for audit trail (separate subsystem)

## Security Considerations

1. **No Production Interference**: Decoys are isolated from production
2. **No Real Credentials**: No real credentials exposed
3. **No Counter-Attacks**: No counter-attack logic
4. **Deterministic**: Same inputs always produce same outputs
5. **Replayable**: Interactions can be replayed deterministically

## Limitations

1. **No Exploitation**: No exploit logic
2. **No Automatic Blocking**: No automatic blocking
3. **No Retaliation**: No retaliation logic
4. **No ML**: No dynamic learning or ML
5. **Explicit Only**: Deployment is explicit only

## Future Enhancements

- Advanced decoy types
- Automated decoy placement
- Enhanced interaction analysis
- Signal correlation
- Deception campaign management

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye Deception Framework documentation.
