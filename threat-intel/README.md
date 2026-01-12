# RansomEye Threat Intelligence Feed & IOC Engine

**AUTHORITATIVE:** Deterministic, offline-first threat intelligence ingestion and correlation

## Overview

The RansomEye Threat Intelligence Feed & IOC Engine ingests **external and internal intelligence feeds**, normalizes indicators into **immutable facts**, correlates IOCs with **existing evidence**, and feeds **KillChain, Threat Graph, Risk Index, Alert Engine**. It remains **offline-capable and deterministic**. Threat intel **informs**, it never decides.

## Core Principles

### Threat Intel Informs, Never Decides

**CRITICAL**: Threat intel informs, never decides:

- ✅ **No automatic blocking**: No automatic blocking based on IOCs
- ✅ **No enrichment mutation**: No mutation of incidents
- ✅ **No trust escalation**: No trust escalation
- ✅ **No ML or heuristics**: No ML or heuristics
- ✅ **No live internet dependency**: No runtime network access
- ✅ **No prioritization logic**: No prioritization logic
- ✅ **No scoring**: No scoring here

### Offline-First Operation

**CRITICAL**: Runtime operation is offline-only:

- ✅ **Offline snapshots**: Feeds are offline snapshots
- ✅ **Signed feeds**: Feeds are signed and versioned
- ✅ **No runtime network**: No runtime network access
- ✅ **Deterministic**: Same feed = same ingestion result

### Deterministic Correlation

**CRITICAL**: Correlation is deterministic:

- ✅ **Evidence-based**: Correlations are evidence-based
- ✅ **Non-mutating**: Correlations do not mutate evidence
- ✅ **Deterministic**: Same evidence + same IOC = same correlation
- ✅ **Facts only**: Correlation outputs are facts, not decisions

## Supported IOC Types

### Explicit Enumeration

All IOC types are explicitly enumerated (no free-form):

- **ip_address**: IPv4 address
- **domain**: Domain name
- **url**: URL
- **file_hash_md5**: MD5 file hash
- **file_hash_sha1**: SHA1 file hash
- **file_hash_sha256**: SHA256 file hash
- **email_address**: Email address
- **registry_key**: Windows registry key
- **process_name**: Process name
- **mutex**: Mutex name
- **user_agent**: User agent string

## Intelligence Sources

### Supported Source Types

- **public_feed**: Public feeds (MISP, NVD-derived, CERT, ISAC)
- **internal_deception**: Deception Framework interactions
- **internal_incident**: Incident artifacts
- **internal_forensics**: Forensics evidence
- **manual_analyst**: Manual analyst-submitted feeds (signed)

### Source Requirements

- **Signed**: All sources must be signed (Ed25519)
- **Versioned**: All sources must be versioned
- **Offline**: Runtime operation is offline-only

## Correlation Rules

### Correlation Methods

Correlation methods are deterministic:

- **hash_match**: IOC hash matches forensic artifact hash
- **exact_match**: IOC value exactly matches evidence value
- **domain_match**: IOC domain matches evidence domain
- **ip_match**: IOC IP matches evidence IP

### Correlation Examples

- **IOC hash matches forensic artifact hash**: File hash IOC correlated with forensic artifact
- **Domain IOC matches network scanner service**: Domain IOC correlated with network scan result
- **IP IOC matches alert source**: IP IOC correlated with alert source IP

## Required Integrations

Threat Intel Engine integrates with:

- **Audit Ledger**: Ingestion, correlation
- **KillChain & Forensics**: Evidence correlation
- **Threat Graph**: Entity + edge creation
- **Risk Index**: Signal input only
- **Alert Engine**: Context only
- **System Explanation Engine (SEE)**: Explanation bundles
- **Global Validator**: Replayability

## Usage

### Ingest Feed

