#!/usr/bin/env python3
"""
RansomEye Signed Reporting Engine - Verify Report CLI
AUTHORITATIVE: Command-line tool for verifying signed reports
"""

import sys
from pathlib import Path
import argparse

# Add parent directory to path for imports
_signed_reporting_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_signed_reporting_dir))

from crypto.report_verifier import ReportVerifier, VerificationError
from engine.render_hasher import RenderHasher
from storage.report_store import ReportStore


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Verify signed report'
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
        '--public-key',
        type=Path,
        required=True,
        help='Path to report signing public key'
    )
    parser.add_argument(
        '--rendered-content',
        type=Path,
        help='Path to rendered report content file (optional, for content hash verification)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load report record
        report_store = ReportStore(args.store)
        report_record = report_store.get_report_by_id(args.report_id)
        
        if not report_record:
            print(f"No report found: {args.report_id}", file=sys.stderr)
            sys.exit(1)
        
        # Initialize verifier
        verifier = ReportVerifier(args.public_key)
        hasher = RenderHasher()
        
        # Verify signature
        if args.rendered_content:
            rendered_content = args.rendered_content.read_bytes()
            
            # Verify content hash
            content_hash = hasher.hash_content(rendered_content)
            expected_hash = report_record.get('content_hash', '')
            
            if content_hash != expected_hash:
                print(f"Content hash mismatch: expected {expected_hash}, got {content_hash}", file=sys.stderr)
                sys.exit(1)
            
            # Verify signature
            signature = report_record.get('signature', '')
            if verifier.verify_signature(rendered_content, signature):
                print("✓ Report signature verified successfully")
                print("✓ Content hash verified successfully")
            else:
                print("✗ Report signature verification failed", file=sys.stderr)
                sys.exit(1)
        else:
            print("Warning: Rendered content not provided, skipping content hash verification", file=sys.stderr)
            print("Note: Signature verification requires rendered content")
        
        print(f"\nReport Verification:")
        print(f"  Report ID: {args.report_id}")
        print(f"  Incident ID: {report_record.get('incident_id', '')}")
        print(f"  View Type: {report_record.get('view_type', '')}")
        print(f"  Format: {report_record.get('format', '')}")
        print(f"  Content Hash: {report_record.get('content_hash', '')}")
        print(f"  Signing Key ID: {report_record.get('signing_key_id', '')}")
        print(f"  Generated At: {report_record.get('generated_at', '')}")
        
    except VerificationError as e:
        print(f"Report verification failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
