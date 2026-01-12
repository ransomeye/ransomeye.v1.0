# RansomEye Threat Correlation Graph Engine

**AUTHORITATIVE:** Deterministic graph engine for modeling entities and relationships across the enterprise

## Overview

The RansomEye Threat Correlation Graph Engine models **entities and relationships** across the enterprise to infer campaigns, lateral movement, and coordinated activity. It provides **relationship intelligence** through deterministic graph traversal and explicit inference rules.

## Core Principles

### Immutable Graph

**CRITICAL**: Graph is immutable:

- ✅ **No mutation**: Entities and edges cannot be modified after creation
- ✅ **Typed edges**: All edges have explicit types
- ✅ **Directed edges**: All edges are directed (source -> target)
- ✅ **Timestamped**: All edges have timestamps
- ✅ **Deterministic**: Same inputs always produce same graph

### Explainable Relationships

**CRITICAL**: All relationships are explainable:

- ✅ **Explicit inference**: All inference logic is explicit (no ML yet)
- ✅ **Inference explanation**: Every edge has explanation of how it was inferred
- ✅ **No implicit edges**: All edges must be explicitly created
- ✅ **No opaque inference**: All inference rules are transparent

### Deterministic Campaign Inference

**CRITICAL**: Campaign inference is deterministic:

- ✅ **Explicit rules**: Graph traversal rules are explicit
- ✅ **No randomness**: Same graph always produces same inferences
- ✅ **Explainable paths**: All inferred paths are explainable
- ✅ **No runtime state**: Graph does not depend on runtime state

### Lossless Neo4j Export

**CRITICAL**: Neo4j export is lossless:

- ✅ **No information loss**: All graph data is preserved
- ✅ **Deterministic**: Same graph always produces same export
- ✅ **No runtime dependency**: No Neo4j runtime required
- ✅ **Multiple formats**: Cypher, JSON, CSV export formats

## Entity Graph

### Entity Types

Supported entity types:

- **Host**: Physical or virtual hosts
- **User**: User accounts
- **Process**: Running processes
- **File**: Files and file system objects
- **IP**: IP addresses
- **Domain**: Domain names
- **Malware**: Malware families and variants
- **Incident**: Security incidents
- **EvidenceArtifact**: Forensic evidence artifacts

### Edge Types

Supported edge types (directed):

- **HOSTED_ON**: Entity hosted on host
- **EXECUTED_BY**: Process executed by user
- **ACCESSED_BY**: Resource accessed by entity
- **COMMUNICATES_WITH**: Network communication
- **CONTAINS**: Containment relationship
- **BELONGS_TO**: Membership relationship
- **TRIGGERED**: Causal relationship
- **CORRELATED_WITH**: Correlation relationship
- **EVIDENCE_OF**: Evidence relationship
- **PART_OF_CAMPAIGN**: Campaign membership
- **LATERAL_MOVEMENT**: Lateral movement relationship
- **DATA_FLOW**: Data flow relationship

### Graph Properties

- **Typed**: All edges have explicit types
- **Directed**: All edges are directed (source -> target)
- **Timestamped**: All edges have timestamps
- **Immutable**: Entities and edges cannot be modified after creation

## Campaign Inference

### Deterministic Graph Traversal

Campaign inference uses **deterministic graph traversal**:

- **Breadth-first search**: Deterministic traversal order
- **Explicit rules**: Traversal rules are explicit
- **Depth limits**: Maximum traversal depth (deterministic)
- **Cycle detection**: Cycles are detected and avoided

### Inference Rules

Campaign inference rules:

1. **Start from incident**: Begin traversal from incident entity
2. **Traverse relationships**: Follow all outgoing and incoming edges
3. **Collect related entities**: Collect all entities within N hops
4. **Explain paths**: Generate explainable path explanations

### Explainable Paths

All inferred paths are **explainable**:

- **Path explanation**: Human-readable explanation of path
- **Edge explanations**: Explanation for each edge in path
- **Entity labels**: Human-readable entity labels in path

## Neo4j Export

### Export Formats

Graph can be exported to Neo4j-compatible formats:

1. **Cypher**: Neo4j Cypher CREATE statements
2. **JSON**: Neo4j JSON import format
3. **CSV**: Neo4j CSV import format (nodes and edges)

### Lossless Export

Export is **lossless**:

- **All entities**: All entities are exported
- **All edges**: All edges are exported
- **All properties**: All entity and edge properties are preserved
- **All metadata**: Timestamps, explanations, and metadata preserved

### No Runtime Dependency

Export does **not require Neo4j runtime**:

- **Offline export**: Export can be performed offline
- **Deterministic**: Same graph always produces same export
- **Import-ready**: Exported files can be imported into Neo4j

## ML Confidence Placeholder

### Foundation Only

ML confidence placeholder provides:

