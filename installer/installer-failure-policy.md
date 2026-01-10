# Installer Failure Semantics
**RansomEye v1.0 – Canonical Installer Failure Policy**

**AUTHORITATIVE**: This document defines immutable failure behavior for RansomEye v1.0 installer. The installer MUST be fail-closed and idempotent. Zero partial state is allowed.

---

## Core Principle

**FAIL-CLOSED**: Installation failures MUST abort installation immediately. Partial installations are forbidden. The installer MUST leave zero partial state on failure.

**IDEMPOTENCY**: The installer MUST be idempotent. Running the installer multiple times with the same parameters MUST produce the same result. Running the installer on an already-installed system MUST be safe (no errors, no duplicate operations).

---

## Failure Categories

### FATAL (Installation Abort)

Fatal failures MUST cause immediate installation abort. No recovery is possible. Installation MUST be rolled back completely (all changes reverted).

#### Fatal Failure Scenarios

1. **Insufficient Privileges**:
   - **Detection**: Installer not running as root/Administrator
   - **Action**: ABORT_INSTALLATION
   - **Rollback**: NONE (no changes made yet)
   - **Error Code**: `INSTALLER_INSUFFICIENT_PRIVILEGES`

2. **Invalid Install Root**:
   - **Detection**: Install root path is invalid (not absolute, contains invalid characters, not writable)
   - **Action**: ABORT_INSTALLATION
   - **Rollback**: NONE (no changes made yet)
   - **Error Code**: `INSTALLER_INVALID_INSTALL_ROOT`

3. **User/Group Creation Failure**:
   - **Detection**: Cannot create runtime user/group (user already exists but UID/GID mismatch, system error)
   - **Action**: ABORT_INSTALLATION
   - **Rollback**: REMOVE_CREATED_USER_GROUP (if created)
   - **Error Code**: `INSTALLER_USER_CREATION_FAILED`

4. **Directory Creation Failure**:
   - **Detection**: Cannot create required directories (permission denied, disk full, invalid path)
   - **Action**: ABORT_INSTALLATION
   - **Rollback**: REMOVE_CREATED_DIRECTORIES (if created)
   - **Error Code**: `INSTALLER_DIRECTORY_CREATION_FAILED`

5. **Manifest Creation Failure**:
   - **Detection**: Cannot write manifest file (permission denied, disk full, invalid JSON)
   - **Action**: ABORT_INSTALLATION
   - **Rollback**: REMOVE_CREATED_DIRECTORIES, REMOVE_CREATED_USER_GROUP
   - **Error Code**: `INSTALLER_MANIFEST_CREATION_FAILED`

6. **Bundle Hash Validation Failure**:
   - **Detection**: Contract bundle hash or schema bundle hash does not match expected value
   - **Action**: ABORT_INSTALLATION
   - **Rollback**: REMOVE_ALL_CREATED_ARTIFACTS
   - **Error Code**: `INSTALLER_BUNDLE_HASH_MISMATCH`

7. **File Installation Failure**:
   - **Detection**: Cannot copy binaries/libraries/config files (source file missing, permission denied, disk full)
   - **Action**: ABORT_INSTALLATION
   - **Rollback**: REMOVE_ALL_CREATED_ARTIFACTS
   - **Error Code**: `INSTALLER_FILE_INSTALLATION_FAILED`

8. **Manifest Schema Validation Failure**:
   - **Detection**: Generated manifest does not conform to schema (invalid JSON, missing required fields, invalid values)
   - **Action**: ABORT_INSTALLATION
   - **Rollback**: REMOVE_ALL_CREATED_ARTIFACTS
   - **Error Code**: `INSTALLER_MANIFEST_SCHEMA_VIOLATION`

---

### RECOVERABLE (Retry or Continue)

Recoverable failures MAY be retried or may allow installation to continue with reduced functionality.

#### Recoverable Failure Scenarios

1. **User/Group Already Exists**:
   - **Detection**: Runtime user/group already exists with correct UID/GID
   - **Action**: CONTINUE_INSTALLATION (user/group creation skipped)
   - **Rollback**: NONE (no changes needed)
   - **Error Code**: `NONE` (warning logged, not an error)

