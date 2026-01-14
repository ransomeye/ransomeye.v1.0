#!/bin/bash
#
# RansomEye License Compliance CI Gate
#
# Fail-fast CI gate that:
# - Runs license validation
# - Blocks build on license violation
# - Prints exact offending dependency + license
#
# Exit codes:
#   0 - All validations passed
#   1 - License violation detected
#   2 - Script error (missing files, etc.)
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "=========================================="
echo "RansomEye License Compliance CI Gate"
echo "=========================================="
echo ""

# Check required files exist
if [[ ! -f "${SCRIPT_DIR}/LICENSE_POLICY.json" ]]; then
    echo -e "${RED}ERROR: LICENSE_POLICY.json not found${NC}" >&2
    exit 2
fi

if [[ ! -f "${SCRIPT_DIR}/THIRD_PARTY_INVENTORY.json" ]]; then
    echo -e "${RED}ERROR: THIRD_PARTY_INVENTORY.json not found${NC}" >&2
    exit 2
fi

# Check Python tools exist
if [[ ! -f "${SCRIPT_DIR}/license_scan.py" ]]; then
    echo -e "${RED}ERROR: license_scan.py not found${NC}" >&2
    exit 2
fi

if [[ ! -f "${SCRIPT_DIR}/validate_licenses.py" ]]; then
    echo -e "${RED}ERROR: validate_licenses.py not found${NC}" >&2
    exit 2
fi

# Check Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: python3 not found${NC}" >&2
    exit 2
fi

echo "Step 1: Running license scan..."
echo "-----------------------------------"
if ! python3 "${SCRIPT_DIR}/license_scan.py" > /tmp/license_scan_report.json 2>&1; then
    echo -e "${RED}FAILED: License scan detected violations${NC}" >&2
    echo ""
    echo "Violations detected:"
    echo "--------------------"
    
    # Extract violations from JSON report if possible
    if [[ -f /tmp/license_scan_report.json ]]; then
        # Try to parse JSON and show violations, otherwise show raw output
        python3 "${SCRIPT_DIR}/license_scan.py" 2>&1 | grep -A 100 "violations" || cat /tmp/license_scan_report.json
    
    echo ""
    echo -e "${RED}BUILD BLOCKED: License violations must be resolved${NC}" >&2
    exit 1
fi

SCAN_EXIT=$?
if [[ $SCAN_EXIT -ne 0 ]]; then
    echo -e "${RED}FAILED: License scan failed with exit code ${SCAN_EXIT}${NC}" >&2
    exit 1
fi

echo -e "${GREEN}✓ License scan passed${NC}"
echo ""

echo "Step 2: Running strict validation..."
echo "-----------------------------------"
if ! python3 "${SCRIPT_DIR}/validate_licenses.py" 2>&1; then
    echo ""
    echo -e "${RED}FAILED: License validation detected errors${NC}" >&2
    echo ""
    echo -e "${RED}BUILD BLOCKED: License validation errors must be resolved${NC}" >&2
    exit 1
fi

VALIDATION_EXIT=$?
if [[ $VALIDATION_EXIT -ne 0 ]]; then
    echo -e "${RED}FAILED: License validation failed with exit code ${VALIDATION_EXIT}${NC}" >&2
    exit 1
fi

echo -e "${GREEN}✓ License validation passed${NC}"
echo ""

echo "Step 3: Final compliance check..."
echo "-----------------------------------"
echo -e "${GREEN}✓ All checks completed by previous steps${NC}"
echo ""

echo "=========================================="
echo -e "${GREEN}SUCCESS: All license compliance checks passed${NC}"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - License scan: PASSED"
echo "  - License validation: PASSED"
echo "  - Forbidden license check: PASSED"
echo ""
exit 0
