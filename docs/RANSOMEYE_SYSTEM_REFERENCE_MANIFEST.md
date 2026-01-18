# RANSOMEYE v1.0 SYSTEM REFERENCE MANIFEST (SRM)

**Version**: 1.1.0  
**Effective Date**: 2026-01-18  
**Authority**: Single Source of Truth for RansomEye Core v1.0  
**Status**: LOCKED — All modules must conform to this manifest  
**Change**: PHASE D.11 — Restructured into component-scoped sections, Python 3.11.x authoritative

---

## VERSION HISTORY

- **v1.1.0** (2026-01-18): PHASE D.11 — Restructured into component-scoped sections, Python 3.11.x authoritative
- **v1.0.0** (2026-01-18): PHASE D.8 — Initial SRM definition

---

# SECTION 1 — CORE ENGINE

## 1.1 Python Runtime

### Authoritative Python Version

| Property | Value | Notes |
|----------|-------|-------|
| **Version** | **Python 3.11.x** | **AUTHORITATIVE** — Only this version is supported for v1.0 |
| **Minimum Patch** | 3.11.0 | Tested and validated |
| **Recommended Patch** | 3.11.9 | Latest stable in 3.11 series |
| **Virtual Environment Path** | `/opt/ransomeye/venv` | **AUTHORITATIVE** — All Python packages MUST be installed here |
| **Python Binary Path** | `/opt/ransomeye/venv/bin/python3` | Used by wrapper scripts |
| **Packaging Strategy** | Option B — Virtual Environment Bundled | Pre-built during release, included in backup |

### Python Version Compatibility Matrix

| Python Version | Status | Reason |
|----------------|--------|--------|
| **3.10.x** | ❌ **UNSUPPORTED** | Dependency pins validated against 3.11.x only |
| **3.11.x** | ✅ **SUPPORTED** | Authoritative version, all dependencies validated |
| **3.12.x** | ❌ **UNSUPPORTED** | Dependency pins may not be compatible |
| **3.13.x** | ❌ **FORBIDDEN** | Explicitly forbidden — incompatible with dependency pins (numpy 1.24.3, psycopg2-binary 2.9.9) |

### Why Python 3.11.x?

**Rationale**:
1. **Dependency Compatibility**: All SRM-pinned dependency versions (numpy==1.24.3, psycopg2-binary==2.9.9, scikit-learn==1.3.2) are validated and tested against Python 3.11.x
2. **Stability**: Python 3.11 is mature and stable, widely available in LTS distributions
3. **Determinism**: Single authoritative version prevents version drift and compatibility issues
4. **Build Reproducibility**: All builds and installations use identical Python version, ensuring deterministic dependency resolution

### Python Version Enforcement

- **Installer MUST verify** Python 3.11.x is available before proceeding
- **Installer MUST fail** if Python version is not 3.11.x
- **Core MUST validate** Python version at startup and refuse to start if version mismatch
- **No compatibility shims** or fallbacks allowed

### Other Runtimes

| Runtime | Status | Notes |
|---------|--------|-------|
| **Node.js** | NOT USED | Explicitly NONE |
| **Java** | NOT USED | Explicitly NONE |
| **Go** | NOT USED | Explicitly NONE |
| **Rust** | NOT USED | Explicitly NONE |

**Policy**: Only Python runtime is used. All other runtimes are explicitly forbidden.

---

## 1.2 Python Dependency Canonical Matrix

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
6. **Python 3.11.x Only**: All dependency pins validated against Python 3.11.x only

---

## 1.3 Port Authority Matrix

### Core Engine Ports

| Port | Owner | Bind Address | Protocol | Direction | Purpose | Collision Policy |
|------|-------|--------------|----------|-----------|---------|------------------|
| **8000** | ingest | 127.0.0.1 | HTTP/1.1 | **Inbound** | Event ingestion endpoint (`POST /events`) | **FAIL HARD** if in use |
| **8080** | ui-backend | 127.0.0.1 | HTTP/1.1 | **Inbound** | UI API endpoint | **FAIL HARD** if in use |
| **5432** | PostgreSQL | 127.0.0.1 | TCP | **Inbound** | Database server | **FAIL HARD** if in use |

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

## 1.4 Orchestration Model

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

## 1.5 Privilege Requirements

### Core Engine Runtime Privileges

