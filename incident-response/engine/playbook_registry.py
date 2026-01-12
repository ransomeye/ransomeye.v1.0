#!/usr/bin/env python3
"""
RansomEye Incident Response - Playbook Registry
AUTHORITATIVE: Immutable playbook storage and retrieval
"""

import json
import sys
import importlib.util
from pathlib import Path
from typing import Dict, Any, List, Optional
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# Add parent directory to path for imports
_ir_dir = Path(__file__).parent.parent
if str(_ir_dir) not in sys.path:
    sys.path.insert(0, str(_ir_dir))

# Import crypto modules using importlib
_verifier_spec = importlib.util.spec_from_file_location("playbook_verifier", _ir_dir / "crypto" / "playbook_verifier.py")
_verifier_module = importlib.util.module_from_spec(_verifier_spec)
_verifier_spec.loader.exec_module(_verifier_module)
PlaybookVerifier = _verifier_module.PlaybookVerifier
VerificationError = _verifier_module.VerificationError


class RegistryError(Exception):
    """Base exception for registry errors."""
    pass


class PlaybookNotFoundError(RegistryError):
    """Raised when playbook is not found."""
    pass


class PlaybookRegistry:
    """
    Immutable playbook storage and retrieval.
    
    Properties:
    - Immutable: Playbooks cannot be modified after registration
    - Signed: All playbooks must be signed
    - Verified: All playbooks are verified on registration
    - Deterministic: Same playbook always produces same storage
    """
    
    def __init__(self, registry_path: Path, public_keys_dir: Path):
        """
        Initialize playbook registry.
        
        Args:
            registry_path: Path to playbook registry file (JSON lines format)
            public_keys_dir: Directory containing public keys for verification
        """
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.public_keys_dir = Path(public_keys_dir)
        self.public_keys_dir.mkdir(parents=True, exist_ok=True)
    
    def register_playbook(self, playbook: Dict[str, Any]) -> None:
        """
        Register playbook in registry.
        
        Process:
        1. Verify playbook signature
        2. Validate playbook structure
        3. Store playbook (immutable)
        
        Args:
            playbook: Playbook dictionary
        
        Raises:
            RegistryError: If registration fails
            VerificationError: If signature verification fails
        """
        # Verify playbook signature
        self._verify_playbook_signature(playbook)
        
        # Validate playbook structure
        self._validate_playbook(playbook)
        
        # Store playbook
        try:
            playbook_json = json.dumps(playbook, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(self.registry_path, 'a', encoding='utf-8') as f:
                f.write(playbook_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise RegistryError(f"Failed to register playbook: {e}") from e
    
    def get_playbook(self, playbook_id: str) -> Optional[Dict[str, Any]]:
        """
        Get playbook by ID.
        
        Args:
            playbook_id: Playbook identifier
        
        Returns:
            Playbook dictionary, or None if not found
        """
        if not self.registry_path.exists():
            return None
        
        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    playbook = json.loads(line)
                    if playbook.get('playbook_id') == playbook_id:
                        return playbook
        except Exception:
            pass
        
        return None
    
    def get_all_playbooks(self) -> List[Dict[str, Any]]:
        """
        Get all playbooks in registry.
        
        Returns:
            List of playbook dictionaries
        """
        playbooks = []
        
        if not self.registry_path.exists():
            return playbooks
        
        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    playbooks.append(json.loads(line))
        except Exception:
            pass
        
        return playbooks
    
    def _verify_playbook_signature(self, playbook: Dict[str, Any]) -> None:
        """Verify playbook signature."""
        key_id = playbook.get('playbook_key_id', '')
        public_key_path = self.public_keys_dir / f"{key_id}_public.pem"
        
        if not public_key_path.exists():
            raise VerificationError(f"Public key not found: {key_id}")
        
        try:
            public_key_data = public_key_path.read_bytes()
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            public_key = serialization.load_pem_public_key(
                public_key_data,
                backend=default_backend()
            )
            
            verifier = PlaybookVerifier(public_key)
            verifier.verify_playbook(playbook)
        except Exception as e:
            raise VerificationError(f"Playbook signature verification failed: {e}") from e
    
    def _validate_playbook(self, playbook: Dict[str, Any]) -> None:
        """Validate playbook structure."""
        # Check required fields
        required_fields = ['playbook_id', 'playbook_name', 'playbook_version', 'scope', 'steps']
        for field in required_fields:
            if field not in playbook:
                raise RegistryError(f"Playbook missing required field: {field}")
        
        # Validate steps
        steps = playbook.get('steps', [])
        if not steps:
            raise RegistryError("Playbook must have at least one step")
        
        # Validate step order (must be sequential, starting from 0)
        step_orders = [step.get('step_order', -1) for step in steps]
        expected_orders = list(range(len(steps)))
        if sorted(step_orders) != expected_orders:
            raise RegistryError("Playbook steps must be sequentially ordered starting from 0")
        
        # Validate step types (frozen enum)
        valid_step_types = ['isolate_host', 'block_ip', 'disable_account', 'snapshot_memory', 'snapshot_disk', 'notify_human']
        for step in steps:
            step_type = step.get('step_type', '')
            if step_type not in valid_step_types:
                raise RegistryError(f"Invalid step type: {step_type}")
