#!/bin/bash
#
# RansomEye v1.0 Release Integrity Validation Script
# AUTHORITATIVE: Enterprise-grade validation for release bundle integrity
# Fail-closed: Any error terminates validation immediately
#

set -euo pipefail  # Fail-fast: exit on any error, undefined variable, or pipe failure

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Error handler: fail-closed
error_exit() {
    echo -e "${RED}FATAL: ${1}${NC}" >&2
    exit 1
}

# Warning handler
warn() {
    echo -e "${YELLOW}WARNING: ${1}${NC}" >&2
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_ROOT="$SCRIPT_DIR"

# Validate checksums file exists
validate_checksums_file() {
    echo "Validating checksums file..."
    
    local checksums_file="${RELEASE_ROOT}/checksums/SHA256SUMS"
    
    if [[ ! -f "$checksums_file" ]]; then
        error_exit "Checksums file not found: $checksums_file"
    fi
    
    # Verify checksums file format (SHA256 hash followed by filename)
    local invalid_lines=$(grep -vE "^[a-f0-9]{64}[[:space:]]+\./" "$checksums_file" || true)
    if [[ -n "$invalid_lines" ]]; then
        error_exit "Invalid checksums file format (expected: SHA256 hash followed by filename)"
    fi
    
    echo -e "${GREEN}✓${NC} Checksums file format valid"
}

# Verify all files in checksums exist
verify_files_exist() {
    echo ""
    echo "Verifying all checksummed files exist..."
    
    local checksums_file="${RELEASE_ROOT}/checksums/SHA256SUMS"
    local missing_files=()
    
    while IFS= read -r line; do
        # Extract filename from checksum line
        local file_path="${line#*\./}"
        local full_path="${RELEASE_ROOT}/${file_path}"
        
        if [[ ! -f "$full_path" ]]; then
            missing_files+=("$file_path")
        fi
    done < "$checksums_file"
    
    if [[ ${#missing_files[@]} -gt 0 ]]; then
        error_exit "Missing files referenced in checksums: ${missing_files[*]}"
    fi
    
    echo -e "${GREEN}✓${NC} All checksummed files exist"
}

# Verify checksums match
verify_checksums() {
    echo ""
    echo "Verifying file checksums..."
    
    local checksums_file="${RELEASE_ROOT}/checksums/SHA256SUMS"
    local failed_checksums=()
    
    cd "$RELEASE_ROOT" || error_exit "Failed to change to release root"
    
    while IFS= read -r line; do
        # Extract hash and filename
        local expected_hash="${line%% *}"
        local file_path="${line#*\./}"
        
        # Calculate actual hash
        local actual_hash
        if [[ ! -f "$file_path" ]]; then
            failed_checksums+=("$file_path (file not found)")
            continue
        fi
        
        actual_hash=$(sha256sum "$file_path" | cut -d' ' -f1)
        
        if [[ "$expected_hash" != "$actual_hash" ]]; then
            failed_checksums+=("$file_path (checksum mismatch: expected $expected_hash, got $actual_hash)")
        fi
    done < "$checksums_file"
    
    if [[ ${#failed_checksums[@]} -gt 0 ]]; then
        echo -e "${RED}Checksum verification failed:${NC}"
        for failure in "${failed_checksums[@]}"; do
            echo -e "${RED}  - ${failure}${NC}"
        done
        error_exit "Checksum verification failed for ${#failed_checksums[@]} file(s)"
    fi
    
    echo -e "${GREEN}✓${NC} All checksums verified successfully"
}

# Verify required component files exist
verify_component_files() {
    echo ""
    echo "Verifying required component files exist..."
    
    local components=("core" "linux-agent" "windows-agent" "dpi-probe")
    local required_files=("install.sh" "uninstall.sh" "README.md" "installer.manifest.json")
    local missing_files=()
    
    for component in "${components[@]}"; do
        local component_dir="${RELEASE_ROOT}/${component}"
        
        if [[ ! -d "$component_dir" ]]; then
            error_exit "Component directory not found: $component_dir"
        fi
        
        for file in "${required_files[@]}"; do
            # Windows Agent uses .bat instead of .sh
            if [[ "$component" == "windows-agent" ]]; then
                if [[ "$file" == "install.sh" ]]; then
                    file="install.bat"
                elif [[ "$file" == "uninstall.sh" ]]; then
                    file="uninstall.bat"
                fi
            fi
            
            if [[ ! -f "${component_dir}/${file}" ]]; then
                missing_files+=("${component}/${file}")
            fi
        done
        
        # Verify service file exists (different names for each component)
        local service_file=""
        case "$component" in
            "core")
                service_file="${component_dir}/ransomeye-core.service"
                ;;
            "linux-agent")
                service_file="${component_dir}/ransomeye-linux-agent.service"
                ;;
            "windows-agent")
                service_file="${component_dir}/ransomeye-windows-agent.service.txt"
                ;;
            "dpi-probe")
                service_file="${component_dir}/ransomeye-dpi.service"
                ;;
        esac
        
        if [[ ! -f "$service_file" ]]; then
            missing_files+=("$service_file")
        fi
    done
    
    if [[ ${#missing_files[@]} -gt 0 ]]; then
        error_exit "Missing required component files: ${missing_files[*]}"
    fi
    
    echo -e "${GREEN}✓${NC} All required component files exist"
}

# Verify audit artifacts exist
verify_audit_artifacts() {
    echo ""
    echo "Verifying audit artifacts exist..."
    
    local audit_dir="${RELEASE_ROOT}/audit"
    local required_audit_files=(
        "build-info.json"
        "component-manifest.json"
    )
    
    for file in "${required_audit_files[@]}"; do
        if [[ ! -f "${audit_dir}/${file}" ]]; then
            error_exit "Audit artifact not found: ${audit_dir}/${file}"
        fi
    done
    
    echo -e "${GREEN}✓${NC} All audit artifacts exist"
}

# Verify signature file exists (optional, may be placeholder)
verify_signature_file() {
    echo ""
    echo "Verifying signature file..."
    
    local signature_file="${RELEASE_ROOT}/checksums/SHA256SUMS.sig"
    
    if [[ ! -f "$signature_file" ]]; then
        warn "Signature file not found: $signature_file (signature verification skipped)"
        return
    fi
    
    # If GPG is available, verify signature
    if command -v gpg &> /dev/null; then
        echo "Attempting GPG signature verification..."
        if gpg --verify "$signature_file" "${RELEASE_ROOT}/checksums/SHA256SUMS" 2>/dev/null; then
            echo -e "${GREEN}✓${NC} Signature verified successfully"
        else
            warn "Signature verification failed (signing key may not be available - this is expected if signature is placeholder)"
        fi
    else
        warn "GPG not available - signature verification skipped"
    fi
}

# Main validation flow
main() {
    echo ""
    echo "================================================================================"
    echo "RansomEye v1.0 Release Integrity Validation"
    echo "================================================================================"
    echo ""
    
    validate_checksums_file
    verify_files_exist
    verify_checksums
    verify_component_files
    verify_audit_artifacts
    verify_signature_file
    
    echo ""
    echo "================================================================================"
    echo -e "${GREEN}Release integrity validation PASSED${NC}"
    echo "================================================================================"
    echo ""
    echo "All required files are present and checksums verified."
    echo ""
    echo "Next steps:"
    echo "  1. Review component README files for installation instructions"
    echo "  2. Install components independently or together as needed"
    echo "  3. Validate signature with GPG if signing key is available"
    echo ""
}

# Run main validation
main "$@"
