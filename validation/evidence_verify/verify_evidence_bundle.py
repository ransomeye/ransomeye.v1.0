#!/usr/bin/env python3
"""
RansomEye v1.0 Phase 8.4 Independent Verification & Forensic Rehydration
AUTHORITATIVE: Read-only verification of evidence bundle
Phase 8.4 requirement: Independent third-party verification without trust in build system
"""

import os
import sys
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Try to import from supply-chain module
try:
    _supply_chain_dir = _project_root / "supply-chain"
    if _supply_chain_dir.exists():
        sys.path.insert(0, str(_supply_chain_dir))
        from crypto.artifact_verifier import ArtifactVerifier, ArtifactVerificationError
        from crypto.vendor_key_manager import VendorKeyManager, VendorKeyManagerError
        _supply_chain_available = True
    else:
        _supply_chain_available = False
except ImportError:
    _supply_chain_available = False

# Verification report structure
report = {
    'verified_at': datetime.now(timezone.utc).isoformat(),
    'signature_valid': False,
    'hash_integrity': 'FAIL',
    'artifact_integrity': 'FAIL',
    'sbom_integrity': 'FAIL',
    'ga_verdict': 'NOT_PRESENT',
    'final_verdict': 'DO-NOT-RELEASE',
    'failures': []
}


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    hash_obj = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def verify_signature(
    bundle_path: Path,
    signature_path: Path,
    public_key_path: Optional[Path] = None,
    key_dir: Optional[Path] = None,
    signing_key_id: Optional[str] = None
) -> bool:
    """
    Verify evidence bundle signature.
    
    Returns:
        True if signature is valid, False otherwise
    """
    if not _supply_chain_available:
        report['failures'].append('Supply-chain verification module not available')
        return False
    
    try:
        # Load bundle
        with open(bundle_path, 'r') as f:
            bundle = json.load(f)
        
        # Load signature
        if not signature_path.exists():
            report['failures'].append(f'Signature file not found: {signature_path}')
            return False
        
        signature = signature_path.read_text(encoding='utf-8').strip()
        
        # Load public key
        verifier = None
        if public_key_path and public_key_path.exists():
            verifier = ArtifactVerifier(public_key_path=public_key_path)
        elif key_dir and signing_key_id:
            key_manager = VendorKeyManager(key_dir)
            public_key = key_manager.get_public_key(signing_key_id)
            if public_key:
                verifier = ArtifactVerifier(public_key=public_key)
            else:
                report['failures'].append(f'Public key not found: {signing_key_id} in {key_dir}')
                return False
        else:
            report['failures'].append('Either public_key_path or (key_dir + signing_key_id) must be provided')
            return False
        
        # Add signature to bundle for verification
        bundle_with_sig = bundle.copy()
        bundle_with_sig['signature'] = signature
        
        # Verify signature
        if verifier.verify_manifest_signature(bundle_with_sig):
            return True
        else:
            report['failures'].append('Signature verification failed')
            return False
            
    except json.JSONDecodeError as e:
        report['failures'].append(f'Bundle JSON decode error: {e}')
        return False
    except Exception as e:
        report['failures'].append(f'Signature verification error: {e}')
        return False


def verify_bundle_integrity(bundle: Dict[str, Any]) -> bool:
    """
    Verify evidence bundle integrity (schema and required fields).
    
    Returns:
        True if bundle is valid, False otherwise
    """
    # Check bundle_version
    bundle_version = bundle.get('bundle_version', '')
    if bundle_version != '1.0':
        report['failures'].append(f'Invalid bundle_version: {bundle_version} (expected: 1.0)')
        return False
    
    # Check overall_status
    overall_status = bundle.get('overall_status', '')
    if overall_status != 'FROZEN':
        report['failures'].append(f'Invalid overall_status: {overall_status} (expected: FROZEN)')
        return False
    
    # Check required fields
    required_fields = ['created_at', 'host', 'git', 'inputs', 'artifacts', 'sbom']
    for field in required_fields:
        if field not in bundle:
            report['failures'].append(f'Missing required field: {field}')
            return False
    
    # Check git structure
    git = bundle.get('git', {})
    if not isinstance(git, dict):
        report['failures'].append('Invalid git field (must be object)')
        return False
    
    # Check inputs structure
    inputs = bundle.get('inputs', {})
    if not isinstance(inputs, dict):
        report['failures'].append('Invalid inputs field (must be object)')
        return False
    
    if 'runtime_smoke' not in inputs:
        report['failures'].append('Missing inputs.runtime_smoke')
        return False
    
    if 'release_integrity' not in inputs:
        report['failures'].append('Missing inputs.release_integrity')
        return False
    
    # Check artifacts structure
    artifacts = bundle.get('artifacts', [])
    if not isinstance(artifacts, list):
        report['failures'].append('Invalid artifacts field (must be array)')
        return False
    
    # Check sbom structure
    sbom = bundle.get('sbom', {})
    if not isinstance(sbom, dict):
        report['failures'].append('Invalid sbom field (must be object)')
        return False
    
    return True


