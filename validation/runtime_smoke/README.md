# Phase 8.1 Runtime Smoke Validation

## Overview

Runtime smoke validation performs offline checks on core RansomEye components before service startup. This validation ensures that critical system components can be imported, configured, and initialized without errors.

**Phase 8.1 Requirement**: Run fully offline (no network calls), exit 0 only if ALL checks pass, else exit 1.

## How to Run

### Basic Usage

```bash
cd /path/to/rebuild
python3 validation/runtime_smoke/runtime_smoke_check.py
```

### Environment Variables

The script uses the following environment variables for database connection (with deterministic defaults for testing):

- `RANSOMEYE_DB_USER` (default: `gagan`)
- `RANSOMEYE_DB_PASSWORD` (default: `gagan`)
- `RANSOMEYE_DB_HOST` (default: `localhost`)
- `RANSOMEYE_DB_PORT` (default: `5432`)
- `RANSOMEYE_DB_NAME` (default: `ransomeye`)
- `RANSOMEYE_INSTALL_ROOT` (default: `/opt/ransomeye`) - Used to locate installer manifest

**Note**: The default credentials (`gagan`/`gagan`) are for POC/testing environments only. Production deployments should override these via environment variables.

### Exit Codes

- `0`: All checks passed
- `1`: One or more checks failed

## Checks Performed

The script performs four mandatory checks:

### 1. Core Service Binary/Module Import

**Check**: `core_service_import`

Verifies that core runtime modules can be imported:
- Imports `core.runtime` and `core.main`
- Verifies key functions exist (`run_core`)
- Ensures modules are properly structured

**Failure**: If core modules cannot be imported or are malformed.

### 2. Database Connection Bootstrap

**Check**: `database_connection`

Verifies database connectivity using deterministic test configuration:
- Connects to PostgreSQL using test DB config
- Executes a simple query (`SELECT 1`)
- Validates connection is functional

**Failure**: If database connection fails (connection refused, authentication failure, query error).

### 3. Config Manifest Loads and Validates Schema

**Check**: `config_manifest`

Verifies configuration loading and manifest validation:
- Tests `ConfigLoader` from `common.config`
- Loads configuration (using optional vars to avoid hard failures)
- If manifest file exists, validates against JSON schema
- Validates manifest structure matches expected schema

**Failure**: If config loader fails, manifest is invalid JSON, or manifest does not match schema.

**Note**: Schema validation requires `jsonschema` package. If not available, config loading is still validated but schema validation is skipped.

### 4. Agent Registry Initializes Without Error

**Check**: `agent_registry`

Verifies agent classes can be imported and initialized:
- Imports `LinuxAgent` from `agents.linux.agent_main`
- Imports `WindowsAgent` from `agents.windows.agent.agent_main`
- Verifies at least one agent class is importable
- Validates agent class structure (has `__init__` method)

**Failure**: If no agent classes can be imported or agent structure is invalid.

## Expected Output

### Console Output (stderr)

The script writes human-readable output to stderr:

```
RansomEye v1.0 Phase 8.1 Runtime Smoke Validation
============================================================
All checks PASSED

Check Summary:
  ✓ core_service_import: PASS
    Core service modules imported successfully
  ✓ database_connection: PASS
    Database connection successful (host=localhost, port=5432, db=ransomeye, user=gagan)
  ✓ config_manifest: PASS
    Config loader works (manifest not found at /opt/ransomeye/config/installer.manifest.json, schema at /path/to/rebuild/installer/install.manifest.schema.json)
  ✓ agent_registry: PASS
    Agent registry initialized successfully (agents: LinuxAgent, WindowsAgent)

Results written to: /path/to/rebuild/validation/runtime_smoke/runtime_smoke_result.json
```

### JSON Output (machine-readable)

Results are written to `runtime_smoke_result.json` in the same directory:

```json
{
  "timestamp": "2024-01-15T10:30:45.123456+00:00",
  "checks": [
    {
      "name": "core_service_import",
      "status": "PASS",
      "message": "Core service modules imported successfully",
      "error": ""
    },
    {
      "name": "database_connection",
      "status": "PASS",
      "message": "Database connection successful (host=localhost, port=5432, db=ransomeye, user=gagan)",
      "error": ""
    },
    {
      "name": "config_manifest",
      "status": "PASS",
      "message": "Config loader works (manifest not found at /opt/ransomeye/config/installer.manifest.json, schema at /path/to/rebuild/installer/install.manifest.schema.json)",
      "error": ""
    },
    {
      "name": "agent_registry",
      "status": "PASS",
      "message": "Agent registry initialized successfully (agents: LinuxAgent, WindowsAgent)",
      "error": ""
    }
  ],
  "overall_status": "PASS"
}
```

## Failure Semantics

### Overall Status

- **PASS**: All four checks passed
- **FAIL**: One or more checks failed

### Individual Check Status

Each check has:
- **status**: `PASS` or `FAIL`
- **message**: Human-readable description of the result
- **error**: Error message (if status is `FAIL`)

### Exit Behavior

- Script exits with code `0` if `overall_status` is `PASS`
- Script exits with code `1` if `overall_status` is `FAIL`
- JSON output is always written, regardless of pass/fail status

### Common Failure Scenarios

1. **Database Connection Failure**
   - Database server not running
   - Wrong credentials
   - Network unreachable
   - Database does not exist

2. **Core Module Import Failure**
   - Missing dependencies
   - Python path issues
   - Corrupted module files

3. **Config Manifest Failure**
   - Invalid JSON in manifest file
   - Manifest does not match schema
   - Missing required fields

4. **Agent Registry Failure**
   - Agent modules not available
   - Import errors in agent code
   - Missing dependencies for agents

## Dependencies

### Required

- Python 3.10+
- `psycopg2` (for database connection)
- Core RansomEye modules (must be in Python path)

### Optional

- `jsonschema` (for manifest schema validation; if not available, schema validation is skipped but config loading is still validated)

## Offline Operation

This script is designed to run **fully offline** (no network calls):

- Database connection uses localhost by default (no external network)
- All imports are from local filesystem
- No HTTP/HTTPS requests
- No external API calls

## Integration

This script is intended for:

- Pre-startup validation
- CI/CD pipeline integration (deterministic checks)
- Local development validation
- Installation verification

**Note**: This script does NOT modify CI workflows. It is a standalone validation tool.

## Troubleshooting

### Database Connection Issues

If database connection fails:

1. Verify PostgreSQL is running: `systemctl status postgresql`
2. Check credentials: Ensure `RANSOMEYE_DB_USER` and `RANSOMEYE_DB_PASSWORD` are correct
3. Verify database exists: `psql -U <user> -d <database> -c "SELECT 1"`

### Import Errors

If module imports fail:

1. Verify Python path includes project root
2. Check that all required modules are present
3. Verify Python version is 3.10+

### Manifest Validation Issues

If manifest validation fails:

1. Verify manifest file exists at expected path
2. Check manifest is valid JSON: `python3 -m json.tool <manifest_file>`
3. Verify schema file exists: `installer/install.manifest.schema.json`
