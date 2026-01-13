# RansomEye v1.0 Forensic Summarization Architecture

**AUTHORITATIVE:** Deterministic forensic summarization engine for post-incident analysis

## Overview

This document defines the architecture for a deterministic forensic summarization engine that reconstructs attacker behavior step-by-step, explains what happened and how it unfolded, and produces machine-verifiable summaries with explicit evidence linking.

## Core Principles

### Deterministic Summarization

**CRITICAL**: Summarization is deterministic:

- ✅ **No speculation**: Only facts from evidence
- ✅ **No probabilities**: No confidence scores or likelihoods
- ✅ **No adjectives**: Factual statements only
- ✅ **No external intel**: Only evidence from database
- ✅ **Replayable**: Same inputs always produce same summary

### Evidence-Linked Claims

**CRITICAL**: Every claim links to evidence:

- ✅ **Event references**: Every claim references `event_id`
- ✅ **Table references**: Every claim references source table
- ✅ **Timestamp references**: Every claim references `observed_at`
- ✅ **No unsupported claims**: No statement without evidence

### Post-Incident Only

**CRITICAL**: Summarization is post-incident:

- ✅ **Not real-time**: Summarization occurs after incident is identified
- ✅ **Complete evidence**: All evidence must be available
- ✅ **Immutable summary**: Summary does not change once generated
- ✅ **Auditable**: Summary generation is logged

### No LLM, No ML

**CRITICAL**: Summarization uses deterministic algorithms:

- ✅ **Rule-based**: Explicit rules for behavior reconstruction
- ✅ **Pattern matching**: Deterministic pattern matching
- ✅ **Graph traversal**: Deterministic graph algorithms
- ✅ **No inference**: No probabilistic or ML-based inference

---

## Architecture Design

### Module Structure

```
forensic-summarization/
├── __init__.py
├── README.md
├── schema/
│   ├── forensic-summary.schema.json       # Summary output schema
│   ├── behavioral-chain.schema.json       # Behavioral chain schema
│   ├── temporal-phase.schema.json         # Temporal phase schema
│   └── evidence-link.schema.json         # Evidence link schema
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

### Data Flow

```
Incident ID
    ↓
Evidence Query (evidence table)
    ↓
Normalized Event Retrieval (process_activity, file_activity, persistence, network_intent, dpi_flows, dns)
    ↓
Behavioral Chain Reconstruction
    ↓
Temporal Phase Detection
    ↓
Evidence Linking & Validation
    ↓
Summary Generation (JSON + Text + Graph)
```

---

## STEP 1 — DATA SOURCES (TABLES/VIEWS)

### Primary Data Sources

**Evidence Table** (`evidence`):
- **Purpose**: Links events to incidents
- **Columns Used**: `incident_id`, `event_id`, `evidence_type`, `normalized_table_name`, `normalized_row_id`, `observed_at`
- **Query Pattern**: `SELECT * FROM evidence WHERE incident_id = $1 ORDER BY observed_at ASC`

**Normalized Tables** (via `normalized_table_name` and `normalized_row_id`):
- **process_activity**: Process creation, termination, injection, modification
- **file_activity**: File create, modify, delete, read, execute, encrypt
- **persistence**: Persistence mechanism establishment (registry, service, scheduled task)
- **network_intent**: DNS queries, connection attempts, listen operations
- **dpi_flows**: Network flows observed by DPI probe
- **dns**: DNS queries and responses observed by DPI probe
- **deception**: Honeypot triggers, decoy access

**Raw Events Table** (`raw_events`):
- **Purpose**: Source event data (if evidence not normalized)
- **Columns Used**: `event_id`, `observed_at`, `payload`, `machine_id`, `component_instance_id`
- **Query Pattern**: `SELECT * FROM raw_events WHERE event_id = ANY($1::uuid[])`

**Incidents Table** (`incidents`):
- **Purpose**: Incident metadata
- **Columns Used**: `incident_id`, `machine_id`, `first_observed_at`, `last_observed_at`, `current_stage`, `confidence_score`
- **Query Pattern**: `SELECT * FROM incidents WHERE incident_id = $1`

**Machines Table** (`machines`):
- **Purpose**: Machine metadata
- **Columns Used**: `machine_id`, `hostname` (if available)
- **Query Pattern**: `SELECT * FROM machines WHERE machine_id = $1`

### View Usage

**Views Used** (from data-plane hardening):
- **Read-only views**: All reads via views (enforced by RBAC)
- **View naming**: `v_<table>_forensics` (e.g., `v_process_activity_forensics`)
- **View filters**: Filter by `machine_id` and `observed_at` time range

**Example Views**:
```sql
CREATE VIEW v_process_activity_forensics AS
SELECT 
    id,
    event_id,
    machine_id,
    component_instance_id,
    observed_at,
    activity_type,
    process_pid,
    parent_pid,
    process_name,
    process_path,
    command_line,
    user_name,
    user_id,
    target_pid,
    target_process_name,
    exit_code
