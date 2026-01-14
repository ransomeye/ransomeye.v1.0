#!/usr/bin/env python3
"""
RansomEye v1.0 Phase 8.2 Release Artifact Integrity (Offline)
AUTHORITATIVE: Offline verification of release artifacts and SBOM
Phase 8.2 requirement: Fully offline integrity checks before release
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
        from engine.verification_engine import VerificationEngine, VerificationEngineError
        _supply_chain_available = True
    else:
        _supply_chain_available = False
except ImportError:
    _supply_chain_available = False

# Try to import from release module
try:
    _release_dir = _project_root / "release"
    if _release_dir.exists():
        sys.path.insert(0, str(_release_dir))
        from verify_sbom import verify_sbom, SBOMVerificationError, compute_file_hash
        _release_available = True
    else:
        _release_available = False
except ImportError:
    _release_available = False

# Results structure
results = {
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'artifacts': [],
    'sbom_status': {},
    'overall_status': 'UNKNOWN'
}


def add_artifact_check(artifact_name: str, check_name: str, status: str, message: str = '', error: str = ''):
    """Add a check result to an artifact's checks array."""
    # Find or create artifact entry
    artifact_entry = None
    for art in results['artifacts']:
        if art['name'] == artifact_name:
            artifact_entry = art
            break
    
    if artifact_entry is None:
        artifact_entry = {
            'name': artifact_name,
            'checks': [],
            'status': 'UNKNOWN'
        }
        results['artifacts'].append(artifact_entry)
    
    # Add check
    check = {
        'name': check_name,
        'status': status,  # 'PASS', 'FAIL'
        'message': message,
        'error': error
    }
    artifact_entry['checks'].append(check)
    
    # Update artifact status (FAIL if any check fails)
    if status == 'FAIL':
        artifact_entry['status'] = 'FAIL'
    elif artifact_entry['status'] == 'UNKNOWN' and status == 'PASS':
        artifact_entry['status'] = 'PASS'
    
    return status == 'PASS'


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    hash_obj = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def find_artifact_files(release_root: Path) -> Dict[str, Path]:
    """
    Find artifact files in release root.
    
    Expected artifacts:
    - core installer (core-installer*.tar.gz or core-installer*.zip)
    - linux-agent (linux-agent*.tar.gz or linux-agent*.zip)
    - windows-agent (windows-agent*.tar.gz or windows-agent*.zip)
    - dpi-probe (dpi-probe*.tar.gz or dpi-probe*.zip)
    """
    artifacts = {}
    
    # Look for artifact files
    for pattern in ['*.tar.gz', '*.zip']:
        for artifact_file in release_root.glob(pattern):
            name = artifact_file.name.lower()
            if 'core' in name and 'installer' in name:
                artifacts['core-installer'] = artifact_file
            elif 'linux-agent' in name or 'linux_agent' in name:
                artifacts['linux-agent'] = artifact_file
            elif 'windows-agent' in name or 'windows_agent' in name:
                artifacts['windows-agent'] = artifact_file
            elif 'dpi-probe' in name or 'dpi_probe' in name:
                artifacts['dpi-probe'] = artifact_file
    
    return artifacts


