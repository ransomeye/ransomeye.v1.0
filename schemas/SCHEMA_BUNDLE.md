# RansomEye v1.0 Schema Bundle
**Authoritative Database Schema – Phase 2**

**AUTHORITATIVE**: This bundle contains the immutable database schema for RansomEye v1.0. This schema defines the canonical, non-negotiable database structure that all future code MUST conform to.

---

## Schema Bundle Metadata

### Version
**Version**: `1.0.0`  
**Release Date**: `2026-01-12`  
**Phase**: Phase 2 – Database First  
**PostgreSQL Version**: 14+ (compatible)

### Integrity Hash
**SHA256 Hash**: `14144a0838f7fbf412f4510a708be4a76dd5fa07c90e539c3a90aa5bbf256acd`

**Hash Computation Method**:
1. Concatenate all schema files in this bundle in lexicographic order:
   - `00_core_identity.sql`
   - `01_raw_events.sql`
   - `02_normalized_agent.sql`
   - `03_normalized_dpi.sql`
   - `04_correlation.sql`
   - `05_ai_metadata.sql`
   - `06_indexes.sql`
   - `07_retention.sql`
   - `SCHEMA_BUNDLE.md` (this file, excluding this hash field)
2. Compute SHA256 hash of the concatenated content
3. Insert hash in this field
4. Recompute hash of updated `SCHEMA_BUNDLE.md`
5. Insert final hash in this field

**Note**: After hash insertion, this bundle is FROZEN and MUST NOT be modified.

---

## Bundle Contents

This bundle contains the following authoritative schema definitions:

### 1. Core Identity Tables (`00_core_identity.sql`)
- **machines**: Authoritative registry of all machines (hosts) that have generated events
- **component_instances**: Registry of all component instances (agent/DPI instances) with state tracking
- **component_identity_history**: Immutable historical log of identity changes (hostname, boot_id, agent_version)

### 2. Raw Events Storage (`01_raw_events.sql`)
- **raw_events**: Immutable storage of exact event envelopes as received
- **event_validation_log**: Immutable log of all validation operations (success and failure)
- **sequence_gaps**: Explicit tracking of sequence gaps per component instance

### 3. Normalized Agent Tables (`02_normalized_agent.sql`)
- **process_activity**: Normalized process activity events from agents
- **file_activity**: Normalized file activity events from agents
- **persistence**: Normalized persistence events from agents
- **network_intent**: Normalized network intent events from agents (before network activity)
- **health_heartbeat**: Normalized health/heartbeat events from agents

### 4. Normalized DPI Tables (`03_normalized_dpi.sql`)
- **dpi_flows**: Normalized network flows observed by DPI probe
- **dns**: Normalized DNS queries and responses observed by DPI probe
- **deception**: Normalized deception events (honeypot triggers, decoy access, etc.)

### 5. Correlation Tables (`04_correlation.sql`)
- **incidents**: Authoritative incident registry with immutable primary key
- **incident_stages**: Immutable log of all incident stage transitions (auditable)
- **evidence**: Evidence linkage (links events to incidents, many-to-many)
- **evidence_correlation_patterns**: Correlation patterns that link multiple events to an incident

### 6. AI Metadata Tables (`05_ai_metadata.sql`)
- **ai_model_versions**: Registry of AI model versions (immutable log of model deployments)
- **feature_vectors**: Feature vectors computed from events (references only, not blobs)
- **clusters**: Clusters identified by AI/ML algorithms
- **cluster_memberships**: Many-to-many relationship (events belong to clusters)
- **novelty_scores**: Novelty scores computed by AI for events
- **shap_explanations**: SHAP explanations for AI predictions (references, not blobs)

### 7. Index Strategy (`06_indexes.sql`)
- Additional composite indexes for common query patterns
- Index maintenance strategies and documentation
- Index usage notes and performance considerations

### 8. Partitioning and Retention (`07_retention.sql`)
- Time-based partitioning strategy (monthly partitions)
- Retention policy: Hot (3 months), Warm (1 year), Cold (7 years), Archive (indefinite)
- Partition management functions and automation

---

## Schema Design Principles

### Database-First Philosophy
- **Schema is not derived from code**: Schema is authoritative and immutable
- **Code will adapt to schema**: All future code must conform to this schema
- **No dynamic columns**: All columns are explicitly defined
- **No JSON blobs for core facts**: JSONB only where explicitly justified (e.g., opaque payloads, flexible metadata)

### Machine-First Modeling
- **Host-centric design**: Tables are organized around machines/hosts, not events
- **Time-indexed everywhere**: All time-indexed tables support efficient time-range queries
- **Immutable primary keys**: All primary keys are UUIDs or BIGSERIAL (never reused)