FROM process_activity
WHERE observed_at >= (SELECT first_observed_at FROM incidents WHERE incident_id = $1)
  AND observed_at <= (SELECT last_observed_at FROM incidents WHERE incident_id = $1)
WITH CHECK OPTION;
```

---

## STEP 2 — DETERMINISTIC SUMMARIZATION ALGORITHM

### Algorithm Overview

**Input**: `incident_id` (UUID)

**Output**: Forensic summary (JSON, text, graph metadata)

**Steps**:
1. **Load Evidence**: Query `evidence` table for all evidence linked to incident
2. **Load Events**: Query normalized tables for all evidence events
3. **Build Behavioral Chains**: Reconstruct process, file, persistence, network chains
4. **Detect Temporal Phases**: Identify phase boundaries (initial execution, expansion, persistence, exfiltration prep)
5. **Link Evidence**: Validate all claims have evidence references
6. **Generate Summary**: Produce JSON, text, and graph metadata outputs

### 1. Behavioral Chain Reconstruction

#### Process Lineage Reconstruction

**Algorithm**: Build process tree from `process_activity` events

**Steps**:
1. **Root Process Identification**: Find earliest `PROCESS_START` event (by `observed_at`)
2. **Parent-Child Linking**: Link processes by `parent_pid` → `process_pid`
3. **Tree Construction**: Build directed tree (parent → child)
4. **Chain Extraction**: Extract chains from root to leaf processes

**Deterministic Rules**:
- **Root Selection**: Earliest `PROCESS_START` event is root (by `observed_at`)
- **Parent Linking**: `parent_pid` must match `process_pid` of earlier event
- **Chain Ordering**: Chains ordered by `observed_at` (temporal order)
- **Gap Handling**: Missing parent processes are noted (not inferred)

**Output Format**:
```json
{
  "chain_type": "process_lineage",
  "root_process": {
    "process_pid": 1234,
    "process_name": "cmd.exe",
    "process_path": "C:\\Windows\\System32\\cmd.exe",
    "command_line": "cmd.exe /c powershell.exe",
    "observed_at": "2025-01-12T12:00:00Z",
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "table": "process_activity"
  },
  "child_processes": [
    {
      "process_pid": 5678,
      "parent_pid": 1234,
      "process_name": "powershell.exe",
      "process_path": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
      "command_line": "powershell.exe -EncodedCommand ...",
      "observed_at": "2025-01-12T12:00:05Z",
      "event_id": "660e8400-e29b-41d4-a716-446655440001",
      "table": "process_activity"
    }
  ],
  "chain_length": 2,
  "time_span_seconds": 5
}
```

#### File Modification Chains

**Algorithm**: Build file modification sequence from `file_activity` events

**Steps**:
1. **File Grouping**: Group events by `file_path`
2. **Temporal Ordering**: Order events by `observed_at` (ascending)
3. **Chain Construction**: Build sequence of file operations (CREATE → MODIFY → DELETE)
4. **Entropy Detection**: Identify `FILE_ENCRYPT` events (entropy change indicators)

**Deterministic Rules**:
- **File Matching**: Exact `file_path` match (case-sensitive on Linux, case-insensitive on Windows)
- **Operation Ordering**: Operations ordered by `observed_at` (temporal order)
- **Entropy Detection**: `entropy_change_indicator = TRUE` indicates encryption
- **Gap Handling**: Missing operations are noted (not inferred)

**Output Format**:
```json
{
  "chain_type": "file_modification",
  "file_path": "C:\\Users\\user\\Documents\\file.txt",
  "operations": [
    {
      "activity_type": "FILE_CREATE",
      "observed_at": "2025-01-12T12:00:10Z",
      "event_id": "770e8400-e29b-41d4-a716-446655440002",
      "table": "file_activity",
      "process_pid": 5678,
      "process_name": "powershell.exe"
    },
    {
      "activity_type": "FILE_MODIFY",
      "observed_at": "2025-01-12T12:00:15Z",
      "entropy_change_indicator": true,
      "event_id": "880e8400-e29b-41d4-a716-446655440003",
      "table": "file_activity",
      "process_pid": 5678,
      "process_name": "powershell.exe"
    }
  ],
  "chain_length": 2,
  "time_span_seconds": 5,
  "encryption_detected": true
}
```

#### Persistence Establishment Chains

**Algorithm**: Build persistence mechanism sequence from `persistence` events

**Steps**:
1. **Persistence Grouping**: Group events by `persistence_type`
2. **Temporal Ordering**: Order events by `observed_at` (ascending)
3. **Chain Construction**: Build sequence of persistence mechanisms
4. **Target Tracking**: Track `target_path` and `target_command_line`

**Deterministic Rules**:
- **Persistence Types**: `SCHEDULED_TASK`, `SERVICE`, `REGISTRY_RUN_KEY`, `STARTUP_FOLDER`, etc.
- **Ordering**: Persistence events ordered by `observed_at` (temporal order)
- **Target Matching**: `target_path` must match process path from `process_activity`
- **Gap Handling**: Missing persistence mechanisms are noted (not inferred)

**Output Format**:
```json
{
  "chain_type": "persistence_establishment",
  "persistence_mechanisms": [
    {
      "persistence_type": "REGISTRY_RUN_KEY",
      "persistence_key": "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run\\MaliciousService",
      "target_path": "C:\\temp\\malware.exe",
      "target_command_line": "C:\\temp\\malware.exe -persist",
      "observed_at": "2025-01-12T12:00:20Z",
      "event_id": "990e8400-e29b-41d4-a716-446655440004",
      "table": "persistence",
      "process_pid": 5678,
      "process_name": "powershell.exe"
    }
  ],
  "chain_length": 1,
  "time_span_seconds": 0
}
```

#### Network Intent Progression

**Algorithm**: Build network activity sequence from `network_intent` and `dpi_flows` events

**Steps**:
1. **Intent Grouping**: Group events by `intent_type` (DNS_QUERY, CONNECTION_ATTEMPT, LISTEN)
2. **Temporal Ordering**: Order events by `observed_at` (ascending)
3. **Flow Correlation**: Correlate `network_intent` with `dpi_flows` (by IP, port, timestamp)
4. **Chain Construction**: Build sequence of network activities

**Deterministic Rules**:
- **Intent Types**: `DNS_QUERY`, `CONNECTION_ATTEMPT`, `LISTEN`
- **Ordering**: Network events ordered by `observed_at` (temporal order)
- **Flow Correlation**: Match `network_intent` to `dpi_flows` by `remote_host`/`remote_ip`, `remote_port`, time window (±5 seconds)
- **Gap Handling**: Missing network activities are noted (not inferred)

**Output Format**:
```json
{
  "chain_type": "network_intent_progression",
  "network_activities": [
    {
      "intent_type": "DNS_QUERY",
      "dns_query_name": "malicious-domain.com",
      "observed_at": "2025-01-12T12:00:25Z",
      "event_id": "aa0e8400-e29b-41d4-a716-446655440005",
      "table": "network_intent",
      "process_pid": 5678,
      "process_name": "powershell.exe"
    },
    {
      "intent_type": "CONNECTION_ATTEMPT",
      "remote_host": "192.168.1.100",
      "remote_port": 443,
      "protocol": "TCP",
      "observed_at": "2025-01-12T12:00:30Z",
      "event_id": "bb0e8400-e29b-41d4-a716-446655440006",
      "table": "network_intent",
      "process_pid": 5678,
      "process_name": "powershell.exe",
      "correlated_flow": {
        "flow_id": "cc0e8400-e29b-41d4-a716-446655440007",
        "table": "dpi_flows",
        "bytes_sent": 1024,
        "bytes_received": 2048
      }
    }
  ],
  "chain_length": 2,
  "time_span_seconds": 5
}
```

#### Lateral Preparation Indicators

**Algorithm**: Detect lateral movement preparation from process, file, and network events

**Steps**:
1. **Credential Access Detection**: Identify credential access patterns (LSASS access, registry credential access)
2. **Network Scanning Detection**: Identify network scanning patterns (multiple connection attempts to different hosts)
3. **Service Discovery Detection**: Identify service discovery patterns (multiple DNS queries, port scans)
4. **Chain Construction**: Build sequence of lateral preparation activities

**Deterministic Rules**:
- **Credential Access**: Process accessing `lsass.exe`, registry keys containing "password", "credential"
- **Network Scanning**: >10 connection attempts to different IPs within 60 seconds
- **Service Discovery**: >10 DNS queries to different domains within 60 seconds
- **Gap Handling**: Missing lateral preparation activities are noted (not inferred)

**Output Format**:
```json
{
  "chain_type": "lateral_preparation",
  "indicators": [
    {
      "indicator_type": "CREDENTIAL_ACCESS",
      "description": "Process accessed LSASS memory",
      "process_pid": 5678,
      "process_name": "powershell.exe",
      "target_pid": 1234,
      "target_process_name": "lsass.exe",
      "observed_at": "2025-01-12T12:00:35Z",
      "event_id": "dd0e8400-e29b-41d4-a716-446655440008",
      "table": "process_activity"
    },
    {
      "indicator_type": "NETWORK_SCANNING",
      "description": "Multiple connection attempts to different hosts",
      "connection_attempts": 15,
      "unique_hosts": 10,
      "time_window_seconds": 60,
      "observed_at": "2025-01-12T12:01:00Z",
      "event_ids": ["ee0e8400-...", "ff0e8400-..."],
      "table": "network_intent"
    }
  ],
  "chain_length": 2,
  "time_span_seconds": 25
}
```

### 2. Temporal Graph Summarization

#### Phase Boundary Detection

**Algorithm**: Detect phase boundaries from behavioral chains

**Phases**:
1. **Initial Execution**: First process creation, first file access
2. **Expansion**: Process spawning, file modifications, network activity
3. **Persistence**: Persistence mechanism establishment
4. **Exfiltration Prep**: Network connections, data collection, encryption

**Deterministic Rules**:
- **Initial Execution**: Earliest `PROCESS_START` event (by `observed_at`)
- **Expansion**: First process spawn (child process creation), first file modification, first network activity
- **Persistence**: First persistence mechanism establishment
- **Exfiltration Prep**: First network connection to external host, first file encryption

**Phase Detection Algorithm**:
```python
def detect_phases(behavioral_chains):
    phases = []
    
    # Phase 1: Initial Execution
    initial_execution = find_earliest_event(behavioral_chains, 'PROCESS_START')
    phases.append({
        'phase': 'INITIAL_EXECUTION',
        'start_time': initial_execution['observed_at'],
        'end_time': find_first_expansion_event(behavioral_chains, initial_execution['observed_at']),
        'events': [initial_execution]
    })
    
    # Phase 2: Expansion
    expansion_start = phases[0]['end_time']
    expansion_end = find_first_persistence_event(behavioral_chains, expansion_start)
    phases.append({
        'phase': 'EXPANSION',
        'start_time': expansion_start,
        'end_time': expansion_end,
        'events': find_events_in_range(behavioral_chains, expansion_start, expansion_end)
    })
    
    # Phase 3: Persistence
    persistence_start = expansion_end
    persistence_end = find_first_exfiltration_prep_event(behavioral_chains, persistence_start)
    phases.append({
        'phase': 'PERSISTENCE',
        'start_time': persistence_start,
        'end_time': persistence_end,
        'events': find_events_in_range(behavioral_chains, persistence_start, persistence_end)
    })
    
    # Phase 4: Exfiltration Prep
    exfiltration_start = persistence_end
    exfiltration_end = find_last_event(behavioral_chains)['observed_at']
    phases.append({
        'phase': 'EXFILTRATION_PREP',
        'start_time': exfiltration_start,
        'end_time': exfiltration_end,
        'events': find_events_in_range(behavioral_chains, exfiltration_start, exfiltration_end)
    })
    
    return phases
