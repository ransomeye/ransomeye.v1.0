# RANSOMEYE v1.0 SYSTEM REFERENCE MANIFEST (SRM)

**Version**: 1.0.0  
**Effective Date**: 2026-01-18  
**Authority**: Single Source of Truth for RansomEye Core v1.0  
**Status**: LOCKED — All modules must conform to this manifest

---

## 1. Platform Baseline

### Operating System

| Property | Value | Notes |
|----------|-------|-------|
| **OS** | Ubuntu LTS | Primary supported platform |
| **Minimum Version** | Ubuntu 20.04 LTS | Tested and supported |
| **Recommended Version** | Ubuntu 22.04 LTS | Current LTS |
| **Future Support** | Ubuntu 24.04 LTS+ | Supported but not primary target for v1.0 |
| **Kernel Expectations** | Linux 5.4+ | Required for systemd and namespace isolation |
| **Architecture** | x86_64 (amd64) | Only architecture supported for v1.0 |
| **Init System** | systemd | Required for service management |

### Kernel Features Required

- **Namespaces**: Required for process isolation
- **Cgroups**: Required for resource limits
- **systemd**: Required for service lifecycle management

---

## 2. Language Runtimes

### Python

| Property | Value | Notes |
|----------|-------|-------|
| **Version** | Python 3.10+ | Minimum required version |
| **Recommended** | Python 3.10 or 3.11 | Tested and validated |
| **Virtual Environment Path** | `/opt/ransomeye/venv` | **AUTHORITATIVE** — All Python packages MUST be installed here |
| **Python Binary Path** | `/opt/ransomeye/venv/bin/python3` | Used by wrapper scripts |
| **Packaging Strategy** | Option B — Virtual Environment Bundled | Pre-built during release, included in backup |

### Other Runtimes

| Runtime | Status | Notes |
|---------|--------|-------|
| **Node.js** | NOT USED | Explicitly NONE |
| **Java** | NOT USED | Explicitly NONE |
| **Go** | NOT USED | Explicitly NONE |
| **Rust** | NOT USED | Explicitly NONE |

**Policy**: Only Python runtime is used. All other runtimes are explicitly forbidden.

---

## 3. Python Dependency Canonical Matrix

### Universal Dependencies (All Components)

| Package | Exact Version | Component(s) | Source | Notes |
|---------|--------------|--------------|--------|-------|
| psycopg2-binary | ==2.9.9 | Core, all components | venv | PostgreSQL client |
| pydantic | ==2.5.0 | Core, all components | venv | Data validation |
| pydantic-settings | ==2.1.0 | Core, all components | venv | Settings management |
| python-dateutil | ==2.8.2 | Core, ingest, policy-engine | venv | Date/time parsing |

### Component-Specific Dependencies

#### ingest
| Package | Exact Version | Component | Source | Notes |
|---------|--------------|-----------|--------|-------|
| fastapi | ==0.104.1 | ingest, ui-backend | venv | HTTP API framework |
| uvicorn[standard] | ==0.24.0 | ingest, ui-backend | venv | ASGI server |
| jsonschema | ==4.19.2 | ingest | venv | Event schema validation |
| pynacl | ==1.6.2 | ingest | venv | Ed25519 signature verification |
| PyJWT | ==2.10.1 | ingest, ui-backend | venv | JWT authentication |

#### ai-core
| Package | Exact Version | Component | Source | Notes |
|---------|--------------|-----------|--------|-------|
| numpy | ==1.24.3 | ai-core | venv | Numerical computing |
| scikit-learn | ==1.3.2 | ai-core | venv | Machine learning (clustering) |
| uuid | ==1.30 | ai-core, correlation-engine | venv | UUID generation |

#### correlation-engine
| Package | Exact Version | Component | Source | Notes |
|---------|--------------|-----------|--------|-------|
| uuid | ==1.30 | correlation-engine | venv | UUID generation |

#### policy-engine
| Package | Exact Version | Component | Source | Notes |
|---------|--------------|-----------|--------|-------|
| cryptography | ==41.0.7 | policy-engine | venv | Command signing |

#### ui-backend
| Package | Exact Version | Component | Source | Notes |
|---------|--------------|-----------|--------|-------|
| fastapi | ==0.104.1 | ui-backend | venv | HTTP API framework |
| uvicorn[standard] | ==0.24.0 | ui-backend | venv | ASGI server |
| fastapi-cors | ==0.0.6 | ui-backend | venv | CORS support |
| PyJWT | ==2.10.1 | ui-backend | venv | JWT authentication |
| bcrypt | ==4.2.1 | ui-backend | venv | Password hashing |

### Dependency Canonical Rules