### Explicit Relationships
- **Foreign keys**: All relationships are explicitly defined with foreign key constraints
- **Deterministic querying**: Schema supports deterministic, reproducible queries
- **Referential integrity**: ON DELETE RESTRICT ensures data integrity

### Production-Grade Requirements
- **Zero data support**: Schema handles empty state correctly
- **One event support**: Schema handles minimal state correctly
- **Partial failure support**: Schema supports graceful degradation
- **Adversarial input support**: Schema includes validation constraints
- **Multi-year growth support**: Schema includes partitioning and retention policies

---

## Compatibility Rules

### Breaking vs Non-Breaking Changes

**CRITICAL**: This schema bundle is **IMMUTABLE** and **FROZEN**. No changes are permitted after finalization and hash insertion.

**Hypothetical Future Compatibility Rules** (for reference only – not applicable to v1.0):

#### Breaking Changes (Require New Major Version and Migration)
- Adding required columns to existing tables
- Removing columns from existing tables
- Changing column types (e.g., VARCHAR → INTEGER, INTEGER → BIGINT)
- Changing column constraints (e.g., NULL → NOT NULL, removing CHECK constraints)
- Adding or removing PRIMARY KEY constraints
- Adding or removing FOREIGN KEY constraints
- Changing ENUM values (adding values is non-breaking, removing values is breaking)
- Changing partition key columns
- Changing retention policies (reducing retention period is breaking)

#### Non-Breaking Changes (Allow Minor/Patch Version Increment with Migration)
- Adding nullable columns with default values
- Adding indexes (performance improvement, no functional change)
- Adding new tables (no impact on existing tables)
- Adding new ENUM values (extending enum)
- Adding CHECK constraints (tightening validation)
- Adding comments (documentation only)

**Note**: For RansomEye v1.0, the above rules are academic only. This bundle is **FROZEN** and will never change. Any modifications require creating a new version (v2.0.0) with a new bundle and migration scripts.

---

## Migration Rules

### Schema Versioning
- **Version format**: Semantic versioning (MAJOR.MINOR.PATCH)
- **Version bumps**: 
  - MAJOR: Breaking changes (requires data migration)
  - MINOR: Non-breaking additions (may require data migration for new features)
  - PATCH: Documentation, index additions (no data migration)
- **Migration scripts**: All schema changes MUST include migration scripts (up and down)
- **Migration testing**: All migrations MUST be tested on production-like data volumes

### Migration Requirements
1. **Backward compatibility**: Migrations must maintain backward compatibility during rollout
2. **Zero-downtime**: Migrations must support zero-downtime deployments (if applicable)
3. **Rollback support**: All migrations must include rollback scripts (down migrations)
4. **Data validation**: All migrations must include data validation steps
5. **Performance testing**: All migrations must be performance tested on production volumes

### Migration Script Naming
- Format: `migration_YYYYMMDD_HHMMSS_<description>.sql`
- Up migration: `migration_YYYYMMDD_HHMMSS_<description>_up.sql`
- Down migration: `migration_YYYYMMDD_HHMMSS_<description>_down.sql`

### Migration Execution
- Migrations MUST be executed in order (sequential)
- Migrations MUST be idempotent (safe to run multiple times)
- Migrations MUST be transactional (ALL or NOTHING)
- Migrations MUST be logged (audit trail)

---

## Freeze Statement

**FROZEN AS OF**: `2026-01-12`

**STATUS**: `FROZEN — DO NOT MODIFY`

This schema bundle is **IMMUTABLE** and **CANONICAL**.

### Immutability Rules

1. **NO MODIFICATIONS ALLOWED**: After finalization and hash insertion, this schema MUST NOT be modified under any circumstances.

2. **NO EXTENSIONS ALLOWED**: Code MUST NOT extend this schema. Any additional tables, columns, or constraints are violations and will result in rejection.

3. **NO INTERPRETATION VARIANCE**: All code MUST implement this schema exactly as specified. No deviation, no "interpretation", no "convenience" modifications.

4. **CONFORMANCE IS MANDATORY**: All future code in RansomEye v1.0 MUST conform to this schema. Any code that violates this schema MUST be rejected and deleted.

5. **MIGRATION IS REQUIRED**: Any schema changes require:
   - New schema version (major version bump)
   - Migration scripts (up and down)
   - Data validation
   - Performance testing
   - Approval process

### Enforcement

- **Schema Validation**: All database operations MUST validate against this schema before execution.
- **Foreign Key Enforcement**: All foreign keys MUST be enforced (ON DELETE RESTRICT).
- **Constraint Enforcement**: All constraints MUST be enforced (CHECK, NOT NULL, UNIQUE, etc.).

### Consequences of Violation