- **Schema**: Schema for confidence scores
- **No prediction**: No prediction logic yet (future phase)
- **Placeholder structure**: Structure ready for ML confidence predictor

### Confidence Schema

Confidence scores are structured as:

- **confidence_defined**: Whether confidence scores are defined
- **schema_version**: Version of confidence schema
- **confidence_scores**: Dictionary of confidence scores (0-1)

## Assurance Integration

### Audit Ledger Integration

**Every graph mutation** emits an Audit Ledger entry:

- **graph_entity_added**: Entity addition logged
- **graph_edge_added**: Edge addition logged
- **No silent mutations**: All mutations are logged

### Global Validator Compatibility

Global Validator can:

- **Rebuild graph**: Rebuild graph from audit ledger
- **Verify edge completeness**: Verify all edges are present
- **Detect missing relationships**: Detect missing relationships
- **Verify graph integrity**: Verify graph matches ledger

## Usage

### Build Graph

```bash
python3 threat-graph/cli/build_graph.py \
    --entities /path/to/entities.json \
    --edges /path/to/edges.json \
    --graph-store /var/lib/ransomeye/graph/graph.json \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output result.json
```

### Infer Campaign

```bash
python3 threat-graph/cli/build_graph.py \
    --graph-store /var/lib/ransomeye/graph/graph.json \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --infer-campaign <incident-entity-id> \
    --output campaign-inference.json
```

### Export to Neo4j

```bash
python3 threat-graph/cli/build_graph.py \
    --graph-store /var/lib/ransomeye/graph/graph.json \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --export-neo4j /path/to/export.cypher \
    --export-format cypher
```

### Programmatic API

```python
from api.graph_api import GraphAPI

api = GraphAPI(
    graph_store_path=Path('/var/lib/ransomeye/graph/graph.json'),
    ledger_path=Path('/var/lib/ransomeye/audit/ledger.jsonl'),
    ledger_key_dir=Path('/var/lib/ransomeye/audit/keys')
)

# Add entity
entity = api.add_entity(
    entity_type='Host',
    entity_label='host-1.example.com',
    properties={'ip': '192.168.1.100'},
    added_by='analyst'
)

# Add edge
edge = api.add_edge(
    source_entity_id=entity['entity_id'],
    target_entity_id=target_entity_id,
    edge_type='COMMUNICATES_WITH',
    edge_label='Network communication',
    properties={},
    timestamp='2025-01-10T12:00:00Z',
    inference_explanation='Detected network connection in logs',
    added_by='analyst'
)

# Infer campaign
campaign = api.infer_campaign(incident_entity_id='incident-uuid')

# Export to Neo4j
api.export_neo4j(Path('/path/to/export.cypher'), format='cypher')
```

## Entity Format

```json
{
  "entity_type": "Host",
  "entity_label": "host-1.example.com",
  "properties": {
    "ip": "192.168.1.100",
    "os": "Linux"
  }
}
```

## Edge Format

```json
{
  "source_entity_id": "entity-uuid-1",
  "target_entity_id": "entity-uuid-2",
  "edge_type": "COMMUNICATES_WITH",
  "edge_label": "Network communication",
  "properties": {
    "protocol": "TCP",
    "port": 443
  },
  "timestamp": "2025-01-10T12:00:00Z",
  "inference_explanation": "Detected network connection in packet capture"
}
```

## File Structure

```
threat-graph/
├── schema/
│   ├── entity.schema.json          # Frozen JSON schema for entities
│   └── edge.schema.json            # Frozen JSON schema for edges
├── engine/
│   ├── __init__.py
│   ├── graph_builder.py            # Immutable graph construction
│   └── campaign_inference.py       # Deterministic campaign inference
├── export/
│   ├── __init__.py
│   └── neo4j_exporter.py           # Lossless Neo4j export
├── api/
│   ├── __init__.py
│   └── graph_api.py                # Graph API with audit integration
├── cli/
│   ├── __init__.py
│   └── build_graph.py              # Graph builder CLI
└── README.md                       # This file
```

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **Audit Ledger**: Required for audit trail (separate subsystem)

## Security Considerations

1. **Immutable Graph**: Entities and edges cannot be modified after creation
2. **Explicit Inference**: All inference rules are explicit and explainable
3. **Audit Trail**: All graph mutations are logged to audit ledger
4. **Deterministic**: All operations are deterministic (no randomness)
5. **No Runtime State**: Graph does not depend on runtime state

## Limitations

1. **No UI**: Phase C2 provides computation only, no UI
2. **No Alerts**: No alerting or notification logic
3. **No Automation**: No automated response based on graph
4. **No ML Prediction**: ML confidence is placeholder only (no prediction logic)

## Future Enhancements

- Real-time graph updates
- Advanced graph algorithms (PageRank, community detection)
- ML-based confidence prediction
- Integration with threat intelligence
- Automated relationship inference

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye Threat Correlation Graph Engine documentation.