2. **Directory Already Exists**:
   - **Detection**: Required directory already exists
   - **Action**: CONTINUE_INSTALLATION (directory creation skipped, ownership/permissions updated)
   - **Rollback**: NONE (no changes needed)
   - **Error Code**: `NONE` (warning logged, not an error)

3. **Manifest Already Exists**:
   - **Detection**: Manifest file already exists (idempotency check)
   - **Action**: VALIDATE_EXISTING_MANIFEST
   - **If Valid**: CONTINUE_INSTALLATION (installation already complete, skip remaining steps)
   - **If Invalid**: ABORT_INSTALLATION (existing manifest is corrupted, cannot proceed)
   - **Error Code**: `NONE` (if valid) or `INSTALLER_EXISTING_MANIFEST_INVALID` (if invalid)

4. **Partial Installation Detected**:
   - **Detection**: Some directories/files exist but manifest is missing (partial previous installation)
   - **Action**: ABORT_INSTALLATION (cannot recover from partial installation automatically)
   - **Rollback**: NONE (manual cleanup required)
   - **Error Code**: `INSTALLER_PARTIAL_INSTALLATION_DETECTED`

---

## Rollback Rules

### Rollback Strategy

**ATOMIC OPERATIONS**: Installer MUST perform operations atomically where possible. If operation fails mid-way, rollback MUST be performed immediately.

**ROLLBACK ORDER**: Rollback MUST be performed in reverse order of installation:
1. Remove created files
2. Remove created directories
3. Remove created user/group (if created)
4. Remove created install root (if created)

### Rollback Implementation

#### Phase 1: Pre-Installation Check (No Rollback Needed)

- Check privileges (root/Administrator)
- Validate install root path
- Check for existing installation

**Rollback**: NONE (no changes made)

#### Phase 2: User/Group Creation (Rollback: Remove User/Group)

- Create runtime group
- Create runtime user

**Rollback**: Remove runtime user, remove runtime group

#### Phase 3: Directory Creation (Rollback: Remove Directories)

- Create install root directory
- Create subdirectories (bin, lib, etc, data, log, run, tmp)
- Set ownership and permissions

**Rollback**: Remove all created directories (in reverse order)

#### Phase 4: File Installation (Rollback: Remove Files, Then Directories)

- Copy binaries to bin directory
- Copy libraries to lib directory
- Copy configuration files to etc directory
- Set ownership and permissions

**Rollback**: Remove all installed files, then remove directories

#### Phase 5: Manifest Creation (Rollback: Remove Manifest, Then Files, Then Directories)

- Generate manifest JSON
- Validate manifest against schema
- Write manifest to etc/install.manifest.json
- Set ownership and permissions

**Rollback**: Remove manifest file, then remove all installed files, then remove directories

### Rollback Failure Handling

If rollback itself fails (cannot remove created artifacts):

1. **Log Critical Error**: Log all rollback failures to stderr and log file (if available)
2. **Exit with Error Code**: Exit with non-zero exit code indicating rollback failure
3. **Manual Cleanup Required**: Provide clear error message indicating manual cleanup is required
4. **Error Code**: `INSTALLER_ROLLBACK_FAILED`

### Rollback Safety

Rollback MUST be safe:

- **No Data Loss**: Rollback MUST NOT remove user data (only installer-created artifacts)
- **No System Modification**: Rollback MUST NOT modify system files outside install root
- **Idempotent Rollback**: Running rollback multiple times MUST be safe (idempotent)

---

## Idempotency Rules

### Idempotency Requirements

The installer MUST be idempotent:

1. **Same Input, Same Output**: Running installer with same parameters multiple times MUST produce identical result
2. **No Duplicate Operations**: Running installer on already-installed system MUST skip operations that are already complete
3. **No Errors on Re-run**: Running installer on already-installed system MUST NOT produce errors (unless explicitly configured to fail)

### Idempotency Implementation

#### Check for Existing Installation

Before performing any operations, installer MUST:

1. Check if manifest exists (`${install_root}/etc/install.manifest.json`)
2. If manifest exists:
   - Read and validate manifest against schema
   - Compare manifest parameters with current installation parameters
   - If parameters match: SKIP_INSTALLATION (installation already complete)
   - If parameters differ: ABORT_INSTALLATION (cannot modify existing installation, uninstall first)

