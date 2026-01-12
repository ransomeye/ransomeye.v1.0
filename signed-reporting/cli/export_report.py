#!/usr/bin/env python3
"""
RansomEye Signed Reporting Engine - Export Report CLI
AUTHORITATIVE: Command-line tool for exporting signed reports
"""

import sys
from pathlib import Path
import argparse

# Add parent directory to path for imports
_signed_reporting_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_signed_reporting_dir))

from api.reporting_api import ReportingAPI, ReportingAPIError
from engine.render_engine import RenderEngine
from storage.report_store import ReportStore


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Export signed report'
    )
    parser.add_argument(
        '--report-id',
        required=True,
        help='Report identifier'
    )
    parser.add_argument(
        '--store',
        type=Path,
        required=True,
        help='Path to report store file'
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
        required=True,
        help='Path to output report file'
    )
    
    args = parser.parse_args()
    
    try:
        # Load report record
        report_store = ReportStore(args.store)
        report_record = report_store.get_report_by_id(args.report_id)
        
        if not report_record:
            print(f"No report found: {args.report_id}", file=sys.stderr)
            sys.exit(1)
        
        # Get assembled explanation and re-render (deterministic)
        if args.assembly_store and args.assembly_ledger and args.assembly_ledger_key_dir:
            from api.assembly_api import AssemblyAPI
            
            assembly_api = AssemblyAPI(
                store_path=args.assembly_store,
                ledger_path=args.assembly_ledger,
                ledger_key_dir=args.assembly_ledger_key_dir
            )
            
            assembled_explanation_id = report_record.get('assembled_explanation_id', '')
            assembled_explanation = assembly_api.get_assembled_explanation(assembled_explanation_id)
            
            if not assembled_explanation:
                print(f"Assembled explanation not found: {assembled_explanation_id}", file=sys.stderr)
                sys.exit(1)
            
            # Re-render report (deterministic)
            render_engine = RenderEngine()
            format_type = report_record.get('format', 'PDF')
            rendered_content = render_engine.render_report(assembled_explanation, format_type)
            
            # Write rendered content
            args.output.write_bytes(rendered_content)
            print(f"Report exported to: {args.output}")
            
            # Emit audit ledger entry
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
            
            try:
                api.ledger_writer.create_entry(
                    component='signed-reporting',
                    component_instance_id='reporting-engine',
                    action_type='REPORT_EXPORTED',
                    subject={'type': 'report', 'id': args.report_id},
                    actor={'type': 'system', 'identifier': 'signed-reporting'},
                    payload={
                        'report_id': args.report_id,
                        'export_path': str(args.output)
                    }
                )
            except Exception as e:
                print(f"Warning: Failed to emit audit ledger entry: {e}", file=sys.stderr)
        else:
            print("Warning: Assembly store not provided, cannot re-render report", file=sys.stderr)
            print("Note: Report record exported, but rendered content requires assembly store", file=sys.stderr)
        
        print(f"\nReport Export:")
        print(f"  Report ID: {args.report_id}")
        print(f"  Incident ID: {report_record.get('incident_id', '')}")
        print(f"  View Type: {report_record.get('view_type', '')}")
        print(f"  Format: {report_record.get('format', '')}")
        print(f"  Content Hash: {report_record.get('content_hash', '')}")
        print(f"  Signing Key ID: {report_record.get('signing_key_id', '')}")
        
    except ReportingAPIError as e:
        print(f"Report export failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
