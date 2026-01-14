#!/bin/bash
# RansomEye v1.0 Core Build Script
# Builds Core Python components into core-installer.tar.gz

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="${PROJECT_ROOT}/build"
ARTIFACTS_DIR="${BUILD_DIR}/artifacts"
CORE_BUILD_DIR="${BUILD_DIR}/core-installer"

# Set deterministic timestamp
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-$(date +%s)}"
export PYTHONHASHSEED=0

echo "=========================================="
echo "Building RansomEye Core"
echo "=========================================="
echo "SOURCE_DATE_EPOCH: ${SOURCE_DATE_EPOCH}"
echo ""

# Clean previous build
rm -rf "${CORE_BUILD_DIR}"
mkdir -p "${CORE_BUILD_DIR}"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv "${BUILD_DIR}/venv-core"
source "${BUILD_DIR}/venv-core/bin/activate"

# Upgrade pip to specific version for determinism
echo "Upgrading pip..."
pip install --upgrade pip==23.3.1

# Install dependencies with exact pins
echo "Installing dependencies..."
cd "${PROJECT_ROOT}"

# Find all requirements.txt files and verify they use exact pins
REQUIREMENTS_FILES=$(find . -name "requirements.txt" -not -path "./build/*" -not -path "./.git/*" | sort)

for req_file in ${REQUIREMENTS_FILES}; do
    echo "Processing ${req_file}..."
    
    # Check for unpinned dependencies (warn but don't fail for now)
    if grep -E "^\s*[^#].*[>=~]" "${req_file}" > /dev/null 2>&1; then
        echo "⚠️  WARNING: ${req_file} contains unpinned dependencies"
        echo "   This may affect build reproducibility"
    fi
    
    pip install --no-deps -r "${req_file}" || {
        echo "❌ Failed to install dependencies from ${req_file}"
        exit 1
    }
done

# Verify no dependency conflicts
echo "Verifying dependencies..."
pip check || {
    echo "❌ Dependency conflicts detected"
    exit 1
}

# Copy Python code
echo "Copying Python code..."
mkdir -p "${CORE_BUILD_DIR}/common"
mkdir -p "${CORE_BUILD_DIR}/core"
mkdir -p "${CORE_BUILD_DIR}/services"
mkdir -p "${CORE_BUILD_DIR}/contracts"
mkdir -p "${CORE_BUILD_DIR}/schemas"
mkdir -p "${CORE_BUILD_DIR}/installer"

cp -r "${PROJECT_ROOT}/common"/* "${CORE_BUILD_DIR}/common/" 2>/dev/null || true
cp -r "${PROJECT_ROOT}/core"/* "${CORE_BUILD_DIR}/core/" 2>/dev/null || true
cp -r "${PROJECT_ROOT}/services"/* "${CORE_BUILD_DIR}/services/" 2>/dev/null || true
cp -r "${PROJECT_ROOT}/contracts"/* "${CORE_BUILD_DIR}/contracts/" 2>/dev/null || true
cp -r "${PROJECT_ROOT}/schemas"/* "${CORE_BUILD_DIR}/schemas/" 2>/dev/null || true
cp -r "${PROJECT_ROOT}/installer/core"/* "${CORE_BUILD_DIR}/installer/" 2>/dev/null || true

# Generate build metadata
echo "Generating build metadata..."
python3 "${SCRIPT_DIR}/generate_build_info.py" \
    --output "${CORE_BUILD_DIR}/build-info.json" \
    --build-id "${GITHUB_RUN_ID:-local}"

# Create tarball with deterministic timestamps
echo "Creating tarball..."
cd "${BUILD_DIR}"
tar czf "${ARTIFACTS_DIR}/core-installer.tar.gz" \
    --owner=0 --group=0 \
    --mtime="@${SOURCE_DATE_EPOCH}" \
    --format=gnu \
    -C "${BUILD_DIR}" \
    core-installer/

# Verify artifact is non-empty
if [ ! -s "${ARTIFACTS_DIR}/core-installer.tar.gz" ]; then
    echo "❌ ERROR: core-installer.tar.gz is empty"
    exit 1
fi

ARTIFACT_SIZE=$(stat -f%z "${ARTIFACTS_DIR}/core-installer.tar.gz" 2>/dev/null || stat -c%s "${ARTIFACTS_DIR}/core-installer.tar.gz" 2>/dev/null)
echo "✅ Core build complete: core-installer.tar.gz (${ARTIFACT_SIZE} bytes)"