def verify_hash_integrity(
    bundle: Dict[str, Any],
    project_root: Path
) -> bool:
    """
    Recompute and verify all hashes.
    
    Returns:
        True if all hashes match, False otherwise
    """
    all_passed = True
    
    # Verify Phase 8.1 hash
    phase_8_1_path = project_root / 'validation' / 'runtime_smoke' / 'runtime_smoke_result.json'
    if phase_8_1_path.exists():
        computed_hash = compute_file_hash(phase_8_1_path)
        expected_hash = bundle['inputs'].get('runtime_smoke', '')
        if computed_hash.lower() != expected_hash.lower():
            report['failures'].append(
                f'Phase 8.1 hash mismatch: expected {expected_hash}, computed {computed_hash}'
            )
            all_passed = False
    else:
        report['failures'].append(f'Phase 8.1 result not found: {phase_8_1_path}')
        all_passed = False
    
    # Verify Phase 8.2 hash
    phase_8_2_path = project_root / 'validation' / 'release_integrity' / 'release_integrity_result.json'
    if phase_8_2_path.exists():
        computed_hash = compute_file_hash(phase_8_2_path)
        expected_hash = bundle['inputs'].get('release_integrity', '')
        if computed_hash.lower() != expected_hash.lower():
            report['failures'].append(
                f'Phase 8.2 hash mismatch: expected {expected_hash}, computed {computed_hash}'
            )
            all_passed = False
    else:
        report['failures'].append(f'Phase 8.2 result not found: {phase_8_2_path}')
        all_passed = False
    
    # Verify GA verdict hash (if present)
    ga_verdict_hash = bundle['inputs'].get('ga_verdict')
    if ga_verdict_hash:
        ga_verdict_path = project_root / 'validation' / 'reports' / 'phase_c' / 'phase_c_aggregate_verdict.json'
        if ga_verdict_path.exists():
            computed_hash = compute_file_hash(ga_verdict_path)
            if computed_hash.lower() != ga_verdict_hash.lower():
                report['failures'].append(
                    f'GA verdict hash mismatch: expected {ga_verdict_hash}, computed {computed_hash}'
                )
                all_passed = False
            else:
                report['ga_verdict'] = 'PASS'
        else:
            report['failures'].append(f'GA verdict not found: {ga_verdict_path}')
            all_passed = False
            report['ga_verdict'] = 'FAIL'
    else:
        report['ga_verdict'] = 'NOT_PRESENT'
    
    return all_passed


def verify_artifact_integrity(
    bundle: Dict[str, Any],
    release_root: Path
) -> bool:
    """
    Verify artifact completeness and hashes.
    
    Returns:
        True if all artifacts exist and hashes match, False otherwise
    """
    all_passed = True
    bundle_artifacts = bundle.get('artifacts', [])
    
    # Check each artifact in bundle
    for artifact in bundle_artifacts:
        artifact_name = artifact.get('name', '')
        expected_hash = artifact.get('sha256', '')
        
        if not artifact_name:
            report['failures'].append('Artifact entry missing name')
            all_passed = False
            continue
        
        if not expected_hash:
            report['failures'].append(f'Artifact {artifact_name} missing sha256')
            all_passed = False
            continue
        
        # Find artifact file
        artifact_path = None
        for pattern in ['*.tar.gz', '*.zip']:
            for file_path in release_root.glob(pattern):
                if file_path.name == artifact_name:
                    artifact_path = file_path
                    break
            if artifact_path:
                break
        
        if not artifact_path or not artifact_path.exists():
            report['failures'].append(f'Artifact not found: {artifact_name}')
            all_passed = False
            continue
        
        # Verify hash
        computed_hash = compute_file_hash(artifact_path)
        if computed_hash.lower() != expected_hash.lower():
            report['failures'].append(
                f'Artifact {artifact_name} hash mismatch: expected {expected_hash}, computed {computed_hash}'
            )
            all_passed = False
    
    # Check for extra artifacts (one-to-one mapping with SBOM)
    # This is a completeness check - all artifacts in bundle should exist
    # Note: We don't fail on extra artifacts in release_root, but we verify all bundle artifacts exist
    
    return all_passed


