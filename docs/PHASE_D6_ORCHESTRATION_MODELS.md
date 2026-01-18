# PHASE D.6 — ORCHESTRATION MODEL CONSOLIDATION

**Status**: COMPLETE  
**Date**: 2026-01-18  
**Purpose**: Define exactly one authoritative orchestration model for RansomEye Core v1.0

---

## D.6.1 — Enumerated Orchestration Models

### Model 1: Unified Single-Service Core (Orchestrator Mode)

**Description**: Core starts and manages all components as child processes. Only ONE systemd service exists.

**Required systemd units**:
- `ransomeye-core.service` (ONE service only)

**Required environment flags**:
- `RANSOMEYE_ORCHESTRATOR` MUST NOT be set, OR set to empty string, OR set to any value other than "systemd"
- Components started by Core receive `RANSOMEYE_ORCHESTRATOR=core` in their environment (set by ComponentAdapter)

**Expected health checks**:
- Core orchestrator starts components via `ComponentAdapter.start()`
- Core orchestrator supervises component health via `ComponentAdapter.health()`
- Components run as child processes of Core

**Backup requirements**:
- `ransomeye-core.service` must exist
- Individual component service files (`.service`) must NOT exist
- Environment file must NOT have `RANSOMEYE_ORCHESTRATOR=systemd`

**Runtime behavior**:
- Core's orchestrator runs in orchestrator mode (starts components)
- Components are started via `Popen()` with environment from Core
- Core manages component lifecycle (start/stop/restart)

---

### Model 2: systemd-Managed Multi-Service Core (Supervision Mode) — UNSUPPORTED for v1.0

**Description**: systemd manages each component as a separate service. Core only supervises.

**Required systemd units**:
- `ransomeye-core.service` (supervision only)
- `ransomeye-secure-bus.service`
- `ransomeye-ingest.service`
- `ransomeye-core-runtime.service`
- `ransomeye-correlation-engine.service`
- `ransomeye-policy-engine.service`
- `ransomeye-ai-core.service`
- `ransomeye-llm-soc.service`
- `ransomeye-ui.service`
- `ransomeye.target` (target unit)

**Required environment flags**:
- `RANSOMEYE_ORCHESTRATOR=systemd` (MUST be set in environment file)
- Each component service file must have `Environment=RANSOMEYE_ORCHESTRATOR=systemd`

**Expected health checks**:
- Core checks if component systemd services are active via `systemctl is-active`
- Core does NOT start components (systemd manages lifecycle)
- Components check `_assert_supervised()` which requires `RANSOMEYE_ORCHESTRATOR=systemd`

**Backup requirements**:
- All individual component service files must exist
- Environment file must have `RANSOMEYE_ORCHESTRATOR=systemd`
- `ransomeye.target` must exist

**Runtime behavior**:
- Core's orchestrator runs in supervision mode (does not start components)
- Components are managed by systemd (not Core)
- Core only monitors health of systemd-managed services

**STATUS**: **UNSUPPORTED FOR v1.0** - Installer does not create individual component services. This model is incompatible with installer design.

---

## D.6.2 — Authoritative Model Selection

### Chosen Model: **Unified Single-Service Core (Orchestrator Mode)**

### Justification:

1. **Installer Design**: Installer creates ONE service (`ransomeye-core.service`) only (install.sh line 688-710). Installing multiple services would require installer changes.

2. **Backup Compatibility**: Backup/restore works with single service. Multi-service model requires all component services in backup, which backup script does not guarantee.

3. **Fail-Closed Guarantees**: Single-service model simplifies recovery - only one unit to restore. Multi-service model creates multiple failure points.

4. **Recovery Baseline**: PHASE D.5 recovery baseline assumes single unified service. Multi-service model contradicts recovery contract.

5. **No Installer Dependency**: Single-service model does not require installer changes. Multi-service model requires new installer logic.

6. **Runtime Simplicity**: Core manages components directly. No need to coordinate with systemd for component lifecycle.

### Unsupported Models:

- **systemd-Managed Multi-Service Core**: UNSUPPORTED for v1.0 (incompatible with installer, backup, and recovery baseline)

---

## D.6.3 — Model Enforcement Implementation

### Hard Enforcement Points:

#### 1. Installer Enforcement

**File**: `installer/core/install.sh` (generate_environment_file)

**Change**: Ensure `RANSOMEYE_ORCHESTRATOR` is NOT set (or explicitly set to empty)

**Enforcement**: Installer MUST NOT set `RANSOMEYE_ORCHESTRATOR=systemd`

#### 2. Core ComponentAdapter Enforcement

**File**: `core/orchestrator.py` (ComponentAdapter.start)

**Change**: When starting child processes, set `RANSOMEYE_ORCHESTRATOR=core` in component environment

**Enforcement**: Components receive `RANSOMEYE_ORCHESTRATOR=core` when started by Core

#### 3. Component Supervision Assertion Fix

**File**: `services/*/main.py` (_assert_supervised)

**Change**: Allow `RANSOMEYE_ORCHESTRATOR=core` (started by Core) OR `RANSOMEYE_ORCHESTRATOR=systemd` (systemd service)

**Enforcement**: Components accept either `core` or `systemd` orchestrator

#### 4. Core Startup Enforcement

**File**: `core/orchestrator.py` (run method)

**Change**: If `RANSOMEYE_ORCHESTRATOR=systemd` but individual services don't exist, FAIL HARD

**Enforcement**: Core refuses to start in systemd mode without required services

#### 5. Restore Script Enforcement

**File**: `scripts/phase_d_restore.sh`

**Change**: Validate that restored environment does NOT have `RANSOMEYE_ORCHESTRATOR=systemd` OR verify all required component services exist

**Enforcement**: Restore fails if orchestration mode mismatch detected

---

## D.6.4 — Recovery & Runtime Contract Updates

### Updated Recovery Contract (v1.0.1)

#### Orchestration Model Requirements:

1. **Backup MUST contain**: `ransomeye-core.service` only (no individual component services)

2. **Backup MUST NOT contain**: `RANSOMEYE_ORCHESTRATOR=systemd` in environment file (or must be validated against existing services)

3. **Restore MUST ensure**: Only `ransomeye-core.service` exists after restore (no individual component services)

4. **Restore MUST abort if**: `RANSOMEYE_ORCHESTRATOR=systemd` is set but individual component services are missing

5. **Runtime MUST enforce**: Core refuses to start if orchestration mode mismatch detected

### Runtime Startup Checks:

1. **Core startup check**: If `RANSOMEYE_ORCHESTRATOR=systemd`, verify all required component services exist and are active

2. **Component startup check**: Components accept `RANSOMEYE_ORCHESTRATOR=core` (Core-managed) or `RANSOMEYE_ORCHESTRATOR=systemd` (systemd-managed)

3. **Environment validation**: Restore script validates orchestration mode matches installed services

---

## D.6.5 — Implementation Checklist

- [x] Document orchestration models
- [x] Select authoritative model (Unified Single-Service Core)
- [ ] Update ComponentAdapter to set `RANSOMEYE_ORCHESTRATOR=core` for child processes
- [ ] Update component `_assert_supervised()` to accept `RANSOMEYE_ORCHESTRATOR=core`
- [ ] Update Core startup to validate orchestration mode
- [ ] Update restore script to validate orchestration mode
- [ ] Update recovery contract documentation
