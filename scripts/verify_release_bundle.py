#!/usr/bin/env python3
"""
RansomEye v1.0 Release Bundle Verifier
AUTHORITATIVE: Offline verification of release bundles
Phase-9: Independent release gate verification
"""

import os
import sys
import json
import hashlib
import tarfile
from pathlib import Path
from typing import Dict, Any, Optional

# Add supply-chain to path
_supply_chain_dir = Path(__file__).parent.parent / "supply-chain"
sys.path.insert(0, str(_supply_chain_dir))

from crypto.persistent_signing_authority import PersistentSigningAuthority, PersistentSigningAuthorityError
from crypto.key_registry import KeyRegistry, KeyRegistryError


class ReleaseBundleVerificationError(Exception):
    """Base exception for release bundle verification errors."""
    pass


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of file."""
    hash_obj = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def verify_bundle_integrity(bundle_path: Path, checksum_path: Optional[Path] = None) -> bool:
    """Verify bundle tarball integrity."""
    if not bundle_path.exists():
        raise ReleaseBundleVerificationError(f"Bundle not found: {bundle_path}")
    
    # Verify tarball can be extracted
    try:
        with tarfile.open(bundle_path, 'r:gz') as tar:
            tar.getmembers()  # Test extraction
    except Exception as e:
        raise ReleaseBundleVerificationError(f"Bundle is corrupted or invalid: {e}") from e
    
    # Verify checksum if provided
    if checksum_path and checksum_path.exists():
        expected_hash = checksum_path.read_text().split()[0]
        actual_hash = compute_file_hash(bundle_path)
        if expected_hash != actual_hash:
            raise ReleaseBundleVerificationError(
                f"Bundle checksum mismatch: expected {expected_hash[:16]}..., got {actual_hash[:16]}..."
            )
    
    return True


def verify_release_manifest(bundle_dir: Path) -> Dict[str, Any]:
    """Verify and load RELEASE_MANIFEST.json."""
    manifest_path = bundle_dir / 'RELEASE_MANIFEST.json'
    
    if not manifest_path.exists():
        raise ReleaseBundleVerificationError("RELEASE_MANIFEST.json not found in bundle")
    
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        raise ReleaseBundleVerificationError(f"RELEASE_MANIFEST.json is invalid JSON: {e}") from e
    
    # Verify manifest structure
    required_fields = ['version', 'release_version', 'artifacts', 'signatures', 'sbom', 'public_keys', 'evidence']
    for field in required_fields:
        if field not in manifest:
            raise ReleaseBundleVerificationError(f"RELEASE_MANIFEST.json missing required field: {field}")
    
    return manifest


def verify_artifacts_match_manifest(bundle_dir: Path, manifest: Dict[str, Any]) -> bool:
    """Verify all artifacts exist and match manifest hashes."""
    for artifact in manifest['artifacts']:
        artifact_path = bundle_dir / artifact['path']
        
        if not artifact_path.exists():
            raise ReleaseBundleVerificationError(f"Artifact not found: {artifact['path']}")
        
        actual_hash = compute_file_hash(artifact_path)
        if actual_hash != artifact['sha256']:
            raise ReleaseBundleVerificationError(
                f"Artifact hash mismatch for {artifact['name']}: "
                f"expected {artifact['sha256'][:16]}..., got {actual_hash[:16]}..."
            )
    
    return True


def verify_signatures(
    bundle_dir: Path,
    manifest: Dict[str, Any],
    registry_path: Optional[Path] = None
) -> bool:
    """Verify all artifact signatures using bundled public keys."""
    # Get public key from bundle
    if not manifest['public_keys']:
        raise ReleaseBundleVerificationError("No public keys in bundle")
    
    public_key_info = manifest['public_keys'][0]
    public_key_path = bundle_dir / public_key_info['key_path']
    
    if not public_key_path.exists():
        raise ReleaseBundleVerificationError(f"Public key not found: {public_key_info['key_path']}")
    
    # Verify public key hash matches manifest
    actual_key_hash = compute_file_hash(public_key_path)
    if actual_key_hash != public_key_info['key_sha256']:
        raise ReleaseBundleVerificationError("Public key hash mismatch")
    
    # Check revocation if registry provided
    if registry_path and registry_path.exists():
        try:
            registry = KeyRegistry(registry_path)
            key_id = public_key_info['key_id']
            
            if registry.is_revoked(key_id):
                raise ReleaseBundleVerificationError(f"Signing key {key_id} is REVOKED")
            
            if not registry.is_key_active(key_id):
                key_entry = registry.get_key(key_id)
                status = key_entry['status'] if key_entry else 'unknown'
                raise ReleaseBundleVerificationError(f"Signing key {key_id} is not active (status: {status})")
        except (KeyRegistryError, PersistentSigningAuthorityError) as e:
            # Registry check is optional - warn but don't fail
            print(f"⚠️  WARNING: Could not check key revocation: {e}", file=sys.stderr)
    
    # Verify each artifact signature
    from crypto.artifact_verifier import ArtifactVerifier
    from cryptography.hazmat.primitives import serialization
    
    # Load public key
    public_key_bytes = public_key_path.read_bytes()
    public_key = serialization.load_pem_public_key(
        public_key_bytes,
        backend=None
    )
    verifier = ArtifactVerifier(public_key=public_key)
    
    for sig_info in manifest['signatures']:
        artifact_name = sig_info['artifact_name']
        artifact_path = bundle_dir / 'artifacts' / artifact_name
        manifest_path = bundle_dir / sig_info['manifest_path']
        sig_path = bundle_dir / sig_info['signature_path']
        
        if not artifact_path.exists():
            raise ReleaseBundleVerificationError(f"Artifact not found for signature verification: {artifact_name}")
        if not manifest_path.exists():
            raise ReleaseBundleVerificationError(f"Manifest not found: {sig_info['manifest_path']}")
        if not sig_path.exists():
            raise ReleaseBundleVerificationError(f"Signature not found: {sig_info['signature_path']}")
        
        # Verify signature using artifact verifier
        # Load manifest
        with open(manifest_path, 'r') as f:
            manifest_data = json.load(f)
        
        # Load signature and add to manifest for verification
        signature = sig_path.read_text(encoding='utf-8').strip()
        manifest_data['signature'] = signature
        
        # Verify signature
        if not verifier.verify_manifest_signature(manifest_data):
            raise ReleaseBundleVerificationError(
                f"Signature verification failed for {artifact_name}"
            )
    
    return True


def verify_sbom(bundle_dir: Path, manifest: Dict[str, Any]) -> bool:
    """Verify SBOM and SBOM signature."""
    sbom_info = manifest['sbom']
    sbom_manifest_path = bundle_dir / sbom_info['manifest_path']
    sbom_sig_path = bundle_dir / sbom_info['signature_path']
    
    if not sbom_manifest_path.exists():
        raise ReleaseBundleVerificationError("SBOM manifest not found")
    if not sbom_sig_path.exists():
        raise ReleaseBundleVerificationError("SBOM signature not found")
    
    # Verify SBOM hash matches manifest
    actual_hash = compute_file_hash(sbom_manifest_path)
    if actual_hash != sbom_info['manifest_sha256']:
        raise ReleaseBundleVerificationError("SBOM manifest hash mismatch")
    
    # Verify SBOM signature using bundled public key
    public_key_info = manifest['public_keys'][0]
    public_key_path = bundle_dir / public_key_info['key_path']
    
    # Verify SBOM signature using artifact verifier
    from crypto.artifact_verifier import ArtifactVerifier
    
    # Load SBOM manifest
    with open(sbom_manifest_path, 'r') as f:
        sbom_manifest = json.load(f)
    
    # Load SBOM signature
    sbom_signature = sbom_sig_path.read_text(encoding='utf-8').strip()
    sbom_manifest['signature'] = sbom_signature
    
    # Verify signature
    verifier = ArtifactVerifier(public_key_path=public_key_path)
    if not verifier.verify_manifest_signature(sbom_manifest):
        raise ReleaseBundleVerificationError("SBOM signature verification failed")
    
    return True


def verify_evidence(bundle_dir: Path, manifest: Dict[str, Any]) -> bool:
    """Verify Phase-8 evidence bundle."""
    evidence_info = manifest['evidence']
    evidence_path = bundle_dir / evidence_info['bundle_path']
    evidence_sig_path = bundle_dir / evidence_info['signature_path']
    
    if not evidence_path.exists():
        raise ReleaseBundleVerificationError("Evidence bundle not found")
    if not evidence_sig_path.exists():
        raise ReleaseBundleVerificationError("Evidence bundle signature not found")
    
    # Verify evidence bundle hash matches manifest
    actual_hash = compute_file_hash(evidence_path)
    if actual_hash != evidence_info['bundle_sha256']:
        raise ReleaseBundleVerificationError("Evidence bundle hash mismatch")
    
    # Verify GA verdict is PASS
    with open(evidence_path, 'r') as f:
        evidence_data = json.load(f)
    
    ga_verdict = evidence_data.get('overall_status', 'UNKNOWN')
    if ga_verdict != 'PASS':
        raise ReleaseBundleVerificationError(f"GA verdict is {ga_verdict} (must be PASS)")
    
    # Verify evidence bundle signature using bundled public key
    public_key_info = manifest['public_keys'][0]
    public_key_path = bundle_dir / public_key_info['key_path']
    
    # Use artifact verifier for evidence bundle (same signing mechanism)
    from crypto.artifact_verifier import ArtifactVerifier
    
    verifier = ArtifactVerifier(public_key_path=public_key_path)
    
    # Load evidence bundle and signature
    with open(evidence_path, 'r') as f:
        evidence_bundle = json.load(f)
    
    signature = evidence_sig_path.read_text(encoding='utf-8').strip()
    evidence_bundle['signature'] = signature
    
    # Verify signature
    if not verifier.verify_manifest_signature(evidence_bundle):
        raise ReleaseBundleVerificationError("Evidence bundle signature verification failed")
    
    return True


def verify_release_bundle(
    bundle_path: Path,
    checksum_path: Optional[Path] = None,
    registry_path: Optional[Path] = None,
    extract_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Verify complete release bundle.
    
    Returns:
        Verification result dictionary
    """
    results = {
        'bundle_integrity': False,
        'manifest_valid': False,
        'artifacts_match': False,
        'signatures_valid': False,
        'sbom_valid': False,
        'evidence_valid': False,
        'overall_status': 'FAIL'
    }
    
    # Extract bundle if needed
    if extract_dir is None:
        extract_dir = bundle_path.parent / f"{bundle_path.stem}-extracted"
    
    extract_dir = Path(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract bundle
    print("Extracting release bundle...")
    with tarfile.open(bundle_path, 'r:gz') as tar:
        tar.extractall(extract_dir)
    
    bundle_dir = extract_dir / bundle_path.stem.replace('.tar.gz', '')
    
    # Verify bundle integrity
    print("Verifying bundle integrity...")
    verify_bundle_integrity(bundle_path, checksum_path)
    results['bundle_integrity'] = True
    print("  ✅ Bundle integrity verified")
    
    # Verify release manifest
    print("Verifying RELEASE_MANIFEST.json...")
    manifest = verify_release_manifest(bundle_dir)
    results['manifest_valid'] = True
    print(f"  ✅ Release version: {manifest['release_version']}")
    
    # Verify artifacts match manifest
    print("Verifying artifacts match manifest...")
    verify_artifacts_match_manifest(bundle_dir, manifest)
    results['artifacts_match'] = True
    print(f"  ✅ {len(manifest['artifacts'])} artifacts verified")
    
    # Verify signatures
    print("Verifying artifact signatures...")
    verify_signatures(bundle_dir, manifest, registry_path)
    results['signatures_valid'] = True
    print(f"  ✅ {len(manifest['signatures'])} signatures verified")
    
    # Verify SBOM
    print("Verifying SBOM...")
    verify_sbom(bundle_dir, manifest)
    results['sbom_valid'] = True
    print("  ✅ SBOM verified")
    
    # Verify evidence
    print("Verifying Phase-8 evidence...")
    verify_evidence(bundle_dir, manifest)
    results['evidence_valid'] = True
    print("  ✅ Evidence bundle verified (GA verdict: PASS)")
    
    # All checks passed
    results['overall_status'] = 'PASS'
    
    return results


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Verify RansomEye Release Bundle'
    )
    parser.add_argument(
        '--bundle',
        type=Path,
        required=True,
        help='Path to release bundle tarball'
    )
    parser.add_argument(
        '--checksum',
        type=Path,
        help='Path to bundle checksum file (optional)'
    )
    parser.add_argument(
        '--registry-path',
        type=Path,
        help='Path to key registry for revocation checking (optional)'
    )
    parser.add_argument(
        '--extract-dir',
        type=Path,
        help='Directory to extract bundle (default: next to bundle)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Path to write verification report (optional)'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("RansomEye v1.0 Release Bundle Verification")
    print("=" * 70)
    print(f"Bundle: {args.bundle}")
    print("")
    
    try:
        results = verify_release_bundle(
            bundle_path=args.bundle,
            checksum_path=args.checksum,
            registry_path=args.registry_path,
            extract_dir=args.extract_dir
        )
        
        print("")
        print("=" * 70)
        if results['overall_status'] == 'PASS':
            print("✅ RELEASE BUNDLE VERIFICATION PASSED")
            print("=" * 70)
            print("")
            print("All verification checks passed:")
            print("  ✅ Bundle integrity")
            print("  ✅ Release manifest")
            print("  ✅ Artifacts match manifest")
            print("  ✅ All signatures verified")
            print("  ✅ SBOM verified")
            print("  ✅ Phase-8 evidence verified (GA verdict: PASS)")
            print("")
            print("FOR-RELEASE: This bundle is approved for release.")
            sys.exit(0)
        else:
            print("❌ RELEASE BUNDLE VERIFICATION FAILED")
            print("=" * 70)
            print("")
            print("Verification results:")
            for check, passed in results.items():
                if check != 'overall_status':
                    status = "✅" if passed else "❌"
                    print(f"  {status} {check}")
            print("")
            print("DO-NOT-RELEASE: This bundle failed verification.")
            sys.exit(1)
        
    except ReleaseBundleVerificationError as e:
        print(f"❌ VERIFICATION FAILED: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Write verification report if requested
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    main()
