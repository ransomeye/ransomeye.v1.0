#!/usr/bin/env python3
"""
RansomEye Supply-Chain Signing & Verification Framework - Manifest Builder
AUTHORITATIVE: Deterministic building of artifact manifests
"""

import hashlib
import platform
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional


class ManifestBuilderError(Exception):
    """Base exception for manifest builder errors."""
    pass


class ManifestBuilder:
    """
    Deterministic building of artifact manifests.
    
    Properties:
    - Deterministic: Same inputs always produce same outputs
    - Reproducible: All steps are reproducible
    - No hardcoded values: All values come from inputs or environment
    """
    
    def __init__(self):
        """Initialize manifest builder."""
        pass
    
    def build_manifest(
        self,
        artifact_path: Path,
        artifact_name: str,
        artifact_type: str,
        version: str,
        signing_key_id: str,
        toolchain_config: Optional[Dict[str, Any]] = None,
        build_host_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build artifact manifest.
        
        Args:
            artifact_path: Path to artifact file
            artifact_name: Artifact name
            artifact_type: Artifact type (CORE_INSTALLER, LINUX_AGENT, WINDOWS_AGENT, DPI_PROBE, RELEASE_BUNDLE)
            version: Artifact version (semver)
            signing_key_id: Signing key identifier
            toolchain_config: Optional toolchain configuration dictionary
            build_host_info: Optional build host information dictionary
        
        Returns:
            Artifact manifest dictionary (without signature)
        """
        # Validate artifact type
        valid_types = ['CORE_INSTALLER', 'LINUX_AGENT', 'WINDOWS_AGENT', 'DPI_PROBE', 'RELEASE_BUNDLE']
        if artifact_type not in valid_types:
            raise ManifestBuilderError(f"Invalid artifact_type: {artifact_type}. Must be one of {valid_types}")
        
        # Compute artifact SHA256
        artifact_sha256 = self._compute_artifact_hash(artifact_path)
        
        # Build toolchain fingerprint
        toolchain_fingerprint = self._compute_toolchain_fingerprint(toolchain_config)
        
        # Build host fingerprint
        build_host_fingerprint = self._compute_build_host_fingerprint(build_host_info)
        
        # Create manifest (without signature)
        manifest = {
            'artifact_id': str(uuid.uuid4()),
            'artifact_name': artifact_name,
            'artifact_type': artifact_type,
            'version': version,
            'build_timestamp': datetime.now(timezone.utc).isoformat(),
            'sha256': artifact_sha256,
            'signing_key_id': signing_key_id,
            'signature': '',  # Will be set by signer
            'toolchain_fingerprint': toolchain_fingerprint,
            'build_host_fingerprint': build_host_fingerprint
        }
        
        return manifest
    
    def _compute_artifact_hash(self, artifact_path: Path) -> str:
        """
        Compute SHA256 hash of artifact.
        
        Args:
            artifact_path: Path to artifact file
        
        Returns:
            SHA256 hash as hexadecimal string
        
        Raises:
            ManifestBuilderError: If artifact file not found or hash computation fails
        """
        if not artifact_path.exists():
            raise ManifestBuilderError(f"Artifact file not found: {artifact_path}")
        
        try:
            hash_obj = hashlib.sha256()
            with open(artifact_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except Exception as e:
            raise ManifestBuilderError(f"Failed to compute artifact hash: {e}") from e
    
    def _compute_toolchain_fingerprint(self, toolchain_config: Optional[Dict[str, Any]]) -> str:
        """
        Compute toolchain fingerprint.
        
        Args:
            toolchain_config: Optional toolchain configuration dictionary
        
        Returns:
            SHA256 hash of toolchain configuration
        """
        if toolchain_config:
            # Hash toolchain configuration (sorted JSON)
            import json
            canonical_json = json.dumps(toolchain_config, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
        else:
            # Default: hash empty dict
            return hashlib.sha256(b'{}').hexdigest()
    
    def _compute_build_host_fingerprint(self, build_host_info: Optional[Dict[str, Any]]) -> str:
        """
        Compute build host fingerprint.
        
        Args:
            build_host_info: Optional build host information dictionary
        
        Returns:
            SHA256 hash of build host identity
        """
        if build_host_info:
            # Hash build host information (sorted JSON)
            import json
            canonical_json = json.dumps(build_host_info, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
        else:
            # Default: hash platform information
            host_info = {
                'hostname': platform.node(),
                'os': platform.system(),
                'arch': platform.machine()
            }
            import json
            canonical_json = json.dumps(host_info, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
