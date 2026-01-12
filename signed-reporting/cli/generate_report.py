#!/usr/bin/env python3
"""
RansomEye Signed Reporting Engine - Generate Report CLI
AUTHORITATIVE: Command-line tool for generating signed reports
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_signed_reporting_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_signed_reporting_dir))

from api.reporting_api import ReportingAPI, ReportingAPIError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Generate signed report from assembled explanation'
    )
    parser.add_argument(
        '--incident-id',
        required=True,
        help='Incident identifier'
    )
    parser.add_argument(
        '--view-type',
        required=True,
        choices=['SOC_ANALYST', 'INCIDENT_COMMANDER', 'EXECUTIVE', 'REGULATOR'],
        help='View type (exactly 4 types, no others)'
    )
    parser.add_argument(
        '--format',
        required=True,
        choices=['PDF', 'HTML', 'CSV'],
        help='Report format (exactly 3 formats: PDF, HTML, CSV)'
    )
    parser.add_argument(
        '--assembled-explanation-id',
        help='Assembled explanation identifier (optional, uses latest if not provided)'
    )
    parser.add_argument(
        '--assembly-store',
        type=Path,
        help='Path to explanation assembly store (optional)'
    )
    parser.add_argument(
        '--assembly-ledger',
        type=Path,
        help='Path to explanation assembly ledger (optional)'
    )
    parser.add_argument(
        '--assembly-ledger-key-dir',
        type=Path,
        help='Directory containing explanation assembly ledger keys (optional)'
    )
    parser.add_argument(
        '--store',
        type=Path,
        required=True,
        help='Path to report store file'
    )
    parser.add_argument(
        '--ledger',
        type=Path,
        required=True,
        help='Path to audit ledger file'
    )
    parser.add_argument(
        '--ledger-key-dir',
        type=Path,
        required=True,
        help='Directory containing ledger signing keys'
    )
    parser.add_argument(
        '--signing-key',
        type=Path,
        required=True,
        help='Path to report signing private key'
    )
    parser.add_argument(
        '--signing-key-id',
        required=True,
        help='Signing key identifier'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Path to output report record JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize Reporting API
        api = ReportingAPI(
            store_path=args.store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir,
            signing_key_path=args.signing_key,
            signing_key_id=args.signing_key_id,
            assembly_store_path=args.assembly_store,
            assembly_ledger_path=args.assembly_ledger,
            assembly_ledger_key_dir=args.assembly_ledger_key_dir
        )
        
        # Generate report
        report_record = api.generate_report(
            incident_id=args.incident_id,
            view_type=args.view_type,
            format_type=args.format,
            assembled_explanation_id=args.assembled_explanation_id
        )
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(report_record, indent=2, ensure_ascii=False))
            print(f"Signed report generated. Result written to: {args.output}")
        else:
            print(json.dumps(report_record, indent=2, ensure_ascii=False))
        
        print(f"\nSigned Report Summary:")
        print(f"  Report ID: {report_record.get('report_id')}")
        print(f"  Incident ID: {args.incident_id}")
        print(f"  View Type: {report_record.get('view_type', '')}")
        print(f"  Format: {report_record.get('format', '')}")
        print(f"  Content Hash: {report_record.get('content_hash', '')}")
        print(f"  Signing Key ID: {report_record.get('signing_key_id', '')}")
        print(f"  Audit Ledger Anchor: {report_record.get('audit_ledger_anchor', '')}")
        
    except ReportingAPIError as e:
        print(f"Report generation failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
