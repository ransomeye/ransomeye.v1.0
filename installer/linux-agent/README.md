# RansomEye v1.0 Linux Agent Installer

**AUTHORITATIVE:** Production-grade installer for standalone RansomEye Linux Agent

## Overview

This installer provides a complete, production-ready installation of RansomEye Linux Agent on Ubuntu LTS systems. The Linux Agent is a **standalone component** that can be installed and run independently of Core. It emits real events to Core's Ingest service when Core is available, and fails gracefully (no crash-loops) when Core is unreachable.

## Standalone Nature of Linux Agent

**CRITICAL**: Linux Agent is **standalone** and does NOT require Core to be installed:

- ✅ **Can be installed without Core**: Agent can be installed on systems where Core is not present
- ✅ **Graceful failure**: Agent fails cleanly if Core is unreachable (no crashes, no infinite loops)
- ✅ **No Core dependencies**: Agent has no dependencies on Core installation
- ✅ **Configurable endpoint**: Core endpoint is configurable via environment variable (default: `http://localhost:8000/events`)
- ✅ **Crash-loop prevention**: Systemd service configured to prevent crash-loops if Core is down (max 5 restarts in 5 minutes)

## What the Installer Does

1. **Creates directory structure** (`bin/`, `config/`, `logs/`, `runtime/`) at user-specified install root
2. **Builds Linux Agent binary** from Rust source code (requires Rust toolchain)
3. **Installs agent binary** to `bin/` directory
4. **Creates system user** `ransomeye-agent` for secure runtime execution
5. **Generates environment configuration** with all required variables (component instance ID, Core endpoint, etc.)
6. **Creates ONE systemd service** `ransomeye-linux-agent.service` (not multiple services)
7. **Validates installation** by starting agent and verifying process execution
8. **Fails-closed**: Any error during installation terminates immediately

## Supported OS

- **Ubuntu LTS** (20.04, 22.04, 24.04+)
- **Required**: Rust toolchain installed (cargo)
- **Required**: Root privileges for installation
- **NOT Required**: Core installation (agent works standalone)

## Prerequisites

Before running the installer, ensure:

1. **Rust toolchain is installed:**
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   source $HOME/.cargo/env
   cargo --version  # Verify installation
   ```

2. **Core installation (optional):**
   - Linux Agent can be installed without Core
   - If Core is installed, provide Core Ingest URL during installation
   - If Core is not installed, agent will fail gracefully when trying to transmit events

## How to Install

### Step 1: Download Installer

Extract the RansomEye Linux Agent installer package to a temporary directory:

```bash
cd /tmp
tar -xzf ransomeye-linux-agent-installer.tar.gz
cd ransomeye-linux-agent-installer/installer/linux-agent
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

1. Prompt for installation root directory (e.g., `/opt/ransomeye-agent`)
2. Check for Rust toolchain (build agent binary from source)
3. Build Linux Agent binary
4. Create directory structure
5. Install binary and files
6. Create systemd service
7. Prompt for Core endpoint (optional, defaults to `http://localhost:8000/events`)
8. Generate environment file
9. Start agent and validate installation

### Step 4: Verify Installation

```bash
# Check service status
sudo systemctl status ransomeye-linux-agent

# Check logs
sudo journalctl -u ransomeye-linux-agent -f

# Check if agent executed (agent is one-shot, exits after event transmission)
sudo journalctl -u ransomeye-linux-agent --no-pager | grep "STARTUP: Linux Agent starting"
```

## Installation Paths

**NO HARDCODED PATHS**: The installer prompts for install root and creates all paths relative to it.

Example installation structure (if install root is `/opt/ransomeye-agent`):

```
/opt/ransomeye-agent/
├── bin/
│   └── ransomeye-linux-agent          # Agent binary (executable)
├── config/
│   ├── environment                     # Environment variables (generated)
│   └── installer.manifest.json         # Installation manifest
├── logs/                               # Log files (writable by ransomeye-agent user)
└── runtime/                            # Runtime files (writable by ransomeye-agent user)
```

