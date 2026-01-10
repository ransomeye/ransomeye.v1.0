# Environment Variable Contract
**RansomEye v1.0 – Canonical Environment Variable Specification**

**AUTHORITATIVE**: This contract defines immutable environment variable requirements for all RansomEye v1.0 services. All services MUST read paths from environment variables. No service may compute paths internally.

---

## Core Principle

**NO PATH COMPUTATION**: Services MUST read all paths from environment variables. Services MUST NOT compute paths internally, MUST NOT use relative paths, MUST NOT assume install locations.

**SINGLE SOURCE OF TRUTH**: Installation manifest is the authoritative source. Environment variables are injected from manifest at service startup.

---

## Required Environment Variables

All environment variables are **REQUIRED** and **MUST** be set before service startup. Missing environment variables MUST cause service startup failure (fail-closed).

### Path Variables (Absolute Paths Only)

#### `RANSOMEYE_INSTALL_ROOT`
- **Type**: Absolute path (string)
- **Required**: YES
- **Description**: Absolute path to installation root directory. MUST be absolute path (starting with /), MUST NOT end with trailing slash. Example: `/opt/ransomeye` or `/home/user/ransomeye`
- **Source**: From `install.manifest.json` → `install_root`
- **Usage**: Base path for all other paths (reference only, services MUST use specific path variables)

#### `RANSOMEYE_BIN_DIR`
- **Type**: Absolute path (string)
- **Required**: YES
- **Description**: Absolute path to binary directory. Contains executable binaries. MUST be absolute path, MUST NOT end with trailing slash. Example: `/opt/ransomeye/bin`
- **Source**: From `install.manifest.json` → `directories.bin`
- **Usage**: Path to service executables

#### `RANSOMEYE_LIB_DIR`
- **Type**: Absolute path (string)
- **Required**: YES
- **Description**: Absolute path to library directory. Contains shared libraries, plugins, modules. MUST be absolute path, MUST NOT end with trailing slash. Example: `/opt/ransomeye/lib`
- **Source**: From `install.manifest.json` → `directories.lib`
- **Usage**: Path to shared libraries and plugins

#### `RANSOMEYE_ETC_DIR`
- **Type**: Absolute path (string)
- **Required**: YES
- **Description**: Absolute path to configuration directory. Contains configuration files. MUST be absolute path, MUST NOT end with trailing slash. Example: `/opt/ransomeye/etc`
- **Source**: From `install.manifest.json` → `directories.etc`
- **Usage**: Path to configuration files

#### `RANSOMEYE_DATA_DIR`
- **Type**: Absolute path (string)
- **Required**: YES
- **Description**: Absolute path to data directory. Contains persistent data, databases, state files. MUST be absolute path, MUST NOT end with trailing slash. Example: `/opt/ransomeye/data`
- **Source**: From `install.manifest.json` → `directories.data`
- **Usage**: Path to database files, persistent state

#### `RANSOMEYE_LOG_DIR`
- **Type**: Absolute path (string)
- **Required**: YES
- **Description**: Absolute path to log directory. Contains log files. MUST be absolute path, MUST NOT end with trailing slash. Example: `/opt/ransomeye/log`
- **Source**: From `install.manifest.json` → `directories.log`
- **Usage**: Path to log files

#### `RANSOMEYE_RUN_DIR`
- **Type**: Absolute path (string)
- **Required**: YES
- **Description**: Absolute path to runtime directory. Contains PID files, sockets, runtime state. MUST be absolute path, MUST NOT end with trailing slash. Example: `/opt/ransomeye/run`
- **Source**: From `install.manifest.json` → `directories.run`
- **Usage**: Path to PID files, Unix domain sockets, runtime state