1. **Exact Versions Only**: All dependencies MUST use exact version pinning (==) as specified above
2. **Single Source**: All dependencies MUST be installed in `/opt/ransomeye/venv`
3. **No Implicit Dependencies**: Transitive dependencies are NOT allowed - all must be explicit
4. **No System Python**: System Python packages MUST NOT be used - only venv packages
5. **Superset Principle**: This matrix is the superset of all component requirements.txt files

---

## 4. System Dependencies

### Database

| Package | Minimum Version | Tested Version | Source | Notes |
|---------|----------------|----------------|--------|-------|
| **PostgreSQL** | 12+ | 14+ recommended | system (apt/yum) | Database server |
| **PostgreSQL Client** | 12+ | 14+ recommended | system (apt/yum) | psql command |
| **python3-dev** | - | - | system (apt/yum) | Required for psycopg2-binary build |

### Cryptography Libraries

| Package | Version | Source | Notes |
|---------|---------|--------|-------|
| **OpenSSL** | 1.1.1+ | system (apt/yum) | Required for Python cryptography module |
| **libcrypto** | 1.1.1+ | system (apt/yum) | Linked by psycopg2-binary |

### Other System Dependencies

| Package | Version | Source | Notes |
|---------|---------|--------|-------|
| **systemd** | 245+ | system (apt/yum) | Service management (Ubuntu 20.04+) |

### Kernel Features

- **Namespaces**: Required (Linux 3.8+)
- **Cgroups**: Required (Linux 2.6+)
- **No special kernel modules required**

---

## 5. Network & Port Allocation Table

### Port Allocation (Authoritative)

| Port | Component | Bind Address | Protocol | Purpose | Collision Policy |
|------|-----------|--------------|----------|---------|------------------|
| **8000** | ingest | 127.0.0.1 | HTTP/1.1 | Event ingestion endpoint | **FAIL HARD** if in use |
| **8080** | ui-backend | 127.0.0.1 | HTTP/1.1 | UI API endpoint | **FAIL HARD** if in use |
| **5432** | PostgreSQL | 127.0.0.1 | TCP | Database server | **FAIL HARD** if in use |

### Port Configuration

- **Environment Variables**: `RANSOMEYE_INGEST_PORT`, `RANSOMEYE_UI_PORT`, `RANSOMEYE_DB_PORT`
- **Default Values**: 8000 (ingest), 8080 (ui), 5432 (postgres)
- **Validation**: All ports MUST be in range 1-65535
- **Binding**: All services MUST bind to `127.0.0.1` (localhost only) unless explicitly configured

### Dynamic Ports

**FORBIDDEN**: No dynamic port allocation is allowed. All ports MUST be statically configured.

### Port Collision Detection

- **Startup Validation**: Core validates port availability before starting components
- **Failure Behavior**: Core refuses to start if any required port is in use
- **Error Message**: Explicitly states which port is in use and by which process

---

## 6. Crypto & Identity Standards

### Key Algorithms

| Algorithm | Purpose | Key Size | Standard |
|-----------|---------|----------|----------|
| **Ed25519** | Command signing, report signing, artifact signing | 256 bits (private), 256 bits (public) | RFC 8032 |
| **Ed25519** | Service-to-service authentication | 256 bits | RFC 8032 |
| **Ed25519** | Supply-chain artifact signing | 256 bits | RFC 8032 |

### Hash Algorithms

| Algorithm | Purpose | Output Size | Standard |
|-----------|---------|-------------|----------|
| **SHA256** | File integrity, content hashing | 256 bits | FIPS 180-4 |
| **SHA256** | Database migration checksums | 256 bits | FIPS 180-4 |
| **SHA256** | Event envelope verification | 256 bits | FIPS 180-4 |

### Encoding Formats

| Format | Purpose | Standard |
|--------|---------|----------|
| **Base64** | Signature encoding | RFC 4648 |
| **RFC3339 UTC** | Timestamps | RFC 3339 |
| **UUID v4** | Identifiers | RFC 4122 |

### Signing Schemes

| Scheme | Purpose | Algorithm | Notes |
|--------|---------|-----------|-------|
| **Ed25519** | Command signing | Ed25519 | Policy Engine → Agent commands |
| **Ed25519** | Report signing | Ed25519 | Signed reports for regulatory |
| **Ed25519** | Artifact signing | Ed25519 | Supply-chain integrity |
| **Ed25519** | Service authentication | Ed25519 | Service-to-service auth |

### Key Management

- **Separate Keys**: Each subsystem uses separate keypairs (no key reuse)
- **Key Storage**: Keys stored in `/opt/ransomeye/config/keys/` (component-specific subdirectories)
- **Key Format**: PEM format for Ed25519 keys
- **Key Generation**: Deterministic (RFC 8032 compliant)

### Minimum Key Sizes

