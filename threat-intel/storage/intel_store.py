#!/usr/bin/env python3
"""
RansomEye Threat Intelligence - Intel Store
AUTHORITATIVE: Immutable IOC storage
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timezone
import uuid
import hashlib
import json


class IntelStoreError(Exception):
    """Base exception for intel store errors."""
    pass


class IntelStore:
    """
    Immutable IOC storage.
    
    Properties:
    - Immutable: IOCs cannot be modified after storage
    - Deterministic: Same IOC = same storage result
    - Hash-based: Storage uses hash-based indexing
    """
    
    def __init__(self, iocs_store_path: Path):
        """
        Initialize intel store.
        
        Args:
            iocs_store_path: Path to IOCs store
        """
        self.iocs_store_path = Path(iocs_store_path)
        self.iocs_store_path.parent.mkdir(parents=True, exist_ok=True)
    
    def store_ioc(
        self,
        ioc_type: str,
        ioc_value: str,
        normalized_value: str,
        intel_source_id: str
    ) -> Dict[str, Any]:
        """
        Store IOC.
        
        Args:
            ioc_type: Type of IOC
            ioc_value: Original IOC value
            normalized_value: Normalized IOC value
            intel_source_id: Intelligence source identifier
        
        Returns:
            IOC dictionary
        """
        # Check if IOC already exists
        existing = self.get_ioc_by_normalized(normalized_value, ioc_type)
        if existing:
            # Update last_seen_at
            existing['last_seen_at'] = datetime.now(timezone.utc).isoformat()
            existing['immutable_hash'] = self._calculate_hash(existing)
            self._update_ioc(existing)
            return existing
        
        # Create new IOC
        ioc = {
            'ioc_id': str(uuid.uuid4()),
            'ioc_type': ioc_type,
            'ioc_value': ioc_value,
            'normalized_value': normalized_value,
            'intel_source_id': intel_source_id,
            'first_seen_at': datetime.now(timezone.utc).isoformat(),
            'last_seen_at': datetime.now(timezone.utc).isoformat(),
            'immutable_hash': ''
        }
        
        # Calculate hash
        ioc['immutable_hash'] = self._calculate_hash(ioc)
        
        # Store IOC
        self._store_ioc(ioc)
        
        return ioc
    
    def get_ioc(self, ioc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get IOC by ID.
        
        Args:
            ioc_id: IOC identifier
        
        Returns:
            IOC dictionary, or None if not found
        """
        iocs = self._load_all_iocs()
        
        for ioc in iocs:
            if ioc.get('ioc_id') == ioc_id:
                return ioc
        
        return None
    
    def get_ioc_by_normalized(
        self,
        normalized_value: str,
        ioc_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get IOC by normalized value and type.
        
        Args:
            normalized_value: Normalized IOC value
            ioc_type: IOC type
        
        Returns:
            IOC dictionary, or None if not found
        """
        iocs = self._load_all_iocs()
        
        for ioc in iocs:
            if (ioc.get('normalized_value') == normalized_value and
                ioc.get('ioc_type') == ioc_type):
                return ioc
        
        return None
    
    def list_iocs(
        self,
        ioc_type: Optional[str] = None,
        source_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List IOCs, optionally filtered by type or source.
        
        Args:
            ioc_type: Optional IOC type filter
            source_id: Optional source ID filter
        
        Returns:
            List of IOC dictionaries
        """
        iocs = self._load_all_iocs()
        
        if ioc_type:
            iocs = [i for i in iocs if i.get('ioc_type') == ioc_type]
        
        if source_id:
            iocs = [i for i in iocs if i.get('intel_source_id') == source_id]
        
        return iocs
    
    def _load_all_iocs(self) -> List[Dict[str, Any]]:
        """Load all IOCs from store."""
        iocs = []
        
        if not self.iocs_store_path.exists():
            return iocs
        
        try:
            with open(self.iocs_store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    iocs.append(json.loads(line))
        except Exception:
            pass
        
        return iocs
    
    def _store_ioc(self, ioc: Dict[str, Any]) -> None:
        """Store IOC to file-based store."""
        try:
            ioc_json = json.dumps(ioc, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(self.iocs_store_path, 'a', encoding='utf-8') as f:
                f.write(ioc_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise IntelStoreError(f"Failed to store IOC: {e}") from e
    
    def _update_ioc(self, ioc: Dict[str, Any]) -> None:
        """Update existing IOC (updates last_seen_at only)."""
        # For Phase J, we update by rewriting the file
        # In production, would use more efficient update mechanism
        iocs = self._load_all_iocs()
        
        # Find and update
        for i, existing in enumerate(iocs):
            if existing.get('ioc_id') == ioc.get('ioc_id'):
                iocs[i] = ioc
                break
        
        # Rewrite file
        try:
            with open(self.iocs_store_path, 'w', encoding='utf-8') as f:
                for ioc_item in iocs:
                    ioc_json = json.dumps(ioc_item, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
                    f.write(ioc_json)
                    f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise IntelStoreError(f"Failed to update IOC: {e}") from e
    
    def _calculate_hash(self, ioc: Dict[str, Any]) -> str:
        """Calculate SHA256 hash of IOC record."""
        hashable_content = {k: v for k, v in ioc.items() if k != 'immutable_hash'}
        canonical_json = json.dumps(hashable_content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