| Component | User | Privileges | Notes |
|-----------|------|------------|-------|
| **ransomeye-core.service** | `ransomeye` | **Non-root** | Runs as unprivileged system user |
| **PostgreSQL** | `postgres` | Database privileges only | System service, separate user |
| **All Core Components** | Inherits from Core | **Non-root** | All components run under Core's user context |

### Forbidden Privilege States

**FORBIDDEN**:
- ❌ Core or any Core component running as root
- ❌ Core or any Core component with SUID/SGID bits set
- ❌ Core or any Core component with unnecessary capabilities
- ❌ Core components accessing files outside `/opt/ransomeye/` except:
  - `/etc/systemd/system/ransomeye-core.service` (read)
  - `/var/log/ransomeye/` (write, if configured)
  - System temporary directories (write, if configured)

---

## 1.6 System Dependencies

### Database

| Package | Minimum Version | Tested Version | Source | Notes |
|---------|----------------|----------------|--------|-------|
| **PostgreSQL** | 12+ | 14+ recommended | system (apt/yum) | Database server |
| **PostgreSQL Client** | 12+ | 14+ recommended | system (apt/yum) | psql command |
| **python3-dev** | - | - | system (apt/yum) | Required for psycopg2-binary build (Python 3.11.x) |

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

## 1.7 Operating System Compatibility

### Supported Operating Systems

| OS | Minimum Version | Recommended Version | Python 3.11.x Available | Notes |
|----|----------------|---------------------|------------------------|-------|
| **Ubuntu LTS** | 20.04 | 22.04 | ✅ Yes (via deadsnakes PPA or compiled) | Primary supported platform |
| **Ubuntu** | 22.04+ | 22.04 | ✅ Yes (native) | Recommended |
| **Debian** | 11+ | 12 | ✅ Yes (via deadsnakes PPA or compiled) | Secondary platform |

### Forbidden Operating Systems

**FORBIDDEN FOR v1.0**:
- ❌ **Windows** — Core Engine not supported on Windows
- ❌ **macOS** — Core Engine not supported on macOS
- ❌ **Non-Linux Unix** — Core Engine not supported on non-Linux Unix systems

---

## 1.8 Forbidden States

### Core Engine Forbidden States

1. **Orchestration Mismatch**:
   - ❌ `RANSOMEYE_ORCHESTRATOR=systemd` with Core orchestrator mode
   - ❌ Multiple systemd service files for Core components

2. **Python Version Mismatch**:
   - ❌ Python version other than 3.11.x
   - ❌ Using system Python packages instead of venv

3. **Port Conflicts**:
   - ❌ Port 8000, 8080, or 5432 in use by non-RansomEye processes
   - ❌ Dynamic port allocation

4. **Privilege Escalation**:
   - ❌ Core or components running as root
   - ❌ Components with unnecessary capabilities or SUID bits

5. **Missing Dependencies**:
   - ❌ Any SRM-pinned dependency missing from venv
   - ❌ Any dependency version mismatch

6. **Directory Access Violations**:
   - ❌ Core components accessing files outside authorized directories
   - ❌ Core components writing to unauthorized locations

---

# SECTION 2 — DPI PROBE

## 2.1 Privilege Requirements

### Packet Capture Privileges

| Capability | Required For | Notes |
|------------|--------------|-------|
| **CAP_NET_RAW** | Raw socket creation (packet capture) | **REQUIRED** — Cannot capture packets without this |
| **CAP_NET_ADMIN** | Network interface configuration | **REQUIRED** — Needed for promiscuous mode |

### Runtime User

| Property | Value | Notes |
|----------|-------|-------|
| **User** | `ransomeye-dpi` | Non-root system user |
| **Privileges** | File capabilities (CAP_NET_RAW, CAP_NET_ADMIN) | Set via `setcap` on executable |
| **Full Root** | ❌ **FORBIDDEN** | DPI Probe MUST NOT run as root |

### Capability Implementation

- **File Capabilities**: Capabilities set on executable file via `setcap cap_net_raw,cap_net_admin+ep`
- **Inheritance**: Process inherits capabilities from file when executed
- **Filesystem Requirement**: Filesystem MUST support capabilities (ext4, xfs) — NFS/tmpfs NOT supported

### Forbidden Privilege States

**FORBIDDEN**:
- ❌ Running DPI Probe as root
- ❌ Using SUID/SGID bits instead of file capabilities
- ❌ Installing DPI Probe on filesystem without capability support (NFS, tmpfs)

---

## 2.2 Network Interfaces

### Interface Requirements

