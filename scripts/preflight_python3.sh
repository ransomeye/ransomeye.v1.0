#!/bin/bash
#
# RansomEye Python3 Preflight Check
# AUTHORITATIVE: Enforce python3 availability and minimum version
#

set -euo pipefail

MIN_MAJOR=3
MIN_MINOR=9

if ! command -v python3 >/dev/null 2>&1; then
    echo "FATAL: python3 is required (>=${MIN_MAJOR}.${MIN_MINOR}) but was not found in PATH." >&2
    exit 1
fi

version_str=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
major=${version_str%%.*}
minor=${version_str#*.}
minor=${minor%%.*}

if [ "$major" -lt "$MIN_MAJOR" ] || { [ "$major" -eq "$MIN_MAJOR" ] && [ "$minor" -lt "$MIN_MINOR" ]; }; then
    echo "FATAL: python3 >= ${MIN_MAJOR}.${MIN_MINOR} required, found ${version_str}." >&2
    exit 1
fi

echo "✓ python3 ${version_str} detected (>=${MIN_MAJOR}.${MIN_MINOR})"
