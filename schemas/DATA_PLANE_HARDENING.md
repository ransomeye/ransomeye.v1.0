# RansomEye v1.0 Data-Plane Hardening Architecture

**AUTHORITATIVE:** Bulletproof data-plane architecture for massive concurrent writes, zero corruption, and strict access control

## Overview

This document defines the hardened data-plane architecture ensuring:
- **Zero data corruption**: All writes are atomic, validated, and auditable
- **Massive concurrency**: Handles 1,000,000+ concurrent writes/reads safely
- **Strict access control**: Every module writes ONLY to designated tables, reads ONLY via approved views
- **Co-located deployment**: Core + DPI + Linux Agent on same machine without conflicts
- **Predictable performance**: No lock contention, no table bloat, no index storms

---

## STEP 1 — WRITE/READ OWNERSHIP MATRIX (CRITICAL)

### Binding Rules

1. **Agents NEVER read DB**: Agents are write-only (telemetry ingestion)
2. **DPI NEVER reads agent tables**: DPI writes only to DPI tables
3. **Core reads via views only**: Core never reads raw tables directly
4. **No direct cross-module table reads**: All cross-module access via views

### Ownership Matrix

| Module | WRITE Tables | READ Tables | READ Method |
|--------|-------------|-------------|-------------|
| **Linux Agent** | `raw_events` (INSERT only)<br>`machines` (UPSERT via trigger)<br>`component_instances` (UPSERT via trigger) | **NONE** | **N/A** (Agents never read) |
| **Windows Agent** | `raw_events` (INSERT only)<br>`machines` (UPSERT via trigger)<br>`component_instances` (UPSERT via trigger) | **NONE** | **N/A** (Agents never read) |
| **DPI Probe** | `raw_events` (INSERT only)<br>`machines` (UPSERT via trigger)<br>`component_instances` (UPSERT via trigger) | **NONE** | **N/A** (DPI never reads) |
| **Core Ingest Service** | `raw_events` (INSERT only)<br>`event_validation_log` (INSERT only)<br>`sequence_gaps` (INSERT only)<br>`machines` (UPSERT via trigger)<br>`component_instances` (UPSERT via trigger) | **NONE** (Ingest is write-only) | **N/A** |
| **Core Normalization Service** | `process_activity` (INSERT only)<br>`file_activity` (INSERT only)<br>`persistence` (INSERT only)<br>`network_intent` (INSERT only)<br>`health_heartbeat` (INSERT only)<br>`dpi_flows` (INSERT only)<br>`dns` (INSERT only)<br>`deception` (INSERT only) | `raw_events` | **View**: `v_raw_events_normalization` (filtered, read-only) |
| **Core Correlation Engine** | `incidents` (INSERT/UPDATE)<br>`incident_stages` (INSERT only)<br>`evidence` (INSERT only)<br>`evidence_correlation_patterns` (INSERT only) | `raw_events`<br>`process_activity`<br>`file_activity`<br>`network_intent`<br>`dpi_flows`<br>`dns` | **Views**: `v_raw_events_correlation`<br>`v_process_activity_correlation`<br>`v_file_activity_correlation`<br>`v_network_intent_correlation`<br>`v_dpi_flows_correlation`<br>`v_dns_correlation` |
| **Core AI Service** | `ai_model_versions` (INSERT only)<br>`feature_vectors` (INSERT only)<br>`clusters` (INSERT/UPDATE)<br>`cluster_memberships` (INSERT only)<br>`novelty_scores` (INSERT only)<br>`shap_explanations` (INSERT only) | `raw_events`<br>`process_activity`<br>`file_activity`<br>`network_intent` | **Views**: `v_raw_events_ai`<br>`v_process_activity_ai`<br>`v_file_activity_ai`<br>`v_network_intent_ai` |
| **Core Policy Engine** | **NONE** (Policy engine does not write to DB) | `incidents`<br>`evidence`<br>`process_activity`<br>`file_activity` | **Views**: `v_incidents_policy`<br>`v_evidence_policy`<br>`v_process_activity_policy`<br>`v_file_activity_policy` |
| **Core UI/API** | **NONE** (UI is read-only) | All tables | **Views**: `v_*_ui` (read-only, filtered, aggregated) |

### View Definitions (Read-Only Access)

**View Naming Convention**: `v_<table>_<module>` (e.g., `v_raw_events_correlation`)

