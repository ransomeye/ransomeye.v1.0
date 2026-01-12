#!/usr/bin/env python3
"""
RansomEye Audit Ledger - Verification CLI
AUTHORITATIVE: Command-line tool for verifying ledger integrity
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import argparse

# Add parent directory to path for imports
_audit_ledger_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_audit_ledger_dir))

from storage.append_only_store import AppendOnlyStore, StorageError
from crypto.verifier import Verifier, VerificationError, SignatureVerificationError, HashMismatchError
from crypto.key_manager import KeyManager, KeyNotFoundError


class VerificationReport:
    """Verification report with pass/fail status and failure details."""
    
    def __init__(self):
        self.passed = True
        self.total_entries = 0
        self.verified_entries = 0
        self.failures: List[Dict[str, Any]] = []
        self.first_failure_entry_id: Optional[str] = None
        self.first_failure_location: Optional[str] = None
    
    def add_failure(self, entry_id: str, location: str, error: str):
        """Add a verification failure."""
        self.passed = False
        if self.first_failure_entry_id is None:
            self.first_failure_entry_id = entry_id
            self.first_failure_location = location
        
        self.failures.append({
            'entry_id': entry_id,
            'location': location,
            'error': str(error)
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            'passed': self.passed,
            'total_entries': self.total_entries,
            'verified_entries': self.verified_entries,
            'first_failure_entry_id': self.first_failure_entry_id,
            'first_failure_location': self.first_failure_location,
            'failures': self.failures
        }


def validate_entry_schema(entry: Dict[str, Any], schema_path: Path) -> bool:
    """
    Validate entry against JSON schema.
    
    Args:
        entry: Ledger entry dictionary
        schema_path: Path to JSON schema file
    
    Returns:
        True if valid
    
    Raises:
        VerificationError: If validation fails
    """
    try:
        import jsonschema
    except ImportError:
        # Schema validation optional if jsonschema not available
        return True
    
    try:
        schema = json.loads(schema_path.read_text())
        jsonschema.validate(instance=entry, schema=schema)
        return True
    except jsonschema.ValidationError as e:
        raise VerificationError(f"Schema validation failed: {e.message}") from e
    except Exception as e:
        raise VerificationError(f"Schema validation error: {e}") from e


def verify_ledger(
    ledger_path: Path,
    key_dir: Path,
    schema_path: Optional[Path] = None
) -> VerificationReport:
    """
    Verify entire ledger.
    
    Verification steps:
    1. Read all entries
    2. For each entry:
       - Validate schema (if schema provided)
       - Verify entry hash
       - Verify signature
       - Verify hash chain
    3. Produce verification report
    
    Args:
        ledger_path: Path to ledger file
        key_dir: Directory containing public key
        schema_path: Optional path to JSON schema file
    
    Returns:
        VerificationReport with pass/fail status
    """
    report = VerificationReport()
    
    # Load public key
    try:
        key_manager = KeyManager(key_dir)
        public_key = key_manager.get_public_key()
        verifier = Verifier(public_key)
    except KeyNotFoundError as e:
        report.add_failure('', 'key_loading', f"Failed to load public key: {e}")
        return report
    except Exception as e:
        report.add_failure('', 'key_loading', f"Key loading error: {e}")
        return report
    
    # Load schema if provided
    if schema_path and schema_path.exists():
        schema_available = True
    else:
        schema_available = False
    
    # Read and verify all entries
    store = AppendOnlyStore(ledger_path, read_only=True)
    prev_entry: Optional[Dict[str, Any]] = None
    
    try:
        for entry in store.read_all():
            report.total_entries += 1
            entry_id = entry.get('ledger_entry_id', 'unknown')
            
            try:
                # Validate schema
                if schema_available and schema_path:
                    validate_entry_schema(entry, schema_path)
                
                # Verify entry (hash, signature, hash chain)
                verifier.verify_entry(entry, prev_entry)
                
                report.verified_entries += 1
                prev_entry = entry
                
            except VerificationError as e:
                report.add_failure(entry_id, 'verification', str(e))
                # Continue verification to find all failures
                prev_entry = entry
            except Exception as e:
                report.add_failure(entry_id, 'unexpected_error', f"Unexpected error: {e}")
                prev_entry = entry
    
    except StorageError as e:
        report.add_failure('', 'storage', f"Storage error: {e}")
        return report
    
    return report


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Verify RansomEye Audit Ledger integrity'
    )
    parser.add_argument(
        '--ledger',
        type=Path,
        required=True,
        help='Path to ledger file'
    )
    parser.add_argument(
        '--key-dir',
        type=Path,
        required=True,
        help='Directory containing public key'
    )
    parser.add_argument(
        '--schema',
        type=Path,
        help='Path to JSON schema file (optional)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Path to output verification report JSON (optional)'
    )
    
    args = parser.parse_args()
    
    # Verify ledger
    report = verify_ledger(args.ledger, args.key_dir, args.schema)
    
    # Output report
    if args.output:
        args.output.write_text(json.dumps(report.to_dict(), indent=2))
        print(f"Verification report written to: {args.output}")
    
    # Print summary
    print(f"Total entries: {report.total_entries}")
    print(f"Verified entries: {report.verified_entries}")
    
    if report.passed:
        print("VERIFICATION: PASSED")
        sys.exit(0)
    else:
        print("VERIFICATION: FAILED")
        print(f"First failure at: {report.first_failure_location}")
        print(f"First failure entry ID: {report.first_failure_entry_id}")
        print(f"Total failures: {len(report.failures)}")
        for failure in report.failures[:5]:  # Show first 5 failures
            print(f"  - Entry {failure['entry_id']}: {failure['error']}")
        sys.exit(1)


if __name__ == '__main__':
    main()