def verify_artifact(
    artifact_name: str,
    artifact_path: Path,
    release_root: Path,
    verifier: ArtifactVerifier
) -> bool:
    """
    Verify a single artifact.
    
    Checks:
    1. Artifact file exists
    2. Manifest file exists
    3. Signature file exists
    4. SHA256 matches manifest
    5. ed25519 signature verifies
    """
    all_passed = True
    
    # Check 1: Artifact exists
    if not artifact_path.exists():
        add_artifact_check(artifact_name, 'artifact_exists', 'FAIL', '', f'Artifact file not found: {artifact_path}')
        return False
    add_artifact_check(artifact_name, 'artifact_exists', 'PASS', f'Artifact file found: {artifact_path.name}')
    
    # Check 2: Manifest exists
    # Look for manifest in signed/ subdirectory or same directory
    manifest_paths = [
        release_root / 'signed' / f'{artifact_path.name}.manifest.json',
        artifact_path.parent / f'{artifact_path.name}.manifest.json',
        release_root / f'{artifact_path.name}.manifest.json'
    ]
    
    manifest_path = None
    for path in manifest_paths:
        if path.exists():
            manifest_path = path
            break
    
    if manifest_path is None:
        add_artifact_check(artifact_name, 'manifest_exists', 'FAIL', '', f'Manifest file not found for {artifact_path.name}')
        return False
    add_artifact_check(artifact_name, 'manifest_exists', 'PASS', f'Manifest file found: {manifest_path}')
    
    # Check 3: Signature exists
    signature_paths = [
        release_root / 'signed' / f'{artifact_path.name}.manifest.sig',
        manifest_path.parent / f'{manifest_path.name}.sig',
        manifest_path.with_suffix('.sig')
    ]
    
    signature_path = None
    for path in signature_paths:
        if path.exists():
            signature_path = path
            break
    
    if signature_path is None:
        add_artifact_check(artifact_name, 'signature_exists', 'FAIL', '', f'Signature file not found for {artifact_path.name}')
        all_passed = False
    else:
        add_artifact_check(artifact_name, 'signature_exists', 'PASS', f'Signature file found: {signature_path}')
    
    # Load manifest
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    except Exception as e:
        add_artifact_check(artifact_name, 'manifest_load', 'FAIL', '', f'Failed to load manifest: {e}')
        return False
    
    # Check 4: SHA256 matches manifest
    expected_sha256 = manifest.get('sha256', '')
    if not expected_sha256:
        add_artifact_check(artifact_name, 'sha256_in_manifest', 'FAIL', '', 'Manifest missing SHA256 hash')
        all_passed = False
    else:
        computed_sha256 = compute_sha256(artifact_path)
        if computed_sha256.lower() != expected_sha256.lower():
            add_artifact_check(
                artifact_name, 'sha256_match', 'FAIL', '',
                f'SHA256 mismatch: expected {expected_sha256}, computed {computed_sha256}'
            )
            all_passed = False
        else:
            add_artifact_check(artifact_name, 'sha256_match', 'PASS', f'SHA256 matches manifest: {computed_sha256}')
    
    # Check 5: ed25519 signature verifies
    if signature_path and signature_path.exists():
        try:
            # Load signature
            signature = signature_path.read_text(encoding='utf-8').strip()
            
            # Add signature to manifest for verification
            manifest_with_sig = manifest.copy()
            manifest_with_sig['signature'] = signature
            
            # Verify signature
            if verifier.verify_manifest_signature(manifest_with_sig):
                add_artifact_check(artifact_name, 'signature_verify', 'PASS', 'ed25519 signature verified')
            else:
                add_artifact_check(artifact_name, 'signature_verify', 'FAIL', '', 'ed25519 signature verification failed')
                all_passed = False
        except Exception as e:
            add_artifact_check(artifact_name, 'signature_verify', 'FAIL', '', f'Signature verification error: {e}')
            all_passed = False
    else:
        # Use signature from manifest if available
        if manifest.get('signature'):
            manifest_with_sig = manifest.copy()
            if verifier.verify_manifest_signature(manifest_with_sig):
                add_artifact_check(artifact_name, 'signature_verify', 'PASS', 'ed25519 signature verified (from manifest)')
            else:
                add_artifact_check(artifact_name, 'signature_verify', 'FAIL', '', 'ed25519 signature verification failed')
                all_passed = False
        else:
            add_artifact_check(artifact_name, 'signature_verify', 'FAIL', '', 'No signature found in manifest or signature file')
            all_passed = False
    
    return all_passed


