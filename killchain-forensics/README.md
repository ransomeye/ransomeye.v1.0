# RansomEye KillChain & Forensics Engine

**AUTHORITATIVE:** Evidence-grade correlation engine for reconstructing full adversary timelines

## Overview

The RansomEye KillChain & Forensics Engine reconstructs **full adversary timelines** across hosts, users, processes, and network activity with **court-admissible evidence handling**. It provides **evidence-grade correlation** for forensic analysis and incident response.

## Core Principles

### Immutable Timelines

**CRITICAL**: Timelines are immutable:

- ✅ **No mutation**: Events cannot be modified after creation
- ✅ **Ordered**: Events are deterministically ordered by timestamp
- ✅ **Cross-host**: Events from multiple hosts are stitched together
- ✅ **Deterministic**: Same inputs always produce same timeline

### Evidence Management

**CRITICAL**: All evidence is managed with chain-of-custody:

- ✅ **References only**: Memory dumps and artifacts are referenced, not stored as blobs
- ✅ **Artifact hashing**: All artifacts are hashed (SHA256)
- ✅ **Compression support**: Artifacts can be compressed for storage
- ✅ **Secure indexing**: Evidence is indexed for fast lookup
- ✅ **Integrity verification**: Artifact hashes are verified on access

### Chain-of-Custody Integration

**CRITICAL**: Every evidence access is logged:

- ✅ **No silent reads**: All evidence access emits audit ledger entry
- ✅ **Complete log**: Full access log maintained in evidence records
- ✅ **Integrity verification**: Evidence integrity is verified and logged
- ✅ **Audit trail**: Complete chain-of-custody in audit ledger

### Deterministic Correlation

**CRITICAL**: Campaign correlation is deterministic:

- ✅ **Explicit rules**: Linking rules are explicit and deterministic
- ✅ **No randomness**: Same inputs always produce same correlations
- ✅ **Cross-host**: Links incidents across hosts, users, IPs, malware families

## MITRE ATT&CK Timeline Reconstruction

### Technique Mapping

Events are mapped to MITRE ATT&CK techniques using **deterministic rules**:

- **Process Creation**: T1055 (Process Injection), T1053 (Scheduled Task)
- **File Access**: T1005 (Data from Local System), T1003.001 (LSASS Memory)
- **Network Connection**: T1071 (Application Layer Protocol), T1071.001 (Web Protocols)
- **Registry Modification**: T1112 (Modify Registry), T1547.001 (Boot or Logon Autostart Execution)
- **Credential Access**: T1003 (OS Credential Dumping), T1003.001 (LSASS Memory)
- **Lateral Movement**: T1021 (Remote Services), T1021.001 (Remote Desktop Protocol)

### Stage Transitions

Timeline reconstruction detects **explicit stage transitions**:

- **Reconnaissance** → **Resource Development** → **Initial Access**
- **Initial Access** → **Execution** → **Persistence**
- **Persistence** → **Privilege Escalation** → **Defense Evasion**
- **Defense Evasion** → **Credential Access** → **Discovery**
- **Discovery** → **Lateral Movement** → **Collection**
- **Collection** → **Command and Control** → **Exfiltration** → **Impact**

### Cross-Host Stitching

Timelines are **stitched across hosts** using:

- **Campaign correlation**: Events linked by IPs, malware families, users
- **Deterministic rules**: Explicit linking rules (no ambiguity)
- **Ordered timeline**: Events ordered by timestamp across all hosts

## Evidence Management

### Evidence Types

Supported evidence types:

- **Memory Dump**: Process memory dumps (references only)
- **Disk Artifact**: File system artifacts
- **Network Capture**: Network packet captures
- **Log File**: System and application logs
- **Registry Hive**: Windows registry hives
- **Process Image**: Process executable images

### Artifact Hashing

All artifacts are hashed using **SHA256**:

- **Registration**: Hash calculated on registration
- **Verification**: Hash verified on every access
- **Integrity**: Mismatch detection on verification

### Compression Support

Artifacts can be compressed for storage:

- **gzip compression**: Deterministic compression
- **Decompression**: Deterministic decompression
- **Size tracking**: Original and compressed sizes tracked

### Secure Storage Indexing

Evidence is indexed for fast lookup:

- **Evidence ID**: UUID identifier for each evidence record
- **Storage location**: Path to artifact (reference, not blob)
- **Access log**: Complete chain-of-custody log

## Campaign Correlation

### Linking Rules

Campaigns are linked using **deterministic rules** (in order):

1. **IP Address**: If event shares IP with existing campaign, link to that campaign
2. **Malware Family**: If event shares malware family with existing campaign, link to that campaign
3. **User**: If event shares user with existing campaign, link to that campaign
4. **Host**: If event shares host with existing campaign, link to that campaign
5. **New Campaign**: Otherwise, create new campaign