| Property | Value | Notes |
|----------|-------|-------|
| **Configuration** | Via `RANSOMEYE_DPI_INTERFACE` environment variable | Must specify interface name (e.g., `eth0`, `ens33`) |
| **Promiscuous Mode** | Required | Enabled via CAP_NET_ADMIN |
| **Access Method** | AF_PACKET fastpath (C library) | `/opt/ransomeye/lib/libransomeye_dpi_af_packet.so` |

### Forbidden Interface States

**FORBIDDEN**:
- ❌ Capturing on all interfaces simultaneously (unless explicitly configured)
- ❌ Accessing interfaces without proper privileges
- ❌ Operating in non-promiscuous mode (unless explicitly configured for test)

---

## 2.3 Ports

### DPI Probe Communication

| Port | Owner | Bind Address | Protocol | Direction | Purpose | Collision Policy |
|------|-------|--------------|----------|-----------|---------|------------------|
| **8000** | Core Ingest | 127.0.0.1 | HTTP/1.1 | **Outbound** | Transmit telemetry events (`POST /events`) | N/A (outbound only) |
| **8003** | DPI Probe (optional) | 127.0.0.1 | HTTP/1.1 | **Inbound** | DPI probe API (if exposed) | **FAIL HARD** if in use (if enabled) |

**Note**: Port 8003 is optional and may not be exposed. DPI Probe primarily communicates via outbound HTTP to Core Ingest.

### Forbidden Port States

**FORBIDDEN**:
- ❌ Listening on unauthorized ports
- ❌ Exposing DPI Probe API on non-localhost addresses
- ❌ Dynamic port allocation for API endpoint

---

## 2.4 Dependencies

### Python Dependencies

| Package | Exact Version | Source | Notes |
|---------|--------------|--------|-------|
| psycopg2-binary | ==2.9.9 | venv (shared with Core) | PostgreSQL client (if needed) |
| pydantic | ==2.5.0 | venv (shared with Core) | Data validation |
| pydantic-settings | ==2.1.0 | venv (shared with Core) | Settings management |
| pynacl | ==1.6.2 | venv (shared with Core) | Telemetry signing (Ed25519) |

### System Dependencies

| Package | Version | Source | Notes |
|---------|---------|--------|-------|
| **libpcap** | - | system (apt/yum) | Packet capture library (if used) |
| **libcap2-bin** | - | system (apt/yum) | Required for `setcap` command |
| **gcc** | - | system (apt/yum) | Required for building AF_PACKET library |

### Forbidden Dependencies

**FORBIDDEN**:
- ❌ Direct system Python packages (must use venv)
- ❌ Dependencies not listed in SRM

---

## 2.5 Isolation Rules

### Process Isolation

| Property | Value | Notes |
|----------|-------|-------|
| **Supervision** | **REQUIRED** — Core-supervised only | DPI Probe MUST run under Core supervision |
| **Standalone Service** | ❌ **FORBIDDEN** | No standalone systemd service allowed |
| **Execution Model** | Child process of Core | Launched by Core orchestrator |

### Forbidden Isolation States

**FORBIDDEN**:
- ❌ DPI Probe running as standalone systemd service
- ❌ DPI Probe running without Core supervision
- ❌ DPI Probe running in container without proper capabilities

---

## 2.6 Forbidden States

### DPI Probe Forbidden States

1. **Privilege Violations**:
   - ❌ Running as root
   - ❌ Missing CAP_NET_RAW or CAP_NET_ADMIN capabilities
   - ❌ Installed on filesystem without capability support

2. **Supervision Violations**:
   - ❌ Running without Core supervision
   - ❌ Running as standalone systemd service

3. **Interface Violations**:
   - ❌ Capturing on unauthorized interfaces
   - ❌ Operating without promiscuous mode when required

4. **Communication Violations**:
   - ❌ Transmitting telemetry to unauthorized endpoints
   - ❌ Exposing API on non-localhost addresses

5. **Dependency Violations**:
   - ❌ Missing required dependencies
   - ❌ Using system Python packages instead of venv

---

# SECTION 3 — LINUX AGENT

## 3.1 Privilege Model

### Runtime Privileges

| Property | Value | Notes |
|----------|-------|-------|
| **User** | `ransomeye-agent` | Non-root system user |
| **Privileges** | **Non-root** — Minimal privileges | Agent runs unprivileged |
| **SUID/SGID** | ❌ **FORBIDDEN** | No SUID/SGID bits allowed |

### Monitoring Capabilities

