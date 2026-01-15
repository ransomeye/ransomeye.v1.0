# RansomEye v1.0 DPI Probe Installer

**AUTHORITATIVE:** Production-grade installer for Core-supervised RansomEye DPI Probe

## Overview

This installer provides a complete, production-ready installation of the Core-supervised RansomEye DPI Probe on Ubuntu LTS systems. The DPI Probe runs **only under Core supervision**, captures network packets for deep packet inspection, and emits telemetry to Core's Ingest service. If Core/Ingest is unavailable, the probe fails fast so Core can react.

## Core Supervision Requirement

**CRITICAL**: DPI Probe **must** run under Core supervision. There is no standalone service.

- ✅ **Supervised-only**: DPI Probe refuses to start without Core supervision
- ✅ **Fail-fast**: If Core/Ingest is unavailable, the probe exits and Core reacts
- ✅ **Deterministic**: No stub loops or idle "RUNNING" state

## Required Privileges and Capabilities

**CRITICAL**: DPI Probe requires **scoped privileges** for network packet capture:

- ✅ **CAP_NET_RAW**: Required for raw socket creation (packet capture)
- ✅ **CAP_NET_ADMIN**: Required for network interface configuration
- ✅ **NOT full root**: DPI Probe runs as non-root user (`ransomeye-dpi`) with file capabilities
- ✅ **Capability-based security**: More secure than running as full root

**Capabilities are set on the script file** via `setcap cap_net_raw,cap_net_admin+ep` command. Core launches the probe as user `ransomeye-dpi`, and the script inherits file capabilities, allowing packet capture without full root privileges.

**NOTE**: Some filesystems (e.g., NFS, tmpfs) do not support Linux capabilities. Ensure DPI Probe is installed on a filesystem with capability support (e.g., ext4, xfs).

## What the Installer Does

1. **Creates directory structure** (`bin/`, `config/`, `lib/`, `logs/`, `runtime/`) at user-specified install root
2. **Installs DPI Probe Python script** to `bin/` directory
3. **Builds AF_PACKET fastpath library** into `lib/`
4. **Sets Linux capabilities** (CAP_NET_RAW, CAP_NET_ADMIN) on the script file (scoped privileges, not full root)
5. **Creates system user** `ransomeye-dpi` for secure runtime execution
6. **Generates telemetry signing keys** in `config/component-keys`
7. **Generates environment configuration** with all required variables (component instance ID, Core endpoint, network interface, etc.)
8. **Validates installation** by verifying fastpath library and capabilities
9. **Fails-closed**: Any error during installation terminates immediately

## Supported OS

- **Ubuntu LTS** (20.04, 22.04, 24.04+)
- **Required**: Python 3.10+ installed
- **Required**: Root privileges for installation (capability management requires root)
- **Required**: Filesystem with capability support (ext4, xfs - not NFS, tmpfs)
- **Required**: Core installation (DPI Probe runs only under Core supervision)

## Prerequisites

Before running the installer, ensure:

1. **Python 3.10+ is installed:**
   ```bash
   python3 --version  # Should show Python 3.10 or higher
   # If not installed: sudo apt-get install python3
   ```

2. **libcap2-bin is installed** (for capability management):
   ```bash
   sudo apt-get install libcap2-bin
   ```

3. **Filesystem supports capabilities:**
   - DPI Probe must be installed on a filesystem with capability support
   - ext4, xfs: ✅ Supported
   - NFS, tmpfs: ❌ Not supported
   - Check filesystem: `df -T $(pwd) | tail -1 | awk '{print $2}'`

4. **Build tools installed** (for AF_PACKET fastpath build):
   ```bash
   sudo apt-get install build-essential
   ```

5. **PyNaCl installed** (telemetry signing):
   ```bash
   python3 -m pip install pynacl
   ```

6. **Core installed and running:**
   - DPI Probe runs only under Core supervision

## How to Install

### Step 1: Download Installer

Extract the RansomEye DPI Probe installer package to a temporary directory:

```bash
cd /tmp
tar -xzf ransomeye-dpi-probe-installer.tar.gz
cd ransomeye-dpi-probe-installer/installer/dpi-probe
```

### Step 2: Make Installer Executable

```bash
chmod +x install.sh
```

