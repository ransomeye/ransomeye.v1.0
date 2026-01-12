# RansomEye v1.0 Enterprise Release Bundle

**AUTHORITATIVE:** Enterprise-grade release bundle for RansomEye v1.0

## What is RansomEye?

RansomEye is an enterprise and military-grade threat detection and response platform designed to identify, analyze, and respond to ransomware attacks in real-time. It provides comprehensive visibility into system behavior, network traffic, and threat indicators through multiple specialized components working together.

## Components Overview

This release bundle contains **four production-grade installers** for RansomEye components:

### 1. **RansomEye Core** (`core/`)

**Purpose**: Unified runtime that orchestrates all Core components as a single integrated service.

**Components Included**:
- Ingest Service (receives events from agents)
- Correlation Engine (correlates events and detects patterns)
- AI Core (machine learning analysis)
- Policy Engine (policy enforcement and command signing)
- UI Backend (web API for management interface)

**Standalone**: ❌ **No** - Core is required for full functionality

**Service**: `ransomeye-core.service` (systemd)

**Prerequisites**: PostgreSQL, Python 3.8+, FastAPI, Uvicorn

**Supported OS**: Ubuntu LTS 20.04+, 22.04+, 24.04+

### 2. **RansomEye Linux Agent** (`linux-agent/`)

**Purpose**: Standalone agent that monitors Linux systems and emits events to Core.

**Standalone**: ✅ **Yes** - Can be installed independently of Core

**Service**: `ransomeye-linux-agent.service` (systemd)

**Prerequisites**: Rust toolchain (for building), Python 3.10+

**Supported OS**: Ubuntu LTS 20.04+, 22.04+, 24.04+

**Required Privileges**: None (runs as non-root user)

### 3. **RansomEye Windows Agent** (`windows-agent/`)

**Purpose**: Standalone agent that monitors Windows systems and emits events to Core.

**Standalone**: ✅ **Yes** - Can be installed independently of Core

**Service**: `RansomEyeWindowsAgent` (Windows Service)

**Prerequisites**: Rust toolchain (for building), Windows Agent binary (.exe)

**Supported OS**: Windows Server 2016+, 2019+, 2022+, Windows 10 Enterprise/Pro, Windows 11 Enterprise/Pro

**Required Privileges**: None (runs as non-Administrator user)

### 4. **RansomEye DPI Probe** (`dpi-probe/`)

**Purpose**: Standalone privileged component for deep packet inspection and network monitoring.

**Standalone**: ✅ **Yes** - Can be installed independently of Core

**Service**: `ransomeye-dpi.service` (systemd)

**Prerequisites**: Python 3.10+, libcap2-bin, filesystem with capability support (ext4, xfs)

**Supported OS**: Ubuntu LTS 20.04+, 22.04+, 24.04+

**Required Privileges**: 
- **CAP_NET_RAW**: Required for raw socket creation (packet capture)
- **CAP_NET_ADMIN**: Required for network interface configuration
- **NOT full root**: Runs as non-root user with file capabilities (scoped privileges)

## Installation Order (Optional)

Components can be installed **independently or together** depending on your deployment strategy:

### Recommended Installation Order:

1. **Install Core First** (if using full RansomEye stack):
   ```bash
   cd core
   sudo ./install.sh
   ```

2. **Install Agents** (Linux/Windows) on target systems:
   ```bash
   # Linux
   cd linux-agent
   sudo ./install.sh
   
   # Windows
   cd windows-agent
   # Right-click install.bat, select "Run as administrator"
   ```

3. **Install DPI Probe** (optional, for network monitoring):
   ```bash
   cd dpi-probe
   sudo ./install.sh
   ```

### Standalone Installation:

Each component can be installed **standalone** without other components:
- **Linux Agent**: Can emit events even if Core is not yet installed (will fail gracefully)
- **Windows Agent**: Can emit events even if Core is not yet installed (will fail gracefully)
- **DPI Probe**: Can capture packets even if Core is not yet installed (will fail gracefully when transmitting)
- **Core**: Required for processing events from agents and probes

## Standalone vs Core Components

### Standalone Components (Can Install Independently):

- ✅ **Linux Agent**: No Core dependency
- ✅ **Windows Agent**: No Core dependency
- ✅ **DPI Probe**: No Core dependency