**View Rules**:
- All views are `WITH CHECK OPTION` (read-only enforcement)
- Views filter by `component` or `machine_id` where applicable
- Views exclude sensitive fields (PII, internal metadata)
- Views include only columns needed by consuming module

**Example View**:
```sql
CREATE VIEW v_raw_events_correlation AS
SELECT 
    event_id,
    machine_id,
    component_instance_id,
    component,
    observed_at,
    ingested_at,
    sequence,
    payload,
    validation_status
FROM raw_events
WHERE validation_status = 'VALID'
WITH CHECK OPTION;
```

### Database Role-Based Access Control (RBAC)

**PostgreSQL Roles**:
- `ransomeye_agent_linux`: INSERT on `raw_events`, UPSERT on `machines`, `component_instances`
- `ransomeye_agent_windows`: INSERT on `raw_events`, UPSERT on `machines`, `component_instances`
- `ransomeye_dpi`: INSERT on `raw_events`, UPSERT on `machines`, `component_instances`
- `ransomeye_ingest`: INSERT on `raw_events`, `event_validation_log`, `sequence_gaps`
- `ransomeye_normalization`: INSERT on normalized tables, SELECT on `v_raw_events_normalization`
- `ransomeye_correlation`: INSERT/UPDATE on `incidents`, `incident_stages`, `evidence`, SELECT on correlation views
- `ransomeye_ai`: INSERT on AI metadata tables, SELECT on AI views
- `ransomeye_policy`: SELECT on policy views (read-only)
- `ransomeye_ui`: SELECT on UI views (read-only)

**Role Enforcement**:
- Each module connects with its designated role
- GRANT statements enforce write/read permissions
- REVOKE ALL on base tables from all roles (force view usage)
- GRANT SELECT on views to appropriate roles

---

## STEP 2 — SCHEMA HARDENING STRATEGY

### Event Ingestion Tables (Append-Only)

**Tables**: `raw_events`, `event_validation_log`, `sequence_gaps`

**Characteristics**:
- **Append-only**: INSERT only, no UPDATE/DELETE
- **Partitioned**: Monthly partitions by `ingested_at` (for `raw_events`)
- **Indexed**: Minimal indexes (write-optimized)
- **Logged**: WAL enabled (data integrity critical)

**Partitioning Strategy**:
- **Partition Key**: `ingested_at` (TIMESTAMPTZ)
- **Partition Granularity**: Monthly (1 partition per month)
- **Partition Naming**: `raw_events_YYYY_MM` (e.g., `raw_events_2025_01`)
- **Partition Creation**: Pre-create 3 months ahead (automated)
- **Partition Retention**: Hot (3 months), Warm (1 year), Cold (7 years), Archive (indefinite)

**Indexing Strategy**:
- **PRIMARY KEY**: `(event_id, ingested_at)` - Composite key includes partition key
- **Indexes**: 
  - `idx_raw_events_machine_id` (BTREE, local to partition)
  - `idx_raw_events_component_instance_id` (BTREE, local to partition)
  - `idx_raw_events_ingested_at` (BRIN, local to partition) - For time-range queries
  - `idx_raw_events_validation_status` (BTREE, partial: `WHERE validation_status != 'VALID'`)
  - `idx_raw_events_hash_sha256` (BTREE, unique, local to partition) - For integrity chain validation

**WAL Tuning**:
- **WAL Level**: `replica` (required for replication, if used)
- **WAL Segment Size**: 16MB (default)
- **Checkpoint Frequency**: `checkpoint_timeout = 5min`, `max_wal_size = 4GB`
- **WAL Archiving**: Enabled for archive partitions (if replication used)

### Normalized Tables (Append-Only)

**Tables**: `process_activity`, `file_activity`, `persistence`, `network_intent`, `health_heartbeat`, `dpi_flows`, `dns`, `deception`

**Characteristics**:
- **Append-only**: INSERT only, no UPDATE/DELETE
- **Partitioned**: Monthly partitions by `observed_at`
- **Indexed**: Minimal indexes (write-optimized)
- **Logged**: WAL enabled

**Partitioning Strategy**:
- **Partition Key**: `observed_at` (TIMESTAMPTZ)
- **Partition Granularity**: Monthly
- **Partition Naming**: `<table>_YYYY_MM` (e.g., `process_activity_2025_01`)

