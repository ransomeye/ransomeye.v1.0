#!/usr/bin/env python3
"""
RansomEye AI Model Registry - Model Registration CLI
AUTHORITATIVE: Command-line tool for registering models in registry
"""

import sys
import json
import hashlib
import base64
from pathlib import Path
import argparse

# Add parent directory to path for imports
_registry_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_registry_dir))

from api.registry_api import RegistryAPI, RegistryAPIError

# Import crypto modules directly to avoid path conflicts
import importlib.util
_registry_dir = Path(__file__).parent.parent

_key_manager_spec = importlib.util.spec_from_file_location("model_key_manager", _registry_dir / "crypto" / "key_manager.py")
_key_manager_module = importlib.util.module_from_spec(_key_manager_spec)
_key_manager_spec.loader.exec_module(_key_manager_module)
ModelKeyManager = _key_manager_module.ModelKeyManager
ModelKeyManagerError = _key_manager_module.ModelKeyManagerError

_bundle_verifier_spec = importlib.util.spec_from_file_location("bundle_verifier", _registry_dir / "crypto" / "bundle_verifier.py")
_bundle_verifier_module = importlib.util.module_from_spec(_bundle_verifier_spec)
_bundle_verifier_spec.loader.exec_module(_bundle_verifier_module)
BundleVerifier = _bundle_verifier_module.BundleVerifier


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def sign_artifact_hash(artifact_hash: str, private_key) -> str:
    """Sign artifact hash with private key."""
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        hash_bytes = bytes.fromhex(artifact_hash)
        signature_bytes = private_key.sign(hash_bytes)
        return base64.b64encode(signature_bytes).decode('ascii')
    except Exception as e:
        raise ValueError(f"Failed to sign artifact: {e}") from e


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Register a model in the AI Model Registry'
    )
    parser.add_argument(
        '--artifact',
        type=Path,
        required=True,
        help='Path to model artifact file'
    )
    parser.add_argument(
        '--model-name',
        required=True,
        help='Model name'
    )
    parser.add_argument(
        '--model-version',
        required=True,
        help='Model version (semantic versioning)'
    )
    parser.add_argument(
        '--model-type',
        choices=['ML', 'DL', 'LLM', 'ruleset'],
        required=True,
        help='Model type'
    )
    parser.add_argument(
        '--intended-use',
        choices=['classification', 'clustering', 'summarization', 'anomaly_detection', 
                 'threat_detection', 'policy_recommendation', 'forensic_analysis', 'correlation', 'other'],
        required=True,
        help='Intended use case'
    )
    parser.add_argument(
        '--training-data',
        type=Path,
        help='Path to training data provenance JSON file (optional)'
    )
    parser.add_argument(
        '--metadata',
        type=Path,
        help='Path to metadata JSON file (optional)'
    )
    parser.add_argument(
        '--registered-by',
        required=True,
        help='Entity that registered model (user, system, etc.)'
    )
    parser.add_argument(
        '--registry',
        type=Path,
        required=True,
        help='Path to registry file'
    )
    parser.add_argument(
        '--model-key-dir',
        type=Path,
        required=True,
        help='Directory containing model signing keys'
    )
    parser.add_argument(
        '--ledger',
        type=Path,
        required=True,
        help='Path to audit ledger file'
    )
    parser.add_argument(
        '--ledger-key-dir',
        type=Path,
        required=True,
        help='Directory containing ledger signing keys'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Path to output model record JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Calculate artifact hash
        artifact_hash = calculate_file_hash(args.artifact)
        
        # Sign artifact hash
        key_manager = ModelKeyManager(args.model_key_dir)
        private_key, public_key, key_id = key_manager.get_or_create_keypair()
        artifact_signature = sign_artifact_hash(artifact_hash, private_key)
        
        # Load training data provenance
        training_data_provenance = {
            'data_hashes': [],
            'data_sources': []
        }
        if args.training_data and args.training_data.exists():
            training_data = json.loads(args.training_data.read_text())
            training_data_provenance = training_data.get('training_data_provenance', training_data_provenance)
        
        # Load metadata
        metadata = {}
        if args.metadata and args.metadata.exists():
            metadata = json.loads(args.metadata.read_text())
        
        # Initialize registry API
        api = RegistryAPI(
            registry_path=args.registry,
            model_key_dir=args.model_key_dir,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Register model
        model_record = api.register_model(
            artifact_path=args.artifact,
            artifact_hash=artifact_hash,
            artifact_signature=artifact_signature,
            signing_key_id=key_id,
            model_name=args.model_name,
            model_version=args.model_version,
            model_type=args.model_type,
            intended_use=args.intended_use,
            training_data_provenance=training_data_provenance,
            registered_by=args.registered_by,
            metadata=metadata
        )
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(model_record, indent=2, ensure_ascii=False))
            print(f"Model registered successfully. Record written to: {args.output}")
        else:
            print(json.dumps(model_record, indent=2, ensure_ascii=False))
        
        print(f"Model ID: {model_record['model_id']}")
        print(f"Model Name: {model_record['model_name']}")
        print(f"Model Version: {model_record['model_version']}")
        print(f"Lifecycle State: {model_record['lifecycle_state']}")
        
    except RegistryAPIError as e:
        print(f"Registration failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
