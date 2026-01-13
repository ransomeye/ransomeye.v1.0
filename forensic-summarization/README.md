# RansomEye v1.0 Forensic Summarization Engine

**AUTHORITATIVE:** Deterministic forensic summarization for post-incident analysis

## Overview

The RansomEye Forensic Summarization Engine reconstructs attacker behavior step-by-step, explains what happened and how it unfolded, and produces machine-verifiable summaries with explicit evidence linking.

## Core Principles

### Deterministic Summarization
- **No speculation**: Only facts from evidence
- **No probabilities**: No confidence scores or likelihoods
- **No adjectives**: Factual statements only
- **No external intel**: Only evidence from database
- **Replayable**: Same inputs always produce same summary

### Evidence-Linked Claims
- **Event references**: Every claim references `event_id`
- **Table references**: Every claim references source table
- **Timestamp references**: Every claim references `observed_at`
- **No unsupported claims**: No statement without evidence

### Post-Incident Only
- **Not real-time**: Summarization occurs after incident is identified
- **Complete evidence**: All evidence must be available
- **Immutable summary**: Summary does not change once generated
- **Auditable**: Summary generation is logged

### No LLM, No ML
- **Rule-based**: Explicit rules for behavior reconstruction
- **Pattern matching**: Deterministic pattern matching
- **Graph traversal**: Deterministic graph algorithms
- **No inference**: No probabilistic or ML-based inference

## Module Structure

```
forensic-summarization/
├── __init__.py
├── README.md
├── FORENSIC_SUMMARIZATION_ARCHITECTURE.md
├── engine/
│   ├── __init__.py
│   ├── behavioral_chain_builder.py       # Process/file/persistence chain reconstruction
│   ├── temporal_phase_detector.py        # Phase boundary detection
│   ├── evidence_linker.py                 # Evidence linking and validation
│   └── summary_generator.py               # Summary text generation
├── api/
│   ├── __init__.py
│   └── summarization_api.py               # Main API for summarization
└── cli/
    ├── __init__.py
    └── generate_summary.py                # CLI tool for summary generation
```

## Usage

### API Usage

```python
from forensic_summarization.api import SummarizationAPI
import psycopg2

# Get database connection
conn = psycopg2.connect(...)

# Initialize API
api = SummarizationAPI(conn)

# Generate summary
summary = api.generate_summary(
    incident_id="incident_123e4567-e89b-12d3-a456-426614174000",
    output_format="all"  # 'json', 'text', 'graph', or 'all'
)

# Access outputs
json_summary = summary['json_summary']
text_summary = summary['text_summary']
graph_metadata = summary['graph_metadata']
```

### CLI Usage

```bash
# Generate summary (all formats)
python3 -m forensic_summarization.cli.generate_summary \
    --incident-id "incident_123e4567-e89b-12d3-a456-426614174000" \
    --output-format all \
    --output-file summary.json

# Generate JSON only
python3 -m forensic_summarization.cli.generate_summary \
    --incident-id "incident_123e4567-e89b-12d3-a456-426614174000" \
    --output-format json \
    --json-only
```

## Data Sources

### Database Tables (Read-Only via Views)

- `evidence` - Links events to incidents
- `process_activity` - Process creation, termination, injection
- `file_activity` - File create, modify, delete, encrypt
- `persistence` - Persistence mechanism establishment
- `network_intent` - DNS queries, connection attempts
- `dpi_flows` - Network flows (for correlation)
- `dns` - DNS queries/responses (for correlation)
- `raw_events` - Source event data (if not normalized)
- `incidents` - Incident metadata

### View Usage

All database reads use read-only views (per data-plane hardening):
- `v_process_activity_forensics`
- `v_file_activity_forensics`
- `v_persistence_forensics`
- `v_network_intent_forensics`
- `v_dpi_flows_forensics`
- `v_dns_forensics`

## Behavioral Chains

### Process Lineage
- Reconstructs process tree from `parent_pid` → `process_pid` relationships
- Identifies root process (earliest `PROCESS_START`)
- Links child processes to parents
- Marks gaps (missing parent processes)

