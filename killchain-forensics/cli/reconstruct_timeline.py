#!/usr/bin/env python3
"""
RansomEye KillChain & Forensics - Timeline Reconstruction CLI
AUTHORITATIVE: Command-line tool for reconstructing killchain timelines
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_forensics_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_forensics_dir))

from api.forensics_api import ForensicsAPI, ForensicsAPIError


def load_events(events_path: Path) -> list:
    """Load source events from JSON file."""
    if not events_path.exists():
        return []
    
    try:
        content = events_path.read_text()
        events = json.loads(content)
        if isinstance(events, list):
            return events
        elif isinstance(events, dict):
            return events.get('events', [])
        else:
            return []
    except Exception as e:
        print(f"Warning: Failed to load events from {events_path}: {e}", file=sys.stderr)
        return []


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Reconstruct killchain timeline from source events'
    )
    parser.add_argument(
        '--source-events',
        type=Path,
        required=True,
        help='Path to source events JSON file'
    )
    parser.add_argument(
        '--artifact-store',
        type=Path,
        required=True,
        help='Path to evidence index file'
    )
    parser.add_argument(
        '--artifact-storage-root',
        type=Path,
        required=True,
        help='Root directory for evidence storage'
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
        '--reconstructed-by',
        default='system',
        help='Entity that reconstructed timeline (default: system)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Path to output timeline JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load source events
        source_events = load_events(args.source_events)
        
        if not source_events:
            print("Warning: No source events found", file=sys.stderr)
        
        # Initialize forensics API
        api = ForensicsAPI(
            artifact_store_path=args.artifact_store,
            artifact_storage_root=args.artifact_storage_root,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Reconstruct timeline
        result = api.reconstruct_timeline(
            source_events=source_events,
            reconstructed_by=args.reconstructed_by
        )
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False))
            print(f"Timeline reconstructed successfully. Result written to: {args.output}")
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        print(f"\nTimeline Summary:")
        print(f"  Events processed: {len(source_events)}")
        print(f"  Timeline events: {len(result['timeline'])}")
        print(f"  Stage transitions: {len(result['stage_transitions'])}")
        print(f"  Campaigns: {len(result['campaigns'])}")
        
    except ForensicsAPIError as e:
        print(f"Timeline reconstruction failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