#### `RANSOMEYE_TMP_DIR`
- **Type**: Absolute path (string)
- **Required**: YES
- **Description**: Absolute path to temporary directory. Contains temporary files. MUST be absolute path, MUST NOT end with trailing slash. Example: `/opt/ransomeye/tmp`
- **Source**: From `install.manifest.json` → `directories.tmp`
- **Usage**: Path to temporary files (cleaned on service restart)

### Runtime Identity Variables

#### `RANSOMEYE_USER`
- **Type**: String (username)
- **Required**: YES
- **Description**: System username for RansomEye runtime. MUST be valid POSIX username. Example: `ransomeye`
- **Source**: From `install.manifest.json` → `runtime_identity.user`
- **Usage**: Username for privilege drop (runtime must drop to this user)

#### `RANSOMEYE_GROUP`
- **Type**: String (groupname)
- **Required**: YES
- **Description**: System groupname for RansomEye runtime. MUST be valid POSIX groupname. Example: `ransomeye`
- **Source**: From `install.manifest.json` → `runtime_identity.group`
- **Usage**: Groupname for privilege drop

#### `RANSOMEYE_UID`
- **Type**: Integer (UID)
- **Required**: YES
- **Description**: Numeric user ID (UID) for RansomEye runtime. MUST be valid UID (1 to 65534). System-assigned UID.
- **Source**: From `install.manifest.json` → `runtime_identity.uid`
- **Usage**: UID for privilege drop (for systems where username lookup may fail)

#### `RANSOMEYE_GID`
- **Type**: Integer (GID)
- **Required**: YES
- **Description**: Numeric group ID (GID) for RansomEye runtime. MUST be valid GID (1 to 65534). System-assigned GID.
- **Source**: From `install.manifest.json` → `runtime_identity.gid`
- **Usage**: GID for privilege drop (for systems where groupname lookup may fail)

### Component Configuration Variables

#### `RANSOMEYE_COMPONENT`
- **Type**: String (enum)
- **Required**: YES
- **Description**: Component identifier for this service instance. MUST be one of: `linux_agent`, `windows_agent`, `dpi`, `core`, `correlation_engine`, `ai_core`
- **Source**: Determined by service startup (which service is being started)
- **Usage**: Component identification for event envelope (matches Phase 1 contract enum)

#### `RANSOMEYE_COMPONENT_INSTANCE_ID`
- **Type**: String (UUID or unique identifier)
- **Required**: YES
- **Description**: Unique identifier for this specific component instance. MUST be unique across all instances of the same component type. UUID v4 recommended. Example: `550e8400-e29b-41d4-a716-446655440000`
- **Source**: Generated by installer or service startup script
- **Usage**: Component instance identification for event envelope (matches Phase 1 contract)

### Version and Bundle Variables

#### `RANSOMEYE_VERSION`
- **Type**: String (version)
- **Required**: YES
- **Description**: RansomEye version string. MUST be exactly `1.0.0` for RansomEye v1.0. Example: `1.0.0`
- **Source**: Hardcoded in installer or service binary
- **Usage**: Version reporting in events, logs, API responses

#### `RANSOMEYE_CONTRACT_BUNDLE_HASH`
- **Type**: String (SHA256 hash)
- **Required**: YES
- **Description**: SHA256 hash of Phase 1 contract bundle. MUST be 64-character hexadecimal string. Used for bundle integrity verification.
- **Source**: From `install.manifest.json` → `bundle_hashes.contract_bundle_sha256`
- **Usage**: Bundle integrity verification at service startup

#### `RANSOMEYE_SCHEMA_BUNDLE_HASH`
- **Type**: String (SHA256 hash)
- **Required**: YES
- **Description**: SHA256 hash of Phase 2 schema bundle. MUST be 64-character hexadecimal string. Used for bundle integrity verification.
- **Source**: From `install.manifest.json` → `bundle_hashes.schema_bundle_sha256`
- **Usage**: Bundle integrity verification at service startup

### Manifest Path Variable

