#!/usr/bin/env python3
"""
RansomEye v1.0 Phase 8.3 Evidence Bundle Freezing & Attestation
AUTHORITATIVE: Tamper-evident, immutable evidence bundle creation
Phase 8.3 requirement: Cryptographic freezing of all validation evidence
"""

import os
import sys
import json
import hashlib
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

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
        from crypto.artifact_signer import ArtifactSigner, ArtifactSigningError
        from crypto.persistent_signing_authority import PersistentSigningAuthority, PersistentSigningAuthorityError
        _supply_chain_available = True
    else:
        _supply_chain_available = False
except ImportError:
    _supply_chain_available = False

# Bundle structure
bundle = {
    'bundle_version': '1.0',
    'created_at': '',
    'host': '',
    'git': {
        'repo': '',
        'branch': '',
        'commit': ''
    },
    'inputs': {
        'runtime_smoke': '',
        'release_integrity': '',
        'ga_verdict': None
    },
    'artifacts': [],
    'sbom': {
        'sha256': '',
        'signature_sha256': ''
    },
    'overall_status': 'UNKNOWN'
}


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    hash_obj = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def get_git_info(project_root: Path) -> Dict[str, str]:
    """Get git repository information."""
    git_info = {
        'repo': '',
        'branch': '',
        'commit': ''
    }
    
    try:
        # Get remote URL
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            git_info['repo'] = result.stdout.strip()
    except Exception:
        pass
    
    try:
        # Get current branch
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            git_info['branch'] = result.stdout.strip()
    except Exception:
        pass
    
    try:
        # Get commit hash
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            git_info['commit'] = result.stdout.strip()
    except Exception:
        pass
    
    return git_info


def get_hostname() -> str:
    """Get hostname."""
    try:
        return socket.gethostname()
    except Exception:
        return 'unknown'


def load_and_validate_phase_8_1(project_root: Path) -> Tuple[Dict[str, Any], str]:
    """
    Load and validate Phase 8.1 results.
    
    Returns:
        Tuple of (result_dict, file_hash)
    
    Raises:
        SystemExit: If file missing or overall_status != PASS
    """
    result_path = project_root / 'validation' / 'runtime_smoke' / 'runtime_smoke_result.json'
    
    if not result_path.exists():
        print(f"ERROR: Phase 8.1 result not found: {result_path}", file=sys.stderr)
        sys.exit(1)
    
    try:
        with open(result_path, 'r') as f:
            result = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Phase 8.1 result is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to read Phase 8.1 result: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Validate overall_status
    overall_status = result.get('overall_status', 'UNKNOWN')
    if overall_status != 'PASS':
        print(f"ERROR: Phase 8.1 overall_status is not PASS: {overall_status}", file=sys.stderr)
        sys.exit(1)
    
    # Compute hash
    file_hash = compute_file_hash(result_path)
    
    return result, file_hash


def load_and_validate_phase_8_2(project_root: Path) -> Tuple[Dict[str, Any], str]:
    """
    Load and validate Phase 8.2 results.
    
    Returns:
        Tuple of (result_dict, file_hash)
    
    Raises:
        SystemExit: If file missing or overall_status != PASS
    """
    result_path = project_root / 'validation' / 'release_integrity' / 'release_integrity_result.json'
    
    if not result_path.exists():
        print(f"ERROR: Phase 8.2 result not found: {result_path}", file=sys.stderr)
        sys.exit(1)
    
    try:
        with open(result_path, 'r') as f:
            result = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Phase 8.2 result is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to read Phase 8.2 result: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Validate overall_status
    overall_status = result.get('overall_status', 'UNKNOWN')
    if overall_status != 'PASS':
        print(f"ERROR: Phase 8.2 overall_status is not PASS: {overall_status}", file=sys.stderr)
        sys.exit(1)
    
    # Compute hash
    file_hash = compute_file_hash(result_path)
    
    return result, file_hash