## Configuration

The installer generates `${INSTALL_ROOT}/config/environment` with all required environment variables:

- **Installation paths**: All absolute paths based on install root
- **Agent identity**: Component instance ID (UUID), version
- **Core endpoint**: Ingest service URL (configurable, defaults to `http://localhost:8000/events`)
- **Database credentials**: Provided via environment variables if needed (no defaults)
- **Runtime identity**: User/group IDs

**DO NOT EDIT MANUALLY**: Regenerate using installer if paths change.

### Environment Variables Required by Agent

- `RANSOMEYE_COMPONENT_INSTANCE_ID` (required): Unique UUID for this agent instance
- `RANSOMEYE_VERSION` (required): Agent version string
- `RANSOMEYE_INGEST_URL` (optional): Core Ingest service URL (default: `http://localhost:8000/events`)

## Service Management

The installer creates **ONE systemd service**: `ransomeye-linux-agent.service`

### Service Commands

```bash
# Start agent (one-shot: runs once and exits)
sudo systemctl start ransomeye-linux-agent

# Stop agent (if still running)
sudo systemctl stop ransomeye-linux-agent

# Check status
sudo systemctl status ransomeye-linux-agent

# Restart agent (triggers new event transmission)
sudo systemctl restart ransomeye-linux-agent

# Enable auto-start on boot (optional)
sudo systemctl enable ransomeye-linux-agent

# Disable auto-start
sudo systemctl disable ransomeye-linux-agent

# View logs
sudo journalctl -u ransomeye-linux-agent -f
sudo journalctl -u ransomeye-linux-agent --since "1 hour ago"
```

### Service Behavior

- **Agent is one-shot**: Runs once, transmits event, exits (exit code 0 on success)
- **Restart on failure**: Automatically restarts if agent crashes (exit code non-zero)
- **Crash-loop prevention**: After 5 failed attempts in 5 minutes, systemd stops restarting (prevents crash-loop if Core is down)
- **Graceful shutdown**: Handles SIGTERM cleanly (agent exits immediately on signal)
- **Resource limits**: Prevents runaway processes
- **Security hardening**: Runs as unprivileged user, restricted filesystem access

### Behavior When Core is Unreachable

**CRITICAL**: Linux Agent handles Core unavailability gracefully:

1. **Agent runs**: Agent starts successfully and constructs event envelope
2. **Transmission attempt**: Agent attempts to transmit event to Core Ingest service
3. **Graceful failure**: If Core is unreachable (connection refused, timeout, etc.):
   - Agent logs error message
   - Agent exits with code 3 (RuntimeError)
   - Systemd restarts agent after 60 seconds (RestartSec=60)
   - After 5 failed attempts in 5 minutes, systemd stops restarting (prevents crash-loop)
4. **No crashes**: Agent does not crash or hang when Core is unreachable
5. **Clean exit**: Agent always exits cleanly with appropriate exit code

**Exit Codes**:
- `0` (Success): Event transmitted successfully
- `1` (ConfigError): Missing or invalid configuration
- `2` (StartupError): Startup failure (e.g., cannot create HTTP client)
- `3` (RuntimeError): Transmission failure (Core unreachable or HTTP error)
- `4` (FatalError): Fatal error (unexpected failure)

## How to Uninstall

### Step 1: Run Uninstaller

```bash
cd /tmp/ransomeye-linux-agent-installer/installer/linux-agent
chmod +x uninstall.sh
sudo ./uninstall.sh
```

The uninstaller will:

1. Detect installation root (from manifest or prompt)
2. Stop and remove systemd service
3. Remove installation directory (with confirmation)
4. Optionally remove system user (with confirmation)

### Step 2: Manual Cleanup (Optional)

If you want to remove system user manually:

```bash
sudo userdel ransomeye-agent
```