#### `RANSOMEYE_MANIFEST_PATH`
- **Type**: Absolute path (string)
- **Required**: YES
- **Description**: Absolute path to installation manifest file. MUST be absolute path. Example: `/opt/ransomeye/etc/install.manifest.json`
- **Source**: Computed by installer: `${RANSOMEYE_ETC_DIR}/install.manifest.json`
- **Usage**: Path to read installation manifest (for services that need manifest data)

---

## Environment Variable Validation

All services MUST validate environment variables at startup:

1. **Required Variable Check**: All required variables MUST be present. Missing variables MUST cause startup failure.
2. **Path Validation**: All path variables MUST be absolute paths (starting with `/`). Relative paths MUST cause startup failure.
3. **Path Existence**: Services MAY check if directories exist, but MUST NOT create directories (installer responsibility).
4. **Path Permissions**: Services MUST check read/write permissions on required directories. Insufficient permissions MUST cause startup failure.
5. **Type Validation**: UID/GID MUST be valid integers. Component enum MUST match allowed values. Version MUST match expected format.

---

## Environment Variable Injection

Environment variables are injected by:

1. **Service Startup Scripts**: Startup scripts (systemd ExecStart scripts, init scripts) MUST export all required environment variables before starting services.
2. **Manifest Reader**: Startup scripts MUST read `install.manifest.json` and export environment variables.
3. **Fail-Closed**: If manifest cannot be read or parsed, startup MUST fail (do not start service with missing/invalid environment).

---

## Component-Specific Variables

### Core Service
- All core path variables (REQUIRED)
- `RANSOMEYE_COMPONENT=core`
- `RANSOMEYE_COMPONENT_INSTANCE_ID` (REQUIRED, unique UUID)
- Database connection variables (if applicable, defined separately)

### Linux Agent
- All core path variables (REQUIRED)
- `RANSOMEYE_COMPONENT=linux_agent`
- `RANSOMEYE_COMPONENT_INSTANCE_ID` (REQUIRED, unique UUID)
- `RANSOMEYE_MACHINE_ID` (REQUIRED, machine identifier, may be computed from hostname/system ID)

### Windows Agent
- All core path variables (REQUIRED)
- `RANSOMEYE_COMPONENT=windows_agent`
- `RANSOMEYE_COMPONENT_INSTANCE_ID` (REQUIRED, unique UUID)
- `RANSOMEYE_MACHINE_ID` (REQUIRED, machine identifier)

### DPI Probe
- All core path variables (REQUIRED)
- `RANSOMEYE_COMPONENT=dpi`
- `RANSOMEYE_COMPONENT_INSTANCE_ID` (REQUIRED, unique UUID)

### Correlation Engine
- All core path variables (REQUIRED)
- `RANSOMEYE_COMPONENT=correlation_engine`
- `RANSOMEYE_COMPONENT_INSTANCE_ID` (REQUIRED, unique UUID)

### AI Core
- All core path variables (REQUIRED)
- `RANSOMEYE_COMPONENT=ai_core`
- `RANSOMEYE_COMPONENT_INSTANCE_ID` (REQUIRED, unique UUID)

---

## Environment Variable Naming Convention

- **Prefix**: All RansomEye environment variables MUST use prefix `RANSOMEYE_`
- **Uppercase**: All environment variable names MUST be uppercase
- **Underscore separator**: Use underscores to separate words
- **Descriptive**: Variable names MUST be descriptive and unambiguous

---

## Prohibited Patterns

Services MUST NOT:

- Compute paths relative to executable location
- Use `argv[0]` or `__file__` to determine paths
- Assume standard locations (`/opt`, `/usr/local`, `/var`, etc.)
- Use hardcoded paths anywhere in service code
- Read paths from configuration files (paths come from environment only)
- Use relative paths (all paths MUST be absolute)

---

**CONTRACT STATUS**: FROZEN  
**VERSION**: 1.0.0  
**HASH**: [PLACEHOLDER - SHA256 will be inserted here after bundle finalization]