- **Command Signing Key**: Minimum 32 characters (for `RANSOMEYE_COMMAND_SIGNING_KEY` environment variable)
- **Cryptographic Keys**: 256 bits (Ed25519)
- **Hash Output**: 256 bits (SHA256)

---

## 7. Orchestration Invariants

### Supported Orchestration Model

**Model**: **Unified Single-Service Core (Orchestrator Mode)**

**Definition**:
- Core starts and manages all components as child processes
- Only ONE systemd service exists: `ransomeye-core.service`
- Components run as child processes under Core supervision
- Components receive `RANSOMEYE_ORCHESTRATOR=core` environment variable

**Required Systemd Units**:
- `ransomeye-core.service` (ONE service only)

**Required Environment Flags**:
- `RANSOMEYE_ORCHESTRATOR` MUST NOT be set, OR set to empty string, OR set to "core"

**Health Checks**:
- Core orchestrator starts components via `ComponentAdapter.start()`
- Core orchestrator supervises component health via `ComponentAdapter.health()`
- Components run as child processes of Core

**Backup Requirements**:
- `ransomeye-core.service` must exist
- Individual component service files (`.service`) must NOT exist
- Environment file must NOT have `RANSOMEYE_ORCHESTRATOR=systemd`

### Forbidden Orchestration Models

**UNSUPPORTED FOR v1.0**: systemd-Managed Multi-Service Core (Supervision Mode)

**Definition** (forbidden):
- systemd manages each component as a separate service
- Multiple systemd service files exist (e.g., `ransomeye-ingest.service`, `ransomeye-ai-core.service`)
- Core only supervises (does not start components)
- `RANSOMEYE_ORCHESTRATOR=systemd` in environment file

**Why Forbidden**:
- Incompatible with installer design (installer creates ONE service only)
- Incompatible with backup/restore (backup assumes single service)
- Violates recovery baseline (PHASE D.5)
- Creates multiple failure points

### What Must Never Exist

**FORBIDDEN ARTIFACTS**:
- `/etc/systemd/system/ransomeye-secure-bus.service` — MUST NOT EXIST
- `/etc/systemd/system/ransomeye-ingest.service` — MUST NOT EXIST
- `/etc/systemd/system/ransomeye-core-runtime.service` — MUST NOT EXIST
- `/etc/systemd/system/ransomeye-correlation-engine.service` — MUST NOT EXIST
- `/etc/systemd/system/ransomeye-policy-engine.service` — MUST NOT EXIST
- `/etc/systemd/system/ransomeye-ai-core.service` — MUST NOT EXIST
- `/etc/systemd/system/ransomeye-llm-soc.service` — MUST NOT EXIST
- `/etc/systemd/system/ransomeye-ui.service` — MUST NOT EXIST

**Exception**: `ransomeye-linux-agent.service` is allowed (separate component, not part of Core).

---

## 8. Backup & Restore Contract (SRM View)

### Required Backup Artifacts

**MANDATORY** (restore fails if missing):

1. **Installation Directory**: `/opt/ransomeye/` (complete tree)
   - `bin/` — Executable wrappers
   - `lib/` — Python code
   - `config/` — Configuration files (including `environment` with secrets)
   - `logs/` — Log files
   - `runtime/` — Runtime state
   - **`venv/`** — Python virtual environment (D.7 requirement)

2. **Systemd Service Unit**: `/etc/systemd/system/ransomeye-core.service`
   - Must be `ransomeye-core.service` (not component services)
   - Must have `@INSTALL_ROOT@` replaced with actual path (or already replaced)

3. **Environment Configuration**: `/opt/ransomeye/config/environment`
   - Must NOT contain `RANSOMEYE_ORCHESTRATOR=systemd`
   - Must contain all required secrets and instance-specific IDs

4. **Database Dump**: PostgreSQL logical dump (`.sql` file)

**OPTIONAL** (restore continues if missing):
- System state snapshot (metadata only)
- `/opt/ransomeye-agent/` (separate component)
- `/etc/ransomeye/` (if exists)

### Restore Invalidation Conditions

**RESTORE FAILS** (abort immediately) if:

1. **Missing Environment File**: `/opt/ransomeye/config/environment` not found
2. **Missing Systemd Unit**: `/etc/systemd/system/ransomeye-core.service` not found
3. **Missing Virtual Environment**: `/opt/ransomeye/venv/` not found (D.7 requirement)
4. **Orchestration Mismatch**: `RANSOMEYE_ORCHESTRATOR=systemd` set but component services missing
5. **Dependency Validation Fails**: Pre-start dependency check fails (missing packages)

**RESTORE CONTINUES** (but Core may fail to start) if:

1. Database dump missing (Core cannot connect, but restore completes)
2. System user missing (Core fails with permission error)
3. PostgreSQL not running (Core fails with connection error)

### Dependency Envelope Requirements

**Per D.7.5**:

1. **Virtual Environment MUST be in Backup**: `/opt/ransomeye/venv/` must be backed up
2. **Dependencies MUST be Installed**: All packages from Dependency Canonical Matrix must be installed in venv
3. **Pre-Start Validation**: Core validates dependencies before starting components
4. **Fail-Closed**: Core refuses to start if any dependency is missing

---

## 9. Enforcement Rules

### Startup Failures

**Core REFUSES TO START** (exits with error code) if:

1. **Missing Runtime Dependencies**: Any package from Dependency Canonical Matrix is not importable
   - Error: `RUNTIME DEPENDENCY MISSING: <component>:<package>`
   - Exit code: 2 (STARTUP_ERROR)

2. **Orchestration Mode Mismatch**: `RANSOMEYE_ORCHESTRATOR=systemd` but required component services missing
   - Error: `ORCHESTRATION MODE MISMATCH: RANSOMEYE_ORCHESTRATOR=systemd but required systemd services are missing`
   - Exit code: 1 (CONFIG_ERROR)

3. **Port Collision**: Required port is in use
   - Error: Explicit message stating port and process
   - Exit code: 2 (STARTUP_ERROR)

4. **Missing Configuration**: Required environment variables missing
   - Error: `RANSOMEYE_<VAR> is required`
   - Exit code: 1 (CONFIG_ERROR)

5. **Database Connection Failure**: Cannot connect to PostgreSQL
   - Error: Database connection error with details
   - Exit code: 2 (STARTUP_ERROR)

### Restore Failures

**Restore Script ABORTS** (exits with error code) if:

1. **Missing Environment File**: `/opt/ransomeye/config/environment` not in backup
   - Error: `Environment configuration missing`
   - Exit code: 1

2. **Missing Systemd Service**: `/etc/systemd/system/ransomeye-core.service` not in backup
   - Error: `Required systemd service missing: ransomeye-core.service`
   - Exit code: 1

3. **Missing Virtual Environment**: `/opt/ransomeye/venv/` not in backup (D.7 requirement)
   - Error: `Virtual environment missing: /opt/ransomeye/venv/`
   - Exit code: 1

4. **Archive Checksum Mismatch**: Backup archive checksum does not match expected value
   - Error: `BACKUP INTEGRITY COMPROMISED - RESTORE ABORTED`
   - Exit code: 1

### Install Failures

**Installer ABORTS** (exits with error code) if:

1. **Missing Dependencies**: Cannot install required Python packages in venv
   - Error: Explicit pip install error message
   - Exit code: 1

2. **Port Collision**: Required port is in use during installation
   - Error: Port availability check failure
   - Exit code: 1

3. **Service File Generation Failure**: Cannot create or install `ransomeye-core.service`
   - Error: `Failed to install systemd service`
   - Exit code: 1

4. **Virtual Environment Creation Failure**: Cannot create `/opt/ransomeye/venv/`
   - Error: `Failed to create virtual environment`
   - Exit code: 1

---

## 10. Version Authority Rules

### Single Source of Truth

**This SRM is the ONLY authoritative source for**:
- Python package versions
- Port numbers
- Cryptographic algorithms
- Orchestration model
- Dependency requirements

### Module Conformance

**NO MODULE MAY**:
- Override SRM versions
- Introduce version conflicts
- Use undocumented ports
- Introduce implicit dependencies
- Use unsupported orchestration models

### Validation

**All modules MUST**:
- Validate against SRM before committing changes
- Fail startup if SRM violations detected
- Report SRM violations explicitly (no silent failures)

---

## 11. Change Control

### SRM Modification Rules

1. **Breaking Changes**: Require major version bump (v1.0 → v2.0)
2. **Non-Breaking Changes**: Require minor version bump (v1.0.0 → v1.1.0)
3. **Documentation Only**: Require patch version bump (v1.0.0 → v1.0.1)

### Version History

- **v1.0.0** (2026-01-18): Initial SRM definition (PHASE D.8)

---

## 12. Enforcement Implementation

### SRM Validation Points

1. **Installer**: Validates SRM compliance during installation
2. **Restore Script**: Validates SRM compliance during restore
3. **Core Startup**: Validates SRM compliance before starting components
4. **Build Process**: Validates SRM compliance during release packaging

### Violation Reporting

**All SRM violations MUST**:
- Log explicit error message referencing SRM section
- Exit with non-zero code
- NOT attempt silent fallback or compatibility shim

---

**END OF SYSTEM REFERENCE MANIFEST**

**This document is LOCKED for v1.0. All changes require formal change control.**