**Indexing Strategy**:
- **PRIMARY KEY**: `(id, observed_at)` - Composite key includes partition key
- **Indexes** (per table):
  - `idx_<table>_event_id` (BTREE, local to partition) - Foreign key to `raw_events`
  - `idx_<table>_machine_id` (BTREE, local to partition) - Host-centric queries
  - `idx_<table>_observed_at` (BRIN, local to partition) - Time-range queries
  - **Table-specific indexes** (minimal, write-optimized):
    - `process_activity`: `idx_process_activity_process_pid` (BTREE), `idx_process_activity_parent_pid` (BTREE)
    - `file_activity`: `idx_file_activity_file_path` (GIN with trigram, partial: `WHERE file_path IS NOT NULL`)
    - `network_intent`: `idx_network_intent_dest_ip` (BTREE), `idx_network_intent_dest_port` (BTREE)
    - `dpi_flows`: `idx_dpi_flows_local_ip` (BTREE), `idx_dpi_flows_remote_ip` (BTREE), `idx_dpi_flows_active` (BTREE, partial: `WHERE flow_ended_at IS NULL`)
    - `dns`: `idx_dns_query_name` (BTREE), `idx_dns_resolved_ips` (GIN, for INET[])

### Correlation Tables (HOT Updates)

**Tables**: `incidents`, `incident_stages`, `evidence`, `evidence_correlation_patterns`

**Characteristics**:
- **HOT Updates**: `incidents` table has UPDATE operations (stage transitions, evidence count)
- **Partitioned**: Monthly partitions by `first_observed_at` (for `incidents`)
- **Indexed**: Write-optimized indexes
- **Logged**: WAL enabled

**Partitioning Strategy**:
- **Partition Key**: `first_observed_at` (for `incidents`), `observed_at` (for `evidence`)
- **Partition Granularity**: Monthly

**Indexing Strategy**:
- **PRIMARY KEY**: `(incident_id, first_observed_at)` - Composite key includes partition key
- **Indexes**:
  - `idx_incidents_machine_id` (BTREE, local to partition)
  - `idx_incidents_current_stage` (BTREE, local to partition)
  - `idx_incidents_first_observed_at` (BRIN, local to partition)
  - **HOT Update Optimization**: `fillfactor = 90` on `incidents` table (leave 10% free space for HOT updates)

**HOT Update Avoidance**:
- **Strategy**: Minimize UPDATE operations
- **Implementation**: Use `incident_stages` table for stage transitions (INSERT only)
- **UPDATE Operations**: Only for `incidents.current_stage`, `incidents.last_observed_at`, `incidents.total_evidence_count` (infrequent)
- **Fillfactor**: 90% (leave 10% free space for HOT updates)

### AI Metadata Tables (Append-Only)

**Tables**: `ai_model_versions`, `feature_vectors`, `clusters`, `cluster_memberships`, `novelty_scores`, `shap_explanations`

**Characteristics**:
- **Append-only**: INSERT only (except `clusters` which has UPDATE)
- **Partitioned**: Monthly partitions by `computed_at` or `created_at`
- **Indexed**: Minimal indexes
- **Logged**: WAL enabled

**Partitioning Strategy**:
- **Partition Key**: `computed_at` (for `feature_vectors`, `novelty_scores`, `shap_explanations`), `created_at` (for `clusters`, `cluster_memberships`)
- **Partition Granularity**: Monthly

**Indexing Strategy**:
- **PRIMARY KEY**: `(id, computed_at)` or `(id, created_at)` - Composite key includes partition key
- **Indexes**: Minimal (write-optimized)

### Identity Tables (Small, Infrequent Updates)

**Tables**: `machines`, `component_instances`, `component_identity_history`

**Characteristics**:
- **Not Partitioned**: Small tables (< 1M rows), infrequent updates
- **UPSERT Operations**: `machines` and `component_instances` use UPSERT (INSERT ... ON CONFLICT UPDATE)
- **Indexed**: Standard BTREE indexes
- **Logged**: WAL enabled

**UPSERT Strategy**:
- **Implementation**: `INSERT ... ON CONFLICT (primary_key) DO UPDATE`
- **Trigger-Based**: UPSERT handled by database triggers (from `raw_events` INSERT)
- **Lock Contention**: Minimal (UPSERT on unique keys, row-level locks)

### UNLOGGED vs LOGGED Tables

**UNLOGGED Tables**: **NONE** (all tables are LOGGED)

**Rationale**:
- **Data Integrity**: All tables contain security-critical data (events, incidents, evidence)
- **Replication**: WAL required for replication (if used)
- **Recovery**: WAL required for point-in-time recovery
- **Zero Corruption**: WAL ensures atomic writes and crash recovery

