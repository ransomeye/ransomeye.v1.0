#!/usr/bin/env python3
"""
RansomEye LLM Summarizer - Verify Model CLI
AUTHORITATIVE: Verify model integrity and registry state (no inference)
"""

import sys
import os
import argparse
from pathlib import Path

# Add parent directory to path
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

# Add project root to path for imports
_project_root = _parent_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from llm.model_loader import ModelLoader, ModelLoaderError
import importlib.util

# Import RegistryAPI for model registry
_model_registry_dir = _project_root / "ai-model-registry"
if str(_model_registry_dir) not in sys.path:
    sys.path.insert(0, str(_model_registry_dir))

_registry_api_spec = importlib.util.spec_from_file_location("registry_api", _model_registry_dir / "api" / "registry_api.py")
_registry_api_module = importlib.util.module_from_spec(_registry_api_spec)
_registry_api_spec.loader.exec_module(_registry_api_module)
RegistryAPI = _registry_api_module.RegistryAPI


def main():
    """Verify model integrity and registry state."""
    parser = argparse.ArgumentParser(
        description='Verify model integrity and registry state (no inference)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --model-id <uuid> --model-version 1.0.0

Environment Variables:
  RANSOMEYE_LLM_MODEL_PATH - Path to GGUF model file
  RANSOMEYE_MODEL_REGISTRY_PATH - Path to model registry
  RANSOMEYE_MODEL_KEY_DIR - Directory containing model signing keys
  RANSOMEYE_AUDIT_LEDGER_PATH - Path to audit ledger file
  RANSOMEYE_AUDIT_LEDGER_KEY_DIR - Directory containing ledger signing keys
        """
    )
    
    parser.add_argument(
        '--model-id',
        type=str,
        required=True,
        help='Model identifier from registry (UUID)'
    )
    
    parser.add_argument(
        '--model-version',
        type=str,
        required=True,
        help='Model version (semver, e.g., 1.0.0)'
    )
    
    parser.add_argument(
        '--model-path',
        type=Path,
        default=None,
        help='Path to model file (overrides RANSOMEYE_LLM_MODEL_PATH)'
    )
    
    parser.add_argument(
        '--model-registry-path',
        type=Path,
        default=None,
        help='Path to model registry (overrides RANSOMEYE_MODEL_REGISTRY_PATH)'
    )
    
    parser.add_argument(
        '--model-key-dir',
        type=Path,
        default=None,
        help='Directory containing model signing keys (overrides RANSOMEYE_MODEL_KEY_DIR)'
    )
    
    parser.add_argument(
        '--ledger-path',
        type=Path,
        default=None,
        help='Path to audit ledger (overrides RANSOMEYE_AUDIT_LEDGER_PATH)'
    )
    
    parser.add_argument(
        '--ledger-key-dir',
        type=Path,
        default=None,
        help='Directory containing ledger keys (overrides RANSOMEYE_AUDIT_LEDGER_KEY_DIR)'
    )
    
    args = parser.parse_args()
    
    # Get paths from env or args
    model_path = args.model_path or Path(os.getenv('RANSOMEYE_LLM_MODEL_PATH', ''))
    model_registry_path = args.model_registry_path or Path(os.getenv('RANSOMEYE_MODEL_REGISTRY_PATH', ''))
    model_key_dir = args.model_key_dir or Path(os.getenv('RANSOMEYE_MODEL_KEY_DIR', ''))
    ledger_path = args.ledger_path or Path(os.getenv('RANSOMEYE_AUDIT_LEDGER_PATH', ''))
    ledger_key_dir = args.ledger_key_dir or Path(os.getenv('RANSOMEYE_AUDIT_LEDGER_KEY_DIR', ''))
    
    # Validate required paths
    if not model_path:
        print("ERROR: Model path not provided. Set RANSOMEYE_LLM_MODEL_PATH or use --model-path", file=sys.stderr)
        sys.exit(1)
    if not model_registry_path:
        print("ERROR: Model registry path not provided. Set RANSOMEYE_MODEL_REGISTRY_PATH or use --model-registry-path", file=sys.stderr)
        sys.exit(1)
    if not model_key_dir:
        print("ERROR: Model key directory not provided. Set RANSOMEYE_MODEL_KEY_DIR or use --model-key-dir", file=sys.stderr)
        sys.exit(1)
    if not ledger_path:
        print("ERROR: Audit ledger path not provided. Set RANSOMEYE_AUDIT_LEDGER_PATH or use --ledger-path", file=sys.stderr)
        sys.exit(1)
    if not ledger_key_dir:
        print("ERROR: Audit ledger key directory not provided. Set RANSOMEYE_AUDIT_LEDGER_KEY_DIR or use --ledger-key-dir", file=sys.stderr)
        sys.exit(1)
    
    # Validate model file exists
    if not model_path.exists():
        print(f"ERROR: Model file not found: {model_path}", file=sys.stderr)
        sys.exit(1)
    
    # Initialize model registry API
    try:
        model_registry_api = RegistryAPI(
            registry_path=model_registry_path,
            model_key_dir=model_key_dir,
            ledger_path=ledger_path,
            ledger_key_dir=ledger_key_dir
        )
    except Exception as e:
        print(f"ERROR: Failed to initialize model registry API: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Initialize model loader
    try:
        model_loader = ModelLoader(model_registry_api=model_registry_api)
        # Override model path env var for this verification
        import os
        os.environ['RANSOMEYE_LLM_MODEL_PATH'] = str(model_path)
    except Exception as e:
        print(f"ERROR: Failed to initialize model loader: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Verify model (load with verification, but don't keep loaded)
    try:
        model_instance, model_metadata = model_loader.load_model(
            model_id=args.model_id,
            model_version=args.model_version
        )
    except ModelLoaderError as e:
        print(f"ERROR: Model verification failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error during model verification: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Print verification results
    print("SUCCESS: Model verification passed")
    print(f"  Model ID: {model_metadata.get('model_id', 'N/A')}")
    print(f"  Model Version: {model_metadata.get('model_version', 'N/A')}")
    print(f"  Model Hash: {model_metadata.get('model_hash', 'N/A')}")
    print(f"  Lifecycle State: {model_metadata.get('lifecycle_state', 'N/A')}")
    print(f"  Model Type: {model_metadata.get('model_type', 'N/A')}")
    print(f"  Intended Use: {model_metadata.get('intended_use', 'N/A')}")
    print(f"  Model Path: {model_metadata.get('model_path', 'N/A')}")
    
    # Verify lifecycle state is PROMOTED
    if model_metadata.get('lifecycle_state') != 'PROMOTED':
        print(f"WARNING: Model is not in PROMOTED state. Current state: {model_metadata.get('lifecycle_state')}", file=sys.stderr)
        print("WARNING: Model should not be used for production inference", file=sys.stderr)
        sys.exit(1)
    
    print()
    print("Model is ready for use in production inference.")
    
    sys.exit(0)


if __name__ == '__main__':
    main()