### File Modification Chains
- Groups file operations by `file_path`
- Orders operations by `observed_at` (temporal order)
- Detects entropy changes (encryption indicators)

### Persistence Establishment
- Sequences persistence mechanisms by `persistence_type` and `observed_at`
- Tracks `target_path` and `target_command_line`

### Network Intent Progression
- Sequences network activities (DNS queries, connection attempts)
- Correlates `network_intent` with `dpi_flows` (by IP, port, timestamp ±5 seconds)

### Lateral Preparation Indicators
- Credential access detection (LSASS access)
- Network scanning detection (>10 connection attempts to different hosts)
- Service discovery detection (>10 DNS queries to different domains)

## Temporal Phases

### Phase Detection
1. **INITIAL_EXECUTION**: First process creation, first file access
2. **EXPANSION**: Process spawning, file modifications, network activity
3. **PERSISTENCE**: Persistence mechanism establishment
4. **EXFILTRATION_PREP**: Network connections, data collection, encryption

### Phase Boundaries
- **Explicit rules**: Phase boundaries determined by explicit rules (not heuristics)
- **No overlap**: Phases do not overlap (explicit boundaries)
- **Complete coverage**: All events assigned to phases

## Evidence Linking

### Claim Validation
- Every claim must reference `event_id`, `table`, `observed_at`
- Claims without evidence are rejected (not included in summary)
- Evidence matching by exact `event_id`, `table`, `observed_at`

## Output Formats

### JSON Output
Structured JSON with all behavioral chains, temporal phases, and evidence links.

### Text Output
Plain text narrative (template-based, deterministic, no LLM):
- Header (incident ID, machine ID, time range)
- Timeline (all events in chronological order)
- Behavioral Chains (process lineage, file modification, persistence, network intent)
- Temporal Phases (phase boundaries and event counts)
- Evidence References (summary by table)

### Graph Metadata
Graph structure with nodes (entities) and edges (relationships):
- **Node Types**: PROCESS, FILE, PERSISTENCE, NETWORK, MACHINE
- **Edge Types**: PARENT_OF, CREATED, MODIFIED, ESTABLISHED, QUERIED, CONNECTED_TO
- All nodes and edges include evidence references

## Configuration

### Environment Variables

- `RANSOMEYE_DB_HOST`: Database host (default: localhost)
- `RANSOMEYE_DB_PORT`: Database port (default: 5432)
- `RANSOMEYE_DB_NAME`: Database name (default: ransomeye)
- `RANSOMEYE_DB_USER`: Database user (default: ransomeye_forensics)
- `RANSOMEYE_DB_PASSWORD`: Database password
- `RANSOMEYE_LATERAL_NETWORK_SCAN_THRESHOLD`: Network scan threshold (default: 10)
- `RANSOMEYE_LATERAL_DNS_SCAN_THRESHOLD`: DNS scan threshold (default: 10)
- `RANSOMEYE_LATERAL_TIME_WINDOW_SECONDS`: Lateral detection time window (default: 60)

## Limitations

1. **Evidence Completeness**: Summary quality depends on evidence completeness
2. **Temporal Ordering**: Phase boundaries assume events are temporally ordered
3. **Process Lineage Gaps**: Missing parent processes result in incomplete lineage
4. **File Path Normalization**: Case-sensitive on Linux, case-insensitive on Windows
5. **Network Correlation Window**: ±5 second time window for network intent/DPI flow correlation
6. **Lateral Preparation Detection**: Uses explicit thresholds (>10 connections, >10 DNS queries)
7. **No Cross-Host Correlation**: Summary is per-incident (single machine)
8. **No Intent Inference**: Summary does not infer attacker intent
9. **No Mitigation Recommendations**: Summary does not provide mitigation advice
10. **Deterministic but Not Optimal**: Summary may have suboptimal phase boundaries

## Dependencies

- `psycopg2` - PostgreSQL database connection
- Standard library: `json`, `uuid`, `datetime`, `collections`, `pathlib`

---

**AUTHORITATIVE**: This README is the single authoritative source for Forensic Summarization Engine usage.

**STATUS**: Phase B forensic summarization implemented. Ready for Phase C.
