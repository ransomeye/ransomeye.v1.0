#!/usr/bin/env python3
"""
RansomEye Manifest Generator

Purpose: Generate cryptographically-signed manifest for release artifacts
Status: SCAFFOLD - REQUIRES IMPLEMENTATION

See: docs/governance/signing-ceremony-and-key-custody-sop-v1.0.0.md
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any


def compute_file_hash(filepath: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def scan_artifacts(artifact_dir: Path) -> List[Dict[str, Any]]:
    """Scan artifact directory and collect file metadata."""
    artifacts = []
    
    for filepath in sorted(artifact_dir.rglob('*')):
        if not filepath.is_file():
            continue
        
        # Skip manifest itself and signature files
        if filepath.name in ('manifest.json', 'manifest.json.sig'):
            continue
        
        relative_path = filepath.relative_to(artifact_dir)
        file_hash = compute_file_hash(filepath)
        file_size = filepath.stat().st_size
        
        artifacts.append({
            'path': str(relative_path),
            'sha256': file_hash,
            'size': file_size,
            'type': filepath.suffix[1:] if filepath.suffix else 'unknown'
        })
    
    return artifacts


def generate_manifest(artifact_dir: Path, version: str = None) -> Dict[str, Any]:
    """Generate release manifest."""
    
    # Detect version from directory name if not provided
    if not version:
        version = artifact_dir.name.replace('ransomeye-', '').replace('-unsigned', '')
    
    artifacts = scan_artifacts(artifact_dir)
    
    manifest = {
        'version': '1.0',
        'release': {
            'version': version,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'platform': 'linux',
            'architecture': 'x86_64'
        },
        'artifacts': artifacts,
        'metadata': {
            'artifact_count': len(artifacts),
            'total_size': sum(a['size'] for a in artifacts),
            'generator': 'manifest_generator.py',
            'generator_version': '1.0.0'
        }
    }
    
    return manifest


def main():
    parser = argparse.ArgumentParser(
        description='Generate RansomEye release manifest',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input ransomeye-v1.0.0-unsigned --output manifest.json
  %(prog)s --input ./signed/ --output manifest.json --version v1.0.0

Environment Variables:
  None (all configuration via CLI)

Output:
  Deterministic JSON manifest with SHA256 hashes of all artifacts

See: docs/governance/signing-ceremony-and-key-custody-sop-v1.0.0.md
        """
    )
    
    parser.add_argument(
        '--input',
        required=True,
        help='Input directory containing release artifacts'
    )
    
    parser.add_argument(
        '--output',
        required=True,
        help='Output manifest file path'
    )
    
    parser.add_argument(
        '--version',
        help='Release version (auto-detected if not provided)'
    )
    
    parser.add_argument(
        '--pretty',
        action='store_true',
        help='Pretty-print JSON output'
    )
    
    args = parser.parse_args()
    
    # Validate input
    artifact_dir = Path(args.input)
    if not artifact_dir.exists():
        print(f"ERROR: Input directory does not exist: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    if not artifact_dir.is_dir():
        print(f"ERROR: Input path is not a directory: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    # Generate manifest
    print(f"Scanning artifacts in: {artifact_dir}")
    manifest = generate_manifest(artifact_dir, args.version)
    
    print(f"Found {manifest['metadata']['artifact_count']} artifacts")
    print(f"Total size: {manifest['metadata']['total_size']} bytes")
    
    # Write manifest
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        if args.pretty:
            json.dump(manifest, f, indent=2, sort_keys=True)
        else:
            json.dump(manifest, f, sort_keys=True)
    
    print(f"✓ Manifest written to: {output_path}")
    
    # Compute manifest hash for audit trail
    manifest_hash = compute_file_hash(output_path)
    print(f"✓ Manifest hash: {manifest_hash}")
    
    # TODO: Implement additional validations
    # - Check for required files (installer, services, etc.)
    # - Validate artifact naming conventions
    # - Check for forbidden files (.git, secrets, etc.)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
