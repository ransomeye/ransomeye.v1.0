#!/bin/bash
# Phase-6 Evidence Collection Script
# 
# This script helps collect evidence from GitHub Actions CI runs.
# It provides instructions and validates collected files.
#
# Usage: ./collect_evidence.sh [workflow_run_id]

set -euo pipefail

EVIDENCE_DIR="$(dirname "$0")"
SCRIPT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

echo "=========================================="
echo "PHASE 6: Evidence Collection Helper"
echo "=========================================="
echo ""

if [ $# -eq 0 ]; then
    echo "Usage: $0 <workflow_run_id>"
    echo ""
    echo "To find workflow_run_id:"
    echo "1. Go to GitHub Actions → CI Build and Sign - PHASE 6"
    echo "2. Click on a successful run"
    echo "3. The run ID is in the URL: .../actions/runs/<run_id>"
    echo ""
    echo "Or use 'gh' CLI:"
    echo "  gh run list --workflow='CI Build and Sign - PHASE 6'"
    echo ""
    exit 1
fi

RUN_ID="$1"
REPO="${GITHUB_REPOSITORY:-$(git remote get-url origin | sed 's/.*github.com[:/]\([^.]*\).*/\1/')}"

echo "Workflow Run ID: $RUN_ID"
echo "Repository: $REPO"
echo "Evidence Directory: $EVIDENCE_DIR"
echo ""

# Check if gh CLI is available
if ! command -v gh &> /dev/null; then
    echo "⚠ WARNING: GitHub CLI (gh) not found"
    echo "You will need to manually download artifacts from GitHub Actions UI"
    echo ""
    echo "Manual steps:"
    echo "1. Go to: https://github.com/$REPO/actions/runs/$RUN_ID"
    echo "2. Download artifacts:"
    echo "   - phase-c-linux-results"
    echo "   - phase-c-windows-results"
    echo "   - ga-verdict"
    echo "   - signed-artifacts"
    echo "   - signing-public-key"
    echo "3. Extract to: $EVIDENCE_DIR"
    echo ""
    exit 0
fi

echo "Using GitHub CLI to download artifacts..."
echo ""

# Create temporary directory for downloads
TMP_DIR=$(mktemp -d)
trap "rm -rf $TMP_DIR" EXIT

# Download artifacts
echo "Downloading artifacts..."
gh run download "$RUN_ID" --dir "$TMP_DIR" || {
    echo "❌ ERROR: Failed to download artifacts"
    echo "Make sure you're authenticated: gh auth login"
    exit 1
}

# Extract and organize files
echo ""
echo "Organizing evidence files..."

# Extract validation results
if [ -d "$TMP_DIR/phase-c-linux-results" ]; then
    cp "$TMP_DIR/phase-c-linux-results"/*.json "$EVIDENCE_DIR/" 2>/dev/null || true
fi

if [ -d "$TMP_DIR/phase-c-windows-results" ]; then
    cp "$TMP_DIR/phase-c-windows-results"/*.json "$EVIDENCE_DIR/" 2>/dev/null || true
fi

if [ -d "$TMP_DIR/ga-verdict" ]; then
    cp "$TMP_DIR/ga-verdict"/*.json "$EVIDENCE_DIR/" 2>/dev/null || true
fi

# Extract signed artifacts
if [ -d "$TMP_DIR/signed-artifacts" ]; then
    mkdir -p "$EVIDENCE_DIR/artifacts"
    cp -r "$TMP_DIR/signed-artifacts"/* "$EVIDENCE_DIR/artifacts/" 2>/dev/null || true
fi

# Extract signing key
if [ -d "$TMP_DIR/signing-public-key" ]; then
    mkdir -p "$EVIDENCE_DIR/keys"
    cp "$TMP_DIR/signing-public-key"/*.pub "$EVIDENCE_DIR/keys/" 2>/dev/null || true
fi

# Validate collected files
echo ""
echo "Validating collected evidence..."

MISSING_FILES=0

# Check required files
REQUIRED_FILES=(
    "phase_c_aggregate_verdict.json"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$EVIDENCE_DIR/$file" ]; then
        echo "✅ Found: $file"
    else
        echo "❌ Missing: $file"
        MISSING_FILES=$((MISSING_FILES + 1))
    fi
done

# Check optional but recommended files
OPTIONAL_FILES=(
    "phase_c_linux_results.json"
    "phase_c_windows_results.json"
)

for file in "${OPTIONAL_FILES[@]}"; do
    if [ -f "$EVIDENCE_DIR/$file" ]; then
        echo "✅ Found: $file"
    else
        echo "⚠ Missing (optional): $file"
    fi
done

# Check artifacts
if [ -d "$EVIDENCE_DIR/artifacts/signed" ]; then
    ARTIFACT_COUNT=$(find "$EVIDENCE_DIR/artifacts/signed" -name "*.manifest.json" | wc -l)
    echo "✅ Found $ARTIFACT_COUNT artifact manifest(s)"
else
    echo "⚠ Missing: artifacts/signed/"
fi

# Check SBOM
if [ -f "$EVIDENCE_DIR/artifacts/sbom/manifest.json" ]; then
    echo "✅ Found: SBOM manifest"
else
    echo "⚠ Missing: SBOM manifest"
fi

# Check keys
if [ -d "$EVIDENCE_DIR/keys" ] && [ -n "$(find "$EVIDENCE_DIR/keys" -name "*.pub" 2>/dev/null)" ]; then
    echo "✅ Found: Signing public key"
else
    echo "⚠ Missing: Signing public key"
fi

echo ""

if [ $MISSING_FILES -gt 0 ]; then
    echo "❌ ERROR: Some required files are missing"
    echo "Please download artifacts manually from GitHub Actions"
    exit 1
fi

# Compute hashes
echo "Computing evidence hashes..."
cd "$EVIDENCE_DIR"
find . -type f -not -name "evidence_hashes.txt" -exec sha256sum {} \; | sort > evidence_hashes.txt
echo "✅ Hashes computed: evidence_hashes.txt"

echo ""
echo "=========================================="
echo "✅ Evidence collection complete"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Review collected files in: $EVIDENCE_DIR"
echo "2. Run offline verification: ./verify_offline.sh"
echo "3. Update PHASE_6_GA_PROOF.md with CI run information"
echo ""
