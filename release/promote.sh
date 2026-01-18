#!/usr/bin/env bash
#
# RansomEye Release Promotion Script
# Purpose: Promote signed artifacts across environments (dev → staging → prod)
# Status: SCAFFOLD - REQUIRES IMPLEMENTATION
#

set -euo pipefail

# Configuration via environment only
ARTIFACT_STORE="${ARTIFACT_STORE:-}"
AUDIT_LOG="${AUDIT_LOG:-/var/log/ransomeye/promotion-audit.log}"

usage() {
    cat <<EOF
Usage: $0 --env <environment> --artifact <path> --version <version>

Promotes a signed RansomEye release artifact to the specified environment.

Options:
  --env         Target environment (dev|staging|prod)
  --artifact    Path to signed artifact directory
  --version     Release version (e.g., v1.0.0)
  --help        Show this help

Environment Variables:
  ARTIFACT_STORE  Path to artifact storage (required)
  AUDIT_LOG       Path to audit log (default: /var/log/ransomeye/promotion-audit.log)

Examples:
  $0 --env dev --artifact ./signed/ --version v1.0.0
  $0 --env staging --artifact ./signed/ --version v1.0.0

Governance:
  - DEV: Automatic (no approval)
  - STAGING: Requires Release Engineer approval
  - PROD: Requires Release Engineer + Security Officer approval

See: docs/governance/promotion-approvals-and-release-governance-v1.0.0.md
EOF
    exit 0
}

# Parse arguments
ENVIRONMENT=""
ARTIFACT_PATH=""
VERSION=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --artifact)
            ARTIFACT_PATH="$2"
            shift 2
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        --help)
            usage
            ;;
        *)
            echo "ERROR: Unknown option: $1"
            usage
            ;;
    esac
done

# Validation
if [[ -z "$ENVIRONMENT" ]] || [[ -z "$ARTIFACT_PATH" ]] || [[ -z "$VERSION" ]]; then
    echo "ERROR: Missing required arguments"
    usage
fi

if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    echo "ERROR: Invalid environment: $ENVIRONMENT (must be dev|staging|prod)"
    exit 1
fi

if [[ ! -d "$ARTIFACT_PATH" ]]; then
    echo "ERROR: Artifact path does not exist: $ARTIFACT_PATH"
    exit 1
fi

if [[ -z "$ARTIFACT_STORE" ]]; then
    echo "ERROR: ARTIFACT_STORE environment variable not set"
    exit 1
fi

# Verify signatures exist
echo "Verifying signed artifacts..."
if [[ ! -f "$ARTIFACT_PATH/manifest.json" ]]; then
    echo "ERROR: manifest.json not found in artifact path"
    exit 1
fi

# Verify signatures using existing verification infrastructure
echo "Running signature verification..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ -f "$PROJECT_ROOT/scripts/verify_release_bundle.py" ]]; then
    python3 "$PROJECT_ROOT/scripts/verify_release_bundle.py" \
        --bundle "$ARTIFACT_PATH" \
        --output "/tmp/promote-verification-$$.json" || {
            echo "ERROR: Signature verification FAILED"
            echo "Bundle verification failed. Refusing to promote."
            exit 1
        }
    echo "✓ Signature verification PASSED"
else
    # Fallback: check for signature files at minimum
    if [[ ! -f "$ARTIFACT_PATH/manifest.json.sig" ]] || [[ ! -f "$ARTIFACT_PATH/SHA256SUMS.sig" ]]; then
        echo "ERROR: Missing signature files (.sig) in artifact path"
        echo "Expected: manifest.json.sig, SHA256SUMS.sig"
        exit 1
    fi
    echo "✓ Signature files present (full verification script not available)"
fi

# Compute artifact hash
ARTIFACT_HASH=$(find "$ARTIFACT_PATH" -type f -exec sha256sum {} \; | sort | sha256sum | awk '{print $1}')
echo "Artifact hash: $ARTIFACT_HASH"

