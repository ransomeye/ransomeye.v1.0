# RansomEye v1.0 DPI Probe Installer

**AUTHORITATIVE:** Production-grade installer for standalone RansomEye DPI Probe

## Overview

This installer provides a complete, production-ready installation of RansomEye DPI Probe on Ubuntu LTS systems. The DPI Probe is a **standalone privileged component** that can be installed and run independently of Core. It captures network packets for deep packet inspection and emits telemetry to Core's Ingest service when Core is available, and fails gracefully (no crash-loops) when Core is unreachable.

## Standalone Nature of DPI Probe

**CRITICAL**: DPI Probe is **standalone** and does NOT require Core to be installed:

- ✅ **Can be installed without Core**: DPI Probe can be installed on systems where Core is not present
- ✅ **Graceful failure**: DPI Probe fails cleanly if Core is unreachable (no crashes, no infinite loops)
- ✅ **No Core dependencies**: DPI Probe has no dependencies on Core installation
- ✅ **Configurable endpoint**: Core endpoint is configurable via environment variable (default: `http://localhost:8000/events`)
- ✅ **Crash-loop prevention**: Systemd service configured to prevent crash-loops if Core is down (max 5 restarts in 5 minutes)

## Required Privileges and Capabilities

**CRITICAL**: DPI Probe requires **scoped privileges** for network packet capture:

- ✅ **CAP_NET_RAW**: Required for raw socket creation (packet capture)
- ✅ **CAP_NET_ADMIN**: Required for network interface configuration
- ✅ **NOT full root**: DPI Probe runs as non-root user (`ransomeye-dpi`) with file capabilities
- ✅ **Capability-based security**: More secure than running as full root

**Capabilities are set on the script file** via `setcap cap_net_raw,cap_net_admin+ep` command. The systemd service runs the probe as user `ransomeye-dpi` but the script inherits file capabilities, allowing packet capture without full root privileges.

**NOTE**: Some filesystems (e.g., NFS, tmpfs) do not support Linux capabilities. Ensure DPI Probe is installed on a filesystem with capability support (e.g., ext4, xfs).

## What the Installer Does

1. **Creates directory structure** (`bin/`, `config/`, `logs/`, `runtime/`) at user-specified install root
2. **Installs DPI Probe Python script** to `bin/` directory
3. **Sets Linux capabilities** (CAP_NET_RAW, CAP_NET_ADMIN) on the script file (scoped privileges, not full root)
4. **Creates system user** `ransomeye-dpi` for secure runtime execution
5. **Generates environment configuration** with all required variables (component instance ID, Core endpoint, network interface, etc.)
6. **Creates ONE systemd service** `ransomeye-dpi.service` (not multiple services)
7. **Validates installation** by starting probe and verifying process execution and capabilities
8. **Fails-closed**: Any error during installation terminates immediately

## Supported OS

- **Ubuntu LTS** (20.04, 22.04, 24.04+)
- **Required**: Python 3.10+ installed
- **Required**: Root privileges for installation (capability management requires root)
- **Required**: Filesystem with capability support (ext4, xfs - not NFS, tmpfs)
- **NOT Required**: Core installation (DPI Probe works standalone)

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

4. **Core installation (optional):**
   - DPI Probe can be installed without Core
   - If Core is installed, provide Core Ingest URL during installation
   - If Core is not installed, probe will fail gracefully when trying to transmit events

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

1. Prompt for installation root directory (e.g., `/opt/ransomeye-dpi`)
2. Check for Python 3.10+
3. Check for libcap2-bin (capability management)
4. Create directory structure
5. Install DPI Probe script
6. Set Linux capabilities (CAP_NET_RAW, CAP_NET_ADMIN)
7. Create system user `ransomeye-dpi`
8. Prompt for Core endpoint (optional, defaults to `http://localhost:8000/events`)
9. Prompt for network interface (optional, empty for auto-detect)
10. Generate environment file
11. Create systemd service
12. Start probe and validate installation

### Step 4: Verify Installation