def verify_sbom_integrity(
    release_root: Path,
    key_dir: Optional[Path] = None,
    signing_key_id: Optional[str] = None,
    public_key_path: Optional[Path] = None
) -> bool:
    """
    Verify SBOM integrity.
    
    Checks:
    1. SBOM exists (manifest.json)
    2. SBOM signature exists (manifest.json.sig)
    3. SBOM signature verifies
    4. SBOM references all artifacts exactly once
    """
    all_passed = True
    
    # Check 1: SBOM exists
    sbom_manifest_path = release_root / 'manifest.json'
    if not sbom_manifest_path.exists():
        results['sbom_status'] = {
            'status': 'FAIL',
            'checks': [{
                'name': 'sbom_exists',
                'status': 'FAIL',
                'message': '',
                'error': f'SBOM manifest not found: {sbom_manifest_path}'
            }]
        }
        return False
    
    results['sbom_status']['checks'] = []
    results['sbom_status']['checks'].append({
        'name': 'sbom_exists',
        'status': 'PASS',
        'message': f'SBOM manifest found: {sbom_manifest_path}',
        'error': ''
    })
    
    # Check 2: SBOM signature exists
    sbom_signature_path = release_root / 'manifest.json.sig'
    if not sbom_signature_path.exists():
        results['sbom_status']['checks'].append({
            'name': 'sbom_signature_exists',
            'status': 'FAIL',
            'message': '',
            'error': f'SBOM signature not found: {sbom_signature_path}'
        })
        all_passed = False
    else:
        results['sbom_status']['checks'].append({
            'name': 'sbom_signature_exists',
            'status': 'PASS',
            'message': f'SBOM signature found: {sbom_signature_path}',
            'error': ''
        })
    
    # Check 3: SBOM signature verifies
    if _release_available and sbom_signature_path.exists():
        try:
            verify_sbom(
                release_root=release_root,
                manifest_path=sbom_manifest_path,
                signature_path=sbom_signature_path,
                key_dir=key_dir,
                signing_key_id=signing_key_id,
                public_key_path=public_key_path
            )
            results['sbom_status']['checks'].append({
                'name': 'sbom_signature_verify',
                'status': 'PASS',
                'message': 'SBOM signature verified successfully',
                'error': ''
            })
        except SBOMVerificationError as e:
            results['sbom_status']['checks'].append({
                'name': 'sbom_signature_verify',
                'status': 'FAIL',
                'message': '',
                'error': f'SBOM signature verification failed: {e}'
            })
            all_passed = False
        except Exception as e:
            results['sbom_status']['checks'].append({
                'name': 'sbom_signature_verify',
                'status': 'FAIL',
                'message': '',
                'error': f'SBOM verification error: {e}'
            })
            all_passed = False
    else:
        if not _release_available:
            results['sbom_status']['checks'].append({
                'name': 'sbom_signature_verify',
                'status': 'FAIL',
                'message': '',
                'error': 'SBOM verification module not available (release/verify_sbom.py)'
            })
            all_passed = False
    
    # Check 4: SBOM references all artifacts exactly once
    try:
        manifest = json.loads(sbom_manifest_path.read_text(encoding='utf-8'))
        artifacts = manifest.get('artifacts', [])
        
        # Count references by artifact name
        artifact_refs = {}
        for artifact in artifacts:
            artifact_name = artifact.get('name', '')
            artifact_type = artifact.get('type', '')
            
            # Map artifact types to expected artifact names
            if artifact_type == 'core':
                key = 'core-installer'
            elif artifact_type == 'linux_agent':
                key = 'linux-agent'
            elif artifact_type == 'windows_agent':
                key = 'windows-agent'
            elif artifact_type == 'dpi_probe':
                key = 'dpi-probe'
            else:
                continue  # Skip non-artifact entries
            
            if key not in artifact_refs:
                artifact_refs[key] = []
            artifact_refs[key].append(artifact)
        
        # Check each expected artifact is referenced exactly once
        expected_artifacts = ['core-installer', 'linux-agent', 'windows-agent', 'dpi-probe']
        for expected in expected_artifacts:
            ref_count = len(artifact_refs.get(expected, []))
            if ref_count == 0:
                results['sbom_status']['checks'].append({
                    'name': 'sbom_references',
                    'status': 'FAIL',
                    'message': '',
                    'error': f'SBOM does not reference {expected}'
                })
                all_passed = False
            elif ref_count > 1:
                results['sbom_status']['checks'].append({
                    'name': 'sbom_references',
                    'status': 'FAIL',
                    'message': '',
                    'error': f'SBOM references {expected} {ref_count} times (expected exactly once)'
                })
                all_passed = False
            else:
                results['sbom_status']['checks'].append({
                    'name': f'sbom_references_{expected}',
                    'status': 'PASS',
                    'message': f'SBOM references {expected} exactly once',
                    'error': ''
                })
        
    except Exception as e:
        results['sbom_status']['checks'].append({
            'name': 'sbom_references',
            'status': 'FAIL',
            'message': '',
            'error': f'Failed to check SBOM references: {e}'
        })
        all_passed = False
    
    results['sbom_status']['status'] = 'PASS' if all_passed else 'FAIL'
    return all_passed


