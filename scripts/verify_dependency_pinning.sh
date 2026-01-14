#!/bin/bash
# RansomEye v1.0 Dependency Pinning Verification
# Verifies that all dependencies are pinned (no ranges, no >=, no ~=)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "Verifying Dependency Pinning"
echo "=========================================="

FAILED=0

# Check Python requirements.txt files
echo "Checking Python requirements.txt files..."
REQUIREMENTS_FILES=$(find "${PROJECT_ROOT}" -name "requirements.txt" -not -path "./build/*" -not -path "./.git/*" | sort)

for req_file in ${REQUIREMENTS_FILES}; do
    echo "Checking ${req_file}..."
    
    # Check for unpinned dependencies (>=, ~=, >, <, !=)
    if grep -E "^\s*[^#].*[>=~<!=]" "${req_file}" > /dev/null 2>&1; then
        echo "❌ ERROR: ${req_file} contains unpinned dependencies:"
        grep -E "^\s*[^#].*[>=~<!=]" "${req_file}" | sed 's/^/   /'
        FAILED=1
    else
        echo "✅ ${req_file} uses exact pins"
    fi
done

# Check Rust Cargo.toml files
echo ""
echo "Checking Rust Cargo.toml files..."
CARGO_FILES=$(find "${PROJECT_ROOT}" -name "Cargo.toml" -not -path "./build/*" -not -path "./.git/*" | sort)

for cargo_file in ${CARGO_FILES}; do
    echo "Checking ${cargo_file}..."
    
    # Check for version ranges in dependencies
    if grep -E '^\s*version\s*=\s*"[^"]*[>=~<!=]' "${cargo_file}" > /dev/null 2>&1; then
        echo "❌ ERROR: ${cargo_file} contains version ranges:"
        grep -E '^\s*version\s*=\s*"[^"]*[>=~<!=]' "${cargo_file}" | sed 's/^/   /'
        FAILED=1
    else
        echo "✅ ${cargo_file} uses exact versions"
    fi
    
    # Verify Cargo.lock exists
    CARGO_DIR=$(dirname "${cargo_file}")
    if [ ! -f "${CARGO_DIR}/Cargo.lock" ]; then
        echo "⚠️  WARNING: ${CARGO_DIR}/Cargo.lock not found (will be generated on first build)"
    fi
done

if [ $FAILED -eq 1 ]; then
    echo ""
    echo "❌ Dependency pinning verification FAILED"
    echo "All dependencies must use exact version pins (e.g., ==1.2.3, not >=1.2.3)"
    exit 1
else
    echo ""
    echo "✅ Dependency pinning verification PASSED"
    exit 0
fi
