#!/usr/bin/env python3
"""
RansomEye Threat Intelligence - Correlate IOCs CLI
AUTHORITATIVE: Command-line tool for correlating IOCs with evidence
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_intel_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_intel_dir))

from api.intel_api import IntelAPI, IntelAPIError


def load_evidence(evidence_path: Path) -> dict:
    """Load evidence from file."""
    if not evidence_path.exists():
        return {}
    
    try:
        return json.loads(evidence_path.read_text())
    except Exception as e:
        print(f"Warning: Failed to load evidence: {e}", file=sys.stderr)
        return {}


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Correlate IOCs with evidence'
    )
    parser.add_argument(
        '--evidence',
        type=Path,
        required=True,
        help='Path to evidence JSON file'
    )
    parser.add_argument(
        '--evidence-type',
        choices=['forensic_artifact', 'network_scan', 'alert', 'deception_interaction', 'incident'],
        required=True,
        help='Type of evidence'
    )
    parser.add_argument(
        '--iocs-store',
        type=Path,
        required=True,
        help='Path to IOCs store'
    )
    parser.add_argument(
        '--sources-store',
        type=Path,
        required=True,
        help='Path to intelligence sources store'
    )
    parser.add_argument(
        '--correlations-store',
        type=Path,
        required=True,
        help='Path to correlations store'
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
        '--output',
        type=Path,
        help='Path to output correlations JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load evidence
        evidence = load_evidence(args.evidence)
        if not evidence:
            print("Error: Failed to load evidence", file=sys.stderr)
            sys.exit(1)
        
        # Initialize intel API
        api = IntelAPI(
            iocs_store_path=args.iocs_store,
            sources_store_path=args.sources_store,
            correlations_store_path=args.correlations_store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Correlate IOCs
        correlations = api.correlate_iocs(
            evidence=evidence,
            evidence_type=args.evidence_type
        )
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(correlations, indent=2, ensure_ascii=False))
            print(f"Correlations completed. Result written to: {args.output}")
        else:
            print(json.dumps(correlations, indent=2, ensure_ascii=False))
        
        print(f"\nCorrelation Summary:")
        print(f"  Evidence Type: {args.evidence_type}")
        print(f"  Correlations Found: {len(correlations)}")
        for i, corr in enumerate(correlations, 1):
            print(f"  Correlation {i}: {corr.get('correlation_method')} (IOC: {corr.get('ioc_id')[:8]}...)")
        
    except IntelAPIError as e:
        print(f"Correlation failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
