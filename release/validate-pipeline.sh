#!/usr/bin/env bash
#
# RansomEye Pipeline Validation Script
# Purpose: Validate CI/CD pipeline implementation (dry-run test)
# Status: OPERATIONAL
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "================================================================"
echo "RansomEye CI/CD Pipeline Validation"
echo "================================================================"
echo ""

# Test 1: Build scripts exist and are executable
echo "✓ Test 1: Verify build scripts..."
test -x "$PROJECT_ROOT/scripts/build_core.sh" || { echo "❌ build_core.sh not executable"; exit 1; }
test -x "$PROJECT_ROOT/scripts/build_dpi_probe.sh" || { echo "❌ build_dpi_probe.sh not executable"; exit 1; }
test -x "$PROJECT_ROOT/scripts/build_linux_agent.sh" || { echo "❌ build_linux_agent.sh not executable"; exit 1; }
test -x "$PROJECT_ROOT/scripts/build_windows_agent.sh" || { echo "❌ build_windows_agent.sh not executable"; exit 1; }
echo "  ✓ All build scripts present and executable"

# Test 2: Helper scripts exist and are executable
echo "✓ Test 2: Verify helper scripts..."
test -x "$PROJECT_ROOT/release/promote.sh" || { echo "❌ promote.sh not executable"; exit 1; }
test -x "$PROJECT_ROOT/release/publish.sh" || { echo "❌ publish.sh not executable"; exit 1; }
test -x "$PROJECT_ROOT/tools/manifest_generator.py" || { echo "❌ manifest_generator.py not executable"; exit 1; }
echo "  ✓ All helper scripts present and executable"

# Test 3: Verification infrastructure exists
echo "✓ Test 3: Verify verification infrastructure..."
test -f "$PROJECT_ROOT/scripts/verify_release_bundle.py" || { echo "❌ verify_release_bundle.py missing"; exit 1; }
test -f "$PROJECT_ROOT/scripts/create_release_bundle.py" || { echo "❌ create_release_bundle.py missing"; exit 1; }
echo "  ✓ Verification infrastructure present"

# Test 4: CI/CD workflow exists
echo "✓ Test 4: Verify CI/CD workflow..."
test -f "$PROJECT_ROOT/.github/workflows/ransomeye-release.yml" || { echo "❌ CI workflow missing"; exit 1; }
echo "  ✓ CI/CD workflow present"

# Test 5: Documentation exists
echo "✓ Test 5: Verify documentation..."
test -f "$PROJECT_ROOT/docs/governance/signing-ceremony-and-key-custody-sop-v1.0.0.md" || { echo "❌ Signing SOP missing"; exit 1; }
test -f "$PROJECT_ROOT/docs/governance/promotion-approvals-and-release-governance-v1.0.0.md" || { echo "❌ Promotion governance missing"; exit 1; }
test -f "$PROJECT_ROOT/docs/operations/deployment-runbook-v1.0.0.md" || { echo "❌ Deployment runbook missing"; exit 1; }
test -f "$PROJECT_ROOT/docs/operations/quick-start-v1.0.0.md" || { echo "❌ Quick-start missing"; exit 1; }
echo "  ✓ All documentation present"

# Test 6: Script syntax validation
echo "✓ Test 6: Validate script syntax..."
bash -n "$PROJECT_ROOT/release/promote.sh" || { echo "❌ promote.sh syntax error"; exit 1; }
bash -n "$PROJECT_ROOT/release/publish.sh" || { echo "❌ publish.sh syntax error"; exit 1; }
python3 -m py_compile "$PROJECT_ROOT/tools/manifest_generator.py" 2>/dev/null || { echo "❌ manifest_generator.py syntax error"; exit 1; }
echo "  ✓ All scripts have valid syntax"

# Test 7: Manifest generator functional test
echo "✓ Test 7: Test manifest generator..."
TEST_DIR=$(mktemp -d)
mkdir -p "$TEST_DIR/test-release"
echo "test" > "$TEST_DIR/test-release/test.txt"
python3 "$PROJECT_ROOT/tools/manifest_generator.py" \
    --input "$TEST_DIR/test-release" \
    --output "$TEST_DIR/manifest.json" \
    --version "v0.0.1-test" \
    --pretty > /dev/null || { echo "❌ manifest_generator.py failed"; rm -rf "$TEST_DIR"; exit 1; }
test -f "$TEST_DIR/manifest.json" || { echo "❌ manifest.json not created"; rm -rf "$TEST_DIR"; exit 1; }
rm -rf "$TEST_DIR"
echo "  ✓ Manifest generator working"

# Test 8: promote.sh help and validation
echo "✓ Test 8: Test promote.sh..."
"$PROJECT_ROOT/release/promote.sh" --help > /dev/null || { echo "❌ promote.sh --help failed"; exit 1; }
echo "  ✓ promote.sh functional"

# Test 9: publish.sh help
echo "✓ Test 9: Test publish.sh..."
"$PROJECT_ROOT/release/publish.sh" 2>&1 | grep -q "Usage:" || { echo "❌ publish.sh usage not available"; exit 1; }
echo "  ✓ publish.sh functional"

echo ""
echo "================================================================"
echo "VALIDATION COMPLETE - ALL TESTS PASSED"
echo "================================================================"
echo ""
echo "Pipeline components verified:"
echo "  ✓ Build scripts (4)"
echo "  ✓ Helper scripts (3)"
echo "  ✓ Verification infrastructure"
echo "  ✓ CI/CD workflow"
echo "  ✓ Documentation (governance + operations)"
echo "  ✓ Script syntax"
echo "  ✓ Functional tests"
echo ""
echo "Next steps:"
echo "  1. Generate signing keys (follow signing SOP)"
echo "  2. Create GitHub environments (dev, staging, prod)"
echo "  3. Configure environment protection rules"
echo "  4. Run full dry-run release with tag v0.0.1-test"
echo ""
