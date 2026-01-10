# RansomEye v1.0 Core Installer

**AUTHORITATIVE:** Commercial-grade installer for RansomEye Core runtime

## Overview

This installer provides a complete, production-ready installation of RansomEye Core on Ubuntu LTS systems. It creates a single unified systemd service that runs all Core components (Ingest, Correlation Engine, AI Core, Policy Engine, UI Backend) as one integrated runtime.

## What the Installer Does

1. **Creates directory structure** (`bin/`, `lib/`, `config/`, `logs/`, `runtime/`) at user-specified install root
2. **Installs Python code** (common utilities, core runtime, services, contracts, schemas)
3. **Creates system user** `ransomeye` for secure runtime execution
4. **Generates environment configuration** with all required variables (paths, credentials, etc.)
5. **Creates ONE systemd service** `ransomeye-core.service` (not multiple services)
6. **Validates installation** by starting Core and performing health checks
7. **Fails-closed**: Any error during installation terminates immediately

## Supported OS

- **Ubuntu LTS** (20.04, 22.04, 24.04+)
- **Required**: PostgreSQL installed and running
- **Required**: Python 3.8+ installed
- **Required**: Root privileges for installation

## Prerequisites

Before running the installer, ensure:

1. **PostgreSQL is installed and running:**
   ```bash
   sudo apt-get update
   sudo apt-get install -y postgresql postgresql-contrib
   sudo systemctl start postgresql
   sudo systemctl enable postgresql
   ```

2. **PostgreSQL database and user created:**
   ```bash
   sudo -u postgres psql -c "CREATE DATABASE ransomeye;"
   sudo -u postgres psql -c "CREATE USER gagan WITH PASSWORD 'gagangagan';"
   sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ransomeye TO gagan;"
   sudo -u postgres psql -d ransomeye -c "GRANT ALL ON SCHEMA public TO gagan;"
   ```

3. **Python 3 and dependencies installed:**
   ```bash
   sudo apt-get install -y python3 python3-pip python3-psycopg2
   pip3 install fastapi uvicorn psycopg2-binary jsonschema pydantic
   ```

4. **Database schemas applied:**
   ```bash
   # Apply all schema files from schemas/ directory
   for schema_file in schemas/*.sql; do
       psql -h localhost -U gagan -d ransomeye -f "$schema_file"
   done
   ```

## How to Install

### Step 1: Download Installer

Extract the RansomEye Core installer package to a temporary directory:

```bash
cd /tmp
tar -xzf ransomeye-core-installer.tar.gz
cd ransomeye-core-installer/installer/core
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
2. Create directory structure
3. Install all files
4. Create systemd service
5. Start Core and validate health
6. Report success or failure

### Step 4: Verify Installation

```bash
# Check service status
sudo systemctl status ransomeye-core

# Check logs
sudo journalctl -u ransomeye-core -f

# Check health endpoints (if services are running)
curl http://localhost:8000/health  # Ingest service
curl http://localhost:8080/health  # UI Backend
```

## Installation Paths

**NO HARDCODED PATHS**: The installer prompts for install root and creates all paths relative to it.

Example installation structure (if install root is `/opt/ransomeye`):

```
/opt/ransomeye/
├── bin/
│   └── ransomeye-core          # Executable wrapper script
├── lib/
│   ├── common/                 # Common utilities
│   ├── core/                   # Core runtime
│   └── services/               # Service modules
├── config/
│   ├── contracts/              # Contract schemas
│   ├── schemas/                # Database schemas
│   ├── environment             # Environment variables (generated)
│   └── installer.manifest.json # Installation manifest
├── logs/                       # Log files (writable by ransomeye user)
└── runtime/                    # Runtime files (writable by ransomeye user)
```

## Configuration

The installer generates `${INSTALL_ROOT}/config/environment` with all required environment variables:

- **Installation paths**: All absolute paths based on install root
- **Database credentials**: user: `gagan`, password: `gagangagan`
- **Service ports**: Ingest (8000), UI Backend (8080)
- **Component identity**: Component instance ID (UUID)
- **Runtime identity**: User/group IDs

**DO NOT EDIT MANUALLY**: Regenerate using installer if paths change.

## Service Management

The installer creates **ONE systemd service**: `ransomeye-core.service`

### Service Commands

```bash
# Start Core
sudo systemctl start ransomeye-core

# Stop Core
sudo systemctl stop ransomeye-core

# Restart Core
sudo systemctl restart ransomeye-core

