# PHASE D.7 — RUNTIME DEPENDENCY CONTRACT

**Status**: COMPLETE  
**Date**: 2026-01-18  
**Purpose**: Define authoritative runtime dependency envelope for RansomEye Core v1.0

---

## D.7.1 — Runtime Dependencies (Authoritative)

### System Dependencies (Runtime-Critical)

| Package | Version | Source | Required By | Notes |
|---------|---------|--------|-------------|-------|
| PostgreSQL | 12+ | system (apt/yum) | Core, all components | Database server |
| Python 3 | 3.10+ | system (apt/yum) | Core, all components | Python interpreter |
| python3-dev | - | system (apt/yum) | psycopg2-binary build | For psycopg2 compilation |

### Python Dependencies (Runtime-Critical)

#### Core Dependencies (All Components)
| Package | Version | Required By | Notes |
|---------|---------|-------------|-------|
| psycopg2-binary | ==2.9.9 | Core, all components | PostgreSQL client |
| pydantic | ==2.5.0 | Core, all components | Environment validation |
| pydantic-settings | ==2.1.0 | Core, all components | Settings management |
| python-dateutil | ==2.8.2 | Core, ingest, policy-engine | Date/time parsing |

#### Component-Specific Dependencies

**ingest**:
| Package | Version | Required By | Notes |
|---------|---------|-------------|-------|
| fastapi | ==0.104.1 | ingest, ui-backend | HTTP API framework |
| uvicorn[standard] | ==0.24.0 | ingest, ui-backend | ASGI server |
| jsonschema | ==4.19.2 | ingest | Event schema validation |
| pynacl | ==1.6.2 | ingest | Ed25519 signature verification |
| PyJWT | ==2.10.1 | ingest, ui-backend | JWT authentication |

**ai-core**:
| Package | Version | Required By | Notes |
|---------|---------|-------------|-------|
| numpy | ==1.24.3 | ai-core | Numerical computing |
| scikit-learn | ==1.3.2 | ai-core | Machine learning (clustering) |
| uuid | ==1.30 | ai-core, correlation-engine | UUID generation |

**policy-engine**:
| Package | Version | Required By | Notes |
|---------|---------|-------------|-------|
| cryptography | ==41.0.7 | policy-engine | Command signing |

**ui-backend**:
| Package | Version | Required By | Notes |
|---------|---------|-------------|-------|
| fastapi-cors | ==0.0.6 | ui-backend | CORS support |
| bcrypt | ==4.2.1 | ui-backend | Password hashing |

**correlation-engine**:
| Package | Version | Required By | Notes |
|---------|---------|-------------|-------|
| uuid | ==1.30 | correlation-engine | UUID generation |

### Optional / Feature-Gated Dependencies

None for v1.0 (fail-closed design - all features are required or disabled)

### Build-Time Only Dependencies

None (all dependencies are runtime-required)

---

## D.7.2 — Dependency Contract

### Contract v1.0

**Effective Date**: 2026-01-18  
**Applies To**: RansomEye Core v1.0

#### Exact Package Names and Versions

All Python dependencies MUST be installed with EXACT versions (==) as specified in component `requirements.txt` files:
- `services/ai-core/requirements.txt`
- `services/ingest/requirements.txt`
- `services/correlation-engine/requirements.txt`
- `services/policy-engine/requirements.txt`
- `services/ui/backend/requirements.txt`

#### Minimum Versions

System dependencies have minimum versions:
- PostgreSQL: 12+
- Python: 3.10+

#### Source (Packaging Strategy)

**Chosen**: **Option B — Python Virtual Environment Bundled in /opt/ransomeye/venv**

Justification:
1. **Offline-first**: Virtual environment can be pre-built and bundled in release
2. **Restorable**: Virtual environment is included in backup (part of `/opt/ransomeye/`)
3. **Deterministic**: Exact versions pinned in requirements.txt
4. **Enterprise-grade**: Isolated from system Python, no conflicts
5. **No system modification**: Does not modify system Python packages
6. **Portable**: Can be moved with installation directory

Alternative strategies rejected:
- **Option A (system-level)**: Requires root, conflicts with system packages, not portable
- **Option C (bundled wheel)**: More complex, harder to verify, larger bundle size

#### Component Dependency Mapping

| Component | Required Packages |
|-----------|-------------------|
| Core | psycopg2-binary, pydantic, pydantic-settings, python-dateutil |
| ingest | Core + fastapi, uvicorn[standard], jsonschema, pynacl, PyJWT |
| ai-core | Core + numpy, scikit-learn, uuid |
| correlation-engine | Core + uuid |
| policy-engine | Core + cryptography |
| ui-backend | Core + fastapi, uvicorn[standard], fastapi-cors, PyJWT, bcrypt |

#### Implicit Dependencies

**FORBIDDEN**: All dependencies MUST be explicitly declared in requirements.txt files. No transitive dependencies may be assumed.

---

## D.7.3 — Pre-Start Validation Enforcement

### Implementation

**File**: `core/runtime.py` (add `_validate_runtime_dependencies()` function)

**Enforcement Point**: Before Core starts, validate all required Python packages are importable.

