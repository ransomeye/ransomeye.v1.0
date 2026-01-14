#!/bin/bash
# RansomEye v1.0 Windows Agent Build Script
# Builds Windows Agent Python package into windows-agent.zip

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="${PROJECT_ROOT}/build"
ARTIFACTS_DIR="${BUILD_DIR}/artifacts"
AGENT_SOURCE_DIR="${PROJECT_ROOT}/agents/windows"
AGENT_BUILD_DIR="${BUILD_DIR}/windows-agent"

# Set deterministic timestamp
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-$(date +%s)}"
export PYTHONHASHSEED=0

echo "=========================================="
echo "Building RansomEye Windows Agent"
echo "=========================================="
echo "SOURCE_DATE_EPOCH: ${SOURCE_DATE_EPOCH}"
echo ""

# Clean previous build
rm -rf "${AGENT_BUILD_DIR}"
mkdir -p "${AGENT_BUILD_DIR}"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv "${BUILD_DIR}/venv-windows-agent"
source "${BUILD_DIR}/venv-windows-agent/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip==23.3.1

# Check for requirements.txt in agent directory
if [ -f "${AGENT_SOURCE_DIR}/requirements.txt" ]; then
    echo "Installing dependencies..."
    pip install --no-deps -r "${AGENT_SOURCE_DIR}/requirements.txt" || {
        echo "❌ Failed to install dependencies"
        exit 1
    }
fi

# Copy Python code
echo "Copying Python code..."
mkdir -p "${AGENT_BUILD_DIR}/agent"
mkdir -p "${AGENT_BUILD_DIR}/installer"

cp -r "${AGENT_SOURCE_DIR}/agent"/* "${AGENT_BUILD_DIR}/agent/" 2>/dev/null || true
cp -r "${PROJECT_ROOT}/installer/windows-agent"/* "${AGENT_BUILD_DIR}/installer/" 2>/dev/null || true

# Copy common utilities if needed
if [ -d "${PROJECT_ROOT}/common" ]; then
    mkdir -p "${AGENT_BUILD_DIR}/common"
    cp -r "${PROJECT_ROOT}/common"/* "${AGENT_BUILD_DIR}/common/" 2>/dev/null || true
fi

# Generate build metadata
echo "Generating build metadata..."
python3 "${SCRIPT_DIR}/generate_build_info.py" \
    --output "${AGENT_BUILD_DIR}/build-info.json" \
    --build-id "${GITHUB_RUN_ID:-local}"

# Create ZIP with deterministic timestamps
echo "Creating ZIP archive..."
cd "${BUILD_DIR}"

# Use Python zipfile for deterministic timestamps
python3 << 'PYTHON_EOF'
import os
import zipfile
from pathlib import Path

source_date_epoch = int(os.environ.get('SOURCE_DATE_EPOCH', '0'))
zip_path = Path('build/artifacts/windows-agent.zip')
source_dir = Path('build/windows-agent')

# Remove existing zip
if zip_path.exists():
    zip_path.unlink()

# Create zip with deterministic timestamps
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            file_path = Path(root) / file
            arc_name = file_path.relative_to(source_dir.parent)
            zinfo = zipfile.ZipInfo(str(arc_name))
            zinfo.date_time = (1980, 1, 1, 0, 0, 0)  # Deterministic timestamp
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            with open(file_path, 'rb') as f:
                zf.writestr(zinfo, f.read())

print(f"Created {zip_path} ({zip_path.stat().st_size} bytes)")
PYTHON_EOF

# Verify artifact is non-empty
if [ ! -s "${ARTIFACTS_DIR}/windows-agent.zip" ]; then
    echo "❌ ERROR: windows-agent.zip is empty"
    exit 1
fi

ARTIFACT_SIZE=$(stat -f%z "${ARTIFACTS_DIR}/windows-agent.zip" 2>/dev/null || stat -c%s "${ARTIFACTS_DIR}/windows-agent.zip" 2>/dev/null)
echo "✅ Windows Agent build complete: windows-agent.zip (${ARTIFACT_SIZE} bytes)"