| Capability | Privilege Required | Notes |
|------------|-------------------|-------|
| **Process Monitoring** | Non-root (same user namespace) | Can monitor processes in same namespace |
| **File System Monitoring** | Non-root (read access) | Requires read access to monitored directories |
| **Network Connection Monitoring** | Non-root | Can enumerate connections for current user |
| **System Call Monitoring** | **Root or CAP_SYS_ADMIN** | Requires eBPF/auditd privileges (if enabled) |

### Forbidden Privilege States

**FORBIDDEN**:
- ❌ Linux Agent running as root (unless explicitly required for system call monitoring)
- ❌ Linux Agent with SUID/SGID bits set
- ❌ Linux Agent with unnecessary capabilities

---

## 3.2 Kernel Requirements

### Kernel Features

| Feature | Required | Notes |
|---------|----------|-------|
| **Namespaces** | ✅ Required | Process isolation |
| **Cgroups** | ✅ Required | Resource limits |
| **eBPF** | Optional | For advanced system call monitoring |
| **auditd** | Optional | Alternative to eBPF for system call monitoring |

### Kernel Version

| Property | Value | Notes |
|----------|-------|-------|
| **Minimum Version** | Linux 5.4+ | Required for systemd and namespace isolation |
| **Recommended Version** | Linux 5.15+ | Better eBPF support |

---

## 3.3 Communication Ports

### Linux Agent Communication

| Port | Owner | Bind Address | Protocol | Direction | Purpose | Collision Policy |
|------|-------|--------------|----------|-----------|---------|------------------|
| **8000** | Core Ingest | 127.0.0.1 | HTTP/1.1 | **Outbound** | Transmit events (`POST /events`) | N/A (outbound only) |
| **N/A** | Linux Agent | N/A | N/A | **None** | No listening ports — agent is one-shot | N/A |

**Note**: Linux Agent does not listen on any ports. It is a one-shot agent that transmits events via outbound HTTP to Core Ingest.

### Forbidden Port States

**FORBIDDEN**:
- ❌ Linux Agent listening on any ports
- ❌ Linux Agent exposing HTTP API
- ❌ Linux Agent acting as server

---

## 3.4 Dependencies

### Runtime Dependencies

| Package | Version | Source | Notes |
|---------|---------|--------|-------|
| **Rust** | - | system (if agent is Rust-based) | Compile-time dependency |
| **Python 3.11.x** | 3.11.x | system | If agent is Python-based |
| **libc** | - | system | Standard C library |

### Forbidden Dependencies

**FORBIDDEN**:
- ❌ Dependencies not listed in SRM
- ❌ Unnecessary runtime dependencies

---

## 3.5 Execution Constraints

### Execution Model

| Property | Value | Notes |
|----------|-------|-------|
| **Execution Type** | **One-shot** | Agent runs, transmits event, exits |
| **Service Model** | systemd service with auto-restart | `ransomeye-linux-agent.service` |
| **Standalone** | ✅ Yes | Can operate independently of Core |

### Service Configuration

| Property | Value | Notes |
|----------|-------|--------|
| **Service Name** | `ransomeye-linux-agent.service` | systemd unit |
| **Auto-restart** | ✅ Enabled | Restarts on failure |
| **Crash-loop Prevention** | ✅ Enabled | Stops restarting after 5 failures in 5 minutes |

### Forbidden Execution States

**FORBIDDEN**:
- ❌ Linux Agent running as long-lived daemon (unless explicitly required)
- ❌ Linux Agent without crash-loop prevention
- ❌ Linux Agent without auto-restart on failure

---

## 3.6 Forbidden States

### Linux Agent Forbidden States

1. **Privilege Violations**:
   - ❌ Running as root (unless required for system call monitoring)
   - ❌ Unnecessary capabilities or SUID bits

2. **Port Violations**:
   - ❌ Listening on any ports
   - ❌ Acting as server or exposing API

3. **Execution Violations**:
   - ❌ Running as long-lived daemon without proper service management
   - ❌ Missing crash-loop prevention
   - ❌ Missing auto-restart on failure

4. **Communication Violations**:
   - ❌ Transmitting events to unauthorized endpoints
   - ❌ Bypassing Core Ingest service

---

# SECTION 4 — WINDOWS AGENT

## 4.1 OS Version Support

### Supported Windows Versions

| OS Version | Status | Notes |
|------------|--------|-------|
| **Windows 10** | ✅ Supported | All editions |
| **Windows 11** | ✅ Supported | All editions |
| **Windows Server 2016+** | ✅ Supported | All editions |
| **Windows Server 2019+** | ✅ Supported | All editions |
| **Windows Server 2022+** | ✅ Supported | All editions |