def verify_sbom_integrity(
    bundle: Dict[str, Any],
    release_root: Path
) -> bool:
    """
    Verify SBOM integrity (manifest and signature hashes).
    
    Returns:
        True if SBOM hashes match, False otherwise
    """
    all_passed = True
    sbom = bundle.get('sbom', {})
    
    # Verify SBOM manifest hash
    sbom_manifest_path = release_root / 'manifest.json'
    expected_manifest_hash = sbom.get('sha256', '')
    
    if expected_manifest_hash:
        if sbom_manifest_path.exists():
            computed_hash = compute_file_hash(sbom_manifest_path)
            if computed_hash.lower() != expected_manifest_hash.lower():
                report['failures'].append(
                    f'SBOM manifest hash mismatch: expected {expected_manifest_hash}, computed {computed_hash}'
                )
                all_passed = False
        else:
            report['failures'].append(f'SBOM manifest not found: {sbom_manifest_path}')
            all_passed = False
    else:
        report['failures'].append('SBOM manifest hash missing in bundle')
        all_passed = False
    
    # Verify SBOM signature hash
    sbom_signature_path = release_root / 'manifest.json.sig'
    expected_signature_hash = sbom.get('signature_sha256', '')
    
    if expected_signature_hash:
        if sbom_signature_path.exists():
            computed_hash = compute_file_hash(sbom_signature_path)
            if computed_hash.lower() != expected_signature_hash.lower():
                report['failures'].append(
                    f'SBOM signature hash mismatch: expected {expected_signature_hash}, computed {computed_hash}'
                )
                all_passed = False
        else:
            report['failures'].append(f'SBOM signature not found: {sbom_signature_path}')
            all_passed = False
    else:
        report['failures'].append('SBOM signature hash missing in bundle')
        all_passed = False
    
    return all_passed


