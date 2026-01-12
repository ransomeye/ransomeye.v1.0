# RansomEye Network Scanner & Topology Engine

**AUTHORITATIVE:** Deterministic discovery, non-intrusive network scanning and topology intelligence

## Overview

The RansomEye Network Scanner & Topology Engine discovers network assets (active + passive), builds **immutable topology maps**, performs **offline CVE matching**, and produces **facts only**, not actions. It operates safely in enterprise & regulated environments.

## Core Principles

### Observation, Not Attack

**CRITICAL**: Scanning is observation, not attack:

- ✅ **No exploitation**: No exploit attempts
- ✅ **No credential brute-force**: No credential attacks
- ✅ **No lateral movement**: No lateral movement attempts
- ✅ **No remediation or blocking**: No enforcement actions
- ✅ **No auto-scheduling**: No background scanning
- ✅ **No ML inference during scan**: No ML during scanning
- ✅ **No network mutation**: No network changes

### Deterministic Discovery

**CRITICAL**: All discovery is deterministic:

- ✅ **Same scan → same results**: Same scan scope = same results
- ✅ **Explicit scanning**: Scans are explicit and bounded
- ✅ **No hidden scope expansion**: No implicit scope expansion
- ✅ **Replayable**: Discovery can be replayed deterministically

### Immutable Topology

**CRITICAL**: Topology is immutable:

- ✅ **Fact graph**: Topology is a fact graph
- ✅ **Directed edges**: All edges are directed
- ✅ **Timestamped**: All edges are timestamped
- ✅ **Immutable**: All edges are immutable

## Discovery Methods

### Active Scanning (Bounded)

Active scanning uses **nmap only**:

- **Explicit scan scope**: CIDR notation or interface
- **Explicit port list**: No full sweep by default
- **Rate-limited**: Rate limiting to prevent network disruption
- **Produces**: Assets, open services, banners
- **Explicit trigger**: Scan execution must be explicitly triggered

### Passive Discovery

Passive discovery consumes:

- **DPI Probe outputs**: Deep packet inspection data
- **Flow metadata**: Network flow data
- **Read-only**: No packet crafting, no injection
- **No mutation**: Read-only ingestion

## Topology Requirements

### Topology Graph Structure

Topology is a **fact graph**:

- **Nodes**:
  - Hosts (assets)
  - Network devices
  - Services
- **Edges**:
  - `communicates_with`: Asset-to-asset communication
  - `hosts_service`: Asset-to-service relationship
  - `routes_through`: Network routing relationships

### Edge Properties

All edges are:

- ✅ **Directed**: Edges have direction
- ✅ **Timestamped**: Edges have discovery timestamp
- ✅ **Immutable**: Edges cannot be modified after creation

## CVE Matching Requirements

### Offline CVE Matching

CVE matching uses **offline NVD snapshot**:

- **Banner/service-based**: Banner/service-based matching only
- **No exploitability scoring**: No exploitability scoring
- **Deterministic rules**: Deterministic matching rules only
- **Produces**:
  - `possible_cve_id`: CVE identifier
  - `match_reason`: Reason for match (banner_version, service_name, etc.)
  - `confidence`: Confidence level (LOW | MEDIUM | HIGH)

## Required Integrations

Network Scanner integrates with:

- **Audit Ledger**: Scan start/end, scope, results
- **Threat Graph Engine**: Entity + edges
- **KillChain & Forensics**: Evidence references
- **Global Validator**: Replayability

## Usage

### Active Network Scan

```bash
python3 network-scanner/cli/scan_network.py \
    --scan-scope 192.168.1.0/24 \
    --ports 22 80 443 3389 \
    --scan-type syn \
    --rate-limit 100 \
    --assets-store /var/lib/ransomeye/network/assets.jsonl \
    --services-store /var/lib/ransomeye/network/services.jsonl \
    --topology-store /var/lib/ransomeye/network/topology.jsonl \
    --cve-matches-store /var/lib/ransomeye/network/cve_matches.jsonl \
    --cve-db /var/lib/ransomeye/network/cve_db \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output scan_results.json
```

