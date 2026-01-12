#!/usr/bin/env python3
"""
RansomEye Audit Ledger - Append-Only Store
AUTHORITATIVE: File-based append-only storage for audit ledger entries
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Iterator, Optional
import uuid
from datetime import datetime, timezone


class StorageError(Exception):
    """Base exception for storage errors."""
    pass


class AppendError(StorageError):
    """Raised when append operation fails."""
    pass


class ReadOnlyError(StorageError):
    """Raised when write operation attempted on read-only store."""
    pass


class AppendOnlyStore:
    """
    Append-only file-based storage for audit ledger entries.
    
    Properties:
    - Append-only: Entries cannot be modified or deleted
    - Write-once: Each entry is written once and never changed
    - fsync: All writes are synced to disk immediately
    - Hash-chained: Each entry references previous entry's hash
    - Read-only mount: Supports read-only filesystem mounts
    """
    
    def __init__(self, ledger_path: Path, read_only: bool = False):
        """
        Initialize append-only store.
        
        Args:
            ledger_path: Path to ledger file (append-only log)
            read_only: If True, store is read-only (no writes allowed)
        """
        self.ledger_path = Path(ledger_path)
        self.read_only = read_only
        
        # Create parent directory if it doesn't exist (only if not read-only)
        if not self.read_only:
            self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
    
    def append(self, entry: Dict[str, Any]) -> None:
        """
        Append an entry to the ledger.
        
        This operation:
        - Writes entry as JSON line (one entry per line)
        - Calls fsync to ensure write is persisted
        - Enforces append-only semantics (no modification/deletion)
        
        Args:
            entry: Ledger entry dictionary (must be complete with entry_hash and signature)
        
        Raises:
            ReadOnlyError: If store is read-only
            AppendError: If append operation fails
        """
        if self.read_only:
            raise ReadOnlyError("Cannot append to read-only store")
        
        try:
            # Serialize entry to JSON (compact, one line)
            entry_json = json.dumps(entry, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            
            # Append to file (append mode)
            with open(self.ledger_path, 'a', encoding='utf-8') as f:
                f.write(entry_json)
                f.write('\n')
                # Force fsync to ensure write is persisted
                f.flush()
                os.fsync(f.fileno())
            
        except Exception as e:
            raise AppendError(f"Failed to append entry: {e}") from e
    
    def read_all(self) -> Iterator[Dict[str, Any]]:
        """
        Read all entries from the ledger.
        
        Yields:
            Ledger entry dictionaries
        
        Raises:
            StorageError: If read operation fails
        """
        if not self.ledger_path.exists():
            # Empty ledger (no entries yet)
            return
        
        try:
            with open(self.ledger_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry = json.loads(line)
                        yield entry
                    except json.JSONDecodeError as e:
                        raise StorageError(
                            f"Invalid JSON at line {line_num} in {self.ledger_path}: {e}"
                        ) from e
        
        except Exception as e:
            raise StorageError(f"Failed to read ledger: {e}") from e
    
    def get_last_entry(self) -> Optional[Dict[str, Any]]:
        """
        Get the last entry in the ledger.
        
        Returns:
            Last ledger entry dictionary, or None if ledger is empty
        
        Raises:
            StorageError: If read operation fails
        """
        last_entry = None
        for entry in self.read_all():
            last_entry = entry
        return last_entry
    
    def get_entry_count(self) -> int:
        """
        Get the number of entries in the ledger.
        
        Returns:
            Number of entries
        
        Raises:
            StorageError: If read operation fails
        """
        count = 0
        for _ in self.read_all():
            count += 1
        return count
    
    def exists(self) -> bool:
        """
        Check if ledger file exists.
        
        Returns:
            True if ledger file exists, False otherwise
        """
        return self.ledger_path.exists()
    
    def get_prev_entry_hash(self) -> str:
        """
        Get the entry_hash of the last entry (for hash chaining).
        
        Returns:
            Previous entry's entry_hash, or empty string if ledger is empty
        """
        last_entry = self.get_last_entry()
        if last_entry is None:
            return ''
        return last_entry.get('entry_hash', '')


class LedgerWriter:
    """
    High-level writer for audit ledger entries.
    
    Handles:
    - Entry creation (UUID, timestamp)
    - Hash chaining (prev_entry_hash)
    - Signing (entry_hash, signature)
    - Appending to store
    """
    
    def __init__(self, store: AppendOnlyStore, signer):
        """
        Initialize ledger writer.
        
        Args:
            store: Append-only store for writing entries
            signer: Signer instance for signing entries
        """
        self.store = store
        self.signer = signer
    
    def create_entry(
        self,
        component: str,
        component_instance_id: str,
        action_type: str,
        subject: Dict[str, str],
        actor: Dict[str, str],
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create and append a ledger entry.
        
        Args:
            component: Component name (core, linux-agent, etc.)
            component_instance_id: Component instance identifier
            action_type: Action type (installer_install, service_start, etc.)
            subject: Subject dictionary with 'type' and 'id'
            actor: Actor dictionary with 'type' and 'identifier'
            payload: Action-specific payload data
        
        Returns:
            Complete ledger entry dictionary
        """
        # Get previous entry hash for chaining
        prev_entry_hash = self.store.get_prev_entry_hash()
        
        # Create entry (without entry_hash and signature)
        entry = {
            'ledger_entry_id': str(uuid.uuid4()),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'component': component,
            'component_instance_id': component_instance_id,
            'action_type': action_type,
            'subject': subject,
            'actor': actor,
            'payload': payload,
            'prev_entry_hash': prev_entry_hash
        }
        
        # Sign entry (adds entry_hash, signature, signing_key_id)
        complete_entry = self.signer.sign_complete_entry(entry)
        
        # Append to store
        self.store.append(complete_entry)
        
        return complete_entry