**Failure Behavior**: Core refuses to start, logs exact missing dependency, exits with error code.

**Implementation Details**:

```python
def _validate_runtime_dependencies() -> None:
    """
    D.7.3: Hard pre-flight check - Core refuses to start if any runtime-critical dependency is missing.
    """
    required_packages = {
        "core": ["psycopg2", "pydantic", "pydantic_settings", "dateutil"],
        "ingest": ["fastapi", "uvicorn", "jsonschema", "nacl", "jwt"],
        "ai-core": ["numpy", "sklearn"],
        "correlation-engine": [],
        "policy-engine": ["cryptography"],
        "ui-backend": ["fastapi", "uvicorn", "fastapi_cors", "jwt", "bcrypt"],
    }
    
    missing = []
    for component, packages in required_packages.items():
        for pkg in packages:
            try:
                __import__(pkg.replace("-", "_"))
            except ImportError:
                missing.append(f"{component}:{pkg}")
    
    if missing:
        error_msg = f"RUNTIME DEPENDENCY MISSING: {', '.join(missing)}"
        logger.fatal(error_msg)
        exit_startup_error(error_msg)
```

**Location**: Called in `_initialize_core()` before component startup.

---

## D.7.4 — Packaging Strategy Decision

### Chosen Strategy: **Option B — Python Virtual Environment Bundled in /opt/ransomeye/venv**

### Justification:

1. **Offline-first**: Virtual environment can be pre-built during release packaging and included in release bundle
2. **Restorable**: Virtual environment is part of `/opt/ransomeye/` backup, automatically restored
3. **Deterministic**: Exact versions pinned in requirements.txt, reproducible builds
4. **Enterprise-grade**: Isolated from system Python, no conflicts with system packages
5. **No system modification**: Does not require modifying system-wide Python packages
6. **Portable**: Installation can be moved to different path (with environment update)

### Implementation Requirements:

1. **Installer must create**: `/opt/ransomeye/venv/` virtual environment
2. **Installer must install**: All dependencies from requirements.txt files
3. **Environment file must set**: `PYTHONPATH` and `VIRTUAL_ENV` pointing to `/opt/ransomeye/venv`
4. **Wrapper script must activate**: Virtual environment before running Python

### Alternatives Considered:

**Option A — System-level dependencies (apt/yum, pinned)**:
- REJECTED: Requires root, conflicts with system packages, not portable, modifies system state

**Option C — Fully self-contained wheel bundle**:
- REJECTED: More complex packaging, harder to verify, larger bundle size, less standard

---

## D.7.5 — Backup & Restore Contract Updates

### Updated Recovery Contract (v1.0.2)

#### Dependency Envelope Requirements:

1. **Backup MUST include**: `/opt/ransomeye/venv/` virtual environment (if using Option B)

2. **Restore MUST ensure**: Virtual environment exists and is executable (if using Option B)

3. **Restore validation MUST check**: All runtime-critical dependencies are importable before Core startup

4. **Runtime MUST enforce**: Core refuses to start if any dependency is missing

#### What Constitutes a Recoverable System (Updated):

A system is **RECOVERABLE** if:
1. Backup contains `/opt/ransomeye/` directory with `config/environment` file
2. Backup contains at least one systemd unit file (`ransomeye-core.service`)
3. Backup contains database dump (`.sql` file)
4. **NEW**: Backup contains `/opt/ransomeye/venv/` virtual environment with all dependencies installed

A system is **NOT RECOVERABLE** if:
1. `config/environment` is missing (contains required secrets)
2. No systemd unit files in backup
3. Database dump is missing AND database schema migrations are not available
4. **NEW**: Virtual environment missing or incomplete (missing dependencies)

#### Additional Steps Required (Updated):

1. **System User Creation** (if not exists):
   ```bash
   sudo useradd --system --no-create-home --shell /bin/false ransomeye
   ```

2. **PostgreSQL Prerequisites** (if not met):
   - PostgreSQL must be installed and running
   - `postgres` user must exist (system default)

3. **Dependency Validation** (if virtual environment restored):
   ```bash
   # Virtual environment should be automatically restored with /opt/ransomeye/
   # If missing, restore must fail
   ```

4. **Post-Restore Verification**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl start ransomeye-core  # Pre-start validation will check dependencies
   sudo systemctl status ransomeye-core
   ```

#### Explicit Failures (What Causes Restore to Fail) — Updated:

1. **Missing Environment File**: Restore continues, but Core cannot start (missing secrets)
2. **Missing Systemd Units**: Restore continues, but verification fails
3. **Database Restore Failure**: Restore continues, but Core cannot connect to database
4. **Missing Dependencies**: **NEW** - Core refuses to start, exits with dependency error

**Fail-closed behavior**: Core pre-start validation exits with error if any runtime-critical dependency is missing.

---

## Implementation Checklist

- [x] D.7.1 — Enumerate runtime dependencies
- [x] D.7.2 — Define dependency contract
- [ ] D.7.3 — Enforce pre-start validation (implementation needed)
- [x] D.7.4 — Decide packaging strategy (Option B chosen)
- [x] D.7.5 — Update backup & restore contract
