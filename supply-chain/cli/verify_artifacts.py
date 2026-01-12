#!/usr/bin/env python3
"""
RansomEye Supply-Chain Signing & Verification Framework - Verify Artifacts CLI
AUTHORITATIVE: Command-line tool for verifying artifacts
"""

import sys
from pathlib import Path
import argparse

# Add parent directory to path for imports
_supply_chain_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_supply_chain_dir))

# Add branding module to path
_branding_dir = Path(__file__).parent.parent.parent / "branding"
sys.path.insert(0, str(_branding_dir))

from crypto.vendor_key_manager import VendorKeyManager, VendorKeyManagerError
from crypto.artifact_verifier import ArtifactVerifier, ArtifactVerificationError
from engine.verification_engine import VerificationEngine, VerificationEngineError
from branding.branding_utils import BrandingUtils


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Verify artifact supply-chain integrity'
    )
    parser.add_argument(
        '--artifact',
        type=Path,
        required=True,
        help='Path to artifact file'
    )
    parser.add_argument(
        '--manifest',
        type=Path,
        required=True,
        help='Path to manifest file'
    )
    parser.add_argument(
        '--public-key',
        type=Path,
        help='Path to public key file (optional, for external trust root)'
    )
    parser.add_argument(
        '--key-dir',
        type=Path,
        help='Directory containing vendor signing keys (optional, if public-key not provided)'
    )
    parser.add_argument(
        '--signing-key-id',
        help='Signing key identifier (optional, if public-key not provided)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize verifier
        if args.public_key:
            # Use external public key (customer trust root)
            verifier = ArtifactVerifier(public_key_path=args.public_key)
        elif args.key_dir and args.signing_key_id:
            # Use vendor key
            key_manager = VendorKeyManager(args.key_dir)
            public_key = key_manager.get_public_key(args.signing_key_id)
            if not public_key:
                print(f"Public key not found: {args.signing_key_id}", file=sys.stderr)
                sys.exit(1)
            verifier = ArtifactVerifier(public_key=public_key)
        else:
            print("Either --public-key or both --key-dir and --signing-key-id must be provided", file=sys.stderr)
            sys.exit(1)
        
        # Initialize verification engine
        verification_engine = VerificationEngine(verifier)
        
        # Verify artifact
        result = verification_engine.verify_artifact(args.artifact, args.manifest)
        
        # Output result with branding
        print(f"\n{BrandingUtils.get_product_name()} — Supply Chain Verification")
        print("=" * 60)
        
        if result.passed:
            print("PASS: Artifact verification successful")
            print(f"  Reason: {result.reason}")
            if result.details:
                print(f"  Details:")
                print(f"    Artifact ID: {result.details.get('artifact_id', 'N/A')}")
                print(f"    Artifact Name: {result.details.get('artifact_name', 'N/A')}")
                print(f"    Version: {result.details.get('version', 'N/A')}")
                print(f"    Signing Key ID: {result.details.get('signing_key_id', 'N/A')}")
            print(f"\n{BrandingUtils.get_evidence_notice()}")
            sys.exit(0)
        else:
            print("FAIL: Artifact verification failed", file=sys.stderr)
            print(f"  Reason: {result.reason}", file=sys.stderr)
            if result.details:
                print(f"  Details:", file=sys.stderr)
                for key, value in result.details.items():
                    print(f"    {key}: {value}", file=sys.stderr)
            sys.exit(1)
        
    except (VendorKeyManagerError, ArtifactVerificationError, VerificationEngineError) as e:
        print(f"Artifact verification failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