```bash
# Check service status
sudo systemctl status ransomeye-dpi

# Check logs
sudo journalctl -u ransomeye-dpi -f

# Check if probe executed
sudo journalctl -u ransomeye-dpi --no-pager | grep "STARTUP: DPI Probe starting"

# Verify capabilities are set correctly
getcap /opt/ransomeye-dpi/bin/ransomeye-dpi-probe
# Should show: cap_net_raw,cap_net_admin+ep
```

## Installation Paths

**NO HARDCODED PATHS**: The installer prompts for install root and creates all paths relative to it.

Example installation structure (if install root is `/opt/ransomeye-dpi`):

```
/opt/ransomeye-dpi/
├── bin/
│   └── ransomeye-dpi-probe          # DPI Probe script (with capabilities)
├── config/
│   ├── environment                   # Environment variables (generated)
│   └── installer.manifest.json       # Installation manifest
├── logs/                             # Log files (writable by ransomeye-dpi user)
└── runtime/                          # Runtime files (writable by ransomeye-dpi user)
```

## Configuration

The installer generates `${INSTALL_ROOT}/config/environment` with all required environment variables:

- **Installation paths**: All absolute paths based on install root
- **Probe identity**: Component instance ID (UUID), version
- **Core endpoint**: Ingest service URL (configurable, defaults to `http://localhost:8000/events`)
- **Network interface**: Interface name for packet capture (configurable, empty for auto-detect)
- **DPI configuration**: Capture enabled flag, interface selection
- **Database credentials**: username: `gagan`, password: `gagan` (for future use, if needed)
- **Runtime identity**: User/group IDs

**DO NOT EDIT MANUALLY**: Regenerate using installer if paths change.

### Environment Variables Required by Probe

- `RANSOMEYE_INGEST_URL` (optional): Core Ingest service URL (default: `http://localhost:8000/events`)
- `RANSOMEYE_DPI_CAPTURE_ENABLED` (optional): Enable packet capture (default: `false`)
- `RANSOMEYE_DPI_INTERFACE` (optional): Network interface name for capture (default: empty for auto-detect)

## Service Management

The installer creates **ONE systemd service**: `ransomeye-dpi.service`

### Service Commands

```bash
# Start probe
sudo systemctl start ransomeye-dpi

# Stop probe
sudo systemctl stop ransomeye-dpi

# Check status
sudo systemctl status ransomeye-dpi

# Restart probe
sudo systemctl restart ransomeye-dpi

# Enable auto-start on boot
sudo systemctl enable ransomeye-dpi

# Disable auto-start
sudo systemctl disable ransomeye-dpi

# View logs
sudo journalctl -u ransomeye-dpi -f
sudo journalctl -u ransomeye-dpi --since "1 hour ago"
```

### Service Behavior

- **Probe is long-running**: Runs continuously until stopped or shutdown signal
- **Restart on failure**: Automatically restarts if probe crashes (exit code non-zero)
- **Crash-loop prevention**: After 5 failed attempts in 5 minutes, systemd stops restarting (prevents crash-loop if Core is down)
- **Graceful shutdown**: Handles SIGTERM cleanly (probe exits immediately on signal)
- **Resource limits**: Prevents runaway processes
- **Security hardening**: Runs as unprivileged user with scoped capabilities (not full root)

### Privilege Model

**CRITICAL**: DPI Probe runs with **scoped privileges**, not full root:

- **Service runs as**: User `ransomeye-dpi` (non-root)
- **Capabilities granted**: CAP_NET_RAW, CAP_NET_ADMIN (set on script file via `setcap`)
- **Capability inheritance**: Script inherits file capabilities when executed
- **Security benefit**: More secure than running as full root (least privilege principle)
- **Filesystem requirement**: Must be installed on filesystem with capability support (ext4, xfs)

**Capabilities Explained**:
- **CAP_NET_RAW**: Allows raw socket creation for packet capture (required for network monitoring)
- **CAP_NET_ADMIN**: Allows network interface configuration (required for interface binding)