def load_ga_verdict(project_root: Path) -> Optional[Tuple[Dict[str, Any], str]]:
    """
    Load GA verdict if present.
    
    Returns:
        Tuple of (result_dict, file_hash) or None if not found
    """
    result_path = project_root / 'validation' / 'reports' / 'phase_c' / 'phase_c_aggregate_verdict.json'
    
    if not result_path.exists():
        return None
    
    try:
        with open(result_path, 'r') as f:
            result = json.load(f)
    except json.JSONDecodeError as e:
        print(f"WARNING: GA verdict is not valid JSON: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"WARNING: Failed to read GA verdict: {e}", file=sys.stderr)
        return None
    
    # Compute hash
    file_hash = compute_file_hash(result_path)
    
    return result, file_hash


def collect_artifact_hashes(release_root: Path) -> List[Dict[str, str]]:
    """
    Collect artifact hashes from release root.
    
    Returns:
        List of artifact dicts with 'name' and 'sha256'
    """
    artifacts = []
    
    # Find artifact files
    for pattern in ['*.tar.gz', '*.zip']:
        for artifact_file in release_root.glob(pattern):
            name = artifact_file.name
            # Only include actual artifacts (exclude manifests, signatures, etc.)
            if '.manifest' not in name and '.sig' not in name:
                sha256 = compute_file_hash(artifact_file)
                artifacts.append({
                    'name': name,
                    'sha256': sha256
                })
    
    return artifacts


def collect_sbom_info(release_root: Path) -> Dict[str, str]:
    """
    Collect SBOM hash and signature hash.
    
    Returns:
        Dict with 'sha256' and 'signature_sha256'
    """
    sbom_info = {
        'sha256': '',
        'signature_sha256': ''
    }
    
    sbom_manifest_path = release_root / 'manifest.json'
    sbom_signature_path = release_root / 'manifest.json.sig'
    
    if sbom_manifest_path.exists():
        sbom_info['sha256'] = compute_file_hash(sbom_manifest_path)
    
    if sbom_signature_path.exists():
        sbom_info['signature_sha256'] = compute_file_hash(sbom_signature_path)
    
    return sbom_info


def create_evidence_bundle(
    project_root: Path,
    release_root: Path
) -> Dict[str, Any]:
    """Create evidence bundle from all inputs."""
    # Set timestamp
    bundle['created_at'] = datetime.now(timezone.utc).isoformat()
    
    # Set hostname
    bundle['host'] = get_hostname()
    
    # Set git info
    bundle['git'] = get_git_info(project_root)
    
    # Load and validate Phase 8.1
    print("Loading Phase 8.1 results...", file=sys.stderr)
    phase_8_1_result, phase_8_1_hash = load_and_validate_phase_8_1(project_root)
    bundle['inputs']['runtime_smoke'] = phase_8_1_hash
    print(f"  ✓ Phase 8.1: {phase_8_1_hash[:16]}...", file=sys.stderr)
    
    # Load and validate Phase 8.2
    print("Loading Phase 8.2 results...", file=sys.stderr)
    phase_8_2_result, phase_8_2_hash = load_and_validate_phase_8_2(project_root)
    bundle['inputs']['release_integrity'] = phase_8_2_hash
    print(f"  ✓ Phase 8.2: {phase_8_2_hash[:16]}...", file=sys.stderr)
    
    # Load GA verdict (optional)
    print("Loading GA verdict (optional)...", file=sys.stderr)
    ga_verdict = load_ga_verdict(project_root)
    if ga_verdict:
        ga_result, ga_hash = ga_verdict
        bundle['inputs']['ga_verdict'] = ga_hash
        print(f"  ✓ GA verdict: {ga_hash[:16]}...", file=sys.stderr)
    else:
        print("  - GA verdict not found (optional)", file=sys.stderr)
    
    # Collect artifact hashes
    print("Collecting artifact hashes...", file=sys.stderr)
    artifacts = collect_artifact_hashes(release_root)
    bundle['artifacts'] = artifacts
    print(f"  ✓ Found {len(artifacts)} artifacts", file=sys.stderr)
    
    # Collect SBOM info
    print("Collecting SBOM info...", file=sys.stderr)
    sbom_info = collect_sbom_info(release_root)
    bundle['sbom'] = sbom_info
    if sbom_info['sha256']:
        print(f"  ✓ SBOM manifest: {sbom_info['sha256'][:16]}...", file=sys.stderr)
    if sbom_info['signature_sha256']:
        print(f"  ✓ SBOM signature: {sbom_info['signature_sha256'][:16]}...", file=sys.stderr)
    
    # Set overall status
    bundle['overall_status'] = 'FROZEN'
    
    return bundle


def sign_bundle(
    bundle: Dict[str, Any],
    key_dir: Path,
    signing_key_id: str
) -> str:
    """
    Sign evidence bundle with ed25519.
    
    Returns:
        Base64-encoded signature
    
    Raises:
        SystemExit: If signing fails
    """
    if not _supply_chain_available:
        print("ERROR: Supply-chain signing module not available", file=sys.stderr)
        sys.exit(1)
    
    try:
        # PHASE-9: Use persistent signing authority (no ephemeral keys)
        from crypto.persistent_signing_authority import PersistentSigningAuthority
        import os
        
        # Get vault and registry paths from environment or key_dir
        vault_dir = Path(os.environ.get('RANSOMEYE_KEY_VAULT_DIR', key_dir / 'vault'))
        registry_path = Path(os.environ.get('RANSOMEYE_KEY_REGISTRY_PATH', key_dir.parent / 'registry.json'))
        
        # Load signing key from persistent vault
        authority = PersistentSigningAuthority(
            vault_dir=vault_dir,
            registry_path=registry_path
        )
        private_key, public_key = authority.get_signing_key(signing_key_id, require_active=True)
        
        # Create signer
        signer = ArtifactSigner(private_key=private_key, key_id=signing_key_id)
        
        # Sign bundle (without signature field)
        signature = signer.sign_manifest(bundle)
        
        return signature
        
    except (PersistentSigningAuthorityError, ImportError) as e:
        print(f"ERROR: Failed to load signing key: {e}", file=sys.stderr)
        print("PHASE-9: Persistent signing keys required. Ephemeral key generation is forbidden.", file=sys.stderr)
        sys.exit(1)
    except ArtifactSigningError as e:
        print(f"ERROR: Failed to sign bundle: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected signing error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point."""
    print("RansomEye v1.0 Phase 8.3 Evidence Bundle Freezing & Attestation", file=sys.stderr)
    print("=" * 70, file=sys.stderr)
    
    # Get configuration from environment
    release_root = Path(os.getenv('RANSOMEYE_RELEASE_ROOT', './build/artifacts'))
    key_dir = os.getenv('RANSOMEYE_SIGNING_KEY_DIR')
    signing_key_id = os.getenv('RANSOMEYE_SIGNING_KEY_ID', 'vendor-release-key-1')
    
    if not key_dir:
        print("ERROR: RANSOMEYE_SIGNING_KEY_DIR environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    key_dir_path = Path(key_dir)
    if not key_dir_path.exists():
        print(f"ERROR: Signing key directory not found: {key_dir_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Project root: {_project_root}", file=sys.stderr)
    print(f"Release root: {release_root}", file=sys.stderr)
    print(f"Key directory: {key_dir_path}", file=sys.stderr)
    print(f"Signing key ID: {signing_key_id}", file=sys.stderr)
    print("", file=sys.stderr)
    
    # Create evidence bundle
    try:
        bundle = create_evidence_bundle(_project_root, release_root)
    except SystemExit:
        raise
    except Exception as e:
        print(f"ERROR: Failed to create evidence bundle: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Sign bundle
    print("", file=sys.stderr)
    print("Signing evidence bundle...", file=sys.stderr)
    try:
        signature = sign_bundle(bundle, key_dir_path, signing_key_id)
        print(f"  ✓ Signature created", file=sys.stderr)
    except SystemExit:
        raise
    except Exception as e:
        print(f"ERROR: Failed to sign bundle: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Write bundle
    output_dir = _project_root / 'validation' / 'evidence_bundle'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    bundle_path = output_dir / 'evidence_bundle.json'
    signature_path = output_dir / 'evidence_bundle.json.sig'
    
    print("", file=sys.stderr)
    print("Writing evidence bundle...", file=sys.stderr)
    try:
        with open(bundle_path, 'w') as f:
            json.dump(bundle, f, indent=2)
        print(f"  ✓ Bundle written: {bundle_path}", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: Failed to write bundle: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Write signature
    try:
        with open(signature_path, 'w') as f:
            f.write(signature)
        print(f"  ✓ Signature written: {signature_path}", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: Failed to write signature: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Print summary
    print("", file=sys.stderr)
    print("Evidence Bundle Summary:", file=sys.stderr)
    print(f"  Bundle version: {bundle['bundle_version']}", file=sys.stderr)
    print(f"  Created at: {bundle['created_at']}", file=sys.stderr)
    print(f"  Host: {bundle['host']}", file=sys.stderr)
    print(f"  Git repo: {bundle['git']['repo']}", file=sys.stderr)
    print(f"  Git branch: {bundle['git']['branch']}", file=sys.stderr)
    print(f"  Git commit: {bundle['git']['commit']}", file=sys.stderr)
    print(f"  Artifacts: {len(bundle['artifacts'])}", file=sys.stderr)
    print(f"  Overall status: {bundle['overall_status']}", file=sys.stderr)
    print("", file=sys.stderr)
    print("✓ Evidence bundle frozen and attested", file=sys.stderr)
    
    sys.exit(0)


if __name__ == '__main__':
    main()
