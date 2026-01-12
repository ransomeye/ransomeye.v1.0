# RansomEye HNMP Engine (Host / Network / Malware / Process Intelligence Core)

**AUTHORITATIVE:** Lowest-level, evidence-grade behavioral intelligence layer

## Overview

The RansomEye HNMP Engine provides **ground-truth behavioral facts** across **Host** (user, privilege, filesystem, memory), **Network** (flows, connections, DNS, DPI outputs), **Malware** (artifacts, hashes, behaviors), and **Process** (execution, parent/child, injections). HNMP produces **facts only**, never conclusions.

## Core Principles

### Observation and Normalization Only

**CRITICAL**: HNMP is observation and normalization only:

- ✅ **No scoring**: No scoring logic
- ✅ **No ML**: No machine learning
- ✅ **No heuristics**: No heuristics
- ✅ **No enforcement**: No enforcement actions
- ✅ **No alerting**: No alerting logic
- ✅ **No aggregation logic**: No aggregation logic
- ✅ **No implicit inference**: No implicit inference
- ✅ **No mutation**: No mutation of upstream data

### Facts Only, Never Conclusions

**CRITICAL**: HNMP produces facts only:

- ✅ **Ground-truth**: All events are ground-truth behavioral facts
- ✅ **Immutable**: All events are immutable
- ✅ **Deterministic**: Same inputs = same outputs
- ✅ **Canonical**: All events are normalized to canonical form

### Zero Optional Fields

**CRITICAL**: All schemas have zero optional fields:

- ✅ **All fields mandatory**: Every field is required
- ✅ **Explicit enumeration**: All types are explicitly enumerated
- ✅ **No defaults**: No default assumptions
- ✅ **No implicit joins**: No implicit joins

## Event Types

### Host Events

- **user_login**: User login event
- **user_logout**: User logout event
- **privilege_escalation**: Privilege escalation event
- **file_creation**: File creation event
- **file_modification**: File modification event
- **registry_change**: Registry change event (Windows)
- **credential_access_attempt**: Credential access attempt event

### Network Events

- **flow_start**: Network flow start event
- **flow_end**: Network flow end event
- **dns_query**: DNS query event
- **dns_response**: DNS response event
- **protocol_detection**: Protocol detection event
- **tls_metadata**: TLS metadata event (no payload)

### Process Events

- **process_start**: Process start event
- **process_exit**: Process exit event
- **parent_child_linkage**: Parent/child process linkage
- **injection_attempt**: Process injection attempt
- **suspicious_flags**: Suspicious flags (explicit, no inference)

### Malware Events

- **hash_observation**: Hash observation event
- **execution_attempt**: Execution attempt event
- **artifact_discovery**: Artifact discovery event
- **sandbox_verdict_reference**: Sandbox verdict reference (no scoring)

## Data Sources

HNMP ingests **only signed, validated inputs** from:

- **Linux Agent**: eBPF, procfs, audit
- **Windows Agent**: ETW, registry, process telemetry
- **DPI Probe**: Flows, L7 metadata
- **Forensics Engine**: Artifacts, memory dumps
- **Deception Framework**: Interactions
- **Threat Intel Engine**: IOC matches

**No raw packet capture storage.**

## Correlation Rules

Correlation is **strictly factual**:

- **process_network_flow**: Process ↔ network flow
- **process_file_artifact**: Process ↔ file artifact
- **file_artifact_malware_hash**: File artifact ↔ malware hash
- **user_process**: User ↔ process
- **host_network_identity**: Host ↔ network identity

**No campaign inference, no timelines, no killchain logic.**

## Required Integrations

HNMP Engine integrates with:

- **Audit Ledger**: All ingestion & correlation
- **KillChain & Forensics**: Input + downstream
- **Threat Graph**: Entity + edge generation
- **Alert Engine**: Context input only
- **Risk Index**: Signal input only
- **System Explanation Engine**: Fact substrate
- **Global Validator**: Full replay

## Determinism Rules

- ✅ **Same inputs → same outputs**: Deterministic normalization
- ✅ **Canonical timestamps**: RFC3339 UTC timestamps
- ✅ **Explicit field ordering**: Explicit field ordering
- ✅ **No time windows**: No time windows
- ✅ **No implicit joins**: No implicit joins
- ✅ **No default assumptions**: No default assumptions

## Usage

