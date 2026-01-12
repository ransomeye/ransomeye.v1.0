# RansomEye Mishka — SOC Assistant - Knowledge Sources Guide

**AUTHORITATIVE:** Complete guide to knowledge sources for Mishka RAG system

## Overview

Mishka uses RAG (Retrieval-Augmented Generation) to answer queries. The model provides **understanding and reasoning**, while the RAG knowledge base provides **specific factual data**. This separation allows:

- **Model**: Understands cybersecurity concepts, can reason about vulnerabilities, interprets queries
- **RAG Knowledge Base**: Contains actual CVE data, threat intel, IOCs, and other dynamic information

## Why RAG for CVEs and Dynamic Data?

**CVEs are constantly updated** - new vulnerabilities published daily. You cannot retrain the model every day. Instead:

1. **Model is trained once** to understand CVE structure, CVSS scoring, vulnerability types
2. **CVE database is in RAG** - updated daily by re-indexing the vector store
3. **Queries work immediately** - "What is CVE-2024-12345?" retrieves the actual CVE from RAG

This architecture provides **GenAI-like capabilities** with **offline operation** and **deterministic responses**.

## Knowledge Source Categories

### 1. RansomEye System Data (Internal)

These sources come from RansomEye's own systems:

#### Audit Ledger
- **Source**: `/var/lib/ransomeye/audit/ledger.jsonl`
- **Content**: All system actions, decisions, state changes
- **Format**: JSON lines, one entry per line
- **Update**: Real-time (as events occur)
- **Use Cases**: "What actions were taken on incident X?", "Show me all policy decisions"

#### KillChain Timelines
- **Source**: KillChain Forensics module output
- **Content**: Attack timeline events, MITRE ATT&CK mappings
- **Format**: JSON timeline files
- **Update**: As incidents are analyzed
- **Use Cases**: "What's the timeline for this attack?", "What MITRE techniques were used?"

#### Threat Graph
- **Source**: Threat Correlation Graph Engine
- **Content**: Entity relationships, campaign inferences
- **Format**: JSON graph files
- **Update**: As entities are correlated
- **Use Cases**: "How are these hosts related?", "What campaigns involve this user?"

#### Risk Index History
- **Source**: Risk Index Engine
- **Content**: Historical risk scores, risk computations
- **Format**: JSON lines
- **Update**: As risk scores are computed
- **Use Cases**: "Why did the risk score change?", "What's the risk history for this host?"

#### Explanation Bundles (SEE)
- **Source**: System Explainer Engine
- **Content**: Reasoning chains, causal links, evidence
- **Format**: JSON bundles
- **Update**: As explanations are generated
- **Use Cases**: "Why was this incident created?", "Explain this risk score change"

#### Playbook Metadata
- **Source**: Incident Response playbook registry
- **Content**: Playbook definitions, steps, scope (NOT execution records)
- **Format**: JSON registry
- **Update**: When playbooks are registered/updated
- **Use Cases**: "What playbooks are available?", "What steps are in playbook X?"

---

### 2. Cybersecurity Knowledge Bases (External)

These sources provide general cybersecurity knowledge:

#### MITRE ATT&CK Framework
- **Source**: MITRE ATT&CK JSON files (offline snapshot)
- **Content**: Techniques, tactics, procedures, detection rules, mitigation strategies
- **Format**: MITRE ATT&CK JSON schema
- **Update**: Periodic (quarterly recommended)
- **Use Cases**: "What is technique T1055?", "How do I detect lateral movement?"

#### CVE Database (NIST NVD) ⭐ CRITICAL
- **Source**: NIST National Vulnerability Database
- **Content**: 
  - CVE IDs and descriptions
  - CVSS v2/v3/v3.1 scores and vectors
  - Affected products and versions
  - References and patches
  - CWE mappings
- **Format**: NVD JSON feed (or offline snapshot)
- **Update**: **Daily** (new CVEs published daily)
- **Size**: ~200K+ CVEs (growing)
- **Ingestion**: Use `ingest_cve_database()` method
- **Use Cases**: 
  - "What is CVE-2024-12345?"
  - "What CVEs affect Apache Log4j?"
  - "Show me critical CVEs from 2024"
  - "What's the CVSS score for CVE-2024-12345?"

**Download NVD Feed**:
```bash
# Download latest NVD feed
curl -o nvd-feed.json https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-recent.json.gz
gunzip nvd-feed.json.gz

# Or download full historical feed
# https://nvd.nist.gov/vuln/data-feeds#JSON_FEED
```

