#!/usr/bin/env python3
"""
RansomEye Supply-Chain Signing & Verification Framework - Sign Artifacts CLI
AUTHORITATIVE: Command-line tool for signing artifacts
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_supply_chain_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_supply_chain_dir))

from crypto.persistent_signing_authority import PersistentSigningAuthority, PersistentSigningAuthorityError
from crypto.artifact_signer import ArtifactSigner, ArtifactSigningError
from engine.manifest_builder import ManifestBuilder, ManifestBuilderError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Sign artifact for supply-chain integrity'
    )
    parser.add_argument(
        '--artifact',
        type=Path,
        required=True,
        help='Path to artifact file'
    )
    parser.add_argument(
        '--artifact-name',
        required=True,
        help='Artifact name'
    )
    parser.add_argument(
        '--artifact-type',
        required=True,
        choices=['CORE_INSTALLER', 'LINUX_AGENT', 'WINDOWS_AGENT', 'DPI_PROBE', 'RELEASE_BUNDLE'],
        help='Artifact type (exactly 5 types, no others)'
    )
    parser.add_argument(
        '--version',
        required=True,
        help='Artifact version (semver format)'
    )
    parser.add_argument(
        '--signing-key-id',
        required=True,
        help='Signing key identifier'
    )
    parser.add_argument(
        '--vault-dir',
        type=Path,
        required=True,
        help='Directory containing encrypted key vault'
    )
    parser.add_argument(
        '--registry-path',
        type=Path,
        required=True,
        help='Path to key registry JSON file'
    )
    parser.add_argument(
        '--toolchain-config',
        type=Path,
        help='Path to toolchain configuration JSON file (optional)'
    )
    parser.add_argument(
        '--build-host-info',
        type=Path,
        help='Path to build host information JSON file (optional)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        required=True,
        help='Output directory for manifest and signature files'
    )
    
    args = parser.parse_args()
    
    try:
        # Load optional configuration files
        toolchain_config = None
        if args.toolchain_config:
            toolchain_config = json.loads(args.toolchain_config.read_text())
        
        build_host_info = None
        if args.build_host_info:
            build_host_info = json.loads(args.build_host_info.read_text())
        
        # Initialize persistent signing authority
        # PHASE-9: Use persistent signing authority (no ephemeral keys)
        authority = PersistentSigningAuthority(
            vault_dir=args.vault_dir,
            registry_path=args.registry_path
        )
        
        # Get signing key from persistent vault
        private_key, public_key = authority.get_signing_key(args.signing_key_id, require_active=True)
        
        # Initialize signer and manifest builder
        signer = ArtifactSigner(private_key, args.signing_key_id)
        manifest_builder = ManifestBuilder()
        
        # Build manifest
        manifest = manifest_builder.build_manifest(
            artifact_path=args.artifact,
            artifact_name=args.artifact_name,
            artifact_type=args.artifact_type,
            version=args.version,
            signing_key_id=args.signing_key_id,
            toolchain_config=toolchain_config,
            build_host_info=build_host_info
        )
        
        # Sign manifest
        signature = signer.sign_manifest(manifest)
        manifest['signature'] = signature
        
        # Write outputs
        args.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Write SHA256 file
        sha256_path = args.output_dir / f"{args.artifact.name}.sha256"
        sha256_path.write_text(f"{manifest['sha256']}  {args.artifact.name}\n")
        
        # Write manifest file
        manifest_path = args.output_dir / f"{args.artifact.name}.manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
        
        # Write signature file
        signature_path = args.output_dir / f"{args.artifact.name}.manifest.sig"
        signature_path.write_text(signature)
        
        print(f"Artifact signed successfully:")
        print(f"  Artifact: {args.artifact}")
        print(f"  Artifact ID: {manifest['artifact_id']}")
        print(f"  SHA256: {manifest['sha256']}")
        print(f"  Signing Key ID: {manifest['signing_key_id']}")
        print(f"  Output files:")
        print(f"    - {sha256_path}")
        print(f"    - {manifest_path}")
        print(f"    - {signature_path}")
        
    except (PersistentSigningAuthorityError, ArtifactSigningError, ManifestBuilderError) as e:
        print(f"Artifact signing failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
