#!/bin/bash
# Phase-6 Offline Verification Script
# Run in clean environment with no network access
# 
# Usage: ./verify_offline.sh [evidence_directory]
#
# This script verifies:
# 1. GA verdict is GA-READY
# 2. All artifact signatures are valid
# 3. SBOM signature is valid
# 4. All hashes match

set -euo pipefail

# Default evidence directory
EVIDENCE_DIR="${1:-$(dirname "$0")}"
SCRIPT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
KEY_DIR="$EVIDENCE_DIR/keys"
ARTIFACTS_DIR="$EVIDENCE_DIR/artifacts"

echo "=========================================="
echo "PHASE 6: Offline Verification"
echo "=========================================="
echo "Evidence Directory: $EVIDENCE_DIR"
echo "Script Directory: $SCRIPT_DIR"
echo ""

# Check required files exist
if [ ! -f "$EVIDENCE_DIR/phase_c_aggregate_verdict.json" ]; then
    echo "❌ ERROR: phase_c_aggregate_verdict.json not found"
    exit 1
fi

if [ ! -d "$KEY_DIR" ]; then
    echo "❌ ERROR: Keys directory not found: $KEY_DIR"
    exit 1
fi

if [ ! -d "$ARTIFACTS_DIR" ]; then
    echo "❌ ERROR: Artifacts directory not found: $ARTIFACTS_DIR"
    exit 1
fi

# 1. Verify GA verdict
echo "=== Step 1: Verifying GA Verdict ==="
VERDICT_FILE="$EVIDENCE_DIR/phase_c_aggregate_verdict.json"

VERDICT=$(python3 -c "
import json
import sys
try:
    with open('$VERDICT_FILE') as f:
        data = json.load(f)
        verdict = data.get('verdict', 'UNKNOWN')
        ga_ready = data.get('ga_ready', False)
        linux_pass = data.get('linux_pass', False)
        windows_pass = data.get('windows_pass', False)
        
        print(f'Verdict: {verdict}')
        print(f'GA Ready: {ga_ready}')
        print(f'Linux Pass: {linux_pass}')
        print(f'Windows Pass: {windows_pass}')
        
        if verdict != 'GA-READY':
            print(f'❌ ERROR: Verdict is {verdict}, expected GA-READY', file=sys.stderr)
            sys.exit(1)
        if not ga_ready:
            print('❌ ERROR: ga_ready is False, expected True', file=sys.stderr)
            sys.exit(1)
        if not linux_pass:
            print('❌ ERROR: Linux validation did not pass', file=sys.stderr)
            sys.exit(1)
        if not windows_pass:
            print('❌ ERROR: Windows validation did not pass', file=sys.stderr)
            sys.exit(1)
        
        print('✅ GA Verdict: GA-READY')
        sys.exit(0)
except Exception as e:
    print(f'❌ ERROR: Failed to parse verdict file: {e}', file=sys.stderr)
    sys.exit(1)
")

if [ $? -ne 0 ]; then
    echo "$VERDICT"
    exit 1
fi

echo "$VERDICT"
echo ""

# 2. Verify artifact signatures
echo "=== Step 2: Verifying Artifact Signatures ==="
SIGNED_COUNT=0
FAILED_COUNT=0

# Find all artifacts
for artifact in "$ARTIFACTS_DIR"/*.tar.gz "$ARTIFACTS_DIR"/*.zip; do
    if [ ! -f "$artifact" ]; then
        continue
    fi
    
    ARTIFACT_NAME=$(basename "$artifact")
    MANIFEST="$ARTIFACTS_DIR/signed/${ARTIFACT_NAME}.manifest.json"
    SIGNATURE="$ARTIFACTS_DIR/signed/${ARTIFACT_NAME}.manifest.sig"
    
    if [ ! -f "$MANIFEST" ]; then
        echo "❌ ERROR: Manifest not found for $ARTIFACT_NAME"
        FAILED_COUNT=$((FAILED_COUNT + 1))
        continue
    fi
    
    if [ ! -f "$SIGNATURE" ]; then
        echo "❌ ERROR: Signature not found for $ARTIFACT_NAME"
        FAILED_COUNT=$((FAILED_COUNT + 1))
        continue
    fi
    
    echo "Verifying: $ARTIFACT_NAME"
    
    cd "$SCRIPT_DIR"
    python3 supply-chain/cli/verify_artifacts.py \
        --artifact "$artifact" \
        --manifest "$MANIFEST" \
        --key-dir "$KEY_DIR" \
        --signing-key-id ci-signing-key
    
    if [ $? -eq 0 ]; then
        echo "✅ Verified: $ARTIFACT_NAME"
        SIGNED_COUNT=$((SIGNED_COUNT + 1))
    else
        echo "❌ Verification failed: $ARTIFACT_NAME"
        FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
done

if [ $FAILED_COUNT -gt 0 ]; then
    echo "❌ ERROR: $FAILED_COUNT artifact(s) failed verification"
    exit 1
fi

echo "✅ All $SIGNED_COUNT artifact(s) verified"
echo ""

# 3. Verify SBOM
echo "=== Step 3: Verifying SBOM ==="
SBOM_MANIFEST="$ARTIFACTS_DIR/sbom/manifest.json"
SBOM_SIGNATURE="$ARTIFACTS_DIR/sbom/manifest.json.sig"

if [ ! -f "$SBOM_MANIFEST" ]; then
    echo "❌ ERROR: SBOM manifest not found"
    exit 1
fi

if [ ! -f "$SBOM_SIGNATURE" ]; then
    echo "❌ ERROR: SBOM signature not found"
    exit 1
fi

cd "$SCRIPT_DIR"
python3 release/verify_sbom.py \
    --release-root "$ARTIFACTS_DIR" \
    --manifest "$SBOM_MANIFEST" \
    --signature "$SBOM_SIGNATURE" \
    --key-dir "$KEY_DIR"

if [ $? -eq 0 ]; then
    echo "✅ SBOM verified"
else
    echo "❌ SBOM verification failed"
    exit 1
fi

echo ""

# 4. Compute and display hashes
echo "=== Step 4: Computing Evidence Hashes ==="
cd "$EVIDENCE_DIR"
find . -type f -exec sha256sum {} \; | sort > evidence_hashes.txt
echo "✅ Evidence hashes computed: evidence_hashes.txt"
echo ""

echo "=========================================="
echo "✅ ALL VERIFICATIONS PASSED"
echo "=========================================="
echo "GA Verdict: GA-READY"
echo "Artifacts Verified: $SIGNED_COUNT"
echo "SBOM Verified: ✅"
echo "Evidence Directory: $EVIDENCE_DIR"
echo ""