#### Threat Intelligence Feeds ⭐ CRITICAL
- **Source**: Various threat intel providers, IOC databases
- **Content**:
  - IOC databases (hashes, IPs, domains, URLs)
  - APT group profiles and behaviors
  - Malware family descriptions
  - Threat actor profiles
- **Format**: JSON (custom or STIX/TAXII)
- **Update**: Weekly or as new intel arrives
- **Ingestion**: Use `ingest_threat_intel()` method
- **Use Cases**:
  - "Is IP 192.168.1.100 known to be malicious?"
  - "What are the indicators for APT28?"
  - "Has this file hash been seen in malware?"

**Sources**:
- OpenCTI (open source threat intel platform)
- MISP (Malware Information Sharing Platform)
- Commercial threat intel feeds
- Public IOC repositories

#### Security Advisories ⭐ CRITICAL
- **Source**: Vendor advisories, CERT/CC, US-CERT
- **Content**:
  - Vulnerability disclosures
  - Patch information
  - Workarounds and mitigations
  - Affected products
- **Format**: JSON (structured advisories)
- **Update**: As advisories are published
- **Ingestion**: Use `ingest_security_advisories()` method
- **Use Cases**:
  - "What patches are available for this CVE?"
  - "What's the workaround for CVE-2024-12345?"
  - "Which Microsoft advisories affect Windows Server 2019?"

---

### 3. Enhanced Knowledge Sources (Optional)

These provide additional capabilities for comprehensive GenAI-like functionality:

#### Exploit Database
- **Source**: Exploit-DB, GitHub Security Advisories
- **Content**: Exploit descriptions, exploitation techniques, PoC information
- **Format**: Structured exploit descriptions
- **Update**: Daily
- **Use Cases**: "How is this CVE exploited?", "What exploits exist for this vulnerability?"

#### Security Configuration Baselines
- **Source**: CIS Benchmarks, NIST checklists, vendor hardening guides
- **Content**: Configuration recommendations, security controls, compliance requirements
- **Format**: Structured configuration guidance
- **Update**: Periodic (as benchmarks are updated)
- **Use Cases**: "What are the CIS benchmarks for Linux?", "How do I harden Windows Server?"

#### Malware Analysis Reports
- **Source**: Public malware analysis, sandbox reports
- **Content**: Malware capabilities, IOCs, behavioral patterns, MITRE ATT&CK mappings
- **Format**: Structured analysis reports
- **Update**: As reports are published
- **Use Cases**: "What does this malware do?", "What are the IOCs for Emotet?"

#### Security Tools Documentation
- **Source**: SIEM queries, log analysis patterns, detection rules
- **Content**: Tool usage guides, common queries, detection patterns
- **Format**: Documentation and examples
- **Update**: As tools are updated
- **Use Cases**: "How do I query Splunk for failed logins?", "What's a good detection rule for lateral movement?"

#### Compliance and Regulatory Information
- **Source**: GDPR, CCPA, industry regulations, compliance frameworks
- **Content**: Regulatory requirements, compliance checklists, audit guidance
- **Format**: Structured compliance documentation
- **Update**: As regulations change
- **Use Cases**: "What are GDPR requirements for data breaches?", "What controls are needed for PCI-DSS?"

---

## Data Ingestion Workflow

### Initial Setup

1. **Download Knowledge Sources**:
   ```bash
   # CVE Database (NVD)
   curl -o nvd-feed.json https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-recent.json.gz
   gunzip nvd-feed.json.gz
   
   # MITRE ATT&CK (if not already included)
   # Download from https://github.com/mitre/cti
   
   # Threat Intel (from your sources)
   # Download or export from threat intel platform
   ```

2. **Ingest into Vector Store**:
   ```python
   from rag.document_ingestor import DocumentIngestor
   from rag.vector_store import VectorStore
   from pathlib import Path
   
   ingestor = DocumentIngestor()
   vector_store = VectorStore(Path('/var/lib/ransomeye/mishka/vector_store.faiss'), embedding_dim=384)
   
   # Ingest CVE database
   cve_docs = ingestor.ingest_cve_database(Path('nvd-feed.json'))
   for doc in cve_docs:
       vector_store.add_document(doc)
   
   # Ingest threat intel
   threat_docs = ingestor.ingest_threat_intel(Path('threat-intel.json'))
   for doc in threat_docs:
       vector_store.add_document(doc)
   
   # Ingest security advisories
   advisory_docs = ingestor.ingest_security_advisories(Path('advisories.json'))
   for doc in advisory_docs:
       vector_store.add_document(doc)
   
   # Save vector store
   vector_store.save()
   ```

