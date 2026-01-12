#!/usr/bin/env python3
"""
RansomEye Supply-Chain Signing & Verification Framework - Verification Engine
AUTHORITATIVE: Comprehensive artifact verification
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from crypto.artifact_verifier import ArtifactVerifier, ArtifactVerificationError


class VerificationEngineError(Exception):
    """Base exception for verification engine errors."""
    pass


class VerificationResult:
    """Verification result container."""
    
    def __init__(self, passed: bool, reason: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize verification result.
        
        Args:
            passed: True if verification passed, False otherwise
            reason: Human-readable reason for pass/fail
            details: Optional details dictionary
        """
        self.passed = passed
        self.reason = reason
        self.details = details or {}
    
    def __bool__(self) -> bool:
        """Return True if verification passed."""
        return self.passed
    
    def __str__(self) -> str:
        """Return string representation."""
        status = "PASS" if self.passed else "FAIL"
        return f"{status}: {self.reason}"


class VerificationEngine:
    """
    Comprehensive artifact verification.
    
    Properties:
    - Explicit failures: No silent failures
    - External key support: Supports customer trust root injection
    - Offline: No network or external dependencies
    """
    
    def __init__(self, verifier: ArtifactVerifier):
        """
        Initialize verification engine.
        
        Args:
            verifier: Artifact verifier instance
        """
        self.verifier = verifier
    
    def verify_artifact(
        self,
        artifact_path: Path,
        manifest_path: Path
    ) -> VerificationResult:
        """
        Verify artifact and manifest.
        
        Process:
        1. Load manifest
        2. Verify SHA256 hash
        3. Verify manifest hash
        4. Verify signature
        
        Args:
            artifact_path: Path to artifact file
            manifest_path: Path to manifest file
        
        Returns:
            VerificationResult
        """
        try:
            # Load manifest
            if not manifest_path.exists():
                return VerificationResult(
                    passed=False,
                    reason=f"Manifest file not found: {manifest_path}",
                    details={'manifest_path': str(manifest_path)}
                )
            
            manifest = json.loads(manifest_path.read_text())
            
            # Verify artifact SHA256
            expected_sha256 = manifest.get('sha256', '')
            if not expected_sha256:
                return VerificationResult(
                    passed=False,
                    reason="Manifest missing SHA256 hash",
                    details={'manifest': manifest}
                )
            
            if not self.verifier.verify_artifact_hash(artifact_path, expected_sha256):
                return VerificationResult(
                    passed=False,
                    reason=f"Artifact SHA256 hash mismatch: expected {expected_sha256}",
                    details={
                        'artifact_path': str(artifact_path),
                        'expected_sha256': expected_sha256
                    }
                )
            
            # Verify manifest signature
            if not self.verifier.verify_manifest_signature(manifest):
                return VerificationResult(
                    passed=False,
                    reason="Manifest signature verification failed",
                    details={
                        'artifact_path': str(artifact_path),
                        'manifest_path': str(manifest_path),
                        'signing_key_id': manifest.get('signing_key_id', '')
                    }
                )
            
            # All checks passed
            return VerificationResult(
                passed=True,
                reason="All verification checks passed",
                details={
                    'artifact_path': str(artifact_path),
                    'manifest_path': str(manifest_path),
                    'artifact_id': manifest.get('artifact_id', ''),
                    'artifact_name': manifest.get('artifact_name', ''),
                    'version': manifest.get('version', ''),
                    'signing_key_id': manifest.get('signing_key_id', '')
                }
            )
            
        except json.JSONDecodeError as e:
            return VerificationResult(
                passed=False,
                reason=f"Manifest JSON decode error: {e}",
                details={'manifest_path': str(manifest_path)}
            )
        except Exception as e:
            return VerificationResult(
                passed=False,
                reason=f"Verification error: {e}",
                details={
                    'artifact_path': str(artifact_path),
                    'manifest_path': str(manifest_path)
                }
            )
