#!/usr/bin/env python3
"""
RansomEye Explanation Assembly Engine - Assembly Store
AUTHORITATIVE: Immutable, append-only storage for assembled explanations
"""

import json
from pathlib import Path
from typing import Dict, Any, Iterator, Optional, List
import os


class AssemblyStoreError(Exception):
    """Base exception for assembly store errors."""
    pass


class AssemblyStore:
    """
    Immutable, append-only storage for assembled explanations.
    
    Properties:
    - Immutable: Records cannot be modified after creation
    - Append-only: Only additions allowed, no updates or deletes
    - Deterministic: Same inputs always produce same outputs
    - Offline-capable: No network or database dependencies
    """
    
    def __init__(self, store_path: Path):
        """
        Initialize assembly store.
        
        Args:
            store_path: Path to assembly store file (JSON lines format)
        """
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
    
    def store_assembly(self, assembled_explanation: Dict[str, Any]) -> None:
        """
        Store assembled explanation (immutable).
        
        Args:
            assembled_explanation: Assembled explanation dictionary (must be complete and valid)
        
        Raises:
            AssemblyStoreError: If storage fails
        """
        try:
            # Serialize to JSON (compact, one line)
            record_json = json.dumps(assembled_explanation, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            
            # Append to store file
            with open(self.store_path, 'a', encoding='utf-8') as f:
                f.write(record_json)
                f.write('\n')
                f.flush()
                os.fsync(f.fileno())
            
        except Exception as e:
            raise AssemblyStoreError(f"Failed to store assembled explanation: {e}") from e
    
    def get_assembly_by_id(self, assembled_explanation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get assembled explanation by ID.
        
        Args:
            assembled_explanation_id: Assembled explanation identifier
        
        Returns:
            Assembled explanation dictionary, or None if not found
        """
        for assembly in self.read_all():
            if assembly.get('assembled_explanation_id') == assembled_explanation_id:
                return assembly
        return None
    
    def get_assemblies_by_incident_id(self, incident_id: str) -> List[Dict[str, Any]]:
        """
        Get all assembled explanations for incident ID.
        
        Args:
            incident_id: Incident identifier
        
        Returns:
            List of assembled explanation dictionaries
        """
        assemblies = []
        for assembly in self.read_all():
            if assembly.get('incident_id') == incident_id:
                assemblies.append(assembly)
        return assemblies
    
    def read_all(self) -> Iterator[Dict[str, Any]]:
        """
        Read all assembled explanations from store.
        
        Yields:
            Assembled explanation dictionaries
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
            raise AssemblyStoreError(f"Failed to read assembly store: {e}") from e
    
    def count_assemblies(self) -> int:
        """
        Get count of stored assembled explanations.
        
        Returns:
            Number of assemblies
        """
        count = 0
        for _ in self.read_all():
            count += 1
        return count
