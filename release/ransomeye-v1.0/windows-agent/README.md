# RansomEye v1.0 Windows Agent Installer

**AUTHORITATIVE:** Production-grade installer for standalone RansomEye Windows Agent

## Overview

This installer provides a complete, production-ready installation of RansomEye Windows Agent on Windows Server / Windows 10+ systems. The Windows Agent is a **standalone component** that can be installed and run independently of Core. It emits real events to Core's Ingest service when Core is available, and fails gracefully (no crash-loops) when Core is unreachable.

## Standalone Nature of Windows Agent

**CRITICAL**: Windows Agent is **standalone** and does NOT require Core to be installed:

- ✅ **Can be installed without Core**: Agent can be installed on systems where Core is not present
- ✅ **Graceful failure**: Agent fails cleanly if Core is unreachable (no crashes, no infinite loops)
- ✅ **No Core dependencies**: Agent has no dependencies on Core installation
- ✅ **Configurable endpoint**: Core endpoint is configurable via environment variable (default: `http://localhost:8000/events`)
- ✅ **Crash-loop prevention**: Windows Service configured to prevent crash-loops if Core is down (max 5 restarts in 5 minutes)

## What the Installer Does

1. **Creates directory structure** (`bin\`, `config\`, `logs\`, `runtime\`) at user-specified install directory
2. **Installs Windows Agent binary** (.exe file) to `bin\` directory
3. **Creates Windows service user** `ransomeye-agent` for secure runtime execution
4. **Generates configuration file** (`environment.txt`) with all required variables (component instance ID, Core endpoint, etc.)
5. **Creates wrapper script** that reads environment file and runs agent with proper environment
6. **Creates ONE Windows Service** `RansomEyeWindowsAgent` (not multiple services)
7. **Validates installation** by starting service and verifying service is running
8. **Fails-closed**: Any error during installation terminates immediately

## Supported Windows Versions

- **Windows Server** 2016, 2019, 2022+
- **Windows 10** / **Windows 11** (Enterprise, Pro)
- **Required**: Administrator privileges for installation
- **Required**: Windows Agent binary (.exe file) must be built and available
- **NOT Required**: Core installation (agent works standalone)

## Prerequisites

Before running the installer, ensure:

1. **Windows Agent binary is built:**
   - Build Windows Agent from Rust source: `cargo build --release --target x86_64-pc-windows-msvc`
   - Binary should be located at: `services\windows-agent\target\release\ransomeye-windows-agent.exe`
   - Alternatively, provide path to pre-built binary when prompted

2. **Administrator privileges:**
   - Installer must be run as Administrator
   - Right-click `install.bat` and select "Run as administrator"

3. **Core installation (optional):**
   - Windows Agent can be installed without Core
   - If Core is installed, provide Core Ingest URL during installation
   - If Core is not installed, agent will fail gracefully when trying to transmit events

## How to Install

### Step 1: Download Installer

Extract the RansomEye Windows Agent installer package to a temporary directory:

```
C:\Temp
├── ransomeye-windows-agent-installer\
    └── installer\
        └── windows-agent\
            ├── install.bat
            ├── uninstall.bat
            ├── ransomeye-windows-agent.service.txt
            ├── installer.manifest.json
            └── README.md
```

### Step 2: Build Windows Agent Binary (if not already built)

If you need to build the agent:

```cmd
cd services\windows-agent
cargo build --release --target x86_64-pc-windows-msvc
```

The binary will be at: `target\x86_64-pc-windows-msvc\release\ransomeye-windows-agent.exe`

### Step 3: Run Installer as Administrator

1. **Right-click** `install.bat`
2. Select **"Run as administrator"**
3. Follow prompts:
   - Enter installation directory (e.g., `C:\RansomEye\Agent`)
   - Provide path to agent binary (if not found automatically)
   - Enter Core Ingest URL (optional, defaults to `http://localhost:8000/events`)

The installer will:

1. Prompt for installation directory (no hardcoded paths)
2. Check for Windows Agent binary
3. Create directory structure
4. Install binary and files
5. Create Windows service user
6. Generate configuration file
7. Create wrapper script
8. Install Windows Service
9. Configure service recovery (restart on failure with crash-loop prevention)
10. Start service and validate installation

### Step 4: Verify Installation

```cmd
REM Check service status
sc query RansomEyeWindowsAgent

REM Check service configuration
sc qc RansomEyeWindowsAgent

REM Check Event Viewer for agent logs
eventvwr.msc
REM Navigate to: Windows Logs / Application
REM Filter for: "RansomEyeWindowsAgent" or "ransomeye"
```

## Installation Paths

**NO HARDCODED PATHS**: The installer prompts for install directory and creates all paths relative to it.

Example installation structure (if install directory is `C:\RansomEye\Agent`):

```
C:\RansomEye\Agent\
├── bin\
│   ├── ransomeye-windows-agent.exe              # Agent binary (executable)
│   └── ransomeye-windows-agent-wrapper.bat      # Wrapper script (reads environment and runs agent)
├── config\
│   ├── environment.txt                          # Environment variables (generated)
│   └── installer.manifest.json                  # Installation manifest
├── logs\                                        # Log files (writable by ransomeye-agent user)
└── runtime\                                     # Runtime files (writable by ransomeye-agent user)
```

## Configuration

The installer generates `${INSTALL_ROOT}\config\environment.txt` with all required environment variables:

- **Installation paths**: All absolute paths based on install directory
- **Agent identity**: Component instance ID (UUID), version
- **Core endpoint**: Ingest service URL (configurable, defaults to `http://localhost:8000/events`)
- **Database credentials**: username: `gagan`, password: `gagan` (for future use, if needed)
- **Runtime identity**: Service user name

**DO NOT EDIT MANUALLY**: Regenerate using installer if paths change.

### Environment Variables Required by Agent

- `RANSOMEYE_COMPONENT_INSTANCE_ID` (required): Unique UUID for this agent instance
- `RANSOMEYE_VERSION` (required): Agent version string
- `RANSOMEYE_INGEST_URL` (optional): Core Ingest service URL (default: `http://localhost:8000/events`)

## Service Management

The installer creates **ONE Windows Service**: `RansomEyeWindowsAgent`

### Service Commands

```cmd
REM Start service
sc start RansomEyeWindowsAgent

REM Stop service
sc stop RansomEyeWindowsAgent

REM Query service status
sc query RansomEyeWindowsAgent

REM Query service configuration
sc qc RansomEyeWindowsAgent

REM Query service type
sc querytype RansomEyeWindowsAgent

REM Configure service recovery (if needed)
sc failure RansomEyeWindowsAgent reset= 300 actions= restart/60000/restart/120000/restart/300000

REM Delete service (before uninstall)
sc delete RansomEyeWindowsAgent
```

### Service Behavior

- **Agent is one-shot**: Runs once, transmits event, exits (exit code 0 on success)
- **Auto-restart on failure**: Automatically restarts if agent crashes (exit code non-zero)
- **Crash-loop prevention**: After 5 failed attempts in 5 minutes, service stops restarting (prevents crash-loop if Core is down)
- **Graceful shutdown**: Handles service stop signal cleanly (agent exits immediately on signal)
- **Resource limits**: Prevents runaway processes
- **Security hardening**: Runs as unprivileged service user, minimal filesystem access

### Behavior When Core is Unreachable

**CRITICAL**: Windows Agent handles Core unavailability gracefully:

1. **Agent runs**: Agent starts successfully and constructs event envelope
2. **Transmission attempt**: Agent attempts to transmit event to Core Ingest service
3. **Graceful failure**: If Core is unreachable (connection refused, timeout, etc.):
   - Agent logs error message to Event Viewer
   - Agent exits with code 3 (RuntimeError)
   - Windows Service restarts agent after 60 seconds (configured recovery action)
   - After 5 failed attempts in 5 minutes, service stops restarting (prevents crash-loop)
4. **No crashes**: Agent does not crash or hang when Core is unreachable
5. **Clean exit**: Agent always exits cleanly with appropriate exit code

**Exit Codes**:
- `0` (Success): Event transmitted successfully
- `1` (ConfigError): Missing or invalid configuration
- `2` (StartupError): Startup failure (e.g., cannot create HTTP client)
- `3` (RuntimeError): Transmission failure (Core unreachable or HTTP error)
- `4` (FatalError): Fatal error (unexpected failure)

## How to Uninstall

### Step 1: Run Uninstaller as Administrator

1. **Right-click** `uninstall.bat`
2. Select **"Run as administrator"**
3. Follow prompts:
   - Uninstaller will detect installation directory (from manifest or prompt)
   - Confirm removal of installation directory
   - Optionally confirm removal of Windows service user

The uninstaller will:

1. Detect installation directory (from manifest or prompt)
2. Stop and remove Windows Service
3. Remove installation directory (with confirmation)
4. Optionally remove Windows service user (with confirmation)

### Step 2: Manual Cleanup (Optional)

If needed, manually remove service or user:

```cmd
REM Remove service
sc delete RansomEyeWindowsAgent

REM Remove user
net user ransomeye-agent /delete
```

## Idempotency

The installer is **idempotent**: running it multiple times on the same install directory is safe.

- Existing files are preserved (not overwritten unless necessary)
- Windows service user creation is skipped if user exists
- Windows Service is updated if already exists (stopped, removed, recreated)
- Installation manifest is regenerated with current timestamp
- Agent binary is copied over if updated

## Failure Behavior (Fail-Closed)

The installer implements **fail-closed semantics**:

1. **Any error terminates installation immediately** (no partial state)
2. **Validates all prerequisites before starting** (Administrator privileges, binary availability, permissions)
3. **Validates installation after completion** (starts service, checks service status)
4. **Exits with non-zero code on failure** (clear error messages)

If installation fails:

1. Check error message for specific issue
2. Fix the issue (e.g., run as Administrator, provide correct binary path)
3. Re-run installer (idempotent, safe to retry)
4. If issue persists, check Event Viewer: `eventvwr.msc` → Windows Logs → Application

## Troubleshooting

### Installation Fails: "Installer must be run as Administrator"

**Solution**: Right-click `install.bat` and select "Run as administrator"

### Installation Fails: "Agent binary not found"

**Solution**: 
- Build agent first: `cd services\windows-agent && cargo build --release --target x86_64-pc-windows-msvc`
- Or provide path to pre-built binary when prompted

### Installation Fails: "Failed to create user 'ransomeye-agent'"

**Solution**: 
- Check if user already exists: `net user ransomeye-agent`
- If exists, installer will use existing user (safe)
- If creation fails, check Group Policy restrictions on user creation

### Service Fails to Start: "Service could not be started"

**Solution**: 
- Check Event Viewer for detailed error: `eventvwr.msc` → Windows Logs → Application
- Verify agent binary is executable: `dir "C:\RansomEye\Agent\bin\ransomeye-windows-agent.exe"`
- Check environment file exists: `dir "C:\RansomEye\Agent\config\environment.txt"`
- Verify wrapper script is correct: `type "C:\RansomEye\Agent\bin\ransomeye-windows-agent-wrapper.bat"`

### Agent Exits with Code 3 (RuntimeError)

**This is expected behavior** when Core is unreachable:
- Agent attempts to transmit event to Core
- Core is not available (not installed, not running, network issue, etc.)
- Agent exits with code 3 (RuntimeError) - this is correct behavior
- Windows Service will restart agent (with restart limits to prevent crash-loop)

**Solution**: 
- Verify Core is installed and running (if Core should be available)
- Check Core Ingest URL in environment file: `type "C:\RansomEye\Agent\config\environment.txt" | findstr RANSOMEYE_INGEST_URL`
- Check network connectivity: `curl http://localhost:8000/health` (if Core is installed)
- If Core is intentionally not installed, this behavior is correct (agent fails gracefully)

### Service Crash-Loops

**This should not happen** due to service recovery limits:
- Service is configured with `sc failure` to limit restarts
- After 5 failed attempts in 5 minutes, service stops restarting
- Check Event Viewer: `eventvwr.msc` → Windows Logs → Application → Filter for "RansomEyeWindowsAgent"

**If crash-loop persists**:
- Check agent logs in Event Viewer for repeated errors
- Verify agent binary is not corrupted: `dir "C:\RansomEye\Agent\bin\ransomeye-windows-agent.exe"`
- Rebuild and reinstall agent
- Manually stop service: `sc stop RansomEyeWindowsAgent`
- Check service recovery configuration: `sc qfailure RansomEyeWindowsAgent`

## Security Considerations

1. **Runtime runs as unprivileged service user** (`ransomeye-agent`) - no Administrator privileges
2. **Configuration file permissions**: Environment file readable only by service user
3. **Minimal filesystem access**: Service user has read/execute on `bin\`, read on `config\`, full control on `logs\` and `runtime\` only
4. **No local persistence**: Agent does not store events locally
5. **No retries**: Agent fails immediately on transmission failure (fail-closed)

## Support

For issues or questions:

1. Check installation manifest: `${INSTALL_ROOT}\config\installer.manifest.json`
2. Check Event Viewer: `eventvwr.msc` → Windows Logs → Application (filter for "RansomEyeWindowsAgent")
3. Check application logs: `${INSTALL_ROOT}\logs\`
4. Verify environment: `type "${INSTALL_ROOT}\config\environment.txt"`
5. Verify Core endpoint: `curl ${RANSOMEYE_INGEST_URL}/health` (if Core is installed)
6. Check service status: `sc query RansomEyeWindowsAgent`
7. Check service configuration: `sc qc RansomEyeWindowsAgent`

## License

RansomEye v1.0 - Enterprise & Military-Grade Build