```

**Output Format**:
```json
{
  "temporal_phases": [
    {
      "phase": "INITIAL_EXECUTION",
      "start_time": "2025-01-12T12:00:00Z",
      "end_time": "2025-01-12T12:00:05Z",
      "duration_seconds": 5,
      "event_count": 1,
      "events": [
        {
          "event_id": "550e8400-e29b-41d4-a716-446655440000",
          "table": "process_activity",
          "observed_at": "2025-01-12T12:00:00Z"
        }
      ]
    },
    {
      "phase": "EXPANSION",
      "start_time": "2025-01-12T12:00:05Z",
      "end_time": "2025-01-12T12:00:20Z",
      "duration_seconds": 15,
      "event_count": 3,
      "events": [...]
    },
    {
      "phase": "PERSISTENCE",
      "start_time": "2025-01-12T12:00:20Z",
      "end_time": "2025-01-12T12:00:25Z",
      "duration_seconds": 5,
      "event_count": 1,
      "events": [...]
    },
    {
      "phase": "EXFILTRATION_PREP",
      "start_time": "2025-01-12T12:00:25Z",
      "end_time": "2025-01-12T12:01:00Z",
      "duration_seconds": 35,
      "event_count": 2,
      "events": [...]
    }
  ],
  "total_duration_seconds": 60,
  "total_event_count": 7
}
```

### 3. Evidence Linking

#### Evidence Link Validation

**Algorithm**: Validate all claims have evidence references

**Steps**:
1. **Claim Extraction**: Extract all claims from behavioral chains and temporal phases
2. **Evidence Matching**: Match claims to evidence entries (by `event_id`, `table`, `observed_at`)
3. **Validation**: Ensure every claim has at least one evidence reference
4. **Link Generation**: Generate evidence links for all claims

**Deterministic Rules**:
- **Event ID Matching**: Claims must reference `event_id` from evidence
- **Table Matching**: Claims must reference `table` from evidence
- **Timestamp Matching**: Claims must reference `observed_at` from evidence
- **No Unsupported Claims**: Claims without evidence are rejected (not included in summary)

**Output Format**:
```json
{
  "evidence_links": [
    {
      "claim": "Process 1234 (cmd.exe) created child process 5678 (powershell.exe)",
      "evidence_references": [
        {
          "event_id": "550e8400-e29b-41d4-a716-446655440000",
          "table": "process_activity",
          "observed_at": "2025-01-12T12:00:00Z",
          "evidence_id": "evt_001",
          "confidence_level": "HIGH"
        },
        {
          "event_id": "660e8400-e29b-41d4-a716-446655440001",
          "table": "process_activity",
          "observed_at": "2025-01-12T12:00:05Z",
          "evidence_id": "evt_002",
          "confidence_level": "HIGH"
        }
      ]
    }
  ],
  "total_claims": 1,
  "total_evidence_references": 2
}
```

### 4. Summary Generation

#### JSON Output (Machine)

**Format**: Structured JSON with all behavioral chains, temporal phases, and evidence links

**Schema**: `forensic-summary.schema.json`

**Example**:
```json
{
  "summary_id": "summary_550e8400-e29b-41d4-a716-446655440000",
  "incident_id": "incident_123e4567-e89b-12d3-a456-426614174000",
  "machine_id": "host-001",
  "generated_at": "2025-01-12T13:00:00Z",
  "time_range": {
    "start_time": "2025-01-12T12:00:00Z",
    "end_time": "2025-01-12T12:01:00Z",
    "duration_seconds": 60
  },
  "behavioral_chains": {
    "process_lineage": [...],
    "file_modification": [...],
    "persistence_establishment": [...],
    "network_intent_progression": [...],
    "lateral_preparation": [...]
  },
  "temporal_phases": [...],
  "evidence_links": [...],
  "statistics": {
    "total_events": 7,
    "total_processes": 2,
    "total_files": 1,
    "total_persistence_mechanisms": 1,
    "total_network_activities": 2
  }
}
```

#### Text Output (Human, Non-LLM)

**Format**: Plain text narrative (deterministic, rule-based)

**Generation Rules**:
- **Section Order**: Header, Timeline, Behavioral Chains, Temporal Phases, Evidence References
- **Factual Statements**: Only facts from evidence (no speculation)
- **Evidence Citations**: Every statement includes `[event_id, table, timestamp]`
- **No Adjectives**: No descriptive adjectives (e.g., "suspicious", "malicious")
- **No Recommendations**: No mitigation advice or recommendations

**Example**:
```
FORENSIC SUMMARY
Incident ID: incident_123e4567-e89b-12d3-a456-426614174000
Machine ID: host-001
Time Range: 2025-01-12T12:00:00Z to 2025-01-12T12:01:00Z
Duration: 60 seconds

