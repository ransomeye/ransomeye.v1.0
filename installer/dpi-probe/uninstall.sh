#!/bin/bash
#
# RansomEye v1.0 DPI Probe Uninstaller
# AUTHORITATIVE: Production-grade uninstaller for standalone DPI Probe
# Fail-closed: Any error terminates uninstallation immediately
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

# Validate root privileges
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error_exit "Uninstaller must be run as root (required for systemd service, capability removal, and file removal)"
    fi
}

# Detect installation root from manifest or prompt
detect_install_root() {
    # Try to find manifest in common locations
    local manifest_paths=(
        "/opt/ransomeye/config/installer.manifest.json"
        "/usr/local/ransomeye-dpi/config/installer.manifest.json"
    )
    
    INSTALL_ROOT=""
    
    for manifest_path in "${manifest_paths[@]}"; do
        if [[ -f "$manifest_path" ]]; then
            # Extract install_root from manifest (simple JSON parsing)
            INSTALL_ROOT=$(grep -o '"install_root"[[:space:]]*:[[:space:]]*"[^"]*"' "$manifest_path" | cut -d'"' -f4 || true)
            if [[ -n "$INSTALL_ROOT" ]]; then
                echo -e "${GREEN}✓${NC} Found installation at: ${INSTALL_ROOT}"
                return
            fi
        fi
    done
    
    # Prompt if not found
    echo ""
    echo "RansomEye v1.0 DPI Probe Uninstaller"
    echo "====================================="
    echo ""
    echo "Installation manifest not found in common locations."
    echo "Enter installation root directory (absolute path, no trailing slash):"
    echo "  Example: /opt/ransomeye"
    echo -n "Install root: "
    
    read -r INSTALL_ROOT
    
    if [[ -z "$INSTALL_ROOT" ]]; then
        error_exit "Install root cannot be empty"
    fi
    
    # Validate: must be absolute path
    if [[ ! "$INSTALL_ROOT" =~ ^/ ]]; then
        error_exit "Install root must be an absolute path (starting with /)"
    fi
    
    if [[ ! -d "$INSTALL_ROOT" ]]; then
        error_exit "Installation directory does not exist: $INSTALL_ROOT"
    fi
    
    # Verify it's a RansomEye DPI Probe installation
    if [[ ! -f "${INSTALL_ROOT}/config/installer.manifest.json" ]]; then
        error_exit "Not a valid RansomEye DPI Probe installation: manifest not found at ${INSTALL_ROOT}/config/installer.manifest.json"
    fi
}

# Remove Linux capabilities
remove_capabilities() {
    echo ""
    echo "Removing Linux capabilities from DPI Probe script..."
    
    local probe_script="${INSTALL_ROOT}/bin/ransomeye-dpi-probe"
    
    if [[ -f "$probe_script" ]]; then
        if command -v setcap &> /dev/null; then
            # Remove all capabilities
            setcap -r "$probe_script" 2>/dev/null || true
            echo -e "${GREEN}✓${NC} Capabilities removed from DPI Probe script"
        else
            echo -e "${YELLOW}✓${NC} setcap not found, skipping capability removal"
        fi
    else
        echo -e "${YELLOW}✓${NC} DPI Probe script not found, skipping capability removal"
    fi
}

# Stop and remove systemd service
remove_systemd_service() {
    echo ""
    echo "Removing systemd service..."
    
    if systemctl list-unit-files --type=service | grep -q "^ransomeye-dpi.service"; then
        # Stop service if running
        if systemctl is-active --quiet ransomeye-dpi; then
            echo "Stopping ransomeye-dpi service..."
            systemctl stop ransomeye-dpi || error_exit "Failed to stop ransomeye-dpi service"
            echo -e "${GREEN}✓${NC} Service stopped"
        fi
        
        # Disable service
        systemctl disable ransomeye-dpi || error_exit "Failed to disable ransomeye-dpi service"
        echo -e "${GREEN}✓${NC} Service disabled"
        
        # Remove service file
        if [[ -f /etc/systemd/system/ransomeye-dpi.service ]]; then
            rm -f /etc/systemd/system/ransomeye-dpi.service || error_exit "Failed to remove systemd service file"
            echo -e "${GREEN}✓${NC} Service file removed"
        fi
        
        # Reload systemd
        systemctl daemon-reload || error_exit "Failed to reload systemd daemon"
        echo -e "${GREEN}✓${NC} Systemd daemon reloaded"
    else
        echo -e "${YELLOW}✓${NC} Service not found (may have been removed already)"
    fi
}

# Remove installation directory
remove_installation() {
    echo ""
    echo "Removing installation directory..."
    
    if [[ -d "$INSTALL_ROOT" ]]; then
        # Confirmation prompt
        echo ""
        echo "WARNING: This will permanently delete the installation directory:"
        echo "  ${INSTALL_ROOT}"
        echo ""
        echo "Logs and configuration will be lost."
        echo -n "Continue? [y/N]: "
        read -r confirm
        
        if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
            echo "Uninstallation cancelled."
            exit 0
        fi
        
        # Remove directory
        rm -rf "$INSTALL_ROOT" || error_exit "Failed to remove installation directory: $INSTALL_ROOT"
        echo -e "${GREEN}✓${NC} Removed: $INSTALL_ROOT"
    else
        echo -e "${YELLOW}✓${NC} Installation directory does not exist: $INSTALL_ROOT"
    fi
}

# Remove system user (optional, with confirmation)
remove_system_user() {
    echo ""
    echo "System user 'ransomeye-dpi' management..."
    
    if id "ransomeye-dpi" &>/dev/null; then
        echo "User 'ransomeye-dpi' exists."
        echo "NOTE: Removing system user may affect other installations or services."
        echo -n "Remove user 'ransomeye-dpi'? [y/N]: "
        read -r confirm_user
        
        if [[ "$confirm_user" == "y" || "$confirm_user" == "Y" ]]; then
            # Check if user is used by any other process
            if pgrep -u ransomeye-dpi > /dev/null 2>&1; then
                error_exit "Cannot remove user 'ransomeye-dpi': processes are still running as this user"
            fi
            
            userdel ransomeye-dpi || error_exit "Failed to remove user 'ransomeye-dpi'"
            echo -e "${GREEN}✓${NC} Removed user: ransomeye-dpi"
        else
            echo -e "${YELLOW}✓${NC} User 'ransomeye-dpi' kept (not removed)"
        fi
    else
        echo -e "${YELLOW}✓${NC} User 'ransomeye-dpi' does not exist"
    fi
}

# Main uninstallation flow
main() {
    check_root
    detect_install_root
    remove_capabilities
    remove_systemd_service
    remove_installation
    remove_system_user
    
    echo ""
    echo "================================================================================"
    echo -e "${GREEN}Uninstallation completed successfully!${NC}"
    echo "================================================================================"
    echo ""
    echo "RansomEye DPI Probe has been removed from this system."
    echo ""
    echo "NOTE: DPI Probe is supervised by Core; ensure Core is stopped."
    echo ""
}

# Run main uninstallation
main "$@"