### Campaign Metadata

Each campaign tracks:

- **Hosts**: Set of hosts involved in campaign
- **Users**: Set of users involved in campaign
- **IP Addresses**: Set of IP addresses used in campaign
- **Malware Families**: Set of malware families in campaign
- **Events**: List of event IDs in campaign

## Chain-of-Custody Integration

### Access Logging

Every evidence access is logged:

- **Access timestamp**: When evidence was accessed
- **Accessed by**: Entity that accessed evidence
- **Access type**: Type of access (read, verify, export)
- **Ledger entry ID**: Audit ledger entry for this access

### Integrity Verification

Evidence integrity is verified:

- **Hash verification**: Artifact hash verified on access
- **Mismatch detection**: Hash mismatches are detected and reported
- **Verification flag**: Integrity verification status tracked

### Audit Ledger Entries

All evidence operations emit audit ledger entries:

- **forensic_artifact_access**: Evidence access logged
- **forensic_timeline_reconstructed**: Timeline reconstruction logged
- **No silent reads**: All reads are logged

## Usage

### Reconstruct Timeline

```bash
python3 killchain-forensics/cli/reconstruct_timeline.py \
    --source-events /path/to/events.json \
    --artifact-store /var/lib/ransomeye/forensics/evidence.jsonl \
    --artifact-storage-root /var/lib/ransomeye/forensics/artifacts \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output timeline.json
```

### Register Evidence

```python
from api.forensics_api import ForensicsAPI

api = ForensicsAPI(
    artifact_store_path=Path('/var/lib/ransomeye/forensics/evidence.jsonl'),
    artifact_storage_root=Path('/var/lib/ransomeye/forensics/artifacts'),
    ledger_path=Path('/var/lib/ransomeye/audit/ledger.jsonl'),
    ledger_key_dir=Path('/var/lib/ransomeye/audit/keys')
)

# Register evidence
evidence_record = api.register_evidence(
    artifact_path=Path('/path/to/memory.dump'),
    evidence_type='memory_dump',
    registered_by='analyst'
)
```

### Access Evidence

```python
# Access evidence (with chain-of-custody logging)
evidence = api.access_evidence(
    evidence_id='evidence-uuid',
    accessed_by='analyst',
    access_type='read'
)

# Verify integrity
api.verify_evidence_integrity(
    evidence_id='evidence-uuid',
    verified_by='analyst'
)
```

## Source Event Format

```json
[
  {
    "event_id": "event-uuid",
    "timestamp": "2025-01-10T12:00:00Z",
    "host_id": "host-1",
    "user_id": "user-1",
    "process_id": "process-1",
    "event_type": "process_creation",
    "metadata": {
      "scheduled_task": false,
      "service_creation": false,
      "suspicious_parent": true
    },
    "ip_addresses": ["192.168.1.100"],
    "malware_families": ["ransomware-variant-1"],
    "indicators": [
      {"type": "hash", "value": "abc123..."},
      {"type": "domain", "value": "evil.com"}
    ],
    "evidence_references": ["evidence-uuid-1"]
  }
]
```

## File Structure

```
killchain-forensics/
├── schema/
│   ├── killchain-event.schema.json    # Frozen JSON schema for events
│   └── evidence-record.schema.json    # Frozen JSON schema for evidence
├── engine/
│   ├── __init__.py
│   ├── timeline_builder.py            # Timeline reconstruction
│   ├── mitre_mapper.py                # MITRE ATT&CK mapping
│   └── campaign_stitcher.py           # Campaign correlation
├── evidence/
│   ├── __init__.py
│   ├── artifact_store.py              # Evidence storage indexing
│   ├── hasher.py                      # Artifact hashing
│   └── compressor.py                  # Artifact compression
├── api/
│   ├── __init__.py
│   └── forensics_api.py               # Forensics API with audit integration
├── cli/
│   ├── __init__.py
│   └── reconstruct_timeline.py       # Timeline reconstruction CLI
└── README.md                          # This file
```

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **Audit Ledger**: Required for audit trail (separate subsystem)

## Security Considerations

1. **Immutable Timelines**: Events cannot be modified after creation
2. **Chain-of-Custody**: All evidence access is logged
3. **Integrity Verification**: Artifact hashes are verified on access
4. **No Silent Reads**: All evidence access emits audit ledger entry
5. **Deterministic**: All correlation is deterministic (no randomness)

## Limitations

1. **No UI**: Phase C1 provides computation only, no UI
2. **No Automation**: No automated response or alerting
3. **No Heuristics**: All rules are explicit and justified

## Future Enhancements

- Real-time timeline updates
- Advanced MITRE technique detection
- Machine learning for campaign correlation
- Integration with threat intelligence
- Automated IOC extraction

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye KillChain & Forensics Engine documentation.