### Step 3: Run Installer as Root

```bash
sudo ./install.sh
```

The installer will:

1. Prompt for installation root directory (e.g., `/opt/ransomeye`)
2. Check for Python 3.10+
3. Check for libcap2-bin (capability management)
4. Create directory structure
5. Install DPI Probe script
6. Build AF_PACKET fastpath library
7. Set Linux capabilities (CAP_NET_RAW, CAP_NET_ADMIN)
8. Create system user `ransomeye-dpi`
9. Generate telemetry signing keys
10. Prompt for Core endpoint
11. Prompt for network interface
12. Generate environment file
13. Validate installation

### Step 4: Verify Installation

```bash
# Verify capabilities are set correctly
getcap /opt/ransomeye/bin/ransomeye-dpi-probe
# Should show: cap_net_raw,cap_net_admin+ep

# Verify fastpath library exists
ls /opt/ransomeye/lib/libransomeye_dpi_af_packet.so
```

## Installation Paths

**NO HARDCODED PATHS**: The installer prompts for install root and creates all paths relative to it.

Example installation structure (if install root is `/opt/ransomeye`):

```
/opt/ransomeye/
├── bin/
│   └── ransomeye-dpi-probe          # DPI Probe script (with capabilities)
├── config/
│   ├── environment                   # Environment variables (generated)
│   └── installer.manifest.json       # Installation manifest
│   └── component-keys/               # Telemetry signing keys
│   └── keys/                         # Service auth keys
├── lib/
│   └── libransomeye_dpi_af_packet.so # AF_PACKET capture library
├── logs/                             # Log files (writable by ransomeye-dpi user)
└── runtime/                          # Runtime files (writable by ransomeye-dpi user)
```

## Configuration

The installer generates `${INSTALL_ROOT}/config/environment` with all required environment variables:

- **Installation paths**: All absolute paths based on install root
- **Probe identity**: Component instance ID (UUID), version
- **Core endpoint**: Ingest service URL
- **Network interface**: Interface name for packet capture
- **DPI configuration**: Capture backend, flow timeout, privacy controls
- **Telemetry keys**: Component key directory for signatures
- **Runtime identity**: User/group IDs

**DO NOT EDIT MANUALLY**: Regenerate using installer if paths change.

### Environment Variables Required by Probe

- `RANSOMEYE_INGEST_URL` (required): Core Ingest service URL
- `RANSOMEYE_DPI_CAPTURE_BACKEND` (optional): Capture backend (`af_packet_c`)
- `RANSOMEYE_DPI_INTERFACE` (required): Network interface name for capture
- `RANSOMEYE_DPI_FASTPATH_LIB` (required): Path to AF_PACKET library
- `RANSOMEYE_COMPONENT_KEY_DIR` (required): Telemetry signing key directory
- `RANSOMEYE_SERVICE_KEY_DIR` (required): Service auth key directory

## Core Supervision

The DPI Probe is launched by Core orchestrator and **must not** be started directly.

### Behavior When Core is Unreachable

**CRITICAL**: DPI Probe fails fast when Core/Ingest is unavailable:

1. **Probe attempts telemetry**: Events are sent immediately
2. **Failure triggers exit**: Any telemetry failure causes probe to exit
3. **Core reacts**: Core supervision treats DPI as critical

**Exit Codes**:
- `0` (Success): Normal completion or graceful shutdown
- `1` (ConfigError): Missing or invalid configuration
- `2` (StartupError): Startup failure (e.g., capability check failure)
- `3` (RuntimeError): Transmission failure (Core unreachable or HTTP error)
- `4` (FatalError): Fatal error (unexpected failure)

## How to Uninstall

### Step 1: Run Uninstaller

```bash
cd /tmp/ransomeye-dpi-probe-installer/installer/dpi-probe
chmod +x uninstall.sh
sudo ./uninstall.sh
```

The uninstaller will:

1. Detect installation directory (from manifest or prompt)
2. Remove Linux capabilities from script file
3. Remove DPI artifacts and keys
4. Remove installation directory (with confirmation)
5. Optionally remove system user (with confirmation)

### Step 2: Manual Cleanup (Optional)

If you want to remove system user manually:

```bash
sudo userdel ransomeye-dpi
```