TIMELINE
--------
2025-01-12T12:00:00Z: Process 1234 (cmd.exe) started [event_id: 550e8400-..., table: process_activity]
2025-01-12T12:00:05Z: Process 5678 (powershell.exe) started, parent PID 1234 [event_id: 660e8400-..., table: process_activity]
2025-01-12T12:00:10Z: File C:\Users\user\Documents\file.txt created by process 5678 [event_id: 770e8400-..., table: file_activity]
2025-01-12T12:00:15Z: File C:\Users\user\Documents\file.txt modified by process 5678, entropy change detected [event_id: 880e8400-..., table: file_activity]
2025-01-12T12:00:20Z: Registry key HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run\MaliciousService created by process 5678 [event_id: 990e8400-..., table: persistence]
2025-01-12T12:00:25Z: DNS query for malicious-domain.com by process 5678 [event_id: aa0e8400-..., table: network_intent]
2025-01-12T12:00:30Z: Connection attempt to 192.168.1.100:443 by process 5678 [event_id: bb0e8400-..., table: network_intent]

BEHAVIORAL CHAINS
-----------------
Process Lineage:
  Root: Process 1234 (cmd.exe) [event_id: 550e8400-..., table: process_activity, timestamp: 2025-01-12T12:00:00Z]
  Child: Process 5678 (powershell.exe), parent PID 1234 [event_id: 660e8400-..., table: process_activity, timestamp: 2025-01-12T12:00:05Z]