**Exception**: Temporary staging tables (if used) may be UNLOGGED, but must be explicitly documented.

### BRIN vs BTREE Indexes

**BRIN Indexes** (Block Range Indexes):
- **Use Cases**: Time-range queries on partitioned tables
- **Tables**: `raw_events.ingested_at`, `process_activity.observed_at`, `file_activity.observed_at`, etc.
- **Rationale**: BRIN indexes are write-optimized (minimal overhead on INSERT), efficient for time-range queries on ordered data
- **Maintenance**: Auto-maintained by PostgreSQL (no manual maintenance)

**BTREE Indexes**:
- **Use Cases**: Equality and range queries on non-time columns
- **Tables**: All foreign keys, machine_id, component_instance_id, process_pid, etc.
- **Rationale**: BTREE indexes provide optimal performance for equality and range queries
- **Maintenance**: Auto-maintained by PostgreSQL (VACUUM, REINDEX)

**GIN Indexes**:
- **Use Cases**: Full-text search, array queries, JSONB queries
- **Tables**: `file_activity.file_path` (trigram), `dns.resolved_ips` (INET[]), `raw_events.payload` (JSONB, if needed)
- **Rationale**: GIN indexes support complex queries but have higher write overhead
- **Maintenance**: Auto-maintained by PostgreSQL

### Partitioned Tables Summary

**Partitioned Tables**:
- `raw_events` (by `ingested_at`)
- `process_activity` (by `observed_at`)
- `file_activity` (by `observed_at`)
- `persistence` (by `observed_at`)
- `network_intent` (by `observed_at`)
- `health_heartbeat` (by `observed_at`)
- `dpi_flows` (by `observed_at`)
- `dns` (by `observed_at`)
- `deception` (by `observed_at`)
- `incidents` (by `first_observed_at`)
- `evidence` (by `observed_at`)
- `feature_vectors` (by `computed_at`)
- `novelty_scores` (by `computed_at`)
- `shap_explanations` (by `computed_at`)
- `clusters` (by `created_at`)
- `cluster_memberships` (by `created_at`)
- `component_identity_history` (by `first_observed_at`)

**Non-Partitioned Tables**:
- `machines` (small, < 1M rows)
- `component_instances` (small, < 1M rows)
- `event_validation_log` (small, < 10M rows, append-only)
- `sequence_gaps` (small, < 1M rows, append-only)
- `incident_stages` (small, < 10M rows, append-only)
- `evidence_correlation_patterns` (small, < 1M rows, append-only)
- `ai_model_versions` (very small, < 1000 rows)

---

## STEP 3 — HIGH-CONCURRENCY INGEST DESIGN

### 1M+ Concurrent Inserts

**Challenge**: Handle 1,000,000+ concurrent INSERT operations without lock contention or performance degradation.

**Solution**: **COPY-based batch ingestion** with connection pooling and partition-aware routing.

**Implementation**:

1. **COPY vs INSERT Decision**:
   - **COPY**: Used for batch ingestion (1000-10000 events per batch)
   - **INSERT**: Used for single-event ingestion (real-time, low-latency)
   - **Hybrid**: COPY for bulk ingestion, INSERT for real-time ingestion

2. **Batch Sizes**:
   - **COPY Batch Size**: 10,000 events per COPY operation (optimal for 1M+ events)
   - **INSERT Batch Size**: 100-1000 events per transaction (for real-time ingestion)
   - **Connection Pool Size**: 100 connections (for concurrent ingestion)

3. **Partition-Aware Routing**:
   - **Pre-compute Partition**: Determine target partition from `ingested_at` before INSERT
   - **Partition Pruning**: PostgreSQL automatically routes INSERT to correct partition
   - **Partition Lock**: Row-level locks (no table-level locks on partitioned tables)

4. **Connection Pooling**:
   - **Pool Size**: 100 connections (for 1M+ concurrent operations)
   - **Pool Type**: `psycopg2.pool.ThreadedConnectionPool` or `asyncpg.Pool`
   - **Connection Reuse**: Reuse connections for batch operations
   - **Connection Timeout**: 30 seconds (fail-fast on connection exhaustion)

### Burst Traffic Handling

**Challenge**: Handle sudden bursts of events (10x normal rate) without dropping events or causing database overload.

**Solution**: **Queue-based ingestion** with backpressure and rate limiting.

**Implementation**:

1. **Ingest Queue**:
   - **Queue Type**: In-memory queue (Redis, RabbitMQ, or in-process queue)
   - **Queue Size**: 1,000,000 events (buffer for burst traffic)
   - **Queue Backend**: Redis Streams or RabbitMQ (persistent, durable)

2. **Backpressure from Core**:
   - **Queue Full Detection**: Monitor queue size, reject new events if queue > 90% full
   - **Rate Limiting**: Limit ingestion rate to database capacity (10,000 events/second)
   - **Circuit Breaker**: Stop ingestion if database errors exceed threshold (10 errors/second)

3. **Retry Semantics**:
   - **Retry Strategy**: Exponential backoff (1s, 2s, 4s, 8s, 16s, max 60s)
   - **Max Retries**: 10 retries per event
   - **Dead Letter Queue**: Events that fail after max retries are stored in dead letter queue
   - **Idempotency**: Event ID-based deduplication (reject duplicate `event_id`)

4. **No Duplicate Ingestion**:
   - **Primary Key Constraint**: `raw_events.event_id` is PRIMARY KEY (database-level duplicate rejection)
   - **Application-Level Deduplication**: Check `event_id` existence before INSERT (optional, for performance)
   - **Idempotent Operations**: All INSERT operations are idempotent (safe to retry)

### Failure Handling

**Database Connection Failures**:
- **Retry**: Exponential backoff (1s, 2s, 4s, 8s, 16s, max 60s)
- **Circuit Breaker**: Stop ingestion if connection failures exceed threshold (10 failures/minute)
- **Queue Persistence**: Events remain in queue during connection failures

**Database Write Failures**:
- **Retry**: Exponential backoff (same as connection failures)
- **Dead Letter Queue**: Events that fail after max retries are stored in dead letter queue
- **Error Classification**: Distinguish transient errors (retry) from permanent errors (dead letter)

**Partition Full Failures**:
- **Pre-create Partitions**: Create partitions 3 months ahead (automated)
- **Partition Creation on Demand**: Create partition if missing (fallback)
- **Partition Full Detection**: Monitor partition size, create new partition if > 90% full

### Queue-Based Ingest Architecture

```
Agent/DPI → Ingest Queue (Redis/RabbitMQ) → Ingest Service → PostgreSQL
                ↓
         Backpressure Detection
                ↓
         Rate Limiting
                ↓
         Circuit Breaker
```

**Queue Implementation**:
- **Redis Streams**: Persistent, durable, supports consumer groups
- **RabbitMQ**: Persistent, durable, supports message acknowledgments
- **In-Process Queue**: Python `queue.Queue` (for single-process deployment)

**Ingest Service**:
- **Workers**: 10-100 worker processes/threads (depending on load)
- **Batch Processing**: Process 10,000 events per batch (COPY operation)
- **Connection Pooling**: 100 connections per worker process
- **Error Handling**: Retry with exponential backoff, dead letter queue

---

## STEP 4 — CO-LOCATED POC SAFETY

### Port Separation

**Service Ports** (No Conflicts):

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| **Core Ingest Service** | 8000 | HTTP | Event ingestion endpoint |
| **Core API Service** | 8001 | HTTP | REST API endpoint |
| **Core UI Service** | 8002 | HTTP | Web UI endpoint |
| **DPI Probe** | 8003 | HTTP | DPI probe API (if exposed) |
| **Linux Agent** | **N/A** | **N/A** | No HTTP server (writes directly to DB) |
| **PostgreSQL** | 5432 | TCP | Database server |

**Port Binding**:
- **Explicit Binding**: All services bind to `127.0.0.1` (localhost only) or specific interface
- **Port Validation**: Validate port availability on startup (fail-fast if port in use)
- **Port Configuration**: Environment variables (`RANSOMEYE_INGEST_PORT`, `RANSOMEYE_API_PORT`, etc.)

### CPU Pinning Strategy

**CPU Affinity** (Isolate Services):

| Service | CPU Cores | Rationale |
|---------|-----------|-----------|
| **PostgreSQL** | Cores 0-3 | Database server (4 cores) |
| **Core Ingest Service** | Cores 4-5 | Event ingestion (2 cores) |
| **Core Normalization Service** | Cores 6-7 | Event normalization (2 cores) |
| **Core Correlation Engine** | Cores 8-9 | Correlation processing (2 cores) |
| **Core AI Service** | Cores 10-11 | AI processing (2 cores) |
| **DPI Probe** | Cores 12-13 | DPI packet processing (2 cores) |
| **Linux Agent** | Cores 14-15 | Agent telemetry (2 cores) |