### Forbidden OS Versions

**FORBIDDEN**:
- ❌ **Windows 8.1 and earlier** — Not supported
- ❌ **Windows Server 2012 R2 and earlier** — Not supported

---

## 4.2 Privilege Requirements

### Runtime Privileges

| Property | Value | Notes |
|----------|-------|-------|
| **User** | `.\ransomeye-agent` | Local service account (non-Administrator) |
| **Privileges** | **Non-Administrator** — Minimal privileges | Agent runs unprivileged when possible |

### Required Windows Privileges (if needed)

| Privilege | Required For | Notes |
|-----------|--------------|-------|
| **SeDebugPrivilege** | Process enumeration and injection detection | Optional — required for advanced monitoring |
| **SeBackupPrivilege** | Registry key monitoring | Optional — required for registry monitoring |
| **Administrator** | ETW session creation | Optional — required for ETW monitoring |

### Forbidden Privilege States

**FORBIDDEN**:
- ❌ Windows Agent running as Administrator unless explicitly required
- ❌ Windows Agent with unnecessary privileges
- ❌ Windows Agent with SYSTEM account (unless required)

---

## 4.3 Services

### Windows Service Configuration

| Property | Value | Notes |
|----------|-------|-------|
| **Service Name** | `RansomEyeWindowsAgent` | Windows Service name |
| **Display Name** | `RansomEye Windows Agent` | Service display name |
| **Service Type** | OWN_PROCESS (10) | Standalone process |
| **Start Type** | AUTO_START (2) | Start automatically on boot |
| **Error Control** | NORMAL (1) | Log error but continue |

### Service Recovery

| Property | Value | Notes |
|----------|-------|-------|
| **Reset Period** | 300 seconds (5 minutes) | Time window for failure counting |
| **First Failure** | Restart after 60 seconds | |
| **Second Failure** | Restart after 120 seconds | |
| **Subsequent Failures** | Restart after 300 seconds | |
| **Crash-loop Prevention** | Stop after 5 failures in 5 minutes | Prevents crash-loop if Core is unreachable |

### Forbidden Service States

**FORBIDDEN**:
- ❌ Windows Agent without service recovery configuration
- ❌ Windows Agent without crash-loop prevention
- ❌ Windows Agent with incorrect service type or start type

---

## 4.4 Communication Ports

### Windows Agent Communication

| Port | Owner | Bind Address | Protocol | Direction | Purpose | Collision Policy |
|------|-------|--------------|----------|-----------|---------|------------------|
| **8000** | Core Ingest | 127.0.0.1 | HTTP/1.1 | **Outbound** | Transmit events (`POST /events`) | N/A (outbound only) |
| **N/A** | Windows Agent | N/A | N/A | **None** | No listening ports — agent is one-shot | N/A |

**Note**: Windows Agent does not listen on any ports. It is a one-shot agent that transmits events via outbound HTTP to Core Ingest.

### Forbidden Port States

**FORBIDDEN**:
- ❌ Windows Agent listening on any ports
- ❌ Windows Agent exposing HTTP API
- ❌ Windows Agent acting as server

---

## 4.5 Dependencies

### Runtime Dependencies

| Package | Version | Source | Notes |
|---------|---------|--------|-------|
| **Python 3.11.x** | 3.11.x | system | Required for Python-based agent |
| **ETW** | - | Windows built-in | Event Tracing for Windows (if used) |

### Python Dependencies (if Python-based)

| Package | Exact Version | Source | Notes |
|---------|--------------|--------|-------|
| psycopg2-binary | ==2.9.9 | venv | PostgreSQL client (if needed) |
| pydantic | ==2.5.0 | venv | Data validation |
| pydantic-settings | ==2.1.0 | venv | Settings management |

### Forbidden Dependencies

**FORBIDDEN**:
- ❌ Dependencies not listed in SRM
- ❌ Unnecessary runtime dependencies

---

## 4.6 Forbidden States

### Windows Agent Forbidden States

1. **Privilege Violations**:
   - ❌ Running as Administrator unless required
   - ❌ Running as SYSTEM account unless required
   - ❌ Unnecessary privileges

2. **Port Violations**:
   - ❌ Listening on any ports
   - ❌ Acting as server or exposing API

3. **Service Violations**:
   - ❌ Missing service recovery configuration
   - ❌ Missing crash-loop prevention
   - ❌ Incorrect service type or start type

