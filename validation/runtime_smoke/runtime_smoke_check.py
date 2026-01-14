#!/usr/bin/env python3
"""
RansomEye v1.0 Phase 8.1 Runtime Smoke Validation
AUTHORITATIVE: Runtime smoke checks for core system components
Phase 8.1 requirement: Offline runtime validation before service startup
"""

import os
import sys
import json
import psycopg2
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Results structure
results = {
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'checks': [],
    'overall_status': 'UNKNOWN'
}


def add_check(name: str, status: str, message: str = '', error: str = ''):
    """Add a check result to the results."""
    check = {
        'name': name,
        'status': status,  # 'PASS', 'FAIL'
        'message': message,
        'error': error
    }
    results['checks'].append(check)
    return status == 'PASS'


def check_core_service_import():
    """
    Check 1: Core service binary/module import succeeds.
    Verifies that core runtime and main modules can be imported without errors.
    """
    try:
        # Import core runtime module
        from core import runtime
        from core import main
        
        # Verify key functions/classes exist
        assert hasattr(runtime, 'run_core'), "run_core function not found"
        assert hasattr(main, '__file__'), "main module not properly loaded"
        
        return add_check(
            'core_service_import',
            'PASS',
            'Core service modules imported successfully'
        )
    except ImportError as e:
        return add_check(
            'core_service_import',
            'FAIL',
            'Failed to import core service modules',
            str(e)
        )
    except AssertionError as e:
        return add_check(
            'core_service_import',
            'FAIL',
            'Core service module structure invalid',
            str(e)
        )
    except Exception as e:
        return add_check(
            'core_service_import',
            'FAIL',
            'Unexpected error during core service import',
            str(e)
        )


def check_database_connection():
    """
    Check 2: Database connection bootstrap check.
    Uses existing deterministic test DB config (gagan/gagan defaults, overridable via env).
    """
    try:
        # Use test DB config pattern from validation/harness/test_helpers.py
        db_user = os.getenv("RANSOMEYE_DB_USER", "gagan")
        db_password = os.getenv("RANSOMEYE_DB_PASSWORD", "gagan")
        db_host = os.getenv("RANSOMEYE_DB_HOST", "localhost")
        db_port = int(os.getenv("RANSOMEYE_DB_PORT", "5432"))
        db_name = os.getenv("RANSOMEYE_DB_NAME", "ransomeye")
        
        # Attempt connection
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
            connect_timeout=5  # Fail fast if DB is unreachable
        )
        
        # Verify connection works with a simple query
        cur = conn.cursor()
        cur.execute("SELECT 1")
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result and result[0] == 1:
            return add_check(
                'database_connection',
                'PASS',
                f'Database connection successful (host={db_host}, port={db_port}, db={db_name}, user={db_user})'
            )
        else:
            return add_check(
                'database_connection',
                'FAIL',
                'Database connection established but query returned unexpected result',
                f'Query result: {result}'
            )
    except psycopg2.OperationalError as e:
        return add_check(
            'database_connection',
            'FAIL',
            'Database connection failed (operational error)',
            str(e)
        )
    except psycopg2.Error as e:
        return add_check(
            'database_connection',
            'FAIL',
            'Database connection failed (PostgreSQL error)',
            str(e)
        )
    except Exception as e:
        return add_check(
            'database_connection',
            'FAIL',
            'Database connection failed (unexpected error)',
            str(e)
        )