def main():
    """Main entry point."""
    print("RansomEye v1.0 Phase 8.2 Release Artifact Integrity Check", file=sys.stderr)
    print("=" * 70, file=sys.stderr)
    
    # Get configuration from environment
    release_root = Path(os.getenv('RANSOMEYE_RELEASE_ROOT', './build/artifacts'))
    key_dir = os.getenv('RANSOMEYE_SIGNING_KEY_DIR')
    signing_key_id = os.getenv('RANSOMEYE_SIGNING_KEY_ID', 'vendor-release-key-1')
    
    if not release_root.exists():
        print(f"ERROR: Release root not found: {release_root}", file=sys.stderr)
        print("Set RANSOMEYE_RELEASE_ROOT environment variable", file=sys.stderr)
        results['overall_status'] = 'FAIL'
        results['error'] = f'Release root not found: {release_root}'
        _write_results()
        sys.exit(1)
    
    print(f"Release root: {release_root}", file=sys.stderr)
    
    # Initialize verifier
    verifier = None
    if _supply_chain_available:
        if key_dir:
            try:
                key_manager = VendorKeyManager(Path(key_dir))
                public_key = key_manager.get_public_key(signing_key_id)
                if public_key:
                    verifier = ArtifactVerifier(public_key=public_key)
                    print(f"Using public key from key_dir: {key_dir} (key_id: {signing_key_id})", file=sys.stderr)
                else:
                    print(f"WARNING: Public key not found: {signing_key_id} in {key_dir}", file=sys.stderr)
            except Exception as e:
                print(f"WARNING: Failed to load key from key_dir: {e}", file=sys.stderr)
        
        # Try to find public key in release root
        if verifier is None:
            public_key_paths = [
                release_root / 'public_key.pem',
                release_root / 'keys' / f'{signing_key_id}.pub',
                release_root / 'keys' / 'public_key.pem'
            ]
            for pub_key_path in public_key_paths:
                if pub_key_path.exists():
                    try:
                        verifier = ArtifactVerifier(public_key_path=pub_key_path)
                        print(f"Using public key from: {pub_key_path}", file=sys.stderr)
                        break
                    except Exception as e:
                        continue
        
        if verifier is None:
            print("ERROR: No public key found. Set RANSOMEYE_SIGNING_KEY_DIR or place public_key.pem in release root", file=sys.stderr)
            results['overall_status'] = 'FAIL'
            results['error'] = 'No public key found for signature verification'
            _write_results()
            sys.exit(1)
    else:
        print("ERROR: Supply-chain verification module not available", file=sys.stderr)
        results['overall_status'] = 'FAIL'
        results['error'] = 'Supply-chain verification module not available'
        _write_results()
        sys.exit(1)
    
    # Find artifacts
    print("\nFinding artifacts...", file=sys.stderr)
    artifacts = find_artifact_files(release_root)
    
    expected_artifacts = ['core-installer', 'linux-agent', 'windows-agent', 'dpi-probe']
    missing_artifacts = []
    for expected in expected_artifacts:
        if expected not in artifacts:
            missing_artifacts.append(expected)
            # Create artifact entry with failure
            add_artifact_check(expected, 'artifact_exists', 'FAIL', '', f'Artifact file not found: {expected}')
    
    if missing_artifacts:
        print(f"WARNING: Missing artifacts: {', '.join(missing_artifacts)}", file=sys.stderr)
    
    # Verify each artifact
    print("\nVerifying artifacts...", file=sys.stderr)
    all_artifacts_passed = True
    for artifact_name, artifact_path in artifacts.items():
        print(f"  Verifying {artifact_name}...", file=sys.stderr)
        if not verify_artifact(artifact_name, artifact_path, release_root, verifier):
            all_artifacts_passed = False
    
    # Verify SBOM
    print("\nVerifying SBOM...", file=sys.stderr)
    sbom_passed = verify_sbom_integrity(
        release_root=release_root,
        key_dir=Path(key_dir) if key_dir else None,
        signing_key_id=signing_key_id,
        public_key_path=None  # Will use key_dir or find in release_root
    )
    
    # Determine overall status
    if all_artifacts_passed and sbom_passed and not missing_artifacts:
        results['overall_status'] = 'PASS'
        print("\n✓ All checks PASSED", file=sys.stderr)
    else:
        results['overall_status'] = 'FAIL'
        print("\n✗ One or more checks FAILED", file=sys.stderr)
    
    # Print summary
    print("\nArtifact Summary:", file=sys.stderr)
    for artifact in results['artifacts']:
        status_symbol = '✓' if artifact['status'] == 'PASS' else '✗'
        print(f"  {status_symbol} {artifact['name']}: {artifact['status']}", file=sys.stderr)
        for check in artifact['checks']:
            check_symbol = '  ✓' if check['status'] == 'PASS' else '  ✗'
            print(f"{check_symbol} {check['name']}: {check['status']}", file=sys.stderr)
            if check['error']:
                print(f"      Error: {check['error']}", file=sys.stderr)
    
    print(f"\nSBOM Status: {results['sbom_status'].get('status', 'UNKNOWN')}", file=sys.stderr)
    if 'checks' in results['sbom_status']:
        for check in results['sbom_status']['checks']:
            check_symbol = '  ✓' if check['status'] == 'PASS' else '  ✗'
            print(f"{check_symbol} {check['name']}: {check['status']}", file=sys.stderr)
            if check['error']:
                print(f"      Error: {check['error']}", file=sys.stderr)
    
    # Write results
    _write_results()
    
    # Exit with appropriate code
    if results['overall_status'] == 'PASS':
        sys.exit(0)
    else:
        sys.exit(1)


def _write_results():
    """Write results to JSON file."""
    output_file = Path(_project_root) / 'validation' / 'release_integrity' / 'release_integrity_result.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults written to: {output_file}", file=sys.stderr)


if __name__ == '__main__':
    main()