#### Idempotent Operations

1. **User/Group Creation**: Check if user/group exists before creating. If exists with correct UID/GID, skip creation.
2. **Directory Creation**: Check if directory exists before creating. If exists, update ownership/permissions only.
3. **File Installation**: Check if file exists before copying. If exists and matches hash, skip copying.
4. **Manifest Creation**: Check if manifest exists before writing. If exists and valid, skip writing.

---

## Recovery Procedures

### Manual Recovery from Partial Installation

If installation fails and rollback fails (leaving partial state):

1. **Identify Partial State**: Check which artifacts were created (directories, files, user/group, manifest)
2. **Manual Cleanup**: Remove all artifacts manually:
   - Remove install root directory: `rm -rf ${install_root}`
   - Remove runtime user: `userdel ransomeye` (Linux) or equivalent (Windows)
   - Remove runtime group: `groupdel ransomeye` (Linux) or equivalent (Windows)
3. **Re-run Installer**: After cleanup, re-run installer from scratch

### Recovery from Corrupted Installation

If installation is corrupted (invalid manifest, missing files, etc.):

1. **Uninstall First**: Run uninstaller (if available) or manual cleanup
2. **Re-install**: Re-run installer from scratch

---

## Error Codes

All installer failures MUST use explicit error codes:

- `INSTALLER_INSUFFICIENT_PRIVILEGES`: Insufficient privileges (not root/Administrator)
- `INSTALLER_INVALID_INSTALL_ROOT`: Invalid install root path
- `INSTALLER_USER_CREATION_FAILED`: Failed to create runtime user/group
- `INSTALLER_DIRECTORY_CREATION_FAILED`: Failed to create required directories
- `INSTALLER_MANIFEST_CREATION_FAILED`: Failed to create manifest file
- `INSTALLER_BUNDLE_HASH_MISMATCH`: Bundle hash validation failed
- `INSTALLER_FILE_INSTALLATION_FAILED`: Failed to install files
- `INSTALLER_MANIFEST_SCHEMA_VIOLATION`: Manifest does not conform to schema
- `INSTALLER_PARTIAL_INSTALLATION_DETECTED`: Partial installation detected (manual cleanup required)
- `INSTALLER_EXISTING_MANIFEST_INVALID`: Existing manifest is invalid or corrupted
- `INSTALLER_ROLLBACK_FAILED`: Rollback failed (manual cleanup required)

---

## Exit Codes

Installer MUST use explicit exit codes:

- `0`: Installation successful (or already installed, idempotent)
- `1`: Fatal error (installation aborted, rollback attempted)
- `2`: Fatal error with rollback failure (manual cleanup required)
- `3`: Invalid arguments (usage error)
- `4`: Insufficient privileges (not root/Administrator)

---

## Logging Requirements

All installer operations MUST be logged:

1. **Log File**: Installer MUST write log file to `${install_root}/log/installer.log` (if directory exists) or stderr (if directory does not exist)
2. **Log Format**: Timestamp, log level (INFO, WARN, ERROR, FATAL), message, error code (if applicable)
3. **Log Levels**:
   - **INFO**: Normal operations (directory creation, file installation, etc.)
   - **WARN**: Recoverable issues (existing user/group, existing directories, etc.)
   - **ERROR**: Fatal errors (installation abort, rollback)
   - **FATAL**: Critical errors (rollback failure, system error)

---

## Implementation Requirements

All installer implementations MUST:

1. **Validate privileges at startup**: Check for root/Administrator, abort if insufficient
2. **Check for existing installation**: Read manifest, validate, skip if already installed
3. **Perform operations atomically**: Use atomic operations where possible
4. **Rollback on failure**: Rollback all changes if any operation fails
5. **Log all operations**: Log to file and stderr
6. **Exit with explicit codes**: Use defined exit codes
7. **Fail-closed**: Abort on any fatal error, do not continue with partial state

---

**CONTRACT STATUS**: FROZEN  
**VERSION**: 1.0.0  
**HASH**: [PLACEHOLDER - SHA256 will be inserted here after bundle finalization]