**CPU Pinning Implementation**:
- **PostgreSQL**: `taskset -c 0-3 postgres`
- **Python Services**: `taskset -c 4-5 python3 services/ingest/app/main.py`
- **Systemd**: Use `CPUAffinity` in systemd unit files

**CPU Isolation**:
- **Isolated CPUs**: Reserve CPUs 0-15 for RansomEye services (via kernel boot parameters)
- **CPU Quota**: Use `cpu.cfs_quota_us` for CPU limits (if cgroups available)
- **CPU Monitoring**: Monitor CPU usage per service (alert if > 80% utilization)

### Memory Limits per Service

**Memory Limits** (Prevent Resource Starvation):

| Service | Memory Limit | Rationale |
|---------|--------------|-----------|
| **PostgreSQL** | 8GB | Database server (shared_buffers = 2GB, work_mem = 256MB) |
| **Core Ingest Service** | 2GB | Event ingestion (queue buffer, connection pool) |
| **Core Normalization Service** | 2GB | Event normalization (batch processing) |
| **Core Correlation Engine** | 4GB | Correlation processing (stateful, large working set) |
| **Core AI Service** | 4GB | AI processing (model inference, feature vectors) |
| **DPI Probe** | 1GB | DPI packet processing (flow state, packet buffers) |
| **Linux Agent** | 512MB | Agent telemetry (event buffering) |

**Memory Limit Implementation**:
- **Systemd**: Use `MemoryMax` in systemd unit files
- **Docker**: Use `--memory` flag (if containerized)
- **Cgroups**: Use `memory.limit_in_bytes` (if cgroups available)
- **OOM Killer**: Configure OOM killer to prioritize services (lower priority for non-critical services)

**Memory Monitoring**:
- **Alert Threshold**: Alert if memory usage > 80% of limit
- **OOM Prevention**: Kill non-critical services before critical services (PostgreSQL, Core Ingest)

### IO Scheduling Considerations

**IO Scheduler** (Optimize for Database Workload):

| Service | IO Scheduler | Priority | Rationale |
|---------|--------------|----------|-----------|
| **PostgreSQL** | `deadline` or `mq-deadline` | High | Database requires low-latency, predictable IO |
| **Core Services** | `deadline` or `mq-deadline` | Medium | Event processing requires consistent IO |
| **DPI Probe** | `deadline` or `mq-deadline` | Low | Packet processing is less IO-sensitive |

**IO Scheduler Configuration**:
- **Kernel Parameter**: `elevator=deadline` (for legacy schedulers) or use `mq-deadline` (for multi-queue)
- **Per-Device**: `echo deadline > /sys/block/sda/queue/scheduler`
- **IO Priority**: Use `ionice` to set IO priority (PostgreSQL: `-c 1 -n 0`, Core: `-c 2 -n 4`)

**IO Isolation**:
- **Separate Disks**: Use separate disks for PostgreSQL data and logs (if possible)
- **IO Limits**: Use `blkio.throttle.*` cgroup limits (if cgroups available)
- **IO Monitoring**: Monitor IO wait time per service (alert if > 100ms)

### Network Namespace / Socket Separation

**Network Namespace** (Optional, for Advanced Isolation):

- **Not Required**: Co-located POC does not require network namespaces (all services on localhost)
- **Future Consideration**: Network namespaces may be used for production deployment (multi-tenant)

**Socket Separation**:
- **Unix Domain Sockets**: Use Unix domain sockets for local communication (faster than TCP)
- **Socket Paths**: `/var/run/ransomeye/ingest.sock`, `/var/run/ransomeye/api.sock`, etc.
- **Socket Permissions**: Restrict socket permissions (600, owner-only)

---

## STEP 5 — GUARANTEES & FAILURE MODES

### What Failures are Tolerated

**Tolerated Failures** (System Continues Operation):

1. **Single Event Ingestion Failure**:
   - **Behavior**: Event is rejected, logged, and stored in dead letter queue
   - **Recovery**: Manual review of dead letter queue, retry after fix
   - **Impact**: Single event lost (not critical for system operation)

2. **Temporary Database Connection Failure**:
   - **Behavior**: Events are queued, retry with exponential backoff
   - **Recovery**: Automatic retry, events processed when connection restored
   - **Impact**: Temporary ingestion delay (events not lost)

3. **Partition Full**:
   - **Behavior**: New partition is created automatically (fallback)
   - **Recovery**: Automatic partition creation, events routed to new partition
   - **Impact**: Temporary ingestion delay (events not lost)