**Behavior When Core is Unreachable**:
- Standalone components fail gracefully (no crashes, no infinite loops)
- Components continue running but cannot transmit events
- Systemd/Windows Service restarts with limits to prevent crash-loops
- After 5 failed attempts in 5 minutes, service stops restarting (prevents crash-loop)

### Core Component (Required for Full Functionality):

- ❌ **Core**: Required for processing events and full platform functionality

**Core Provides**:
- Event ingestion and validation
- Event correlation and pattern detection
- AI-based threat analysis
- Policy enforcement and command signing
- Web API for management interface

## Credentials Policy

**CRITICAL**: RansomEye v1.0 uses **fixed credentials** for database access:

- **Database Username**: `gagan`
- **Database Password**: `gagan`

**Note**: These are **default credentials** for v1.0. **Change credentials in production deployments** for security.

### Database Setup Example (PostgreSQL):

```bash
sudo -u postgres psql -c "CREATE DATABASE ransomeye;"
sudo -u postgres psql -c "CREATE USER gagan WITH PASSWORD 'gagan';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ransomeye TO gagan;"
sudo -u postgres psql -d ransomeye -c "GRANT ALL ON SCHEMA public TO gagan;"
```

## Supported OS Matrix

| Component | Ubuntu LTS | Windows Server | Windows 10/11 |
|-----------|-----------|----------------|---------------|
| Core | ✅ 20.04+, 22.04+, 24.04+ | ❌ | ❌ |
| Linux Agent | ✅ 20.04+, 22.04+, 24.04+ | ❌ | ❌ |
| Windows Agent | ❌ | ✅ 2016+, 2019+, 2022+ | ✅ Enterprise, Pro |
| DPI Probe | ✅ 20.04+, 22.04+, 24.04+ | ❌ | ❌ |

## Security & Privilege Model

### Core Runtime:
- **Runtime User**: `ransomeye` (non-root)
- **Required Privileges**: None (runs as unprivileged user)
- **Security Hardening**: NoNewPrivileges, ProtectSystem, ProtectHome

### Linux Agent:
- **Runtime User**: `ransomeye-agent` (non-root)
- **Required Privileges**: None (runs as unprivileged user)
- **Security Hardening**: NoNewPrivileges, ProtectSystem, ProtectHome

### Windows Agent:
- **Runtime User**: `ransomeye-agent` (non-Administrator)
- **Required Privileges**: None (runs as unprivileged user)
- **Security Hardening**: Minimal filesystem access, service recovery limits

### DPI Probe (Privileged Component):
- **Runtime User**: `ransomeye-dpi` (non-root)
- **Required Privileges**: **CAP_NET_RAW**, **CAP_NET_ADMIN** (file capabilities, not full root)
- **Security Model**: Capability-based security (scoped privileges)
- **Security Hardening**: NoNewPrivileges, ProtectSystem, ProtectHome, file capabilities
- **Filesystem Requirement**: Must be installed on filesystem with capability support (ext4, xfs)

**Capabilities Explained**:
- **CAP_NET_RAW**: Allows raw socket creation for packet capture (required for network monitoring)
- **CAP_NET_ADMIN**: Allows network interface configuration (required for interface binding)

**Why Not Full Root?**:
- Capability-based security is more secure than running as full root
- Only required capabilities are granted (least privilege principle)
- Reduced attack surface and privilege escalation risk

## How to Validate Integrity

### Step 1: Verify Checksums

Run the validation script to verify all file checksums:

```bash
cd ransomeye-v1.0
./validate-release.sh
```

The validation script will:
- ✅ Verify checksums file format
- ✅ Verify all checksummed files exist
- ✅ Verify all checksums match
- ✅ Verify required component files exist
- ✅ Verify audit artifacts exist
- ✅ Verify signature file (optional)

### Step 2: Manual Checksum Verification

Manually verify checksums:

```bash
cd ransomeye-v1.0
sha256sum -c checksums/SHA256SUMS
```

### Step 3: Verify Signature (Optional)

If GPG signing key is available:

```bash
cd ransomeye-v1.0
gpg --verify checksums/SHA256SUMS.sig checksums/SHA256SUMS
```

**Note**: The included signature file is a placeholder. In production, the release should be signed with a GPG key.

### Step 4: Verify Component Manifests

Check component manifests for expected structure:

```bash
cd ransomeye-v1.0
cat audit/component-manifest.json | jq '.components[] | {name: .name, standalone: .standalone, service: .service_name}'
```