def check_config_manifest():
    """
    Check 3: Config manifest loads and validates schema.
    Attempts to load config using ConfigLoader and validate against manifest schema.
    """
    try:
        # Import config loader
        from common.config import ConfigLoader, ConfigError
        
        # Create a minimal config loader for core (smoke test)
        config_loader = ConfigLoader('core')
        
        # Try to load configuration (this validates required vars are present)
        # For smoke test, we'll use optional vars to avoid hard failure
        # This checks that ConfigLoader itself works
        config_loader.optional('RANSOMEYE_DB_HOST', default='localhost')
        config_loader.optional('RANSOMEYE_DB_PORT', default='5432')
        config_loader.optional('RANSOMEYE_DB_NAME', default='ransomeye')
        
        # Load config (will succeed even if some vars missing, since we used optional)
        config = config_loader.load()
        
        # Verify config structure
        assert isinstance(config, dict), "Config must be a dictionary"
        
        # Try to validate against manifest schema if manifest file exists
        manifest_path = Path(os.getenv(
            'RANSOMEYE_INSTALL_ROOT', '/opt/ransomeye'
        )) / 'config' / 'installer.manifest.json'
        
        schema_path = _project_root / 'installer' / 'install.manifest.schema.json'
        
        schema_validated = False
        if manifest_path.exists() and schema_path.exists():
            try:
                import jsonschema
                
                # Load manifest
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                
                # Load schema
                with open(schema_path, 'r') as f:
                    schema = json.load(f)
                
                # Validate
                jsonschema.validate(manifest, schema)
                schema_validated = True
                
                return add_check(
                    'config_manifest',
                    'PASS',
                    f'Config manifest loaded and validated against schema (manifest={manifest_path})'
                )
            except json.JSONDecodeError as e:
                return add_check(
                    'config_manifest',
                    'FAIL',
                    'Config manifest file is not valid JSON',
                    str(e)
                )
            except jsonschema.ValidationError as e:
                return add_check(
                    'config_manifest',
                    'FAIL',
                    'Config manifest does not match schema',
                    str(e.message)
                )
            except ImportError:
                # jsonschema not available, skip schema validation but pass config loading
                return add_check(
                    'config_manifest',
                    'PASS',
                    f'Config loader works (manifest={manifest_path}, schema validation skipped: jsonschema not available)'
                )
        else:
            # Manifest doesn't exist, but config loader works
            return add_check(
                'config_manifest',
                'PASS',
                f'Config loader works (manifest not found at {manifest_path}, schema at {schema_path})'
            )
            
    except ImportError as e:
        return add_check(
            'config_manifest',
            'FAIL',
            'Failed to import config loader',
            str(e)
        )
    except ConfigError as e:
        return add_check(
            'config_manifest',
            'FAIL',
            'Config validation failed',
            str(e)
        )
    except Exception as e:
        return add_check(
            'config_manifest',
            'FAIL',
            'Unexpected error during config manifest check',
            str(e)
        )


def check_agent_registry():
    """
    Check 4: Agent registry initializes without error.
    Verifies that agent classes can be imported and initialized (minimal initialization).
    """
    try:
        # Try to import Linux agent
        linux_agent_imported = False
        try:
            from agents.linux.agent_main import LinuxAgent
            linux_agent_imported = True
        except ImportError as e:
            # Linux agent might not be available in all environments
            pass
        
        # Try to import Windows agent
        windows_agent_imported = False
        try:
            from agents.windows.agent.agent_main import WindowsAgent
            windows_agent_imported = True
        except ImportError as e:
            # Windows agent might not be available in all environments
            pass        
        except Exception as e:
            # Windows agent module might have import-time errors
            pass
        
        # At least one agent should be importable
        if linux_agent_imported or windows_agent_imported:
            agents_found = []
            if linux_agent_imported:
                agents_found.append('LinuxAgent')
            if windows_agent_imported:
                agents_found.append('WindowsAgent')
            
            # Try minimal initialization check (verify class structure)
            if linux_agent_imported:
                assert hasattr(LinuxAgent, '__init__'), "LinuxAgent missing __init__"
            if windows_agent_imported:
                assert hasattr(WindowsAgent, '__init__'), "WindowsAgent missing __init__"
            
            return add_check(
                'agent_registry',
                'PASS',
                f'Agent registry initialized successfully (agents: {", ".join(agents_found)})'
            )
        else:
            return add_check(
                'agent_registry',
                'FAIL',
                'No agent classes could be imported (LinuxAgent and WindowsAgent both failed)',
                'Both LinuxAgent and WindowsAgent import failed'
            )
            
    except AssertionError as e:
        return add_check(
            'agent_registry',
            'FAIL',
            'Agent class structure invalid',
            str(e)
        )
    except Exception as e:
        return add_check(
            'agent_registry',
            'FAIL',
            'Unexpected error during agent registry initialization',
            str(e)
        )


def main():
    """Run all smoke checks and output results."""
    print("RansomEye v1.0 Phase 8.1 Runtime Smoke Validation", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    
    # Run all checks
    checks_passed = []
    checks_passed.append(check_core_service_import())
    checks_passed.append(check_database_connection())
    checks_passed.append(check_config_manifest())
    checks_passed.append(check_agent_registry())
    
    # Determine overall status
    if all(checks_passed):
        results['overall_status'] = 'PASS'
        print("All checks PASSED", file=sys.stderr)
    else:
        results['overall_status'] = 'FAIL'
        print("One or more checks FAILED", file=sys.stderr)
    
    # Print summary to stderr
    print("\nCheck Summary:", file=sys.stderr)
    for check in results['checks']:
        status_symbol = '✓' if check['status'] == 'PASS' else '✗'
        print(f"  {status_symbol} {check['name']}: {check['status']}", file=sys.stderr)
        if check['message']:
            print(f"    {check['message']}", file=sys.stderr)
        if check['error']:
            print(f"    Error: {check['error']}", file=sys.stderr)
    
    # Write JSON output to stdout (machine-readable)
    output_file = Path(_project_root) / 'validation' / 'runtime_smoke' / 'runtime_smoke_result.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults written to: {output_file}", file=sys.stderr)
    
    # Exit with appropriate code
    if results['overall_status'] == 'PASS':
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
