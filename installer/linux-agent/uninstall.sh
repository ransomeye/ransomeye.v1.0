#!/bin/bash
#
# RansomEye v1.0 Linux Agent Uninstaller
# AUTHORITATIVE: Production-grade uninstaller for standalone Linux Agent
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
        error_exit "Uninstaller must be run as root (required for systemd service and file removal)"
    fi
}

# Detect installation root from manifest or prompt
detect_install_root() {
    # Try to find manifest in common locations
    local manifest_paths=(
        "/opt/ransomeye-agent/config/installer.manifest.json"
        "/usr/local/ransomeye-agent/config/installer.manifest.json"
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
    echo "RansomEye v1.0 Linux Agent Uninstaller"
    echo "======================================="
    echo ""
    echo "Installation manifest not found in common locations."
    echo "Enter installation root directory (absolute path, no trailing slash):"
    echo "  Example: /opt/ransomeye-agent"
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
    
    # Verify it's a RansomEye Linux Agent installation
    if [[ ! -f "${INSTALL_ROOT}/config/installer.manifest.json" ]]; then
        error_exit "Not a valid RansomEye Linux Agent installation: manifest not found at ${INSTALL_ROOT}/config/installer.manifest.json"
    fi
}

# Stop and remove systemd service
remove_systemd_service() {
    echo ""
    echo "Removing systemd service..."
    
    if systemctl list-unit-files --type=service | grep -q "^ransomeye-linux-agent.service"; then
        # Stop service if running
        if systemctl is-active --quiet ransomeye-linux-agent; then
            echo "Stopping ransomeye-linux-agent service..."
            systemctl stop ransomeye-linux-agent || error_exit "Failed to stop ransomeye-linux-agent service"
            echo -e "${GREEN}✓${NC} Service stopped"
        fi
        
        # Disable service
        systemctl disable ransomeye-linux-agent || error_exit "Failed to disable ransomeye-linux-agent service"
        echo -e "${GREEN}✓${NC} Service disabled"
        
        # Remove service file
        if [[ -f /etc/systemd/system/ransomeye-linux-agent.service ]]; then
            rm -f /etc/systemd/system/ransomeye-linux-agent.service || error_exit "Failed to remove systemd service file"
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
    echo "System user 'ransomeye-agent' management..."
    
    if id "ransomeye-agent" &>/dev/null; then
        echo "User 'ransomeye-agent' exists."
        echo "NOTE: Removing system user may affect other installations or services."
        echo -n "Remove user 'ransomeye-agent'? [y/N]: "
        read -r confirm_user
        
        if [[ "$confirm_user" == "y" || "$confirm_user" == "Y" ]]; then
            # Check if user is used by any other process
            if pgrep -u ransomeye-agent > /dev/null 2>&1; then
                error_exit "Cannot remove user 'ransomeye-agent': processes are still running as this user"
            fi
            
            userdel ransomeye-agent || error_exit "Failed to remove user 'ransomeye-agent'"
            echo -e "${GREEN}✓${NC} Removed user: ransomeye-agent"
        else
            echo -e "${YELLOW}✓${NC} User 'ransomeye-agent' kept (not removed)"
        fi
    else
        echo -e "${YELLOW}✓${NC} User 'ransomeye-agent' does not exist"
    fi
}

# Main uninstallation flow
main() {
    check_root
    detect_install_root
    remove_systemd_service
    remove_installation
    remove_system_user
    
    echo ""
    echo "================================================================================"
    echo -e "${GREEN}Uninstallation completed successfully!${NC}"
    echo "================================================================================"
    echo ""
    echo "RansomEye Linux Agent has been removed from this system."
    echo ""
    echo "NOTE: Linux Agent is standalone - no Core dependencies to clean up."
    echo ""
}

# Run main uninstallation
main "$@"