# Environment-specific logic and approval enforcement
case $ENVIRONMENT in
    dev)
        echo "Promoting to DEV (automatic)..."
        # No approval required for DEV
        ;;
    staging)
        echo "Promoting to STAGING (requires Release Engineer approval)..."
        # Check for approval (in CI, this is enforced by GitHub environment protection)
        if [[ -n "${CI:-}" ]]; then
            echo "✓ Running in CI - approval enforced by environment protection"
        else
            # Manual promotion requires explicit approval variable
            if [[ -z "${RELEASE_APPROVED_BY:-}" ]]; then
                echo "ERROR: STAGING promotion requires RELEASE_APPROVED_BY environment variable"
                echo "Set: export RELEASE_APPROVED_BY='your-name'"
                exit 1
            fi
            echo "✓ Approved by: $RELEASE_APPROVED_BY"
        fi
        ;;
    prod)
        echo "Promoting to PROD (requires dual approval)..."
        # Check for dual approval
        if [[ -n "${CI:-}" ]]; then
            echo "✓ Running in CI - dual approval enforced by environment protection"
        else
            # Manual promotion requires both approvers
            if [[ -z "${RELEASE_APPROVED_BY:-}" ]] || [[ -z "${SECURITY_APPROVED_BY:-}" ]]; then
                echo "ERROR: PROD promotion requires both RELEASE_APPROVED_BY and SECURITY_APPROVED_BY"
                echo "Set: export RELEASE_APPROVED_BY='release-engineer-name'"
                echo "     export SECURITY_APPROVED_BY='security-officer-name'"
                exit 1
            fi
            echo "✓ Approved by Release Engineer: $RELEASE_APPROVED_BY"
            echo "✓ Approved by Security Officer: $SECURITY_APPROVED_BY"
        fi
        ;;
esac

# Copy artifacts to environment-specific location (immutable)
TARGET_DIR="$ARTIFACT_STORE/$ENVIRONMENT/$VERSION"

# Enforce immutability: refuse if version already exists
if [[ -d "$TARGET_DIR" ]]; then
    echo "ERROR: Version $VERSION already exists in $ENVIRONMENT"
    echo "Target: $TARGET_DIR"
    echo "Promotion is immutable - cannot overwrite existing version"
    exit 1
fi

# Create target and copy artifacts
echo "Copying artifacts to: $TARGET_DIR"
mkdir -p "$TARGET_DIR"
cp -r "$ARTIFACT_PATH"/* "$TARGET_DIR/" || {
    echo "ERROR: Failed to copy artifacts"
    rm -rf "$TARGET_DIR"
    exit 1
}

echo "✓ Artifacts promoted to $ENVIRONMENT"

# Audit log with complete metadata
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
APPROVER="${RELEASE_APPROVED_BY:-${USER:-unknown}}"
SECURITY_APPROVER="${SECURITY_APPROVED_BY:-}"

mkdir -p "$(dirname "$AUDIT_LOG")"

# Write audit entry as JSON
cat >> "$AUDIT_LOG" <<EOF
{
  "timestamp": "$TIMESTAMP",
  "environment": "$ENVIRONMENT",
  "version": "$VERSION",
  "artifact_hash": "$ARTIFACT_HASH",
  "approver": "$APPROVER",
  "security_approver": "$SECURITY_APPROVER",
  "ci_run_id": "${GITHUB_RUN_ID:-local}",
  "target_path": "$TARGET_DIR"
}
EOF

echo ""
echo "================================================================"
echo "PROMOTION COMPLETE"
echo "================================================================"
echo "Environment:  $ENVIRONMENT"
echo "Version:      $VERSION"
echo "Artifact:     $ARTIFACT_HASH"
echo "Target:       $TARGET_DIR"
echo "Approver:     $APPROVER"
if [[ -n "$SECURITY_APPROVER" ]]; then
    echo "Security:     $SECURITY_APPROVER"
fi
echo "================================================================"
echo ""
echo "✓ Audit log: $AUDIT_LOG"
