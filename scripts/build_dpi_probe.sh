#!/bin/bash
# RansomEye v1.0 DPI Probe Build Script
# Builds DPI Probe Python package into dpi-probe.tar.gz

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="${PROJECT_ROOT}/build"
ARTIFACTS_DIR="${BUILD_DIR}/artifacts"
PROBE_SOURCE_DIR="${PROJECT_ROOT}/dpi/probe"
PROBE_BUILD_DIR="${BUILD_DIR}/dpi-probe"

# Set deterministic timestamp
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-$(date +%s)}"
export PYTHONHASHSEED=0

echo "=========================================="
echo "Building RansomEye DPI Probe"
echo "=========================================="
echo "SOURCE_DATE_EPOCH: ${SOURCE_DATE_EPOCH}"
echo ""

# Clean previous build
rm -rf "${PROBE_BUILD_DIR}"
mkdir -p "${PROBE_BUILD_DIR}"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv "${BUILD_DIR}/venv-dpi"
source "${BUILD_DIR}/venv-dpi/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip==23.3.1

# Check for requirements.txt
if [ -f "${PROBE_SOURCE_DIR}/requirements.txt" ]; then
    echo "Installing dependencies..."
    pip install --no-deps -r "${PROBE_SOURCE_DIR}/requirements.txt" || {
        echo "❌ Failed to install dependencies"
        exit 1
    }
fi

# Copy Python code
echo "Copying Python code..."
mkdir -p "${PROBE_BUILD_DIR}/probe"
mkdir -p "${PROBE_BUILD_DIR}/installer"

cp -r "${PROBE_SOURCE_DIR}"/* "${PROBE_BUILD_DIR}/probe/" 2>/dev/null || true
cp -r "${PROJECT_ROOT}/installer/dpi-probe"/* "${PROBE_BUILD_DIR}/installer/" 2>/dev/null || true

# Copy common utilities if needed
if [ -d "${PROJECT_ROOT}/common" ]; then
    mkdir -p "${PROBE_BUILD_DIR}/common"
    cp -r "${PROJECT_ROOT}/common"/* "${PROBE_BUILD_DIR}/common/" 2>/dev/null || true
fi

# Generate build metadata
echo "Generating build metadata..."
python3 "${SCRIPT_DIR}/generate_build_info.py" \
    --output "${PROBE_BUILD_DIR}/build-info.json" \
    --build-id "${GITHUB_RUN_ID:-local}"

# Create tarball with deterministic timestamps
echo "Creating tarball..."
cd "${BUILD_DIR}"
tar czf "${ARTIFACTS_DIR}/dpi-probe.tar.gz" \
    --owner=0 --group=0 \
    --mtime="@${SOURCE_DATE_EPOCH}" \
    --format=gnu \
    -C "${BUILD_DIR}" \
    dpi-probe/

# Verify artifact is non-empty
if [ ! -s "${ARTIFACTS_DIR}/dpi-probe.tar.gz" ]; then
    echo "❌ ERROR: dpi-probe.tar.gz is empty"
    exit 1
fi

ARTIFACT_SIZE=$(stat -f%z "${ARTIFACTS_DIR}/dpi-probe.tar.gz" 2>/dev/null || stat -c%s "${ARTIFACTS_DIR}/dpi-probe.tar.gz" 2>/dev/null)
echo "✅ DPI Probe build complete: dpi-probe.tar.gz (${ARTIFACT_SIZE} bytes)"
