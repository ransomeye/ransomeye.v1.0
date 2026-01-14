#!/usr/bin/env python3
"""
RansomEye v1.0 GA - SBOM Verification Utility
AUTHORITATIVE: Offline verification of release bundle SBOM (manifest.json)

GA-BLOCKING: This utility verifies manifest.json.sig and all artifact hashes.
Used by installers for fail-closed verification before installation.
"""

import sys
import json
import hashlib
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add supply-chain to path (try multiple locations for air-gapped scenarios)
_supply_chain_dir = None
for possible_dir in [
    Path(__file__).parent.parent / "supply-chain",  # Development environment
    Path(__file__).parent / "supply-chain",  # Release bundle
    Path("/opt/ransomeye/lib/supply-chain"),  # Installed location
]:
    if possible_dir.exists():
        _supply_chain_dir = possible_dir
        sys.path.insert(0, str(_supply_chain_dir))
        break

if _supply_chain_dir:
    from crypto.artifact_verifier import ArtifactVerifier, ArtifactVerificationError
    from crypto.vendor_key_manager import VendorKeyManager, VendorKeyManagerError
else:
    # Fallback: Minimal inline implementation for air-gapped scenarios
    class ArtifactVerificationError(Exception):
        pass
    class VendorKeyManagerError(Exception):
        pass
    
    # Minimal inline verifier (for air-gapped scenarios without full supply-chain module)
    class ArtifactVerifier:
        def __init__(self, public_key=None, public_key_path=None):
            if public_key_path:
                from cryptography.hazmat.primitives import serialization
                from cryptography.hazmat.backends import default_backend
                public_key_bytes = public_key_path.read_bytes()
                self.public_key = serialization.load_pem_public_key(
                    public_key_bytes, backend=default_backend()
                )
            else:
                self.public_key = public_key
        
        def verify_manifest_signature(self, manifest):
            # Inline implementation (same as supply-chain version)
            signature_b64 = manifest.get('signature', '')
            if not signature_b64:
                return False
            manifest_copy = manifest.copy()
            manifest_copy.pop('signature', None)
            canonical_json = json.dumps(manifest_copy, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            manifest_hash = hashlib.sha256(canonical_json.encode('utf-8')).digest()
            signature_bytes = base64.b64decode(signature_b64.encode('ascii'))
            self.public_key.verify(signature_bytes, manifest_hash)
            return True
        
        def verify_artifact_hash(self, artifact_path, expected_sha256):
            hash_obj = hashlib.sha256()
            with open(artifact_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_obj.update(chunk)
            computed_hash = hash_obj.hexdigest()
            return computed_hash == expected_sha256.lower()
    
    class VendorKeyManager:
        def __init__(self, key_dir):
            self.key_dir = Path(key_dir)
        
        def get_public_key(self, key_id):
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend
            public_key_path = self.key_dir / f"{key_id}.pub"
            if not public_key_path.exists():
                return None
            public_key_bytes = public_key_path.read_bytes()
            return serialization.load_pem_public_key(public_key_bytes, backend=default_backend())


class SBOMVerificationError(Exception):
    """Base exception for SBOM verification errors."""
    pass


def compute_file_hash(file_path: Path) -> str:
    """
    Compute SHA256 hash of file.
    
    Args:
        file_path: Path to file
        
    Returns:
        SHA256 hash as hexadecimal string
    """
    hash_obj = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def verify_sbom(
    release_root: Path,
    manifest_path: Path,
    signature_path: Path,
    public_key_path: Optional[Path] = None,
    key_dir: Optional[Path] = None,
    signing_key_id: Optional[str] = None
) -> bool:
    """
    GA-BLOCKING: Verify SBOM (manifest.json) signature and all artifact hashes.
    
    This function performs fail-closed verification:
    - Verifies manifest.json.sig signature
    - Verifies every artifact's SHA256 hash
    - Returns False on any failure (no warnings, no overrides)
    
    Args:
        release_root: Root directory of release bundle
        manifest_path: Path to manifest.json
        signature_path: Path to manifest.json.sig
        public_key_path: Optional path to public key file (for offline verification)
        key_dir: Optional directory containing vendor signing keys
        signing_key_id: Optional signing key identifier (if using key_dir)
        
    Returns:
        True if all verifications pass, False otherwise
        
    Raises:
        SBOMVerificationError: If verification fails (fail-closed)
    """
    # Load manifest
    if not manifest_path.exists():
        raise SBOMVerificationError(f"Manifest file not found: {manifest_path}")
    
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    except Exception as e:
        raise SBOMVerificationError(f"Failed to load manifest: {e}") from e
    
    # Load signature
    if not signature_path.exists():
        raise SBOMVerificationError(f"Signature file not found: {signature_path}")
    
    signature = signature_path.read_text(encoding='utf-8').strip()
    
    # Add signature to manifest for verification
    manifest['signature'] = signature
    
    # Load public key
    if public_key_path:
        verifier = ArtifactVerifier(public_key_path=public_key_path)
    elif key_dir and signing_key_id:
        key_manager = VendorKeyManager(key_dir)
        public_key = key_manager.get_public_key(signing_key_id)
        if not public_key:
            raise SBOMVerificationError(f"Public key not found: {signing_key_id}")
        verifier = ArtifactVerifier(public_key=public_key)
    else:
        raise SBOMVerificationError("Either public_key_path or (key_dir + signing_key_id) must be provided")
    
    # GA-BLOCKING: Verify manifest signature
    if not verifier.verify_manifest_signature(manifest):
        raise SBOMVerificationError(
            "Manifest signature verification failed. "
            "This indicates the manifest may have been tampered with."
        )
    
    # GA-BLOCKING: Verify all artifact hashes
    artifacts = manifest.get('artifacts', [])
    if not artifacts:
        raise SBOMVerificationError("Manifest contains no artifacts")
    
    failed_artifacts = []
    for artifact in artifacts:
        artifact_path = release_root / artifact['path']
        expected_hash = artifact['sha256']
        
        if not artifact_path.exists():
            failed_artifacts.append({
                'path': artifact['path'],
                'reason': 'file not found'
            })
            continue
        
        # Verify artifact hash
        if not verifier.verify_artifact_hash(artifact_path, expected_hash):
            computed_hash = compute_file_hash(artifact_path)
            failed_artifacts.append({
                'path': artifact['path'],
                'reason': f'hash mismatch (expected: {expected_hash}, computed: {computed_hash})'
            })
    
    if failed_artifacts:
        error_msg = "Artifact hash verification failed:\n"
        for failure in failed_artifacts:
            error_msg += f"  - {failure['path']}: {failure['reason']}\n"
        raise SBOMVerificationError(error_msg)
    
    return True


def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Verify SBOM (manifest.json) for RansomEye release bundle'
    )
    parser.add_argument(
        '--release-root',
        type=Path,
        required=True,
        help='Root directory of release bundle'
    )
    parser.add_argument(
        '--manifest',
        type=Path,
        default=None,
        help='Path to manifest.json (default: release-root/manifest.json)'
    )
    parser.add_argument(
        '--signature',
        type=Path,
        default=None,
        help='Path to manifest.json.sig (default: release-root/manifest.json.sig)'
    )
    parser.add_argument(
        '--public-key',
        type=Path,
        help='Path to public key file (for offline verification)'
    )
    parser.add_argument(
        '--key-dir',
        type=Path,
        help='Directory containing vendor signing keys'
    )
    parser.add_argument(
        '--signing-key-id',
        help='Signing key identifier (if using key_dir)'
    )
    
    args = parser.parse_args()
    
    if not args.release_root.exists():
        print(f"Error: Release root not found: {args.release_root}", file=sys.stderr)
        sys.exit(1)
    
    manifest_path = args.manifest or (args.release_root / 'manifest.json')
    signature_path = args.signature or (args.release_root / 'manifest.json.sig')
    
    try:
        verify_sbom(
            release_root=args.release_root,
            manifest_path=manifest_path,
            signature_path=signature_path,
            public_key_path=args.public_key,
            key_dir=args.key_dir,
            signing_key_id=args.signing_key_id
        )
        print("✓ SBOM verification passed")
        print("  - Manifest signature: VALID")
        print("  - All artifact hashes: VERIFIED")
        return 0
    except SBOMVerificationError as e:
        print(f"✗ SBOM verification failed: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