## Release Bundle Structure

```
ransomeye-v1.0/
├── core/                          # Core installer
│   ├── install.sh
│   ├── uninstall.sh
│   ├── ransomeye-core.service
│   ├── installer.manifest.json
│   └── README.md
├── linux-agent/                   # Linux Agent installer
│   ├── install.sh
│   ├── uninstall.sh
│   ├── ransomeye-linux-agent.service
│   ├── installer.manifest.json
│   └── README.md
├── windows-agent/                 # Windows Agent installer
│   ├── install.bat
│   ├── uninstall.bat
│   ├── ransomeye-windows-agent.service.txt
│   ├── installer.manifest.json
│   └── README.md
├── dpi-probe/                     # DPI Probe installer
│   ├── install.sh
│   ├── uninstall.sh
│   ├── ransomeye-dpi.service
│   ├── installer.manifest.json
│   └── README.md
├── checksums/                     # Integrity artifacts
│   ├── SHA256SUMS                 # SHA256 checksums for all files
│   └── SHA256SUMS.sig             # GPG signature (placeholder)
├── audit/                         # Audit artifacts
│   ├── build-info.json            # Build metadata
│   └── component-manifest.json    # Component manifest
├── validate-release.sh            # Release validation script
└── README.md                      # This file
```

## Installation Instructions

### Quick Start (Full Stack):

1. **Install Core**:
   ```bash
   cd core
   sudo ./install.sh
   ```

2. **Install Linux Agent** (on target Linux systems):
   ```bash
   cd linux-agent
   sudo ./install.sh
   ```

3. **Install Windows Agent** (on target Windows systems):
   - Right-click `install.bat`, select "Run as administrator"

4. **Install DPI Probe** (optional, for network monitoring):
   ```bash
   cd dpi-probe
   sudo ./install.sh
   ```

### Component-Specific Instructions:

See individual component README files for detailed installation instructions:
- `core/README.md` - Core installation guide
- `linux-agent/README.md` - Linux Agent installation guide
- `windows-agent/README.md` - Windows Agent installation guide
- `dpi-probe/README.md` - DPI Probe installation guide

## Uninstallation

Each component includes an uninstaller:

```bash
# Core
cd core
sudo ./uninstall.sh

# Linux Agent
cd linux-agent
sudo ./uninstall.sh

# Windows Agent
cd windows-agent
# Right-click uninstall.bat, select "Run as administrator"

# DPI Probe
cd dpi-probe
sudo ./uninstall.sh
```

## Troubleshooting

### Validation Script Fails

**Issue**: `validate-release.sh` reports checksum mismatches

**Solution**:
- Ensure release bundle is not corrupted (re-download if needed)
- Verify filesystem integrity: `fsck` on Linux, `chkdsk` on Windows
- Check for file modifications: `git status` (if using git)
- Re-run validation: `./validate-release.sh`

### Installation Fails

**Issue**: Component installer fails during installation

**Solution**:
- Check component-specific README for prerequisites
- Verify all prerequisites are installed (PostgreSQL, Python, Rust, etc.)
- Check error messages for specific issues
- Review installer logs: `sudo journalctl -u <service-name>`

### Component Fails to Start

**Issue**: Component service fails to start after installation

**Solution**:
- Check service status: `sudo systemctl status <service-name>`
- Review service logs: `sudo journalctl -u <service-name> -f`
- Verify environment configuration: `cat <component>/config/environment`
- Check prerequisites: PostgreSQL running, network connectivity, etc.

## Support

For technical support, issues, or questions:

1. **Review Component READMEs**: Each component includes detailed documentation
2. **Check Audit Artifacts**: Review `audit/build-info.json` and `audit/component-manifest.json` for component details
3. **Validate Release Bundle**: Run `./validate-release.sh` to verify integrity
4. **Review Installation Logs**: Check system logs for detailed error messages

**Note**: Production support channels should be established separately. This release bundle is a technical artifact.

## License

RansomEye v1.0 - Enterprise & Military-Grade Build

---

**Release Information**:
- **Version**: 1.0.0
- **Build Timestamp**: See `audit/build-info.json`
- **Git Commit**: See `audit/build-info.json`
- **Integrity Method**: SHA256 checksums
- **Signature Method**: GPG (placeholder - requires signing key)

**AUTHORITATIVE**: This release bundle is the single authoritative entry point for RansomEye v1.0 installation and deployment.
