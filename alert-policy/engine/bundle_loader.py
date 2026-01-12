#!/usr/bin/env python3
"""
RansomEye Alert Policy - Bundle Loader
AUTHORITATIVE: Hot-reload, atomic bundle loading
"""

import json
import yaml
import sys
import importlib.util
from pathlib import Path
from typing import Dict, Any, Optional
import threading
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# Add parent directory to path for imports
_policy_dir = Path(__file__).parent.parent
if str(_policy_dir) not in sys.path:
    sys.path.insert(0, str(_policy_dir))

# Import crypto modules using importlib
_verifier_spec = importlib.util.spec_from_file_location("bundle_verifier", _policy_dir / "crypto" / "bundle_verifier.py")
_verifier_module = importlib.util.module_from_spec(_verifier_spec)
_verifier_spec.loader.exec_module(_verifier_module)
BundleVerifier = _verifier_module.BundleVerifier
VerificationError = _verifier_module.VerificationError


class BundleLoadError(Exception):
    """Base exception for bundle loading errors."""
    pass


class BundleLoader:
    """
    Hot-reload, atomic bundle loading.
    
    Properties:
    - Atomic: Reload is atomic (old bundle remains active until new bundle is valid)
    - Hot-reload: Supports hot-reload without downtime
    - No partial loading: Bundle must be complete and valid
    - Thread-safe: Safe for concurrent access
    """
    
    def __init__(self, public_keys_dir: Path):
        """
        Initialize bundle loader.
        
        Args:
            public_keys_dir: Directory containing public keys for verification
        """
        self.public_keys_dir = Path(public_keys_dir)
        self.public_keys_dir.mkdir(parents=True, exist_ok=True)
        self.current_bundle: Optional[Dict[str, Any]] = None
        self.bundle_lock = threading.Lock()
    
    def load_bundle(self, bundle_path: Path) -> Dict[str, Any]:
        """
        Load and validate policy bundle.
        
        Process:
        1. Load bundle (YAML or JSON)
        2. Validate schema
        3. Verify signature
        4. Validate rules (no priority ties, no ambiguity)
        5. Return validated bundle
        
        Args:
            bundle_path: Path to bundle file
        
        Returns:
            Validated bundle dictionary
        
        Raises:
            BundleLoadError: If loading or validation fails
        """
        # Load bundle file
        try:
            if bundle_path.suffix in ['.yaml', '.yml']:
                bundle = yaml.safe_load(bundle_path.read_text())
            else:
                bundle = json.loads(bundle_path.read_text())
        except Exception as e:
            raise BundleLoadError(f"Failed to load bundle file: {e}") from e
        
        # Validate schema (basic validation)
        self._validate_bundle_schema(bundle)
        
        # Verify signature
        self._verify_bundle_signature(bundle)
        
        # Validate rules
        self._validate_rules(bundle)
        
        return bundle
    
    def hot_reload(self, bundle_path: Path) -> bool:
        """
        Hot-reload bundle atomically.
        
        Process:
        1. Load and validate new bundle
        2. If valid, atomically replace current bundle
        3. If invalid, keep current bundle (no change)
        
        Args:
            bundle_path: Path to new bundle file
        
        Returns:
            True if reload succeeded, False if failed (old bundle remains active)
        """
        try:
            # Load and validate new bundle
            new_bundle = self.load_bundle(bundle_path)
            
            # Atomically replace current bundle
            with self.bundle_lock:
                self.current_bundle = new_bundle
            
            return True
        except Exception as e:
            # Reload failed, old bundle remains active
            return False
    
    def get_current_bundle(self) -> Optional[Dict[str, Any]]:
        """
        Get current active bundle.
        
        Returns:
            Current bundle dictionary, or None if no bundle loaded
        """
        with self.bundle_lock:
            return self.current_bundle
    
    def _validate_bundle_schema(self, bundle: Dict[str, Any]) -> None:
        """Validate bundle schema."""
        required_fields = ['bundle_id', 'bundle_version', 'authority_scope', 'created_at', 'created_by', 'rules', 'bundle_signature', 'bundle_key_id']
        for field in required_fields:
            if field not in bundle:
                raise BundleLoadError(f"Bundle missing required field: {field}")
        
        # Validate rules exist
        rules = bundle.get('rules', [])
        if not rules:
            raise BundleLoadError("Bundle must have at least one rule")
    
    def _verify_bundle_signature(self, bundle: Dict[str, Any]) -> None:
        """Verify bundle signature."""
        key_id = bundle.get('bundle_key_id', '')
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
            
            verifier = BundleVerifier(public_key)
            verifier.verify_bundle(bundle)
        except Exception as e:
            raise BundleLoadError(f"Bundle signature verification failed: {e}") from e
    
    def _validate_rules(self, bundle: Dict[str, Any]) -> None:
        """Validate rules (no priority ties, no ambiguity)."""
        rules = bundle.get('rules', [])
        
        # Check for priority ties
        priorities = [rule.get('priority', -1) for rule in rules]
        if len(priorities) != len(set(priorities)):
            raise BundleLoadError("Rules have duplicate priorities (ties not allowed)")
        
        # Validate each rule
        for rule in rules:
            self._validate_rule(rule)
    
    def _validate_rule(self, rule: Dict[str, Any]) -> None:
        """Validate single rule."""
        required_fields = ['rule_id', 'match_conditions', 'severity_thresholds', 'risk_score_thresholds', 'allowed_actions', 'required_authority', 'explanation_template_id', 'priority']
        for field in required_fields:
            if field not in rule:
                raise BundleLoadError(f"Rule missing required field: {field}")
        
        # Validate match conditions
        match_conditions = rule.get('match_conditions', {})
        if 'condition_type' not in match_conditions or 'conditions' not in match_conditions:
            raise BundleLoadError("Rule match_conditions must have condition_type and conditions")
        
        conditions = match_conditions.get('conditions', [])
        if not conditions:
            raise BundleLoadError("Rule must have at least one match condition")
        
        # Validate allowed actions
        allowed_actions = rule.get('allowed_actions', [])
        if not allowed_actions:
            raise BundleLoadError("Rule must have at least one allowed action")