Any component, service, or system that violates this schema:

1. **WILL BE REJECTED** during code review
2. **WILL BE DELETED** if discovered post-deployment
3. **WILL NOT BE SUPPORTED** as part of RansomEye v1.0

### Approval Process

This bundle requires explicit approval before finalization:

- [ ] Schema bundle reviewed and approved
- [ ] All schema files validated for completeness and correctness
- [ ] All indexes validated for query patterns
- [ ] All partitioning strategies validated for retention policies
- [ ] PostgreSQL 14+ compatibility verified
- [ ] SHA256 hash computed and inserted
- [ ] Freeze date recorded
- [ ] Bundle declared FROZEN

**Current Status**: `FROZEN — DO NOT MODIFY`

---

## Schema Alignment with System Contracts

This schema is **exactly aligned** with the frozen system contracts from Phase 1:

### Event Envelope Contract
- **raw_events** table stores exact event envelopes (all required fields)
- **component_type** enum matches event envelope enum exactly (`linux_agent`, `windows_agent`, `dpi`, `core`)
- **event_id** is UUID v4 (matches schema)
- **sequence** is BIGINT (covers uint64 range: 0 to 2^64-1)
- **hash_sha256** and **prev_hash_sha256** are CHAR(64) (matches SHA256 format)
- **observed_at** and **ingested_at** are TIMESTAMPTZ (RFC3339 UTC converted)

### Time Semantics Contract
- **observed_at** and **ingested_at** are TIMESTAMPTZ (UTC timezone)
- **late_arrival** flag tracks late arrival events (ingested_at - observed_at > 1 hour)
- **arrival_latency_seconds** stores latency for late arrival events
- **sequence_gaps** table explicitly tracks sequence gaps per component instance

### Failure Semantics Contract
- **component_state** enum matches failure semantics exactly (`HEALTHY`, `DEGRADED`, `STALE`, `FAILED`, `BROKEN`)
- **event_validation_status** enum tracks validation status from failure semantics
- **integrity_chain_broken** flag tracks broken integrity chains
- **validation_log** table tracks all validation operations (explicit state, log classification)

---

## PostgreSQL Requirements

### Version
- **Minimum**: PostgreSQL 14.0
- **Recommended**: PostgreSQL 15+ (better partitioning and performance)

### Extensions
- **pg_trgm**: Required for trigram text search (GIN indexes on text columns)
  ```sql
  CREATE EXTENSION IF NOT EXISTS pg_trgm;
  ```

### Configuration
- **Time zone**: UTC (required for TIMESTAMPTZ consistency)
  ```sql
  SET timezone = 'UTC';
  ```
- **Partitioning**: Enabled (default in PostgreSQL 14+)
- **Foreign keys**: Enabled (default)
- **Constraints**: Enabled (default)

### Performance Settings
- **shared_buffers**: Tune based on available RAM (typically 25% of RAM)
- **effective_cache_size**: Tune based on available RAM (typically 50-75% of RAM)
- **maintenance_work_mem**: Increase for index builds and vacuum operations
- **work_mem**: Tune for query performance (sorting, hash joins)

---

## Schema Statistics

### Table Count
- **Core Identity**: 3 tables
- **Raw Events**: 3 tables
- **Normalized Agent**: 5 tables
- **Normalized DPI**: 3 tables
- **Correlation**: 4 tables
- **AI Metadata**: 6 tables
- **Total**: 24 tables

### Index Count
- **Primary Keys**: 24 (one per table)
- **Foreign Keys**: ~40 (relationships)
- **Time-based Indexes**: ~15 (time-indexed queries)
- **Machine-centric Indexes**: ~10 (host-centric queries)
- **Composite Indexes**: ~20 (common query patterns)
- **Partial Indexes**: ~10 (filtered queries)
- **GIN Indexes**: ~5 (text search, array queries)
- **Total**: ~120 indexes

### Partitioning Strategy
- **Partitioned Tables**: ~15 (all time-indexed tables)
- **Partition Granularity**: Monthly
- **Default Retention**: 7 years (hot: 3 months, warm: 1 year, cold: 7 years, archive: indefinite)

---

## Legal and Status

**Schema Bundle Status**: `FROZEN — DO NOT MODIFY`  
**Schema Bundle Version**: `1.0.0`  
**Schema Bundle Phase**: `Phase 2 – Database First`  
**Immutable After**: `2026-01-12`  
**SHA256 Hash**: `14144a0838f7fbf412f4510a708be4a76dd5fa07c90e539c3a90aa5bbf256acd`  
**PostgreSQL Version**: `14+`

**THIS BUNDLE IS FROZEN AND CANNOT BE MODIFIED.**

---

**END OF SCHEMA BUNDLE**
