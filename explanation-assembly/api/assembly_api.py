#!/usr/bin/env python3
"""
RansomEye Explanation Assembly Engine - Assembly API
AUTHORITATIVE: API for assembling explanations into audience-specific views
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

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

# Import assembly engine components
_assembly_dir = Path(__file__).parent.parent
if str(_assembly_dir) not in sys.path:
    sys.path.insert(0, str(_assembly_dir))

_assembly_engine_spec = importlib.util.spec_from_file_location("assembly_engine", _assembly_dir / "engine" / "assembly_engine.py")
_assembly_engine_module = importlib.util.module_from_spec(_assembly_engine_spec)
_assembly_engine_spec.loader.exec_module(_assembly_engine_module)
AssemblyEngine = _assembly_engine_module.AssemblyEngine

_assembly_hasher_spec = importlib.util.spec_from_file_location("assembly_hasher", _assembly_dir / "engine" / "assembly_hasher.py")
_assembly_hasher_module = importlib.util.module_from_spec(_assembly_hasher_spec)
_assembly_hasher_spec.loader.exec_module(_assembly_hasher_module)
AssemblyHasher = _assembly_hasher_module.AssemblyHasher

_assembly_store_spec = importlib.util.spec_from_file_location("assembly_store", _assembly_dir / "storage" / "assembly_store.py")
_assembly_store_module = importlib.util.module_from_spec(_assembly_store_spec)
_assembly_store_spec.loader.exec_module(_assembly_store_module)
AssemblyStore = _assembly_store_module.AssemblyStore


class AssemblyAPIError(Exception):
    """Base exception for assembly API errors."""
    pass


class AssemblyAPI:
    """
    API for assembling explanations into audience-specific views.
    
    All operations:
    - Read-only access to all upstream systems
    - Write ONLY to assembly_store
    - Emit audit ledger entries
    - Never modify source explanations
    """
    
    def __init__(
        self,
        store_path: Path,
        ledger_path: Path,
        ledger_key_dir: Path
    ):
        """
        Initialize assembly API.
        
        Args:
            store_path: Path to assembly store file
            ledger_path: Path to audit ledger file
            ledger_key_dir: Directory containing ledger signing keys
        """
        self.store = AssemblyStore(store_path)
        self.assembly_engine = AssemblyEngine()
        self.assembly_hasher = AssemblyHasher()
        
        # Initialize audit ledger
        try:
            ledger_store = AppendOnlyStore(ledger_path, read_only=False)
            ledger_key_manager = KeyManager(ledger_key_dir)
            ledger_private_key, ledger_public_key, ledger_key_id = ledger_key_manager.get_or_create_keypair()
            ledger_signer = Signer(ledger_private_key, ledger_key_id)
            self.ledger_writer = LedgerWriter(ledger_store, ledger_signer)
        except Exception as e:
            raise AssemblyAPIError(f"Failed to initialize audit ledger: {e}") from e
    
    def assemble_incident_explanation(
        self,
        incident_id: str,
        view_type: str,
        source_explanation_bundle_ids: List[str],
        source_alert_ids: List[str],
        source_context_block_ids: List[str],
        source_risk_ids: List[str],
        source_content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assemble incident explanation into audience-specific view.
        
        Args:
            incident_id: Incident identifier
            view_type: View type (SOC_ANALYST, INCIDENT_COMMANDER, EXECUTIVE, REGULATOR)
            source_explanation_bundle_ids: SEE bundle identifiers
            source_alert_ids: Alert identifiers
            source_context_block_ids: Alert context block identifiers
            source_risk_ids: Risk score identifiers
            source_content: Dictionary of source content (read-only references)
        
        Returns:
            Assembled explanation dictionary
        """
        # Assemble explanation
        try:
            assembled_explanation = self.assembly_engine.assemble_explanation(
                incident_id=incident_id,
                view_type=view_type,
                source_explanation_bundle_ids=source_explanation_bundle_ids,
                source_alert_ids=source_alert_ids,
                source_context_block_ids=source_context_block_ids,
                source_risk_ids=source_risk_ids,
                source_content=source_content
            )
        except Exception as e:
            raise AssemblyAPIError(f"Failed to assemble explanation: {e}") from e
        
        # Compute integrity hash
        integrity_hash = self.assembly_hasher.hash_assembled_explanation(assembled_explanation)
        assembled_explanation['integrity_hash'] = integrity_hash
        
        # Store assembled explanation (immutable)
        try:
            self.store.store_assembly(assembled_explanation)
        except Exception as e:
            raise AssemblyAPIError(f"Failed to store assembled explanation: {e}") from e
        
        # Emit audit ledger entry
        try:
            self.ledger_writer.create_entry(
                component='explanation-assembly',
                component_instance_id='assembly-engine',
                action_type='EXPLANATION_ASSEMBLED',
                subject={'type': 'incident', 'id': incident_id},
                actor={'type': 'system', 'identifier': 'explanation-assembly'},
                payload={
                    'assembled_explanation_id': assembled_explanation.get('assembled_explanation_id', ''),
                    'view_type': view_type,
                    'source_explanation_bundle_ids': source_explanation_bundle_ids,
                    'source_alert_ids': source_alert_ids,
                    'source_context_block_ids': source_context_block_ids,
                    'source_risk_ids': source_risk_ids,
                    'integrity_hash': integrity_hash
                }
            )
        except Exception as e:
            raise AssemblyAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return assembled_explanation
    
    def get_assembled_explanation(self, assembled_explanation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get assembled explanation by ID.
        
        Args:
            assembled_explanation_id: Assembled explanation identifier
        
        Returns:
            Assembled explanation dictionary, or None if not found
        """
        assembly = self.store.get_assembly_by_id(assembled_explanation_id)
        
        if assembly:
            # Emit audit ledger entry
            try:
                self.ledger_writer.create_entry(
                    component='explanation-assembly',
                    component_instance_id='assembly-engine',
                    action_type='EXPLANATION_RETRIEVED',
                    subject={'type': 'assembled_explanation', 'id': assembled_explanation_id},
                    actor={'type': 'system', 'identifier': 'explanation-assembly'},
                    payload={
                        'assembled_explanation_id': assembled_explanation_id,
                        'incident_id': assembly.get('incident_id', ''),
                        'view_type': assembly.get('view_type', '')
                    }
                )
            except Exception as e:
                raise AssemblyAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return assembly
    
    def list_assembled_explanations(self, incident_id: str) -> List[Dict[str, Any]]:
        """
        List all assembled explanations for incident ID.
        
        Args:
            incident_id: Incident identifier
        
        Returns:
            List of assembled explanation dictionaries
        """
        return self.store.get_assemblies_by_incident_id(incident_id)