### Daily Updates

**Automated Update Script**:
```python
#!/usr/bin/env python3
"""
Daily update script for CVE database and threat intel
"""

from pathlib import Path
import subprocess
from rag.document_ingestor import DocumentIngestor
from rag.vector_store import VectorStore

def update_cve_database():
    """Update CVE database from NVD feed."""
    # Download latest feed
    subprocess.run(['curl', '-o', 'nvd-feed.json.gz', 
                   'https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-recent.json.gz'])
    subprocess.run(['gunzip', 'nvd-feed.json.gz'])
    
    # Ingest new CVEs
    ingestor = DocumentIngestor()
    vector_store = VectorStore.load(Path('/var/lib/ransomeye/mishka/vector_store.faiss'))
    
    cve_docs = ingestor.ingest_cve_database(Path('nvd-feed.json'))
    for doc in cve_docs:
        vector_store.add_document(doc)
    
    vector_store.save()
    print(f"Updated {len(cve_docs)} CVE entries")

if __name__ == '__main__':
    update_cve_database()
```

**Schedule with cron**:
```bash
# Update CVE database daily at 2 AM
0 2 * * * /usr/local/bin/update-mishka-knowledge.sh
```

---

## Query Examples

### CVE Queries

**Query**: "What is CVE-2024-12345?"
**RAG Retrieval**: Searches for CVE-2024-12345 in CVE database
**Model Response**: Interprets the CVE data, explains the vulnerability, provides context

**Query**: "What CVEs affect Apache Log4j version 2.14.1?"
**RAG Retrieval**: Searches CVE database for affected products containing "Apache Log4j"
**Model Response**: Lists relevant CVEs, explains severity, provides patch information

**Query**: "Show me critical CVEs from the last 30 days"
**RAG Retrieval**: Searches CVE database for CVEs with CVSS severity "CRITICAL" and recent published dates
**Model Response**: Summarizes critical CVEs, explains why they're critical, provides recommendations

### Threat Intelligence Queries

**Query**: "Is IP 192.168.1.100 known to be malicious?"
**RAG Retrieval**: Searches threat intel for IP address 192.168.1.100
**Model Response**: Reports if found, provides context (APT group, malware family, etc.)

**Query**: "What are the indicators for APT28?"
**RAG Retrieval**: Searches threat intel for APT28 profile and associated IOCs
**Model Response**: Lists IOCs, explains APT28 tactics, provides detection guidance

### Combined Queries

**Query**: "This incident involves CVE-2024-12345. What should I do?"
**RAG Retrieval**: 
- Retrieves CVE-2024-12345 details
- Retrieves related security advisories
- Retrieves relevant playbooks
- Retrieves similar incidents from audit ledger

**Model Response**: 
- Explains the CVE
- Provides patch/workaround information
- Suggests relevant playbooks
- References similar past incidents

---

## Best Practices

### 1. Data Freshness
- **CVEs**: Update daily (new CVEs published daily)
- **Threat Intel**: Update weekly or as new intel arrives
- **Advisories**: Update as advisories are published
- **System Data**: Real-time (as events occur)

### 2. Data Quality
- **Validate CVE IDs**: Ensure CVE format is correct
- **Verify CVSS Scores**: Check scores match NVD
- **Check IOC Format**: Validate hashes, IPs, domains
- **Remove Duplicates**: Deduplicate before indexing

### 3. Storage Considerations
- **CVE Database**: Large (~200K+ CVEs), consider compression
- **Threat Intel**: Can be large, consider filtering by relevance
- **System Data**: Grows over time, consider retention policies

### 4. Security
- **Sanitize Inputs**: Validate all ingested data
- **Verify Sources**: Only ingest from trusted sources
- **Monitor Updates**: Alert on suspicious or unexpected updates
- **Version Control**: Track knowledge base versions

---

## Troubleshooting

### Issue: CVE queries return "insufficient data"
**Solution**: 
- Check if CVE database is ingested
- Verify CVE ID format (CVE-YYYY-NNNNN)
- Check vector store contains CVE documents

### Issue: Outdated CVE information
**Solution**: 
- Run daily update script
- Verify NVD feed download succeeded
- Check ingestion logs for errors

### Issue: Large vector store size
**Solution**:
- Consider separate indexes for different source types
- Implement data retention policies
- Compress old or low-relevance documents

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye Mishka knowledge sources.

**Note**: The term "SOC Copilot" is deprecated. This subsystem is now authoritatively named **Mishka — SOC Assistant (Basic, Read-Only)**.
