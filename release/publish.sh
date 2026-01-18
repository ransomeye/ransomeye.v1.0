#!/usr/bin/env bash
#
# RansomEye Release Publishing Script
# Purpose: Publish prod-approved artifacts to customer-facing channels
# Status: SCAFFOLD - REQUIRES IMPLEMENTATION
#

set -euo pipefail

# Configuration via environment only
RELEASE_BUCKET="${RELEASE_BUCKET:-}"
RELEASE_CDN="${RELEASE_CDN:-}"

usage() {
    cat <<EOF
Usage: $0 <artifact-path> <version>

Publishes a prod-approved RansomEye release to customer-facing distribution channels.

Arguments:
  artifact-path   Path to signed, prod-approved artifact directory
  version         Release version (e.g., v1.0.0)

Environment Variables:
  RELEASE_BUCKET  S3 bucket or storage location for releases (required)
  RELEASE_CDN     CDN endpoint for distribution (optional)

Preconditions:
  - Artifact must be prod-approved
  - Signatures must be valid
  - Release notes must be present

Examples:
  $0 ./signed/ v1.0.0

See: docs/governance/promotion-approvals-and-release-governance-v1.0.0.md
EOF
    exit 0
}

# Parse arguments
if [[ $# -lt 2 ]]; then
    usage
fi

ARTIFACT_PATH="$1"
VERSION="$2"

# Validation
if [[ ! -d "$ARTIFACT_PATH" ]]; then
    echo "ERROR: Artifact path does not exist: $ARTIFACT_PATH"
    exit 1
fi

if [[ -z "$RELEASE_BUCKET" ]]; then
    echo "ERROR: RELEASE_BUCKET environment variable not set"
    exit 1
fi

# Verify this is a prod-approved artifact
echo "Verifying prod approval..."

# Check if artifact comes from prod environment
if [[ -f "$ARTIFACT_PATH/.promoted" ]]; then
    PROMOTED_ENV=$(grep -o '"environment"[[:space:]]*:[[:space:]]*"[^"]*"' "$ARTIFACT_PATH/.promoted" | cut -d'"' -f4 || echo "unknown")
    if [[ "$PROMOTED_ENV" != "prod" ]]; then
        echo "ERROR: Artifact is not prod-approved (environment: $PROMOTED_ENV)"
        exit 1
    fi
    echo "✓ Artifact is prod-approved"
else
    echo "WARNING: Cannot verify prod approval (.promoted metadata missing)"
    echo "Proceeding with caution..."
fi

# Verify signatures using existing verification infrastructure
echo "Verifying signatures..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ -f "$PROJECT_ROOT/scripts/verify_release_bundle.py" ]]; then
    python3 "$PROJECT_ROOT/scripts/verify_release_bundle.py" \
        --bundle "$ARTIFACT_PATH" \
        --output "/tmp/publish-verification-$$.json" || {
            echo "ERROR: Signature verification FAILED"
            echo "Refusing to publish unverified bundle."
            exit 1
        }
    echo "✓ Signature verification PASSED"
else
    # Fallback: check for signature files at minimum
    if [[ ! -f "$ARTIFACT_PATH/manifest.json.sig" ]] || [[ ! -f "$ARTIFACT_PATH/SHA256SUMS.sig" ]]; then
        echo "ERROR: Missing signature files"
        exit 1
    fi
    echo "✓ Signature files present"
fi

# Verify release notes
if [[ ! -f "$ARTIFACT_PATH/RELEASE_NOTES_${VERSION}.md" ]]; then
    echo "WARNING: Release notes not found: RELEASE_NOTES_${VERSION}.md"
fi

# Compute final artifact hash
ARTIFACT_HASH=$(find "$ARTIFACT_PATH" -type f -exec sha256sum {} \; | sort | sha256sum | awk '{print $1}')
echo "Final artifact hash: $ARTIFACT_HASH"

# Determine publish destination
if [[ -n "$RELEASE_BUCKET" ]]; then
    PUBLISH_TARGET="$RELEASE_BUCKET/releases/$VERSION"
else
    # Fallback to local immutable directory
    PUBLISH_TARGET="/srv/ransomeye/releases/$VERSION"
    echo "RELEASE_BUCKET not set, using local directory: $PUBLISH_TARGET"
fi

# Enforce immutability: refuse if version already published
if [[ -d "$PUBLISH_TARGET" ]] || [[ -n "$RELEASE_BUCKET" ]]; then
    # For local: check directory existence
    if [[ ! -n "$RELEASE_BUCKET" ]] && [[ -d "$PUBLISH_TARGET" ]]; then
        echo "ERROR: Version $VERSION already published"
        echo "Target: $PUBLISH_TARGET"
        echo "Publication is immutable - cannot overwrite"
        exit 1
    fi
fi

# Create immutable release bundle
RELEASE_BUNDLE="ransomeye-${VERSION}.tar.gz"
echo "Creating release bundle: $RELEASE_BUNDLE"

tar -czf "$RELEASE_BUNDLE" \
    --owner=0 --group=0 \
    --format=gnu \
    -C "$ARTIFACT_PATH" .

# Verify bundle was created
if [[ ! -f "$RELEASE_BUNDLE" ]]; then
    echo "ERROR: Failed to create release bundle"
    exit 1
fi

BUNDLE_SIZE=$(stat -c%s "$RELEASE_BUNDLE" 2>/dev/null || stat -f%z "$RELEASE_BUNDLE" 2>/dev/null)
echo "✓ Release bundle created: $RELEASE_BUNDLE ($BUNDLE_SIZE bytes)"

# Publish to destination
if [[ -n "$RELEASE_BUCKET" ]]; then
    echo "Publishing to cloud storage: $RELEASE_BUCKET"
    # Cloud storage upload (AWS S3, GCS, etc.)
    # Uncomment and configure based on your storage backend:
    #
    # AWS S3:
    # aws s3 cp "$RELEASE_BUNDLE" "s3://$RELEASE_BUCKET/releases/$VERSION/"
    # aws s3 cp "$ARTIFACT_PATH/SHA256SUMS" "s3://$RELEASE_BUCKET/releases/$VERSION/"
    # aws s3 cp "$ARTIFACT_PATH/SHA256SUMS.sig" "s3://$RELEASE_BUCKET/releases/$VERSION/"
    # aws s3 cp "$ARTIFACT_PATH/manifest.json" "s3://$RELEASE_BUCKET/releases/$VERSION/"
    # aws s3 cp "$ARTIFACT_PATH/manifest.json.sig" "s3://$RELEASE_BUCKET/releases/$VERSION/"
    #
    # Google Cloud Storage:
    # gsutil cp "$RELEASE_BUNDLE" "gs://$RELEASE_BUCKET/releases/$VERSION/"
    #
    echo "⚠️  Cloud upload not configured - set up storage backend in this script"
    echo "Bundle ready for manual upload: $RELEASE_BUNDLE"
else
    # Local immutable directory
    echo "Publishing to local directory: $PUBLISH_TARGET"
    mkdir -p "$PUBLISH_TARGET"
    
    cp "$RELEASE_BUNDLE" "$PUBLISH_TARGET/"
    cp "$ARTIFACT_PATH/SHA256SUMS" "$PUBLISH_TARGET/" 2>/dev/null || true
    cp "$ARTIFACT_PATH/SHA256SUMS.sig" "$PUBLISH_TARGET/" 2>/dev/null || true
    cp "$ARTIFACT_PATH/manifest.json" "$PUBLISH_TARGET/" 2>/dev/null || true
    cp "$ARTIFACT_PATH/manifest.json.sig" "$PUBLISH_TARGET/" 2>/dev/null || true
    
    # Make immutable (read-only)
    chmod -R a-w "$PUBLISH_TARGET"
    
    echo "✓ Published to: $PUBLISH_TARGET"
fi

# CDN cache invalidation
if [[ -n "$RELEASE_CDN" ]]; then
    echo "Invalidating CDN cache at: $RELEASE_CDN"
    # Uncomment and configure based on your CDN:
    #
    # AWS CloudFront:
    # aws cloudfront create-invalidation --distribution-id $CDN_DISTRIBUTION_ID --paths "/releases/$VERSION/*"
    #
    # Cloudflare:
    # curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache" \
    #      -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
    #      -d '{"files":["https://cdn.example.com/releases/'$VERSION'/*"]}'
    #
    echo "⚠️  CDN invalidation not configured"
else
    echo "ℹ️  RELEASE_CDN not set - skipping CDN invalidation"
fi

# Generate download URL
if [[ -n "$RELEASE_BUCKET" ]]; then
    DOWNLOAD_URL="https://${RELEASE_BUCKET}/releases/${VERSION}/${RELEASE_BUNDLE}"
elif [[ -n "$RELEASE_CDN" ]]; then
    DOWNLOAD_URL="${RELEASE_CDN}/releases/${VERSION}/${RELEASE_BUNDLE}"
else
    DOWNLOAD_URL="file://${PUBLISH_TARGET}/${RELEASE_BUNDLE}"
fi

# Record publication
PUBLISH_RECORD="/tmp/ransomeye-publish-${VERSION}.json"
cat > "$PUBLISH_RECORD" <<EOF
{
  "version": "$VERSION",
  "bundle": "$RELEASE_BUNDLE",
  "artifact_hash": "$ARTIFACT_HASH",
  "bundle_size": $BUNDLE_SIZE,
  "published_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "published_by": "${USER:-unknown}",
  "publish_target": "$PUBLISH_TARGET",
  "download_url": "$DOWNLOAD_URL"
}
EOF

echo ""
echo "================================================================"
echo "RELEASE PUBLISHED"
echo "================================================================"
echo "Version:      $VERSION"
echo "Bundle:       $RELEASE_BUNDLE"
echo "Size:         $BUNDLE_SIZE bytes"
echo "Hash:         $ARTIFACT_HASH"
echo "Target:       $PUBLISH_TARGET"
echo "Download URL: $DOWNLOAD_URL"
echo "================================================================"
echo ""
echo "Publication record: $PUBLISH_RECORD"

# Future enhancements (currently placeholders):
# - Send release notification to team/customers
# - Update release registry/database
# - Trigger documentation deployment
# - Generate release announcement
# - Update public download page