### Build Topology

```bash
python3 network-scanner/cli/build_topology.py \
    --assets /var/lib/ransomeye/network/assets.jsonl \
    --services /var/lib/ransomeye/network/services.jsonl \
    --communication-data /var/lib/ransomeye/network/communication.json \
    --topology-store /var/lib/ransomeye/network/topology.jsonl \
    --assets-store /var/lib/ransomeye/network/assets.jsonl \
    --services-store /var/lib/ransomeye/network/services.jsonl \
    --cve-matches-store /var/lib/ransomeye/network/cve_matches.jsonl \
    --cve-db /var/lib/ransomeye/network/cve_db \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output topology.json
```

### Programmatic API

```python
from api.scanner_api import ScannerAPI

api = ScannerAPI(
    assets_store_path=Path('/var/lib/ransomeye/network/assets.jsonl'),
    services_store_path=Path('/var/lib/ransomeye/network/services.jsonl'),
    topology_store_path=Path('/var/lib/ransomeye/network/topology.jsonl'),
    cve_matches_store_path=Path('/var/lib/ransomeye/network/cve_matches.jsonl'),
    cve_db_path=Path('/var/lib/ransomeye/network/cve_db'),
    ledger_path=Path('/var/lib/ransomeye/audit/ledger.jsonl'),
    ledger_key_dir=Path('/var/lib/ransomeye/audit/keys'),
    rate_limit=100
)

# Active scan
result = api.scan_network(
    scan_scope='192.168.1.0/24',
    ports=[22, 80, 443],
    scan_type='syn'
)

# Passive discovery
assets = api.discover_passive(
    dpi_data=dpi_records,
    flow_data=flow_records
)

# Build topology
edges = api.build_topology(
    assets=assets,
    services=services,
    communication_data=comm_data
)

# Match CVEs
matches = api.match_cves(services)
```

## File Structure

```
network-scanner/
├── schema/
│   ├── asset.schema.json              # Frozen JSON schema for assets
│   ├── service.schema.json            # Frozen JSON schema for services
│   ├── topology-edge.schema.json     # Frozen JSON schema for topology edges
│   └── cve-match.schema.json         # Frozen JSON schema for CVE matches
├── engine/
│   ├── __init__.py
│   ├── active_scanner.py              # nmap-based, bounded active scanning
│   ├── passive_discoverer.py         # DPI/flow-based passive discovery
│   ├── topology_builder.py           # Immutable topology graph
│   └── cve_matcher.py                # Offline CVE correlation
├── data/
│   └── cve_db/                        # Offline NVD snapshot
├── api/
│   ├── __init__.py
│   └── scanner_api.py                 # Scanner API with audit integration
├── cli/
│   ├── __init__.py
│   ├── scan_network.py                # Active network scan CLI
│   └── build_topology.py              # Build topology CLI
└── README.md                          # This file
```

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **nmap**: Required for active scanning (system dependency)
- **Audit Ledger**: Required for audit trail (separate subsystem)

## Security Considerations

1. **No Network Mutation**: No network changes
2. **Bounded Scanning**: Explicit scan scope and ports
3. **Rate Limiting**: Rate limiting to prevent network disruption
4. **Deterministic**: Same inputs always produce same outputs
5. **Replayable**: Discovery can be replayed deterministically

## Limitations

1. **No Exploitation**: No exploit attempts
2. **No Credential Attacks**: No credential brute-force
3. **No Remediation**: No enforcement actions
4. **No Auto-Scheduling**: No background scanning
5. **Offline CVE Matching**: Uses offline NVD snapshot only

## Future Enhancements

- Advanced passive discovery methods
- Enhanced CVE database integration
- Topology visualization
- Network change detection
- Asset inventory management

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye Network Scanner & Topology Engine documentation.
