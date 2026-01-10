# Privilege Model
**RansomEye v1.0 – Canonical Privilege Model**

**AUTHORITATIVE**: This document defines immutable privilege requirements for RansomEye v1.0 installer and runtime components.

---

## Core Principle

**PRIVILEGE SEPARATION**: Installer runs with elevated privileges (root or administrator). Runtime services run with minimal privileges (dropped to dedicated user/group).

**FAIL-CLOSED**: Insufficient privileges MUST cause installation or service startup failure. No service may run with excessive privileges.

---

## Installer Privilege Requirements

### Minimum Required Privileges

The installer MUST run with the following privileges:

1. **User/Group Creation**:
   - Create system user (POSIX: `useradd` or equivalent)
   - Create system group (POSIX: `groupadd` or equivalent)
   - Assign UID/GID (or use system-assigned UID/GID)

2. **Directory Creation**:
   - Create installation root directory (if it does not exist)
   - Create all subdirectories (bin, lib, etc, data, log, run, tmp)
   - Set directory ownership to runtime user/group
   - Set directory permissions (755 for directories, 644 for files by default)

3. **File Installation**:
   - Copy binaries to bin directory
   - Copy libraries to lib directory
   - Copy configuration files to etc directory
   - Set file ownership to runtime user/group
   - Set file permissions (755 for executables, 644 for configuration files)

4. **Manifest Creation**:
   - Write `install.manifest.json` to etc directory
   - Set manifest file ownership to runtime user/group
   - Set manifest file permissions (644, readable by runtime user, writable by installer only)

5. **System Integration** (if applicable):
   - Create systemd unit files (requires root)
   - Create init scripts (requires root)
   - Register services with system service manager (requires root)

### Installer Execution Context

- **POSIX/Linux**: Installer MUST run as `root` (UID 0)
- **Windows**: Installer MUST run as Administrator (elevated privileges)
- **macOS**: Installer MUST run as Administrator (elevated privileges)

### Installer Privilege Validation

The installer MUST validate privileges at startup:

1. **Check for root/elevated privileges**: If not running as root/Administrator, abort installation with clear error message.
2. **Check for required capabilities**: Verify that user/group creation, directory creation, and file installation are possible.
3. **Fail-closed**: If privileges are insufficient, abort installation immediately. Do not attempt partial installation.

---

## Runtime Privilege Drop Rules

### General Rule

**ALL runtime services MUST drop privileges to dedicated user/group after startup initialization.**

### Privilege Drop Sequence

1. **Service Startup** (as root/elevated):
   - Read environment variables (from manifest or startup script)
   - Validate paths and permissions
   - Initialize resources that require elevated privileges (if any)

2. **Immediate Privilege Drop**:
   - Drop to runtime user/group (`RANSOMEYE_USER` / `RANSOMEYE_GROUP`)
   - Use UID/GID from environment variables (`RANSOMEYE_UID` / `RANSOMEYE_GID`)
   - Drop supplementary groups
   - Verify privilege drop succeeded

3. **Runtime Execution** (as runtime user):
   - All service operations MUST run as runtime user
   - No elevated privileges during normal operation
   - No privilege escalation allowed

### Runtime Privilege Requirements

Runtime services require the following privileges (as runtime user):

1. **Read Access**:
   - Read configuration files (etc directory)
   - Read binaries and libraries (bin, lib directories)
   - Read manifest file (etc/install.manifest.json)

2. **Write Access**:
   - Write log files (log directory)
   - Write PID files (run directory)
   - Write runtime state files (run directory, if applicable)
   - Write temporary files (tmp directory)

3. **Execute Access**:
   - Execute binaries (bin directory)
   - Load libraries (lib directory)

4. **Database Access** (Core service only):
   - Read/write database files (data directory)
   - Create database files and directories (data directory)

### Prohibited Privileges

Runtime services MUST NOT:

- Run as root (UID 0) during normal operation
- Run with elevated privileges (setuid, setgid binaries)
- Access files outside installation root (unless explicitly configured)
- Modify system files (outside installation root)
- Bind to privileged ports (< 1024) without explicit configuration
- Escalate privileges (no sudo, no su, no privilege escalation mechanisms)

---

## Agent/DPI Exception Boundaries

### Agent Components (Linux Agent, Windows Agent)

Agents require **elevated privileges** for specific operations:

#### Linux Agent Exception Boundaries

1. **System Call Interception**:
   - Requires root or `CAP_SYS_ADMIN` capability for kernel module loading (if applicable)
   - Requires root or `CAP_SYS_PTRACE` capability for process tracing
   - Requires root or `CAP_SYS_CHROOT` capability for chroot operations (if applicable)

2. **File System Monitoring**:
   - Requires root or `CAP_DAC_OVERRIDE` capability for accessing files outside user's permissions
   - Requires root or `CAP_DAC_READ_SEARCH` capability for reading files outside user's permissions

3. **Network Monitoring**:
   - Requires root or `CAP_NET_RAW` capability for raw socket operations
   - Requires root or `CAP_NET_ADMIN` capability for network interface configuration

**Privilege Strategy for Linux Agent**:

- **Option 1 (Recommended)**: Run agent as root, but isolate operations using capabilities (drop all capabilities except required ones)
- **Option 2**: Run agent as runtime user, but use setuid/setgid wrapper for specific operations (not recommended, security risk)
- **Option 3**: Use kernel module or eBPF program that runs with kernel privileges (kernel-level agent, not user-space agent)

**Implementation Requirement**: If Linux agent requires elevated privileges, installer MUST document this requirement clearly. Installer MUST NOT install Linux agent with excessive privileges unless explicitly configured.

#### Windows Agent Exception Boundaries

1. **System Call Interception**:
   - Requires Administrator privileges for kernel-mode driver installation (if applicable)
   - Requires Administrator privileges for ETW (Event Tracing for Windows) session creation

2. **Process Monitoring**:
   - Requires Administrator privileges or `SeDebugPrivilege` for process enumeration and injection detection

3. **Registry Monitoring**:
   - Requires Administrator privileges or `SeBackupPrivilege` for registry key monitoring

**Privilege Strategy for Windows Agent**:

- Run agent as Administrator or with specific privileges (`SeDebugPrivilege`, `SeBackupPrivilege`)
- Installer MUST document privilege requirements clearly
- Installer MUST NOT install Windows agent with excessive privileges unless explicitly configured

### DPI Probe Exception Boundaries

DPI probe requires **elevated privileges** for network packet capture:

#### DPI Probe Privilege Requirements

1. **Network Packet Capture**:
   - **Linux**: Requires root or `CAP_NET_RAW` capability for raw socket operations (libpcap)
   - **Windows**: Requires Administrator privileges for WinPcap/Npcap driver access
   - **macOS**: Requires root for packet capture (BPF device access)

2. **Network Interface Access**:
   - Requires root or `CAP_NET_ADMIN` capability for network interface configuration (promiscuous mode)

**Privilege Strategy for DPI Probe**:

- **Option 1 (Recommended)**: Run DPI probe as root, but isolate operations using capabilities (drop all capabilities except `CAP_NET_RAW` and `CAP_NET_ADMIN`)
- **Option 2**: Use setuid/setgid wrapper for packet capture operations (not recommended, security risk)
- **Option 3**: Use dedicated packet capture daemon (tcpdump, Wireshark) with appropriate privileges, DPI probe runs as runtime user and receives packets from daemon

**Implementation Requirement**: If DPI probe requires elevated privileges, installer MUST document this requirement clearly. Installer MUST NOT install DPI probe with excessive privileges unless explicitly configured.

---

## Privilege Model Enforcement

### Installer Enforcement

1. **Privilege Check at Startup**: Installer MUST verify it is running with required privileges (root/Administrator).
2. **Privilege Check During Installation**: Installer MUST verify it can perform all required operations (user creation, directory creation, file installation).
3. **Fail-Closed**: If privileges are insufficient, installer MUST abort installation immediately.

### Runtime Enforcement

1. **Privilege Drop Verification**: Services MUST verify privilege drop succeeded (check UID/GID after drop).
2. **Runtime Privilege Check**: Services MUST check required permissions at startup (read/write permissions on directories).
3. **Fail-Closed**: If privileges are insufficient, services MUST abort startup immediately.

### Exception Boundary Enforcement

1. **Capability Isolation**: Agents/DPI that require elevated privileges MUST use capability isolation (Linux) or privilege separation (Windows).
2. **Minimal Privilege**: Agents/DPI MUST use minimal privileges required for their operations (drop all unnecessary capabilities/privileges).
3. **Audit Trail**: All privilege operations MUST be logged (who, what, when, why).

---

## Security Considerations

### Principle of Least Privilege

- Installer: Run with elevated privileges only during installation. After installation, installer has no ongoing privileges.
- Runtime: Run with minimal privileges required for normal operation.
- Agents/DPI: Use elevated privileges only for specific operations, isolate using capabilities or privilege separation.

### Privilege Escalation Prevention

- Services MUST NOT escalate privileges during runtime (no sudo, no su, no privilege escalation mechanisms).
- Services MUST NOT modify their own privilege level (no setuid, no setgid, except for explicitly configured exception boundaries).

### Audit and Monitoring

- All privilege operations MUST be logged (privilege drop, capability usage, elevated operation attempts).
- All privilege violations MUST be logged (insufficient privileges, privilege escalation attempts).
- Logs MUST include: timestamp, component, operation, privilege level, result (success/failure).

---

## Implementation Requirements

All components implementing privilege model MUST:

1. **Validate privileges at startup**: Check for required privileges, abort if insufficient.
2. **Drop privileges immediately**: Drop to runtime user/group as soon as possible after startup.
3. **Verify privilege drop**: Confirm privilege drop succeeded before continuing.
4. **Check permissions**: Verify required read/write/execute permissions on directories and files.
5. **Log privilege operations**: Log all privilege operations (drop, check, violations).
6. **Fail-closed**: Abort on insufficient privileges, do not continue with partial privileges.

---

**CONTRACT STATUS**: FROZEN  
**VERSION**: 1.0.0  
**HASH**: [PLACEHOLDER - SHA256 will be inserted here after bundle finalization]