4. **Communication Violations**:
   - ❌ Transmitting events to unauthorized endpoints
   - ❌ Bypassing Core Ingest service

---

# SECTION 5 — PORT AUTHORITY MATRIX (COMPLETE)

## 5.1 All Ports in System

| Port | Owner | Bind Address | Protocol | Direction | Purpose | Collision Policy |
|------|-------|--------------|----------|-----------|---------|------------------|
| **5432** | PostgreSQL | 127.0.0.1 | TCP | **Inbound** | Database server | **FAIL HARD** if in use |
| **8000** | Core Ingest | 127.0.0.1 | HTTP/1.1 | **Inbound** | Event ingestion endpoint (`POST /events`) | **FAIL HARD** if in use |
| **8000** | DPI Probe | 127.0.0.1 | HTTP/1.1 | **Outbound** | Transmit telemetry events | N/A (outbound only) |
| **8000** | Linux Agent | 127.0.0.1 | HTTP/1.1 | **Outbound** | Transmit events | N/A (outbound only) |
| **8000** | Windows Agent | 127.0.0.1 | HTTP/1.1 | **Outbound** | Transmit events | N/A (outbound only) |
| **8003** | DPI Probe (optional) | 127.0.0.1 | HTTP/1.1 | **Inbound** | DPI probe API (if exposed) | **FAIL HARD** if in use (if enabled) |
| **8080** | Core UI Backend | 127.0.0.1 | HTTP/1.1 | **Inbound** | UI API endpoint | **FAIL HARD** if in use |

### Port Ownership Rules

1. **Inbound Ports**: Only one component may bind to an inbound port
2. **Outbound Ports**: Multiple components may connect to the same outbound port (e.g., all agents connect to Core Ingest on 8000)
3. **Port Conflicts**: System MUST fail hard if required inbound port is in use
4. **Dynamic Ports**: FORBIDDEN — all ports MUST be statically configured

---

# SECTION 6 — VERSION & COMPATIBILITY MATRIX

## 6.1 Python Version ↔ Dependency Compatibility

### Core Engine Dependencies (Python 3.11.x Only)

| Python Version | numpy==1.24.3 | psycopg2-binary==2.9.9 | scikit-learn==1.3.2 | Status |
|----------------|---------------|------------------------|---------------------|--------|
| **3.10.x** | ⚠️ May work | ✅ Compatible | ⚠️ May work | ❌ **UNSUPPORTED** — Not validated |
| **3.11.x** | ✅ Compatible | ✅ Compatible | ✅ Compatible | ✅ **SUPPORTED** — Authoritative |
| **3.12.x** | ⚠️ May work | ⚠️ May work | ⚠️ May work | ❌ **UNSUPPORTED** — Not validated |
| **3.13.x** | ❌ **INCOMPATIBLE** | ❌ **INCOMPATIBLE** | ❌ **INCOMPATIBLE** | ❌ **FORBIDDEN** — Explicitly forbidden |

### Dependency Validation Policy

- **Python 3.11.x**: All dependencies validated and tested
- **Other Python versions**: NOT validated — installer MUST fail if version mismatch

---

## 6.2 OS Version ↔ Component Compatibility

### Core Engine Compatibility

| OS | Version | Core Engine | Python 3.11.x Available | Status |
|----|---------|-------------|------------------------|--------|
| **Ubuntu LTS** | 20.04 | ✅ Supported | ✅ Yes (via deadsnakes PPA or compiled) | ✅ Supported |
| **Ubuntu LTS** | 22.04 | ✅ Supported | ✅ Yes (native) | ✅ **Recommended** |
| **Ubuntu** | 24.04+ | ✅ Supported | ✅ Yes (native) | ✅ Supported |
| **Debian** | 11+ | ✅ Supported | ✅ Yes (via deadsnakes PPA or compiled) | ✅ Supported |
| **Debian** | 12+ | ✅ Supported | ✅ Yes (native) | ✅ Supported |
| **Windows** | Any | ❌ Not supported | N/A | ❌ **FORBIDDEN** |
| **macOS** | Any | ❌ Not supported | N/A | ❌ **FORBIDDEN** |

### DPI Probe Compatibility

