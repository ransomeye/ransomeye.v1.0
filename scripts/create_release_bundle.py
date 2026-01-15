#!/usr/bin/env python3
"""
RansomEye v1.0 Release Bundle Creator
AUTHORITATIVE: Creates self-contained, offline-verifiable release bundles
Phase-9: Release gate independence from CI artifacts
"""

import os
import sys
import json
import hashlib
import shutil
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional


class ReleaseBundleError(Exception):
    """Base exception for release bundle errors."""
    pass


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of file."""
    hash_obj = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def collect_artifacts(artifacts_dir: Path) -> List[Dict[str, Any]]:
    """Collect all build artifacts."""
    artifacts = []
    
    artifact_patterns = [
        'core-installer.tar.gz',
        'linux-agent.tar.gz',
        'windows-agent.zip',
        'dpi-probe.tar.gz'
    ]
    
    for pattern in artifact_patterns:
        artifact_path = artifacts_dir / pattern
        if artifact_path.exists():
            artifacts.append({
                'name': pattern,
                'path': f'artifacts/{pattern}',
                'sha256': compute_file_hash(artifact_path),
                'size': artifact_path.stat().st_size
            })
        else:
            raise ReleaseBundleError(f"Required artifact not found: {pattern}")
    
    return artifacts


def collect_signatures(signed_dir: Path) -> List[Dict[str, Any]]:
    """Collect all artifact signatures."""
    signatures = []
    
    for manifest_file in signed_dir.glob('*.manifest.json'):
        artifact_name = manifest_file.stem.replace('.manifest', '')
        sig_file = signed_dir / f"{manifest_file.stem}.sig"
        
        if not sig_file.exists():
            raise ReleaseBundleError(f"Signature file missing for {artifact_name}")
        
        signatures.append({
            'artifact_name': artifact_name,
            'manifest_path': f'signatures/{manifest_file.name}',
            'signature_path': f'signatures/{sig_file.name}',
            'manifest_sha256': compute_file_hash(manifest_file),
            'signature_sha256': compute_file_hash(sig_file)
        })
    
    if len(signatures) != 4:  # Expected: 4 artifacts
        raise ReleaseBundleError(f"Expected 4 signatures, found {len(signatures)}")
    
    return signatures


def collect_sbom(sbom_dir: Path) -> Dict[str, Any]:
    """Collect SBOM and SBOM signature."""
    manifest_path = sbom_dir / 'manifest.json'
    sig_path = sbom_dir / 'manifest.json.sig'
    
    if not manifest_path.exists():
        raise ReleaseBundleError("SBOM manifest not found")
    if not sig_path.exists():
        raise ReleaseBundleError("SBOM signature not found")
    
    return {
        'manifest_path': 'sbom/manifest.json',
        'signature_path': 'sbom/manifest.json.sig',
        'manifest_sha256': compute_file_hash(manifest_path),
        'signature_sha256': compute_file_hash(sig_path)
    }


def collect_public_keys(keys_dir: Path, signing_key_id: str) -> Dict[str, Any]:
    """Collect public signing keys."""
    public_key_path = keys_dir / f"{signing_key_id}.pub"
    
    if not public_key_path.exists():
        raise ReleaseBundleError(f"Public key not found: {public_key_path}")
    
    public_key_hash = compute_file_hash(public_key_path)
    
    return {
        'key_id': signing_key_id,
        'key_path': f'keys/{signing_key_id}.pub',
        'key_sha256': public_key_hash
    }


def collect_evidence(evidence_dir: Path) -> Dict[str, Any]:
    """Collect Phase-8 evidence bundle."""
    bundle_path = evidence_dir / 'evidence_bundle.json'
    sig_path = evidence_dir / 'evidence_bundle.json.sig'
    
    if not bundle_path.exists():
        raise ReleaseBundleError("Phase-8 evidence bundle not found")
    if not sig_path.exists():
        raise ReleaseBundleError("Phase-8 evidence bundle signature not found")
    
    # Load evidence bundle to extract GA verdict
    with open(bundle_path, 'r') as f:
        bundle_data = json.load(f)
    
    return {
        'bundle_path': 'evidence/evidence_bundle.json',
        'signature_path': 'evidence/evidence_bundle.json.sig',
        'bundle_sha256': compute_file_hash(bundle_path),
        'signature_sha256': compute_file_hash(sig_path),
        'ga_verdict': bundle_data.get('overall_status', 'UNKNOWN')
    }


def collect_metadata(metadata_dir: Path) -> Dict[str, Any]:
    """Collect build and environment metadata."""
    metadata = {}
    
    build_info_path = metadata_dir / 'build-info.json'
    build_env_path = metadata_dir / 'build-environment.json'
    
    if build_info_path.exists():
        with open(build_info_path, 'r') as f:
            metadata['build_info'] = json.load(f)
        metadata['build_info_path'] = 'metadata/build-info.json'
    
    if build_env_path.exists():
        with open(build_env_path, 'r') as f:
            metadata['build_environment'] = json.load(f)
        metadata['build_environment_path'] = 'metadata/build-environment.json'
    
    return metadata


def create_release_manifest(
    version: str,
    artifacts: List[Dict[str, Any]],
    signatures: List[Dict[str, Any]],
    sbom: Dict[str, Any],
    public_key: Dict[str, Any],
    evidence: Dict[str, Any],
    metadata: Dict[str, Any],
    project_root: Path
) -> Dict[str, Any]:
    """Create RELEASE_MANIFEST.json."""
    manifest = {
        'version': '1.0',
        'release_version': version,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'bundle_type': 'ransomeye-release-bundle',
        'artifacts': artifacts,
        'signatures': signatures,
        'sbom': sbom,
        'public_keys': [public_key],
        'evidence': evidence,
        'metadata': metadata,
        'verification_instructions': {
            'offline_verification': 'All verification can be performed offline using bundled public keys',
            'long_term_verification': 'Bundle can be verified years later using bundled keys and evidence',
            'no_ci_dependency': 'Verification does not require CI access or artifact retention'
        }
    }
    
    return manifest


def create_release_bundle(
    version: str,
    build_artifacts_dir: Path,
    signed_artifacts_dir: Path,
    sbom_dir: Path,
    public_keys_dir: Path,
    evidence_dir: Path,
    metadata_dir: Path,
    signing_key_id: str,
    output_dir: Path,
    project_root: Path
) -> Path:
    """
    Create self-contained release bundle.
    
    Returns:
        Path to created release bundle tarball
    """
    bundle_name = f"ransomeye-{version}-release-bundle"
    bundle_dir = output_dir / bundle_name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    
    # Create directory structure
    (bundle_dir / 'artifacts').mkdir()
    (bundle_dir / 'signatures').mkdir()
    (bundle_dir / 'sbom').mkdir()
    (bundle_dir / 'keys').mkdir()
    (bundle_dir / 'evidence').mkdir()
    (bundle_dir / 'metadata').mkdir()
    
    # Collect and copy artifacts
    print("Collecting artifacts...")
    artifacts = collect_artifacts(build_artifacts_dir)
    for artifact in artifacts:
        src = build_artifacts_dir / artifact['name']
        dst = bundle_dir / 'artifacts' / artifact['name']
        shutil.copy2(src, dst)
        print(f"  ✅ {artifact['name']}")
    
    # Collect and copy signatures
    print("Collecting signatures...")
    signatures = collect_signatures(signed_artifacts_dir)
    for sig in signatures:
        manifest_src = signed_artifacts_dir / Path(sig['manifest_path']).name
        sig_src = signed_artifacts_dir / Path(sig['signature_path']).name
        shutil.copy2(manifest_src, bundle_dir / sig['manifest_path'])
        shutil.copy2(sig_src, bundle_dir / sig['signature_path'])
        print(f"  ✅ {sig['artifact_name']}")
    
    # Collect and copy SBOM
    print("Collecting SBOM...")
    sbom_data = collect_sbom(sbom_dir)
    shutil.copy2(sbom_dir / 'manifest.json', bundle_dir / sbom_data['manifest_path'])
    shutil.copy2(sbom_dir / 'manifest.json.sig', bundle_dir / sbom_data['signature_path'])
    print("  ✅ SBOM manifest and signature")
    
    # Collect and copy public keys
    print("Collecting public keys...")
    public_key_data = collect_public_keys(public_keys_dir, signing_key_id)
    shutil.copy2(public_keys_dir / f"{signing_key_id}.pub", bundle_dir / public_key_data['key_path'])
    print(f"  ✅ {signing_key_id}.pub")
    
    # Collect and copy evidence
    print("Collecting Phase-8 evidence...")
    evidence_data = collect_evidence(evidence_dir)
    shutil.copy2(evidence_dir / 'evidence_bundle.json', bundle_dir / evidence_data['bundle_path'])
    shutil.copy2(evidence_dir / 'evidence_bundle.json.sig', bundle_dir / evidence_data['signature_path'])
    print("  ✅ Evidence bundle and signature")
    
    # Collect and copy metadata
    print("Collecting metadata...")
    metadata_data = collect_metadata(metadata_dir)
    if 'build_info_path' in metadata_data:
        shutil.copy2(metadata_dir / 'build-info.json', bundle_dir / metadata_data['build_info_path'])
    if 'build_environment_path' in metadata_data:
        shutil.copy2(metadata_dir / 'build-environment.json', bundle_dir / metadata_data['build_environment_path'])
    print("  ✅ Build metadata")
    
    # Create RELEASE_MANIFEST.json
    print("Creating RELEASE_MANIFEST.json...")
    manifest = create_release_manifest(
        version=version,
        artifacts=artifacts,
        signatures=signatures,
        sbom=sbom_data,
        public_key=public_key_data,
        evidence=evidence_data,
        metadata=metadata_data,
        project_root=project_root
    )
    
    manifest_path = bundle_dir / 'RELEASE_MANIFEST.json'
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    # Compute manifest hash
    manifest_sha256 = compute_file_hash(manifest_path)
    print(f"  ✅ RELEASE_MANIFEST.json (SHA256: {manifest_sha256[:16]}...)")
    
    # Create tarball
    print("Creating release bundle tarball...")
    source_date_epoch = os.environ.get('SOURCE_DATE_EPOCH', str(int(datetime.now(timezone.utc).timestamp())))
    
    tarball_path = output_dir / f"{bundle_name}.tar.gz"
    with tarfile.open(tarball_path, 'w:gz') as tar:
        tar.add(
            bundle_dir,
            arcname=bundle_name,
            recursive=True,
            filter=lambda tarinfo: tarinfo  # Include all files
        )
        # Set deterministic timestamps
        for member in tar.getmembers():
            member.mtime = int(source_date_epoch)
    
    tarball_size = tarball_path.stat().st_size
    tarball_sha256 = compute_file_hash(tarball_path)
    
    print(f"✅ Release bundle created: {tarball_path.name}")
    print(f"   Size: {tarball_size:,} bytes")
    print(f"   SHA256: {tarball_sha256}")
    print(f"   Manifest SHA256: {manifest_sha256}")
    
    # Write bundle checksum file
    checksum_path = output_dir / f"{bundle_name}.tar.gz.sha256"
    with open(checksum_path, 'w') as f:
        f.write(f"{tarball_sha256}  {tarball_path.name}\n")
    print(f"   Checksum: {checksum_path.name}")
    
    return tarball_path


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Create RansomEye Release Bundle'
    )
    parser.add_argument(
        '--version',
        required=True,
        help='Release version (e.g., v1.0.0)'
    )
    parser.add_argument(
        '--build-artifacts-dir',
        type=Path,
        default=Path('build/artifacts'),
        help='Directory containing build artifacts'
    )
    parser.add_argument(
        '--signed-artifacts-dir',
        type=Path,
        default=Path('build/artifacts/signed'),
        help='Directory containing signed artifacts'
    )
    parser.add_argument(
        '--sbom-dir',
        type=Path,
        default=Path('build/artifacts/sbom'),
        help='Directory containing SBOM'
    )
    parser.add_argument(
        '--public-keys-dir',
        type=Path,
        default=Path('build/artifacts/public-keys'),
        help='Directory containing public keys'
    )
    parser.add_argument(
        '--evidence-dir',
        type=Path,
        default=Path('validation/evidence_bundle'),
        help='Directory containing Phase-8 evidence'
    )
    parser.add_argument(
        '--metadata-dir',
        type=Path,
        default=Path('build/artifacts'),
        help='Directory containing build metadata'
    )
    parser.add_argument(
        '--signing-key-id',
        required=True,
        help='Signing key identifier'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('release/bundles'),
        help='Output directory for release bundle'
    )
    parser.add_argument(
        '--project-root',
        type=Path,
        default=Path('.'),
        help='Project root directory'
    )
    
    args = parser.parse_args()
    
    try:
        bundle_path = create_release_bundle(
            version=args.version,
            build_artifacts_dir=Path(args.build_artifacts_dir),
            signed_artifacts_dir=Path(args.signed_artifacts_dir),
            sbom_dir=Path(args.sbom_dir),
            public_keys_dir=Path(args.public_keys_dir),
            evidence_dir=Path(args.evidence_dir),
            metadata_dir=Path(args.metadata_dir),
            signing_key_id=args.signing_key_id,
            output_dir=Path(args.output_dir),
            project_root=Path(args.project_root)
        )
        
        print("")
        print("=" * 70)
        print("✅ Release Bundle Creation Complete")
        print("=" * 70)
        print(f"Bundle: {bundle_path}")
        print(f"Checksum: {bundle_path}.sha256")
        print("")
        print("The release bundle is self-contained and can be verified offline.")
        print("No CI access or artifact retention is required for verification.")
        
    except ReleaseBundleError as e:
        print(f"❌ ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
