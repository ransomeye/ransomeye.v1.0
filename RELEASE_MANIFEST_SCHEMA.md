# RELEASE_MANIFEST.json Schema

**Document Classification:** Release Bundle Specification  
**Version:** 1.0  
**Date:** 2024-01-15  
**Status:** Authoritative

---

## Overview

`RELEASE_MANIFEST.json` is the authoritative manifest for RansomEye release bundles. It provides a complete, verifiable inventory of all components in a release bundle, enabling offline verification and long-term auditability.

---

## Schema Definition

```json
{
  "version": "1.0",
  "release_version": "v1.0.0",
  "created_at": "2024-01-15T12:00:00Z",
  "bundle_type": "ransomeye-release-bundle",
  "artifacts": [
    {
      "name": "core-installer.tar.gz",
      "path": "artifacts/core-installer.tar.gz",
      "sha256": "abc123...",
      "size": 12345678
    }
  ],
  "signatures": [
    {
      "artifact_name": "core-installer.tar.gz",
      "manifest_path": "signatures/core-installer.tar.gz.manifest.json",
      "signature_path": "signatures/core-installer.tar.gz.manifest.sig",
      "manifest_sha256": "def456...",
      "signature_sha256": "ghi789..."
    }
  ],
  "sbom": {
    "manifest_path": "sbom/manifest.json",
    "signature_path": "sbom/manifest.json.sig",
    "manifest_sha256": "jkl012...",
    "signature_sha256": "mno345..."
  },
  "public_keys": [
    {
      "key_id": "vendor-signing-key-1",
      "key_path": "keys/vendor-signing-key-1.pub",
      "key_sha256": "pqr678..."
    }
  ],
  "evidence": {
    "bundle_path": "evidence/evidence_bundle.json",
    "signature_path": "evidence/evidence_bundle.json.sig",
    "bundle_sha256": "stu901...",
    "signature_sha256": "vwx234...",
    "ga_verdict": "PASS"
  },
  "metadata": {
    "build_info_path": "metadata/build-info.json",
    "build_environment_path": "metadata/build-environment.json",
    "build_info": { ... },
    "build_environment": { ... }
  },
  "verification_instructions": {
    "offline_verification": "All verification can be performed offline using bundled public keys",
    "long_term_verification": "Bundle can be verified years later using bundled keys and evidence",
    "no_ci_dependency": "Verification does not require CI access or artifact retention"
  }
}
```

---

## Field Descriptions

### Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | Yes | Schema version (currently "1.0") |
| `release_version` | string | Yes | Release version (e.g., "v1.0.0") |
| `created_at` | string (ISO 8601) | Yes | Bundle creation timestamp (UTC) |
| `bundle_type` | string | Yes | Bundle type identifier ("ransomeye-release-bundle") |
| `artifacts` | array | Yes | List of build artifacts |
| `signatures` | array | Yes | List of artifact signatures |
| `sbom` | object | Yes | SBOM information |
| `public_keys` | array | Yes | List of public signing keys |
| `evidence` | object | Yes | Phase-8 evidence bundle information |
| `metadata` | object | Yes | Build and environment metadata |
| `verification_instructions` | object | Yes | Verification guidance |

### Artifacts Array

Each artifact entry:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Artifact filename |
| `path` | string | Yes | Relative path within bundle |
| `sha256` | string | Yes | SHA256 hash of artifact |
| `size` | integer | Yes | Artifact size in bytes |

### Signatures Array

Each signature entry:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `artifact_name` | string | Yes | Name of signed artifact |
| `manifest_path` | string | Yes | Relative path to manifest file |
| `signature_path` | string | Yes | Relative path to signature file |
| `manifest_sha256` | string | Yes | SHA256 hash of manifest file |
| `signature_sha256` | string | Yes | SHA256 hash of signature file |

### SBOM Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `manifest_path` | string | Yes | Relative path to SBOM manifest |
| `signature_path` | string | Yes | Relative path to SBOM signature |
| `manifest_sha256` | string | Yes | SHA256 hash of SBOM manifest |
| `signature_sha256` | string | Yes | SHA256 hash of SBOM signature |

### Public Keys Array

Each public key entry:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `key_id` | string | Yes | Key identifier |
| `key_path` | string | Yes | Relative path to public key file |
| `key_sha256` | string | Yes | SHA256 hash of public key file |

### Evidence Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `bundle_path` | string | Yes | Relative path to evidence bundle |
| `signature_path` | string | Yes | Relative path to evidence signature |
| `bundle_sha256` | string | Yes | SHA256 hash of evidence bundle |
| `signature_sha256` | string | Yes | SHA256 hash of evidence signature |
| `ga_verdict` | string | Yes | GA verdict from evidence bundle ("PASS", "FAIL", "PARTIAL") |

### Metadata Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `build_info_path` | string | No | Relative path to build-info.json |
| `build_environment_path` | string | No | Relative path to build-environment.json |
| `build_info` | object | No | Build info content (if embedded) |
| `build_environment` | object | No | Build environment content (if embedded) |

---

## Validation Rules

1. **All artifacts must have signatures:** Every artifact in `artifacts` array must have a corresponding entry in `signatures` array
2. **All hashes must match:** All SHA256 hashes in manifest must match actual file hashes
3. **GA verdict must be PASS:** `evidence.ga_verdict` must be "PASS" for release approval
4. **Public keys required:** At least one public key must be present in `public_keys` array
5. **SBOM required:** SBOM manifest and signature must be present

---

## Usage

### Creation

`RELEASE_MANIFEST.json` is created by `scripts/create_release_bundle.py` during release bundle creation.

### Verification

`RELEASE_MANIFEST.json` is verified by `scripts/verify_release_bundle.py` during release gate execution.

### Long-Term Verification

The manifest enables long-term verification by:
- Providing complete inventory of bundle contents
- Enabling hash verification of all components
- Documenting verification procedures
- Enabling offline verification without CI access

---

**End of Schema Definition**