| OS | Version | DPI Probe | Kernel Requirements | Status |
|----|---------|-----------|---------------------|--------|
| **Ubuntu LTS** | 20.04+ | ✅ Supported | Linux 5.4+ | ✅ Supported |
| **Ubuntu LTS** | 22.04+ | ✅ Supported | Linux 5.15+ | ✅ **Recommended** |
| **Debian** | 11+ | ✅ Supported | Linux 5.4+ | ✅ Supported |
| **Windows** | Any | ❌ Not supported | N/A | ❌ **FORBIDDEN** |
| **macOS** | Any | ❌ Not supported | N/A | ❌ **FORBIDDEN** |

### Linux Agent Compatibility

| OS | Version | Linux Agent | Kernel Requirements | Status |
|----|---------|-------------|---------------------|--------|
| **Ubuntu LTS** | 20.04+ | ✅ Supported | Linux 5.4+ | ✅ Supported |
| **Ubuntu LTS** | 22.04+ | ✅ Supported | Linux 5.15+ | ✅ **Recommended** |
| **Debian** | 11+ | ✅ Supported | Linux 5.4+ | ✅ Supported |
| **Windows** | Any | ❌ Not supported | N/A | ❌ **FORBIDDEN** |
| **macOS** | Any | ❌ Not supported | N/A | ❌ **FORBIDDEN** |

### Windows Agent Compatibility

| OS | Version | Windows Agent | Status |
|----|---------|---------------|--------|
| **Windows 10** | All editions | ✅ Supported | ✅ Supported |
| **Windows 11** | All editions | ✅ Supported | ✅ Supported |
| **Windows Server** | 2016+ | ✅ Supported | ✅ Supported |
| **Windows Server** | 2019+ | ✅ Supported | ✅ **Recommended** |
| **Windows Server** | 2022+ | ✅ Supported | ✅ Supported |
| **Linux** | Any | ❌ Not supported | ❌ **FORBIDDEN** |
| **macOS** | Any | ❌ Not supported | ❌ **FORBIDDEN** |

---

# SECTION 7 — ENFORCEMENT & VALIDATION

## 7.1 Startup Failures

**Core REFUSES TO START** (exits with error code) if:

1. **Python Version Mismatch**: Python version is not 3.11.x
   - Error: `PYTHON VERSION MISMATCH: Expected 3.11.x, got <version>`
   - Exit code: 1 (CONFIG_ERROR)

2. **Missing Runtime Dependencies**: Any package from Dependency Canonical Matrix is not importable
   - Error: `RUNTIME DEPENDENCY MISSING: <component>:<package>`
   - Exit code: 2 (STARTUP_ERROR)

3. **Orchestration Mode Mismatch**: `RANSOMEYE_ORCHESTRATOR=systemd` but required component services missing
   - Error: `ORCHESTRATION MODE MISMATCH: RANSOMEYE_ORCHESTRATOR=systemd but required systemd services are missing`
   - Exit code: 1 (CONFIG_ERROR)

4. **Port Collision**: Required port is in use
   - Error: Explicit message stating port and process
   - Exit code: 2 (STARTUP_ERROR)

5. **Missing Configuration**: Required environment variables missing
   - Error: `RANSOMEYE_<VAR> is required`
   - Exit code: 1 (CONFIG_ERROR)

6. **Database Connection Failure**: Cannot connect to PostgreSQL
   - Error: Database connection error with details
   - Exit code: 2 (STARTUP_ERROR)

## 7.2 Install Failures

**Installer ABORTS** (exits with error code) if:

1. **Python Version Mismatch**: Python 3.11.x not available
   - Error: `PYTHON VERSION MISMATCH: Python 3.11.x required, found <version>`
   - Exit code: 1

2. **Missing Dependencies**: Cannot install required Python packages in venv
   - Error: Explicit pip install error message
   - Exit code: 1

3. **Port Collision**: Required port is in use during installation
   - Error: Port availability check failure
   - Exit code: 1

4. **Service File Generation Failure**: Cannot create or install `ransomeye-core.service`
   - Error: `Failed to install systemd service`
   - Exit code: 1

5. **Virtual Environment Creation Failure**: Cannot create `/opt/ransomeye/venv/`
   - Error: `Failed to create virtual environment`
   - Exit code: 1

## 7.3 SRM Validation Points

1. **Installer**: Validates SRM compliance during installation
2. **Restore Script**: Validates SRM compliance during restore
3. **Core Startup**: Validates SRM compliance before starting components
4. **Build Process**: Validates SRM compliance during release packaging

## 7.4 Violation Reporting

**All SRM violations MUST**:
- Log explicit error message referencing SRM section
- Exit with non-zero code
- NOT attempt silent fallback or compatibility shim

