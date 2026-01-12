#!/usr/bin/env python3
"""
RansomEye Alert Policy - Policy API
AUTHORITATIVE: Single API for policy bundle operations with audit ledger integration
"""

import sys
from pathlib import Path
from typing import Dict, Any
import uuid
from datetime import datetime, timezone

# Add audit-ledger to path
_audit_ledger_dir = Path(__file__).parent.parent.parent / "audit-ledger"
if str(_audit_ledger_dir) not in sys.path:
    sys.path.insert(0, str(_audit_ledger_dir))

# Import audit ledger components
import importlib.util

_store_spec = importlib.util.spec_from_file_location("audit_ledger_storage", _audit_ledger_dir / "storage" / "append_only_store.py")
_store_module = importlib.util.module_from_spec(_store_spec)
_store_spec.loader.exec_module(_store_module)
AppendOnlyStore = _store_module.AppendOnlyStore
LedgerWriter = _store_module.LedgerWriter

_key_manager_spec = importlib.util.spec_from_file_location("audit_ledger_key_manager", _audit_ledger_dir / "crypto" / "key_manager.py")
_key_manager_module = importlib.util.module_from_spec(_key_manager_spec)
_key_manager_spec.loader.exec_module(_key_manager_module)
KeyManager = _key_manager_module.KeyManager

_signer_spec = importlib.util.spec_from_file_location("audit_ledger_signer", _audit_ledger_dir / "crypto" / "signer.py")
_signer_module = importlib.util.module_from_spec(_signer_spec)
_signer_spec.loader.exec_module(_signer_module)
Signer = _signer_module.Signer

# Import policy components
_policy_dir = Path(__file__).parent.parent
if str(_policy_dir) not in sys.path:
    sys.path.insert(0, str(_policy_dir))

_bundle_loader_spec = importlib.util.spec_from_file_location("bundle_loader", _policy_dir / "engine" / "bundle_loader.py")
_bundle_loader_module = importlib.util.module_from_spec(_bundle_loader_spec)
_bundle_loader_spec.loader.exec_module(_bundle_loader_module)
BundleLoader = _bundle_loader_module.BundleLoader

_router_spec = importlib.util.spec_from_file_location("router", _policy_dir / "engine" / "router.py")
_router_module = importlib.util.module_from_spec(_router_spec)
_router_spec.loader.exec_module(_router_module)
Router = _router_module.Router


class PolicyAPIError(Exception):
    """Base exception for policy API errors."""
    pass


class PolicyAPI:
    """
    Single API for policy bundle operations.
    
    All operations:
    - Load bundles (hot-reload, atomic)
    - Route alerts (deterministic, high-throughput)
    - Emit audit ledger entries (every decision)
    """
    
    def __init__(
        self,
        public_keys_dir: Path,
        ledger_path: Path,
        ledger_key_dir: Path
    ):
        """
        Initialize policy API.
        
        Args:
            public_keys_dir: Directory containing public keys for verification
            ledger_path: Path to audit ledger file
            ledger_key_dir: Directory containing ledger signing keys
        """
        self.bundle_loader = BundleLoader(public_keys_dir)
        self.router = Router(self.bundle_loader)
        
        # Initialize audit ledger
        try:
            ledger_store = AppendOnlyStore(ledger_path, read_only=False)
            ledger_key_manager = KeyManager(ledger_key_dir)
            ledger_private_key, ledger_public_key, ledger_key_id = ledger_key_manager.get_or_create_keypair()
            ledger_signer = Signer(ledger_private_key, ledger_key_id)
            self.ledger_writer = LedgerWriter(ledger_store, ledger_signer)
        except Exception as e:
            raise PolicyAPIError(f"Failed to initialize audit ledger: {e}") from e
    
    def load_bundle(self, bundle_path: Path) -> Dict[str, Any]:
        """
        Load policy bundle.
        
        Process:
        1. Load and validate bundle
        2. Hot-reload atomically
        3. Emit audit ledger entry
        
        Args:
            bundle_path: Path to bundle file
        
        Returns:
            Loaded bundle dictionary
        
        Raises:
            PolicyAPIError: If loading fails
        """
        # Load bundle (hot-reload)
        success = self.bundle_loader.hot_reload(bundle_path)
        
        if not success:
            raise PolicyAPIError("Bundle hot-reload failed (old bundle remains active)")
        
        bundle = self.bundle_loader.get_current_bundle()
        
        # Emit audit ledger entry
        try:
            self.ledger_writer.create_entry(
                component='alert-policy',
                component_instance_id='policy-engine',
                action_type='policy_bundle_loaded',
                subject={'type': 'policy_bundle', 'id': bundle.get('bundle_id', '')},
                actor={'type': 'system', 'identifier': 'policy-engine'},
                payload={
                    'bundle_version': bundle.get('bundle_version', ''),
                    'authority_scope': bundle.get('authority_scope', ''),
                    'rule_count': len(bundle.get('rules', []))
                }
            )
        except Exception as e:
            raise PolicyAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return bundle
    
    def route_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route alert based on policy rules.
        
        Process:
        1. Route alert
        2. Emit audit ledger entry
        3. Return routing decision
        
        Args:
            alert: Alert dictionary
        
        Returns:
            Routing decision dictionary
        
        Raises:
            PolicyAPIError: If routing fails
        """
        # Route alert
        decision = self.router.route_alert(alert)
        
        # Emit audit ledger entry
        try:
            ledger_entry = self.ledger_writer.create_entry(
                component='alert-policy',
                component_instance_id='policy-engine',
                action_type='routing_decision',
                subject={'type': 'alert', 'id': decision.get('alert_id', '')},
                actor={'type': 'system', 'identifier': 'policy-engine'},
                payload={
                    'decision_id': decision.get('decision_id', ''),
                    'rule_id': decision.get('rule_id', ''),
                    'routing_action': decision.get('routing_action', ''),
                    'required_authority': decision.get('required_authority', '')
                }
            )
            decision['ledger_entry_id'] = ledger_entry.get('ledger_entry_id', '')
        except Exception as e:
            raise PolicyAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return decision
