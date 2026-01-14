#!/usr/bin/env python3
"""
RansomEye v1.0 AI Core - Model Storage
AUTHORITATIVE: Persistent storage of trained AI models for replay
Python 3.10+ only
"""

import os
import sys
import json
import pickle
import hashlib
from typing import Optional, Dict, Any
from pathlib import Path

try:
    import numpy as np
    from sklearn.cluster import KMeans
    _sklearn_available = True
except ImportError:
    _sklearn_available = False
    KMeans = None


class ModelStorageError(Exception):
    """Model storage error."""
    pass


class ModelStorage:
    """
    PHASE 3: Persistent storage for trained AI models.
    
    Ensures:
    - Models are persisted (not retrained silently)
    - Models can be loaded for replay
    - Same training data → same model
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize model storage.
        
        Args:
            storage_dir: Directory for model storage (default: from RANSOMEYE_MODEL_STORAGE_DIR)
        """
        if storage_dir:
            self.storage_dir = storage_dir
        else:
            storage_dir_env = os.getenv('RANSOMEYE_MODEL_STORAGE_DIR')
            if storage_dir_env:
                self.storage_dir = Path(storage_dir_env)
            else:
                # Default: /opt/ransomeye/runtime/models
                install_root = os.getenv('RANSOMEYE_INSTALL_ROOT', '/opt/ransomeye')
                self.storage_dir = Path(install_root) / 'runtime' / 'models'
        
        # Create storage directory if it doesn't exist
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def compute_training_data_hash(self, feature_vectors) -> str:
        """
        Compute deterministic hash of training data.
        
        Args:
            feature_vectors: Training feature vectors (numpy array or list)
            
        Returns:
            SHA256 hash of training data
        """
        # Convert to list for JSON serialization
        if isinstance(feature_vectors, np.ndarray):
            vectors_list = feature_vectors.tolist()
        else:
            vectors_list = feature_vectors
        
        # Sort for deterministic hashing
        vectors_json = json.dumps(vectors_list, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(vectors_json.encode('utf-8')).hexdigest()
    
    def save_model(self, model, model_type: str, model_version: str, 
                   training_data_hash: str, model_params: Optional[Dict[str, Any]] = None) -> str:
        """
        PHASE 3: Save trained model to persistent storage.
        
        Args:
            model: Trained model (e.g., KMeans)
            model_type: Model type (e.g., 'CLUSTERING')
            model_version: Model version string
            training_data_hash: SHA256 hash of training data
            model_params: Model parameters (for reproducibility)
            
        Returns:
            Model storage path
        """
        if not _sklearn_available:
            raise ModelStorageError("scikit-learn not available - cannot save models")
        
        # Create model identifier from type, version, and training data hash
        model_id = f"{model_type}_{model_version}_{training_data_hash[:16]}"
        model_file = self.storage_dir / f"{model_id}.pkl"
        
        # Save model with metadata
        model_metadata = {
            'model_type': model_type,
            'model_version': model_version,
            'training_data_hash': training_data_hash,
            'model_params': model_params or {}
        }
        
        try:
            # Save model using pickle
            with open(model_file, 'wb') as f:
                pickle.dump({
                    'model': model,
                    'metadata': model_metadata
                }, f)
            
            return str(model_file)
        except Exception as e:
            raise ModelStorageError(f"Failed to save model: {e}") from e
    
    def load_model(self, model_type: str, model_version: str, 
                   training_data_hash: str) -> Optional[Any]:
        """
        PHASE 3: Load trained model from persistent storage.
        
        Args:
            model_type: Model type
            model_version: Model version string
            training_data_hash: SHA256 hash of training data
            
        Returns:
            Loaded model, or None if not found
        """
        # Create model identifier
        model_id = f"{model_type}_{model_version}_{training_data_hash[:16]}"
        model_file = self.storage_dir / f"{model_id}.pkl"
        
        if not model_file.exists():
            return None
        
        try:
            with open(model_file, 'rb') as f:
                model_data = pickle.load(f)
                return model_data.get('model')
        except Exception as e:
            raise ModelStorageError(f"Failed to load model: {e}") from e
    
    def get_model_hash(self, model) -> str:
        """
        Compute deterministic hash of model.
        
        Args:
            model: Trained model
            
        Returns:
            SHA256 hash of model
        """
        try:
            # Serialize model to bytes
            model_bytes = pickle.dumps(model)
            return hashlib.sha256(model_bytes).hexdigest()
        except Exception as e:
            raise ModelStorageError(f"Failed to compute model hash: {e}") from e
