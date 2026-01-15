# RansomEye v1.0 Architecture Document

**Document Classification:** Technical Architecture  
**Version:** 1.0  
**Date:** 2025-01-15  
**Status:** Authoritative

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Architectural Principles](#architectural-principles)
4. [System Architecture](#system-architecture)
5. [Component Architecture](#component-architecture)
6. [Data Architecture](#data-architecture)
7. [Security Architecture](#security-architecture)
8. [Deployment Architecture](#deployment-architecture)
9. [Integration Architecture](#integration-architecture)
10. [Operational Architecture](#operational-architecture)
11. [Technology Stack](#technology-stack)
12. [Scalability and Performance](#scalability-and-performance)

---

## Executive Summary

RansomEye is an enterprise and military-grade threat detection and response platform designed to identify, analyze, and respond to ransomware attacks in real-time. The system provides comprehensive visibility into system behavior, network traffic, and threat indicators through multiple specialized components working together.

**Key Architectural Characteristics:**
- **Modular Design**: Loosely coupled components with well-defined interfaces
- **Event-Driven Architecture**: Event-based communication with immutable event storage
- **Database-Centric**: PostgreSQL as the single source of truth
- **Security-First**: Zero-trust security model with comprehensive audit logging
- **Air-Gapped Capable**: Designed for offline operation and secure environments
- **Deterministic Processing**: Rule-based and deterministic algorithms where possible

---

## System Overview

### Purpose

RansomEye v1.0 is designed to:
- **Detect** ransomware attacks through multi-layered telemetry collection
- **Analyze** threats using rule-based correlation and AI-powered insights
- **Respond** to incidents with policy-driven enforcement and human authority
- **Document** incidents with forensic-grade evidence and audit trails

### Core Capabilities

1. **Telemetry Collection**: Agents collect system and network events from Linux and Windows systems
2. **Event Processing**: Ingest service validates and stores events in an immutable log
3. **Correlation**: Rule-based correlation engine detects patterns and creates incidents
4. **AI Analysis**: Machine learning models provide advisory insights and anomaly detection
5. **Policy Enforcement**: Policy engine enforces security policies and signs commands
6. **Forensics**: Forensic summarization reconstructs attack timelines
7. **Reporting**: Signed reports and audit trails support compliance and investigation

### System Boundaries

**In Scope:**
- Event collection from agents
- Event processing and storage
- Incident detection and correlation
- AI-powered analysis
- Policy enforcement
- Forensic analysis
- Web-based management interface

**Out of Scope (v1.0):**
- Automated remediation (response planning only)
- Third-party SIEM integration
- Multi-tenant isolation
- High availability clustering

---

## Architectural Principles

### 1. Immutability First

**Principle**: Events and evidence are immutable once stored.

**Implementation**:
- Events stored in `raw_events` table are never updated or deleted
- Evidence linked to incidents is append-only
- Audit ledger entries are immutable
- Database schema enforces immutability constraints

**Rationale**: Ensures auditability, prevents tampering, and enables complete forensic reconstruction.

### 2. Database as Single Source of Truth

**Principle**: PostgreSQL database is the authoritative data store for all system state.

**Implementation**:
- All events stored in PostgreSQL
- All incidents and evidence in PostgreSQL
- Components communicate via database (shared-nothing architecture)
- No component-to-component direct communication

**Rationale**: Simplifies architecture, ensures consistency, and enables independent component scaling.

### 3. Deterministic Processing

**Principle**: Core detection and correlation logic is deterministic and reproducible.

**Implementation**:
- Rule-based correlation (no probabilistic inference in critical path)
- Deterministic state machine for incident lifecycle
- Reproducible forensic summarization
- No external dependencies in correlation logic

**Rationale**: Ensures consistent behavior, enables verification, and supports audit requirements.

### 4. Security by Design

**Principle**: Security is integrated into every component, not bolted on.

**Implementation**:
- Zero-trust access control (RBAC with default DENY)
- Comprehensive audit logging (all actions logged)
- Cryptographic signing of commands and reports
- Least privilege execution (non-root agents)
- Capability-based security (DPI Probe uses file capabilities)

**Rationale**: Critical for enterprise and military deployments where security is paramount.

### 5. Fail-Safe Defaults

**Principle**: System fails in secure state, not insecure state.

**Implementation**:
- Authentication failures result in access denial
- Policy failures result in action blocking
- Validation failures result in event rejection
- Component failures do not compromise security boundaries

**Rationale**: Prevents security violations during failures or attacks.

### 6. Air-Gapped Operation

**Principle**: System operates without external network dependencies.

**Implementation**:
- Offline threat intelligence feeds
- Local LLM models (GGUF format)
- No external API calls in critical path
- Self-contained release bundles

**Rationale**: Required for secure deployments where external network access is prohibited.

### 7. Human Authority

**Principle**: Critical decisions require human approval.

**Implementation**:
- Human Authority Framework (HAF) for override approvals
- Policy engine requires signed commands
- Incident resolution requires human confirmation
- No fully automated remediation

**Rationale**: Prevents automated systems from making irreversible mistakes.

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        RansomEye Platform                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Linux Agent  │  │Windows Agent │  │  DPI Probe   │         │
│  │  (Rust)      │  │  (Python)    │  │  (Python)    │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                  │
│         └──────────────────┼──────────────────┘                  │
│                            │                                      │
│                    ┌───────▼────────┐                            │
│                    │  RansomEye Core │                            │
│                    │  (Orchestrated) │                            │
│                    ├─────────────────┤                            │
│                    │                 │                            │
│  ┌─────────────────▼──┐  ┌──────────▼──────────┐                │
│  │  Ingest Service    │  │  Correlation Engine │                │
│  │  (FastAPI)         │  │  (Python)           │                │
│  └─────────┬──────────┘  └──────────┬──────────┘                │
│            │                         │                            │
│  ┌─────────▼─────────────────────────▼──────────┐                │
│  │           PostgreSQL Database                 │                │
│  │         (Single Source of Truth)              │                │
│  └─────────┬─────────────────────────┬──────────┘                │
│            │                         │                            │
│  ┌─────────▼──────────┐  ┌──────────▼──────────┐                │
│  │   AI Core          │  │  Policy Engine      │                │
│  │   (Python)         │  │  (Python)           │                │
│  └────────────────────┘  └─────────────────────┘                │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              UI Backend (FastAPI)                        │   │
│  │  ┌──────────────┐              ┌──────────────┐         │   │
│  │  │   Frontend   │              │   API        │         │   │
│  │  │  (React)     │◄─────────────┤  Endpoints   │         │   │
│  │  └──────────────┘              └──────────────┘         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Component Communication Pattern

RansomEye uses a **database-centric architecture** where:
- Components do not communicate directly with each other
- All communication happens through the PostgreSQL database
- Components read from and write to shared database tables
- Event-driven processing: components poll database for new work

**Advantages**:
- Simple architecture (no message queues, no service mesh)
- Natural persistence (database handles durability)
- Easy debugging (all state visible in database)
- Independent scaling (components can scale independently)

**Disadvantages**:
- Database becomes bottleneck (mitigated by indexing and partitioning)
- No real-time push notifications (mitigated by polling)

### Data Flow

#### Event Ingestion Flow

```
1. Agent collects event (process activity, file activity, etc.)
   ↓
2. Agent constructs event envelope (UUID, timestamps, payload)
   ↓
3. Agent sends HTTP POST to Ingest Service (/events)
   ↓
4. Ingest Service validates event (schema, timestamps, hash)
   ↓
5. Ingest Service stores event in raw_events table
   ↓
6. Ingest Service stores normalized data in component-specific tables
   (process_activity, file_activity, dpi_flows, etc.)
```

#### Incident Detection Flow

```
1. Correlation Engine polls raw_events for new events
   ↓
2. Correlation Engine evaluates rules against event
   ↓
3. If rule matches, Correlation Engine creates/updates incident
   ↓
4. Correlation Engine links event as evidence to incident
   ↓
5. Correlation Engine updates incident confidence and stage
   (SUSPICIOUS → PROBABLE → CONFIRMED)
   ↓
6. Incident stored in incidents table with evidence links
```

#### AI Analysis Flow

```
1. AI Core polls incidents table for unresolved incidents
   ↓
2. AI Core extracts features from incidents
   ↓
3. AI Core performs clustering (groups similar incidents)
   ↓
4. AI Core generates SHAP explanations (feature importance)
   ↓
5. AI Core stores metadata in AI tables
   (feature_vectors, clusters, shap_explanations)
   ↓
6. AI metadata linked to incidents (read-only, advisory)
```

#### Policy Enforcement Flow

```
1. Policy Engine receives command request
   ↓
2. Policy Engine evaluates policy rules
   ↓
3. Policy Engine signs command with cryptographic key
   ↓
4. Policy Engine stores signed command in database
   ↓
5. Executor verifies signature before execution
   ↓
6. Execution logged in audit ledger
```

---

## Component Architecture

### Core Platform

The **RansomEye Core** is a unified runtime that orchestrates all Core components as a single integrated service.

**Components**:
- **Ingest Service**: Receives and validates events from agents
- **Correlation Engine**: Detects patterns and creates incidents
- **AI Core**: Performs machine learning analysis
- **Policy Engine**: Enforces policies and signs commands
- **UI Backend**: Provides web API for management interface

**Runtime Model**:
- Core runtime loads all components as Python modules
- Components execute within Core process (not separate processes)
- Core coordinates component lifecycle (startup, shutdown)
- Components share database connections (connection pooling)

**Service**: `ransomeye-core.service` (systemd)

### Agents

#### Linux Agent

**Technology**: Rust  
**Purpose**: Monitors Linux systems and emits events

**Capabilities**:
- Process monitoring (process creation, termination)
- File system monitoring (file creation, modification, deletion)
- System call monitoring (via eBPF/auditd)
- Network connection monitoring
- Event envelope construction
- HTTP transmission to Core

**Service**: `ransomeye-linux-agent.service` (systemd)  
**User**: `ransomeye-agent` (non-root)  
**Standalone**: Yes (can operate independently of Core)

#### Windows Agent

**Technology**: Python (with ETW integration)  
**Purpose**: Monitors Windows systems and emits events

**Capabilities**:
- Windows Event Tracing (ETW) integration
- Process monitoring
- File system monitoring
- Registry monitoring
- Network monitoring
- Event envelope construction
- HTTP transmission to Core

**Service**: `RansomEyeWindowsAgent` (Windows Service)  
**User**: `ransomeye-agent` (non-Administrator)  
**Standalone**: Yes (can operate independently of Core)

### DPI Probe

**Technology**: Python (with libpcap/libnetfilter_queue)  
**Purpose**: Deep packet inspection and network monitoring

**Capabilities** (v1.0 Status: Stub Implementation):
- Network packet capture (planned)
- Flow assembly (planned)
- Protocol analysis (planned)
- Event generation (planned)

**Current Status**: Stub runtime exists but packet capture is disabled

**Service**: `ransomeye-dpi.service` (systemd)  
**User**: `ransomeye-dpi` (non-root, with CAP_NET_RAW and CAP_NET_ADMIN capabilities)  
**Standalone**: Yes (can operate independently of Core)

### Ingest Service

**Technology**: Python, FastAPI  
**Purpose**: Receives, validates, and stores events

**Responsibilities**:
- HTTP endpoint for event reception (`POST /events`)
- Event envelope validation (schema, timestamps, hash)
- Duplicate detection
- Event storage in `raw_events` table
- Normalized data storage (component-specific tables)
- Validation status logging

**Key Features**:
- Schema validation against `event-envelope.schema.json`
- Timestamp validation (clock skew, age limits)
- Hash integrity verification
- Idempotent storage (duplicate events rejected)

### Correlation Engine

**Technology**: Python  
**Purpose**: Detects patterns and creates incidents

**Responsibilities**:
- Rule evaluation against events
- Incident creation and management
- Evidence linking
- Confidence accumulation
- State machine management (SUSPICIOUS → PROBABLE → CONFIRMED)
- Deduplication (same machine, similar patterns)

**Key Features**:
- Rule-based correlation (deterministic)
- State machine for incident lifecycle
- Deduplication window (prevent duplicate incidents)
- Contradiction detection (confidence decay)
- Confidence scoring (0.00 to 100.00)

### AI Core

**Technology**: Python (scikit-learn, SHAP)  
**Purpose**: Machine learning analysis and insights

**Responsibilities**:
- Feature extraction from incidents
- Clustering (group similar incidents)
- SHAP explanations (feature importance)
- Metadata storage (not incident modification)

**Key Features**:
- **Read-only**: Does not modify incidents or evidence
- **Non-blocking**: Operates in batch mode, does not block pipeline
- **Advisory only**: Output is metadata for human review
- **Offline**: No external API calls, uses local models

**AI Tables**:
- `feature_vectors`: Feature vector references (hashes)
- `clusters`: Cluster metadata
- `cluster_memberships`: Incident ↔ cluster mapping
- `shap_explanations`: SHAP explanation references (hashes)

### Policy Engine

**Technology**: Python  
**Purpose**: Policy enforcement and command signing

**Responsibilities**:
- Policy rule evaluation
- Command signing (cryptographic)
- Policy enforcement
- Command verification
- Audit logging

**Key Features**:
- Policy-driven enforcement
- Cryptographic signing (ed25519)
- Command verification before execution
- Integration with Human Authority Framework (HAF)

### UI Backend

**Technology**: Python, FastAPI  
**Purpose**: Web API for management interface

**Endpoints**:
- `GET /incidents`: List incidents
- `GET /incidents/{id}`: Get incident details
- `GET /evidence/{incident_id}`: Get evidence for incident
- `GET /ai/metadata/{incident_id}`: Get AI metadata for incident
- Read-only API (no mutations via API)

**Key Features**:
- RESTful API
- Read-only enforcement (queries only)
- RBAC integration (planned, not enforced in v1.0)
- JSON responses

### UI Frontend

**Technology**: React, Vite  
**Purpose**: Web-based management interface

**Features**:
- Incident list view
- Incident detail view
- Evidence display
- AI insights display
- Real-time updates (polling)

**Status**: Basic implementation (no authentication in v1.0)

### Supporting Components

#### Threat Intelligence

**Purpose**: IOC ingestion and correlation

**Features**:
- Feed ingestion (offline-first)
- IOC normalization
- IOC correlation with events
- Signed feeds support

#### Forensic Summarization

**Purpose**: Deterministic forensic analysis

**Features**:
- Behavioral chain reconstruction
- Temporal phase detection
- Evidence linking
- Summary generation (deterministic, rule-based)

#### LLM Summarizer

**Purpose**: Human-readable incident narratives

**Features**:
- Offline LLM (GGUF format)
- Prompt generation
- PII redaction
- Narrative generation

#### RBAC

**Purpose**: Role-based access control

**Features**:
- Five roles: SUPER_ADMIN, SECURITY_ANALYST, POLICY_MANAGER, IT_ADMIN, AUDITOR
- Permission model
- Server-side enforcement (planned, not enforced in v1.0)

#### Audit Ledger

**Purpose**: Immutable audit log

**Features**:
- All actions logged
- Immutable entries
- Cryptographic integrity
- Query interface

#### Supply Chain Security

**Purpose**: Build integrity and artifact signing

**Features**:
- Artifact signing (ed25519)
- SBOM generation
- Signature verification
- Key management

---

## Data Architecture

### Database Schema Overview

RansomEye uses PostgreSQL as the single source of truth. The schema is organized into logical groups:

#### Core Identity Tables

- **machines**: Machine registry (host-centric modeling)
- **component_instances**: Component instance registry
- **component_types**: Component type enumeration

#### Raw Events Tables

- **raw_events**: Immutable event log (exact event envelopes as received)
- **event_validation_log**: Event validation results

#### Normalized Data Tables

- **process_activity**: Normalized process events
- **file_activity**: Normalized file events
- **dpi_flows**: Normalized network flow events
- **dns**: Normalized DNS events
- Component-specific normalized tables

#### Correlation Tables

- **incidents**: Incident registry
- **evidence**: Evidence linked to incidents
- **incident_stages**: Incident state transition history
- **correlation_rules**: Correlation rule definitions

#### AI Metadata Tables

- **ai_model_versions**: Model version registry
- **feature_vectors**: Feature vector references (hashes)
- **clusters**: Cluster metadata
- **cluster_memberships**: Incident ↔ cluster mapping
- **shap_explanations**: SHAP explanation references (hashes)

#### Policy Tables

- **signed_commands**: Cryptographically signed commands
- **policy_rules**: Policy rule definitions

#### Audit Tables

- **audit_ledger**: Immutable audit log

#### RBAC Tables

- **users**: User registry
- **roles**: Role definitions
- **permissions**: Permission definitions
- **user_roles**: User ↔ role mapping

### Data Model Principles

#### Immutability

- **raw_events**: Never updated, never deleted
- **evidence**: Append-only (new evidence added, existing evidence never modified)
- **incident_stages**: Append-only state transition log
- **audit_ledger**: Immutable audit entries

#### Host-Centric Modeling

- Incidents are associated with machines (not users or processes)
- One incident per machine for similar patterns (deduplication)
- Machine-first modeling (machines table is authoritative)

#### Event Envelope Contract

All events conform to the **Event Envelope Contract**:
- `event_id`: UUID v4 (immutable identifier)
- `machine_id`: Machine identifier
- `component_instance_id`: Component instance identifier
- `component`: Component type (LINUX_AGENT, WINDOWS_AGENT, DPI_PROBE)
- `observed_at`: RFC3339 UTC timestamp (when event occurred)
- `ingested_at`: RFC3339 UTC timestamp (when event ingested)
- `sequence`: Monotonically increasing sequence number
- `payload`: Opaque JSON object (component-specific)
- `hash_sha256`: SHA256 hash of entire envelope
- `prev_hash_sha256`: SHA256 hash of previous event (integrity chain)

#### Time Semantics

- All timestamps in UTC (RFC3339 format)
- Clock skew tolerance: 5 seconds
- Event age limit: 30 days
- Late arrival detection: > 1 hour delay
- Deterministic timestamp handling (no clock adjustments)

#### Integrity Chain

Events form an integrity chain:
- First event: `sequence = 0`, `prev_hash_sha256 = NULL`
- Subsequent events: `prev_hash_sha256` = hash of previous event
- Chain validation: Each event's `prev_hash_sha256` must match previous event's `hash_sha256`
- Broken chain detection: Events with broken chains are rejected

### Data Flow Patterns

#### Write Pattern

1. **Ingest Service** writes to `raw_events` and normalized tables
2. **Correlation Engine** writes to `incidents`, `evidence`, `incident_stages`
3. **AI Core** writes to AI metadata tables (read-only with respect to incidents)
4. **Policy Engine** writes to `signed_commands`, `audit_ledger`
5. **UI Backend** reads only (no writes)

#### Read Pattern

1. **Correlation Engine** reads from `raw_events` (polling)
2. **AI Core** reads from `incidents` (polling)
3. **UI Backend** reads from `incidents`, `evidence`, AI tables (queries)
4. **Forensic Summarization** reads from `incidents`, `evidence`, normalized tables

#### Transaction Boundaries

- **Ingest Service**: Single transaction per event (atomic storage)
- **Correlation Engine**: Single transaction per incident update
- **AI Core**: Batch transactions (multiple incidents processed together)
- **Policy Engine**: Single transaction per command signing

---

## Security Architecture

### Security Model

RansomEye implements a **zero-trust security model**:
- Default DENY (all access denied unless explicitly permitted)
- Explicit permissions (no implied permissions)
- Server-side enforcement (not just UI hiding)
- Comprehensive audit logging (all actions logged)

### Authentication and Authorization

#### RBAC (Role-Based Access Control)

**Five Roles**:
1. **SUPER_ADMIN**: Full system access
2. **SECURITY_ANALYST**: Incident analysis and investigation
3. **POLICY_MANAGER**: Policy configuration and management
4. **IT_ADMIN**: System administration
5. **AUDITOR**: Read-only access for auditing

**Status**: RBAC model implemented, enforcement not fully integrated in v1.0

#### Permission Model

- Permissions are explicit (no implied permissions)
- Permissions are checked server-side (not just UI)
- Permission checks are logged to audit ledger
- Default DENY (unauthorized access blocked)

### Cryptographic Security

#### Command Signing

- Commands are cryptographically signed (ed25519)
- Signatures verified before execution
- Signed commands stored in database
- Key management via persistent signing authority

#### Artifact Signing

- Build artifacts are cryptographically signed
- Signatures verified during deployment
- SBOM signed for supply chain security
- Key registry tracks all signing keys

#### Report Signing

- Reports are cryptographically signed
- Signatures enable verification of report integrity
- Long-term verifiability (7+ years)

### Network Security

#### Agent-to-Core Communication

- HTTP/HTTPS (TLS recommended in production)
- Event envelopes are JSON
- No persistent connections (stateless HTTP)

#### UI Access

- Web-based interface (HTTPS recommended in production)
- RESTful API
- CORS configuration (if needed)

### Data Security

#### Encryption at Rest

- Database encryption (PostgreSQL encryption at rest)
- Key management (environment variables, key vaults)

#### Encryption in Transit

- TLS/HTTPS for all network communication
- Certificate management

#### PII Handling

- PII redaction in LLM summarizer
- Privacy policies (STRICT, BALANCED, FORENSIC modes)
- Redaction logging

### Audit and Compliance

#### Audit Ledger

- All actions logged to `audit_ledger` table
- Immutable audit entries
- Cryptographic integrity (hash chains)
- Query interface for audit trail

#### Compliance Features

- Signed reports (forensic-grade)
- Complete audit trail
- Evidence preservation (immutable storage)
- Long-term retention (7+ year SOX compliance)

### Least Privilege

#### Agent Execution

- **Linux Agent**: Runs as non-root user (`ransomeye-agent`)
- **Windows Agent**: Runs as non-Administrator user (`ransomeye-agent`)
- **DPI Probe**: Runs as non-root user with file capabilities (`ransomeye-dpi`)

#### Capability-Based Security

- **DPI Probe** uses Linux capabilities (CAP_NET_RAW, CAP_NET_ADMIN)
- File capabilities (not full root)
- Reduced attack surface

#### Core Execution

- **Core Runtime**: Runs as non-root user (`ransomeye`)
- Systemd security hardening (NoNewPrivileges, ProtectSystem, ProtectHome)

---

## Deployment Architecture

### Deployment Model

RansomEye v1.0 uses a **single-server deployment model**:
- Core runtime on one server
- PostgreSQL database on same server (or separate server)
- Agents deployed on target systems (Linux/Windows)
- DPI Probe deployed on network monitoring servers (optional)

### Installation Components

#### Core Installer

**Location**: `installer/core/`  
**Components Installed**:
- Core runtime (Python)
- All Core components (Ingest, Correlation, AI, Policy, UI)
- Database schema
- Systemd service
- Configuration files

**Prerequisites**:
- PostgreSQL 14+
- Python 3.8+
- System dependencies

#### Linux Agent Installer

**Location**: `installer/linux-agent/`  
**Components Installed**:
- Linux Agent binary (Rust)
- Systemd service
- Configuration files

**Prerequisites**:
- Rust toolchain (for building)
- Python 3.10+ (for installer)

#### Windows Agent Installer

**Location**: `installer/windows-agent/`  
**Components Installed**:
- Windows Agent (Python)
- Windows Service
- Configuration files

**Prerequisites**:
- Python 3.10+
- Windows Service dependencies

#### DPI Probe Installer

**Location**: `installer/dpi-probe/`  
**Components Installed**:
- DPI Probe (Python)
- Systemd service
- Configuration files
- File capabilities

**Prerequisites**:
- Python 3.10+
- libcap2-bin
- Filesystem with capability support (ext4, xfs)

### Deployment Topology

#### Single-Server Deployment (Recommended for v1.0)

```
┌─────────────────────────────────────┐
│      RansomEye Core Server          │
│  ┌───────────────────────────────┐  │
│  │  RansomEye Core Runtime       │  │
│  │  (Ingest, Correlation, AI,    │  │
│  │   Policy, UI)                 │  │
│  └──────────────┬────────────────┘  │
│                 │                    │
│  ┌──────────────▼────────────────┐  │
│  │  PostgreSQL Database          │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
         ▲                    ▲
         │                    │
    ┌────┴────┐         ┌─────┴─────┐
    │  Linux  │         │  Windows  │
    │  Agent  │         │   Agent   │
    └─────────┘         └───────────┘
```

#### Network Monitoring Deployment (Optional)

```
┌──────────────────────┐
│   Network Segment    │
│  ┌────────────────┐  │
│  │   DPI Probe    │  │
│  │  (CAP_NET_RAW) │  │
│  └────────┬───────┘  │
│           │          │
└───────────┼──────────┘
            │
            │ HTTP
            ▼
┌──────────────────────┐
│   RansomEye Core     │
└──────────────────────┘
```

### Configuration Management

#### Environment Variables

Core components use environment variables for configuration:
- `RANSOMEYE_DB_PASSWORD`: Database password
- `RANSOMEYE_DB_USER`: Database user
- `RANSOMEYE_DB_HOST`: Database host
- `RANSOMEYE_DB_PORT`: Database port
- `RANSOMEYE_COMMAND_SIGNING_KEY`: Command signing key
- Component-specific environment variables

#### Configuration Files

- Service configuration: `/etc/ransomeye/core/config/`
- Agent configuration: `/etc/ransomeye/agent/config/`
- DPI Probe configuration: `<install_root>/config/` (Core supervised)

### Service Management

#### Linux Services (systemd)

- **ransomeye-core.service**: Core runtime
- **ransomeye-linux-agent.service**: Linux Agent
- **DPI Probe**: Launched by Core orchestrator (no standalone systemd service)

#### Windows Services

- **RansomEyeWindowsAgent**: Windows Agent

### Upgrade and Rollback

**Status**: Upgrade and rollback mechanisms not implemented in v1.0

**Planned Features**:
- Version management
- Database migration automation
- Rollback procedures
- Zero-downtime upgrades (future)

---

## Integration Architecture

### Event Envelope Contract

All events conform to the **Event Envelope Contract** (see `contracts/event-envelope.schema.json`):

- **Schema**: JSON Schema Draft 2020-12
- **Protobuf**: Protocol Buffers v3
- **Immutable**: Contract is frozen, cannot be modified

### API Contracts

#### Ingest Service API

**Endpoint**: `POST /events`  
**Content-Type**: `application/json`  
**Payload**: Event envelope (JSON)

**Response**:
- `200 OK`: Event accepted
- `400 Bad Request`: Validation failure
- `409 Conflict`: Duplicate event
- `500 Internal Server Error`: Server error

#### UI Backend API

**Endpoints**:
- `GET /incidents`: List incidents
- `GET /incidents/{id}`: Get incident details
- `GET /evidence/{incident_id}`: Get evidence for incident
- `GET /ai/metadata/{incident_id}`: Get AI metadata for incident

**Response Format**: JSON

### External Integrations

#### Threat Intelligence Feeds

- Offline-first design
- Signed feeds support
- IOC normalization
- IOC correlation with events

#### LLM Models

- Offline LLM models (GGUF format)
- Local inference (no external API calls)
- PII redaction before inference

### Integration Points

#### Agent Integration

- Agents send events via HTTP POST
- Event envelope format (JSON)
- Authentication (planned, not implemented in v1.0)

#### Database Integration

- PostgreSQL 14+ required
- Connection pooling
- Transaction management
- Schema versioning

---

## Operational Architecture

### Monitoring and Observability

#### Logging

- Structured logging (JSON format)
- Log levels: DEBUG, INFO, WARN, ERROR, FATAL
- Component-specific loggers
- Audit logging (audit_ledger table)

#### Metrics

- Component-specific metrics (planned)
- Database metrics (PostgreSQL metrics)
- System metrics (CPU, memory, disk)

#### Health Checks

- Component health endpoints (`/health`)
- Database connectivity checks
- Service status checks

**Status**: Basic health checks implemented, aggregation not implemented in v1.0

### Backup and Recovery

#### Database Backup

- PostgreSQL backup (pg_dump, pg_basebackup)
- Backup frequency: As per organizational policy
- Backup retention: As per organizational policy

#### Configuration Backup

- Configuration files backed up
- Environment variables documented
- Key material backed up (secure storage)

#### Recovery Procedures

- Database restore procedures
- Configuration restore procedures
- Service restart procedures

### Disaster Recovery

**Status**: Disaster recovery procedures not fully documented in v1.0

**Considerations**:
- Database replication (planned)
- Backup and restore procedures
- Failover procedures (planned)

### Maintenance Operations

#### Database Maintenance

- Vacuum and analyze (PostgreSQL maintenance)
- Index maintenance
- Schema migrations (manual in v1.0)

#### Component Maintenance

- Service restart procedures
- Configuration updates
- Component updates (planned)

---

## Technology Stack

### Core Technologies

#### Programming Languages

- **Python 3.8+**: Core runtime, most services, agents
- **Rust**: Linux Agent (performance-critical)
- **JavaScript/TypeScript**: UI Frontend (React)

#### Web Frameworks

- **FastAPI**: Ingest Service, UI Backend (async Python web framework)
- **React**: UI Frontend (JavaScript framework)
- **Vite**: UI Frontend build tool

#### Database

- **PostgreSQL 14+**: Primary data store (relational database)

#### Machine Learning

- **scikit-learn**: Clustering, feature extraction
- **SHAP**: Model explainability
- **GGUF**: LLM model format (offline LLM)

### Supporting Technologies

#### Build and Packaging

- **Cargo**: Rust build tool (Linux Agent)
- **pip**: Python package manager
- **npm**: JavaScript package manager (UI Frontend)

#### System Integration

- **systemd**: Linux service management
- **Windows Services**: Windows service management
- **libpcap/libnetfilter_queue**: Packet capture (DPI Probe)

#### Security

- **ed25519**: Cryptographic signing
- **SHA256**: Hash functions
- **TLS/HTTPS**: Transport encryption

#### Validation and Testing

- **JSON Schema**: Schema validation
- **pytest**: Python testing (minimal in v1.0)
- **Validation harness**: Custom validation framework

### Development Tools

#### Version Control

- **Git**: Source code version control

#### CI/CD

- **GitHub Actions**: Continuous integration
- **Build scripts**: Artifact generation
- **Signing workflows**: Cryptographic signing

#### Documentation

- **Markdown**: Documentation format
- **JSON Schema**: Schema documentation
- **Protobuf**: Contract documentation

---

## Scalability and Performance

### Current Limitations (v1.0)

RansomEye v1.0 is designed for **single-server deployment**:
- Single Core runtime instance
- Single PostgreSQL database
- No horizontal scaling
- No high availability clustering

### Performance Characteristics

#### Event Ingestion

- **Throughput**: Limited by database write performance
- **Latency**: Low (direct database writes)
- **Bottleneck**: Database write performance

#### Correlation

- **Throughput**: Limited by database read/write performance
- **Latency**: Moderate (rule evaluation, database queries)
- **Bottleneck**: Database query performance

#### AI Analysis

- **Throughput**: Limited by CPU (ML model inference)
- **Latency**: High (batch processing)
- **Bottleneck**: CPU (model inference)

#### UI Queries

- **Throughput**: Limited by database read performance
- **Latency**: Low (direct database queries)
- **Bottleneck**: Database query performance

### Scalability Considerations

#### Database Scaling

**Current**: Single PostgreSQL database  
**Future Options**:
- Read replicas (for query scaling)
- Partitioning (for large tables)
- Connection pooling (already implemented)

#### Component Scaling

**Current**: Single instance per component  
**Future Options**:
- Horizontal scaling (multiple instances)
- Load balancing (for Ingest Service)
- Message queues (for event distribution)

#### Storage Scaling

**Current**: Single database storage  
**Future Options**:
- Table partitioning (by time, by machine)
- Archive storage (old events)
- Compression (for historical data)

### Performance Optimization

#### Database Optimization

- **Indexing**: Strategic indexes on frequently queried columns
- **Query Optimization**: Efficient queries, proper JOINs
- **Connection Pooling**: Reuse database connections

#### Application Optimization

- **Batch Processing**: AI Core processes incidents in batches
- **Polling Intervals**: Configurable polling intervals
- **Caching**: Planned (not implemented in v1.0)

---

## Appendix

### Glossary

- **Event Envelope**: Canonical structure for all events in RansomEye
- **Incident**: A detected threat or security event
- **Evidence**: Event data linked to an incident
- **Correlation**: Process of detecting patterns in events
- **DPI**: Deep Packet Inspection
- **IOC**: Indicator of Compromise
- **RBAC**: Role-Based Access Control
- **HAF**: Human Authority Framework
- **SBOM**: Software Bill of Materials

### References

- **Event Envelope Contract**: `contracts/event-envelope.schema.json`
- **Time Semantics Contract**: `contracts/time-semantics.md`
- **Failure Semantics Contract**: `contracts/failure-semantics.md`
- **Database Schema**: `schemas/SCHEMA_BUNDLE.md`
- **Release Documentation**: `release/ransomeye-v1.0/README.md`

### Document History

- **v1.0** (2025-01-15): Initial architecture document

---

**End of Architecture Document**