4. **Normalization Service Failure**:
   - **Behavior**: Raw events are stored, normalization deferred
   - **Recovery**: Normalization service processes backlog when restored
   - **Impact**: Normalized tables temporarily out of sync (raw events preserved)

5. **Correlation Engine Failure**:
   - **Behavior**: Events are stored, correlation deferred
   - **Recovery**: Correlation engine processes backlog when restored
   - **Impact**: Incidents temporarily not created (events preserved)

6. **AI Service Failure**:
   - **Behavior**: Events are stored, AI processing deferred
   - **Recovery**: AI service processes backlog when restored
   - **Impact**: AI metadata temporarily missing (events preserved)

### What Failures are Fatal

**Fatal Failures** (System Must Shutdown):

1. **Database Corruption**:
   - **Detection**: Checksum errors, constraint violations, data inconsistency
   - **Behavior**: System shutdown, manual intervention required
   - **Recovery**: Restore from backup, replay WAL, verify integrity

2. **Primary Key Violation (Duplicate event_id)**:
   - **Detection**: Database constraint violation on `raw_events.event_id`
   - **Behavior**: System shutdown (invariant violation)
   - **Recovery**: Manual investigation, fix duplicate event source

3. **Integrity Chain Breakage**:
   - **Detection**: `prev_hash_sha256` mismatch in `raw_events`
   - **Behavior**: Mark component instance as `integrity_chain_broken`, reject subsequent events
   - **Recovery**: Manual investigation, fix component instance

4. **Partition Creation Failure**:
   - **Detection**: Cannot create new partition (disk full, permissions, etc.)
   - **Behavior**: System shutdown (cannot ingest new events)
   - **Recovery**: Fix underlying issue (disk space, permissions), create partition manually

5. **WAL Full**:
   - **Detection**: WAL directory full, cannot write WAL segments
   - **Behavior**: System shutdown (data integrity at risk)
   - **Recovery**: Free WAL space, archive old WAL segments, restart

### How Corruption is Prevented

**Corruption Prevention Mechanisms**:

1. **Atomic Writes**:
   - **Transaction Isolation**: All writes are in transactions (ACID guarantees)
   - **WAL**: Write-Ahead Logging ensures atomicity (all-or-nothing)
   - **Constraint Enforcement**: Database constraints prevent invalid data

2. **Primary Key Constraints**:
   - **Duplicate Prevention**: `event_id` PRIMARY KEY prevents duplicate events
   - **Integrity**: Foreign key constraints ensure referential integrity

3. **Checksum Validation**:
   - **Event Hash**: `hash_sha256` validates event integrity
   - **Integrity Chain**: `prev_hash_sha256` validates event sequence
   - **Database Checksums**: PostgreSQL page-level checksums (if enabled)

4. **Constraint Validation**:
   - **CHECK Constraints**: Validate data ranges, formats, relationships
   - **NOT NULL Constraints**: Prevent missing required fields
   - **Foreign Key Constraints**: Ensure referential integrity

5. **Audit Logging**:
   - **Event Validation Log**: All validation operations are logged
   - **Sequence Gaps**: Sequence gaps are explicitly tracked
   - **Integrity Chain Breaks**: Integrity chain breaks are logged and tracked

### How Partial Writes are Handled

**Partial Write Prevention**:

1. **Transaction Boundaries**:
   - **Single Transaction**: All related writes are in single transaction
   - **Atomicity**: Transaction commit ensures all-or-nothing
   - **Rollback**: Transaction rollback on any error (no partial writes)

2. **Foreign Key Constraints**:
   - **Referential Integrity**: Foreign keys ensure parent records exist
   - **Cascade Rules**: `ON DELETE RESTRICT` prevents orphaned records
   - **Deferred Constraints**: Use `DEFERRABLE INITIALLY DEFERRED` for complex relationships

3. **Trigger-Based UPSERT**:
   - **Atomic UPSERT**: `INSERT ... ON CONFLICT UPDATE` is atomic
   - **Trigger Execution**: Triggers execute within same transaction
   - **Error Handling**: Trigger errors cause transaction rollback

4. **Batch Processing**:
   - **COPY Operation**: COPY is atomic (all rows or none)
   - **Batch Size**: Small batches (1000-10000 rows) reduce partial write risk
   - **Error Handling**: Batch errors cause entire batch rollback

### How Replay Works

