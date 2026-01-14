#!/bin/bash
# RansomEye v1.0 Linux Agent Build Script
# Builds Linux Agent Rust binary into linux-agent.tar.gz

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="${PROJECT_ROOT}/build"
ARTIFACTS_DIR="${BUILD_DIR}/artifacts"
AGENT_SOURCE_DIR="${PROJECT_ROOT}/services/linux-agent"
AGENT_BUILD_DIR="${BUILD_DIR}/linux-agent"

# Set deterministic timestamp
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-$(date +%s)}"
export RUSTFLAGS="-C link-arg=-fuse-ld=gold"

echo "=========================================="
echo "Building RansomEye Linux Agent"
echo "=========================================="
echo "SOURCE_DATE_EPOCH: ${SOURCE_DATE_EPOCH}"
echo ""

# Verify Rust toolchain
if ! command -v rustc &> /dev/null; then
    echo "❌ ERROR: rustc not found. Installing Rust toolchain..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
fi

# Verify Cargo.lock exists
if [ ! -f "${AGENT_SOURCE_DIR}/Cargo.lock" ]; then
    echo "❌ ERROR: Cargo.lock not found. Generating..."
    cd "${AGENT_SOURCE_DIR}"
    cargo generate-lockfile
fi

# Clean previous build
rm -rf "${AGENT_BUILD_DIR}"
mkdir -p "${AGENT_BUILD_DIR}"

# Build Rust binary
echo "Building Rust binary..."
cd "${AGENT_SOURCE_DIR}"

# Install target if not present
rustup target add x86_64-unknown-linux-gnu || true

# Build with locked dependencies for reproducibility
cargo build \
    --release \
    --locked \
    --target x86_64-unknown-linux-gnu

# Verify binary exists
BINARY_PATH="${AGENT_SOURCE_DIR}/target/x86_64-unknown-linux-gnu/release/ransomeye-linux-agent"
if [ ! -f "${BINARY_PATH}" ]; then
    echo "❌ ERROR: Binary not found at ${BINARY_PATH}"
    exit 1
fi

# Verify binary is executable
if [ ! -x "${BINARY_PATH}" ]; then
    echo "❌ ERROR: Binary is not executable"
    exit 1
fi

# Record binary hash
echo "Recording binary hash..."
sha256sum "${BINARY_PATH}" > "${AGENT_BUILD_DIR}/binary.sha256"

# Copy binary and installer
echo "Packaging agent..."
mkdir -p "${AGENT_BUILD_DIR}/bin"
mkdir -p "${AGENT_BUILD_DIR}/installer"

cp "${BINARY_PATH}" "${AGENT_BUILD_DIR}/bin/ransomeye-linux-agent"
cp -r "${PROJECT_ROOT}/installer/linux-agent"/* "${AGENT_BUILD_DIR}/installer/" 2>/dev/null || true

# Generate build metadata
echo "Generating build metadata..."
python3 "${SCRIPT_DIR}/generate_build_info.py" \
    --output "${AGENT_BUILD_DIR}/build-info.json" \
    --build-id "${GITHUB_RUN_ID:-local}"

# Create tarball with deterministic timestamps
echo "Creating tarball..."
cd "${BUILD_DIR}"
tar czf "${ARTIFACTS_DIR}/linux-agent.tar.gz" \
    --owner=0 --group=0 \
    --mtime="@${SOURCE_DATE_EPOCH}" \
    --format=gnu \
    -C "${BUILD_DIR}" \
    linux-agent/

# Verify artifact is non-empty
if [ ! -s "${ARTIFACTS_DIR}/linux-agent.tar.gz" ]; then
    echo "❌ ERROR: linux-agent.tar.gz is empty"
    exit 1
fi

ARTIFACT_SIZE=$(stat -f%z "${ARTIFACTS_DIR}/linux-agent.tar.gz" 2>/dev/null || stat -c%s "${ARTIFACTS_DIR}/linux-agent.tar.gz" 2>/dev/null)
BINARY_SIZE=$(stat -f%z "${BINARY_PATH}" 2>/dev/null || stat -c%s "${BINARY_PATH}" 2>/dev/null)
echo "✅ Linux Agent build complete: linux-agent.tar.gz (${ARTIFACT_SIZE} bytes)"
echo "   Binary size: ${BINARY_SIZE} bytes"