File Modification:
  File: C:\Users\user\Documents\file.txt
  Operations:
    - CREATE [event_id: 770e8400-..., table: file_activity, timestamp: 2025-01-12T12:00:10Z]
    - MODIFY (entropy change) [event_id: 880e8400-..., table: file_activity, timestamp: 2025-01-12T12:00:15Z]

Persistence Establishment:
  Mechanism: REGISTRY_RUN_KEY
  Key: HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run\MaliciousService
  Target: C:\temp\malware.exe [event_id: 990e8400-..., table: persistence, timestamp: 2025-01-12T12:00:20Z]

Network Intent Progression:
  - DNS query: malicious-domain.com [event_id: aa0e8400-..., table: network_intent, timestamp: 2025-01-12T12:00:25Z]
  - Connection attempt: 192.168.1.100:443 [event_id: bb0e8400-..., table: network_intent, timestamp: 2025-01-12T12:00:30Z]

TEMPORAL PHASES
---------------
Phase 1: INITIAL_EXECUTION (2025-01-12T12:00:00Z to 2025-01-12T12:00:05Z, duration: 5 seconds)
  Events: 1
  Description: Initial process execution (cmd.exe)

Phase 2: EXPANSION (2025-01-12T12:00:05Z to 2025-01-12T12:00:20Z, duration: 15 seconds)
  Events: 3
  Description: Process spawning, file operations, persistence establishment

