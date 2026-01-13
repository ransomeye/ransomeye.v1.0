#!/usr/bin/env python3
"""
RansomEye LLM Summarizer - Model Loader
AUTHORITATIVE: GGUF model loading with hash verification and registry integration
"""

import os
import sys
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# Add ai-model-registry to path
_model_registry_dir = Path(__file__).parent.parent.parent / "ai-model-registry"
if str(_model_registry_dir) not in sys.path:
    sys.path.insert(0, str(_model_registry_dir))

# Import model registry components
import importlib.util

_registry_api_spec = importlib.util.spec_from_file_location("registry_api", _model_registry_dir / "api" / "registry_api.py")
_registry_api_module = importlib.util.module_from_spec(_registry_api_spec)
_registry_api_spec.loader.exec_module(_registry_api_module)
RegistryAPI = _registry_api_module.RegistryAPI


class ModelLoaderError(Exception):
    """Base exception for model loader errors."""
    pass


class ModelNotFoundError(ModelLoaderError):
    """Raised when model file is not found."""
    pass


class ModelHashMismatchError(ModelLoaderError):
    """Raised when model hash does not match registry."""
    pass


class ModelNotPromotedError(ModelLoaderError):
    """Raised when model is not in PROMOTED state."""
    pass


class ModelLoader:
    """
    GGUF model loader with hash verification and registry integration.
    
    Properties:
    - Offline: Loads from filesystem only
    - Hash-verified: Verifies model hash against registry
    - State-verified: Verifies model is PROMOTED
    - Fail-closed: Any mismatch causes rejection
    """
    
    def __init__(
        self,
        model_registry_api: Optional[RegistryAPI] = None,
        model_path_env_var: str = "RANSOMEYE_LLM_MODEL_PATH"
    ):
        """
        Initialize model loader.
        
        Args:
            model_registry_api: Optional RegistryAPI instance (if None, will create)
            model_path_env_var: Environment variable name for model path
        """
        self.model_path_env_var = model_path_env_var
        self.model_registry_api = model_registry_api
        self._loaded_model = None
        self._model_metadata = None
    
    def load_model(
        self,
        model_id: str,
        model_version: str
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        Load GGUF model with verification.
        
        Process:
        1. Get model path from environment
        2. Verify model file exists
        3. Calculate model SHA256 hash
        4. Verify hash matches registry
        5. Verify model state == PROMOTED
        6. Load model (GGUF)
        7. Return model instance and metadata
        
        Args:
            model_id: Model identifier from registry
            model_version: Model version from registry
        
        Returns:
            Tuple of (model_instance, model_metadata)
        
        Raises:
            ModelNotFoundError: If model file not found
            ModelHashMismatchError: If hash mismatch
            ModelNotPromotedError: If model not PROMOTED
            ModelLoaderError: If loading fails
        """
        # Get model path from environment
        model_path_str = os.getenv(self.model_path_env_var)
        if not model_path_str:
            raise ModelLoaderError(
                f"Model path not found in environment variable: {self.model_path_env_var}"
            )
        
        model_path = Path(model_path_str)
        if not model_path.exists():
            raise ModelNotFoundError(f"Model file not found: {model_path}")
        
        # Get model record from registry
        if not self.model_registry_api:
            raise ModelLoaderError("Model registry API not initialized")
        
        try:
            # RegistryAPI has get_model method
            model_record = self.model_registry_api.get_model(model_id, model_version)
            if not model_record:
                raise ModelLoaderError(f"Model not found in registry: {model_id} version {model_version}")
        except Exception as e:
            raise ModelLoaderError(f"Failed to get model from registry: {e}") from e
        
        # Verify model state
        lifecycle_state = model_record.get('lifecycle_state')
        if lifecycle_state != 'PROMOTED':
            raise ModelNotPromotedError(
                f"Model {model_id} version {model_version} is not PROMOTED. "
                f"Current state: {lifecycle_state}"
            )
        
        # Calculate model file hash
        model_hash = self._calculate_file_hash(model_path)
        
        # Verify hash matches registry
        registry_hash = model_record.get('artifact_hash', '').lower()
        if model_hash.lower() != registry_hash.lower():
            raise ModelHashMismatchError(
                f"Model hash mismatch for {model_id} version {model_version}: "
                f"calculated={model_hash}, registry={registry_hash}"
            )
        
        # Load GGUF model
        try:
            model_instance = self._load_gguf_model(model_path)
        except Exception as e:
            raise ModelLoaderError(f"Failed to load GGUF model: {e}") from e
        
        # Store metadata
        self._loaded_model = model_instance
        self._model_metadata = {
            'model_id': model_id,
            'model_version': model_version,
            'model_hash': model_hash,
            'model_path': str(model_path),
            'lifecycle_state': lifecycle_state,
            'model_type': model_record.get('model_type', ''),
            'intended_use': model_record.get('intended_use', '')
        }
        
        return model_instance, self._model_metadata
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA256 hash of model file.
        
        Args:
            file_path: Path to model file
        
        Returns:
            SHA256 hash (64 hex characters)
        """
        hash_obj = hashlib.sha256()
        
        # Read file in chunks to handle large files
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    
    def _load_gguf_model(self, model_path: Path) -> Any:
        """
        Load GGUF model using llama-cpp-python.
        
        Args:
            model_path: Path to GGUF model file
        
        Returns:
            Model instance (Llama from llama-cpp-python)
        
        Raises:
            ModelLoaderError: If loading fails
        """
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ModelLoaderError(
                "llama-cpp-python not available. "
                "Install with: pip install llama-cpp-python"
            )
        
        try:
            # Load model with deterministic settings
            # n_ctx: context window size
            # n_threads: CPU threads (deterministic if fixed)
            # seed: fixed seed for determinism
            # verbose: False to suppress output
            model = Llama(
                model_path=str(model_path),
                n_ctx=4096,  # Context window
                n_threads=1,  # Single thread for determinism
                verbose=False,
                use_mmap=True,  # Memory mapping for large models
                use_mlock=False  # Don't lock memory
            )
            
            return model
        except Exception as e:
            raise ModelLoaderError(f"Failed to load GGUF model: {e}") from e
    
    def get_model_metadata(self) -> Optional[Dict[str, Any]]:
        """Get loaded model metadata."""
        return self._model_metadata
    
    def is_model_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._loaded_model is not None
