#!/usr/bin/env python3
"""
RansomEye Supply-Chain Signing & Verification Framework - Key Registry
AUTHORITATIVE: Persistent key registry with lifecycle management
Phase-9: Persistent vendor signing authority
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum


class KeyStatus(Enum):
    """Key status enumeration."""
    ACTIVE = "active"
    REVOKED = "revoked"
    ROTATED = "rotated"
    COMPROMISED = "compromised"


class KeyType(Enum):
    """Key type enumeration."""
    ROOT = "root"
    SIGNING = "signing"


class KeyRegistryError(Exception):
    """Base exception for key registry errors."""
    pass


class KeyRegistry:
    """
    Persistent key registry for vendor signing keys.
    
    Three-tier hierarchy:
    1. Root Key (offline, air-gapped) - attests signing keys only
    2. Vendor Signing Key (persistent) - signs artifacts, SBOM, evidence
    3. No ephemeral keys allowed
    
    Properties:
    - Persistent: Keys persist across CI runs
    - Auditable: All key operations logged
    - Lifecycle-managed: Generation, rotation, revocation tracked
    """
    
    def __init__(self, registry_path: Path):
        """
        Initialize key registry.
        
        Args:
            registry_path: Path to key registry JSON file
        """
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._registry = self._load_registry()
    
    def _load_registry(self) -> Dict[str, Any]:
        """Load registry from disk."""
        if not self.registry_path.exists():
            return {
                "version": "1.0",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "keys": {},
                "revocation_list": []
            }
        
        try:
            with open(self.registry_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise KeyRegistryError(f"Failed to load key registry: {e}") from e
    
    def _save_registry(self) -> None:
        """Save registry to disk."""
        try:
            with open(self.registry_path, 'w') as f:
                json.dump(self._registry, f, indent=2, ensure_ascii=False)
        except IOError as e:
            raise KeyRegistryError(f"Failed to save key registry: {e}") from e
    
    def register_key(
        self,
        key_id: str,
        key_type: KeyType,
        public_key_fingerprint: str,
        generation_date: str,
        generation_log_path: Optional[Path] = None,
        parent_key_id: Optional[str] = None
    ) -> None:
        """
        Register a new key in the registry.
        
        Args:
            key_id: Key identifier (e.g., vendor-signing-key-1)
            key_type: Key type (ROOT or SIGNING)
            public_key_fingerprint: SHA256 fingerprint of public key
            generation_date: ISO 8601 timestamp of key generation
            generation_log_path: Path to key generation ceremony log
            parent_key_id: Parent key ID (for signing keys, the root key that attested it)
        
        Raises:
            KeyRegistryError: If key already exists or registration fails
        """
        if key_id in self._registry["keys"]:
            raise KeyRegistryError(f"Key already registered: {key_id}")
        
        key_entry = {
            "key_id": key_id,
            "key_type": key_type.value,
            "public_key_fingerprint": public_key_fingerprint,
            "status": KeyStatus.ACTIVE.value,
            "generation_date": generation_date,
            "generation_log_path": str(generation_log_path) if generation_log_path else None,
            "parent_key_id": parent_key_id,
            "rotation_date": None,
            "revocation_date": None,
            "compromise_date": None,
            "registered_at": datetime.now(timezone.utc).isoformat()
        }
        
        self._registry["keys"][key_id] = key_entry
        self._save_registry()
    
    def get_key(self, key_id: str) -> Optional[Dict[str, Any]]:
        """
        Get key entry by ID.
        
        Args:
            key_id: Key identifier
        
        Returns:
            Key entry dictionary, or None if not found
        """
        return self._registry["keys"].get(key_id)
    
    def is_key_active(self, key_id: str) -> bool:
        """
        Check if key is active (not revoked, rotated, or compromised).
        
        Args:
            key_id: Key identifier
        
        Returns:
            True if key is active, False otherwise
        
        Raises:
            KeyRegistryError: If key not found
        """
        key_entry = self.get_key(key_id)
        if not key_entry:
            raise KeyRegistryError(f"Key not found: {key_id}")
        
        status = KeyStatus(key_entry["status"])
        return status == KeyStatus.ACTIVE
    
    def revoke_key(
        self,
        key_id: str,
        reason: str,
        revocation_date: Optional[str] = None
    ) -> None:
        """
        Revoke a key.
        
        Args:
            key_id: Key identifier
            reason: Revocation reason
            revocation_date: ISO 8601 timestamp (defaults to now)
        
        Raises:
            KeyRegistryError: If key not found or already revoked
        """
        key_entry = self.get_key(key_id)
        if not key_entry:
            raise KeyRegistryError(f"Key not found: {key_id}")
        
        if key_entry["status"] == KeyStatus.REVOKED.value:
            raise KeyRegistryError(f"Key already revoked: {key_id}")
        
        revocation_date = revocation_date or datetime.now(timezone.utc).isoformat()
        key_entry["status"] = KeyStatus.REVOKED.value
        key_entry["revocation_date"] = revocation_date
        key_entry["revocation_reason"] = reason
        
        # Add to revocation list
        revocation_entry = {
            "key_id": key_id,
            "revocation_date": revocation_date,
            "reason": reason,
            "public_key_fingerprint": key_entry["public_key_fingerprint"]
        }
        self._registry["revocation_list"].append(revocation_entry)
        
        self._save_registry()
    
    def rotate_key(
        self,
        old_key_id: str,
        new_key_id: str,
        rotation_date: Optional[str] = None
    ) -> None:
        """
        Mark old key as rotated and register new key.
        
        Args:
            old_key_id: Old key identifier
            new_key_id: New key identifier
            rotation_date: ISO 8601 timestamp (defaults to now)
        
        Raises:
            KeyRegistryError: If old key not found or new key already exists
        """
        old_key_entry = self.get_key(old_key_id)
        if not old_key_entry:
            raise KeyRegistryError(f"Old key not found: {old_key_id}")
        
        if new_key_id in self._registry["keys"]:
            raise KeyRegistryError(f"New key already exists: {new_key_id}")
        
        rotation_date = rotation_date or datetime.now(timezone.utc).isoformat()
        old_key_entry["status"] = KeyStatus.ROTATED.value
        old_key_entry["rotation_date"] = rotation_date
        old_key_entry["rotated_to"] = new_key_id
        
        self._save_registry()
    
    def mark_compromised(
        self,
        key_id: str,
        compromise_date: Optional[str] = None
    ) -> None:
        """
        Mark key as compromised.
        
        Args:
            key_id: Key identifier
            compromise_date: ISO 8601 timestamp (defaults to now)
        
        Raises:
            KeyRegistryError: If key not found
        """
        key_entry = self.get_key(key_id)
        if not key_entry:
            raise KeyRegistryError(f"Key not found: {key_id}")
        
        compromise_date = compromise_date or datetime.now(timezone.utc).isoformat()
        key_entry["status"] = KeyStatus.COMPROMISED.value
        key_entry["compromise_date"] = compromise_date
        
        # Automatically revoke compromised keys
        self.revoke_key(key_id, "Key compromise detected", compromise_date)
        
        self._save_registry()
    
    def get_revocation_list(self) -> List[Dict[str, Any]]:
        """
        Get certificate revocation list (CRL).
        
        Returns:
            List of revoked key entries
        """
        return self._registry["revocation_list"].copy()
    
    def is_revoked(self, key_id: str) -> bool:
        """
        Check if key is in revocation list.
        
        Args:
            key_id: Key identifier
        
        Returns:
            True if key is revoked, False otherwise
        """
        for entry in self._registry["revocation_list"]:
            if entry["key_id"] == key_id:
                return True
        return False
