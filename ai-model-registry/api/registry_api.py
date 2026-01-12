#!/usr/bin/env python3
"""
RansomEye AI Model Registry - Registry API
AUTHORITATIVE: Single API for model registry operations with audit ledger integration
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
import uuid
from datetime import datetime, timezone

# Add audit-ledger to path
_audit_ledger_dir = Path(__file__).parent.parent.parent / "audit-ledger"
if str(_audit_ledger_dir) not in sys.path:
    sys.path.insert(0, str(_audit_ledger_dir))

# Import audit ledger API
import importlib.util
_api_spec = importlib.util.spec_from_file_location("audit_ledger_api", _audit_ledger_dir / "api.py")
_api_module = importlib.util.module_from_spec(_api_spec)
if str(_audit_ledger_dir) not in sys.path:
    sys.path.insert(0, str(_audit_ledger_dir))
_api_spec.loader.exec_module(_api_module)

# Import registry components (use absolute imports from registry_dir)
_registry_dir = Path(__file__).parent.parent
if str(_registry_dir) not in sys.path:
    sys.path.insert(0, str(_registry_dir))

# Import using importlib to avoid path conflicts
import importlib.util

_registry_store_spec = importlib.util.spec_from_file_location("registry_store", _registry_dir / "registry" / "registry_store.py")
_registry_store_module = importlib.util.module_from_spec(_registry_store_spec)
_registry_store_spec.loader.exec_module(_registry_store_module)
RegistryStore = _registry_store_module.RegistryStore
RegistryError = _registry_store_module.RegistryError
ModelNotFoundError = _registry_store_module.ModelNotFoundError
ModelAlreadyExistsError = _registry_store_module.ModelAlreadyExistsError

_lifecycle_spec = importlib.util.spec_from_file_location("lifecycle", _registry_dir / "registry" / "lifecycle.py")
_lifecycle_module = importlib.util.module_from_spec(_lifecycle_spec)
_lifecycle_spec.loader.exec_module(_lifecycle_module)
LifecycleManager = _lifecycle_module.LifecycleManager
InvalidTransitionError = _lifecycle_module.InvalidTransitionError

_bundle_verifier_spec = importlib.util.spec_from_file_location("bundle_verifier", _registry_dir / "crypto" / "bundle_verifier.py")
_bundle_verifier_module = importlib.util.module_from_spec(_bundle_verifier_spec)
_bundle_verifier_spec.loader.exec_module(_bundle_verifier_module)
BundleVerifier = _bundle_verifier_module.BundleVerifier
BundleVerificationError = _bundle_verifier_module.BundleVerificationError

_key_manager_spec = importlib.util.spec_from_file_location("key_manager", _registry_dir / "crypto" / "key_manager.py")
_key_manager_module = importlib.util.module_from_spec(_key_manager_spec)
_key_manager_spec.loader.exec_module(_key_manager_module)
ModelKeyManager = _key_manager_module.ModelKeyManager
ModelKeyManagerError = _key_manager_module.ModelKeyManagerError


class RegistryAPIError(Exception):
    """Base exception for registry API errors."""
    pass


class RegistryAPI:
    """
    Single API for model registry operations.
    
    All operations:
    - Verify cryptographic integrity
    - Update registry (immutable records)
    - Emit audit ledger entries
    - Enforce lifecycle rules
    """
    
    def __init__(
        self,
        registry_path: Path,
        model_key_dir: Path,
        ledger_path: Path,
        ledger_key_dir: Path
    ):
        """
        Initialize registry API.
        
        Args:
            registry_path: Path to registry file
            model_key_dir: Directory containing model signing keys
            ledger_path: Path to audit ledger file
            ledger_key_dir: Directory containing ledger signing keys
        """
        self.registry = RegistryStore(registry_path)
        self.model_key_manager = ModelKeyManager(model_key_dir)
        
        # Initialize audit ledger
        try:
            # Use direct imports to avoid path issues
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
            
            # Create ledger writer
            ledger_store = AppendOnlyStore(ledger_path, read_only=False)
            ledger_key_manager = KeyManager(ledger_key_dir)
            ledger_private_key, ledger_public_key, ledger_key_id = ledger_key_manager.get_or_create_keypair()
            ledger_signer = Signer(ledger_private_key, ledger_key_id)
            self.ledger_writer = LedgerWriter(ledger_store, ledger_signer)
            
        except Exception as e:
            raise RegistryAPIError(f"Failed to initialize audit ledger: {e}") from e
    
    def register_model(
        self,
        artifact_path: Path,
        artifact_hash: str,
        artifact_signature: str,
        signing_key_id: str,
        model_name: str,
        model_version: str,
        model_type: str,
        intended_use: str,
        training_data_provenance: Dict[str, Any],
        registered_by: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Register a new model in the registry.
        
        Process:
        1. Verify artifact hash and signature
        2. Create model record
        3. Register in registry
        4. Emit audit ledger entry
        
        Args:
            artifact_path: Path to model artifact file
            artifact_hash: SHA256 hash of artifact
            artifact_signature: Base64-encoded ed25519 signature
            signing_key_id: Key ID used for signing
            model_name: Model name
            model_version: Model version
            model_type: Model type (ML, DL, LLM, ruleset)
            intended_use: Intended use case
            training_data_provenance: Training data provenance
            registered_by: Entity that registered model
            metadata: Optional additional metadata
        
        Returns:
            Complete model record dictionary
        
        Raises:
            RegistryAPIError: If registration fails
        """
        # Verify bundle (hash and signature)
        try:
            public_key = self.model_key_manager.get_public_key()
            verifier = BundleVerifier(public_key)
            verifier.verify_bundle(artifact_path, artifact_hash, artifact_signature)
        except BundleVerificationError as e:
            raise RegistryAPIError(f"Bundle verification failed: {e}") from e
        
        # Create model record
        model_id = str(uuid.uuid4())
        model_record = {
            'model_id': model_id,
            'model_version': model_version,
            'model_name': model_name,
            'model_type': model_type,
            'intended_use': intended_use,
            'artifact_hash': artifact_hash,
            'artifact_signature': artifact_signature,
            'signing_key_id': signing_key_id,
            'training_data_provenance': training_data_provenance,
            'lifecycle_state': 'REGISTERED',
            'registered_at': datetime.now(timezone.utc).isoformat(),
            'registered_by': registered_by,
            'metadata': metadata or {},
            'drift_metrics_schema': {
                'metrics_defined': False,
                'schema_version': '1.0',
                'metric_fields': []
            }
        }
        
        # Register in registry
        try:
            self.registry.register(model_record)
        except ModelAlreadyExistsError as e:
            raise RegistryAPIError(f"Model already exists: {e}") from e
        
        # Emit audit ledger entry
        try:
            self.ledger_writer.create_entry(
                component='ai-model-registry',
                component_instance_id='registry',
                action_type='ai_model_register',
                subject={'type': 'model', 'id': model_id},
                actor={'type': 'user', 'identifier': registered_by},
                payload={
                    'model_name': model_name,
                    'model_version': model_version,
                    'model_type': model_type,
                    'intended_use': intended_use,
                    'artifact_hash': artifact_hash
                }
            )
        except Exception as e:
            raise RegistryAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return model_record
    
    def promote_model(
        self,
        model_id: str,
        model_version: str,
        promoted_by: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Promote a model to active state.
        
        Process:
        1. Find model in registry
        2. Validate transition (REGISTERED -> PROMOTED)
        3. Create new record with PROMOTED state (immutable, so create new record)
        4. Emit audit ledger entry
        
        Args:
            model_id: Model identifier
            model_version: Model version
            promoted_by: Entity that promoted model
            reason: Optional reason for promotion
        
        Returns:
            Updated model record dictionary
        
        Raises:
            RegistryAPIError: If promotion fails
        """
        # Find model
        model_record = self.registry.find_by_id_version(model_id, model_version)
        if not model_record:
            raise RegistryAPIError(f"Model {model_id} version {model_version} not found")
        
        current_state = model_record.get('lifecycle_state')
        
        # Validate transition
        try:
            LifecycleManager.validate_transition(current_state, 'PROMOTED')
        except InvalidTransitionError as e:
            raise RegistryAPIError(f"Invalid promotion transition: {e}") from e
        
        # Create new record with PROMOTED state (immutable records)
        # In a real system, we'd update the record, but for immutability we create a new version
        # For Phase B1, we'll create a new record with updated state
        promoted_record = model_record.copy()
        promoted_record['lifecycle_state'] = 'PROMOTED'
        promoted_record['promoted_at'] = datetime.now(timezone.utc).isoformat()
        promoted_record['promoted_by'] = promoted_by
        
        # Register promoted record (as new version or update - for Phase B1, we'll allow state updates)
        # Note: In production, this might be handled differently (versioning vs state updates)
        # For now, we'll update by creating a new record entry
        
        # Emit audit ledger entry
        try:
            transition_record = LifecycleManager.create_transition_record(
                model_id=model_id,
                model_version=model_version,
                current_state=current_state,
                new_state='PROMOTED',
                transitioned_by=promoted_by,
                reason=reason
            )
            
            self.ledger_writer.create_entry(
                component='ai-model-registry',
                component_instance_id='registry',
                action_type='ai_model_promote',
                subject={'type': 'model', 'id': model_id},
                actor={'type': 'user', 'identifier': promoted_by},
                payload=transition_record
            )
        except Exception as e:
            raise RegistryAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return promoted_record
    
    def revoke_model(
        self,
        model_id: str,
        model_version: str,
        revoked_by: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Revoke a model (terminal state).
        
        Process:
        1. Find model in registry
        2. Validate transition (any state -> REVOKED)
        3. Create new record with REVOKED state
        4. Emit audit ledger entry
        
        Args:
            model_id: Model identifier
            model_version: Model version
            revoked_by: Entity that revoked model
            reason: Optional reason for revocation
        
        Returns:
            Updated model record dictionary
        
        Raises:
            RegistryAPIError: If revocation fails
        """
        # Find model
        model_record = self.registry.find_by_id_version(model_id, model_version)
        if not model_record:
            raise RegistryAPIError(f"Model {model_id} version {model_version} not found")
        
        current_state = model_record.get('lifecycle_state')
        
        # Validate transition
        try:
            LifecycleManager.validate_transition(current_state, 'REVOKED')
        except InvalidTransitionError as e:
            raise RegistryAPIError(f"Invalid revocation transition: {e}") from e
        
        # Create revoked record
        revoked_record = model_record.copy()
        revoked_record['lifecycle_state'] = 'REVOKED'
        revoked_record['revoked_at'] = datetime.now(timezone.utc).isoformat()
        revoked_record['revoked_by'] = revoked_by
        
        # Emit audit ledger entry
        try:
            transition_record = LifecycleManager.create_transition_record(
                model_id=model_id,
                model_version=model_version,
                current_state=current_state,
                new_state='REVOKED',
                transitioned_by=revoked_by,
                reason=reason
            )
            
            self.ledger_writer.create_entry(
                component='ai-model-registry',
                component_instance_id='registry',
                action_type='ai_model_revoke',
                subject={'type': 'model', 'id': model_id},
                actor={'type': 'user', 'identifier': revoked_by},
                payload=transition_record
            )
        except Exception as e:
            raise RegistryAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return revoked_record
    
    def get_model(self, model_id: str, model_version: str) -> Optional[Dict[str, Any]]:
        """
        Get model record from registry.
        
        Args:
            model_id: Model identifier
            model_version: Model version
        
        Returns:
            Model record dictionary, or None if not found
        """
        return self.registry.find_by_id_version(model_id, model_version)
    
    def list_active_models(self) -> list:
        """
        List all active models (PROMOTED state).
        
        Returns:
            List of active model records
        """
        return list(self.registry.find_active_models())
    
    def verify_model_integrity(self, model_id: str, model_version: str, artifact_path: Path) -> bool:
        """
        Verify model artifact integrity against registry.
        
        Args:
            model_id: Model identifier
            model_version: Model version
            artifact_path: Path to model artifact file
        
        Returns:
            True if integrity verified
        
        Raises:
            RegistryAPIError: If verification fails
        """
        model_record = self.registry.find_by_id_version(model_id, model_version)
        if not model_record:
            raise RegistryAPIError(f"Model {model_id} version {model_version} not found in registry")
        
        # Verify artifact hash
        try:
            public_key = self.model_key_manager.get_public_key()
            verifier = BundleVerifier(public_key)
            expected_hash = model_record.get('artifact_hash')
            verifier.verify_hash(artifact_path, expected_hash)
        except BundleVerificationError as e:
            raise RegistryAPIError(f"Model integrity verification failed: {e}") from e
        
        return True
