#!/usr/bin/env python3
"""
RansomEye Audit Ledger - Export CLI
AUTHORITATIVE: Command-line tool for exporting ledger entries
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
import argparse

# Add parent directory to path for imports
_audit_ledger_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_audit_ledger_dir))

from storage.append_only_store import AppendOnlyStore, StorageError


def export_ledger(
    ledger_path: Path,
    output_path: Path,
    format: str = 'json',
    start_entry_id: Optional[str] = None,
    end_entry_id: Optional[str] = None
) -> None:
    """
    Export ledger entries to file.
    
    Args:
        ledger_path: Path to ledger file
        output_path: Path to output file
        format: Export format ('json' or 'jsonl')
        start_entry_id: Optional entry ID to start from
        end_entry_id: Optional entry ID to end at
    """
    store = AppendOnlyStore(ledger_path, read_only=True)
    
    entries = []
    in_range = start_entry_id is None
    
    for entry in store.read_all():
        entry_id = entry.get('ledger_entry_id', '')
        
        # Check if we've reached start entry
        if not in_range and entry_id == start_entry_id:
            in_range = True
        
        # Add entry if in range
        if in_range:
            entries.append(entry)
            
            # Check if we've reached end entry
            if end_entry_id and entry_id == end_entry_id:
                break
    
    # Write output
    if format == 'json':
        output_path.write_text(json.dumps(entries, indent=2, ensure_ascii=False))
    elif format == 'jsonl':
        with open(output_path, 'w', encoding='utf-8') as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False))
                f.write('\n')
    else:
        raise ValueError(f"Unsupported format: {format}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Export RansomEye Audit Ledger entries'
    )
    parser.add_argument(
        '--ledger',
        type=Path,
        required=True,
        help='Path to ledger file'
    )
    parser.add_argument(
        '--output',
        type=Path,
        required=True,
        help='Path to output file'
    )
    parser.add_argument(
        '--format',
        choices=['json', 'jsonl'],
        default='json',
        help='Export format (default: json)'
    )
    parser.add_argument(
        '--start-entry-id',
        help='Entry ID to start from (optional)'
    )
    parser.add_argument(
        '--end-entry-id',
        help='Entry ID to end at (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        export_ledger(
            args.ledger,
            args.output,
            args.format,
            args.start_entry_id,
            args.end_entry_id
        )
        print(f"Exported {len(list(AppendOnlyStore(args.ledger, read_only=True).read_all()))} entries to: {args.output}")
        sys.exit(0)
    except Exception as e:
        print(f"Export failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