## Idempotency

The installer is **idempotent**: running it multiple times on the same install root is safe.

- Existing files are preserved (not overwritten unless necessary)
- System user creation is skipped if user exists
- Configuration and keys are regenerated if already exists
- Installation manifest is regenerated with current timestamp
- DPI Probe script is reinstalled if updated
- Capabilities are reset if changed

## Failure Behavior (Fail-Closed)

The installer implements **fail-closed semantics**:

1. **Any error terminates installation immediately** (no partial state)
2. **Validates all prerequisites before starting** (Python, libcap2-bin, filesystem support, permissions)
3. **Validates installation after completion** (verifies fastpath library and capabilities)
4. **Exits with non-zero code on failure** (clear error messages)

If installation fails:

1. Check error message for specific issue
2. Fix the issue (e.g., install Python 3.10+, install libcap2-bin, use supported filesystem)
3. Re-run installer (idempotent, safe to retry)
4. If issue persists, check Core logs and DPI logs under `${INSTALL_ROOT}/logs/`

## Troubleshooting

### Installation Fails: "Python 3 is not installed"

**Solution**: Install Python 3.10+:
```bash
sudo apt-get install python3
python3 --version  # Verify installation
```

### Installation Fails: "setcap command not found"

**Solution**: Install libcap2-bin:
```bash
sudo apt-get install libcap2-bin
```

### Installation Fails: "Failed to set capabilities"

**Solution**: 
- Check filesystem supports capabilities: `df -T $(pwd) | tail -1 | awk '{print $2}'`
- DPI Probe must be installed on ext4 or xfs filesystem (not NFS, tmpfs)
- Reinstall on a supported filesystem

### Probe Fails to Start: "Permission denied"

**Solution**: 
- Check capabilities are set: `getcap /opt/ransomeye/bin/ransomeye-dpi-probe`
- Should show: `cap_net_raw,cap_net_admin+ep`
- If not set, reinstall or manually set: `sudo setcap cap_net_raw,cap_net_admin+ep /opt/ransomeye/bin/ransomeye-dpi-probe`
- Verify filesystem supports capabilities

### Probe Exits on Telemetry Failure

**This is expected behavior** when Core/Ingest is unreachable:
- Probe attempts to transmit telemetry to Core Ingest
- Any transmission failure causes the probe to exit
- Core supervision treats DPI as critical and reacts

**Solution**:
- Verify Core is installed and running
- Check Core Ingest URL in environment file: `cat /opt/ransomeye/config/environment | grep RANSOMEYE_INGEST_URL`
- Check network connectivity: `curl http://localhost:8000/health` (if Core is installed)
- Check logs: `${INSTALL_ROOT}/logs/`

**If crash-loop persists**:
- Check probe logs for repeated errors
- Verify probe script is not corrupted: `file /opt/ransomeye/bin/ransomeye-dpi-probe`
- Verify capabilities are set correctly
- Check filesystem supports capabilities
- Rebuild and reinstall probe

## Security Considerations

1. **Runtime runs as unprivileged user** (`ransomeye-dpi`) - no root privileges by default
2. **Capabilities are scoped** - only CAP_NET_RAW and CAP_NET_ADMIN (not full root)
3. **Environment file is read-only** (600 permissions) - secrets not exposed
4. **Systemd hardening** - restricted filesystem access, no new privileges
5. **Least privilege principle** - only required capabilities are granted
6. **Filesystem requirement** - capabilities only work on supported filesystems (ext4, xfs)

## Support

For issues or questions:

1. Check installation manifest: `${INSTALL_ROOT}/config/installer.manifest.json`
2. Check DPI logs: `${INSTALL_ROOT}/logs/`
3. Check application logs: `${INSTALL_ROOT}/logs/`
4. Verify environment: `sudo cat ${INSTALL_ROOT}/config/environment`
5. Verify capabilities: `getcap ${INSTALL_ROOT}/bin/ransomeye-dpi-probe`
6. Verify Core endpoint: `curl ${RANSOMEYE_INGEST_URL}/health` (if Core is installed)
7. Check filesystem: `df -T ${INSTALL_ROOT}` (must support capabilities)

## License

RansomEye v1.0 - Enterprise & Military-Grade Build
