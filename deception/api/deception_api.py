#!/usr/bin/env python3
"""
RansomEye Deception Framework - Deception API
AUTHORITATIVE: Single API for deception operations with audit ledger integration
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json

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

# Import deception components
_deception_dir = Path(__file__).parent.parent
if str(_deception_dir) not in sys.path:
    sys.path.insert(0, str(_deception_dir))

_decoy_registry_spec = importlib.util.spec_from_file_location("decoy_registry", _deception_dir / "engine" / "decoy_registry.py")
_decoy_registry_module = importlib.util.module_from_spec(_decoy_registry_spec)
_decoy_registry_spec.loader.exec_module(_decoy_registry_module)
DecoyRegistry = _decoy_registry_module.DecoyRegistry

_deployment_engine_spec = importlib.util.spec_from_file_location("deployment_engine", _deception_dir / "engine" / "deployment_engine.py")
_deployment_engine_module = importlib.util.module_from_spec(_deployment_engine_spec)
_deployment_engine_spec.loader.exec_module(_deployment_engine_module)
DeploymentEngine = _deployment_engine_module.DeploymentEngine

_interaction_collector_spec = importlib.util.spec_from_file_location("interaction_collector", _deception_dir / "engine" / "interaction_collector.py")
_interaction_collector_module = importlib.util.module_from_spec(_interaction_collector_spec)
_interaction_collector_spec.loader.exec_module(_interaction_collector_module)
InteractionCollector = _interaction_collector_module.InteractionCollector

_signal_builder_spec = importlib.util.spec_from_file_location("signal_builder", _deception_dir / "engine" / "signal_builder.py")
_signal_builder_module = importlib.util.module_from_spec(_signal_builder_spec)
_signal_builder_spec.loader.exec_module(_signal_builder_module)
SignalBuilder = _signal_builder_module.SignalBuilder


class DeceptionAPIError(Exception):
    """Base exception for deception API errors."""
    pass


class DeceptionAPI:
    """
    Single API for deception operations.
    
    All operations:
    - Register decoys (immutable)
    - Deploy decoys (explicit only)
    - Collect interactions (evidence-grade)
    - Build signals (high-confidence)
    - Emit audit ledger entries (every operation)
    """
    
    def __init__(
        self,
        decoys_store_path: Path,
        deployments_store_path: Path,
        interactions_store_path: Path,
        signals_store_path: Path,
        ledger_path: Path,
        ledger_key_dir: Path
    ):
        """
        Initialize deception API.
        
        Args:
            decoys_store_path: Path to decoys store
            deployments_store_path: Path to deployments store
            interactions_store_path: Path to interactions store
            signals_store_path: Path to signals store
            ledger_path: Path to audit ledger file
            ledger_key_dir: Directory containing ledger signing keys
        """
        self.decoy_registry = DecoyRegistry(decoys_store_path)
        self.deployment_engine = DeploymentEngine()
        self.interaction_collector = InteractionCollector()
        self.signal_builder = SignalBuilder()
        
        self.deployments_store_path = Path(deployments_store_path)
        self.deployments_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.interactions_store_path = Path(interactions_store_path)
        self.interactions_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.signals_store_path = Path(signals_store_path)
        self.signals_store_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize audit ledger
        try:
            ledger_store = AppendOnlyStore(ledger_path, read_only=False)
            ledger_key_manager = KeyManager(ledger_key_dir)
            ledger_private_key, ledger_public_key, ledger_key_id = ledger_key_manager.get_or_create_keypair()
            ledger_signer = Signer(ledger_private_key, ledger_key_id)
            self.ledger_writer = LedgerWriter(ledger_store, ledger_signer)
        except Exception as e:
            raise DeceptionAPIError(f"Failed to initialize audit ledger: {e}") from e
    
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
        # Register decoy
        decoy = self.decoy_registry.register_decoy(
            decoy_type=decoy_type,
            decoy_name=decoy_name,
            decoy_config=decoy_config,
            deployment_target=deployment_target
        )
        
        # Emit audit ledger entry
        try:
            self.ledger_writer.create_entry(
                component='deception',
                component_instance_id='deception',
                action_type='decoy_registered',
                subject={'type': 'decoy', 'id': decoy.get('decoy_id', '')},
                actor={'type': 'system', 'identifier': 'deception'},
                payload={
                    'decoy_id': decoy.get('decoy_id', ''),
                    'decoy_type': decoy_type,
                    'decoy_name': decoy_name
                }
            )
        except Exception as e:
            raise DeceptionAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return decoy
    
    def deploy_decoy(
        self,
        decoy_id: str,
        deployed_by: str
    ) -> Dict[str, Any]:
        """
        Deploy decoy.
        
        Args:
            decoy_id: Decoy identifier
            deployed_by: Entity deploying decoy
        
        Returns:
            Deployment record dictionary
        """
        # Get decoy
        decoy = self.decoy_registry.get_decoy(decoy_id)
        if not decoy:
            raise DeceptionAPIError(f"Decoy not found: {decoy_id}")
        
        # Deploy decoy
        deployment = self.deployment_engine.deploy_decoy(decoy, deployed_by)
        
        # Store deployment
        self._store_deployment(deployment)
        
        # Emit audit ledger entry
        try:
            ledger_entry = self.ledger_writer.create_entry(
                component='deception',
                component_instance_id='deception',
                action_type='decoy_deployed',
                subject={'type': 'decoy', 'id': decoy_id},
                actor={'type': 'system', 'identifier': 'deception'},
                payload={
                    'deployment_id': deployment.get('deployment_id', ''),
                    'decoy_id': decoy_id,
                    'deployment_status': deployment.get('deployment_status', '')
                }
            )
            deployment['ledger_entry_id'] = ledger_entry.get('ledger_entry_id', '')
        except Exception as e:
            raise DeceptionAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return deployment
    
    def collect_interaction(
        self,
        decoy_id: str,
        interaction_type: str,
        source_ip: str,
        source_host: str = '',
        source_process: str = '',
        evidence_reference: str = ''
    ) -> Dict[str, Any]:
        """
        Collect interaction with decoy.
        
        Args:
            decoy_id: Decoy identifier
            interaction_type: Type of interaction (auth_attempt, scan, access, command)
            source_ip: Source IP address
            source_host: Source hostname (optional)
            source_process: Source process identifier (optional)
            evidence_reference: Evidence reference identifier (optional)
        
        Returns:
            Interaction record dictionary
        """
        # Collect interaction
        interaction = self.interaction_collector.collect_interaction(
            decoy_id=decoy_id,
            interaction_type=interaction_type,
            source_ip=source_ip,
            source_host=source_host,
            source_process=source_process,
            evidence_reference=evidence_reference
        )
        
        # Store interaction
        self._store_interaction(interaction)
        
        # Emit audit ledger entry
        try:
            ledger_entry = self.ledger_writer.create_entry(
                component='deception',
                component_instance_id='deception',
                action_type='interaction_collected',
                subject={'type': 'decoy', 'id': decoy_id},
                actor={'type': 'system', 'identifier': 'deception'},
                payload={
                    'interaction_id': interaction.get('interaction_id', ''),
                    'interaction_type': interaction_type,
                    'source_ip': source_ip
                }
            )
            interaction['ledger_entry_id'] = ledger_entry.get('ledger_entry_id', '')
        except Exception as e:
            raise DeceptionAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return interaction
    
    def build_signal(
        self,
        decoy_id: str
    ) -> Dict[str, Any]:
        """
        Build high-confidence signal from decoy interactions.
        
        Args:
            decoy_id: Decoy identifier
        
        Returns:
            Signal dictionary
        """
        # Get decoy
        decoy = self.decoy_registry.get_decoy(decoy_id)
        if not decoy:
            raise DeceptionAPIError(f"Decoy not found: {decoy_id}")
        
        # Load interactions for decoy
        interactions = self._load_interactions(decoy_id)
        
        if not interactions:
            raise DeceptionAPIError(f"No interactions found for decoy: {decoy_id}")
        
        # Build signal
        signal = self.signal_builder.build_signal(interactions, decoy)
        
        # Store signal
        self._store_signal(signal)
        
        # Emit audit ledger entry
        try:
            self.ledger_writer.create_entry(
                component='deception',
                component_instance_id='deception',
                action_type='signal_built',
                subject={'type': 'decoy', 'id': decoy_id},
                actor={'type': 'system', 'identifier': 'deception'},
                payload={
                    'signal_id': signal.get('signal_id', ''),
                    'interaction_count': len(interactions)
                }
            )
        except Exception as e:
            raise DeceptionAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return signal
    
    def _load_interactions(self, decoy_id: str) -> List[Dict[str, Any]]:
        """Load interactions for decoy."""
        interactions = []
        
        if not self.interactions_store_path.exists():
            return interactions
        
        try:
            with open(self.interactions_store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    interaction = json.loads(line)
                    if interaction.get('decoy_id') == decoy_id:
                        interactions.append(interaction)
        except Exception:
            pass
        
        return interactions
    
    def _store_deployment(self, deployment: Dict[str, Any]) -> None:
        """Store deployment to file-based store."""
        try:
            deployment_json = json.dumps(deployment, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(self.deployments_store_path, 'a', encoding='utf-8') as f:
                f.write(deployment_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise DeceptionAPIError(f"Failed to store deployment: {e}") from e
    
    def _store_interaction(self, interaction: Dict[str, Any]) -> None:
        """Store interaction to file-based store."""
        try:
            interaction_json = json.dumps(interaction, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(self.interactions_store_path, 'a', encoding='utf-8') as f:
                f.write(interaction_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise DeceptionAPIError(f"Failed to store interaction: {e}") from e
    
    def _store_signal(self, signal: Dict[str, Any]) -> None:
        """Store signal to file-based store."""
        try:
            signal_json = json.dumps(signal, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(self.signals_store_path, 'a', encoding='utf-8') as f:
                f.write(signal_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise DeceptionAPIError(f"Failed to store signal: {e}") from e
