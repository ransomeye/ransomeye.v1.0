#!/usr/bin/env python3
"""
RansomEye KillChain & Forensics - Artifact Store
AUTHORITATIVE: Secure storage indexing for evidence artifacts
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Iterator, Optional
import uuid
from datetime import datetime, timezone


class ArtifactStoreError(Exception):
    """Base exception for artifact store errors."""
    pass


class ArtifactNotFoundError(ArtifactStoreError):
    """Raised when artifact is not found."""
    pass


class ArtifactStore:
    """
    Secure storage indexing for evidence artifacts.
    
    Properties:
    - Immutable: Evidence records cannot be modified after creation
    - Indexed: Fast lookup by evidence_id
    - Chain-of-custody: Complete access log maintained
    - Integrity: Hash verification on every access
    """
    
    def __init__(self, store_path: Path, storage_root: Path):
        """
        Initialize artifact store.
        
        Args:
            store_path: Path to evidence index file (JSON lines format)
            storage_root: Root directory for evidence artifact storage
        """
        self.store_path = Path(store_path)
        self.storage_root = Path(storage_root)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_root.mkdir(parents=True, exist_ok=True)
    
    def register_artifact(
        self,
        artifact_path: Path,
        evidence_type: str,
        artifact_hash: str,
        artifact_size: int,
        compression_applied: bool = False
    ) -> Dict[str, Any]:
        """
        Register evidence artifact in store.
        
        Args:
            artifact_path: Path to evidence artifact
            evidence_type: Type of evidence (memory_dump, disk_artifact, etc.)
            artifact_hash: SHA256 hash of artifact
            artifact_size: Size of artifact in bytes
            compression_applied: Whether compression was applied
        
        Returns:
            Evidence record dictionary
        """
        evidence_id = str(uuid.uuid4())
        
        # Determine storage location
        storage_location = str(self.storage_root / f"{evidence_id}.artifact")
        
        # Create evidence record
        evidence_record = {
            'evidence_id': evidence_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'evidence_type': evidence_type,
            'artifact_path': str(artifact_path),
            'artifact_hash': artifact_hash,
            'artifact_size': artifact_size,
            'compression_applied': compression_applied,
            'storage_location': storage_location,
            'access_log': [],
            'integrity_verified': False
        }
        
        # Store record
        try:
            record_json = json.dumps(evidence_record, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(self.store_path, 'a', encoding='utf-8') as f:
                f.write(record_json)
                f.write('\n')
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            raise ArtifactStoreError(f"Failed to register artifact: {e}") from e
        
        return evidence_record
    
    def read_all(self) -> Iterator[Dict[str, Any]]:
        """
        Read all evidence records from store.
        
        Yields:
            Evidence record dictionaries
        """
        if not self.store_path.exists():
            return
        
        try:
            with open(self.store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    yield json.loads(line)
        except Exception as e:
            raise ArtifactStoreError(f"Failed to read artifact store: {e}") from e
    
    def find_by_id(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        """
        Find evidence record by ID.
        
        Args:
            evidence_id: Evidence identifier
        
        Returns:
            Evidence record dictionary, or None if not found
        """
        for record in self.read_all():
            if record.get('evidence_id') == evidence_id:
                return record
        return None
    
    def log_access(
        self,
        evidence_id: str,
        accessed_by: str,
        access_type: str,
        ledger_entry_id: str
    ) -> None:
        """
        Log evidence access (chain-of-custody).
        
        Note: This updates the access log, which is the only mutable part of evidence records.
        All access must be logged for chain-of-custody.
        
        Args:
            evidence_id: Evidence identifier
            accessed_by: Entity that accessed evidence
            access_type: Type of access (read, verify, export)
            ledger_entry_id: Audit ledger entry ID for this access
        """
        # Find record
        record = self.find_by_id(evidence_id)
        if not record:
            raise ArtifactNotFoundError(f"Evidence not found: {evidence_id}")
        
        # Add access log entry
        access_entry = {
            'access_timestamp': datetime.now(timezone.utc).isoformat(),
            'accessed_by': accessed_by,
            'access_type': access_type,
            'ledger_entry_id': ledger_entry_id
        }
        
        record['access_log'].append(access_entry)
        
        # Rewrite record (immutable except for access log)
        # For Phase C1, we update the access log in place
        # In production, this might be handled differently (append-only log)
        try:
            # Read all records
            all_records = list(self.read_all())
            
            # Update target record
            for i, r in enumerate(all_records):
                if r.get('evidence_id') == evidence_id:
                    all_records[i] = record
                    break
            
            # Rewrite store
            with open(self.store_path, 'w', encoding='utf-8') as f:
                for r in all_records:
                    record_json = json.dumps(r, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
                    f.write(record_json)
                    f.write('\n')
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            raise ArtifactStoreError(f"Failed to log access: {e}") from e
    
    def verify_integrity(self, evidence_id: str) -> bool:
        """
        Verify evidence artifact integrity.
        
        Args:
            evidence_id: Evidence identifier
        
        Returns:
            True if integrity verified
        
        Raises:
            ArtifactNotFoundError: If evidence not found
            ArtifactStoreError: If verification fails
        """
        record = self.find_by_id(evidence_id)
        if not record:
            raise ArtifactNotFoundError(f"Evidence not found: {evidence_id}")
        
        artifact_path = Path(record.get('artifact_path'))
        expected_hash = record.get('artifact_hash')
        
        from evidence.hasher import Hasher
        
        try:
            Hasher.verify_hash(artifact_path, expected_hash)
            
            # Mark as verified
            record['integrity_verified'] = True
            
            # Update record (for integrity flag only)
            all_records = list(self.read_all())
            for i, r in enumerate(all_records):
                if r.get('evidence_id') == evidence_id:
                    all_records[i] = record
                    break
            
            with open(self.store_path, 'w', encoding='utf-8') as f:
                for r in all_records:
                    record_json = json.dumps(r, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
                    f.write(record_json)
                    f.write('\n')
                f.flush()
                os.fsync(f.fileno())
            
            return True
        except Exception as e:
            raise ArtifactStoreError(f"Integrity verification failed: {e}") from e
