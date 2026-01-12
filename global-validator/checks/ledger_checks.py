#!/usr/bin/env python3
"""
RansomEye Global Validator - Ledger Integrity Checks
AUTHORITATIVE: Deterministic checks for audit ledger integrity
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add audit-ledger to path
_audit_ledger_dir = Path(__file__).parent.parent.parent / "audit-ledger"
sys.path.insert(0, str(_audit_ledger_dir))

from storage.append_only_store import AppendOnlyStore, StorageError
from crypto.verifier import Verifier, VerificationError
from crypto.key_manager import KeyManager, KeyNotFoundError


class LedgerCheckError(Exception):
    """Base exception for ledger check errors."""
    pass


class LedgerChecks:
    """
    Deterministic checks for audit ledger integrity.
    
    Checks performed:
    1. Full ledger replay
    2. Hash chain verification
    3. Signature verification
    4. Key continuity verification
    """
    
    def __init__(self, ledger_path: Path, key_dir: Path):
        """
        Initialize ledger checks.
        
        Args:
            ledger_path: Path to audit ledger file
            key_dir: Directory containing ledger public keys
        """
        self.ledger_path = ledger_path
        self.key_dir = key_dir
    
    def run_checks(self) -> Dict[str, Any]:
        """
        Run all ledger integrity checks.
        
        Returns:
            Dictionary with check results:
            - status: PASS or FAIL
            - total_entries: Number of entries in ledger
            - verified_entries: Number of entries that passed verification
            - hash_chain_valid: Whether hash chain is valid
            - signatures_valid: Whether all signatures are valid
            - key_continuity_valid: Whether key continuity is maintained
            - failures: List of failures
        """
        result = {
            'status': 'PASS',
            'total_entries': 0,
            'verified_entries': 0,
            'hash_chain_valid': True,
            'signatures_valid': True,
            'key_continuity_valid': True,
            'failures': []
        }
        
        # Load public key
        try:
            key_manager = KeyManager(self.key_dir)
            public_key = key_manager.get_public_key()
            verifier = Verifier(public_key)
        except KeyNotFoundError as e:
            result['status'] = 'FAIL'
            result['failures'].append({
                'entry_id': '',
                'error': f"Failed to load ledger public key: {e}"
            })
            return result
        except Exception as e:
            result['status'] = 'FAIL'
            result['failures'].append({
                'entry_id': '',
                'error': f"Key loading error: {e}"
            })
            return result
        
        # Read and verify all entries
        store = AppendOnlyStore(self.ledger_path, read_only=True)
        prev_entry: Optional[Dict[str, Any]] = None
        seen_key_ids = set()
        
        try:
            for entry in store.read_all():
                result['total_entries'] += 1
                entry_id = entry.get('ledger_entry_id', 'unknown')
                
                try:
                    # Verify entry (hash, signature, hash chain)
                    verifier.verify_entry(entry, prev_entry)
                    
                    # Track key IDs for continuity check
                    key_id = entry.get('signing_key_id')
                    if key_id:
                        seen_key_ids.add(key_id)
                    
                    result['verified_entries'] += 1
                    prev_entry = entry
                    
                except VerificationError as e:
                    result['status'] = 'FAIL'
                    result['hash_chain_valid'] = False
                    result['signatures_valid'] = False
                    result['failures'].append({
                        'entry_id': entry_id,
                        'error': str(e)
                    })
                    # Fail-fast: stop on first failure
                    break
                except Exception as e:
                    result['status'] = 'FAIL'
                    result['failures'].append({
                        'entry_id': entry_id,
                        'error': f"Unexpected error: {e}"
                    })
                    break
        
        except StorageError as e:
            result['status'] = 'FAIL'
            result['failures'].append({
                'entry_id': '',
                'error': f"Storage error: {e}"
            })
            return result
        
        # Key continuity check: all entries should use same key (or documented rotation)
        # For Phase A2, we check that at least one key is used
        if result['total_entries'] > 0 and len(seen_key_ids) == 0:
            result['status'] = 'FAIL'
            result['key_continuity_valid'] = False
            result['failures'].append({
                'entry_id': '',
                'error': "No signing key IDs found in ledger entries"
            })
        
        return result