**Replay Mechanism**:

1. **Event Replay**:
   - **Source**: Replay from `raw_events` table (immutable log)
   - **Method**: Query `raw_events` by `ingested_at` or `observed_at` time range
   - **Processing**: Re-process events through normalization, correlation, AI services
   - **Idempotency**: All processing is idempotent (safe to replay)

2. **Normalization Replay**:
   - **Source**: Query `raw_events` where `validation_status = 'VALID'`
   - **Method**: Process events through normalization service
   - **Deduplication**: Check if normalized record exists (by `event_id`) before INSERT
   - **Idempotency**: `INSERT ... ON CONFLICT DO NOTHING` ensures idempotency

3. **Correlation Replay**:
   - **Source**: Query normalized tables (`process_activity`, `file_activity`, etc.)
   - **Method**: Re-run correlation engine on historical events
   - **Deduplication**: Check if incident exists (by `incident_id`) before INSERT
   - **Idempotency**: Correlation patterns are deterministic (same events → same incidents)

4. **AI Replay**:
   - **Source**: Query normalized tables or `raw_events`
   - **Method**: Re-run AI service on historical events
   - **Deduplication**: Check if feature vector exists (by `event_id`, `model_version_id`) before INSERT
   - **Idempotency**: AI processing is deterministic (same events → same features)

5. **Replay Tools**:
   - **CLI Tool**: `tools/replay_events.py` - Replay events from time range
   - **API Endpoint**: `POST /api/v1/replay` - Replay events via API
   - **Batch Processing**: Process events in batches (10,000 events per batch)

---

## Explicit List of Remaining Risks

### 1. Database Connection Pool Exhaustion

**Risk**: Under extreme load (10M+ events/second), connection pool may be exhausted.

**Mitigation**:
- **Pool Size**: Increase pool size to 1000 connections (if needed)
- **Connection Timeout**: Reduce connection timeout to 10 seconds (fail-fast)
- **Queue Backpressure**: Reject events if connection pool > 90% full

**Status**: **ACCEPTABLE RISK** (mitigated by queue backpressure)

### 2. Partition Lock Contention

**Risk**: Concurrent INSERTs to same partition may cause lock contention.

**Mitigation**:
- **Partition Granularity**: Monthly partitions (spread load across partitions)
- **Row-Level Locks**: PostgreSQL uses row-level locks (minimal contention)
- **Partition Pruning**: Queries filter by partition key (reduces lock scope)

**Status**: **ACCEPTABLE RISK** (mitigated by partition granularity)

### 3. Index Bloat on High-Volume Tables

**Risk**: High-volume INSERTs may cause index bloat (performance degradation).

**Mitigation**:
- **BRIN Indexes**: Use BRIN indexes for time-range queries (minimal bloat)
- **Partial Indexes**: Use partial indexes (reduce index size)
- **VACUUM**: Regular VACUUM on partitions (auto-vacuum enabled)

**Status**: **ACCEPTABLE RISK** (mitigated by BRIN indexes and VACUUM)

### 4. WAL Growth Under Burst Traffic

**Risk**: Burst traffic may cause WAL to grow rapidly (disk space exhaustion).

**Mitigation**:
- **WAL Archiving**: Archive WAL segments to external storage
- **Checkpoint Frequency**: Increase checkpoint frequency (reduce WAL size)
- **WAL Monitoring**: Monitor WAL size, alert if > 80% of disk space

**Status**: **ACCEPTABLE RISK** (mitigated by WAL archiving)

### 5. Dead Letter Queue Growth

**Risk**: Persistent failures may cause dead letter queue to grow unbounded.

**Mitigation**:
- **Queue Size Limit**: Limit dead letter queue size (1M events)
- **Queue Retention**: Retain events for 30 days, then archive
- **Manual Review**: Regular manual review of dead letter queue

**Status**: **ACCEPTABLE RISK** (mitigated by queue size limits)

### 6. Co-Located Resource Contention

**Risk**: Co-located services may compete for CPU, memory, IO resources.

**Mitigation**:
- **CPU Pinning**: Pin services to specific CPU cores
- **Memory Limits**: Set memory limits per service
- **IO Scheduling**: Use deadline scheduler, set IO priorities

**Status**: **ACCEPTABLE RISK** (mitigated by resource isolation)

---

**AUTHORITATIVE**: This data-plane hardening architecture is the single authoritative source for database safety, scale, and access control.

**STATUS**: Data-plane hardened. Ready to proceed to Phase B.