### Ingest Event

```bash
python3 hnmp/cli/ingest_hnmp.py \
    --event /path/to/event.json \
    --event-type process \
    --source-agent linux_agent \
    --host-events /var/lib/ransomeye/hnmp/host_events.jsonl \
    --network-events /var/lib/ransomeye/hnmp/network_events.jsonl \
    --process-events /var/lib/ransomeye/hnmp/process_events.jsonl \
    --malware-events /var/lib/ransomeye/hnmp/malware_events.jsonl \
    --correlations /var/lib/ransomeye/hnmp/correlations.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output normalized_event.json
```

### Correlate Events

```bash
python3 hnmp/cli/correlate_hnmp.py \
    --source-event-id <source-event-uuid> \
    --source-type process \
    --target-event-id <target-event-uuid> \
    --target-type network \
    --host-events /var/lib/ransomeye/hnmp/host_events.jsonl \
    --network-events /var/lib/ransomeye/hnmp/network_events.jsonl \
    --process-events /var/lib/ransomeye/hnmp/process_events.jsonl \
    --malware-events /var/lib/ransomeye/hnmp/malware_events.jsonl \
    --correlations /var/lib/ransomeye/hnmp/correlations.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output correlation.json
```

### Programmatic API

```python
from api.hnmp_api import HNMPAPI

api = HNMPAPI(
    host_events_path=Path('/var/lib/ransomeye/hnmp/host_events.jsonl'),
    network_events_path=Path('/var/lib/ransomeye/hnmp/network_events.jsonl'),
    process_events_path=Path('/var/lib/ransomeye/hnmp/process_events.jsonl'),
    malware_events_path=Path('/var/lib/ransomeye/hnmp/malware_events.jsonl'),
    correlations_path=Path('/var/lib/ransomeye/hnmp/correlations.jsonl'),
    ledger_path=Path('/var/lib/ransomeye/audit/ledger.jsonl'),
    ledger_key_dir=Path('/var/lib/ransomeye/audit/keys')
)

# Ingest event
normalized = api.ingest_event(
    raw_event=raw_event_dict,
    event_type='process',
    source_agent='linux_agent'
)

# Correlate events
correlation = api.correlate_events(
    source_event_id='<source-uuid>',
    source_type='process',
    target_event_id='<target-uuid>',
    target_type='network'
)
```

## File Structure

```
hnmp/
├── schema/
│   ├── host-event.schema.json          # Frozen JSON schema for host events
│   ├── network-event.schema.json       # Frozen JSON schema for network events
│   ├── process-event.schema.json       # Frozen JSON schema for process events
│   ├── malware-event.schema.json      # Frozen JSON schema for malware events
│   └── hnmp-correlation.schema.json   # Frozen JSON schema for correlations
├── engine/
│   ├── __init__.py
│   ├── host_normalizer.py             # Canonical host event normalization
│   ├── network_normalizer.py          # Canonical network event normalization
│   ├── process_normalizer.py          # Canonical process event normalization
│   ├── malware_normalizer.py         # Canonical malware event normalization
│   └── correlator.py                 # Strictly factual event correlation
├── storage/
│   ├── __init__.py
│   └── hnmp_store.py                 # Immutable HNMP event storage
├── api/
│   ├── __init__.py
│   └── hnmp_api.py                   # HNMP API with audit integration
├── cli/
│   ├── __init__.py
│   ├── ingest_hnmp.py                # Ingest HNMP event CLI
│   └── correlate_hnmp.py             # Correlate HNMP events CLI
└── README.md                         # This file
```

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **Audit Ledger**: Required for audit trail (separate subsystem)

## Security Considerations

1. **No Decision Logic**: No decision logic exists
2. **No Scoring**: No scoring logic
3. **No ML or Heuristics**: No ML or heuristics
4. **Immutable Storage**: All events are immutable
5. **Deterministic**: Same inputs always produce same outputs

## Limitations

1. **No Enforcement**: No enforcement actions
2. **No Alerting**: No alerting logic
3. **No Aggregation**: No aggregation logic
4. **No Inference**: No implicit inference
5. **Facts Only**: Produces facts only, never conclusions

## Future Enhancements

- Advanced event normalization
- Enhanced correlation methods
- Event lifecycle management
- Event query and retrieval
- Event replay and reconstruction

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye HNMP Engine documentation.