```bash
python3 threat-intel/cli/ingest_feed.py \
    --feed /path/to/feed.json \
    --source-name "MISP Feed" \
    --source-type public_feed \
    --source-version "1.0.0" \
    --signature <ed25519-signature> \
    --public-key-id <public-key-id> \
    --iocs-store /var/lib/ransomeye/threat-intel/iocs.jsonl \
    --sources-store /var/lib/ransomeye/threat-intel/sources.jsonl \
    --correlations-store /var/lib/ransomeye/threat-intel/correlations.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output iocs.json
```

### Correlate IOCs

```bash
python3 threat-intel/cli/correlate_iocs.py \
    --evidence /path/to/evidence.json \
    --evidence-type forensic_artifact \
    --iocs-store /var/lib/ransomeye/threat-intel/iocs.jsonl \
    --sources-store /var/lib/ransomeye/threat-intel/sources.jsonl \
    --correlations-store /var/lib/ransomeye/threat-intel/correlations.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output correlations.json
```

### Programmatic API

```python
from api.intel_api import IntelAPI

api = IntelAPI(
    iocs_store_path=Path('/var/lib/ransomeye/threat-intel/iocs.jsonl'),
    sources_store_path=Path('/var/lib/ransomeye/threat-intel/sources.jsonl'),
    correlations_store_path=Path('/var/lib/ransomeye/threat-intel/correlations.jsonl'),
    ledger_path=Path('/var/lib/ransomeye/audit/ledger.jsonl'),
    ledger_key_dir=Path('/var/lib/ransomeye/audit/keys')
)

# Register source
source = api.register_source(
    source_name='MISP Feed',
    source_type='public_feed',
    source_version='1.0.0',
    signature='<ed25519-signature>',
    public_key_id='<public-key-id>'
)

# Ingest feed
iocs = api.ingest_feed(
    feed_path=Path('/path/to/feed.json'),
    source_id=source.get('source_id', ''),
    signature='<ed25519-signature>',
    public_key_id='<public-key-id>'
)

# Correlate IOCs
correlations = api.correlate_iocs(
    evidence=evidence_dict,
    evidence_type='forensic_artifact'
)
```

## File Structure

```
threat-intel/
├── schema/
│   ├── ioc.schema.json              # Frozen JSON schema for IOCs
│   ├── intel-source.schema.json    # Frozen JSON schema for sources
│   └── correlation.schema.json     # Frozen JSON schema for correlations
├── engine/
│   ├── __init__.py
│   ├── feed_ingestor.py            # Offline snapshot ingestion
│   ├── normalizer.py               # Canonical IOC normalization
│   ├── deduplicator.py             # Hash-based IOC deduplication
│   └── correlator.py               # Evidence ↔ IOC correlation
├── storage/
│   ├── __init__.py
│   └── intel_store.py              # Immutable IOC storage
├── api/
│   ├── __init__.py
│   └── intel_api.py                # Threat Intelligence API
├── cli/
│   ├── __init__.py
│   ├── ingest_feed.py              # Ingest feed CLI
│   └── correlate_iocs.py          # Correlate IOCs CLI
└── README.md                       # This file
```

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **Audit Ledger**: Required for audit trail (separate subsystem)

## Security Considerations

1. **No Automatic Blocking**: IOCs do not cause automatic actions
2. **No Enrichment Mutation**: No mutation of facts
3. **No Heuristics or ML**: No heuristics or ML
4. **Offline-Only**: Runtime operation is offline-only
5. **Deterministic**: Same inputs always produce same outputs

## Limitations

1. **No Decision Logic**: No decision logic exists
2. **No Automatic Actions**: No automatic actions based on IOCs
3. **No Runtime Network**: No runtime network access
4. **No Prioritization**: No prioritization logic
5. **No Scoring**: No scoring here

## Future Enhancements

- Advanced feed formats (STIX 2.1, TAXII)
- Enhanced correlation methods
- IOC expiration and lifecycle management
- Feed aggregation and merging
- IOC confidence scoring (explicit, not ML)

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye Threat Intelligence Feed & IOC Engine documentation.