def main():
    """Main entry point."""
    print("RansomEye v1.0 Phase 8.4 Independent Verification & Forensic Rehydration", file=sys.stderr)
    print("=" * 70, file=sys.stderr)
    
    # Get configuration from environment
    release_root = Path(os.getenv('RANSOMEYE_RELEASE_ROOT', './build/artifacts'))
    key_dir = os.getenv('RANSOMEYE_SIGNING_KEY_DIR')
    signing_key_id = os.getenv('RANSOMEYE_SIGNING_KEY_ID', 'vendor-release-key-1')
    
    print(f"Project root: {_project_root}", file=sys.stderr)
    print(f"Release root: {release_root}", file=sys.stderr)
    if key_dir:
        print(f"Key directory: {key_dir}", file=sys.stderr)
    print(f"Signing key ID: {signing_key_id}", file=sys.stderr)
    print("", file=sys.stderr)
    
    # Load evidence bundle
    bundle_path = _project_root / 'validation' / 'evidence_bundle' / 'evidence_bundle.json'
    signature_path = _project_root / 'validation' / 'evidence_bundle' / 'evidence_bundle.json.sig'
    
    if not bundle_path.exists():
        report['failures'].append(f'Evidence bundle not found: {bundle_path}')
        report['final_verdict'] = 'DO-NOT-RELEASE'
        _write_report()
        print(f"ERROR: Evidence bundle not found: {bundle_path}", file=sys.stderr)
        sys.exit(1)
    
    if not signature_path.exists():
        report['failures'].append(f'Evidence bundle signature not found: {signature_path}')
        report['final_verdict'] = 'DO-NOT-RELEASE'
        _write_report()
        print(f"ERROR: Evidence bundle signature not found: {signature_path}", file=sys.stderr)
        sys.exit(1)
    
    print("Loading evidence bundle...", file=sys.stderr)
    try:
        with open(bundle_path, 'r') as f:
            bundle = json.load(f)
    except json.JSONDecodeError as e:
        report['failures'].append(f'Bundle JSON decode error: {e}')
        report['final_verdict'] = 'DO-NOT-RELEASE'
        _write_report()
        print(f"ERROR: Bundle is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        report['failures'].append(f'Failed to load bundle: {e}')
        report['final_verdict'] = 'DO-NOT-RELEASE'
        _write_report()
        print(f"ERROR: Failed to load bundle: {e}", file=sys.stderr)
        sys.exit(1)
    
    print("  ✓ Bundle loaded", file=sys.stderr)
    
    # Step A: Verify signature
    print("", file=sys.stderr)
    print("Step A: Verifying signature...", file=sys.stderr)
    public_key_path = None
    key_dir_path = None
    
    # Try to find public key
    if key_dir:
        key_dir_path = Path(key_dir)
        if key_dir_path.exists():
            public_key_path = key_dir_path / f'{signing_key_id}.pub'
            if not public_key_path.exists():
                public_key_path = None
    
    # Try release root
    if not public_key_path or not public_key_path.exists():
        release_pub_key = release_root / 'public_key.pem'
        if release_pub_key.exists():
            public_key_path = release_pub_key
    
    if public_key_path and public_key_path.exists():
        signature_valid = verify_signature(
            bundle_path, signature_path,
            public_key_path=public_key_path
        )
    elif key_dir_path:
        signature_valid = verify_signature(
            bundle_path, signature_path,
            key_dir=key_dir_path,
            signing_key_id=signing_key_id
        )
    else:
        report['failures'].append('No public key found for signature verification')
        signature_valid = False
    
    report['signature_valid'] = signature_valid
    if signature_valid:
        print("  ✓ Signature verified", file=sys.stderr)
    else:
        print("  ✗ Signature verification failed", file=sys.stderr)
    
    # Step B: Verify bundle integrity
    print("", file=sys.stderr)
    print("Step B: Verifying bundle integrity...", file=sys.stderr)
    bundle_valid = verify_bundle_integrity(bundle)
    if bundle_valid:
        print("  ✓ Bundle integrity verified", file=sys.stderr)
    else:
        print("  ✗ Bundle integrity check failed", file=sys.stderr)
    
    # Step C: Verify hash integrity
    print("", file=sys.stderr)
    print("Step C: Recomputing and verifying hashes...", file=sys.stderr)
    hash_valid = verify_hash_integrity(bundle, _project_root)
    if hash_valid:
        report['hash_integrity'] = 'PASS'
        print("  ✓ Hash integrity verified", file=sys.stderr)
    else:
        report['hash_integrity'] = 'FAIL'
        print("  ✗ Hash integrity check failed", file=sys.stderr)
    
    # Step D: Verify artifact integrity
    print("", file=sys.stderr)
    print("Step D: Verifying artifact completeness...", file=sys.stderr)
    artifact_valid = verify_artifact_integrity(bundle, release_root)
    if artifact_valid:
        report['artifact_integrity'] = 'PASS'
        print("  ✓ Artifact integrity verified", file=sys.stderr)
    else:
        report['artifact_integrity'] = 'FAIL'
        print("  ✗ Artifact integrity check failed", file=sys.stderr)
    
    # Verify SBOM integrity
    print("", file=sys.stderr)
    print("Verifying SBOM integrity...", file=sys.stderr)
    sbom_valid = verify_sbom_integrity(bundle, release_root)
    if sbom_valid:
        report['sbom_integrity'] = 'PASS'
        print("  ✓ SBOM integrity verified", file=sys.stderr)
    else:
        report['sbom_integrity'] = 'FAIL'
        print("  ✗ SBOM integrity check failed", file=sys.stderr)
    
    # Determine final verdict
    print("", file=sys.stderr)
    print("Determining final verdict...", file=sys.stderr)
    if (signature_valid and bundle_valid and hash_valid and 
        artifact_valid and sbom_valid and len(report['failures']) == 0):
        report['final_verdict'] = 'FOR-RELEASE'
        print("  ✓ FOR-RELEASE", file=sys.stderr)
    else:
        report['final_verdict'] = 'DO-NOT-RELEASE'
        print("  ✗ DO-NOT-RELEASE", file=sys.stderr)
        if report['failures']:
            print("", file=sys.stderr)
            print("Failures:", file=sys.stderr)
            for failure in report['failures']:
                print(f"  - {failure}", file=sys.stderr)
    
    # Write report
    _write_report()
    
    # Print summary
    print("", file=sys.stderr)
    print("Verification Summary:", file=sys.stderr)
    print(f"  Signature valid: {report['signature_valid']}", file=sys.stderr)
    print(f"  Hash integrity: {report['hash_integrity']}", file=sys.stderr)
    print(f"  Artifact integrity: {report['artifact_integrity']}", file=sys.stderr)
    print(f"  SBOM integrity: {report['sbom_integrity']}", file=sys.stderr)
    print(f"  GA verdict: {report['ga_verdict']}", file=sys.stderr)
    print(f"  Final verdict: {report['final_verdict']}", file=sys.stderr)
    
    # Exit with appropriate code
    if report['final_verdict'] == 'FOR-RELEASE':
        sys.exit(0)
    else:
        sys.exit(1)


def _write_report():
    """Write verification report to JSON file."""
    output_file = _project_root / 'validation' / 'evidence_verify' / 'verification_report.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nVerification report written to: {output_file}", file=sys.stderr)


if __name__ == '__main__':
    main()
