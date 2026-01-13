#!/usr/bin/env python3
"""
RansomEye v1.0 RBAC Initialization CLI
AUTHORITATIVE: Initialize RBAC system (database schema and role-permission mappings)
Python 3.10+ only
"""

import os
import sys
import argparse
from pathlib import Path

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.config import ConfigLoader, ConfigError
    from common.logging import setup_logging
    _common_available = True
    _logger = setup_logging('rbac-init')
except ImportError:
    _common_available = False
    _logger = None

# Add rbac to path
_rbac_path = os.path.join(_project_root, 'rbac')
if os.path.exists(_rbac_path) and _rbac_path not in sys.path:
    sys.path.insert(0, _rbac_path)

from api.rbac_api import RBACAPI, RBACAPIError


def main():
    """Initialize RBAC system."""
    parser = argparse.ArgumentParser(description='Initialize RansomEye RBAC system')
    parser.add_argument('--db-host', default='localhost', help='Database host')
    parser.add_argument('--db-port', type=int, default=5432, help='Database port')
    parser.add_argument('--db-name', default='ransomeye', help='Database name')
    parser.add_argument('--db-user', default='ransomeye', help='Database user')
    parser.add_argument('--db-password', required=True, help='Database password')
    parser.add_argument('--ledger-path', type=Path, help='Audit ledger path (optional)')
    parser.add_argument('--ledger-key-dir', type=Path, help='Audit ledger key directory (optional)')
    
    args = parser.parse_args()
    
    db_conn_params = {
        'host': args.db_host,
        'port': args.db_port,
        'database': args.db_name,
        'user': args.db_user,
        'password': args.db_password
    }
    
    try:
        rbac_api = RBACAPI(
            db_conn_params=db_conn_params,
            ledger_path=args.ledger_path,
            ledger_key_dir=args.ledger_key_dir
        )
        
        print("Initializing RBAC role-permission mappings...")
        rbac_api.initialize_role_permissions(created_by='system')
        print("✅ RBAC initialization complete")
        
    except RBACAPIError as e:
        print(f"❌ RBAC initialization failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
