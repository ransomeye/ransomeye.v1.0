#!/usr/bin/env python3
"""
RansomEye LLM Summarizer - Render Summary CLI
AUTHORITATIVE: Render existing summary to PDF/HTML/CSV
"""

import sys
import os
import argparse
from pathlib import Path

# Add parent directory to path
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

# Add project root to path for imports
_project_root = _parent_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from api.summarizer_api import SummarizerAPI, SummarizerAPIError


def main():
    """Render existing summary to PDF/HTML/CSV."""
    parser = argparse.ArgumentParser(
        description='Render existing summary to PDF/HTML/CSV format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --summary-id <uuid> --format PDF --output-file summary.pdf
  %(prog)s --summary-id <uuid> --format HTML --output-file summary.html
  %(prog)s --summary-id <uuid> --format CSV --output-file summary.csv

Environment Variables:
  RANSOMEYE_SUMMARY_STORE_PATH - Path to summary store
  RANSOMEYE_AUDIT_LEDGER_PATH - Path to audit ledger file
  RANSOMEYE_AUDIT_LEDGER_KEY_DIR - Directory containing ledger signing keys
        """
    )
    
    parser.add_argument(
        '--summary-id',
        type=str,
        required=True,
        help='Summary identifier (UUID)'
    )
    
    parser.add_argument(
        '--format',
        type=str,
        required=True,
        choices=['PDF', 'HTML', 'CSV'],
        help='Output format (PDF | HTML | CSV)'
    )
    
    parser.add_argument(
        '--output-file',
        type=Path,
        required=True,
        help='Path to write rendered output'
    )
    
    parser.add_argument(
        '--summary-store-path',
        type=Path,
        default=None,
        help='Path to summary store (overrides RANSOMEYE_SUMMARY_STORE_PATH)'
    )
    
    parser.add_argument(
        '--ledger-path',
        type=Path,
        default=None,
        help='Path to audit ledger (overrides RANSOMEYE_AUDIT_LEDGER_PATH)'
    )
    
    parser.add_argument(
        '--ledger-key-dir',
        type=Path,
        default=None,
        help='Directory containing ledger keys (overrides RANSOMEYE_AUDIT_LEDGER_KEY_DIR)'
    )
    
    parser.add_argument(
        '--template-registry-path',
        type=Path,
        default=None,
        help='Path to template registry (required for API initialization)'
    )
    
    parser.add_argument(
        '--output-schema-path',
        type=Path,
        default=None,
        help='Path to output schema (defaults to schema/summary-output.schema.json)'
    )
    
    args = parser.parse_args()
    
    # Get paths from env or args
    template_registry_path = args.template_registry_path or Path(os.getenv('RANSOMEYE_TEMPLATE_REGISTRY_PATH', ''))
    summary_store_path = args.summary_store_path or Path(os.getenv('RANSOMEYE_SUMMARY_STORE_PATH', ''))
    ledger_path = args.ledger_path or Path(os.getenv('RANSOMEYE_AUDIT_LEDGER_PATH', ''))
    ledger_key_dir = args.ledger_key_dir or Path(os.getenv('RANSOMEYE_AUDIT_LEDGER_KEY_DIR', ''))
    output_schema_path = args.output_schema_path or (_parent_dir / "schema" / "summary-output.schema.json")
    
    # Validate required paths
    if not template_registry_path:
        print("ERROR: Template registry path not provided. Set RANSOMEYE_TEMPLATE_REGISTRY_PATH or use --template-registry-path", file=sys.stderr)
        sys.exit(1)
    if not summary_store_path:
        print("ERROR: Summary store path not provided. Set RANSOMEYE_SUMMARY_STORE_PATH or use --summary-store-path", file=sys.stderr)
        sys.exit(1)
    if not ledger_path:
        print("ERROR: Audit ledger path not provided. Set RANSOMEYE_AUDIT_LEDGER_PATH or use --ledger-path", file=sys.stderr)
        sys.exit(1)
    if not ledger_key_dir:
        print("ERROR: Audit ledger key directory not provided. Set RANSOMEYE_AUDIT_LEDGER_KEY_DIR or use --ledger-key-dir", file=sys.stderr)
        sys.exit(1)
    
    # Initialize summarizer API
    try:
        api = SummarizerAPI(
            template_registry_path=template_registry_path,
            summary_store_path=summary_store_path,
            output_schema_path=output_schema_path,
            ledger_path=ledger_path,
            ledger_key_dir=ledger_key_dir,
            model_registry_api=None,  # Not needed for rendering
            signing_key_path=None,  # Not needed for rendering
            signing_key_id=None
        )
    except Exception as e:
        print(f"ERROR: Failed to initialize summarizer API: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Render summary
    try:
        rendered_output = api.render_summary(args.summary_id, args.format)
    except SummarizerAPIError as e:
        print(f"ERROR: Summary rendering failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error during rendering: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Write output file
    try:
        with open(args.output_file, 'wb') as f:
            f.write(rendered_output)
    except Exception as e:
        print(f"ERROR: Failed to write output file: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Print success
    print("SUCCESS: Summary rendered")
    print(f"  Summary ID: {args.summary_id}")
    print(f"  Format: {args.format}")
    print(f"  Output File: {args.output_file}")
    print(f"  Output Size: {len(rendered_output)} bytes")
    
    sys.exit(0)


if __name__ == '__main__':
    main()
