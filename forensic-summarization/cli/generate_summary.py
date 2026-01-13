#!/usr/bin/env python3
"""
RansomEye v1.0 Forensic Summarization - Summary Generation CLI
AUTHORITATIVE: CLI tool for dev/test/audit use only (not user-facing in production)
"""

import os
import sys
import argparse
import json
from pathlib import Path

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    _logger = setup_logging('forensic-summarization-cli')
except ImportError:
    import logging
    _logger = logging.getLogger('forensic-summarization-cli')

# Database connection
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    _psycopg2_available = True
except ImportError:
    _psycopg2_available = False
    _logger.warning("psycopg2 not available - database operations disabled")

from ..api import SummarizationAPI


def get_db_connection():
    """
    Get database connection from environment variables.
    
    Returns:
        PostgreSQL connection or None if not available
    """
    if not _psycopg2_available:
        return None
    
    db_host = os.getenv('RANSOMEYE_DB_HOST', 'localhost')
    db_port = int(os.getenv('RANSOMEYE_DB_PORT', '5432'))
    db_name = os.getenv('RANSOMEYE_DB_NAME', 'ransomeye')
    db_user = os.getenv('RANSOMEYE_DB_USER', 'ransomeye_forensics')
    db_password = os.getenv('RANSOMEYE_DB_PASSWORD', '')
    
    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        return conn
    except Exception as e:
        _logger.error(f"Failed to connect to database: {e}", exc_info=True)
        return None


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='RansomEye Forensic Summarization CLI (dev/test/audit only)'
    )
    parser.add_argument(
        '--incident-id',
        required=True,
        help='Incident identifier (UUID)'
    )
    parser.add_argument(
        '--output-format',
        choices=['json', 'text', 'graph', 'all'],
        default='all',
        help='Output format (default: all)'
    )
    parser.add_argument(
        '--output-file',
        type=Path,
        help='Output file path (optional, prints to stdout if not specified)'
    )
    parser.add_argument(
        '--json-only',
        action='store_true',
        help='Output JSON only (for machine consumption)'
    )
    
    args = parser.parse_args()
    
    # Get database connection
    db_conn = get_db_connection()
    if not db_conn:
        print("ERROR: Database connection not available", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Initialize API
        api = SummarizationAPI(db_conn)
        
        # Generate summary
        summary = api.generate_summary(
            incident_id=args.incident_id,
            output_format=args.output_format
        )
        
        # Output summary
        if args.json_only or args.output_format == 'json':
            output = json.dumps(summary, indent=2, ensure_ascii=False)
        elif args.output_format == 'text':
            output = summary.get('text_summary', '')
        elif args.output_format == 'graph':
            output = json.dumps(summary.get('graph_metadata', {}), indent=2, ensure_ascii=False)
        else:  # 'all'
            output = json.dumps(summary, indent=2, ensure_ascii=False)
        
        if args.output_file:
            args.output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(args.output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"Summary written to: {args.output_file}")
        else:
            print(output)
        
    except Exception as e:
        _logger.error(f"Failed to generate summary: {e}", exc_info=True)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if db_conn:
            db_conn.close()


if __name__ == '__main__':
    main()