---

# SECTION 8 — BACKUP & RESTORE CONTRACT

## 8.1 Required Backup Artifacts

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

## 8.2 Restore Invalidation Conditions

**RESTORE FAILS** (abort immediately) if:

1. **Missing Environment File**: `/opt/ransomeye/config/environment` not found
2. **Missing Systemd Unit**: `/etc/systemd/system/ransomeye-core.service` not found
3. **Missing Virtual Environment**: `/opt/ransomeye/venv/` not found (D.7 requirement)
4. **Orchestration Mismatch**: `RANSOMEYE_ORCHESTRATOR=systemd` set but component services missing
5. **Dependency Validation Fails**: Pre-start dependency check fails (missing packages)
6. **Python Version Mismatch**: Python 3.11.x not available on restore system

**RESTORE CONTINUES** (but Core may fail to start) if:

1. Database dump missing (Core cannot connect, but restore completes)
2. System user missing (Core fails with permission error)
3. PostgreSQL not running (Core fails with connection error)

---

# SECTION 9 — CRYPTO & IDENTITY STANDARDS

## 9.1 Key Algorithms

| Algorithm | Purpose | Key Size | Standard |
|-----------|---------|----------|----------|
| **Ed25519** | Command signing, report signing, artifact signing | 256 bits (private), 256 bits (public) | RFC 8032 |
| **Ed25519** | Service-to-service authentication | 256 bits | RFC 8032 |
| **Ed25519** | Supply-chain artifact signing | 256 bits | RFC 8032 |

## 9.2 Hash Algorithms

| Algorithm | Purpose | Output Size | Standard |
|-----------|---------|-------------|----------|
| **SHA256** | File integrity, content hashing | 256 bits | FIPS 180-4 |
| **SHA256** | Database migration checksums | 256 bits | FIPS 180-4 |
| **SHA256** | Event envelope verification | 256 bits | FIPS 180-4 |

## 9.3 Encoding Formats

| Format | Purpose | Standard |
|--------|---------|----------|
| **Base64** | Signature encoding | RFC 4648 |
| **RFC3339 UTC** | Timestamps | RFC 3339 |
| **UUID v4** | Identifiers | RFC 4122 |

## 9.4 Signing Schemes

| Scheme | Purpose | Algorithm | Notes |
|--------|---------|-----------|-------|
| **Ed25519** | Command signing | Ed25519 | Policy Engine → Agent commands |
| **Ed25519** | Report signing | Ed25519 | Signed reports for regulatory |
| **Ed25519** | Artifact signing | Ed25519 | Supply-chain integrity |
| **Ed25519** | Service authentication | Ed25519 | Service-to-service auth |

## 9.5 Key Management

- **Separate Keys**: Each subsystem uses separate keypairs (no key reuse)
- **Key Storage**: Keys stored in `/opt/ransomeye/config/keys/` (component-specific subdirectories)
- **Key Format**: PEM format for Ed25519 keys
- **Key Generation**: Deterministic (RFC 8032 compliant)

## 9.6 Minimum Key Sizes

- **Command Signing Key**: Minimum 32 characters (for `RANSOMEYE_COMMAND_SIGNING_KEY` environment variable)
- **Cryptographic Keys**: 256 bits (Ed25519)
- **Hash Output**: 256 bits (SHA256)

---

# SECTION 10 — CHANGE CONTROL

## 10.1 SRM Modification Rules

1. **Breaking Changes**: Require major version bump (v1.0 → v2.0)
2. **Non-Breaking Changes**: Require minor version bump (v1.0.0 → v1.1.0)
3. **Documentation Only**: Require patch version bump (v1.0.0 → v1.0.1)

## 10.2 Version Authority Rules

### Single Source of Truth

**This SRM is the ONLY authoritative source for**:
- Python package versions
- Python runtime version
- Port numbers
- Cryptographic algorithms
- Orchestration model
- Dependency requirements
- Component privilege requirements

### Module Conformance

**NO MODULE MAY**:
- Override SRM versions
- Introduce version conflicts
- Use undocumented ports
- Introduce implicit dependencies
- Use unsupported orchestration models
- Use unsupported Python versions

---

**END OF SYSTEM REFERENCE MANIFEST**

**This document is LOCKED for v1.0. All changes require formal change control.**

**PHASE D.11 COMPLETE** — SRM restructured into component-scoped sections, Python 3.11.x authoritative, Port Authority Matrix added, Version & Compatibility Matrix added.
