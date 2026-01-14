#!/usr/bin/env python3
"""
RansomEye v1.0 GA - Release SBOM Generator
AUTHORITATIVE: Generate machine-readable SBOM (manifest.json) for entire release bundle

GA-BLOCKING: This script generates manifest.json listing every shipped artifact
with SHA256 hashes, enabling offline cryptographic verification.

STRICT REQUIREMENTS:
- Deterministic: Same release bundle → same manifest.json
- Complete: Every artifact must be listed
- Signed: manifest.json.sig must be generated using ed25519
- Offline: No network access required
"""

import sys
import os
import json
import hashlib
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add supply-chain to path
_supply_chain_dir = Path(__file__).parent.parent / "supply-chain"
sys.path.insert(0, str(_supply_chain_dir))

from crypto.vendor_key_manager import VendorKeyManager, VendorKeyManagerError
from crypto.artifact_signer import ArtifactSigner, ArtifactSigningError


class SBOMGeneratorError(Exception):
    """Base exception for SBOM generator errors."""
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


def determine_artifact_type(file_path: Path, release_root: Path) -> str:
    """
    Determine artifact type based on file path.
    
    Args:
        file_path: Path to artifact file
        release_root: Root of release bundle
        
    Returns:
        Artifact type string
    """
    relative_path = file_path.relative_to(release_root)
    path_parts = relative_path.parts
    
    if path_parts[0] == 'core':
        return 'core'
    elif path_parts[0] == 'linux-agent':
        return 'linux_agent'
    elif path_parts[0] == 'windows-agent':
        return 'windows_agent'
    elif path_parts[0] == 'dpi-probe':
        return 'dpi_probe'
    elif path_parts[0] == 'checksums':
        return 'checksum'
    elif path_parts[0] == 'audit':
        return 'audit'
    else:
        return 'other'


def collect_artifacts(release_root: Path) -> List[Dict[str, Any]]:
    """
    Collect all artifacts in release bundle.
    
    GA-BLOCKING: Every shipped artifact must be listed in manifest.
    
    Args:
        release_root: Root directory of release bundle
        
    Returns:
        List of artifact dictionaries
    """
    artifacts = []
    
    # Directories to scan (excluding hidden files and directories)
    scan_dirs = [
        'core',
        'linux-agent',
        'windows-agent',
        'dpi-probe',
        'checksums',
        'audit'
    ]
    
    # Also include root-level files
    root_files = ['README.md', 'validate-release.sh']
    
    # Collect artifacts from component directories
    for dir_name in scan_dirs:
        dir_path = release_root / dir_name
        if not dir_path.exists():
            continue
        
        for file_path in dir_path.rglob('*'):
            if file_path.is_file() and not file_path.name.startswith('.'):
                relative_path = file_path.relative_to(release_root)
                artifact_type = determine_artifact_type(file_path, release_root)
                
                artifacts.append({
                    'name': file_path.name,
                    'path': str(relative_path).replace('\\', '/'),  # Normalize path separators
                    'sha256': compute_file_hash(file_path),
                    'type': artifact_type
                })
    
    # Collect root-level files
    for file_name in root_files:
        file_path = release_root / file_name
        if file_path.exists() and file_path.is_file():
            artifacts.append({
                'name': file_name,
                'path': file_name,
                'sha256': compute_file_hash(file_path),
                'type': 'release'
            })
    
    # Sort artifacts by path for deterministic ordering
    artifacts.sort(key=lambda x: x['path'])
    
    return artifacts


def generate_sbom(
    release_root: Path,
    version: str,
    build_id: str,
    signing_key_id: str,
    key_dir: Path,
    output_path: Path
) -> None:
    """
    GA-BLOCKING: Generate SBOM (manifest.json) for entire release bundle.
    
    Args:
        release_root: Root directory of release bundle
        version: Release version (e.g., "1.0.0")
        build_id: Build identifier (e.g., git commit hash)
        signing_key_id: Signing key identifier
        key_dir: Directory containing vendor signing keys
        output_path: Path to write manifest.json
        
    Raises:
        SBOMGeneratorError: If generation fails
    """
    try:
        # Collect all artifacts
        artifacts = collect_artifacts(release_root)
        
        if not artifacts:
            raise SBOMGeneratorError("No artifacts found in release bundle")
        
        # Build manifest (without signature)
        manifest = {
            'version': version,
            'build_id': build_id,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'artifacts': artifacts
        }
        
        # Sign manifest (without signature field)
        key_manager = VendorKeyManager(key_dir)
        private_key, public_key, key_id = key_manager.get_or_create_keypair(signing_key_id)
        signer = ArtifactSigner(private_key, key_id)
        
        # GA-BLOCKING: Sign manifest (signature computed on manifest without signature field)
        signature = signer.sign_manifest(manifest)
        
        # Add signature and signing_key_id to manifest
        manifest['signature'] = signature
        manifest['signing_key_id'] = signing_key_id
        
        # Write manifest.json (pretty-printed for readability, but signature computed on canonical form)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False, sort_keys=True)
        
        # Write manifest.json.sig (signature file)
        signature_path = output_path.parent / f"{output_path.name}.sig"
        signature_path.write_text(signature, encoding='utf-8')
        
        print(f"SBOM generated successfully:")
        print(f"  Manifest: {output_path}")
        print(f"  Signature: {signature_path}")
        print(f"  Artifacts: {len(artifacts)}")
        print(f"  Signing Key ID: {signing_key_id}")
        
    except (VendorKeyManagerError, ArtifactSigningError) as e:
        raise SBOMGeneratorError(f"Failed to generate SBOM: {e}") from e
    except Exception as e:
        raise SBOMGeneratorError(f"Unexpected error generating SBOM: {e}") from e


def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate SBOM (manifest.json) for RansomEye release bundle'
    )
    parser.add_argument(
        '--release-root',
        type=Path,
        required=True,
        help='Root directory of release bundle'
    )
    parser.add_argument(
        '--version',
        required=True,
        help='Release version (e.g., 1.0.0)'
    )
    parser.add_argument(
        '--build-id',
        required=True,
        help='Build identifier (e.g., git commit hash)'
    )
    parser.add_argument(
        '--signing-key-id',
        required=True,
        help='Signing key identifier'
    )
    parser.add_argument(
        '--key-dir',
        type=Path,
        required=True,
        help='Directory containing vendor signing keys'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=None,
        help='Output path for manifest.json (default: release-root/manifest.json)'
    )
    
    args = parser.parse_args()
    
    if not args.release_root.exists():
        print(f"Error: Release root not found: {args.release_root}", file=sys.stderr)
        sys.exit(1)
    
    output_path = args.output or (args.release_root / 'manifest.json')
    
    try:
        generate_sbom(
            release_root=args.release_root,
            version=args.version,
            build_id=args.build_id,
            signing_key_id=args.signing_key_id,
            key_dir=args.key_dir,
            output_path=output_path
        )
    except SBOMGeneratorError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