### Behavior When Core is Unreachable

**CRITICAL**: DPI Probe handles Core unavailability gracefully:

1. **Probe runs**: Probe starts successfully and initializes packet capture (if enabled)
2. **Transmission attempt**: Probe attempts to transmit telemetry to Core Ingest service
3. **Graceful failure**: If Core is unreachable (connection refused, timeout, etc.):
   - Probe logs error message
   - Probe continues running (packet capture may continue, but events not transmitted)
   - Probe may exit with code 3 (RuntimeError) if transmission is critical
   - Systemd restarts probe after 60 seconds (RestartSec=60)
   - After 5 failed attempts in 5 minutes, systemd stops restarting (prevents crash-loop)
4. **No crashes**: Probe does not crash or hang when Core is unreachable
5. **Clean exit**: Probe always exits cleanly with appropriate exit code

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
3. Stop and remove systemd service
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
- Systemd service is updated if already exists
- Installation manifest is regenerated with current timestamp
- DPI Probe script is reinstalled if updated
- Capabilities are reset if changed

## Failure Behavior (Fail-Closed)

The installer implements **fail-closed semantics**:

1. **Any error terminates installation immediately** (no partial state)
2. **Validates all prerequisites before starting** (Python, libcap2-bin, filesystem support, permissions)
3. **Validates installation after completion** (starts service, checks process, verifies capabilities)
4. **Exits with non-zero code on failure** (clear error messages)

If installation fails:

1. Check error message for specific issue
2. Fix the issue (e.g., install Python 3.10+, install libcap2-bin, use supported filesystem)
3. Re-run installer (idempotent, safe to retry)
4. If issue persists, check logs: `sudo journalctl -u ransomeye-dpi`

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
- Check capabilities are set: `getcap /opt/ransomeye-dpi/bin/ransomeye-dpi-probe`
- Should show: `cap_net_raw,cap_net_admin+ep`
- If not set, reinstall or manually set: `sudo setcap cap_net_raw,cap_net_admin+ep /opt/ransomeye-dpi/bin/ransomeye-dpi-probe`
- Verify filesystem supports capabilities

### Probe Exits with Code 3 (RuntimeError)

**This is expected behavior** when Core is unreachable:
- Probe attempts to transmit telemetry to Core
- Core is not available (not installed, not running, network issue, etc.)
- Probe exits with code 3 (RuntimeError) - this is correct behavior
- Systemd will restart probe (with restart limits to prevent crash-loop)

**Solution**: 
- Verify Core is installed and running (if Core should be available)
- Check Core Ingest URL in environment file: `cat /opt/ransomeye-dpi/config/environment | grep RANSOMEYE_INGEST_URL`
- Check network connectivity: `curl http://localhost:8000/health` (if Core is installed)
- If Core is intentionally not installed, this behavior is correct (probe fails gracefully)

### Service Crash-Loops

**This should not happen** due to systemd restart limits:
- Service is configured with `StartLimitBurst=5` and `StartLimitIntervalSec=300`
- After 5 failed attempts in 5 minutes, systemd stops restarting
- Check logs: `sudo journalctl -u ransomeye-dpi --no-pager | tail -50`

**If crash-loop persists**:
- Check probe logs for repeated errors
- Verify probe script is not corrupted: `file /opt/ransomeye-dpi/bin/ransomeye-dpi-probe`
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
2. Check service logs: `sudo journalctl -u ransomeye-dpi`
3. Check application logs: `${INSTALL_ROOT}/logs/`
4. Verify environment: `sudo cat ${INSTALL_ROOT}/config/environment`
5. Verify capabilities: `getcap ${INSTALL_ROOT}/bin/ransomeye-dpi-probe`
6. Verify Core endpoint: `curl ${RANSOMEYE_INGEST_URL}/health` (if Core is installed)
7. Check filesystem: `df -T ${INSTALL_ROOT}` (must support capabilities)

## License

RansomEye v1.0 - Enterprise & Military-Grade Build