## Idempotency

The installer is **idempotent**: running it multiple times on the same install root is safe.

- Existing files are preserved (not overwritten unless necessary)
- System user creation is skipped if user exists
- Systemd service is updated if already exists
- Installation manifest is regenerated with current timestamp
- Agent binary is rebuilt if source has changed

## Failure Behavior (Fail-Closed)

The installer implements **fail-closed semantics**:

1. **Any error terminates installation immediately** (no partial state)
2. **Validates all prerequisites before starting** (Rust, permissions, etc.)
3. **Validates installation after completion** (starts service, checks process)
4. **Exits with non-zero code on failure** (clear error messages)

If installation fails:

1. Check error message for specific issue
2. Fix the issue (e.g., install Rust, fix permissions)
3. Re-run installer (idempotent, safe to retry)
4. If issue persists, check logs: `sudo journalctl -u ransomeye-linux-agent`

## Troubleshooting

### Installation Fails: "Rust toolchain (cargo) not found"

**Solution**: Install Rust toolchain:
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
cargo --version
```

### Installation Fails: "Cannot create directory"

**Solution**: Check permissions on parent directory:
```bash
ls -ld /opt  # Should be writable by root
sudo mkdir -p /opt  # Create parent if needed
```

### Agent Fails to Start: "Permission denied"

**Solution**: Check ownership and permissions:
```bash
ls -la /opt/ransomeye-agent/bin/ransomeye-linux-agent  # Should be owned by ransomeye-agent:ransomeye-agent, executable
sudo chown ransomeye-agent:ransomeye-agent /opt/ransomeye-agent/bin/ransomeye-linux-agent
sudo chmod +x /opt/ransomeye-agent/bin/ransomeye-linux-agent
```

### Agent Exits with Code 3 (RuntimeError)

**This is expected behavior** when Core is unreachable:
- Agent attempts to transmit event to Core
- Core is not available (not installed, not running, network issue, etc.)
- Agent exits with code 3 (RuntimeError) - this is correct behavior
- Systemd will restart agent (with restart limits to prevent crash-loop)

**Solution**: 
- Verify Core is installed and running (if Core should be available)
- Check Core Ingest URL in environment file: `cat /opt/ransomeye-agent/config/environment | grep RANSOMEYE_INGEST_URL`
- Check network connectivity: `curl http://localhost:8000/health` (if Core is installed)
- If Core is intentionally not installed, this behavior is correct (agent fails gracefully)

### Service Crash-Loops

**This should not happen** due to systemd restart limits:
- Service is configured with `StartLimitBurstSec=5` and `StartLimitIntervalSec=300`
- After 5 failed attempts in 5 minutes, systemd stops restarting
- Check logs: `sudo journalctl -u ransomeye-linux-agent --no-pager | tail -50`

**If crash-loop persists**:
- Check agent logs for repeated errors
- Verify agent binary is not corrupted: `file /opt/ransomeye-agent/bin/ransomeye-linux-agent`
- Rebuild and reinstall agent

## Security Considerations

1. **Runtime runs as unprivileged user** (`ransomeye-agent`) - no root privileges
2. **Environment file is read-only** (600 permissions) - secrets not exposed
3. **Systemd hardening** - restricted filesystem access, no new privileges
4. **No local persistence** - agent does not store events locally
5. **No retries** - agent fails immediately on transmission failure (fail-closed)

## Support

For issues or questions:

1. Check installation manifest: `${INSTALL_ROOT}/config/installer.manifest.json`
2. Check service logs: `sudo journalctl -u ransomeye-linux-agent`
3. Check application logs: `${INSTALL_ROOT}/logs/`
4. Verify environment: `sudo cat ${INSTALL_ROOT}/config/environment`
5. Verify Core endpoint: `curl ${RANSOMEYE_INGEST_URL}/health` (if Core is installed)

## License

RansomEye v1.0 - Enterprise & Military-Grade Build
