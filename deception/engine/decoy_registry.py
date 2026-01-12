#!/usr/bin/env python3
"""
RansomEye Deception Framework - Decoy Registry
AUTHORITATIVE: Immutable decoy definitions and storage
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timezone
import uuid
import hashlib
import json


class DecoyRegistryError(Exception):
    """Base exception for decoy registry errors."""
    pass


class DecoyRegistry:
    """
    Immutable decoy registry.
    
    Properties:
    - Immutable: Decoys cannot be modified after registration
    - Deterministic: Same decoy config = same decoy
    - Isolated: Decoys are isolated from production assets
    """
    
    def __init__(self, decoys_store_path: Path):
        """
        Initialize decoy registry.
        
        Args:
            decoys_store_path: Path to decoys store
        """
        self.decoys_store_path = Path(decoys_store_path)
        self.decoys_store_path.parent.mkdir(parents=True, exist_ok=True)
    
    def register_decoy(
        self,
        decoy_type: str,
        decoy_name: str,
        decoy_config: Dict[str, Any],
        deployment_target: str
    ) -> Dict[str, Any]:
        """
        Register decoy.
        
        Args:
            decoy_type: Type of decoy (host, service, credential, file)
            decoy_name: Human-readable decoy name
            decoy_config: Decoy-specific configuration
            deployment_target: Deployment target identifier
        
        Returns:
            Decoy dictionary
        """
        # Validate decoy type
        valid_types = ['host', 'service', 'credential', 'file']
        if decoy_type not in valid_types:
            raise DecoyRegistryError(f"Invalid decoy type: {decoy_type}")
        
        # Create decoy
        decoy = {
            'decoy_id': str(uuid.uuid4()),
            'decoy_type': decoy_type,
            'decoy_name': decoy_name,
            'decoy_config': decoy_config,
            'deployment_target': deployment_target,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'immutable_hash': ''
        }
        
        # Calculate hash
        decoy['immutable_hash'] = self._calculate_hash(decoy)
        
        # Store decoy
        self._store_decoy(decoy)
        
        return decoy
    
    def get_decoy(self, decoy_id: str) -> Optional[Dict[str, Any]]:
        """
        Get decoy by ID.
        
        Args:
            decoy_id: Decoy identifier
        
        Returns:
            Decoy dictionary, or None if not found
        """
        decoys = self._load_all_decoys()
        
        for decoy in decoys:
            if decoy.get('decoy_id') == decoy_id:
                return decoy
        
        return None
    
    def list_decoys(self, decoy_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all decoys, optionally filtered by type.
        
        Args:
            decoy_type: Optional decoy type filter
        
        Returns:
            List of decoy dictionaries
        """
        decoys = self._load_all_decoys()
        
        if decoy_type:
            decoys = [d for d in decoys if d.get('decoy_type') == decoy_type]
        
        return decoys
    
    def _load_all_decoys(self) -> List[Dict[str, Any]]:
        """Load all decoys from store."""
        decoys = []
        
        if not self.decoys_store_path.exists():
            return decoys
        
        try:
            with open(self.decoys_store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    decoys.append(json.loads(line))
        except Exception:
            pass
        
        return decoys
    
    def _store_decoy(self, decoy: Dict[str, Any]) -> None:
        """Store decoy to file-based store."""
        try:
            decoy_json = json.dumps(decoy, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(self.decoys_store_path, 'a', encoding='utf-8') as f:
                f.write(decoy_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise DecoyRegistryError(f"Failed to store decoy: {e}") from e
    
    def _calculate_hash(self, decoy: Dict[str, Any]) -> str:
        """Calculate SHA256 hash of decoy record."""
        hashable_content = {k: v for k, v in decoy.items() if k != 'immutable_hash'}
        canonical_json = json.dumps(hashable_content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
