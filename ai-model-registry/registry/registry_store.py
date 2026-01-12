#!/usr/bin/env python3
"""
RansomEye AI Model Registry - Registry Store
AUTHORITATIVE: Immutable storage for model registry records
"""

import json
from pathlib import Path
from typing import Dict, Any, Iterator, Optional
import uuid


class RegistryError(Exception):
    """Base exception for registry errors."""
    pass


class ModelNotFoundError(RegistryError):
    """Raised when model is not found in registry."""
    pass


class ModelAlreadyExistsError(RegistryError):
    """Raised when model already exists in registry."""
    pass


class RegistryStore:
    """
    Immutable storage for model registry records.
    
    Properties:
    - Immutable: Records cannot be modified after creation
    - Versioned: Each model version is a separate record
    - Deterministic: Same inputs always produce same outputs
    - Offline-capable: No network or database dependencies
    """
    
    def __init__(self, registry_path: Path):
        """
        Initialize registry store.
        
        Args:
            registry_path: Path to registry file (JSON lines format)
        """
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
    
    def register(self, model_record: Dict[str, Any]) -> None:
        """
        Register a new model record.
        
        Args:
            model_record: Model record dictionary (must be complete and valid)
        
        Raises:
            ModelAlreadyExistsError: If model with same ID and version already exists
            RegistryError: If registration fails
        """
        # Check if model already exists
        model_id = model_record.get('model_id')
        model_version = model_record.get('model_version')
        
        if self.exists(model_id, model_version):
            raise ModelAlreadyExistsError(
                f"Model {model_id} version {model_version} already exists in registry"
            )
        
        try:
            # Serialize to JSON (compact, one line)
            record_json = json.dumps(model_record, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            
            # Append to registry file
            with open(self.registry_path, 'a', encoding='utf-8') as f:
                f.write(record_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
            
        except Exception as e:
            raise RegistryError(f"Failed to register model: {e}") from e
    
    def read_all(self) -> Iterator[Dict[str, Any]]:
        """
        Read all model records from registry.
        
        Yields:
            Model record dictionaries
        """
        if not self.registry_path.exists():
            return
        
        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    yield json.loads(line)
        except Exception as e:
            raise RegistryError(f"Failed to read registry: {e}") from e
    
    def find_by_id(self, model_id: str) -> Iterator[Dict[str, Any]]:
        """
        Find all versions of a model by ID.
        
        Args:
            model_id: Model identifier
        
        Yields:
            Model record dictionaries
        """
        for record in self.read_all():
            if record.get('model_id') == model_id:
                yield record
    
    def find_by_id_version(self, model_id: str, model_version: str) -> Optional[Dict[str, Any]]:
        """
        Find specific model version by ID and version.
        
        Args:
            model_id: Model identifier
            model_version: Model version
        
        Returns:
            Model record dictionary, or None if not found
        """
        for record in self.read_all():
            if (record.get('model_id') == model_id and 
                record.get('model_version') == model_version):
                return record
        return None
    
    def exists(self, model_id: str, model_version: str) -> bool:
        """
        Check if model exists in registry.
        
        Args:
            model_id: Model identifier
            model_version: Model version
        
        Returns:
            True if model exists, False otherwise
        """
        return self.find_by_id_version(model_id, model_version) is not None
    
    def find_active_models(self) -> Iterator[Dict[str, Any]]:
        """
        Find all active models (PROMOTED state).
        
        Yields:
            Model record dictionaries with PROMOTED state
        """
        for record in self.read_all():
            if record.get('lifecycle_state') == 'PROMOTED':
                yield record
    
    def find_by_state(self, state: str) -> Iterator[Dict[str, Any]]:
        """
        Find all models with specific lifecycle state.
        
        Args:
            state: Lifecycle state (REGISTERED, PROMOTED, DEPRECATED, REVOKED)
        
        Yields:
            Model record dictionaries
        """
        for record in self.read_all():
            if record.get('lifecycle_state') == state:
                yield record