Phase 3: PERSISTENCE (2025-01-12T12:00:20Z to 2025-01-12T12:00:25Z, duration: 5 seconds)
  Events: 1
  Description: Persistence mechanism established

Phase 4: EXFILTRATION_PREP (2025-01-12T12:00:25Z to 2025-01-12T12:01:00Z, duration: 35 seconds)
  Events: 2
  Description: Network activity (DNS query, connection attempt)

EVIDENCE REFERENCES
-------------------
All claims are supported by evidence from the following sources:
  - process_activity: 2 events
  - file_activity: 2 events
  - persistence: 1 event
  - network_intent: 2 events
  Total: 7 events
```

#### Graph Metadata (Nodes + Edges)

**Format**: Graph structure with nodes (entities) and edges (relationships)

**Node Types**:
- **Process**: Process entities (PID, name, path)
- **File**: File entities (path)
- **Persistence**: Persistence mechanism entities (type, key)
- **Network**: Network activity entities (host, port, protocol)
- **Machine**: Machine entities (machine_id)

**Edge Types**:
- **PARENT_OF**: Process parent-child relationship
- **CREATED**: Process created file
- **MODIFIED**: Process modified file
- **ESTABLISHED**: Process established persistence
- **QUERIED**: Process queried DNS
- **CONNECTED_TO**: Process connected to network host

**Output Format**:
```json
{
  "graph_metadata": {
    "nodes": [
      {
        "node_id": "proc_1234",
        "node_type": "PROCESS",
        "properties": {
          "process_pid": 1234,
          "process_name": "cmd.exe",
          "process_path": "C:\\Windows\\System32\\cmd.exe"
        },
        "evidence_references": [
          {
            "event_id": "550e8400-e29b-41d4-a716-446655440000",
            "table": "process_activity",
            "observed_at": "2025-01-12T12:00:00Z"
          }
        ]
      },
      {
        "node_id": "proc_5678",
        "node_type": "PROCESS",
        "properties": {
          "process_pid": 5678,
          "process_name": "powershell.exe",
          "process_path": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
        },
        "evidence_references": [
          {
            "event_id": "660e8400-e29b-41d4-a716-446655440001",
            "table": "process_activity",
            "observed_at": "2025-01-12T12:00:05Z"
          }
        ]
      }
    ],
    "edges": [
      {
        "edge_id": "edge_001",
        "edge_type": "PARENT_OF",
        "source_node_id": "proc_1234",
        "target_node_id": "proc_5678",
        "properties": {
          "observed_at": "2025-01-12T12:00:05Z"
        },
        "evidence_references": [
          {
            "event_id": "660e8400-e29b-41d4-a716-446655440001",
            "table": "process_activity",
            "observed_at": "2025-01-12T12:00:05Z"
          }
        ]
      }
    ]
  }
}
```

---

## STEP 3 — DETERMINISTIC ALGORITHM IMPLEMENTATION

### Behavioral Chain Builder

**Class**: `BehavioralChainBuilder`

**Methods**:
- `build_process_lineage(evidence_events: List[Dict]) -> List[Dict]`
- `build_file_modification_chains(evidence_events: List[Dict]) -> List[Dict]`
- `build_persistence_chains(evidence_events: List[Dict]) -> List[Dict]`
- `build_network_intent_chains(evidence_events: List[Dict]) -> List[Dict]`
- `detect_lateral_preparation(evidence_events: List[Dict]) -> List[Dict]`

**Deterministic Guarantees**:
- **Same Input → Same Output**: Same evidence events always produce same chains
- **No Randomness**: No random selection or ordering
- **Explicit Rules**: All chain construction rules are explicit
- **No Inference**: No probabilistic or ML-based inference

### Temporal Phase Detector

**Class**: `TemporalPhaseDetector`

**Methods**:
- `detect_phases(behavioral_chains: Dict, evidence_events: List[Dict]) -> List[Dict]`
- `find_phase_boundaries(events: List[Dict]) -> List[Dict]`

**Deterministic Guarantees**:
- **Phase Boundaries**: Phase boundaries determined by explicit rules (not heuristics)
- **Temporal Ordering**: Phases ordered by `observed_at` (ascending)
- **No Overlap**: Phases do not overlap (explicit boundaries)
- **Complete Coverage**: All events assigned to phases

### Evidence Linker

**Class**: `EvidenceLinker`

**Methods**:
- `link_evidence(claims: List[Dict], evidence_events: List[Dict]) -> List[Dict]`
- `validate_claims(claims: List[Dict]) -> bool`

**Deterministic Guarantees**:
- **Event ID Matching**: Claims matched to evidence by `event_id` (exact match)
- **Table Matching**: Claims matched to evidence by `table` (exact match)
- **Timestamp Matching**: Claims matched to evidence by `observed_at` (exact match)
- **No Unsupported Claims**: Claims without evidence are rejected

### Summary Generator

**Class**: `SummaryGenerator`

**Methods**:
- `generate_json_summary(behavioral_chains: Dict, temporal_phases: List[Dict], evidence_links: List[Dict]) -> Dict`
- `generate_text_summary(behavioral_chains: Dict, temporal_phases: List[Dict], evidence_links: List[Dict]) -> str`
- `generate_graph_metadata(behavioral_chains: Dict, evidence_links: List[Dict]) -> Dict`

**Deterministic Guarantees**:
- **Template-Based**: Text generation uses deterministic templates (not LLM)
- **Factual Statements**: Only facts from evidence (no speculation)
- **Evidence Citations**: Every statement includes evidence references
- **No Adjectives**: No descriptive adjectives
- **No Recommendations**: No mitigation advice

---

## STEP 4 — EXAMPLE FORENSIC SUMMARY OUTPUT

### Complete Example

**Input**: `incident_id = "incident_123e4567-e89b-12d3-a456-426614174000"`

**Output**: See JSON, text, and graph metadata examples above.

---

## STEP 5 — EXPLICIT LIST OF LIMITATIONS

### 1. Evidence Completeness

**Limitation**: Summary quality depends on evidence completeness.

**Impact**: Missing evidence may result in incomplete behavioral chains.

**Mitigation**: Summary explicitly notes missing evidence (gaps in chains).

### 2. Temporal Ordering Assumptions

**Limitation**: Phase boundaries assume events are temporally ordered.

**Impact**: Out-of-order events may result in incorrect phase boundaries.

**Mitigation**: Events are sorted by `observed_at` before phase detection.

### 3. Process Lineage Gaps

**Limitation**: Missing parent processes result in incomplete lineage.

**Impact**: Process chains may have gaps (missing parent processes).

**Mitigation**: Summary explicitly notes missing parent processes.

### 4. File Path Normalization

**Limitation**: File path matching is case-sensitive on Linux, case-insensitive on Windows.

**Impact**: File chains may not match correctly if paths are not normalized.

**Mitigation**: File paths are normalized before matching (case-insensitive on Windows).

### 5. Network Correlation Window

**Limitation**: Network intent correlated with DPI flows using ±5 second time window.

**Impact**: Network activities outside time window may not be correlated.

**Mitigation**: Time window is configurable (default: ±5 seconds).

### 6. Lateral Preparation Detection

**Limitation**: Lateral preparation detection uses explicit thresholds (>10 connections, >10 DNS queries).

**Impact**: Activities below thresholds may not be detected.

**Mitigation**: Thresholds are configurable (default: 10 connections/queries within 60 seconds).

### 7. No Cross-Host Correlation

**Limitation**: Summary is per-incident (single machine).

**Impact**: Cross-host attacks are not correlated in single summary.

**Mitigation**: Multiple summaries can be generated (one per incident), correlation handled by threat-graph.

### 8. No Intent Inference

**Limitation**: Summary does not infer attacker intent.

**Impact**: Summary describes what happened, not why it happened.

**Mitigation**: Intent inference is explicitly forbidden (no speculation).

### 9. No Mitigation Recommendations

**Limitation**: Summary does not provide mitigation advice.

**Impact**: Summary describes incident, not how to respond.

**Mitigation**: Mitigation recommendations are explicitly forbidden.

### 10. Deterministic but Not Optimal

**Limitation**: Summary is deterministic but may not be optimal (e.g., phase boundaries may not be ideal).

**Impact**: Summary may have suboptimal phase boundaries or chain groupings.

**Mitigation**: Determinism is prioritized over optimality (same inputs → same outputs).

---

**AUTHORITATIVE**: This forensic summarization architecture is the single authoritative source for deterministic forensic summarization.

**STATUS**: Phase B forensic summarization designed. Ready for implementation.