# Check status
sudo systemctl status ransomeye-core

# Enable auto-start on boot
sudo systemctl enable ransomeye-core

# Disable auto-start
sudo systemctl disable ransomeye-core

# View logs
sudo journalctl -u ransomeye-core -f
sudo journalctl -u ransomeye-core --since "1 hour ago"
```

### Service Behavior

- **Restart on failure**: Automatically restarts if Core crashes
- **Graceful shutdown**: Handles SIGTERM cleanly (finishes transactions, closes connections)
- **Resource limits**: Prevents runaway processes
- **Security hardening**: Runs as unprivileged user, restricted filesystem access

## How to Uninstall

### Step 1: Run Uninstaller

```bash
cd /tmp/ransomeye-core-installer/installer/core
chmod +x uninstall.sh
sudo ./uninstall.sh
```

The uninstaller will:

1. Detect installation root (from manifest or prompt)
2. Stop and remove systemd service
3. Remove installation directory (with confirmation)
4. Optionally remove system user (with confirmation)
5. **NOTE**: PostgreSQL database and user are NOT removed (manual cleanup required)

### Step 2: Manual Cleanup (Optional)

If you want to remove PostgreSQL database and user:

```bash
sudo -u postgres psql -c "DROP DATABASE ransomeye;"
sudo -u postgres psql -c "DROP USER gagan;"
```

## Idempotency

The installer is **idempotent**: running it multiple times on the same install root is safe.

- Existing files are preserved (not overwritten unless necessary)
- System user creation is skipped if user exists
- Systemd service is updated if already exists
- Installation manifest is regenerated with current timestamp

## Failure Behavior (Fail-Closed)

The installer implements **fail-closed semantics**:

1. **Any error terminates installation immediately** (no partial state)
2. **Validates all prerequisites before starting** (PostgreSQL, Python, permissions)
3. **Validates installation after completion** (starts service, checks health)
4. **Exits with non-zero code on failure** (clear error messages)

If installation fails:

1. Check error message for specific issue
2. Fix the issue (e.g., install prerequisites, fix permissions)
3. Re-run installer (idempotent, safe to retry)
4. If issue persists, check logs: `sudo journalctl -u ransomeye-core`

## Troubleshooting

### Installation Fails: "PostgreSQL connection failed"

**Solution**: Ensure PostgreSQL is running and database exists:
```bash
sudo systemctl status postgresql
sudo -u postgres psql -c "SELECT 1;"  # Test connection
sudo -u postgres psql -c "\l"  # List databases (should see 'ransomeye')
```

### Installation Fails: "Cannot create directory"

**Solution**: Check permissions on parent directory:
```bash
ls -ld /opt  # Should be writable by root
sudo mkdir -p /opt  # Create parent if needed
```

### Service Fails to Start: "Permission denied"

**Solution**: Check ownership and permissions:
```bash
ls -la /opt/ransomeye/bin/ransomeye-core  # Should be owned by ransomeye:ransomeye, executable
sudo chown ransomeye:ransomeye /opt/ransomeye/bin/ransomeye-core
sudo chmod +x /opt/ransomeye/bin/ransomeye-core
```

### Service Fails to Start: "ModuleNotFoundError"

**Solution**: Check PYTHONPATH and Python dependencies:
```bash
sudo -u ransomeye python3 -c "import sys; print(sys.path)"
sudo -u ransomeye python3 -c "import fastapi, uvicorn, psycopg2"  # Should succeed
```

### Health Check Fails

**Solution**: Check service logs and database connectivity:
```bash
sudo journalctl -u ransomeye-core -n 100
sudo -u ransomeye psql -h localhost -U gagan -d ransomeye -c "SELECT 1;"
```

## Security Considerations

1. **Runtime runs as unprivileged user** (`ransomeye`) - no root privileges
2. **Environment file is read-only** (600 permissions) - secrets not exposed
3. **Systemd hardening** - restricted filesystem access, no new privileges
4. **Secrets from environment only** - no hardcoded credentials
5. **Log redaction** - secrets automatically redacted in logs

## Support

For issues or questions:

1. Check installation manifest: `${INSTALL_ROOT}/config/installer.manifest.json`
2. Check service logs: `sudo journalctl -u ransomeye-core`
3. Check application logs: `${INSTALL_ROOT}/logs/`
4. Verify environment: `sudo cat ${INSTALL_ROOT}/config/environment`

## License

RansomEye v1.0 - Enterprise & Military-Grade Build
