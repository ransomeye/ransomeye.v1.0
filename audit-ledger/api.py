#!/usr/bin/env python3
"""
RansomEye Audit Ledger - Integration API
AUTHORITATIVE: Single, minimal append API for audit ledger integration
"""

from pathlib import Path
from typing import Dict, Any, Optional
import uuid
from datetime import datetime, timezone
import sys

# Add current directory to path for imports
_audit_ledger_dir = Path(__file__).parent
if str(_audit_ledger_dir) not in sys.path:
    sys.path.insert(0, str(_audit_ledger_dir))

from storage.append_only_store import AppendOnlyStore, AppendError, ReadOnlyError, LedgerWriter
from crypto.key_manager import KeyManager, KeyManagerError
from crypto.signer import Signer, SignerError


class AuditLedgerError(Exception):
    """Base exception for audit ledger API errors."""
    pass


class AuditLedger:
    """
    Single, minimal API for appending entries to the audit ledger.
    
    This is the integration point for all RansomEye components.
    Components call append() to record security-relevant actions.
    """
    
    def __init__(self, ledger_path: Path, key_dir: Path):
        """
        Initialize audit ledger.
        
        Args:
            ledger_path: Path to ledger file
            key_dir: Directory containing signing keys
        """
        self.ledger_path = ledger_path
        self.key_dir = key_dir
        
        # Initialize store
        self.store = AppendOnlyStore(ledger_path, read_only=False)
        
        # Initialize key manager and signer
        try:
            key_manager = KeyManager(key_dir)
            private_key, public_key, key_id = key_manager.get_or_create_keypair()
            self.signer = Signer(private_key, key_id)
        except KeyManagerError as e:
            raise AuditLedgerError(f"Failed to initialize key manager: {e}") from e
        except SignerError as e:
            raise AuditLedgerError(f"Failed to initialize signer: {e}") from e
        
        # Initialize writer
        self.writer = LedgerWriter(self.store, self.signer)
    
    def append(
        self,
        component: str,
        component_instance_id: str,
        action_type: str,
        subject: Dict[str, str],
        actor: Dict[str, str],
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Append an entry to the audit ledger.
        
        This is the single, minimal API for all components.
        
        Args:
            component: Component name (core, linux-agent, windows-agent, dpi-probe, etc.)
            component_instance_id: Component instance identifier (hostname, service ID, etc.)
            action_type: Action type (installer_install, service_start, policy_enforcement, etc.)
            subject: Subject dictionary with 'type' and 'id' keys
            actor: Actor dictionary with 'type' and 'identifier' keys
            payload: Action-specific payload data
        
        Returns:
            Complete ledger entry dictionary
        
        Raises:
            AuditLedgerError: If append operation fails
        """
        try:
            entry = self.writer.create_entry(
                component=component,
                component_instance_id=component_instance_id,
                action_type=action_type,
                subject=subject,
                actor=actor,
                payload=payload
            )
            return entry
        except AppendError as e:
            raise AuditLedgerError(f"Failed to append entry: {e}") from e
        except Exception as e:
            raise AuditLedgerError(f"Unexpected error appending entry: {e}") from e


# Global ledger instance (initialized on first use)
_ledger_instance: Optional[AuditLedger] = None


def get_ledger(ledger_path: Optional[Path] = None, key_dir: Optional[Path] = None) -> AuditLedger:
    """
    Get or create global audit ledger instance.
    
    Args:
        ledger_path: Path to ledger file (required on first call)
        key_dir: Directory containing signing keys (required on first call)
    
    Returns:
        AuditLedger instance
    """
    global _ledger_instance
    
    if _ledger_instance is None:
        if ledger_path is None or key_dir is None:
            raise AuditLedgerError("ledger_path and key_dir must be provided on first call")
        _ledger_instance = AuditLedger(ledger_path, key_dir)
    
    return _ledger_instance


def append_entry(
    component: str,
    component_instance_id: str,
    action_type: str,
    subject: Dict[str, str],
    actor: Dict[str, str],
    payload: Dict[str, Any],
    ledger_path: Optional[Path] = None,
    key_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Convenience function for appending an entry.
    
    Args:
        component: Component name
        component_instance_id: Component instance identifier
        action_type: Action type
        subject: Subject dictionary
        actor: Actor dictionary
        payload: Payload dictionary
        ledger_path: Path to ledger file (required on first call)
        key_dir: Directory containing signing keys (required on first call)
    
    Returns:
        Complete ledger entry dictionary
    """
    ledger = get_ledger(ledger_path, key_dir)
    return ledger.append(
        component=component,
        component_instance_id=component_instance_id,
        action_type=action_type,
        subject=subject,
        actor=actor,
        payload=payload
    )
